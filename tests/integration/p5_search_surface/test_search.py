import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings
from smind_worker.main import run_worker


def _make_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp(prefix="smind-p5-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _register_with_team(client: TestClient, *, email: str, team_name: str, team_slug: str) -> dict:
    client.post(
        "/auth/register", json={"email": email, "password": "pw", "display_name": "p5"}
    )
    token = client.post("/auth/login", json={"email": email, "password": "pw"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/team/bootstrap", json={"name": team_name, "slug": team_slug}, headers=headers)
    return headers


def _prepare_index(client: TestClient, *, headers: dict, url: str, title: str) -> dict:
    return client.post(
        "/ingestion/url/submit",
        json={"url": url, "title": title},
        headers=headers,
    ).json()


def _drain_worker(rounds: int = 6) -> None:
    for _ in range(4):
        run_worker(once=True, poll_interval=0.0)
    for _ in range(max(0, rounds - 4)):
        run_worker(once=True, poll_interval=0.0)


def test_p5_search_and_debug_surface() -> None:
    client = _make_client()
    headers = _register_with_team(
        client,
        email="p5@example.com",
        team_name="Team P5",
        team_slug="team-p5",
    )
    _prepare_index(
        client,
        headers=headers,
        url="https://example.com/tax-policy-and-filing-guide",
        title="Guide",
    )
    _drain_worker(6)
    response = client.post("/search", json={"query": "tax policy", "limit": 5}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1
    assert isinstance(response.json()["items"][0]["chunk_text"], str)
    assert response.json()["items"][0]["chunk_text"].strip() != ""
    debug = client.post("/search/debug", json={"query": "tax policy", "limit": 5}, headers=headers)
    assert debug.status_code == 200
    assert debug.json()["count"] >= 1
    assert debug.json()["candidate_count"] >= debug.json()["count"]
    assert "filtered" in debug.json()


def test_p5_search_isolated_by_team() -> None:
    client = _make_client()
    headers_a = _register_with_team(
        client,
        email="a-p5@example.com",
        team_name="Team A",
        team_slug="team-a-p5",
    )
    headers_b = _register_with_team(
        client,
        email="b-p5@example.com",
        team_name="Team B",
        team_slug="team-b-p5",
    )
    doc_a = _prepare_index(
        client,
        headers=headers_a,
        url="https://example.com/apple-pie-recipe",
        title="Apple Pie",
    )["document_id"]
    doc_b = _prepare_index(
        client,
        headers=headers_b,
        url="https://example.com/tax-policy-reference",
        title="Tax Policy",
    )["document_id"]
    _drain_worker(8)

    search_b = client.post("/search", json={"query": "apple pie", "limit": 6}, headers=headers_b)
    assert search_b.status_code == 200
    for item in search_b.json()["items"]:
        assert item["document_id"] != doc_a
        assert item["document_id"] == doc_b
