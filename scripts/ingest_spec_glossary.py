"""Ingest docs/baseline/spec-glossary.md through intake to dual-channel vectors."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings
from src.services.registry import SPARK_VL_EMBED_MODEL_KEY

GLOSSARY = Path("docs/baseline/spec-glossary.md")
SOURCE = "spec-glossary-v1"


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 180
    task: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        response.raise_for_status()
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.2)
    raise TimeoutError(f"task did not become terminal: {task}")


def _object_bytes(object_root: Path, team_uuid: str, logical_handle: str) -> bytes:
    digest = logical_handle.rsplit(":", maxsplit=1)[-1]
    return (object_root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest).read_bytes()


def main() -> None:
    settings = Settings(
        persistence_backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
        live_inference=True,
        ns1_cli_mode="stub",
        inference_probe_enabled=False,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=10_000,
    )
    token = settings.active_tokens[0]
    headers = {"Authorization": f"Bearer {token}"}
    content = GLOSSARY.read_text(encoding="utf-8")
    team_uuid = uuid7()
    task_uuid = uuid7()
    trace_uuid = uuid7()
    app = create_app(settings)
    print("settings", {
        "db": str(settings.resolved_database_path),
        "objects": str(settings.resolved_object_root),
        "live": settings.live_inference,
        "cli": settings.ns1_cli_mode,
        "base_url": settings.inference_vllm_base_url,
        "token": settings.inference_vllm_token is not None,
    })

    with TestClient(app, raise_server_exceptions=True) as client:
        ready = client.get("/ready")
        print("ready", ready.status_code, ready.json())
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "spec-glossary-live"},
        )
        print("team", team.status_code, team.text[:300])
        team.raise_for_status()
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "domain": "documentation",
                    "granularity": "g1",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": SOURCE,
                        "media_type": "text/plain",
                        "content": content,
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "live-glossary-ingest",
                    "created_at": utc_now(),
                },
            },
        )
        print("create", created.status_code, created.text[:500])
        created.raise_for_status()
        terminal = _wait(client, team_uuid, task_uuid, headers)
        print("terminal", json.dumps(terminal, ensure_ascii=False)[:800])

    db = settings.resolved_database_path
    object_root = settings.resolved_object_root
    with sqlite3.connect(db) as connection:
        connection.row_factory = sqlite3.Row
        steps = list(
            connection.execute(
                "SELECT step_key, status, error_code FROM mkb_processes "
                "WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
                (team_uuid, task_uuid),
            )
        )
        print("steps:")
        for row in steps:
            print(" ", dict(row))
        artifacts = list(
            connection.execute(
                "SELECT artifact_type, logical_handle, size_bytes FROM mkb_generation_artifacts "
                "WHERE team_uuid=? AND task_uuid=? ORDER BY artifact_type",
                (team_uuid, task_uuid),
            )
        )
        print("artifacts:")
        for row in artifacts:
            print(" ", dict(row))
        vectors = list(
            connection.execute(
                "SELECT channel, block_or_unit_id, dimension, embedding_model_key, publication_state, "
                "length(embedding) AS blob_bytes FROM mkb_vector_records "
                "WHERE team_uuid=? ORDER BY channel, block_or_unit_id",
                (team_uuid,),
            )
        )
        print("vectors:")
        for row in vectors:
            print(" ", dict(row))
        namespaces = list(
            connection.execute(
                "SELECT namespace_key, embedding_model_key, dimension, adapter_kind FROM mkb_vector_namespaces "
                "WHERE team_uuid=?",
                (team_uuid,),
            )
        )
        print("namespaces:")
        for row in namespaces:
            print(" ", dict(row))

        by_type = {row["artifact_type"]: row["logical_handle"] for row in artifacts}
        for name in (
            "retrieval_block_projection",
            "dual_channel_projection",
            "construction_document",
            "structure_document",
        ):
            handle = by_type.get(name)
            if not handle:
                print("missing artifact", name)
                continue
            payload = json.loads(_object_bytes(object_root, team_uuid, handle))
            if name == "retrieval_block_projection":
                blocks = payload.get("blocks") or payload.get("projection", {}).get("blocks")
                if blocks is None and isinstance(payload.get("blocks"), list):
                    blocks = payload["blocks"]
                print("projection_keys", list(payload))
                if isinstance(payload.get("blocks"), list):
                    print(
                        "projection",
                        {
                            "n": len(payload["blocks"]),
                            "granularities": sorted({block.get("granularity") for block in payload["blocks"]}),
                            "original_lens": [len(block.get("original") or "") for block in payload["blocks"]],
                        },
                    )
            elif name == "dual_channel_projection":
                print("dual_keys", list(payload))
                units = payload.get("units") or payload.get("blocks") or []
                if isinstance(units, list):
                    print(
                        "dual",
                        {
                            "n": len(units),
                            "channels": sorted({unit.get("channel") for unit in units if isinstance(unit, dict)}),
                            "granularities": sorted(
                                {unit.get("granularity") for unit in units if isinstance(unit, dict)}
                            ),
                        },
                    )
                    print("dual_sample", json.dumps(units[:2], ensure_ascii=False)[:600])
            else:
                print(name, "keys", list(payload)[:12], "bytes", len(json.dumps(payload)))

    if terminal.get("status") != "succeeded":
        raise SystemExit(f"ingest failed: {terminal}")
    if not vectors:
        raise SystemExit("no vector rows")
    dims = {row["dimension"] for row in vectors}
    models = {row["embedding_model_key"] for row in vectors}
    channels = {row["channel"] for row in vectors}
    print(
        "summary",
        {
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "vector_count": len(vectors),
            "dims": sorted(dims),
            "models": sorted(models),
            "channels": sorted(channels),
            "expected_model": SPARK_VL_EMBED_MODEL_KEY,
        },
    )


if __name__ == "__main__":
    main()
