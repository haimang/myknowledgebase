"""S04/S09 regression: index rebuild is a real generation cutover, not a no-op."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="index-rebuild-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
        persistence_backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, str]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "index-rebuild-e2e",
        "created_at": utc_now(),
    }


def _wait_for_terminal(
    client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]
) -> dict[str, object]:
    deadline = time.monotonic() + 8
    task: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {task}")


def test_scoped_index_rebuild_promotes_generation_without_new_intake_revision(tmp_path: Path) -> None:
    """A successful rebuild must cut over only after a complete new index set.

    This deliberately reads the private substrate after the public Task reaches
    a terminal state.  The API remains opaque; the assertions prove S04/S09's
    durable generation/proof/pointer contract, including the grace retention
    of the old generation.
    """

    database_path = tmp_path / "mkb.sqlite3"
    settings = _settings(tmp_path)
    app = create_app(settings)
    team_uuid = uuid7()
    ingest_task_uuid, ingest_trace_uuid = uuid7(), uuid7()
    headers = {"Authorization": "Bearer index-rebuild-token"}

    with TestClient(app, raise_server_exceptions=True) as client:
        created_team = client.post(
            "/v1/teams",
            headers=headers,
            json={
                "schema_version": "mkb.team.v1",
                "team_uuid": team_uuid,
                "name": "index rebuild regression",
            },
        )
        assert created_team.status_code == 201, created_team.text

        created_ingest = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_task_uuid,
                "trace_uuid": ingest_trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "index-rebuild-document",
                        "content": "A retained document must survive an index generation rebuild.",
                    }
                },
                "audit": _audit(team_uuid, ingest_task_uuid, ingest_trace_uuid),
            },
        )
        assert created_ingest.status_code == 201, created_ingest.text
        assert (
            _wait_for_terminal(
                client,
                team_uuid=team_uuid,
                task_uuid=ingest_task_uuid,
                headers=headers,
            )["status"]
            == "succeeded"
        )

        connection = sqlite3.connect(database_path)
        try:
            item_uuid, revision_uuid = connection.execute(
                "SELECT intake_item_uuid,latest_revision_uuid FROM mkb_intake_items WHERE team_uuid=?",
                (team_uuid,),
            ).fetchone()
            before_pointer = connection.execute(
                "SELECT active_index_generation,pointer_row_revision,last_proof_uuid "
                "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            assert before_pointer is not None
            assert before_pointer[0] == 1
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                    (team_uuid, item_uuid),
                ).fetchone()[0]
                == 1
            )
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
                    "AND index_generation=1 AND deleted_at IS NULL",
                    (team_uuid, item_uuid),
                ).fetchone()[0]
                > 0
            )
        finally:
            connection.close()

        rebuild_task_uuid, rebuild_trace_uuid = uuid7(), uuid7()
        created_rebuild = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": rebuild_task_uuid,
                "trace_uuid": rebuild_trace_uuid,
                "request_intent": "index.rebuild",
                "payload": {"scope": "intake_item", "intake_item_uuid": item_uuid},
                "audit": _audit(team_uuid, rebuild_task_uuid, rebuild_trace_uuid),
            },
        )
        assert created_rebuild.status_code == 201, created_rebuild.text
        terminal = _wait_for_terminal(
            client,
            team_uuid=team_uuid,
            task_uuid=rebuild_task_uuid,
            headers=headers,
        )
        assert terminal["status"] == "succeeded", terminal

        # A promoted generation is not merely a new pointer/proof tuple: it
        # must hydrate through the exact generation artifact and remain a
        # grounded S10 result.
        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "query": "retained document index generation rebuild",
                "return_k": 1,
                "recall_k": 2,
            },
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"][0]["payload_content"] == (
            "A retained document must survive an index generation rebuild."
        )

    connection = sqlite3.connect(database_path)
    try:
        item = connection.execute(
            "SELECT latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone()
        assert item == (revision_uuid, revision_uuid)
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()[0]
            == 1
        )

        pointer = connection.execute(
            "SELECT active_index_generation,pointer_row_revision,last_proof_uuid,lifecycle_state "
            "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone()
        assert pointer is not None
        assert pointer[0] == 2
        assert pointer[1] == before_pointer[1] + 1
        assert pointer[2] != before_pointer[2]
        assert pointer[3] == "active"

        new_generation_count = connection.execute(
            "SELECT COUNT(*) FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
            "AND index_generation=2 AND publication_state='indexed' AND deleted_at IS NULL",
            (team_uuid, item_uuid),
        ).fetchone()[0]
        old_generation_count = connection.execute(
            "SELECT COUNT(*) FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
            "AND index_generation=1 AND deleted_at IS NULL",
            (team_uuid, item_uuid),
        ).fetchone()[0]
        assert new_generation_count > 0
        assert old_generation_count > 0

        proofs = connection.execute(
            "SELECT index_generation,proof_uuid FROM mkb_publication_proofs WHERE team_uuid=? "
            "AND intake_item_uuid=? ORDER BY index_generation",
            (team_uuid, item_uuid),
        ).fetchall()
        assert [proof[0] for proof in proofs] == [1, 2]
        assert proofs[-1][1] == pointer[2]
        process_rows = connection.execute(
            "SELECT process_key,status FROM mkb_processes WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
            (team_uuid, rebuild_task_uuid),
        ).fetchall()
        assert process_rows == [("index.rebuild", "succeeded")]
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("drift", "expected_error"),
    [
        ("item", "INDEX_REBUILD_TARGET_STALE"),
        ("pointer", "INDEX_REBUILD_POINTER_FENCE"),
    ],
)
def test_index_rebuild_stale_fence_fails_without_cutover_and_old_generation_remains_retrievable(
    tmp_path: Path,
    drift: str,
    expected_error: str,
) -> None:
    """A stale source or selection pointer must fail closed before promotion."""

    database_path = tmp_path / "mkb.sqlite3"
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer index-rebuild-token"}
    ingest_task_uuid, ingest_trace_uuid = uuid7(), uuid7()

    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={
                "schema_version": "mkb.team.v1",
                "team_uuid": team_uuid,
                "name": f"index rebuild stale {drift}",
            },
        )
        assert team.status_code == 201, team.text
        ingest = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_task_uuid,
                "trace_uuid": ingest_trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": f"index-rebuild-stale-{drift}",
                        "content": "The old active generation remains grounded after a rejected rebuild.",
                    }
                },
                "audit": _audit(team_uuid, ingest_task_uuid, ingest_trace_uuid),
            },
        )
        assert ingest.status_code == 201, ingest.text
        assert (
            _wait_for_terminal(
                client,
                team_uuid=team_uuid,
                task_uuid=ingest_task_uuid,
                headers=headers,
            )["status"]
            == "succeeded"
        )

        connection = sqlite3.connect(database_path)
        try:
            item_uuid = connection.execute(
                "SELECT intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,)
            ).fetchone()[0]
            before_pointer = connection.execute(
                "SELECT active_index_generation,pointer_row_revision,last_proof_uuid "
                "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            assert before_pointer is not None
        finally:
            connection.close()

        # This seam changes authoritative state after the worker has frozen
        # the source plan but before its staged success callback is accepted.
        # It mirrors a concurrent metadata/publish writer without exposing an
        # unsafe public mutation route solely for a test.
        pipeline = app.state.container.workflow_worker.handler
        original_plan = pipeline._plan_index_rebuild  # type: ignore[attr-defined]

        async def plan_then_drift(frozen_team_uuid: str, scope: object) -> object:
            plans = await original_plan(frozen_team_uuid, scope)
            async with app.state.container.persistence.transaction() as tx:
                if drift == "item":
                    changed = await tx.execute(
                        "UPDATE mkb_intake_items SET row_revision=row_revision+1 "
                        "WHERE team_uuid=? AND intake_item_uuid=?",
                        (team_uuid, item_uuid),
                    )
                else:
                    changed = await tx.execute(
                        "UPDATE mkb_index_active_pointers "
                        "SET pointer_row_revision=pointer_row_revision+1 "
                        "WHERE team_uuid=? AND intake_item_uuid=?",
                        (team_uuid, item_uuid),
                    )
            assert changed.rowcount == 1
            return plans

        pipeline._plan_index_rebuild = plan_then_drift  # type: ignore[attr-defined]
        rebuild_task_uuid, rebuild_trace_uuid = uuid7(), uuid7()
        rebuild = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": rebuild_task_uuid,
                "trace_uuid": rebuild_trace_uuid,
                "request_intent": "index.rebuild",
                "payload": {"scope": "intake_item", "intake_item_uuid": item_uuid},
                "audit": _audit(team_uuid, rebuild_task_uuid, rebuild_trace_uuid),
            },
        )
        assert rebuild.status_code == 201, rebuild.text
        terminal = _wait_for_terminal(
            client,
            team_uuid=team_uuid,
            task_uuid=rebuild_task_uuid,
            headers=headers,
        )
        assert terminal["status"] == "failed", terminal
        assert terminal["error"] is not None
        assert terminal["error"]["code"] == expected_error

        # The old pointer remains queryable even though the rejected Process
        # left staged object bytes behind for GC.  No failed candidate is
        # allowed into S10's active predicate.
        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "query": "old active generation grounded",
                "return_k": 1,
                "recall_k": 2,
            },
        )
        assert search.status_code == 200, search.text
        old_text = "The old active generation remains grounded after a rejected rebuild."
        midpoint = max(1, len(old_text) // 2)
        old_layers = {
            old_text,
            old_text[:midpoint],
            old_text[midpoint:],
            old_text[:midpoint].rstrip(),
            old_text[midpoint:].lstrip(),
        }
        payload = search.json()["results"][0]["payload_content"]
        assert payload in old_layers or (payload and payload in old_text)

    connection = sqlite3.connect(database_path)
    try:
        pointer = connection.execute(
            "SELECT active_index_generation,pointer_row_revision,last_proof_uuid "
            "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone()
        assert pointer is not None
        assert pointer[0] == before_pointer[0] == 1
        assert pointer[2] == before_pointer[2]
        expected_pointer_revision = before_pointer[1] + (1 if drift == "pointer" else 0)
        assert pointer[1] == expected_pointer_revision
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
                "AND index_generation=2",
                (team_uuid, item_uuid),
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM mkb_publication_proofs WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()[0]
            == 1
        )
        processes = connection.execute(
            "SELECT process_key,status,error_code FROM mkb_processes "
            "WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
            (team_uuid, rebuild_task_uuid),
        ).fetchall()
        assert processes == [("index.rebuild", "failed", expected_error)]
    finally:
        connection.close()
