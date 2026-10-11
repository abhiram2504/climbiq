from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ClimbingSession, VideoUpload
from app.schemas.api import SessionListResponse, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
def list_sessions(db: Annotated[Session, Depends(get_db)]) -> SessionListResponse:
    statement = (
        select(ClimbingSession, func.count(VideoUpload.id).label("attempt_count"))
        .outerjoin(VideoUpload)
        .group_by(ClimbingSession.id)
        .order_by(ClimbingSession.created_at.desc())
    )
    rows = db.execute(statement).all()
    items = [
        SessionResponse(
            id=session.id,
            title=session.title,
            notes=session.notes,
            created_at=session.created_at,
            attempt_count=attempt_count,
        )
        for session, attempt_count in rows
    ]
    return SessionListResponse(items=items, total=len(items))
