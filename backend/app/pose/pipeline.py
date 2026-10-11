from __future__ import annotations

import logging
import math
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.pose.landmarker import MediaPipePoseDetector, PoseDetector
from app.pose.types import (
    POSE_CONNECTIONS,
    LandmarkValue,
    ProcessingOutput,
    SampledPose,
    VideoMetadata,
)

logger = logging.getLogger(__name__)

DetectorFactory = Callable[[Settings], PoseDetector]
ProgressCallback = Callable[[int, int], None]


class VideoProcessingError(RuntimeError):
    pass


class VideoPoseProcessor:
    def __init__(
        self,
        settings: Settings,
        detector_factory: DetectorFactory = MediaPipePoseDetector,
    ) -> None:
        self.settings = settings
        self.detector_factory = detector_factory

    def process(
        self,
        source_path: Path,
        annotated_path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> ProcessingOutput:
        import cv2

        source_path = source_path.resolve()
        annotated_path = annotated_path.resolve()
        annotated_path.parent.mkdir(parents=True, exist_ok=True)
        token = uuid4().hex
        raw_path = annotated_path.parent / f".{annotated_path.stem}.{token}.raw.mp4"
        staging_path = annotated_path.parent / f".{annotated_path.stem}.{token}.part.mp4"

        capture = cv2.VideoCapture(str(source_path))
        writer = None
        detector: PoseDetector | None = None
        samples: list[SampledPose] = []
        actual_frame_count = 0
        last_timestamp_ms = -1
        width = 0
        height = 0

        try:
            if not capture.isOpened():
                raise VideoProcessingError("The uploaded video could not be decoded.")
            if hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
                capture.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)

            source_fps = self._safe_fps(capture.get(cv2.CAP_PROP_FPS))
            estimated_frames = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
            estimated_duration = estimated_frames / source_fps if estimated_frames else 0.0
            if estimated_duration > self.settings.max_video_duration_seconds:
                limit = self.settings.max_video_duration_seconds
                raise VideoProcessingError(
                    f"Video is longer than the {limit}-second limit."
                )

            detector = self.detector_factory(self.settings)
            sample_interval_ms = 1000.0 / self.settings.pose_sampling_fps
            next_sample_ms = 0.0
            current_landmarks: tuple[LandmarkValue, ...] = ()
            progress_stride = max(1, round(source_fps))

            while True:
                decoded, frame = capture.read()
                if not decoded:
                    break

                if writer is None:
                    height, width = frame.shape[:2]
                    writer = cv2.VideoWriter(
                        str(raw_path),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        source_fps,
                        (width, height),
                    )
                    if not writer.isOpened():
                        raise VideoProcessingError("Could not create the annotated video stream.")

                timestamp_ms = self._frame_timestamp_ms(
                    capture=capture,
                    cv2=cv2,
                    frame_index=actual_frame_count,
                    source_fps=source_fps,
                    previous_timestamp_ms=last_timestamp_ms,
                )
                last_timestamp_ms = timestamp_ms
                if timestamp_ms / 1000 > self.settings.max_video_duration_seconds:
                    limit = self.settings.max_video_duration_seconds
                    raise VideoProcessingError(
                        f"Video is longer than the {limit}-second limit."
                    )

                if timestamp_ms + 0.5 >= next_sample_ms:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    current_landmarks = detector.detect(rgb_frame, timestamp_ms)
                    samples.append(
                        SampledPose(
                            frame_index=actual_frame_count,
                            timestamp_ms=timestamp_ms,
                            landmarks=current_landmarks,
                        )
                    )
                    while next_sample_ms <= timestamp_ms + 0.5:
                        next_sample_ms += sample_interval_ms

                self._draw_pose(cv2, frame, current_landmarks, width, height)
                writer.write(frame)
                actual_frame_count += 1

                if progress_callback and actual_frame_count % progress_stride == 0:
                    progress_callback(actual_frame_count, estimated_frames)

            if writer is None or actual_frame_count == 0:
                raise VideoProcessingError("The uploaded video contains no decodable frames.")
            if not samples:
                raise VideoProcessingError("No video frames were available for pose sampling.")

            writer.release()
            writer = None
            capture.release()
            self._encode_browser_video(raw_path, source_path, staging_path)
            os.replace(staging_path, annotated_path)

            duration_ms = max(
                last_timestamp_ms,
                round(actual_frame_count / source_fps * 1000),
            )
            metadata = VideoMetadata(
                duration_ms=duration_ms,
                width=width,
                height=height,
                source_fps=source_fps,
                frame_count=actual_frame_count,
            )
            if progress_callback:
                progress_callback(actual_frame_count, actual_frame_count)
            return ProcessingOutput(
                metadata=metadata,
                samples=tuple(samples),
                annotated_path=str(annotated_path),
            )
        except VideoProcessingError:
            raise
        except Exception as exc:
            logger.exception("Unexpected pose processing failure for %s", source_path)
            raise VideoProcessingError(f"Pose processing failed: {exc}") from exc
        finally:
            capture.release()
            if writer is not None:
                writer.release()
            if detector is not None:
                detector.close()
            raw_path.unlink(missing_ok=True)
            staging_path.unlink(missing_ok=True)

    def _encode_browser_video(
        self,
        raw_path: Path,
        source_path: Path,
        staging_path: Path,
    ) -> None:
        command = [
            self.settings.ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(raw_path),
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-metadata:s:v:0",
            "rotate=0",
            "-shortest",
            str(staging_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=max(60, self.settings.max_video_duration_seconds * 3),
            )
        except FileNotFoundError as exc:
            raise VideoProcessingError(
                f"Video encoder '{self.settings.ffmpeg_binary}' is not installed."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise VideoProcessingError("Annotated video encoding timed out.") from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1:] or ["unknown encoding error"]
            raise VideoProcessingError(f"Annotated video encoding failed: {detail[0]}")
        if not staging_path.is_file() or staging_path.stat().st_size == 0:
            raise VideoProcessingError("Annotated video encoding produced an empty file.")

    def _draw_pose(
        self,
        cv2: object,
        frame: object,
        landmarks: tuple[LandmarkValue, ...],
        width: int,
        height: int,
    ) -> None:
        if not landmarks:
            return

        points: dict[int, tuple[int, int]] = {}
        for index, landmark in enumerate(landmarks):
            visible = landmark.visibility is None or (
                landmark.visibility >= self.settings.pose_draw_visibility
            )
            if not landmark.detected or not visible or landmark.x is None or landmark.y is None:
                continue
            points[index] = (round(landmark.x * width), round(landmark.y * height))

        for start, end in POSE_CONNECTIONS:
            if start in points and end in points:
                cv2.line(frame, points[start], points[end], (65, 220, 255), 3, cv2.LINE_AA)
        for point in points.values():
            cv2.circle(frame, point, 5, (118, 255, 61), -1, cv2.LINE_AA)
            cv2.circle(frame, point, 6, (12, 18, 20), 1, cv2.LINE_AA)

    @staticmethod
    def _safe_fps(value: float) -> float:
        if not math.isfinite(value) or value < 1 or value > 240:
            return 30.0
        return float(value)

    @staticmethod
    def _frame_timestamp_ms(
        capture: object,
        cv2: object,
        frame_index: int,
        source_fps: float,
        previous_timestamp_ms: int,
    ) -> int:
        reported = float(capture.get(cv2.CAP_PROP_POS_MSEC))
        fallback = frame_index / source_fps * 1000
        reported_is_useful = (
            math.isfinite(reported)
            and reported >= 0
            and (frame_index == 0 or reported > previous_timestamp_ms)
        )
        candidate = reported if reported_is_useful else fallback
        return max(round(candidate), previous_timestamp_ms + 1)
