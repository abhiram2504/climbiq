from __future__ import annotations

from dataclasses import dataclass

LANDMARK_NAMES = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)

# BlazePose body connections used for the review overlay. Facial contours are omitted so the
# visualization stays legible when the climber occupies a small part of a portrait recording.
POSE_CONNECTIONS = (
    (11, 12),
    (11, 13),
    (13, 15),
    (15, 17),
    (15, 19),
    (15, 21),
    (17, 19),
    (12, 14),
    (14, 16),
    (16, 18),
    (16, 20),
    (16, 22),
    (18, 20),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (27, 29),
    (29, 31),
    (27, 31),
    (24, 26),
    (26, 28),
    (28, 30),
    (30, 32),
    (28, 32),
)


@dataclass(frozen=True, slots=True)
class LandmarkValue:
    name: str
    detected: bool
    x: float | None = None
    y: float | None = None
    z: float | None = None
    visibility: float | None = None
    presence: float | None = None


@dataclass(frozen=True, slots=True)
class SampledPose:
    frame_index: int
    timestamp_ms: int
    landmarks: tuple[LandmarkValue, ...]


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    duration_ms: int
    width: int
    height: int
    source_fps: float
    frame_count: int


@dataclass(frozen=True, slots=True)
class ProcessingOutput:
    metadata: VideoMetadata
    samples: tuple[SampledPose, ...]
    annotated_path: str
