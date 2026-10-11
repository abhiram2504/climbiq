from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import (
    ClimbingSession,
    MovementMetric,
    ProcessingJob,
    ProcessingStatus,
    TechniqueObservation,
    VideoUpload,
)
from app.schemas.api import (
    AnalysisResponse,
    VideoListResponse,
    VideoResponse,
    VideoStatusResponse,
)
from app.services.processing_jobs import (
    ProcessingDispatcher,
    get_processing_dispatcher,
    queue_processing_job,
)
from app.services.video_storage import InvalidVideoError, UploadTooLargeError, VideoStorage

router = APIRouter(prefix="/videos", tags=["videos"])


def require_video(video_id: UUID, db: Session) -> VideoUpload:
    video = db.get(VideoUpload, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
    return video


def serialize_video(video: VideoUpload) -> VideoResponse:
    base = f"/api/videos/{video.id}"
    latest_job = max(video.jobs, key=lambda job: job.created_at, default=None)
    progress_percent = None
    if latest_job and latest_job.progress_total:
        progress_percent = min(
            100,
            round(latest_job.progress_current / latest_job.progress_total * 100),
        )
    response = VideoResponse.model_validate(video)
    return response.model_copy(
        update={
            "stream_url": f"{base}/stream",
            "status_url": f"{base}/status",
            "analysis_url": f"{base}/analysis",
            "annotated_url": f"{base}/annotated" if video.annotated_storage_key else None,
            "progress_percent": progress_percent,
        }
    )


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    video: Annotated[UploadFile, File(description="MP4 or MOV climbing video")],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    dispatcher: Annotated[ProcessingDispatcher, Depends(get_processing_dispatcher)],
    session_id: Annotated[UUID | None, Form()] = None,
    session_title: Annotated[str | None, Form(max_length=160)] = None,
) -> VideoResponse:
    climbing_session: ClimbingSession | None = None
    if session_id is not None:
        climbing_session = db.get(ClimbingSession, session_id)
        if climbing_session is None:
            raise HTTPException(status_code=404, detail="Climbing session not found.")

    video_id = uuid4()
    storage = VideoStorage(settings.video_storage_path, settings.max_upload_size_bytes)
    try:
        storage_key, size_bytes, original_name = await storage.save(video, video_id)
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except InvalidVideoError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if climbing_session is None:
        title = (session_title or "").strip() or f"Session · {datetime.now(UTC):%b %d, %Y}"
        climbing_session = ClimbingSession(title=title)
        db.add(climbing_session)
        db.flush()

    record = VideoUpload(
        id=video_id,
        session_id=climbing_session.id,
        original_filename=original_name,
        storage_key=storage_key,
        content_type=video.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        status=ProcessingStatus.uploaded,
    )
    db.add(record)
    job = queue_processing_job(db, record, settings)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        storage.delete(storage_key)
        raise HTTPException(status_code=500, detail="Could not save video metadata.") from exc
    db.refresh(record)
    db.refresh(job)
    try:
        dispatcher.enqueue(record.id, job.id, settings)
    except RuntimeError as exc:
        record.status = ProcessingStatus.failed
        record.error_message = str(exc)
        job.status = ProcessingStatus.failed
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail="Pose processor is unavailable.") from exc
    return serialize_video(record)


@router.get("", response_model=VideoListResponse)
def list_videos(db: Annotated[Session, Depends(get_db)]) -> VideoListResponse:
    videos = db.scalars(select(VideoUpload).order_by(VideoUpload.created_at.desc())).all()
    items = [serialize_video(video) for video in videos]
    return VideoListResponse(items=items, total=len(items))


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: UUID, db: Annotated[Session, Depends(get_db)]) -> VideoResponse:
    return serialize_video(require_video(video_id, db))


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(
    video_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> VideoStatusResponse:
    video = require_video(video_id, db)
    job = db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.video_id == video.id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    progress_current = job.progress_current if job else 0
    progress_total = job.progress_total if job else 0
    progress_percent = (
        min(100, round(progress_current / progress_total * 100)) if progress_total else None
    )
    return VideoStatusResponse(
        video_id=video.id,
        status=video.status,
        error_message=video.error_message,
        progress_current=progress_current,
        progress_total=progress_total,
        progress_percent=progress_percent,
        updated_at=video.updated_at,
    )


@router.post(
    "/{video_id}/process",
    response_model=VideoResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def process_video(
    video_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    dispatcher: Annotated[ProcessingDispatcher, Depends(get_processing_dispatcher)],
) -> VideoResponse:
    video = require_video(video_id, db)
    if video.status in {ProcessingStatus.queued, ProcessingStatus.processing}:
        raise HTTPException(status_code=409, detail="Video processing is already in progress.")

    job = queue_processing_job(db, video, settings)
    db.commit()
    db.refresh(video)
    db.refresh(job)
    try:
        dispatcher.enqueue(video.id, job.id, settings)
    except RuntimeError as exc:
        video.status = ProcessingStatus.failed
        video.error_message = str(exc)
        job.status = ProcessingStatus.failed
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail="Pose processor is unavailable.") from exc
    return serialize_video(video)


@router.get("/{video_id}/stream", response_class=FileResponse)
def stream_video(
    video_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    video = require_video(video_id, db)
    storage = VideoStorage(settings.video_storage_path, settings.max_upload_size_bytes)
    path = storage.resolve(video.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Video file is unavailable.")
    return FileResponse(path, media_type=video.content_type, filename=video.original_filename)


@router.get("/{video_id}/analysis", response_model=AnalysisResponse)
def get_analysis(video_id: UUID, db: Annotated[Session, Depends(get_db)]) -> AnalysisResponse:
    video = require_video(video_id, db)
    metrics = db.scalars(
        select(MovementMetric)
        .where(MovementMetric.video_id == video_id)
        .order_by(MovementMetric.timestamp_ms)
    ).all()
    observations = db.scalars(
        select(TechniqueObservation)
        .where(TechniqueObservation.video_id == video_id)
        .order_by(TechniqueObservation.start_timestamp_ms)
    ).all()
    analysis_status = {
        ProcessingStatus.uploaded: "not_started",
        ProcessingStatus.queued: "not_started",
        ProcessingStatus.processing: "processing",
        ProcessingStatus.completed: "completed",
        ProcessingStatus.failed: "failed",
    }[video.status]
    return AnalysisResponse(
        video_id=video.id,
        analysis_status=analysis_status,
        disclaimer=(
            "Measurements and observations describe detected motion; they do not establish "
            "correct or incorrect climbing technique."
        ),
        metrics=list(metrics),
        observations=list(observations),
    )


@router.get("/{video_id}/annotated", response_class=FileResponse)
def get_annotated_video(
    video_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    video = require_video(video_id, db)
    if not video.annotated_storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated video is not available yet.",
        )
    storage = VideoStorage(settings.video_storage_path, settings.max_upload_size_bytes)
    path: Path = storage.resolve(video.annotated_storage_key)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Annotated video is unavailable."
        )
    return FileResponse(path, media_type="video/mp4")
