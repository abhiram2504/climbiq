from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi.testclient import TestClient

from app.auth.google import (
    GMAIL_READONLY_SCOPE,
    GoogleProfile,
    GoogleTokens,
    get_google_oauth_client,
)
from app.main import app


def fake_mp4(payload_size: int = 128) -> bytes:
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    return header + (b"\x00" * payload_size)


class FakeGoogleOAuthClient:
    subject = "google-test-user"
    email = "climber@example.com"
    name = "Test Climber"

    def authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
        purpose: str,
        login_hint: str | None = None,
    ) -> str:
        parameters = {"state": state, "challenge": code_challenge, "purpose": purpose}
        if login_hint:
            parameters["login_hint"] = login_hint
        return "https://accounts.example.test/auth?" + urlencode(parameters)

    async def exchange_code(self, *, code: str, code_verifier: str) -> GoogleTokens:
        assert code == "test-code"
        assert code_verifier
        return GoogleTokens(
            access_token="google-access-token",
            refresh_token="google-refresh-token",
            scopes=("openid", "email", "profile", GMAIL_READONLY_SCOPE),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

    async def fetch_profile(self, access_token: str) -> GoogleProfile:
        assert access_token == "google-access-token"
        return GoogleProfile(
            subject=self.subject,
            email=self.email,
            email_verified=True,
            name=self.name,
            picture_url="https://images.example.test/climber.png",
        )

    async def revoke(self, token: str) -> None:
        assert token == "google-refresh-token"


class SecondGoogleOAuthClient(FakeGoogleOAuthClient):
    subject = "google-second-user"
    email = "second@example.com"
    name = "Second Climber"


def extract_state(location: str) -> str:
    values = parse_qs(urlparse(location).query)
    return values["state"][0]


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    client.cookies.clear()

    response = client.get("/api/videos")

    assert response.status_code == 401
    status = client.get("/api/auth/me")
    assert status.status_code == 200
    assert status.json()["authenticated"] is False


def test_google_login_creates_browser_session(client: TestClient) -> None:
    app.dependency_overrides[get_google_oauth_client] = lambda: FakeGoogleOAuthClient()
    client.cookies.clear()
    try:
        start = client.get("/api/auth/google/login", follow_redirects=False)
        assert start.status_code == 307
        state = extract_state(start.headers["location"])

        callback = client.get(
            "/api/auth/google/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        )

        assert callback.status_code == 303
        assert callback.headers["location"].endswith("/?auth=success")
        assert "HttpOnly" in callback.headers["set-cookie"]
        assert "SameSite=lax" in callback.headers["set-cookie"]
        status_response = client.get("/api/auth/me")
        assert status_response.json()["authenticated"] is True
        assert status_response.json()["user"]["email"] == "climber@example.com"
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)


def test_connect_and_disconnect_gmail(client: TestClient) -> None:
    app.dependency_overrides[get_google_oauth_client] = lambda: FakeGoogleOAuthClient()
    try:
        start = client.get("/api/auth/gmail/connect", follow_redirects=False)
        assert start.status_code == 307
        state = extract_state(start.headers["location"])
        assert "login_hint=climber%40example.com" in start.headers["location"]

        callback = client.get(
            "/api/auth/google/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        )

        assert callback.status_code == 303
        assert callback.headers["location"].endswith("/?gmail=connected")
        status_response = client.get("/api/auth/me").json()
        assert status_response["gmail"]["connected"] is True
        assert status_response["gmail"]["email"] == "climber@example.com"
        assert GMAIL_READONLY_SCOPE in status_response["gmail"]["scopes"]

        disconnect = client.delete("/api/auth/gmail")
        assert disconnect.status_code == 204
        assert client.get("/api/auth/me").json()["gmail"]["connected"] is False
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)


def test_oauth_state_can_only_be_used_once(client: TestClient) -> None:
    app.dependency_overrides[get_google_oauth_client] = lambda: FakeGoogleOAuthClient()
    client.cookies.clear()
    try:
        start = client.get("/api/auth/google/login", follow_redirects=False)
        state = extract_state(start.headers["location"])
        first = client.get(
            "/api/auth/google/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        )
        replay = client.get(
            "/api/auth/google/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        )

        assert first.status_code == 303
        assert replay.headers["location"].endswith("/?auth_error=invalid_state")
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)


def test_oauth_callback_requires_the_browser_that_started_the_flow(client: TestClient) -> None:
    app.dependency_overrides[get_google_oauth_client] = lambda: FakeGoogleOAuthClient()
    client.cookies.clear()
    try:
        start = client.get("/api/auth/google/login", follow_redirects=False)
        state = extract_state(start.headers["location"])
        client.cookies.delete("climbiq_oauth_state")

        callback = client.get(
            "/api/auth/google/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        )

        assert callback.status_code == 303
        assert callback.headers["location"].endswith("/?auth_error=invalid_state")
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)


def test_climbing_data_is_isolated_between_accounts(client: TestClient) -> None:
    upload = client.post(
        "/api/videos/upload",
        files={"video": ("private.mp4", fake_mp4(), "video/mp4")},
    )
    assert upload.status_code == 201
    first_user_video_id = upload.json()["id"]

    app.dependency_overrides[get_google_oauth_client] = lambda: SecondGoogleOAuthClient()
    client.cookies.clear()
    try:
        start = client.get("/api/auth/google/login", follow_redirects=False)
        state = extract_state(start.headers["location"])
        callback = client.get(
            "/api/auth/google/callback",
            params={"state": state, "code": "test-code"},
            follow_redirects=False,
        )
        assert callback.status_code == 303

        assert client.get("/api/videos").json()["total"] == 0
        assert client.get(f"/api/videos/{first_user_video_id}").status_code == 404
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)
