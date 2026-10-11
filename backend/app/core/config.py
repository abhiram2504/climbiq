from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ClimbIQ API"
    app_version: str = "0.3.0"
    environment: Literal["development", "test", "production"] = "development"
    service_role: Literal["api", "worker"] = "api"
    database_url: str = "postgresql+psycopg://climbiq:climbiq@localhost:5432/climbiq"
    storage_backend: Literal["local", "s3"] = "local"
    video_storage_path: Path = Path("./data/videos")
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_region: str = "auto"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_signed_url_seconds: int = Field(default=900, ge=60, le=86_400)
    max_upload_size_mb: int = Field(default=250, ge=1, le=5_000)
    max_video_duration_seconds: int = Field(default=600, ge=5, le=3_600)
    pose_model_path: Path = Path("./models/pose_landmarker_full.task")
    pose_model_version: str = "pose_landmarker_full_float16_v1"
    pose_sampling_fps: float = Field(default=8.0, ge=0.5, le=60.0)
    pose_detection_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pose_presence_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pose_tracking_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pose_draw_visibility: float = Field(default=0.35, ge=0.0, le=1.0)
    processing_mode: Literal["local", "database"] = "local"
    processing_workers: int = Field(default=1, ge=1, le=4)
    worker_poll_seconds: float = Field(default=2.0, ge=0.25, le=60.0)
    worker_stale_seconds: int = Field(default=3_600, ge=300, le=86_400)
    worker_max_attempts: int = Field(default=3, ge=1, le=10)
    ffmpeg_binary: str = "ffmpeg"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    trusted_hosts: Annotated[list[str], NoDecode] = ["*"]
    frontend_url: str = "http://localhost:5173"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    auth_required: bool = False
    auth_allowed_emails: Annotated[list[str], NoDecode] = []
    auth_cookie_name: str = "climbiq_session"
    oauth_state_cookie_name: str = "climbiq_oauth_state"
    auth_cookie_secure: bool = False
    auth_session_days: int = Field(default=30, ge=1, le=365)
    oauth_flow_minutes: int = Field(default=10, ge=2, le=30)
    token_encryption_key: str = "development-only-change-before-production"
    log_level: str = "INFO"

    @field_validator("cors_origins", "trusted_hosts", "auth_allowed_emails", mode="before")
    @classmethod
    def parse_comma_separated_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def validate_security_configuration(self) -> Settings:
        only_one_google_secret = bool(self.google_client_id.strip()) != bool(
            self.google_client_secret.strip()
        )
        if only_one_google_secret:
            raise ValueError("Google OAuth client ID and secret must be configured together.")
        if self.storage_backend == "s3" and not all(
            value.strip()
            for value in (
                self.s3_endpoint_url,
                self.s3_bucket,
                self.s3_access_key_id,
                self.s3_secret_access_key,
            )
        ):
            raise ValueError("S3 storage requires endpoint, bucket, access key, and secret key.")
        if self.environment != "production":
            return self
        if self.service_role == "worker":
            if self.processing_mode != "database":
                raise ValueError("Production workers require PROCESSING_MODE=database.")
            if self.storage_backend != "s3":
                raise ValueError("Production workers require STORAGE_BACKEND=s3.")
            return self
        if not self.auth_required:
            raise ValueError("AUTH_REQUIRED must be true in production.")
        if not self.google_oauth_configured:
            raise ValueError("Google OAuth must be configured in production.")
        if not self.auth_allowed_emails:
            raise ValueError("AUTH_ALLOWED_EMAILS must contain at least one private-beta account.")
        if not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true in production.")
        if not self.frontend_url.startswith("https://"):
            raise ValueError("FRONTEND_URL must use HTTPS in production.")
        if not self.google_redirect_uri.startswith("https://"):
            raise ValueError("GOOGLE_REDIRECT_URI must use HTTPS in production.")
        if (
            self.token_encryption_key == "development-only-change-before-production"
            or len(self.token_encryption_key) < 32
        ):
            raise ValueError("TOKEN_ENCRYPTION_KEY must be a strong production secret.")
        if self.storage_backend != "s3":
            raise ValueError("Production APIs require STORAGE_BACKEND=s3.")
        if self.processing_mode != "database":
            raise ValueError("Production APIs require PROCESSING_MODE=database.")
        return self

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    def email_is_allowed(self, email: str) -> bool:
        allowed = {item.casefold() for item in self.auth_allowed_emails}
        return not allowed or email.casefold() in allowed


@lru_cache
def get_settings() -> Settings:
    return Settings()
