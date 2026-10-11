from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import AuthSession, ClimbingSession, User


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User, settings: Settings) -> str:
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utc_now()))
    token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_secret(token),
            expires_at=utc_now() + timedelta(days=settings.auth_session_days),
        )
    )
    return token


def find_session(request: Request, db: Session, settings: Settings) -> AuthSession | None:
    raw_token = request.cookies.get(settings.auth_cookie_name)
    if not raw_token:
        return None
    auth_session = db.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(
            AuthSession.token_hash == hash_secret(raw_token),
            AuthSession.revoked_at.is_(None),
        )
    )
    if auth_session is None or ensure_utc(auth_session.expires_at) <= utc_now():
        return None
    return auth_session


def get_optional_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User | None:
    auth_session = find_session(request, db, settings)
    if auth_session:
        return auth_session.user
    if settings.auth_required or settings.google_oauth_configured:
        return None

    user = db.scalar(select(User).where(User.google_subject == "local-development-user"))
    if user is None:
        user = User(
            google_subject="local-development-user",
            email="local@climbiq.dev",
            display_name="Local Climber",
        )
        db.add(user)
        db.flush()
        db.execute(
            ClimbingSession.__table__.update()
            .where(ClimbingSession.user_id.is_(None))
            .values(user_id=user.id)
        )
        db.commit()
    return user


def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required.",
        )
    return user


class TokenCipher:
    def __init__(self, secret: str) -> None:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Stored OAuth token could not be decrypted.") from exc
