from fastapi.testclient import TestClient
from smind_api.main import create_app


def test_api_healthz() -> None:
    # F2-04: /healthz is now a real probe of core + vec. On a healthy boot it
    # returns 200 with per-subsystem status (no longer a static {"status":"ok"}).
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["core"] == "ok"
    assert body["vec"] == "ok"

