from fastapi.testclient import TestClient

from api.main import SERVICE_VERSION, app


def test_health_endpoint_returns_stable_success_payload() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_metadata_has_version() -> None:
    assert app.version == SERVICE_VERSION
