from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.config import Settings
from app.pose.pipeline import VideoPoseProcessor
from app.pose.types import LANDMARK_NAMES, LandmarkValue


class FakePoseDetector:
    def __init__(self) -> None:
        self.calls = 0
        self.closed = False

    def detect(self, rgb_frame: object, timestamp_ms: int) -> tuple[LandmarkValue, ...]:
        self.calls += 1
        if self.calls == 2:
            return tuple(LandmarkValue(name=name, detected=False) for name in LANDMARK_NAMES)
        return tuple(
            LandmarkValue(
                name=name,
                detected=True,
                x=0.2 + (index % 6) * 0.1,
                y=0.15 + (index // 6) * 0.12,
                z=-0.01 * index,
                visibility=0.95,
                presence=0.98,
            )
            for index, name in enumerate(LANDMARK_NAMES)
        )

    def close(self) -> None:
        self.closed = True


def make_fixture_video(path: Path, fps: float = 12.0, frames: int = 18) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (160, 120),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV MP4 writer is unavailable on this runner")
    for frame_index in range(frames):
        frame = np.full((120, 160, 3), (20 + frame_index, 28, 35), dtype=np.uint8)
        cv2.circle(frame, (30 + frame_index * 3, 60), 12, (240, 240, 240), -1)
        writer.write(frame)
    writer.release()


def test_pipeline_samples_missing_landmarks_and_encodes_h264(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg is unavailable on this runner")

    source = tmp_path / "source.mp4"
    annotated = tmp_path / "annotated.mp4"
    make_fixture_video(source)
    detector = FakePoseDetector()
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        video_storage_path=tmp_path,
        pose_sampling_fps=4,
        max_video_duration_seconds=30,
    )

    output = VideoPoseProcessor(settings, detector_factory=lambda _: detector).process(
        source,
        annotated,
    )

    assert annotated.is_file()
    assert annotated.stat().st_size > 0
    assert output.metadata.width == 160
    assert output.metadata.height == 120
    assert output.metadata.frame_count == 18
    assert len(output.samples) >= 5
    assert all(len(sample.landmarks) == 33 for sample in output.samples)
    assert all(
        earlier.timestamp_ms < later.timestamp_ms
        for earlier, later in zip(output.samples, output.samples[1:], strict=False)
    )
    assert all(not landmark.detected for landmark in output.samples[1].landmarks)
    assert detector.closed

    codec = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,pix_fmt",
            "-of",
            "default=noprint_wrappers=1",
            str(annotated),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "codec_name=h264" in codec
    assert "pix_fmt=yuv420p" in codec
