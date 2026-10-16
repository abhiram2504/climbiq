from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.auth.security import get_current_user
from app.db.session import get_db
from app.models import (
    Climb,
    ClimbDiscipline,
    ClimbingProject,
    ClimbLogEntry,
    ClimbOutcome,
    ClimbSource,
    ProjectDrill,
    ProjectStatus,
    User,
)
from app.schemas.api import (
    CreateLogbookEntryRequest,
    ImportLogbookResponse,
    LogbookEntryResponse,
    LogbookListResponse,
    LogbookSummaryResponse,
    ProgressPointResponse,
)
from app.services.logbook import find_or_create_climb, parse_mountain_project_csv

router = APIRouter(prefix="/logbook", tags=["logbook"])

MAX_IMPORT_BYTES = 5 * 1024 * 1024


def serialize_entry(entry: ClimbLogEntry) -> LogbookEntryResponse:
    return LogbookEntryResponse.model_validate(entry)


def require_entry(entry_id: UUID, db: Session, user: User) -> ClimbLogEntry:
    entry = db.scalar(
        select(ClimbLogEntry)
        .options(joinedload(ClimbLogEntry.climb))
        .where(ClimbLogEntry.id == entry_id, ClimbLogEntry.user_id == user.id)
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Logbook entry not found."
        )
    return entry


