from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Climb, ClimbDiscipline, ClimbSource, User

MOUNTAIN_PROJECT_HEADER = (
    "Date",
    "Route",
    "Rating",
    "Notes",
    "URL",
    "Pitches",
    "Location",
    "Avg Stars",
    "Your Stars",
    "Style",
    "Lead Style",
    "Route Type",
    "Your Rating",
    "Length",
    "Rating Code",
)

_ROUTE_ID_RE = re.compile(r"/route/(\d+)(?:/|$)")
_ATTEMPT_MARKERS = ("fell", "hung", "attempt", "project", "did not send")


@dataclass(frozen=True)
class MountainProjectTick:
    climbed_on: date
    name: str
    grade: str
    notes: str | None
    url: str | None
    external_id: str | None
    pitches: int | None
    location: str | None
    average_stars: float | None
    user_stars: float | None
    style: str | None
    lead_style: str | None
    route_type: str | None
    user_rating: str | None
    length_ft: int | None
    rating_code: str | None
    source_entry_key: str

    @property
    def sent(self) -> bool:
        status = " ".join(filter(None, (self.style, self.lead_style))).casefold()
        return not any(marker in status for marker in _ATTEMPT_MARKERS)


def _clean(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _int(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def _float(value: str | None) -> float | None:
    cleaned = _clean(value)
    if cleaned is None or cleaned == "-1":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _mountain_project_url(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"}:
        return None
    if hostname != "mountainproject.com" and not hostname.endswith(".mountainproject.com"):
        return None
    return cleaned


def _date(value: str) -> date:
    cleaned = value.strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date: {cleaned or '(blank)'}")


def infer_grade_system(grade: str) -> str | None:
    normalized = grade.strip().upper()
    if normalized.startswith("5."):
        return "YDS"
    if re.match(r"^V\d", normalized):
        return "V-scale"
    if re.match(r"^[4-9][ABC][+-]?", normalized):
        return "Font"
    if normalized.startswith(("WI", "AI")):
        return "Ice"
    if re.match(r"^M\d", normalized):
        return "Mixed"
    return None


def identity_key(
    *,
    source: ClimbSource,
    discipline: ClimbDiscipline,
    external_id: str | None,
    name: str,
    grade: str,
    location: str | None,
    board_name: str | None = None,
    board_angle: int | None = None,
) -> str:
    if external_id:
        value = f"{source.value}|{external_id.strip()}"
    else:
        parts = (
            source.value,
            discipline.value,
            name.strip().casefold(),
            grade.strip().casefold(),
            (location or "").strip().casefold(),
            (board_name or "").strip().casefold(),
            str(board_angle or ""),
        )
        value = "|".join(parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_mountain_project_csv(content: bytes) -> tuple[list[MountainProjectTick], list[str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The Mountain Project export must be a UTF-8 CSV file.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("The CSV file is empty.")
    normalized_header = tuple((name or "").strip() for name in reader.fieldnames)
    if normalized_header != MOUNTAIN_PROJECT_HEADER:
        raise ValueError(
            "This does not match the current Mountain Project tick export format. "
            "Export the CSV from Profile → Ticks → Export CSV."
        )

    parsed: list[MountainProjectTick] = []
    errors: list[str] = []
    occurrences: Counter[str] = Counter()
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        try:
            route = _clean(row["Route"])
            grade = _clean(row["Rating"])
            if route is None or grade is None:
                raise ValueError("Route and Rating are required")
            row_fingerprint = "\x1f".join(
                (row[column] or "").strip() for column in MOUNTAIN_PROJECT_HEADER
            )
            occurrence = occurrences[row_fingerprint]
            occurrences[row_fingerprint] += 1
            source_entry_key = hashlib.sha256(
                f"mountain_project|{row_fingerprint}|{occurrence}".encode()
            ).hexdigest()
            url = _mountain_project_url(row["URL"])
            route_id_match = _ROUTE_ID_RE.search(url or "")
            parsed.append(
                MountainProjectTick(
                    climbed_on=_date(row["Date"]),
                    name=route,
                    grade=grade,
                    notes=_clean(row["Notes"]),
                    url=url,
                    external_id=route_id_match.group(1) if route_id_match else None,
                    pitches=_int(row["Pitches"]),
                    location=_clean(row["Location"]),
                    average_stars=_float(row["Avg Stars"]),
                    user_stars=_float(row["Your Stars"]),
                    style=_clean(row["Style"]),
                    lead_style=_clean(row["Lead Style"]),
                    route_type=_clean(row["Route Type"]),
                    user_rating=_clean(row["Your Rating"]),
                    length_ft=_int(row["Length"]),
                    rating_code=_clean(row["Rating Code"]),
                    source_entry_key=source_entry_key,
                )
            )
        except ValueError as exc:
            errors.append(f"Row {row_number}: {exc}")
    return parsed, errors


def find_or_create_climb(
    db: Session,
    user: User,
    *,
    source: ClimbSource,
    discipline: ClimbDiscipline,
    external_id: str | None,
    name: str,
    grade: str,
    grade_system: str | None = None,
    location: str | None = None,
    route_type: str | None = None,
    external_url: str | None = None,
    pitches: int | None = None,
    length_ft: int | None = None,
    board_name: str | None = None,
    board_angle: int | None = None,
    setter: str | None = None,
    is_benchmark: bool = False,
    metadata: dict[str, Any] | None = None,
) -> Climb:
    key = identity_key(
        source=source,
        discipline=discipline,
        external_id=external_id,
        name=name,
        grade=grade,
        location=location,
        board_name=board_name,
        board_angle=board_angle,
    )
    climb = db.scalar(
        select(Climb).where(Climb.user_id == user.id, Climb.identity_key == key)
    )
    if climb is None:
        climb = Climb(
            user_id=user.id,
            identity_key=key,
            source=source,
            discipline=discipline,
            external_id=external_id,
            name=name.strip(),
            grade=grade.strip(),
            grade_system=grade_system or infer_grade_system(grade),
            location=_clean(location),
            route_type=_clean(route_type),
            external_url=_clean(external_url),
            pitches=pitches,
            length_ft=length_ft,
            board_name=_clean(board_name),
            board_angle=board_angle,
            setter=_clean(setter),
            is_benchmark=is_benchmark,
            metadata_json=metadata or {},
        )
        db.add(climb)
        db.flush()
    else:
        # Imports can enrich an existing manual record without replacing user-owned text.
        climb.external_url = climb.external_url or _clean(external_url)
        climb.location = climb.location or _clean(location)
        climb.route_type = climb.route_type or _clean(route_type)
        climb.pitches = climb.pitches or pitches
        climb.length_ft = climb.length_ft or length_ft
    return climb
