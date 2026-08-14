"""NS1-T30/T31/T32/T34: strict prompt identities and frozen graph choices."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.contracts.api.models import IntakeIngestPayload
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.workflow.models import WorkflowOutcomeSelector
from src.runtime.workflow.runtime_materialize import WorkflowMaterializeMixin
from src.services.config_snapshots import ConfigSnapshotService
from src.workflows.builtin_lsrag import BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS
from src.workflows.builtin_scatter import (
    BUILTIN_NS1_PRE_MARKDOWN_SCATTER_COMPATIBILITY_WORKFLOW,
    BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
)
from src.workflows.lsrag_definition import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


def _payload(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "source": {
            "source_kind": "inline_payload",
            "external_key": "ns1-contract",
            "content": "source text",
        },
        "json_prompt_id": "promptB.json.generic",
    }
    value.update(extra)
    return value


def test_ingest_payload_requires_json_identity_and_rejects_transport_coordinates() -> None:
    with pytest.raises(ValidationError):
        IntakeIngestPayload.model_validate(_payload(json_prompt_id=None))

    valid = IntakeIngestPayload.model_validate(
        _payload(
            markdown_prompt_id="promptB.markdown.legal",
            clean_prompt_id="promptA.default",
            summarizer_prompt_id="promptC.default",
        )
    )
    assert valid.json_prompt_id == "promptB.json.generic"

    for forbidden in ("prompt_ref", "git_relative_path", "absolute_path"):
        with pytest.raises(ValidationError):
            IntakeIngestPayload.model_validate(_payload(**{forbidden: "caller-controlled"}))


def _catalog_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for prompt_id, version, relative_path, role, granularity_set in (
        ("promptA.clean", "v1", "clean/promptA.clean.v1.md", "clean", None),
        ("promptA.default", "v1", "prompt-a-clean-v1.md", "clean", None),
        (
            "promptB.markdown.legal",
            "v1",
            "markdown/promptB.markdown.legal.v1.md",
            "markdown",
            None,
        ),
        ("promptB.json.generic", "v1", "json/promptB.json.generic.v1.md", "json", [0, 1, 2]),
        ("promptB.json.legal", "v1", "json/promptB.json.legal.v1.md", "json", [0, 1]),
        ("promptC.summarizer", "v1", "summarizer/promptC.summarizer.v1.md", "summarizer", None),
        ("promptC.default", "v1", "prompt-c-summary-v1.md", "summarizer", None),
    ):
        content = (Path("data/prompts") / relative_path).read_bytes()
        rows.append(
            {
                "prompt_id": prompt_id,
                "prompt_key": prompt_id,
                "prompt_version": version,
                "git_relative_path": relative_path,
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "role": role,
                "status": "active",
                "granularity_set": None if granularity_set is None else json.dumps(granularity_set),
            }
        )
    return rows


def test_materialize_resolves_role_rows_to_hash_path_and_profile() -> None:
    service = object.__new__(ConfigSnapshotService)
    service.settings = SimpleNamespace(prompt_root=Path("data/prompts").resolve())
    payload = IntakeIngestPayload.model_validate(
        _payload(
            markdown_prompt_id="promptB.markdown.legal",
            clean_prompt_id="promptA.default",
            summarizer_prompt_id="promptC.default",
        )
    )

    selection = service._resolve_prompt_selection(_catalog_rows(), SimpleNamespace(payload=payload))

    assert selection["markdown"]["prompt_id"] == "promptB.markdown.legal"
    assert selection["json"]["granularity_set"] == [0, 1, 2]
    assert selection["json"]["git_relative_path"] == "json/promptB.json.generic.v1.md"
    assert all("body" not in pointer for pointer in selection.values() if pointer is not None)

    mismatched = _catalog_rows()
    next(row for row in mismatched if row["prompt_id"] == "promptB.json.generic")["role"] = "markdown"
    with pytest.raises(MkbError) as error:
        service._resolve_prompt_selection(mismatched, SimpleNamespace(payload=payload))
    assert error.value.code == "PROMPT_ROLE_MISMATCH"


def test_new_ingest_selects_latest_active_and_frozen_pointer_stays_put() -> None:
    service = object.__new__(ConfigSnapshotService)
    service.settings = SimpleNamespace(prompt_root=Path("data/prompts").resolve())
    rows = _catalog_rows()
    payload = IntakeIngestPayload.model_validate(_payload())
    first = service._resolve_prompt_selection(rows, SimpleNamespace(payload=payload))
    frozen_hash = first["json"]["content_sha256"]
    v1 = next(row for row in rows if row["prompt_id"] == "promptB.json.generic")
    rows.append(
        {
            **v1,
            "prompt_version": "v10",
            "git_relative_path": "json/promptB.json.generic.v1.md",
            "status": "active",
        }
    )
    v1["status"] = "retired"
    second = service._resolve_prompt_selection(rows, SimpleNamespace(payload=payload))
    assert second["json"]["version"] == "v10"
    assert first["json"]["version"] == "v1"
    assert first["json"]["content_sha256"] == frozen_hash


class _RouteProbe(WorkflowMaterializeMixin):
    pass


def _execution() -> dict[str, object]:
    return {
        "workflow_revision_uuid": uuid7(),
        "execution_uuid": uuid7(),
    }


def test_current_graph_selects_optional_markdown_and_legacy_graph_is_registered() -> None:
    probe = _RouteProbe()
    current = probe._route_decision(
        plan=BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        execution=_execution(),
        source_step_key="accept_snapshot",
        selector=WorkflowOutcomeSelector.SUCCEEDED,
        route_context={"admission_result": "auto_admitted", "admission_markdown_selection": "auto_admitted"},
    )
    assert [route.route_key for route in current["routes"]] == ["accept_snapshot.auto_admitted_markdown"]

    skipped = probe._route_decision(
        plan=BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        execution=_execution(),
        source_step_key="accept_snapshot",
        selector=WorkflowOutcomeSelector.SUCCEEDED,
        route_context={"admission_result": "auto_admitted"},
    )
    assert [route.route_key for route in skipped["routes"]] == ["accept_snapshot.auto_admitted"]

    assert any(
        definition.workflow_key == BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.workflow_key
        and definition.revision_number == 3
        for definition in BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS
    )
    assert BUILTIN_NS1_PRE_MARKDOWN_SCATTER_COMPATIBILITY_WORKFLOW.revision_number == 1
    assert BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW.revision_number == 2
    assert stable_digest(BUILTIN_NS1_PRE_MARKDOWN_SCATTER_COMPATIBILITY_WORKFLOW.model_dump()) != stable_digest(
        BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW.model_dump()
    )


def test_structurize_failure_routes_terminal_without_opening_human_review() -> None:
    probe = _RouteProbe()
    decision = probe._route_decision(
        plan=BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        execution=_execution(),
        source_step_key="structurize",
        selector=WorkflowOutcomeSelector.FAILED,
        route_context={"admission_result": "auto_admitted"},
    )
    assert [route.route_key for route in decision["routes"]] == ["structurize.failed"]
    assert decision["routes"][0].to_step_key == "failed"
