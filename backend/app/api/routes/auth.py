from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.google import (
    GMAIL_READONLY_SCOPE,
    GoogleOAuthClient,
    GoogleOAuthError,
    get_google_oauth_client,
)
from app.auth.security import (
    TokenCipher,
    create_session,
    ensure_utc,
    find_session,
    get_current_user,
    get_optional_user,
    hash_secret,
    utc_now,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import ClimbingSession, GmailConnection, OAuthFlow, User
from app.schemas.api import (
    AuthStatusResponse,
    GmailConnectionResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def frontend_redirect(settings: Settings, **parameters: str) -> RedirectResponse:
    target = settings.frontend_url.rstrip("/") + "/"
    if parameters:
        target += "?" + urlencode(parameters)
    response = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.oauth_state_cookie_name, path="/api/auth/google/callback")
    return response


def ensure_oauth_configured(settings: Settings) -> None:
    if not settings.google_oauth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth has not been configured on the server.",
        )


def create_oauth_flow(
    db: Session,
    settings: Settings,
    oauth: GoogleOAuthClient,
    *,
    purpose: str,
    user: User | None = None,
) -> tuple[str, str]:
    state_value = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    now = utc_now()
    db.execute(delete(OAuthFlow).where(OAuthFlow.expires_at <= now))
    db.add(
        OAuthFlow(
            state_hash=hash_secret(state_value),
            purpose=purpose,
            user_id=user.id if user else None,
            code_verifier=code_verifier,
            expires_at=now + timedelta(minutes=settings.oauth_flow_minutes),
        )
    )
    db.commit()
    return (
        oauth.authorization_url(
            state=state_value,
            code_challenge=code_challenge,
            purpose=purpose,
            login_hint=user.email if user else None,
        ),
        state_value,
    )


def oauth_redirect(url: str, state_value: str, settings: Settings) -> RedirectResponse:
    response = RedirectResponse(url)
    response.set_cookie(
        settings.oauth_state_cookie_name,
        state_value,
        max_age=settings.oauth_flow_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/api/auth/google/callback",
    )
    return response


