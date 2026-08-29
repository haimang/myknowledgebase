"""Registered selected-output projection algebra.

The runtime consumes already-durable Process outcomes; it does not evaluate
route guards or wait for absent branches.  AP-NH1's pure projection helpers
remain as regression oracles for the production CONTROL implemented by NH2.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest

SELECTED_OUTPUT_CONTROL_VERSION = "selected-output.v1"


@dataclass(frozen=True, slots=True)
class SelectedOutputProjection:
    candidate_port: str
    manifest_ref: str
    manifest_digest: str
    selection_digest: str
    control_version: str = SELECTED_OUTPUT_CONTROL_VERSION


def selected_output_compiled_digest(
    candidate_ports: Sequence[str],
    *,
    fallback_port: str | None = None,
    control_version: str = SELECTED_OUTPUT_CONTROL_VERSION,
) -> str:
    """Return the compiler-envelope contribution for this registered CONTROL."""

    ports = tuple(candidate_ports)
    if not ports or len(ports) != len(set(ports)):
        raise ValueError("selected-output candidate ports must be non-empty and unique")
    if fallback_port is not None and fallback_port not in ports:
        raise ValueError("selected-output fallback must name a registered candidate port")
    return stable_digest(
        {
            "control_key": "selected_output",
            "semantics_version": control_version,
            "candidate_ports": ports,
            "fallback_port": fallback_port,
            "selection_law": "exactly_one_durable_projection",
        }
    )


def project_selected_output(
    durable_rows: Sequence[Mapping[str, Any]],
    *,
    representation_fact_digest: str | None,
    control_version: str = SELECTED_OUTPUT_CONTROL_VERSION,
) -> SelectedOutputProjection:
    """Project exactly one committed selection row onto the canonical output."""

    if not _is_digest(representation_fact_digest):
        raise MkbError(
            "WORKFLOW_SELECTION_FACT_MISSING",
            "Selected-output projection requires a durable representation fact",
            409,
        )
    if not durable_rows:
        raise MkbError(
            "WORKFLOW_SELECTED_OUTPUT_MISSING",
            "Selected-output CONTROL has no committed candidate",
            409,
        )
    if len(durable_rows) != 1:
        raise ConflictError(
            "WORKFLOW_SELECTED_OUTPUT_CONFLICT",
            "Selected-output CONTROL observed more than one committed candidate",
        )

    row = durable_rows[0]
    port = row.get("candidate_port")
    manifest_ref = row.get("manifest_ref")
    manifest_digest = row.get("manifest_digest")
    selection_digest = row.get("selection_digest")
    if not all(isinstance(value, str) and value for value in (port, manifest_ref)):
        raise MkbError("WORKFLOW_SELECTION_PROOF_INVALID", "Selection proof is incomplete", 409)
    if not _is_digest(manifest_digest) or not _is_digest(selection_digest):
        raise MkbError("WORKFLOW_SELECTION_PROOF_INVALID", "Selection proof digest is invalid", 409)
    expected_selection = stable_digest(
        {
            "candidate_port": port,
            "manifest_ref": manifest_ref,
            "manifest_digest": manifest_digest,
            "representation_fact_digest": representation_fact_digest,
            "control_version": control_version,
        }
    )
    if selection_digest != expected_selection:
        raise MkbError("WORKFLOW_SELECTION_PROOF_INVALID", "Selection proof failed its digest fence", 409)
    return SelectedOutputProjection(
        candidate_port=port,
        manifest_ref=manifest_ref,
        manifest_digest=manifest_digest,
        selection_digest=selection_digest,
        control_version=control_version,
    )


def selection_digest(
    *,
    candidate_port: str,
    manifest_ref: str,
    manifest_digest: str,
    representation_fact_digest: str,
    control_version: str = SELECTED_OUTPUT_CONTROL_VERSION,
) -> str:
    return stable_digest(
        {
            "candidate_port": candidate_port,
            "manifest_ref": manifest_ref,
            "manifest_digest": manifest_digest,
            "representation_fact_digest": representation_fact_digest,
            "control_version": control_version,
        }
    )


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "SELECTED_OUTPUT_CONTROL_VERSION",
    "SelectedOutputProjection",
    "project_selected_output",
    "selected_output_compiled_digest",
    "selection_digest",
]
