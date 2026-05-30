import os
import tempfile
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient
from smind_api.main import create_app
from smind_config.loader import load_settings


def _make_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp(prefix="smind-p2-"))
    os.environ["SMIND_CORE_DB_PATH"] = str(tmp / "core.db")
    os.environ["SMIND_VEC_DB_PATH"] = str(tmp / "vec.db")
    os.environ["SMIND_OBJECT_STORE_DIR"] = str(tmp / "objects")
    load_settings.cache_clear()
    return TestClient(create_app())


def _register_and_login(client: TestClient, *, email: str = "p2@example.com") -> str:
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": "pw", "display_name": "p2"},
    )
    assert reg.status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": "pw"})
    assert login.status_code == 200
    return login.json()["token"]


def _core_db():
    conn = connect(os.environ["SMIND_CORE_DB_PATH"])
    conn.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    }
    return conn


def test_p2_auth_team_ingestion_management_closure() -> None:
    client = _make_client()
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    blocked = client.post(
        "/ingestion/url/submit",
        json={"url": "https://example.com", "title": "blocked"},
        headers=headers,
    )
    assert blocked.status_code == 403

    team = client.post(
        "/team/bootstrap",
        json={"name": "Team P2", "slug": "team-p2"},
        headers=headers,
    )
    assert team.status_code == 200

    cfg = client.get("/workflow-configs", headers=headers)
    assert cfg.status_code == 200
    assert len(cfg.json()["items"]) >= 1

    init_file = client.post(
        "/ingestion/file/initiate",
        json={"filename": "a.txt", "mime_type": "text/plain"},
        headers=headers,
    )
    assert init_file.status_code == 200
    upload_id = init_file.json()["upload_id"]
    confirm_file = client.post(
        "/ingestion/file/confirm",
        json={"upload_id": upload_id, "title": "File A", "content": "hello"},
        headers=headers,
    )
    assert confirm_file.status_code == 200

    url_submit = client.post(
        "/ingestion/url/submit",
        json={"url": "https://example.com", "title": "Example"},
        headers=headers,
    )
    assert url_submit.status_code == 200

    api_submit = client.post(
        "/ingestion/api/submit",
        json={"external_ref": "api://x", "title": "API", "payload": {"k": "v"}},
        headers=headers,
    )
    assert api_submit.status_code == 200

    static_init = client.post(
        "/ingestion/static/initiate",
        json={"filename": "static.json", "mime_type": "application/json"},
        headers=headers,
    )
    assert static_init.status_code == 200
    static_confirm = client.post(
        "/ingestion/static/confirm",
        json={
            "upload_id": static_init.json()["upload_id"],
            "path": "/static/static.json",
            "content": "{\"ok\":true}",
            "role": "uploaded",
        },
        headers=headers,
    )
    assert static_confirm.status_code == 200

    workflows = client.get("/management/workflows", headers=headers)
    assert workflows.status_code == 200
    assert len(workflows.json()["items"]) >= 3
    workflow_id = workflows.json()["items"][0]["id"]
    workflow_detail = client.get(f"/management/workflows/{workflow_id}", headers=headers)
    assert workflow_detail.status_code == 200

    docs = client.get("/management/documents", headers=headers)
    assert docs.status_code == 200
    assert len(docs.json()["items"]) >= 4
    doc_id = docs.json()["items"][0]["id"]
    doc_detail = client.get(f"/management/documents/{doc_id}", headers=headers)
    assert doc_detail.status_code == 200

    static_files = client.get("/management/static-files", headers=headers)
    assert static_files.status_code == 200
    assert len(static_files.json()["items"]) >= 1
    sf_id = static_files.json()["items"][0]["id"]
    static_detail = client.get(f"/management/static-files/{sf_id}", headers=headers)
    assert static_detail.status_code == 200

    core = _core_db()
    source = core.execute(
        "SELECT source_kind FROM sources WHERE id = ?",
        (static_confirm.json()["source_id"],),
    ).fetchone()
    assert source is not None
    assert source["source_kind"] == "file"
    user = core.execute("SELECT password_hash FROM users WHERE email = 'p2@example.com'").fetchone()
    assert user is not None
    assert user["password_hash"].startswith("pbkdf2_sha256$")


def test_p2_team_select_rejects_non_member() -> None:
    client = _make_client()

    token_a = _register_and_login(client, email="a@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    team_a = client.post(
        "/team/bootstrap",
        json={"name": "Team A", "slug": "team-a"},
        headers=headers_a,
    )
    assert team_a.status_code == 200

    token_b = _register_and_login(client, email="b@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    non_member_select = client.post(
        "/team/select",
        json={"team_id": team_a.json()["team_id"]},
        headers=headers_b,
    )
    assert non_member_select.status_code == 403
    assert non_member_select.json()["detail"] == "team_membership_required"


def test_p2_expired_session_is_rejected() -> None:
    client = _make_client()
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    core = _core_db()
    core.execute(
        """
        UPDATE sessions
        SET expires_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-1 day')
        """
    )
    core.commit()

    expired = client.get("/auth/session", headers=headers)
    assert expired.status_code == 401
