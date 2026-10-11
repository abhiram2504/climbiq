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
