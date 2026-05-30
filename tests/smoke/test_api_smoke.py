from fastapi.testclient import TestClient
from smind_api.main import create_app


def test_api_healthz() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

