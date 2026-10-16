from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def create_project(client: TestClient) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "name": "The Long Game",
            "grade": "5.12a",
            "location": "The Motherlode, Red River Gorge",
            "route_type": "Sport",
            "demand_tags": ["Crimp", "Power Endurance", "crimp"],
            "notes": "Build confidence through the upper crux.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_project_bridges_outdoor_attempts_and_board_drills(client: TestClient) -> None:
    project = create_project(client)
    project_id = project["id"]
    assert project["demand_tags"] == ["crimp", "power endurance"]
    assert project["momentum_score"] == 0
    assert "Add a MoonBoard problem" in project["next_action"]

    drill = client.post(
        f"/api/projects/{project_id}/drills",
        json={"name": "Pinch Me", "grade": "7A", "focus": "Upper crux lock-off"},
    )
    assert drill.status_code == 201
    assert drill.json()["drills"][0]["climb"]["board_name"] == "MoonBoard 2016"
    assert drill.json()["drills"][0]["climb"]["board_angle"] == 40

    board_log = client.post(
        "/api/logbook",
        json={
            "project_id": project_id,
            "discipline": "moonboard",
            "source": "moonboard",
            "name": "Pinch Me",
            "grade": "7A",
            "board_name": "MoonBoard 2016",
            "board_angle": 40,
            "climbed_on": "2026-10-15",
            "outcome": "send",
            "attempts": 3,
        },
    )
    assert board_log.status_code == 201
    assert board_log.json()["project_id"] == project_id

    outdoor_log = client.post(
        "/api/logbook",
        json={
            "project_id": project_id,
            "discipline": "outdoor",
            "source": "manual",
            "name": "The Long Game",
            "grade": "5.12a",
            "climbed_on": "2026-10-15",
            "outcome": "attempt",
            "attempts": 2,
        },
    )
    assert outdoor_log.status_code == 201

    listing = client.get("/api/projects")
    assert listing.status_code == 200
    current = listing.json()["items"][0]
    assert current["outdoor_attempts"] == 2
    assert current["board_sessions"] == 1
    assert current["drill_sends"] == 1
    assert current["momentum_score"] == 75

    target_send = client.post(
        "/api/logbook",
        json={
            "project_id": project_id,
            "discipline": "outdoor",
            "source": "manual",
            "name": "The Long Game",
            "grade": "5.12a",
            "climbed_on": "2026-10-15",
            "outcome": "send",
            "attempts": 1,
        },
    )
    assert target_send.status_code == 201
    assert client.get("/api/projects").json()["items"][0]["status"] == "sent"


def test_project_access_is_scoped_to_the_user(client: TestClient) -> None:
    response = client.post(
        f"/api/projects/{uuid4()}/drills",
        json={"name": "Unknown", "grade": "6B"},
    )
    assert response.status_code == 404
