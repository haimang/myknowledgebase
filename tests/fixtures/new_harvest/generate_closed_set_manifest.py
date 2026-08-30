"""Generate the NH9 closed-set manifest without rewriting NH1-T07 bytes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.api.models import TaskCreateRequest
from src.contracts.common.ids import stable_digest
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS

MANIFEST_PATH = Path(__file__).with_name("closed_set_manifest.v1.json")

_WORK_COUNTS = {
    1: 9,
    2: 8,
    3: 10,
    4: 8,
    5: 8,
    6: 10,
    7: 10,
    8: 8,
    9: 11,
}

_WINDOWS = [
    "W-NH-CREATE",
    "W-NH-SEL",
    "W-NH-SEAL",
    "W-NH-PROCESS",
    "W-NH-PROM-CAT",
    "W-NH-GC-INGEST",
    "W-NH-FANIN",
    "W-NH-PUB",
    "W-NH-OUTBOX",
]

_FAKE_GREEN = [f"FG-NH-{ordinal:02d}" for ordinal in range(1, 18)]


def work_ids() -> list[str]:
    return [
        f"NH{stage}-{ordinal:02d}"
        for stage, count in _WORK_COUNTS.items()
        for ordinal in range(1, count + 1)
    ]


def nh1_material() -> dict[str, Any]:
    strategy_cells = [definition.model_dump(mode="json") for definition in CLEAN_STRATEGY_DEFINITIONS]
    op_cells = [
        {
            "provider": definition.provider,
            "operation": definition.operation,
            "definition_version": definition.definition_version,
            "definition_digest": definition.definition_digest,
        }
        for definition in REGISTERED_PROVIDER_OPERATIONS
    ]
    request_intents = list(get_args(TaskCreateRequest.model_fields["request_intent"].annotation))
    intent_illegal = [
        {
            "request_intent": intent,
            "illegal_combination": "source_descriptor_on_non_ingest_intent",
            "disposition": "rejected_before_task",
            "http_status": 422,
            "error_code": "task-schema-invalid",
        }
        for intent in request_intents
        if intent != "intake.ingest"
    ]
    material = {
        "strategy_cells": strategy_cells,
        "op_cells": op_cells,
        "intent_illegal": intent_illegal,
    }
    return {**material, "digest": stable_digest(material)}


def build_manifest() -> dict[str, Any]:
    base = nh1_material()
    strategy_cells = list(base["strategy_cells"])  # type: ignore[arg-type]
    op_cells = list(base["op_cells"])  # type: ignore[arg-type]
    legal_cells = [
        {
            "kind": "strategy",
            "strategy_key": cell["strategy_key"],
            "path": "default-root",
            "actual_binding": "sealed",
            "semantic": "s04_six_tuple",
            "query": "namespaced_facet_hit",
            "negative": False,
            "min_layer": "L4",
        }
        for cell in strategy_cells
    ]
    legal_cells.extend(
        {
            "kind": "registered_api",
            "provider": cell["provider"],
            "operation": cell["operation"],
            "path": "default-root",
            "actual_binding": "sealed",
            "semantic": "provider_mapped",
            "query": "namespaced_facet_hit",
            "negative": False,
            "min_layer": "L4",
        }
        for cell in op_cells
    )
    negative_cells = [
        {
            "negative_kind": "empty",
            "query_expected": 0,
            "disposition": "fail_loud",
        },
        {
            "negative_kind": "unknown",
            "query_expected": 0,
            "disposition": "fail_loud",
        },
        {
            "negative_kind": "illegal-intent",
            "query_expected": 0,
            "disposition": "rejected_before_task",
        },
        {
            "negative_kind": "missing-supply",
            "query_expected": 0,
            "disposition": "typed_unavailable",
        },
    ]
    assurance = {
        "work_ids": work_ids(),
        "windows": list(_WINDOWS),
        "fake_green": list(_FAKE_GREEN),
        "legal_cells": legal_cells,
        "negative_cells": negative_cells,
        "experiment": {
            "launch_date": None,
            "scores": None,
            "in_closure_join": False,
        },
    }
    return {
        **base,
        **assurance,
        "assurance_digest": stable_digest(assurance),
    }


def render(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    MANIFEST_PATH.write_text(render(build_manifest()), encoding="utf-8")


if __name__ == "__main__":
    main()
