from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_database():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["database"], bool)
