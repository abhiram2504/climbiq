from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models import PoseLandmark, ProcessingJob, ProcessingStatus, VideoUpload
from app.pose import VideoPoseProcessor
from app.services.video_storage import VideoStorage

logger = logging.getLogger(__name__)


class ProcessingDispatcher(Protocol):
    def enqueue(self, video_id: UUID, job_id: UUID, settings: Settings) -> None: ...

    def recover(self, settings: Settings) -> None: ...

    def shutdown(self) -> None: ...


def processing_configuration(settings: Settings) -> dict[str, float | int | str]:
    return {
        "sampling_fps": settings.pose_sampling_fps,
        "detection_confidence": settings.pose_detection_confidence,
        "presence_confidence": settings.pose_presence_confidence,
        "tracking_confidence": settings.pose_tracking_confidence,
        "draw_visibility": settings.pose_draw_visibility,
        "max_duration_seconds": settings.max_video_duration_seconds,
        "output_codec": "h264/yuv420p",
    }


def queue_processing_job(
    db: Session,
    video: VideoUpload,
    settings: Settings,
) -> ProcessingJob:
    job = ProcessingJob(
        video_id=video.id,
        status=ProcessingStatus.queued,
        task_name="pose_analysis",
        attempts=0,
        progress_current=0,
        progress_total=0,
        model_version=settings.pose_model_version,
        configuration_json=processing_configuration(settings),
    )
    video.status = ProcessingStatus.queued
    video.error_message = None
    db.add(job)
    return job


class LocalProcessingDispatcher:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        max_workers: int,
    ) -> None:
        self._session_factory = session_factory
        self._runner = PoseJobRunner(session_factory)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="climbiq-pose",
        )
        self._lock = Lock()
        self._in_flight: set[UUID] = set()
        self._closed = False

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def enqueue(self, video_id: UUID, job_id: UUID, settings: Settings) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("The pose-processing executor is shutting down.")
            if job_id in self._in_flight:
                return
            self._in_flight.add(job_id)

        future = self._executor.submit(self._runner.run, video_id, job_id, settings)
        future.add_done_callback(lambda completed: self._job_finished(job_id, completed))

    def recover(self, settings: Settings) -> None:
        queued: list[tuple[UUID, UUID]] = []
        with self._session_factory() as db:
            videos = db.scalars(
                select(VideoUpload).where(
                    VideoUpload.status.in_(
                        [ProcessingStatus.queued, ProcessingStatus.processing]
                    )
                )
            ).all()
            for video in videos:
                job = db.scalar(
                    select(ProcessingJob)
                    .where(ProcessingJob.video_id == video.id)
                    .order_by(ProcessingJob.created_at.desc())
                    .limit(1)
                )
                if job is None or job.status in {
                    ProcessingStatus.completed,
                    ProcessingStatus.failed,
                }:
                    job = queue_processing_job(db, video, settings)
                    db.flush()
                else:
                    video.status = ProcessingStatus.queued
                    job.status = ProcessingStatus.queued
                    job.error_message = None
                    job.completed_at = None
                queued.append((video.id, job.id))
            db.commit()

        for video_id, job_id in queued:
            self.enqueue(video_id, job_id, settings)
        if queued:
            logger.info("Recovered %d interrupted pose-processing job(s)", len(queued))

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _job_finished(self, job_id: UUID, future: Future[None]) -> None:
        with self._lock:
            self._in_flight.discard(job_id)
        exception = future.exception()
        if exception is not None:
            logger.error(
                "Pose job %s exited unexpectedly",
                job_id,
                exc_info=(type(exception), exception, exception.__traceback__),
            )

