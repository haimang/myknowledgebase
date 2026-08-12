"""Focused S04 metadata semantic binding regressions."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from src.contracts.api.models import IntakeUpdateMetadataPayload
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.intake_pipeline import IntakePipeline
from src.services.intake_lifecycle import IntakeTargetResolver
from tests.unit.test_intake_lifecycle import SeededIntake
from tests.unit.test_intake_lifecycle import seeded_intake as _seeded_intake_fixture


@pytest.fixture
async def seeded_intake(tmp_path: Path) -> AsyncIterator[SeededIntake]:
    """Reuse the canonical S04 fixture while keeping this module standalone."""

    async for seeded in _seeded_intake_fixture.__wrapped__(tmp_path):
        yield seeded


async def _register_semantic_definition(
    persistence: SqlitePersistence,
    *,
    semantic_key: str,
    definition_version: str,
    value_kind: str,
    fingerprint_participation: bool,
) -> str:
    body = {
        "semantic_key": semantic_key,
        "version": definition_version,
        "value_kind": value_kind,
        "fingerprint_participation": fingerprint_participation,
    }
    digest = stable_digest(body)
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_intake_semantic_definitions "
            "(semantic_key,definition_version,value_kind,fingerprint_participation,definition_digest,definition_body_json,"
            "registered_at,payload_extra) VALUES (?,?,?,?,?,?,?,'{}')",
            (
                semantic_key,
                definition_version,
                value_kind,
                int(fingerprint_participation),
                digest,
                json.dumps(body, sort_keys=True, separators=(",", ":")),
                utc_now(),
            ),
        )
    return digest


async def _clean_artifact_uuid(seeded: SeededIntake) -> str:
    async with seeded.persistence.transaction() as tx:
        row = await tx.fetchone(
            "SELECT intake_artifact_uuid FROM mkb_intake_artifacts "
            "WHERE team_uuid=? AND owner_revision_uuid=? AND artifact_role='clean_text'",
            (seeded.team_uuid, seeded.revision_uuid),
        )
    assert row is not None
    return row["intake_artifact_uuid"]


@pytest.mark.asyncio
async def test_metadata_resolver_freezes_exact_definition_participation_and_artifact_ref(
    seeded_intake: SeededIntake,
) -> None:
    """A public metadata command cannot drift to a new definition or foreign ref."""

    ref_digest = await _register_semantic_definition(
        seeded_intake.persistence,
        semantic_key="asset_reference",
        definition_version="v1",
        value_kind="ref",
        fingerprint_participation=True,
    )
    version_two_digest = await _register_semantic_definition(
        seeded_intake.persistence,
        semantic_key="context_metadata",
        definition_version="v2",
        value_kind="text",
        fingerprint_participation=False,
    )
    clean_artifact_uuid = await _clean_artifact_uuid(seeded_intake)
    resolver = IntakeTargetResolver(seeded_intake.persistence)

    frozen = await resolver.resolve_metadata_update(
        seeded_intake.team_uuid,
        IntakeUpdateMetadataPayload(
            intake_item_uuid=seeded_intake.item_uuid,
            semantics={
                "asset_reference": clean_artifact_uuid,
                "context_metadata": {"definition_version": "v2", "value": "routing-only"},
            },
        ),
    )
    values = {value.semantic_key: value for value in frozen.semantics}
    assert values["asset_reference"].definition_version == "v1"
    assert values["asset_reference"].definition_digest == ref_digest
    assert values["asset_reference"].value_kind == "ref"
    assert values["asset_reference"].fingerprint_participation is True
    assert values["asset_reference"].value == clean_artifact_uuid
    assert values["context_metadata"].definition_version == "v2"
    assert values["context_metadata"].definition_digest == version_two_digest
    assert values["context_metadata"].fingerprint_participation is False

    with pytest.raises(MkbError, match="requires an explicit version"):
        await resolver.resolve_metadata_update(
            seeded_intake.team_uuid,
            IntakeUpdateMetadataPayload(
                intake_item_uuid=seeded_intake.item_uuid,
                semantics={"context_metadata": "would select v1 or v2"},
            ),
        )
    with pytest.raises(MkbError, match="version is not registered"):
        await resolver.resolve_metadata_update(
            seeded_intake.team_uuid,
            IntakeUpdateMetadataPayload(
                intake_item_uuid=seeded_intake.item_uuid,
                semantics={"context_metadata": {"definition_version": "v3", "value": "not registered"}},
            ),
        )
    with pytest.raises(MkbError, match="not an available Intake artifact"):
        await resolver.resolve_metadata_update(
            seeded_intake.team_uuid,
            IntakeUpdateMetadataPayload(
                intake_item_uuid=seeded_intake.item_uuid,
                semantics={"asset_reference": uuid7()},
            ),
        )


@pytest.mark.asyncio
async def test_metadata_semantic_helpers_map_refs_recheck_them_and_exclude_nonparticipating_values(
    seeded_intake: SeededIntake,
) -> None:
    """The immutable Revision row has an artifact FK while Task input stays logical."""

    ref_digest = await _register_semantic_definition(
        seeded_intake.persistence,
        semantic_key="asset_reference",
        definition_version="v1",
        value_kind="ref",
        fingerprint_participation=True,
    )
    clean_artifact_uuid = await _clean_artifact_uuid(seeded_intake)
    pipeline = IntakePipeline(seeded_intake.persistence, None, None)  # type: ignore[arg-type]
    ref_entry = {
        "semantic_key": "asset_reference",
        "definition_version": "v1",
        "definition_digest": ref_digest,
        "value_kind": "ref",
        "fingerprint_participation": True,
        "value": clean_artifact_uuid,
        "value_digest": pipeline._semantic_value_digest("asset_reference", "v1", ref_digest, clean_artifact_uuid),
    }
    async with seeded_intake.persistence.transaction() as tx:
        await pipeline._insert_revision_semantic(
            tx,
            seeded_intake.team_uuid,
            seeded_intake.revision_uuid,
            ref_entry,
            utc_now(),
        )
        stored = await tx.fetchone(
            "SELECT value_kind,value_artifact_uuid FROM mkb_intake_revision_semantics "
            "WHERE team_uuid=? AND intake_revision_uuid=? AND semantic_key='asset_reference'",
            (seeded_intake.team_uuid, seeded_intake.revision_uuid),
        )
        assert stored == {"value_kind": "artifact_ref", "value_artifact_uuid": clean_artifact_uuid}
        inherited, _fingerprint = await pipeline._merged_metadata_semantics_tx(
            tx,
            seeded_intake.team_uuid,
            seeded_intake.revision_uuid,
            [],
            [ref_entry],
        )
        assert inherited["asset_reference"] == ref_entry

        missing_ref = {**ref_entry, "value": uuid7()}
        missing_ref["value_digest"] = pipeline._semantic_value_digest(
            "asset_reference", "v1", ref_digest, missing_ref["value"]
        )
        with pytest.raises(MkbError, match="not an available Intake artifact"):
            await pipeline._merged_metadata_semantics_tx(
                tx,
                seeded_intake.team_uuid,
                seeded_intake.revision_uuid,
                [missing_ref],
                [ref_entry],
            )

    participating = {
        "semantic_key": "canonical_content",
        "definition_version": "v1",
        "value_digest": stable_digest({"value": "one"}),
        "fingerprint_participation": True,
    }
    ignored_before = {
        "semantic_key": "route_hint",
        "definition_version": "v1",
        "value_digest": stable_digest({"value": "before"}),
        "fingerprint_participation": False,
    }
    ignored_after = {**ignored_before, "value_digest": stable_digest({"value": "after"})}
    changed_participating = {**participating, "value_digest": stable_digest({"value": "two"})}
    assert pipeline._semantic_fingerprint([participating, ignored_before]) == pipeline._semantic_fingerprint(
        [participating, ignored_after]
    )
    assert pipeline._semantic_fingerprint([participating, ignored_before]) != pipeline._semantic_fingerprint(
        [changed_participating, ignored_before]
    )
