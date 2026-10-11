from __future__ import annotations

from fastapi.testclient import TestClient


def fake_mp4(payload_size: int = 128) -> bytes:
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    return header + (b"\x00" * payload_size)


def test_upload_list_status_analysis_and_stream(client: TestClient) -> None:
    upload = client.post(
        "/api/videos/upload",
        data={"session_title": "Saturday project session"},
        files={"video": ("send-7.mp4", fake_mp4(), "video/mp4")},
    )

    assert upload.status_code == 201
    created = upload.json()
    assert created["original_filename"] == "send-7.mp4"
    assert created["status"] == "queued"
    assert created["progress_percent"] is None
    assert created["stream_url"].endswith("/stream")

    video_id = created["id"]
    listing = client.get("/api/videos")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    status = client.get(f"/api/videos/{video_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "queued"
    assert status.json()["progress_current"] == 0

    analysis = client.get(f"/api/videos/{video_id}/analysis")
    assert analysis.status_code == 200
    assert analysis.json()["analysis_status"] == "not_started"
    assert analysis.json()["metrics"] == []

    stream = client.get(f"/api/videos/{video_id}/stream")
    assert stream.status_code == 200
    assert stream.content == fake_mp4()

    sessions = client.get("/api/sessions")
    assert sessions.status_code == 200
    assert sessions.json()["items"][0]["title"] == "Saturday project session"
    assert sessions.json()["items"][0]["attempt_count"] == 1

    duplicate = client.post(f"/api/videos/{video_id}/process")
    assert duplicate.status_code == 409


def test_upload_rejects_extension_and_invalid_container(client: TestClient) -> None:
    wrong_extension = client.post(
        "/api/videos/upload",
        files={"video": ("notes.txt", b"not video", "text/plain")},
    )
    assert wrong_extension.status_code == 400

    renamed_file = client.post(
        "/api/videos/upload",
        files={"video": ("not-video.mp4", b"not video", "video/mp4")},
    )
    assert renamed_file.status_code == 400


def test_unknown_video_returns_404(client: TestClient) -> None:
    response = client.get("/api/videos/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
