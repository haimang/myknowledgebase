import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings
from smind_worker.main import run_worker
from storage_objects import FileSystemObjectStore
from workflow_rag import process_rag_step

from tests.fixtures.sqlite_kernel import make_kernel_dbs, seed_minimum_graph


def _make_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp(prefix="smind-p4-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _setup(client: TestClient) -> tuple[dict, str]:
    client.post(
        "/auth/register", json={"email": "p4@example.com", "password": "pw", "display_name": "p4"}
    )
    token = client.post("/auth/login", json={"email": "p4@example.com", "password": "pw"}).json()[
        "token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/team/bootstrap", json={"name": "Team P4", "slug": "team-p4"}, headers=headers)
    run_id = client.post(
        "/ingestion/url/submit",
        json={"url": "https://example.com/a", "title": "Doc"},
        headers=headers,
    ).json()["workflow_run_id"]
    return headers, run_id


_FAKE_HTML = (
    "<html><head><title>t</title><style>.x{}</style></head><body>"
    "<h1>Tax Policy Guide</h1>"
    "<p>Value added tax invoice rules for enterprises filing monthly returns.</p>"
    "<script>var x=1;</script>"
    "<p>Deductions and exemptions are explained for small businesses.</p>"
    "</body></html>"
)


def test_p4_rag_pipeline_reaches_completed_and_vectorized(monkeypatch) -> None:
    # F6a: htmlCrawl 真实抓取 — 注入本地 HTML fixture (不打外网, ⛔6)。
    monkeypatch.setattr("cleaners_universal.service.fetch_url", lambda url, **kw: _FAKE_HTML)
    client = _make_client()
    _, run_id = _setup(client)

    for _ in range(5):
        run_worker(once=True, poll_interval=0.0)

    core = connect(os.environ["SMIND_CORE_DB_PATH"])
    core.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    }
    run = core.execute("SELECT status FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
    assert run["status"] == "completed"
    chunk_count = core.execute(
        "SELECT COUNT(1) AS c FROM chunks WHERE workflow_run_id = ? AND vec_status = 'vectorized'",
        (run_id,),
    ).fetchone()["c"]
    assert chunk_count >= 1
    chunk = core.execute(
        """
        SELECT c.id, c.content_artifact_id, a.object_key
        FROM chunks c
        JOIN artifacts a ON a.id = c.content_artifact_id
        WHERE c.workflow_run_id = ?
        ORDER BY c.chunk_index
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    assert chunk is not None
    assert chunk["content_artifact_id"] is not None
    object_path = Path(os.environ["SMIND_OBJECT_STORE_DIR"]) / chunk["object_key"]
    assert object_path.exists()
    assert object_path.read_text(encoding="utf-8").strip() != ""


def test_p4_missing_run_raises_value_error() -> None:
    core_conn, vec_conn = make_kernel_dbs()
    ids = seed_minimum_graph(core_conn)
    core_conn.execute("PRAGMA foreign_keys=OFF;")
    core_conn.execute(
        """
        INSERT INTO workflow_steps (
            id, team_id, workflow_run_id, step_key, stage, action, payload_json, status
        ) VALUES (?, ?, ?, ?, 'rag:structurize', 'rag.structurize', '{}', 'pending')
        """,
        ("step_missing_run", ids["team_id"], "run_missing", "rag:missing"),
    )
    core_conn.commit()

    try:
        process_rag_step(
            core_conn,
            vec_conn,
            "test",
            "step_missing_run",
            FileSystemObjectStore(tempfile.mkdtemp(prefix="p4-missing-run-")),
        )
        assert False, "expected ValueError for missing run"
    except ValueError as exc:
        assert "run not found" in str(exc)
