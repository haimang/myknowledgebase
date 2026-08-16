"""MKB-0815-R2 ingest runner. Reads sealed subjects only."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings

RUN_ROOT = Path(__file__).resolve().parent
SUBJECTS = RUN_ROOT / "subjects"
RESULTS = RUN_ROOT / "results"
META_PATH = RESULTS / "_meta.json"
SAMPLES = {
    "A5": {
        "path": "docs/closure/new-start/NS3-megafile-governance-closure.md",
        "external_key": "docs-closure-NS3-megafile-governance-closure",
        "flavor": "closure",
        "granularity": "g1",
        "timeout": 900,
    },
    "A5g2": {
        "path": "docs/closure/new-start/NS3-megafile-governance-closure.md",
        "external_key": "docs-closure-NS3-megafile-governance-closure-g2",
        "flavor": "closure",
        "granularity": "g2",
        "timeout": 900,
    },
    "A3": {
        "path": "docs/eval/new-start/non-interactive-agentic-pipeline.md",
        "external_key": "docs-eval-non-interactive-agentic-pipeline",
        "flavor": "eval",
        "granularity": "g1",
        "timeout": 1800,
    },
    "A6": {
        "path": "docs/code-review/new-start/NS2-reviewed-by-grok.md",
        "external_key": "docs-review-NS2-reviewed-by-grok",
        "flavor": "code-review",
        "granularity": "g1",
        "timeout": 1800,
    },
    "A2": {
        "path": "docs/eval/new-start/pre-NS1-qna.md",
        "external_key": "docs-eval-pre-NS1-qna",
        "flavor": "qna",
        "granularity": "g1",
        "timeout": 3600,
    },
    "A1": {
        "path": "docs/baseline/spec-glossary.md",
        "external_key": "docs-baseline-spec-glossary",
        "flavor": None,
        "granularity": "g1",
        "timeout": 3600,
    },
    "A4": {
        "path": "docs/plan/new-start/NS3-megafile-governance.md",
        "external_key": "docs-plan-NS3-megafile-governance",
        "flavor": "plan",
        "granularity": "g1",
        "timeout": 3600,
    },
}
LANES = {
    "N": {"priority": "high", "compression_channel": "non-interactive", "suffix": ""},
    "Q": {"priority": "normal", "compression_channel": "local-inference", "suffix": "-qwen"},
}


def parse_cell(cell_id: str) -> tuple[str, str]:
    lane, sample_id = cell_id.split("-", 1)
    if lane not in LANES or sample_id not in SAMPLES:
        raise KeyError(cell_id)
    return lane, sample_id


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"MKB_DATABASE_PATH", "MKB_OBJECT_ROOT", "MKB_DATA_DIR", "MKB_LIVE_INFERENCE"}:
            continue
        os.environ.setdefault(key, value)


def _settings() -> Settings:
    (RUN_ROOT / "runtime").mkdir(parents=True, exist_ok=True)
    return Settings(
        internal_token="dev-0815",
        persistence_backend="turso",
        concurrent_writes_required=True,
        native_vector_required=False,
        live_inference=True,
        ns1_cli_mode="subprocess",
        ns1_cli_executable="claude",
        inference_probe_enabled=False,
        database_path=RUN_ROOT / "runtime" / "mkb.turso.db",
        object_root=RUN_ROOT / "runtime" / "objects",
        inference_generate_timeout_seconds=900,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=10_000,
    )


def load_or_create_team_uuid() -> str:
    if META_PATH.exists():
        data = json.loads(META_PATH.read_text(encoding="utf-8"))
        team = data.get("team_uuid")
        if isinstance(team, str) and team:
            return team
    return uuid7()


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str], timeout: float) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    task: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        response.raise_for_status()
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(2)
    raise TimeoutError(f"task did not become terminal: {task}")


def _append_jsonl(row: dict[str, object]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "runs.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _process_steps(database_path: Path, team_uuid: str, task_uuid: str) -> list[dict[str, object]]:
    """Read process rows through the Turso driver. Stock sqlite3 cannot open this file after pyturso writes."""

    import turso

    columns = (
        "step_key",
        "process_key",
        "status",
        "dispatch_pool",
        "error_code",
        "error_message",
        "payload_extra",
    )
    connection = turso.connect(str(database_path))
    try:
        rows = connection.execute(
            "SELECT step_key, process_key, status, dispatch_pool, error_code, error_message, payload_extra "
            "FROM mkb_processes WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
            (team_uuid, task_uuid),
        ).fetchall()
    finally:
        connection.close()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def ingest_cell(cell_id: str, *, team_uuid: str | None = None, key_suffix: str = "") -> dict[str, object]:
    lane, sample_id = parse_cell(cell_id)
    sample = SAMPLES[sample_id]
    lane_cfg = LANES[lane]
    content = (SUBJECTS / sample["path"]).read_text(encoding="utf-8")
    settings = _settings()
    token = settings.active_tokens[0]
    headers = {"Authorization": f"Bearer {token}"}
    team_uuid = team_uuid or load_or_create_team_uuid()
    task_uuid = uuid7()
    trace_uuid = uuid7()
    payload: dict[str, object] = {
        "domain": "documentation",
        "granularity": sample["granularity"],
        "compression_channel": lane_cfg["compression_channel"],
        "source": {
            "source_kind": "inline_payload",
            "external_key": sample["external_key"] + lane_cfg["suffix"] + key_suffix,
            "media_type": "text/plain",
            "content": content,
        },
    }
    if sample["flavor"]:
        payload["flavor"] = sample["flavor"]
    started = time.monotonic()
    started_at = utc_now()
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=True) as client:
        ready = client.get("/ready")
        print("ready", ready.status_code, ready.json())
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "mkb-dogfood-0815-r2"},
        )
        if team.status_code not in {200, 201, 409}:
            print("team", team.status_code, team.text[:400])
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
                "priority": lane_cfg["priority"],
                "payload": payload,
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "MKB-0815-R2",
                    "created_at": utc_now(),
                },
            },
        )
        print("create", created.status_code, created.text[:500])
        created.raise_for_status()
        terminal = _wait(client, team_uuid, task_uuid, headers, float(sample["timeout"]))
    wall_ms = int((time.monotonic() - started) * 1000)
    steps = _process_steps(settings.resolved_database_path, team_uuid, task_uuid)
    generate_steps = [step for step in steps if step.get("step_key") in {"transcribe_markdown", "structurize", "construct"}]
    generate_pools = sorted(
        {str(step.get("dispatch_pool") or "") for step in generate_steps if step.get("dispatch_pool")}
    )
    kernel_step = next((step for step in reversed(steps) if step.get("error_code")), None)
    extras = [
        step.get("payload_extra")
        for step in steps
        if step.get("payload_extra") not in {None, "", "{}"}
    ]
    row = {
        "experiment_run_id": "MKB-0815-R2",
        "cell_id": cell_id,
        "sample_id": sample_id,
        "lane": lane,
        "external_key": payload["source"]["external_key"],
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "started_at": started_at,
        "wall_ms": wall_ms,
        "flavor": sample["flavor"],
        "granularity": sample["granularity"],
        "priority": lane_cfg["priority"],
        "compression_channel": lane_cfg["compression_channel"],
        "cli_mode": "subprocess",
        "live_inference": True,
        "task_status": terminal.get("status"),
        "error_code": terminal.get("error_code") or (None if kernel_step is None else kernel_step.get("error_code")),
        "error_message": terminal.get("error_message")
        or (None if kernel_step is None else kernel_step.get("error_message")),
        "kernel_code": None if kernel_step is None else kernel_step.get("error_code"),
        "failed_step": None if kernel_step is None else kernel_step.get("step_key"),
        "steps": steps,
        "dispatch_pools": ",".join(
            str(step.get("dispatch_pool") or "")
            for step in steps
            if step.get("step_key") in {"transcribe_markdown", "structurize", "construct", "vectorize"}
        ),
        "generate_pools": generate_pools,
        "lane_contaminated": lane == "Q" and any(pool == "non-interactive" for pool in generate_pools),
        "process_payload_extra": extras,
        "key_suffix": key_suffix,
    }
    _append_jsonl(row)
    print(
        "terminal",
        json.dumps(
            {
                "cell_id": cell_id,
                "task_status": row["task_status"],
                "error_code": row["error_code"],
                "wall_ms": wall_ms,
                "dispatch_pools": row["dispatch_pools"],
            },
            ensure_ascii=False,
        ),
    )
    for step in steps:
        print(" step", step)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cell_id")
    parser.add_argument("--team-uuid")
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()
    _load_dotenv()
    ingest_cell(args.cell_id, team_uuid=args.team_uuid, key_suffix=args.suffix)


if __name__ == "__main__":
    main()
