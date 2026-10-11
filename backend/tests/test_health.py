from fastapi.testclient import TestClient


def test_health_reports_connected_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.0", "database": "connected"}
