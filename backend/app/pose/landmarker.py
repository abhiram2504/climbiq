from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol

from app.core.config import Settings
from app.pose.types import LANDMARK_NAMES, LandmarkValue


class PoseDetector(Protocol):
    def detect(self, rgb_frame: Any, timestamp_ms: int) -> tuple[LandmarkValue, ...]: ...

    def close(self) -> None: ...


class MediaPipePoseDetector:
    def __init__(self, settings: Settings) -> None:
        if not settings.pose_model_path.is_file():
            raise FileNotFoundError(
                f"Pose model is missing at {settings.pose_model_path}. Rebuild the backend "
                "container or download the configured model bundle."
            )

        import mediapipe as mp

        self._mp = mp
        self._presence_threshold = settings.pose_presence_confidence
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(settings.pose_model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=settings.pose_detection_confidence,
            min_pose_presence_confidence=settings.pose_presence_confidence,
            min_tracking_confidence=settings.pose_tracking_confidence,
            output_segmentation_masks=False,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def __enter__(self) -> MediaPipePoseDetector:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def detect(self, rgb_frame: Any, timestamp_ms: int) -> tuple[LandmarkValue, ...]:
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.pose_landmarks:
            return self._missing_landmarks()

        detected_landmarks = result.pose_landmarks[0]
        values: list[LandmarkValue] = []
        for index, name in enumerate(LANDMARK_NAMES):
            if index >= len(detected_landmarks):
                values.append(LandmarkValue(name=name, detected=False))
                continue

            landmark = detected_landmarks[index]
            presence = self._optional_float(landmark.presence)
            visibility = self._optional_float(landmark.visibility)
            detected = presence is None or presence >= self._presence_threshold
            values.append(
                LandmarkValue(
                    name=name,
                    detected=detected,
                    x=self._optional_float(landmark.x) if detected else None,
                    y=self._optional_float(landmark.y) if detected else None,
                    z=self._optional_float(landmark.z) if detected else None,
                    visibility=visibility,
                    presence=presence,
                )
            )
        return tuple(values)

    def close(self) -> None:
        self._landmarker.close()

    @staticmethod
    def _optional_float(value: object) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _missing_landmarks() -> tuple[LandmarkValue, ...]:
        return tuple(LandmarkValue(name=name, detected=False) for name in LANDMARK_NAMES)