@router.get("/me", response_model=AuthStatusResponse)
def auth_status(
    user: Annotated[User | None, Depends(get_optional_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthStatusResponse:
    if user is None:
        return AuthStatusResponse(
            authenticated=False,
            google_oauth_configured=settings.google_oauth_configured,
            gmail=GmailConnectionResponse(connected=False),
        )
    connection = db.scalar(select(GmailConnection).where(GmailConnection.user_id == user.id))
    gmail = (
        GmailConnectionResponse(
            connected=True,
            email=connection.email,
            scopes=connection.granted_scopes,
            connected_at=connection.connected_at,
        )
        if connection
        else GmailConnectionResponse(connected=False)
    )
    return AuthStatusResponse(
        authenticated=True,
        google_oauth_configured=settings.google_oauth_configured,
        user=UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            picture_url=user.picture_url,
        ),
        gmail=gmail,
    )


@router.get("/google/login")
def google_login(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    oauth: Annotated[GoogleOAuthClient, Depends(get_google_oauth_client)],
) -> RedirectResponse:
    ensure_oauth_configured(settings)
    url, state_value = create_oauth_flow(db, settings, oauth, purpose="login")
    return oauth_redirect(url, state_value, settings)


@router.get("/gmail/connect")
def gmail_connect(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    oauth: Annotated[GoogleOAuthClient, Depends(get_google_oauth_client)],
) -> RedirectResponse:
    ensure_oauth_configured(settings)
    url, state_value = create_oauth_flow(db, settings, oauth, purpose="gmail", user=user)
    return oauth_redirect(url, state_value, settings)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    oauth: Annotated[GoogleOAuthClient, Depends(get_google_oauth_client)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
    state_value: Annotated[str, Query(alias="state", min_length=16)],
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    browser_state = request.cookies.get(settings.oauth_state_cookie_name)
    if not browser_state or not secrets.compare_digest(browser_state, state_value):
        return frontend_redirect(settings, auth_error="invalid_state")
    flow = db.scalar(select(OAuthFlow).where(OAuthFlow.state_hash == hash_secret(state_value)))
    if flow is None:
        return frontend_redirect(settings, auth_error="invalid_state")

    purpose = flow.purpose
    flow_user_id = flow.user_id
    code_verifier = flow.code_verifier
    expired = ensure_utc(flow.expires_at) <= utc_now()
    db.delete(flow)
    db.commit()
    if expired:
        return frontend_redirect(settings, auth_error="expired_flow")
    if error or not code:
        return frontend_redirect(settings, auth_error="authorization_denied")

    try:
        tokens = await oauth.exchange_code(code=code, code_verifier=code_verifier)
        profile = await oauth.fetch_profile(tokens.access_token)
    except GoogleOAuthError:
        return frontend_redirect(settings, auth_error="google_verification_failed")
    if not profile.email_verified:
        return frontend_redirect(settings, auth_error="unverified_email")
    if not settings.email_is_allowed(profile.email):
        return frontend_redirect(settings, auth_error="access_denied")

    if purpose == "login":
        user = db.scalar(select(User).where(User.google_subject == profile.subject))
        if user is None:
            email_owner = db.scalar(select(User).where(User.email == profile.email))
            if email_owner is not None:
                return frontend_redirect(settings, auth_error="account_conflict")
            is_first_user = (db.scalar(select(func.count(User.id))) or 0) == 0
            user = User(
                google_subject=profile.subject,
                email=profile.email,
                display_name=profile.name,
                picture_url=profile.picture_url,
            )
            db.add(user)
            db.flush()
            if is_first_user:
                db.execute(
                    ClimbingSession.__table__.update()
                    .where(ClimbingSession.user_id.is_(None))
                    .values(user_id=user.id)
                )
        else:
            email_owner = db.scalar(
                select(User).where(User.email == profile.email, User.id != user.id)
            )
            if email_owner is not None:
                return frontend_redirect(settings, auth_error="account_conflict")
            user.email = profile.email
            user.display_name = profile.name
            user.picture_url = profile.picture_url
        session_token = create_session(db, user, settings)
        db.commit()
        response = frontend_redirect(settings, auth="success")
        response.set_cookie(
            settings.auth_cookie_name,
            session_token,
            max_age=settings.auth_session_days * 24 * 60 * 60,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        return response

    if purpose != "gmail" or flow_user_id is None:
        return frontend_redirect(settings, auth_error="invalid_flow")
    if current_user is None or current_user.id != flow_user_id:
        return frontend_redirect(settings, auth_error="session_changed")
    if profile.subject != current_user.google_subject:
        return frontend_redirect(settings, auth_error="google_account_mismatch")
    if GMAIL_READONLY_SCOPE not in tokens.scopes:
        return frontend_redirect(settings, gmail_error="scope_not_granted")

    cipher = TokenCipher(settings.token_encryption_key)
    connection = db.scalar(
        select(GmailConnection).where(GmailConnection.user_id == current_user.id)
    )
    if connection is None:
        if not tokens.refresh_token:
            return frontend_redirect(settings, gmail_error="offline_access_not_granted")
        connection = GmailConnection(
            user_id=current_user.id,
            google_subject=profile.subject,
            email=profile.email,
            access_token_encrypted=cipher.encrypt(tokens.access_token),
            refresh_token_encrypted=cipher.encrypt(tokens.refresh_token),
            granted_scopes=list(tokens.scopes),
            token_expires_at=tokens.expires_at,
        )
        db.add(connection)
    else:
        connection.google_subject = profile.subject
        connection.email = profile.email
        connection.access_token_encrypted = cipher.encrypt(tokens.access_token)
        if tokens.refresh_token:
            connection.refresh_token_encrypted = cipher.encrypt(tokens.refresh_token)
        connection.granted_scopes = list(tokens.scopes)
        connection.token_expires_at = tokens.expires_at
    db.commit()
    return frontend_redirect(settings, gmail="connected")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    auth_session = find_session(request, db, settings)
    if auth_session:
        auth_session.revoked_at = utc_now()
        db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return response


@router.delete("/gmail", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_gmail(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    oauth: Annotated[GoogleOAuthClient, Depends(get_google_oauth_client)],
) -> Response:
    connection = db.scalar(select(GmailConnection).where(GmailConnection.user_id == user.id))
    if connection is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    cipher = TokenCipher(settings.token_encryption_key)
    encrypted_token = connection.refresh_token_encrypted or connection.access_token_encrypted
    try:
        token = cipher.decrypt(encrypted_token)
        await oauth.revoke(token)
    except (GoogleOAuthError, ValueError):
        pass
    db.delete(connection)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
