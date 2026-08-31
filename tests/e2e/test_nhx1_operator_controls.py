"""NHX1-T24: operator reads are redacted and controls use receipts/fences."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def test_operator_dead_outbox_requeue_is_team_scoped_and_idempotent(tmp_path: Path) -> None:
    token = "nhx1-operator-token"
    team_uuid = uuid7()
    outbox_id = uuid7()
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "operator.sqlite3",
            object_root=tmp_path / "objects",
            persistence_backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
            http_trusted_hosts="testserver",
            rate_limit_ip_per_min=10_000,
            rate_limit_token_per_min=10_000,
        )
    )
    headers = {"Authorization": f"Bearer {token}", "host": "testserver"}
    with TestClient(app, raise_server_exceptions=True) as client:
        created = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "operator"},
        )
        assert created.status_code == 201, created.text

        async def seed() -> None:
            payload = {"execution_uuid": uuid7()}
            payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            async with app.state.container.persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_outbox(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,"
                    "attempts,available_at,created_at,updated_at,owner_kind,owner_uuid,owner_generation,delivery_generation,"
                    "criticality,attempt_budget,dead_error_code) VALUES (?,?,?,?,?,?,'dead',8,?,?,?,?,?,1,1,'critical',8,?)",
                    (
                        outbox_id,
                        team_uuid,
                        "wake_execution",
                        payload_json,
                        stable_digest(payload),
                        "operator-dead",
                        utc_now(),
                        utc_now(),
                        utc_now(),
                        "execution",
                        payload["execution_uuid"],
                        "OUTBOX_WAKE_DEAD",
                    ),
                )

        client.portal.call(seed)
        async def requeue_once() -> dict:
            return await app.state.container.operator_control.requeue_outbox(
                team_uuid,
                outbox_id,
                expected_generation=1,
                idempotency_key="operator-once",
            )

        receipt = client.portal.call(requeue_once)
        assert receipt["disposition"] == "applied"
        assert receipt["decided_at"]
        replay = client.portal.call(requeue_once)
        assert replay["disposition"] == "replayed"
        route_result = client.post(
            f"/internal/teams/{team_uuid}/outbox/{outbox_id}:requeue",
            headers=headers,
            json={"expected_generation": 2, "idempotency_key": "route-denied"},
        )
        assert route_result.status_code == 403
        bad = client.post(
            f"/internal/teams/{uuid7()}/outbox/{outbox_id}:requeue",
            headers=headers,
            json={"expected_generation": 1, "idempotency_key": "other-team"},
        )
        assert bad.status_code in {403, 404}


def test_operator_unknown_process_does_not_echo_payload(tmp_path: Path) -> None:
    token = "nhx1-operator-read-token"
    team_uuid = uuid7()
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "operator-read.sqlite3",
            object_root=tmp_path / "objects",
            persistence_backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
            http_trusted_hosts="testserver",
        )
    )
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.get(
            f"/internal/teams/{team_uuid}/processes/{uuid7()}",
            headers={"Authorization": f"Bearer {token}", "host": "testserver"},
        )
        assert response.status_code == 403
        assert "payload" not in response.text.casefold()
