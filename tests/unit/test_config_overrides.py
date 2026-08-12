"""S14 L3 allowlist, deny+audit, and ops-vs-semantic digest proofs.

Maps to D07 / S14-A07, A08, A09, A10, A17, A18.  These tests drive the real
Task create → ConfigSnapshotService.prepare path; they do not re-implement
allowlist logic in the test body.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            internal_token="override-token",
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            inference_probe_enabled=False,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=1_000,
        )
    )
    return TestClient(app, raise_server_exceptions=True)


def _body(team_uuid: str, task_uuid: str, trace_uuid: str, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "source": {
                "source_kind": "inline_payload",
                "external_key": "override-doc",
                "content": "override body",
            }
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "test",
            "created_at": utc_now(),
        },
    }
    body.update(extra)
    return body


def _read_snapshot(tmp_path: Path, digest: str) -> dict[str, object]:
    for path in (tmp_path / "objects").rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() == digest:
                return json.loads(data)
    raise AssertionError(f"config snapshot object not found for digest {digest}")


def test_allowlisted_semantic_override_enters_l4_and_emits_domain_event(tmp_path: Path) -> None:
    """S14-A09 / A18: top_k within cap changes L4 digest + config.override_applied."""

    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer override-token"}
    with _client(tmp_path) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "override"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_body(
                team_uuid,
                task_uuid,
                trace_uuid,
                overrides={"top_k": 12, "profile_id": "clean.web.v1"},
            ),
        )
        assert created.status_code == 201, created.text

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        execution = connection.execute(
            "SELECT config_snapshot_digest,domain_binding_digest FROM mkb_executions WHERE task_uuid=?",
            (task_uuid,),
        ).fetchone()
        events = connection.execute(
            "SELECT event_type,payload_json FROM mkb_domain_events WHERE event_type='config.override_applied'"
        ).fetchall()
        audits = connection.execute(
            "SELECT action FROM mkb_security_audit_events WHERE action='config.override_denied'"
        ).fetchall()

    assert execution is not None
    assert len(events) == 1
    payload = json.loads(events[0]["payload_json"])
    assert payload["result"] == "applied"
    assert payload["override_keys"] == ["profile_id", "top_k"]
    assert payload["override_digest"]
    assert not audits
    snapshot = _read_snapshot(tmp_path, execution["config_snapshot_digest"])
    assert snapshot["l3"]["overrides"]["top_k"] == 12
    assert snapshot["l3"]["overrides"]["profile_id"] == "clean.web.v1"
    assert "dry_run" not in snapshot["l3"]["overrides"]
    assert snapshot["semantic_knobs"]["top_k"] == 12
    assert snapshot["flag_bundle_digest"]
    assert all(value is False for value in snapshot["flag_bundle"].values())


def test_ops_only_dry_run_does_not_change_binding_or_snapshot_digest(tmp_path: Path) -> None:
    """S14-A17: dry_run must not change config_snapshot_digest or domain_binding_digest."""

    team_uuid = uuid7()
    headers = {"Authorization": "Bearer override-token"}
    with _client(tmp_path) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "ops"},
            ).status_code
            == 201
        )
        base_task, base_trace = uuid7(), uuid7()
        base = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_body(team_uuid, base_task, base_trace),
        )
        assert base.status_code == 201, base.text
        ops_task, ops_trace = uuid7(), uuid7()
        ops = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_body(team_uuid, ops_task, ops_trace, overrides={"dry_run": True, "debug_trace": True}),
        )
        assert ops.status_code == 201, ops.text

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        base_row = connection.execute(
            "SELECT config_snapshot_digest,domain_binding_digest FROM mkb_executions WHERE task_uuid=?",
            (base_task,),
        ).fetchone()
        ops_row = connection.execute(
            "SELECT config_snapshot_digest,domain_binding_digest FROM mkb_executions WHERE task_uuid=?",
            (ops_task,),
        ).fetchone()
        events = connection.execute(
            "SELECT payload_json FROM mkb_domain_events "
            "WHERE event_type='config.override_applied' AND task_uuid=?",
            (ops_task,),
        ).fetchall()

    assert base_row is not None and ops_row is not None
    assert base_row["config_snapshot_digest"] == ops_row["config_snapshot_digest"]
    assert base_row["domain_binding_digest"] == ops_row["domain_binding_digest"]
    assert len(events) == 1
    payload = json.loads(events[0]["payload_json"])
    assert sorted(payload["ops_override_keys"]) == ["debug_trace", "dry_run"]
    assert payload["override_digest"] is None
    snapshot = _read_snapshot(tmp_path, ops_row["config_snapshot_digest"])
    assert snapshot["l3"]["overrides"] == {}
    assert snapshot["l3"]["override_digest"] is None
    assert "dry_run" not in json.dumps(snapshot)
    assert "debug_trace" not in json.dumps(snapshot)


def test_forbidden_model_key_override_is_config_override_rejected_with_security_audit(tmp_path: Path) -> None:
    """S14-A07 / A08: model_key → CONFIG_OVERRIDE_REJECTED + config.override_denied."""

    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer override-token"}
    with _client(tmp_path) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "deny"},
            ).status_code
            == 201
        )
        denied = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_body(team_uuid, task_uuid, trace_uuid, overrides={"model_key": "evil-model"}),
        )
        assert denied.status_code == 422, denied.text
        body = denied.json()
        assert body["error"]["code"] == "CONFIG_OVERRIDE_REJECTED"

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        tasks = connection.execute("SELECT task_uuid FROM mkb_tasks").fetchall()
        audits = connection.execute(
            "SELECT action,denial_code,payload_json FROM mkb_security_audit_events "
            "WHERE action='config.override_denied'"
        ).fetchall()
        events = connection.execute(
            "SELECT event_type FROM mkb_domain_events WHERE event_type='config.override_applied'"
        ).fetchall()

    assert tasks == []
    assert not events
    assert len(audits) == 1
    assert audits[0]["denial_code"] == "CONFIG_OVERRIDE_REJECTED"
    assert "model_key" in audits[0]["payload_json"]


def test_unknown_override_key_is_config_override_rejected_with_security_audit(tmp_path: Path) -> None:
    """S14-A07: unknown key → CONFIG_OVERRIDE_REJECTED + security audit, zero Task rows."""

    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer override-token"}
    with _client(tmp_path) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "unknown"},
            ).status_code
            == 201
        )
        denied = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_body(team_uuid, task_uuid, trace_uuid, overrides={"not_a_real_knob": 1}),
        )
        assert denied.status_code == 422, denied.text
        assert denied.json()["error"]["code"] == "CONFIG_OVERRIDE_REJECTED"

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        tasks = connection.execute("SELECT task_uuid FROM mkb_tasks").fetchall()
        audits = connection.execute(
            "SELECT action,denial_code,payload_json FROM mkb_security_audit_events "
            "WHERE action='config.override_denied'"
        ).fetchall()

    assert tasks == []
    assert len(audits) == 1
    assert audits[0]["denial_code"] == "CONFIG_OVERRIDE_REJECTED"
    assert "not_a_real_knob" in audits[0]["payload_json"]


def test_over_cap_top_k_is_config_override_rejected(tmp_path: Path) -> None:
    """S14-A10: top_k above product cap (50) rejects with audit, no Task."""

    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer override-token"}
    with _client(tmp_path) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "cap"},
            ).status_code
            == 201
        )
        denied = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_body(team_uuid, task_uuid, trace_uuid, overrides={"top_k": 99}),
        )
        assert denied.status_code == 422, denied.text
        assert denied.json()["error"]["code"] == "CONFIG_OVERRIDE_REJECTED"

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        tasks = connection.execute("SELECT task_uuid FROM mkb_tasks").fetchall()
        audits = connection.execute(
            "SELECT denial_code FROM mkb_security_audit_events WHERE action='config.override_denied'"
        ).fetchall()

    assert tasks == []
    assert audits and audits[0]["denial_code"] == "CONFIG_OVERRIDE_REJECTED"
