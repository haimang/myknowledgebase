"""NH1-T04 L2: project a durable exactly-one selection through the spike."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest
from src.persistence.factory import build_persistence
from src.runtime.workflow.selected_output import project_selected_output, selection_digest


async def _persistence(tmp_path: Path, name: str):
    persistence = build_persistence(
        tmp_path / f"{name}.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    async with persistence.transaction() as tx:
        await tx.execute(
            "CREATE TABLE nh1_selection_proofs ("
            "candidate_port TEXT PRIMARY KEY,manifest_ref TEXT NOT NULL,manifest_digest TEXT NOT NULL,"
            "representation_fact_digest TEXT NOT NULL,selection_digest TEXT NOT NULL)"
        )
    return persistence


async def _insert_selection(persistence: object, *, port: str, fact: str, suffix: str) -> None:
    manifest_ref = f"mkbobj:v1:nh1:{suffix}"
    manifest_digest = stable_digest({"candidate": suffix})
    digest = selection_digest(
        candidate_port=port,
        manifest_ref=manifest_ref,
        manifest_digest=manifest_digest,
        representation_fact_digest=fact,
    )
    async with persistence.transaction() as tx:  # type: ignore[attr-defined]
        await tx.execute(
            "INSERT INTO nh1_selection_proofs VALUES (?,?,?,?,?)",
            (port, manifest_ref, manifest_digest, fact, digest),
        )


async def _rows(persistence: object) -> list[dict[str, object]]:
    async with persistence.transaction() as tx:  # type: ignore[attr-defined]
        return await tx.fetchall(
            "SELECT candidate_port,manifest_ref,manifest_digest,selection_digest "
            "FROM nh1_selection_proofs ORDER BY candidate_port"
        )


@pytest.mark.asyncio
async def test_single_candidate_projects(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "single")
    fact = stable_digest({"main_text_presence": "present"})
    try:
        await _insert_selection(persistence, port="candidate_a", fact=fact, suffix="a")
        rows = await _rows(persistence)
        projected = project_selected_output(rows, representation_fact_digest=fact)
        assert projected.candidate_port == "candidate_a"
        assert projected.manifest_digest == stable_digest({"candidate": "a"})
    finally:
        await persistence.close()

@pytest.mark.asyncio
async def test_zero_candidates_fail_loud(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "zero")
    try:
        with pytest.raises(MkbError) as raised:
            project_selected_output([], representation_fact_digest=stable_digest({"fact": "present"}))
        assert raised.value.code == "WORKFLOW_SELECTED_OUTPUT_MISSING"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_double_hit_fail_loud(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "double")
    fact = stable_digest({"main_text_presence": "present"})
    try:
        await _insert_selection(persistence, port="candidate_a", fact=fact, suffix="a")
        await _insert_selection(persistence, port="candidate_b", fact=fact, suffix="b")
        with pytest.raises(ConflictError) as raised:
            project_selected_output(await _rows(persistence), representation_fact_digest=fact)
        assert raised.value.code == "WORKFLOW_SELECTED_OUTPUT_CONFLICT"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_missing_fact_fail_closed(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "missing-fact")
    fact = stable_digest({"main_text_presence": "absent"})
    try:
        await _insert_selection(persistence, port="candidate_b", fact=fact, suffix="b")
        with pytest.raises(MkbError) as raised:
            project_selected_output(await _rows(persistence), representation_fact_digest=None)
        assert raised.value.code == "WORKFLOW_SELECTION_FACT_MISSING"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_does_not_wait_on_scatter_join(tmp_path: Path) -> None:
    persistence = await _persistence(tmp_path, "no-wait")
    fact = stable_digest({"main_text_presence": "present"})
    try:
        await _insert_selection(persistence, port="candidate_a", fact=fact, suffix="only-materialized")
        projected = project_selected_output(await _rows(persistence), representation_fact_digest=fact)
        assert projected.candidate_port == "candidate_a"
        source = Path("src/runtime/workflow/selected_output.py").read_text(encoding="utf-8")
        assert "scatter_children" + "_join" not in source
    finally:
        await persistence.close()
