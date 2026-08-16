"""Prepare the Turso copy of the R2 database for later R3 (after NS4 closure)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from src.persistence.factory import build_persistence
from src.runtime.config import Settings
from src.services.registry import RegistryService

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
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


async def main() -> int:
    os.chdir(ROOT)
    _load_dotenv()
    db = RUN / "runtime" / "mkb.turso.db"
    if not db.exists():
        print("FAIL no runtime/mkb.turso.db — run scripts/ns4_migrate_q_a3.py first")
        return 1
    settings = Settings(
        internal_token="dev-0815",
        persistence_backend="turso",
        concurrent_writes_required=True,
        native_vector_required=False,
        live_inference=True,
        ns1_cli_mode="subprocess",
        inference_probe_enabled=False,
        database_path=db,
        object_root=RUN / "runtime" / "objects",
    )
    persistence = build_persistence(
        settings.resolved_database_path,
        ROOT / "src/persistence/migrations",
        backend="turso",
        concurrent_writes_required=True,
        native_vector_required=False,
    )
    registry = RegistryService(persistence, ROOT / "data/prompts")
    try:
        await persistence.migrate()
        await registry.bootstrap()
        g1 = await registry.register_prompt(
            prompt_id="promptB.documentation.g1",
            prompt_version="v3",
            relative_path="json/promptB.documentation.g1.v3.md",
            role="json",
            granularity_set=(0, 1),
        )
        resolved = await registry.resolve_prompt("promptB.documentation.g1")
        async with persistence.transaction() as tx:
            items = await tx.fetchall(
                "SELECT normalized_external_key, lifecycle_state FROM mkb_intake_items ORDER BY created_at"
            )
            tasks = await tx.fetchall("SELECT task_uuid, status FROM mkb_tasks")
            g1_rows = await tx.fetchall(
                "SELECT prompt_version, status, git_relative_path FROM mkb_prompt_hash_pointers "
                "WHERE prompt_id='promptB.documentation.g1' ORDER BY prompt_version"
            )
    finally:
        await persistence.close()
    serving = [row for row in items if "non-interactive-agentic-pipeline-qwen" in str(row["normalized_external_key"])]
    report = {
        "g1_registered": {"version": g1.prompt_version, "path": g1.relative_path, "sha256": g1.content_sha256},
        "g1_resolved": {"version": resolved.prompt_version, "path": resolved.relative_path},
        "g1_rows": [
            {"version": row["prompt_version"], "status": row["status"], "path": row["git_relative_path"]}
            for row in g1_rows
        ],
        "tasks": [{"task_uuid": row["task_uuid"], "status": row["status"]} for row in tasks],
        "q_a3_present": bool(serving),
        "q_a3_items": [{"key": row["normalized_external_key"], "lifecycle": row["lifecycle_state"]} for row in serving],
    }
    dest = RUN / "results" / "r3_prepare.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if resolved.prompt_version != "v3" or not serving:
        print("FAIL catalog or Q-A3 serving missing")
        return 1
    print("READY catalog v3 on Turso copy; Q-A3 serving preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
