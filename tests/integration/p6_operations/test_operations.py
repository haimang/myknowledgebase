import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings
from smind_worker.main import run_worker


def _make_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp(prefix="smind-p6-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _bootstrap(client: TestClient) -> dict:
    client.post(
        "/auth/register", json={"email": "p6@example.com", "password": "pw", "display_name": "p6"}
    )
    token = client.post("/auth/login", json={"email": "p6@example.com", "password": "pw"}).json()[
        "token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/team/bootstrap", json={"name": "Team P6", "slug": "team-p6"}, headers=headers)
    submitted = client.post(
        "/ingestion/url/submit",
        json={"url": "https://example.com/ops", "title": "Ops Doc"},
        headers=headers,
    ).json()
    for _ in range(4):
        run_worker(once=True, poll_interval=0.0)
    submitted["headers"] = headers
    return submitted


def test_p6_restart_purge_and_health() -> None:
    client = _make_client()
    data = _bootstrap(client)
    headers = data["headers"]

    health = client.get("/ops/health", headers=headers)
    assert health.status_code == 200
    assert "stale_claims" in health.json()["item"]

    restart = client.post(
        "/ops/restarts",
        json={"workflow_run_id": data["workflow_run_id"], "mode": "recovery"},
        headers=headers,
    )
    assert restart.status_code == 200
    run_worker(once=True, poll_interval=0.0)

    purge = client.post("/ops/purges", json={"document_id": data["document_id"]}, headers=headers)
    assert purge.status_code == 200
    post_search = client.post("/search", json={"query": "ops", "limit": 5}, headers=headers)
    assert post_search.status_code == 200
    assert post_search.json()["items"] == []

    core = connect(os.environ["SMIND_CORE_DB_PATH"])
    core.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    }
    restart_row = core.execute(
        "SELECT started_at, completed_at FROM restart_requests WHERE id = ?",
        (restart.json()["request_id"],),
    ).fetchone()
    assert restart_row is not None
    assert "T" in restart_row["started_at"]
    assert "T" in restart_row["completed_at"]

    purge_row = core.execute(
        "SELECT started_at, completed_at FROM purge_requests WHERE id = ?",
        (purge.json()["request_id"],),
    ).fetchone()
    assert purge_row is not None
    assert "T" in purge_row["started_at"]
    assert "T" in purge_row["completed_at"]

    audit_count = core.execute("SELECT COUNT(1) AS c FROM audit_logs").fetchone()["c"]
    event_count = core.execute("SELECT COUNT(1) AS c FROM workflow_events").fetchone()["c"]
    assert audit_count >= 1
    assert event_count >= 1
