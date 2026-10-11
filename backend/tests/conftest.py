from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import hash_secret
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AuthSession, User
from app.services.processing_jobs import get_processing_dispatcher


class StubProcessingDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[tuple[UUID, UUID]] = []

    def enqueue(self, video_id: UUID, job_id: UUID, settings: Settings) -> None:
        self.enqueued.append((video_id, job_id))

    def recover(self, settings: Settings) -> None:
        return None

    def shutdown(self) -> None:
        return None


@pytest.fixture
def dispatcher() -> StubProcessingDispatcher:
    return StubProcessingDispatcher()


@pytest.fixture
def client(
    tmp_path: Path,
    dispatcher: StubProcessingDispatcher,
) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        video_storage_path=tmp_path / "videos",
        max_upload_size_mb=1,
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
    )
    session_token = "test-browser-session"
    with testing_session() as database:
        user = User(
            google_subject="google-test-user",
            email="climber@example.com",
            display_name="Test Climber",
        )
        database.add(user)
        database.flush()
        database.add(
            AuthSession(
                user_id=user.id,
                token_hash=hash_secret(session_token),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        database.commit()

    def override_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_processing_dispatcher] = lambda: dispatcher
    with TestClient(app) as test_client:
        test_client.cookies.set(settings.auth_cookie_name, session_token)
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
