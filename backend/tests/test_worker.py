from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import ClimbingSession, ProcessingJob, ProcessingStatus, VideoUpload
from app.worker import claim_next_job, recover_stale_jobs


def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'worker.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def add_job(
    factory: sessionmaker[Session],
    *,
    status: ProcessingStatus,
    attempts: int = 0,
) -> tuple[VideoUpload, ProcessingJob]:
    with factory() as db:
        climbing_session = ClimbingSession(title="Worker test")
        video = VideoUpload(
            session=climbing_session,
            original_filename="attempt.mp4",
            storage_key=f"{datetime.now(UTC).timestamp()}-{attempts}.mp4",
            content_type="video/mp4",
            size_bytes=128,
            status=status,
        )
        job = ProcessingJob(
            video=video,
            status=status,
            attempts=attempts,
            started_at=datetime.now(UTC) - timedelta(hours=2),
        )
        db.add_all([climbing_session, video, job])
        db.commit()
        return video, job


def test_claim_next_job_moves_oldest_queue_item_to_processing(tmp_path: Path) -> None:
    factory = session_factory(tmp_path)
    video, job = add_job(factory, status=ProcessingStatus.queued)

    assert claim_next_job(factory) == (video.id, job.id)

    with factory() as db:
        claimed_job = db.get(ProcessingJob, job.id)
        claimed_video = db.get(VideoUpload, video.id)
        assert claimed_job is not None and claimed_job.status == ProcessingStatus.processing
        assert claimed_job.started_at is not None
        assert claimed_video is not None and claimed_video.status == ProcessingStatus.processing
    assert claim_next_job(factory) is None


def test_recover_stale_jobs_requeues_or_fails_by_attempt_count(tmp_path: Path) -> None:
    factory = session_factory(tmp_path)
    retry_video, retry_job = add_job(
        factory,
        status=ProcessingStatus.processing,
        attempts=1,
    )
    failed_video, failed_job = add_job(
        factory,
        status=ProcessingStatus.processing,
        attempts=3,
    )
    settings = Settings(
        _env_file=None,
        worker_stale_seconds=300,
        worker_max_attempts=3,
    )

    assert recover_stale_jobs(factory, settings) == 1

    with factory() as db:
        jobs = {item.id: item for item in db.scalars(select(ProcessingJob)).all()}
        videos = {item.id: item for item in db.scalars(select(VideoUpload)).all()}
        assert jobs[retry_job.id].status == ProcessingStatus.queued
        assert videos[retry_video.id].status == ProcessingStatus.queued
        assert jobs[failed_job.id].status == ProcessingStatus.failed
        assert videos[failed_video.id].status == ProcessingStatus.failed
        assert "repeated worker interruptions" in (jobs[failed_job.id].error_message or "")
