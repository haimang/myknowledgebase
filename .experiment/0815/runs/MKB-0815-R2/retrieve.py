"""Run R2 gold retrieval queries against published documents."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.runtime.config import Settings

RUN = Path(__file__).resolve().parent
QUERIES = [
    ("Q-343", "T-O-343 B 交卷合同是什么"),
    ("Q-352", "FullDocument 向量走哪条通道"),
    ("Q-MIXIN", "为什么 NS3 不去 mixin"),
    ("Q-V5R", "NS1-V5.r 后延了什么"),
    ("Q-POOL", "NS2 三池是什么"),
    ("Q-GLOSS", "ProcessCapabilityManifest 是什么"),
]


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


def main() -> None:
    _load_dotenv()
    meta = json.loads((RUN / "results" / "_meta.json").read_text(encoding="utf-8"))
    team = meta["team_uuid"]
    settings = Settings(
        internal_token="dev-0815",
        persistence_backend="turso",
        concurrent_writes_required=True,
        native_vector_required=False,
        live_inference=True,
        ns1_cli_mode="subprocess",
        inference_probe_enabled=False,
        database_path=RUN / "runtime" / "mkb.turso.db",
        object_root=RUN / "runtime" / "objects",
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=10_000,
    )
    dest = RUN / "inspect" / "retrieval"
    dest.mkdir(parents=True, exist_ok=True)
    token = settings.active_tokens[0]
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=True) as client:
        for qid, query in QUERIES:
            body = {
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team,
                "query": query,
                "return_k": 5,
                "recall_k": 20,
                "include_pack": True,
            }
            (dest / f"{qid}.request.json").write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
            response = client.post(f"/v1/teams/{team}/retrieval:search", headers=headers, json=body)
            payload = {"status_code": response.status_code, "body": response.json()}
            (dest / f"{qid}.response.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"
            )
            hits = []
            if response.status_code == 200:
                for hit in (payload["body"].get("results") or [])[:5]:
                    hits.append(
                        {
                            "score": hit.get("score"),
                            "channel": hit.get("channel"),
                            "granularity": hit.get("granularity"),
                            "block": hit.get("block_or_unit_id") or hit.get("unit_id"),
                            "traceback": hit.get("traceback_status"),
                            "payload_head": str(hit.get("payload_content") or hit.get("payload") or "")[:180],
                        }
                    )
            print(qid, response.status_code, hits[:2])


if __name__ == "__main__":
    main()
