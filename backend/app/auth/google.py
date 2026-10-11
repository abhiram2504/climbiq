from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_REVOCATION_ENDPOINT = "https://oauth2.googleapis.com/revoke"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
IDENTITY_SCOPES = ("openid", "email", "profile")


class GoogleOAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    subject: str
    email: str
    email_verified: bool
    name: str
    picture_url: str | None


@dataclass(frozen=True)
class GoogleTokens:
    access_token: str
    refresh_token: str | None
    scopes: tuple[str, ...]
    expires_at: datetime | None


class GoogleOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
        purpose: str,
        login_hint: str | None = None,
    ) -> str:
        scopes = list(IDENTITY_SCOPES)
        parameters = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if purpose == "gmail":
            scopes.append(GMAIL_READONLY_SCOPE)
            parameters.update(
                {
                    "scope": " ".join(scopes),
                    "access_type": "offline",
                    "prompt": "consent",
                    "include_granted_scopes": "true",
                }
            )
            if login_hint:
                parameters["login_hint"] = login_hint
        return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(parameters)}"

    async def exchange_code(self, *, code: str, code_verifier: str) -> GoogleTokens:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    GOOGLE_TOKEN_ENDPOINT,
                    data={
                        "code": code,
                        "client_id": self.settings.google_client_id,
                        "client_secret": self.settings.google_client_secret,
                        "redirect_uri": self.settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": code_verifier,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GoogleOAuthError("Google did not accept the authorization response.") from exc

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise GoogleOAuthError("Google did not return an access token.")
        refresh_token = payload.get("refresh_token")
        scope_value = payload.get("scope", "")
        expires_in = payload.get("expires_in")
        expires_at = None
        if isinstance(expires_in, (int, float)):
            expires_at = datetime.now(UTC) + timedelta(seconds=float(expires_in))
        return GoogleTokens(
            access_token=access_token,
            refresh_token=refresh_token if isinstance(refresh_token, str) else None,
            scopes=tuple(str(scope_value).split()),
            expires_at=expires_at,
        )

    async def fetch_profile(self, access_token: str) -> GoogleProfile:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    GOOGLE_USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GoogleOAuthError("Google profile verification failed.") from exc

        subject = payload.get("sub")
        email = payload.get("email")
        if not isinstance(subject, str) or not isinstance(email, str):
            raise GoogleOAuthError("Google did not return a usable profile.")
        return GoogleProfile(
            subject=subject,
            email=email.lower(),
            email_verified=payload.get("email_verified") is True,
            name=str(payload.get("name") or email.split("@", 1)[0]),
            picture_url=payload.get("picture") if isinstance(payload.get("picture"), str) else None,
        )

    async def revoke(self, token: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(GOOGLE_REVOCATION_ENDPOINT, data={"token": token})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Google token revocation failed.") from exc


def get_google_oauth_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleOAuthClient:
    return GoogleOAuthClient(settings)
