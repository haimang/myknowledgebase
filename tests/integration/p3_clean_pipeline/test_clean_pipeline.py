import json
import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings
from smind_worker.main import run_worker


def _make_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp(prefix="smind-p3-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _register(client: TestClient) -> str:
    client.post(
        "/auth/register", json={"email": "p3@example.com", "password": "pw", "display_name": "p3"}
    )
    token = client.post("/auth/login", json={"email": "p3@example.com", "password": "pw"}).json()[
        "token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/team/bootstrap", json={"name": "Team P3", "slug": "team-p3"}, headers=headers)
    return token


_CHINATAX_JSON = json.dumps(
    {
        "items": [
            {
                "title": "增值税发票管理办法",
                "description": "企业按月申报增值税发票的规则与流程说明。",
                "publisher": "国家税务总局",
                "publish_date": "2026-01-01",
            }
        ]
    }
)


def test_p3_clean_step_creates_clean_artifact_and_rag_step(monkeypatch) -> None:
    # F6a: chinatax 真实 ETL — 注入本地 JSON 响应样本 (不打外网, ⛔6)。
    monkeypatch.setattr("providers_dedicated.service.fetch_api", lambda url, **kw: _CHINATAX_JSON)
    client = _make_client()
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    submitted = client.post(
        "/ingestion/url/submit",
        json={"url": "https://chinatax.gov.cn/policy", "title": "Policy"},
        headers=headers,
    )
    assert submitted.status_code == 200
    run_worker(once=True, poll_interval=0.0)

    core = connect(os.environ["SMIND_CORE_DB_PATH"])
    core.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    }
    artifact = core.execute(
        """
        SELECT *
        FROM artifacts
        WHERE artifact_type = 'cleaned_text'
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    assert artifact is not None
    next_step = core.execute(
        """
        SELECT *
        FROM workflow_steps
        WHERE stage = 'rag:structurize'
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    assert next_step is not None
    payload = json.loads(artifact["metadata_json"])
    assert isinstance(payload.get("text"), str)
    assert payload.get("text", "").strip() != ""


def test_p3_clean_file_reads_object_content() -> None:
    client = _make_client()
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    initiated = client.post(
        "/ingestion/file/initiate",
        json={"filename": "policy.txt", "mime_type": "text/plain"},
        headers=headers,
    )
    assert initiated.status_code == 200
    run = client.post(
        "/ingestion/file/confirm",
        json={
            "upload_id": initiated.json()["upload_id"],
            "title": "Policy",
            "content": "raw-file-content-123",
        },
        headers=headers,
    )
    assert run.status_code == 200
    run_worker(once=True, poll_interval=0.0)

    core = connect(os.environ["SMIND_CORE_DB_PATH"])
    core.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    }
    artifact = core.execute(
        """
        SELECT metadata_json
        FROM artifacts
        WHERE workflow_run_id = ? AND artifact_type = 'cleaned_text'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run.json()["workflow_run_id"],),
    ).fetchone()
    assert artifact is not None
    payload = json.loads(artifact["metadata_json"])
    assert payload["text"] == "raw-file-content-123"


def test_p3_clean_api_uses_payload_text() -> None:
    client = _make_client()
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    submitted = client.post(
        "/ingestion/api/submit",
        json={
            "external_ref": "api://demo",
            "title": "ApiDoc",
            "payload": {"text": "api-payload-xyz"},
        },
        headers=headers,
    )
    assert submitted.status_code == 200
    run_worker(once=True, poll_interval=0.0)

    core = connect(os.environ["SMIND_CORE_DB_PATH"])
    core.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    }
    artifact = core.execute(
        """
        SELECT metadata_json
        FROM artifacts
        WHERE workflow_run_id = ? AND artifact_type = 'cleaned_text'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (submitted.json()["workflow_run_id"],),
    ).fetchone()
    assert artifact is not None
    payload = json.loads(artifact["metadata_json"])
    assert payload["text"] == "api-payload-xyz"
