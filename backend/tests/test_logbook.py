from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient

HEADER = [
    "Date",
    "Route",
    "Rating",
    "Notes",
    "URL",
    "Pitches",
    "Location",
    "Avg Stars",
    "Your Stars",
    "Style",
    "Lead Style",
    "Route Type",
    "Your Rating",
    "Length",
    "Rating Code",
]


def mountain_project_csv() -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(HEADER)
    writer.writerow(
        [
            "2026-10-01",
            "The Classic",
            "5.10a",
            "Clean send",
            "https://www.mountainproject.com/route/123456/the-classic",
            "1",
            "Main Wall > Test Crag > Colorado",
            "3.8",
            "4",
            "Lead",
            "Redpoint",
            "Sport",
            "5.10a",
            "80",
            "1800",
        ]
    )
    writer.writerow(
        [
            "2026-10-02",
            "Project Line",
            "5.12a",
            "Two hangs",
            "https://www.mountainproject.com/route/654321/project-line",
            "1",
            "Upper Wall > Test Crag > Colorado",
            "4.0",
            "-1",
            "Lead",
            "Fell/Hung",
            "Sport",
            "",
            "95",
            "2100",
        ]
    )
    return stream.getvalue().encode()


def test_manual_moonboard_entry_and_summary(client: TestClient) -> None:
    response = client.post(
        "/api/logbook",
        json={
            "discipline": "moonboard",
            "source": "moonboard",
            "name": "Hard Times",
            "grade": "7A",
            "board_name": "MoonBoard 2016",
            "board_angle": 40,
            "climbed_on": "2026-10-10",
            "outcome": "send",
            "ascent_type": "repeat",
            "attempts": 3,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["climb"]["discipline"] == "moonboard"
    assert payload["climb"]["board_angle"] == 40

    listing = client.get("/api/logbook")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    summary = client.get("/api/logbook/summary")
    assert summary.status_code == 200
    assert summary.json()["total_sends"] == 1
    assert summary.json()["moonboard_sends"] == 1
    assert summary.json()["hardest_moonboard"] == "7A"


def test_mountain_project_import_is_idempotent(client: TestClient) -> None:
    files = {"file": ("ticks.csv", mountain_project_csv(), "text/csv")}
    first = client.post("/api/logbook/import/mountain-project", files=files)
    assert first.status_code == 200
    assert first.json() == {"imported": 2, "skipped": 0, "errors": []}

    second = client.post("/api/logbook/import/mountain-project", files=files)
    assert second.status_code == 200
    assert second.json() == {"imported": 0, "skipped": 2, "errors": []}

    listing = client.get("/api/logbook")
    assert listing.json()["total"] == 2
    items = listing.json()["items"]
    assert items[0]["outcome"] == "attempt"
    assert items[1]["outcome"] == "send"
    assert items[1]["rating"] == 4.0
    assert items[1]["climb"]["external_id"] == "123456"


def test_rejects_non_mountain_project_csv(client: TestClient) -> None:
    response = client.post(
        "/api/logbook/import/mountain-project",
        files={"file": ("other.csv", b"name,grade\nTest,V4\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "Mountain Project" in response.json()["detail"]


def test_summary_keeps_outdoor_grade_systems_separate(client: TestClient) -> None:
    base = {
        "discipline": "outdoor",
        "source": "manual",
        "climbed_on": "2026-10-12",
        "outcome": "send",
        "attempts": 1,
    }
    assert client.post(
        "/api/logbook", json={**base, "name": "Rope Route", "grade": "5.11a"}
    ).status_code == 201
    assert client.post(
        "/api/logbook", json={**base, "name": "Granite Bloc", "grade": "V5"}
    ).status_code == 201

    summary = client.get("/api/logbook/summary")
    assert summary.status_code == 200
    assert summary.json()["hardest_outdoor"] == "5.11a · V5"


def test_rejects_unsafe_external_url(client: TestClient) -> None:
    response = client.post(
        "/api/logbook",
        json={
            "discipline": "outdoor",
            "source": "manual",
            "name": "Suspicious Link",
            "grade": "V1",
            "external_url": "javascript:alert(1)",
            "climbed_on": "2026-10-12",
            "outcome": "send",
        },
    )
    assert response.status_code == 422


def test_rejects_a_different_moonboard_setup(client: TestClient) -> None:
    response = client.post(
        "/api/logbook",
        json={
            "discipline": "moonboard",
            "source": "moonboard",
            "name": "Wrong Wall",
            "grade": "6C",
            "board_name": "MoonBoard 2024",
            "board_angle": 40,
            "climbed_on": "2026-10-12",
            "outcome": "send",
        },
    )
    assert response.status_code == 422
    assert "2016" in response.json()["detail"]