@router.get("", response_model=LogbookListResponse)
def list_logbook(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    discipline: Annotated[ClimbDiscipline | None, Query()] = None,
    outcome: Annotated[ClimbOutcome | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LogbookListResponse:
    filters = [ClimbLogEntry.user_id == user.id]
    if discipline is not None:
        filters.append(Climb.discipline == discipline)
    if outcome is not None:
        filters.append(ClimbLogEntry.outcome == outcome)

    base = select(ClimbLogEntry).join(Climb).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    entries = db.scalars(
        base.options(joinedload(ClimbLogEntry.climb))
        .order_by(ClimbLogEntry.climbed_on.desc(), ClimbLogEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return LogbookListResponse(items=[serialize_entry(entry) for entry in entries], total=total)


@router.post("", response_model=LogbookEntryResponse, status_code=status.HTTP_201_CREATED)
def create_logbook_entry(
    payload: CreateLogbookEntryRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> LogbookEntryResponse:
    if (
        payload.discipline == ClimbDiscipline.moonboard
        and payload.source == ClimbSource.mountain_project
    ):
        raise HTTPException(
            status_code=422,
            detail="A MoonBoard climb cannot use Mountain Project as its source.",
        )
    if payload.discipline == ClimbDiscipline.outdoor and payload.source == ClimbSource.moonboard:
        raise HTTPException(
            status_code=422, detail="An outdoor climb cannot use MoonBoard as its source."
        )
    if payload.discipline == ClimbDiscipline.moonboard and (
        payload.source != ClimbSource.moonboard
        or payload.board_name != "MoonBoard 2016"
        or payload.board_angle != 40
    ):
        raise HTTPException(
            status_code=422,
            detail="ClimbIQ currently supports MoonBoard 2016 at 40°.",
        )

    project = None
    if payload.project_id is not None:
        project = db.scalar(
            select(ClimbingProject)
            .options(joinedload(ClimbingProject.target_climb))
            .where(
                ClimbingProject.id == payload.project_id,
                ClimbingProject.user_id == user.id,
            )
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        if project.status == ProjectStatus.archived:
            raise HTTPException(status_code=409, detail="Archived projects cannot receive logs.")

    if project is not None and payload.discipline == ClimbDiscipline.outdoor:
        climb = project.target_climb
    else:
        climb = find_or_create_climb(
            db,
            user,
            source=payload.source,
            discipline=payload.discipline,
            external_id=payload.external_id,
            name=payload.name,
            grade=payload.grade,
            grade_system=payload.grade_system,
            location=payload.location,
            route_type=payload.route_type,
            external_url=payload.external_url,
            board_name=payload.board_name,
            board_angle=payload.board_angle,
            setter=payload.setter,
            is_benchmark=payload.is_benchmark,
        )
    entry = ClimbLogEntry(
        user_id=user.id,
        climb_id=climb.id,
        project_id=project.id if project is not None else None,
        climbed_on=payload.climbed_on,
        outcome=payload.outcome,
        ascent_type=(payload.ascent_type or "").strip() or None,
        attempts=payload.attempts,
        rating=payload.rating,
        notes=(payload.notes or "").strip() or None,
    )
    db.add(entry)
    if (
        project is not None
        and payload.discipline == ClimbDiscipline.outdoor
        and payload.outcome == ClimbOutcome.send
    ):
        project.status = ProjectStatus.sent
    db.commit()
    db.refresh(entry)
    return serialize_entry(entry)


@router.post("/import/mountain-project", response_model=ImportLogbookResponse)
async def import_mountain_project(
    file: Annotated[UploadFile, File(description="Mountain Project tick export CSV")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ImportLogbookResponse:
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="The CSV import must be 5 MB or smaller.")
    try:
        ticks, errors = parse_mountain_project_csv(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    incoming_keys = [tick.source_entry_key for tick in ticks]
    existing_keys = set(
        db.scalars(
            select(ClimbLogEntry.source_entry_key).where(
                ClimbLogEntry.user_id == user.id,
                ClimbLogEntry.source_entry_key.in_(incoming_keys),
            )
        ).all()
    )
    imported = 0
    skipped = 0
    for tick in ticks:
        if tick.source_entry_key in existing_keys:
            skipped += 1
            continue
        climb = find_or_create_climb(
            db,
            user,
            source=ClimbSource.mountain_project,
            discipline=ClimbDiscipline.outdoor,
            external_id=tick.external_id,
            name=tick.name,
            grade=tick.grade,
            location=tick.location,
            route_type=tick.route_type,
            external_url=tick.url,
            pitches=tick.pitches,
            length_ft=tick.length_ft,
            metadata={
                "average_stars": tick.average_stars,
                "user_rating": tick.user_rating,
                "rating_code": tick.rating_code,
            },
        )
        db.add(
            ClimbLogEntry(
                user_id=user.id,
                climb_id=climb.id,
                climbed_on=tick.climbed_on,
                outcome=ClimbOutcome.send if tick.sent else ClimbOutcome.attempt,
                ascent_type=tick.lead_style or tick.style,
                attempts=1,
                rating=tick.user_stars,
                notes=tick.notes,
                import_source="mountain_project_csv",
                source_entry_key=tick.source_entry_key,
            )
        )
        existing_keys.add(tick.source_entry_key)
        imported += 1
    db.commit()
    return ImportLogbookResponse(imported=imported, skipped=skipped, errors=errors[:50])


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_logbook_entry(
    entry_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    entry = require_entry(entry_id, db, user)
    climb = entry.climb
    project_id = entry.project_id
    db.delete(entry)
    db.flush()
    remaining = db.scalar(
        select(func.count(ClimbLogEntry.id)).where(ClimbLogEntry.climb_id == climb.id)
    ) or 0
    project_references = db.scalar(
        select(func.count(ClimbingProject.id)).where(
            ClimbingProject.target_climb_id == climb.id
        )
    ) or 0
    drill_references = db.scalar(
        select(func.count(ProjectDrill.id)).where(ProjectDrill.climb_id == climb.id)
    ) or 0
    if remaining == 0 and project_references == 0 and drill_references == 0:
        db.delete(climb)
    if project_id is not None:
        project = db.get(ClimbingProject, project_id)
        remaining_target_sends = db.scalar(
            select(func.count(ClimbLogEntry.id))
            .join(Climb)
            .where(
                ClimbLogEntry.project_id == project_id,
                ClimbLogEntry.outcome == ClimbOutcome.send,
                Climb.discipline == ClimbDiscipline.outdoor,
            )
        ) or 0
        if (
            project is not None
            and project.status == ProjectStatus.sent
            and remaining_target_sends == 0
        ):
            project.status = ProjectStatus.active
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _grade_score(grade: str) -> float:
    normalized = grade.upper().strip()
    v_match = re.match(r"V(\d+)", normalized)
    if v_match:
        return float(v_match.group(1))
    font_match = re.match(r"([4-9])([ABC])([+-]?)", normalized)
    if font_match:
        number, letter, modifier = font_match.groups()
        return (int(number) - 4) * 3 + "ABC".index(letter) + {"-": -0.25, "": 0, "+": 0.5}[modifier]
    yds_match = re.match(r"5\.(\d+)([ABCD])?", normalized)
    if yds_match:
        number, letter = yds_match.groups()
        return 100 + int(number) * 4 + ("ABCD".index(letter) if letter else 0)
    return -1


def _month_keys(today: date, count: int = 12) -> list[str]:
    month = today.year * 12 + today.month - 1
    keys: list[str] = []
    for offset in reversed(range(count)):
        value = month - offset
        keys.append(f"{value // 12:04d}-{value % 12 + 1:02d}")
    return keys


@router.get("/summary", response_model=LogbookSummaryResponse)
def logbook_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> LogbookSummaryResponse:
    entries = db.scalars(
        select(ClimbLogEntry)
        .options(joinedload(ClimbLogEntry.climb))
        .where(ClimbLogEntry.user_id == user.id)
    ).all()
    sends = [entry for entry in entries if entry.outcome == ClimbOutcome.send]
    outdoor_sends = [entry for entry in sends if entry.climb.discipline == ClimbDiscipline.outdoor]
    moonboard_sends = [
        entry for entry in sends if entry.climb.discipline == ClimbDiscipline.moonboard
    ]

    def hardest(items: list[ClimbLogEntry]) -> str | None:
        if not items:
            return None
        winners: dict[str, ClimbLogEntry] = {}
        for item in items:
            system = item.climb.grade_system or "Other"
            current = winners.get(system)
            if current is None or _grade_score(item.climb.grade) > _grade_score(
                current.climb.grade
            ):
                winners[system] = item
        system_order = {"YDS": 0, "V-scale": 1, "Font": 2, "Ice": 3, "Mixed": 4}
        ordered = sorted(winners.items(), key=lambda pair: system_order.get(pair[0], 99))
        return " · ".join(entry.climb.grade for _, entry in ordered)

    periods = _month_keys(date.today())
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"outdoor": 0, "moonboard": 0, "attempts": 0}
    )
    for entry in entries:
        key = entry.climbed_on.strftime("%Y-%m")
        if key not in periods:
            continue
        if entry.outcome == ClimbOutcome.send:
            counts[key][entry.climb.discipline.value] += 1
        else:
            counts[key]["attempts"] += 1

    return LogbookSummaryResponse(
        total_entries=len(entries),
        total_sends=len(sends),
        outdoor_sends=len(outdoor_sends),
        moonboard_sends=len(moonboard_sends),
        days_climbed=len({entry.climbed_on for entry in entries}),
        hardest_outdoor=hardest(outdoor_sends),
        hardest_moonboard=hardest(moonboard_sends),
        progress=[ProgressPointResponse(period=period, **counts[period]) for period in periods],
    )
