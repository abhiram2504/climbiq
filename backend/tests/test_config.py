import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_accept_comma_separated_environment_value(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://192.168.1.92:5173",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://192.168.1.92:5173",
    ]


def test_render_database_url_uses_installed_psycopg_driver() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://climbiq:secret@database/climbiq",
    )

    assert settings.database_url == "postgresql+psycopg://climbiq:secret@database/climbiq"


def test_production_rejects_insecure_auth_configuration() -> None:
    with pytest.raises(ValidationError, match="AUTH_REQUIRED"):
        Settings(
            _env_file=None,
            environment="production",
            google_client_id="client-id",
            google_client_secret="client-secret",
        )


def test_private_beta_email_allowlist_is_case_insensitive() -> None:
    settings = Settings(
        _env_file=None,
        auth_allowed_emails="Climber@Example.com,coach@example.com",
    )

    assert settings.email_is_allowed("climber@example.com")
    assert not settings.email_is_allowed("other@example.com")


def test_production_worker_requires_durable_queue_and_storage() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        service_role="worker",
        processing_mode="database",
        storage_backend="s3",
        s3_endpoint_url="https://account.r2.cloudflarestorage.com",
        s3_bucket="climbiq-videos",
        s3_access_key_id="access-key",
        s3_secret_access_key="secret-key",
    )

    assert settings.service_role == "worker"

    with pytest.raises(ValidationError, match="PROCESSING_MODE"):
        Settings(_env_file=None, environment="production", service_role="worker")


def test_logbook_only_production_does_not_require_video_infrastructure() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        video_analysis_enabled=False,
        google_client_id="client-id",
        google_client_secret="client-secret",
        auth_required=True,
        auth_allowed_emails="climber@example.com",
        auth_cookie_secure=True,
        frontend_url="https://climbiq.example",
        google_redirect_uri="https://climbiq.example/api/auth/google/callback",
        token_encryption_key="a-production-secret-that-is-long-enough",
    )

    assert settings.video_analysis_enabled is False
    assert settings.storage_backend == "local"
    assert settings.processing_mode == "local"
