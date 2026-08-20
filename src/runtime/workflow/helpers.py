"""Shared pure helpers for workflow runtime mixins."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.runtime.models import ProcessOutcome
from src.contracts.workflow.models import (
    WorkflowDefinition,
)


def canonical_outcome_digest(outcome: ProcessOutcome) -> str:
    """Return the canonical digest a stage must put in ``outcome_digest``.

    The helper makes outcome integrity testable without exposing a mutable JSON
    escape hatch.  A handler can construct an outcome with a temporary 64-hex
    value and replace that value with this result before returning it.
    """

    material = outcome.model_dump(mode="json")
    material.pop("outcome_digest", None)
    return stable_digest(material)


def _compiled_workflow_digest(definition: WorkflowDefinition) -> str:
    """Match the registry compiler digest for an immutable static plan.

    The registry is the durable binding authority; this calculation only
    selects a reviewed in-process interpreter for an already-bound revision.
    Keeping the exact compiler envelope here ensures an old execution cannot
    silently fall through to the active definition merely because its step
    names happen to overlap.
    """

    canonical = definition.model_dump(mode="json")
    return stable_digest(
        {
            "compiler": "mkb.workflow-compiler.v1",
            "definition": canonical,
            "capability_registry": sorted(definition.required_process_keys),
        }
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _add_seconds(value: str, seconds: int | float) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        (parsed.astimezone(UTC) + timedelta(seconds=seconds)).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _required_payload_uuid(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise MkbError("outbox-payload-invalid", f"Outbox payload must contain {key}", 500)
    return value


def _is_sha256_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
