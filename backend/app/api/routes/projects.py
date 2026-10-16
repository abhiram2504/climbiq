from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.security import get_current_user
from app.db.session import get_db
from app.models import (
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
    ClimbResponse,
    CreateProjectDrillRequest,
    CreateProjectRequest,
    ProjectDrillResponse,
    ProjectListResponse,
    ProjectResponse,
    UpdateProjectStatusRequest,
)
from app.services.logbook import find_or_create_climb

router = APIRouter(prefix="/projects", tags=["projects"])


def project_query(user: User):
    return (
        select(ClimbingProject)
        .options(
            joinedload(ClimbingProject.target_climb),
            selectinload(ClimbingProject.drills).joinedload(ProjectDrill.climb),
            selectinload(ClimbingProject.logbook_entries).joinedload(ClimbLogEntry.climb),
        )
        .where(ClimbingProject.user_id == user.id)
        .execution_options(populate_existing=True)
    )


def require_project(project_id: UUID, db: Session, user: User) -> ClimbingProject:
    project = db.scalar(project_query(user).where(ClimbingProject.id == project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def serialize_project(project: ClimbingProject) -> ProjectResponse:
    entries = list(project.logbook_entries)
    board_entries = [
        entry for entry in entries if entry.climb.discipline == ClimbDiscipline.moonboard
    ]
    outdoor_entries = [
        entry for entry in entries if entry.climb.discipline == ClimbDiscipline.outdoor
    ]
    outdoor_attempts = sum(
        entry.attempts for entry in outdoor_entries if entry.outcome == ClimbOutcome.attempt
    )
    sent_climb_ids = {
        entry.climb_id for entry in board_entries if entry.outcome == ClimbOutcome.send
    }
    drill_sends = sum(drill.climb_id in sent_climb_ids for drill in project.drills)
    last_activity = max((entry.climbed_on for entry in entries), default=None)

    if project.status == ProjectStatus.sent:
        momentum_score = 100
        next_action = "Project sent — keep the training bridge as a record of what worked."
    else:
        drill_coverage = int((drill_sends / len(project.drills)) * 35) if project.drills else 0
        recently_active = (
            last_activity is not None
            and last_activity >= date.today() - timedelta(days=14)
        )
        recent_bonus = 10 if recently_active else 0
        momentum_score = min(
            95,
            drill_coverage
            + min(len(board_entries), 4) * 10
            + min(outdoor_attempts, 3) * 10
            + recent_bonus,
        )
        if not project.drills:
            next_action = "Add a MoonBoard problem that rehearses this route's crux demand."
        elif not board_entries:
            next_action = "Log a 2016/40° board session against one of your drills."
        elif drill_sends < len(project.drills):
            next_action = "Repeat an unsent drill, then record what changed in your beta."
        elif outdoor_attempts == 0:
            next_action = "Your drills are moving — schedule an outdoor attempt on the target."
        else:
            next_action = "Return to the crux and compare it with the board movement that improved."

    return ProjectResponse(
        id=project.id,
        status=project.status,
        demand_tags=project.demand_tags,
        notes=project.notes,
        created_at=project.created_at,
        updated_at=project.updated_at,
        target_climb=ClimbResponse.model_validate(project.target_climb),
        drills=[
            ProjectDrillResponse(
                id=drill.id,
                focus=drill.focus,
                created_at=drill.created_at,
                climb=ClimbResponse.model_validate(drill.climb),
                sent=drill.climb_id in sent_climb_ids,
            )
            for drill in project.drills
        ],
        outdoor_attempts=outdoor_attempts,
        board_sessions=len(board_entries),
        drill_sends=drill_sends,
        momentum_score=momentum_score,
        next_action=next_action,
        last_activity=last_activity,
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ProjectListResponse:
    projects = db.scalars(
        project_query(user).order_by(ClimbingProject.created_at.desc())
    ).all()
    projects.sort(key=lambda item: item.status != ProjectStatus.active)
    return ProjectListResponse(items=[serialize_project(project) for project in projects])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreateProjectRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    climb = find_or_create_climb(
        db,
        user,
        source=ClimbSource.manual,
        discipline=ClimbDiscipline.outdoor,
        external_id=None,
        name=payload.name,
        grade=payload.grade,
        location=payload.location,
        route_type=payload.route_type,
        external_url=payload.external_url,
    )
    existing = db.scalar(
        select(ClimbingProject).where(
            ClimbingProject.user_id == user.id,
            ClimbingProject.target_climb_id == climb.id,
            ClimbingProject.status == ProjectStatus.active,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="That climb is already an active project.")

    project = ClimbingProject(
        user_id=user.id,
        target_climb_id=climb.id,
        status=ProjectStatus.active,
        demand_tags=payload.demand_tags,
        notes=(payload.notes or "").strip() or None,
    )
    db.add(project)
    db.commit()
    return serialize_project(require_project(project.id, db, user))


@router.post(
    "/{project_id}/drills",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_drill(
    project_id: UUID,
    payload: CreateProjectDrillRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    project = require_project(project_id, db, user)
    if project.status != ProjectStatus.active:
        raise HTTPException(status_code=409, detail="Only active projects can receive new drills.")
    climb = find_or_create_climb(
        db,
        user,
        source=ClimbSource.moonboard,
        discipline=ClimbDiscipline.moonboard,
        external_id=None,
        name=payload.name,
        grade=payload.grade,
        board_name="MoonBoard 2016",
        board_angle=40,
    )
    if any(drill.climb_id == climb.id for drill in project.drills):
        raise HTTPException(status_code=409, detail="That MoonBoard drill is already attached.")
    db.add(
        ProjectDrill(
            project_id=project.id,
            climb_id=climb.id,
            focus=(payload.focus or "").strip() or None,
        )
    )
    db.commit()
    return serialize_project(require_project(project.id, db, user))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    payload: UpdateProjectStatusRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    project = require_project(project_id, db, user)
    project.status = payload.status
    db.commit()
    return serialize_project(require_project(project.id, db, user))
