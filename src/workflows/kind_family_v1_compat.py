"""Checked-in exact rev1 kind-family compatibility definitions.

The JSON is a frozen artifact captured from the pre-NHX1 commit.  This module
does not call the current kind-family builders, so a code change cannot make an
old persisted execution silently resolve to a new graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from src.contracts.common.errors import MkbError
from src.contracts.workflow.models import WorkflowDefinition

_MANIFEST = Path(__file__).with_name("kind_family_v1_manifest.json")
_EXPECTED_SOURCE_COMMIT = "ba099ee305577cca2281a669afbca364111f200b"


def _load() -> tuple[WorkflowDefinition, ...]:
    try:
        payload = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MkbError("WORKFLOW_REV1_MANIFEST_MISSING", "The exact rev1 workflow manifest is unavailable", 503) from exc
    if payload.get("source_commit") != _EXPECTED_SOURCE_COMMIT:
        raise MkbError("WORKFLOW_REV1_MANIFEST_INVALID", "The rev1 workflow manifest source is not frozen", 503)
    workflows = payload.get("workflows")
    if not isinstance(workflows, list) or len(workflows) != 3:
        raise MkbError("WORKFLOW_REV1_MANIFEST_INVALID", "The rev1 workflow manifest is incomplete", 503)
    definitions: list[WorkflowDefinition] = []
    for row in workflows:
        if not isinstance(row, dict) or row.get("revision_number") != 1:
            raise MkbError("WORKFLOW_REV1_MANIFEST_INVALID", "The rev1 workflow revision is invalid", 503)
        definition = WorkflowDefinition.model_validate(row.get("canonical_definition"), strict=False)
        definitions.append(definition)
    return tuple(definitions)


BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS: Final[tuple[WorkflowDefinition, ...]] = _load()

__all__ = ["BUILTIN_KIND_V1_COMPATIBILITY_WORKFLOWS"]
