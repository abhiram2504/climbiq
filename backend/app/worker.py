from __future__ import annotations

import logging
import signal
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models import ProcessingJob, ProcessingStatus, VideoUpload
from app.services.processing_jobs import PoseJobRunner

logger = logging.getLogger(__name__)


def recover_stale_jobs(
    session_factory: sessionmaker[Session],
    settings: Settings,
) -> int:
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.worker_stale_seconds)
    recovered = 0
    with session_factory() as db:
        jobs = db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.status == ProcessingStatus.processing,
                or_(ProcessingJob.started_at.is_(None), ProcessingJob.started_at < cutoff),
            )
        ).all()
        for job in jobs:
            video = db.get(VideoUpload, job.video_id)
            if job.attempts >= settings.worker_max_attempts:
                job.status = ProcessingStatus.failed
                job.error_message = "Processing stopped after repeated worker interruptions."
                job.completed_at = datetime.now(UTC)
                if video is not None:
                    video.status = ProcessingStatus.failed
                    video.error_message = job.error_message
                continue
            job.status = ProcessingStatus.queued
            job.error_message = None
            job.completed_at = None
            if video is not None:
                video.status = ProcessingStatus.queued
                video.error_message = None
            recovered += 1
        db.commit()
    return recovered


def claim_next_job(
    session_factory: sessionmaker[Session],
) -> tuple[UUID, UUID] | None:
    with session_factory() as db, db.begin():
        job = db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.status == ProcessingStatus.queued)
            .order_by(ProcessingJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        video = db.get(VideoUpload, job.video_id)
        if video is None:
            job.status = ProcessingStatus.failed
            job.error_message = "The queued video record no longer exists."
            job.completed_at = datetime.now(UTC)
            return None
        job.status = ProcessingStatus.processing
        job.started_at = datetime.now(UTC)
        video.status = ProcessingStatus.processing
        return video.id, job.id


def run_worker(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> None:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    stop = Event()

    def request_shutdown(signum: int, frame: object) -> None:
        logger.info("Worker received signal %s; stopping after the current job", signum)
        stop.set()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    recovered = recover_stale_jobs(session_factory, active_settings)
    if recovered:
        logger.info("Recovered %d stale pose-processing job(s)", recovered)
    logger.info("ClimbIQ pose worker is ready")
    runner = PoseJobRunner(session_factory)

    while not stop.is_set():
        claimed = claim_next_job(session_factory)
        if claimed is None:
            stop.wait(active_settings.worker_poll_seconds)
            continue
        video_id, job_id = claimed
        runner.run(video_id, job_id, active_settings)

    logger.info("ClimbIQ pose worker stopped")


if __name__ == "__main__":
    run_worker()
