"""NS1-T05/T06: operator-only catalog CRUD never accepts body or path escape."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from api.dependencies import require_operator_token
from src.runtime.config import Settings


def test_internal_prompt_crud_registers_new_version_and_rejects_body(tmp_path: Path) -> None:
    token = "ns1-operator-token"
    prompt_root = tmp_path / "prompts"
    shutil.copytree(Path("data/prompts"), prompt_root)
    (prompt_root / "route-test.md").write_text("route test body\n", encoding="utf-8")
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            prompt_root_path=prompt_root,
            inference_probe_enabled=False,
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
        )
    )
    async def operator_override() -> str:
        return "operator"

    app.dependency_overrides[require_operator_token] = operator_override
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            "/internal/prompts",
            headers=headers,
            json={
                "prompt_id": "promptA.route-test",
                "prompt_version": "v1",
                "role": "clean",
                "git_relative_path": "route-test.md",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["content_sha256"]
        listed = client.get("/internal/prompts", headers=headers)
        assert listed.status_code == 200
        assert any(item["prompt_id"] == "promptA.route-test" for item in listed.json()["items"])
        bad = client.post(
            "/internal/prompts",
            headers=headers,
            json={
                "prompt_id": "promptA.route-body",
                "prompt_version": "v1",
                "role": "clean",
                "git_relative_path": "../outside.md",
                "body": "must not be accepted",
            },
        )
        assert bad.status_code == 422


def test_internal_prompt_routes_reject_missing_token_and_external_peer(tmp_path: Path) -> None:
    token = "ns1-operator-token"
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            inference_probe_enabled=False,
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
        )
    )
    with TestClient(app, raise_server_exceptions=True) as client:
        missing = client.get("/internal/prompts")
        assert missing.status_code == 401
        # TestClient peer is not a loopback IP, so a valid token still hits the
        # internal-network fence when the operator dependency is not mocked.
        forbidden = client.get("/internal/prompts", headers={"Authorization": f"Bearer {token}"})
        assert forbidden.status_code == 403