class PoseJobRunner:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def run(self, video_id: UUID, job_id: UUID, settings: Settings) -> None:
        storage = VideoStorage.from_settings(settings)
        annotated_key = f"{video_id}.{job_id}.annotated.mp4"
        previous_annotated_key: str | None = None

        try:
            with self._session_factory() as db:
                video = db.get(VideoUpload, video_id)
                job = db.get(ProcessingJob, job_id)
                if video is None or job is None:
                    logger.warning("Skipping missing video/job pair %s/%s", video_id, job_id)
                    return
                if job.status not in {ProcessingStatus.queued, ProcessingStatus.processing}:
                    return

                video.status = ProcessingStatus.processing
                video.error_message = None
                job.status = ProcessingStatus.processing
                job.attempts += 1
                job.started_at = datetime.now(UTC)
                job.completed_at = None
                job.error_message = None
                db.commit()

                last_progress = -1

                def update_progress(current: int, total: int) -> None:
                    nonlocal last_progress
                    percent = round(current / total * 100) if total else 0
                    if percent == last_progress and current != total:
                        return
                    last_progress = percent
                    job.progress_current = current
                    job.progress_total = total
                    db.commit()

                with (
                    storage.materialize(video.storage_key) as source_path,
                    storage.output(annotated_key) as annotated_path,
                ):
                    result = VideoPoseProcessor(settings).process(
                        source_path,
                        annotated_path,
                        progress_callback=update_progress,
                    )

                db.execute(delete(PoseLandmark).where(PoseLandmark.video_id == video_id))
                rows = [
                    {
                        "video_id": video_id,
                        "frame_index": sample.frame_index,
                        "timestamp_ms": sample.timestamp_ms,
                        "landmark_name": landmark.name,
                        "detected": landmark.detected,
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                        "visibility": landmark.visibility,
                        "presence": landmark.presence,
                    }
                    for sample in result.samples
                    for landmark in sample.landmarks
                ]
                for start in range(0, len(rows), 2_000):
                    db.execute(insert(PoseLandmark), rows[start : start + 2_000])

                previous_annotated_key = video.annotated_storage_key
                video.annotated_storage_key = annotated_key
                video.duration_ms = result.metadata.duration_ms
                video.width = result.metadata.width
                video.height = result.metadata.height
                video.source_fps = result.metadata.source_fps
                video.status = ProcessingStatus.completed
                video.error_message = None
                job.status = ProcessingStatus.completed
                job.progress_current = result.metadata.frame_count
                job.progress_total = result.metadata.frame_count
                job.completed_at = datetime.now(UTC)
                db.commit()

            if previous_annotated_key and previous_annotated_key != annotated_key:
                try:
                    storage.delete(previous_annotated_key)
                except Exception:
                    logger.warning(
                        "Could not remove superseded annotation %s",
                        previous_annotated_key,
                        exc_info=True,
                    )
            logger.info(
                "Completed pose job %s for video %s with %d sampled frames",
                job_id,
                video_id,
                len(result.samples),
            )
        except Exception as exc:
            try:
                storage.delete(annotated_key)
            except Exception:
                logger.warning(
                    "Could not remove failed annotation %s", annotated_key, exc_info=True
                )
            error_message = self._safe_error(exc)
            logger.exception("Pose job %s failed for video %s", job_id, video_id)
            with self._session_factory() as db:
                video = db.get(VideoUpload, video_id)
                job = db.get(ProcessingJob, job_id)
                if video is not None:
                    video.status = ProcessingStatus.failed
                    video.error_message = error_message
                if job is not None:
                    job.status = ProcessingStatus.failed
                    job.error_message = error_message
                    job.completed_at = datetime.now(UTC)
                db.commit()

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        return message[:1_000]


class DatabaseQueueDispatcher:
    def __init__(self) -> None:
        self._closed = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    def enqueue(self, video_id: UUID, job_id: UUID, settings: Settings) -> None:
        if self._closed:
            raise RuntimeError("The processing dispatcher is shutting down.")

    def recover(self, settings: Settings) -> None:
        return None

    def shutdown(self) -> None:
        self._closed = True


_dispatcher: LocalProcessingDispatcher | DatabaseQueueDispatcher | None = None
_dispatcher_lock = Lock()


def get_processing_dispatcher() -> ProcessingDispatcher:
    global _dispatcher
    with _dispatcher_lock:
        if _dispatcher is None or _dispatcher.is_closed:
            settings = get_settings()
            if settings.processing_mode == "database":
                _dispatcher = DatabaseQueueDispatcher()
            else:
                _dispatcher = LocalProcessingDispatcher(SessionLocal, settings.processing_workers)
        return _dispatcher
