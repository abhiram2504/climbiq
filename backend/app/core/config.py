from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ClimbIQ API"
    app_version: str = "0.2.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://climbiq:climbiq@localhost:5432/climbiq"
    video_storage_path: Path = Path("./data/videos")
    max_upload_size_mb: int = Field(default=250, ge=1, le=5_000)
    max_video_duration_seconds: int = Field(default=600, ge=5, le=3_600)
    pose_model_path: Path = Path("./models/pose_landmarker_full.task")
    pose_model_version: str = "pose_landmarker_full_float16_v1"
    pose_sampling_fps: float = Field(default=8.0, ge=0.5, le=60.0)
    pose_detection_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pose_presence_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pose_tracking_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pose_draw_visibility: float = Field(default=0.35, ge=0.0, le=1.0)
    processing_workers: int = Field(default=1, ge=1, le=4)
    ffmpeg_binary: str = "ffmpeg"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
