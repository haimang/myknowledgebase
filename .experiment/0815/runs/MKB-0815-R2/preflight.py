"""MKB-0815-R2 preflight. Exit 0 only when every gate passes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
R1 = RUN.parent / "MKB-0815-R1"
ROOT = RUN.parents[3]
# MKB-0815-R2 -> runs -> 0815 -> .experiment -> repo


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


def _check(name: str, ok: bool, detail: str) -> dict[str, object]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def gate_r1_sealed() -> dict[str, object]:
    conclusions = R1 / "evidence" / "CONCLUSIONS.md5"
    seal = json.loads((R1 / "evidence" / "SEAL.json").read_text(encoding="utf-8"))
    proc = subprocess.run(["md5sum", "-c", "evidence/CONCLUSIONS.md5"], cwd=R1, capture_output=True, text=True)
    ok = proc.returncode == 0 and seal.get("status") == "sealed" and seal.get("conclusions", {}).get("token") == "conditional-ready"
    return _check("r1_sealed", ok, proc.stdout.strip() if ok else (proc.stderr or proc.stdout or str(seal.get("status"))))


def gate_r1_subjects() -> dict[str, object]:
    proc = subprocess.run(
        ["md5sum", "-c", "../evidence/SUBJECTS.md5"],
        cwd=R1 / "subjects",
        capture_output=True,
        text=True,
    )
    return _check("r1_subjects_intact", proc.returncode == 0, "ok" if proc.returncode == 0 else proc.stderr)


def gate_r2_subjects() -> dict[str, object]:
    manifest = RUN / "subjects" / "manifest.json"
    if not manifest.exists():
        return _check("r2_subjects_sealed", False, "subjects/manifest.json missing")
    proc = subprocess.run(
        ["md5sum", "-c", "../evidence/SUBJECTS.md5"],
        cwd=RUN / "subjects",
        capture_output=True,
        text=True,
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    needed = {
        "docs/closure/new-start/NS3-megafile-governance-closure.md",
        "data/prompts/json/promptB.documentation.g1.v2.md",
        "data/prompts/summarizer/promptC.documentation.default.v2.md",
    }
    have = {row["path"] for row in data.get("subjects", [])}
    ok = proc.returncode == 0 and needed <= have
    return _check("r2_subjects_sealed", ok, "ok" if ok else f"md5={proc.returncode} missing={sorted(needed - have)}")


def gate_v2_contract() -> dict[str, object]:
    paths = [
        ROOT / "data/prompts/json/promptB.documentation.g1.v2.md",
        ROOT / "data/prompts/json/promptB.documentation.g1.v3.md",
        ROOT / "data/prompts/json/promptB.documentation.g2.v2.md",
        ROOT / "data/prompts/json/promptB.documentation.default.v2.md",
        ROOT / "data/prompts/summarizer/promptC.documentation.default.v2.md",
    ]
    problems: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "MKB" in text:
            problems.append(f"{path.name}: contains MKB")
        if path.name.startswith("promptB") and "mkb.b-json-material.v1" not in text:
            problems.append(f"{path.name}: missing material schema")
        if "semantic_block" in text or "semantic_understanding" in text:
            problems.append(f"{path.name}: legacy dialect")
        if "正例" not in text or "反例" not in text:
            problems.append(f"{path.name}: missing few-shot sections")
        if "步骤 1" not in text or "步骤 3" not in text:
            problems.append(f"{path.name}: missing numbered 步骤")
        if path.name.endswith("g1.v3.md") and "出现 granularity=2 则整包失败" not in text:
            problems.append(f"{path.name}: missing g1 closed-set sentence")
        if path.name.startswith("promptC") and "original_content" not in text:
            problems.append(f"{path.name}: C must mention original_content")
    return _check("v2_prompt_contract", not problems, "ok" if not problems else "; ".join(problems))


def gate_catalog_v2() -> dict[str, object]:
    sys.path.insert(0, str(ROOT))
    from src.persistence.factory import build_persistence
    from src.services.registry import RegistryService

    async def _run() -> tuple[bool, str]:
        db = RUN / "runtime" / "_preflight_catalog.turso.db"
        db.unlink(missing_ok=True)
        persistence = build_persistence(
            db,
            ROOT / "src/persistence/migrations",
            backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
        )
        registry = RegistryService(persistence, ROOT / "data/prompts")
        try:
            await persistence.migrate()
            await registry.bootstrap()
            g1 = await registry.resolve_prompt("promptB.documentation.g1")
            c = await registry.resolve_prompt("promptC.documentation.default")
            ok = g1.prompt_version == "v3" and c.prompt_version == "v2"
            return ok, f"g1={g1.prompt_version} path={g1.relative_path}; C={c.prompt_version}"
        finally:
            await persistence.close()
            db.unlink(missing_ok=True)

    ok, detail = asyncio.run(_run())
    return _check("catalog_resolves_v2", ok, detail)


def gate_unit_tests() -> dict[str, object]:
    proc = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "tests/unit/test_claude_cli_port.py",
            "tests/unit/test_ns1_prompt_bodies.py",
            "tests/unit/test_ns1_prompt_catalog.py",
            "tests/unit/test_ns1_api_workflow.py",
            "tests/unit/test_compression_channel.py",
            "tests/unit/test_dispatch_generation.py",
            "tests/unit/test_structure_reject_histogram.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or proc.stderr or "")[-400:]
    return _check("unit_gates", proc.returncode == 0, tail.replace("\n", " "))


def gate_claude_ping() -> dict[str, object]:
    proc = subprocess.run(
        [
            "claude",
            "--bare",
            "-p",
            "Reply with exactly this token and nothing else: PING_OK",
            "--max-turns",
            "1",
            "--tools",
            "",
            "--effort",
            "low",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    ok = proc.returncode == 0 and "PING_OK" in (proc.stdout or "")
    return _check("claude_ni_ping", ok, (proc.stdout or proc.stderr or "")[:200])


def gate_cli_schema_strip() -> dict[str, object]:
    sys.path.insert(0, str(ROOT))
    from src.runtime.inference.claude_cli import ClaudeCliRequest, build_claude_argv

    argv = build_claude_argv(
        ClaudeCliRequest(
            user_prompt="material",
            system_prompt_file="data/prompts/json/prompt.md",
            json_schema={
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "mkb://schemas/lsrag.layered_content.v1",
                "type": "object",
            },
        )
    )
    payload = json.loads(argv[argv.index("--json-schema") + 1])
    ok = "$schema" not in payload and "$id" not in payload and payload.get("type") == "object"
    return _check("cli_schema_strip", ok, json.dumps(payload, ensure_ascii=False))


def gate_markdown_flavor() -> dict[str, object]:
    sys.path.insert(0, str(ROOT))
    from src.runtime.workflow.runtime_materialize import _markdown_id_from_domain_flavor

    got = _markdown_id_from_domain_flavor({"domain": "documentation", "flavor": "closure"})
    ok = got == "promptB.documentation.closure"
    return _check("markdown_flavor_route", ok, str(got))


def _vllm() -> tuple[str, str | None]:
    url = os.environ.get("MKB_INFERENCE_VLLM_BASE_URL") or "http://127.0.0.1:668"
    token = os.environ.get("MKB_INFERENCE_VLLM_TOKEN") or os.environ.get("MKB_INFERENCE_VLLM_token")
    return url.rstrip("/"), token


def gate_vllm_models() -> dict[str, object]:
    import urllib.request

    url, token = _vllm()
    req = urllib.request.Request(url + "/v1/models")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        ids = {item.get("id") for item in data.get("data", [])}
    except Exception as exc:
        return _check("vllm_models", False, f"{url} {type(exc).__name__}: {exc}")
    need = {
        "LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4",
        "unsloth/Qwen3.8-27B-NVFP4",
    }
    ok = need <= ids
    return _check("vllm_models", ok, f"url={url} have={sorted(ids)}")


def gate_qwen_generate() -> dict[str, object]:
    import urllib.request

    url, token = _vllm()
    payload = {
        "model": "unsloth/Qwen3.8-27B-NVFP4",
        "messages": [{"role": "user", "content": "Reply with exactly PING_OK and nothing else."}],
        "max_tokens": 16,
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"].get("content") or ""
    except Exception as exc:
        return _check("qwen_generate_smoke", False, f"{type(exc).__name__}: {exc}")
    ok = "PING_OK" in text
    return _check("qwen_generate_smoke", ok, text[:160].replace("\n", " "))


def gate_embed_layer_a() -> dict[str, object]:
    import urllib.request

    url, token = _vllm()
    payload = {
        "model": "LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4",
        "input": ["preflight layer a"],
        "dimensions": 1024,
    }
    req = urllib.request.Request(
        url + "/v1/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        vec = data["data"][0]["embedding"]
        model = data.get("model")
    except Exception as exc:
        return _check("embed_smoke", False, f"{type(exc).__name__}: {exc}")
    ok = isinstance(vec, list) and len(vec) == 1024
    return _check("embed_smoke", ok, f"model={model} dim={len(vec) if isinstance(vec, list) else None}")


def gate_runtime_dir() -> dict[str, object]:
    import sqlite3

    db = RUN / "runtime" / "mkb.turso.db"
    archive = RUN / "runtime" / "mkb.db"
    (RUN / "runtime").mkdir(parents=True, exist_ok=True)
    (RUN / "results").mkdir(parents=True, exist_ok=True)
    if not db.exists() and archive.exists():
        return _check("r2_db_clean", True, "archive-only; run scripts/ns4_migrate_q_a3.py")
    if not db.exists():
        return _check("r2_db_clean", True, "absent")
    try:
        with sqlite3.connect(db) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM mkb_intake_items WHERE lifecycle_state IN ('active','published','serving')"
            ).fetchone()
            serving = int(row[0] if row else 0)
    except sqlite3.Error as exc:
        return _check("r2_db_clean", False, f"existing db unreadable: {exc}")
    if serving > 0:
        return _check("r2_db_clean", True, f"serving-preserved n={serving}")
    return _check("r2_db_clean", False, "mkb.db exists without serving rows — rebuild or inspect before launch")


def main() -> int:
    if not (ROOT / "pyproject.toml").is_file():
        raise SystemExit(f"preflight ROOT is not the repo: {ROOT}")
    os.chdir(ROOT)
    _load_dotenv()
    gates = [
        gate_r1_sealed,
        gate_r1_subjects,
        gate_r2_subjects,
        gate_v2_contract,
        gate_catalog_v2,
        gate_unit_tests,
        gate_cli_schema_strip,
        gate_markdown_flavor,
        gate_runtime_dir,
        gate_vllm_models,
        gate_embed_layer_a,
        gate_qwen_generate,
        gate_claude_ping,
    ]
    results = [gate() for gate in gates]
    report = {
        "run_id": "MKB-0815-R2",
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "passed": all(item["status"] == "pass" for item in results),
        "gates": results,
    }
    (RUN / "results").mkdir(parents=True, exist_ok=True)
    (RUN / "results" / "preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for item in results:
        mark = "PASS" if item["status"] == "pass" else "FAIL"
        print(f"{mark:4} {item['name']}: {item['detail'][:200]}")
    print("READY" if report["passed"] else "NOT READY")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
