"""Layered-candidate adoption and projection."""

from __future__ import annotations

from collections.abc import Mapping

from src.contracts.common.ids import stable_digest
from src.contracts.lsrag.layered_content import normalize_layered_text, validate_layered_content
from src.services.lsrag_compiler.models import (
    _SENTENCE,
    RetrievalBlock,
    RetrievalBlockProjection,
    StructureDocument,
    StructureNode,
    TextSpan,
    _block_number,
    _byte_offset,
    _fail,
    _text_digest,
)
from src.services.lsrag_compiler.payloads import structure_document_digest
from src.services.lsrag_compiler.validate import validate_structure


def declared_granularities(granularity_set: tuple[int, ...] | list[int] | None) -> tuple[int, ...]:
    declared = tuple(sorted(set(granularity_set or (0, 1, 2))))
    if not declared or any(isinstance(item, bool) or item not in {0, 1, 2} for item in declared) or 0 not in declared:
        _fail("STRUCTURE_PROFILE_INVALID", "A layered profile must declare a closed set containing g0")
    return declared

def normalize_layered_candidate(*, clean_text: str, layered_json: Mapping[str, object], granularity_set: tuple[int, ...] | list[int] | None = None) -> dict[str, object]:
    """Return the kernel-owned, summary-empty candidate used by S06.

    This is intentionally separate from :meth:`adopt_layered_json` so the
    accepted candidate can be carried to S07 without asking a later stage
    to infer blocks from the projection.  The only invention allowed here
    is the frozen g0 clean-text tunnel.
    """

    clean = normalize_layered_text(clean_text)
    declared = declared_granularities(granularity_set)
    candidate = validate_layered_content(layered_json, summaries_must_be_null=True)
    raw_blocks = candidate["layered_content"]
    assert isinstance(raw_blocks, list)
    observed_granularities = {int(block["granularity"]) for block in raw_blocks}
    if observed_granularities != set(declared):
        _fail("STRUCTURE_GRANULARITY_SET_MISMATCH", "Candidate granularity set does not match the frozen profile")
    g0_blocks = [block for block in raw_blocks if block["granularity"] == 0]
    if len(g0_blocks) != 1:
        _fail("STRUCTURE_G0_REQUIRED", "A layered candidate must contain exactly one g0 block")
    seen_keys: set[tuple[int, int]] = set()
    for raw_block in raw_blocks:
        block_id = int(raw_block["block_id"])
        granularity = int(raw_block["granularity"])
        key = (granularity, block_id)
        if key in seen_keys:
            _fail("STRUCTURE_SCHEMA_INVALID", "Layered block identities must be unique")
        seen_keys.add(key)
        original = raw_block["original_content"]
        assert isinstance(original, dict)
        for field in ("title", "body"):
            value = original[field]
            if isinstance(value, str):
                original[field] = normalize_layered_text(value)
        body = original["body"]
        if granularity == 0 and (body is None or not str(body).strip()):
            original["body"] = clean
        elif not isinstance(body, str) or not body.strip():
            _fail("STRUCTURE_ANCHOR_MISSING", "A non-g0 layered body is empty")
    return candidate

def structurize(*, clean_text: str, generation_artifact_uuid: str, projection_generation_artifact_uuid: str | None = None, clean_artifact_uuid: str, clean_digest: str | None = None) -> tuple[StructureDocument, RetrievalBlockProjection]:
    if not isinstance(clean_text, str) or not clean_text.strip():
        _fail("STRUCTURE_KERNEL_EMPTY", "A structure document requires non-empty clean text")
    projection_generation_artifact_uuid = projection_generation_artifact_uuid or f"{generation_artifact_uuid}:projection"
    if not generation_artifact_uuid or not projection_generation_artifact_uuid or not clean_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Generation and clean artifact identities are required")
    if projection_generation_artifact_uuid == generation_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Structure and projection artifact identities must be distinct")
    observed_clean_digest = _text_digest(clean_text)
    if clean_digest is not None and clean_digest != observed_clean_digest:
        _fail("STRUCTURE_BINDING_CLEAN_DIGEST", "The selected clean artifact digest does not match its bytes")
    clean_digest = observed_clean_digest
    end = len(clean_text.encode("utf-8"))
    root = StructureNode("root", "document", None, 0, 0, 0, "container", None, None, "")
    leaf_id = "node-0001"
    leaf_digest = _text_digest(clean_text)
    leaf = StructureNode(
        leaf_id,
        "paragraph",
        root.node_id,
        0,
        1,
        1,
        "content",
        TextSpan(0, end),
        leaf_digest,
        leaf_digest,
    )
    root = StructureNode("root", "document", None, 0, 0, 0, "container", None, None, stable_digest({"children": [leaf.subtree_digest]}))
    document = StructureDocument(
        generation_artifact_uuid,
        clean_artifact_uuid,
        clean_digest,
        root.node_id,
        (root, leaf),
        stable_digest({"tree": "single-root", "coverage": [(0, end)], "order": ["root", leaf_id]}),
    )
    blocks = project_blocks(clean_text=clean_text, generation_artifact_uuid=generation_artifact_uuid, leaf_id=leaf_id)
    projection = RetrievalBlockProjection(
        projection_generation_artifact_uuid,
        generation_artifact_uuid,
        structure_document_digest(document),
        tuple(blocks),
        stable_digest({"coverage": [(block.block_id, block.original_digest) for block in blocks], "required_g": [0, 1, 2]}),
    )
    validate_structure(document=document, projection=projection, clean_text=clean_text)
    return document, projection

def adopt_layered_json(*, clean_text: str, layered_json: Mapping[str, object], generation_artifact_uuid: str, projection_generation_artifact_uuid: str | None = None, clean_artifact_uuid: str, clean_digest: str | None = None, granularity_set: tuple[int, ...] | list[int] | None = None) -> tuple[StructureDocument, RetrievalBlockProjection]:
    """Admit a B.json candidate and project it into the S06 contract.

    ``structurize`` remains available for historical fixture tests only.
    Production callers must provide this candidate path: the model owns no
    coordinates, and this kernel derives every anchor/digest from clean
    bytes.  The exact profile set is supplied by the frozen json catalog
    row, never inferred from the candidate or from sentence boundaries.
    """

    structure, projection, _report = _adopt_layered_json(
        clean_text=clean_text,
        layered_json=layered_json,
        generation_artifact_uuid=generation_artifact_uuid,
        projection_generation_artifact_uuid=projection_generation_artifact_uuid,
        clean_artifact_uuid=clean_artifact_uuid,
        clean_digest=clean_digest,
        granularity_set=granularity_set,
    )
    return structure, projection

def adopt_layered_json_with_report(*, clean_text: str, layered_json: Mapping[str, object], generation_artifact_uuid: str, projection_generation_artifact_uuid: str | None = None, clean_artifact_uuid: str, clean_digest: str | None = None, granularity_set: tuple[int, ...] | list[int] | None = None) -> tuple[StructureDocument, RetrievalBlockProjection, dict[str, object]]:
    """The same admission API with the auditable anchor report."""

    return _adopt_layered_json(
        clean_text=clean_text,
        layered_json=layered_json,
        generation_artifact_uuid=generation_artifact_uuid,
        projection_generation_artifact_uuid=projection_generation_artifact_uuid,
        clean_artifact_uuid=clean_artifact_uuid,
        clean_digest=clean_digest,
        granularity_set=granularity_set,
    )

def _adopt_layered_json(*, clean_text: str, layered_json: Mapping[str, object], generation_artifact_uuid: str, projection_generation_artifact_uuid: str | None, clean_artifact_uuid: str, clean_digest: str | None, granularity_set: tuple[int, ...] | list[int] | None) -> tuple[StructureDocument, RetrievalBlockProjection, dict[str, object]]:
    clean = normalize_layered_text(clean_text)
    if not clean.strip():
        _fail("STRUCTURE_KERNEL_EMPTY", "A structure document requires non-empty clean text")
    if not generation_artifact_uuid or not clean_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Generation and clean artifact identities are required")
    projection_generation_artifact_uuid = projection_generation_artifact_uuid or f"{generation_artifact_uuid}:projection"
    if projection_generation_artifact_uuid == generation_artifact_uuid:
        _fail("STRUCTURE_BINDING_INVALID", "Structure and projection artifact identities must be distinct")
    declared = declared_granularities(granularity_set)
    observed_clean_digest = _text_digest(clean)
    if clean_digest is not None and clean_digest != observed_clean_digest:
        _fail("STRUCTURE_BINDING_CLEAN_DIGEST", "The selected clean artifact digest does not match its bytes")

    candidate = normalize_layered_candidate(
        clean_text=clean,
        layered_json=layered_json,
        granularity_set=declared,
    )
    raw_blocks = candidate["layered_content"]
    assert isinstance(raw_blocks, list)

    end = len(clean.encode("utf-8"))
    leaf_id = "node-0001"
    leaf_digest = _text_digest(clean)
    root = StructureNode(
        "root",
        "document",
        None,
        0,
        0,
        0,
        "container",
        None,
        None,
        stable_digest({"children": [leaf_digest]}),
    )
    leaf = StructureNode(
        leaf_id,
        "paragraph",
        root.node_id,
        0,
        1,
        1,
        "content",
        TextSpan(0, end),
        leaf_digest,
        leaf_digest,
    )
    structure = StructureDocument(
        generation_artifact_uuid,
        clean_artifact_uuid,
        observed_clean_digest,
        root.node_id,
        (root, leaf),
        stable_digest({"tree": "layered-adopt", "coverage": [(0, end)], "order": [root.node_id, leaf_id]}),
    )
    blocks: list[RetrievalBlock] = []
    anchor_report: list[dict[str, object]] = []
    search_from: dict[int, int] = {}
    for raw_block in sorted(raw_blocks, key=lambda item: (int(item["granularity"]), int(item["block_id"]))):
        block_id = int(raw_block["block_id"])
        granularity = int(raw_block["granularity"])
        original = raw_block["original_content"]
        assert isinstance(original, dict)
        body = original.get("body")
        if not isinstance(body, str) or not body.strip():
            _fail("STRUCTURE_ANCHOR_MISSING", "A non-g0 layered body is empty")
        normalized_body = normalize_layered_text(body)
        if granularity == 0 and normalized_body != clean:
            _fail("STRUCTURE_ANCHOR_MISSING", "The g0 body is not the complete clean artifact")
        if normalized_body not in clean:
            _fail("STRUCTURE_ANCHOR_MISSING", "A layered body is not an exact clean substring")
        first_char = clean.find(normalized_body, search_from.get(granularity, 0))
        if first_char < 0:
            _fail("STRUCTURE_ANCHOR_MISSING", "A layered body has no exact clean anchor")
        occurrence_count = clean.count(normalized_body)
        search_from[granularity] = first_char + max(len(normalized_body), 1)
        start = _byte_offset(clean, first_char)
        finish = _byte_offset(clean, first_char + len(normalized_body))
        projection_block_id = f"g{granularity}:b{block_id:04d}"
        blocks.append(
            RetrievalBlock(
                projection_block_id,
                granularity,
                (leaf_id,),
                (TextSpan(start, finish),),
                normalized_body,
                _text_digest(normalized_body),
            )
        )
        anchor_report.append(
            {
                "block_id": block_id,
                "projection_block_id": projection_block_id,
                "granularity": granularity,
                "start_byte": start,
                "end_byte": finish,
                "occurrence_count": occurrence_count,
            }
        )
    projection = RetrievalBlockProjection(
        projection_generation_artifact_uuid,
        generation_artifact_uuid,
        structure_document_digest(structure),
        tuple(blocks),
        stable_digest({"coverage": anchor_report, "required_g": list(declared)}),
    )
    validate_structure(
        document=structure,
        projection=projection,
        clean_text=clean,
        required_granularities=frozenset(declared),
    )
    report: dict[str, object] = {
        "schema_version": "mkb.layered-content-adoption-report.v1",
        "disposition": "full_valid",
        "granularity_set": list(declared),
        "clean_digest": observed_clean_digest,
        "anchors": anchor_report,
    }
    report["proof_digest"] = stable_digest(report)
    return structure, projection, report

def layered_summary_map(*, layered_json: Mapping[str, object], projection: RetrievalBlockProjection, accepted_layered_json: Mapping[str, object] | None = None) -> dict[str, str]:
    """Map one C whole-package result to exact adopted projection blocks."""

    candidate = validate_layered_content(layered_json, summary_required=True)
    accepted = (
        validate_layered_content(accepted_layered_json, summaries_must_be_null=True)
        if accepted_layered_json is not None
        else None
    )
    candidate_blocks = candidate["layered_content"]
    projection_by_key = {(block.granularity, _block_number(block.block_id)): block for block in projection.blocks}
    accepted_by_key: dict[tuple[int, int], dict[str, object]] = {}
    if accepted is not None:
        accepted_raw = accepted["layered_content"]
        assert isinstance(accepted_raw, list)
        accepted_by_key = {
            (int(block["granularity"]), int(block["block_id"])): block for block in accepted_raw
        }
    summaries: dict[str, str] = {}
    seen: set[tuple[int, int]] = set()
    assert isinstance(candidate_blocks, list)
    for raw_block in candidate_blocks:
        key = (int(raw_block["granularity"]), int(raw_block["block_id"]))
        if key in seen or key not in projection_by_key:
            _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "C layered blocks do not align to the adopted projection")
        seen.add(key)
        projection_block = projection_by_key[key]
        original = raw_block["original_content"]
        summary = raw_block["llm_summary"]
        assert isinstance(original, dict)
        assert isinstance(summary, dict)
        if accepted is not None:
            accepted_block = accepted_by_key.get(key)
            accepted_original = None if accepted_block is None else accepted_block["original_content"]
            if isinstance(accepted_original, dict) and key[0] == 0 and not str(accepted_original.get("body") or "").strip():
                accepted_original = dict(accepted_original)
                accepted_original["body"] = projection_block.original_text
            if accepted_block is None or original != accepted_original:
                _fail("CONSTRUCT_KERNEL_ORIGINAL_MUTATION", "C may fill summary only; original content is immutable")
        elif original.get("body") != projection_block.original_text:
            _fail("CONSTRUCT_KERNEL_ORIGINAL_MUTATION", "C original content does not match the adopted projection")
        body = summary.get("body")
        if not isinstance(body, str) or not body.strip():
            _fail("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Every adopted block needs a non-empty C summary")
        summaries[projection_block.block_id] = body
    if seen != set(projection_by_key):
        _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "C layered output must cover the adopted projection exactly")
    return summaries

def fill_layered_summaries(*, accepted_layered_json: Mapping[str, object], projection: RetrievalBlockProjection, summaries_by_block_id: Mapping[str, str]) -> dict[str, object]:
    """Build the deterministic C-shaped package without changing B fields."""

    candidate = validate_layered_content(accepted_layered_json, summaries_must_be_null=True)
    blocks = candidate["layered_content"]
    assert isinstance(blocks, list)
    projection_by_key = {(block.granularity, _block_number(block.block_id)): block for block in projection.blocks}
    seen: set[tuple[int, int]] = set()
    for raw_block in blocks:
        key = (int(raw_block["granularity"]), int(raw_block["block_id"]))
        projection_block = projection_by_key.get(key)
        if projection_block is None or key in seen:
            _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Summary package does not align to the adopted projection")
        seen.add(key)
        summary = summaries_by_block_id.get(projection_block.block_id)
        if not isinstance(summary, str) or not summary.strip():
            _fail("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Every adopted block needs a non-empty C summary")
        summary_channel = raw_block["llm_summary"]
        assert isinstance(summary_channel, dict)
        summary_channel["body"] = summary
    if seen != set(projection_by_key):
        _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Summary package must cover the adopted projection exactly")
    return candidate

def project_blocks(*, clean_text: str, generation_artifact_uuid: str, leaf_id: str) -> list[RetrievalBlock]:
    end = len(clean_text.encode("utf-8"))
    full = TextSpan(0, end)
    blocks = [
        RetrievalBlock("g0:document", 0, (leaf_id,), (full,), clean_text, _text_digest(clean_text)),
        RetrievalBlock("g1:document", 1, (leaf_id,), (full,), clean_text, _text_digest(clean_text)),
    ]
    sentence_count = 0
    for match in _SENTENCE.finditer(clean_text):
        text = match.group(0)
        if not text.strip():
            continue
        span = TextSpan(_byte_offset(clean_text, match.start()), _byte_offset(clean_text, match.end()))
        blocks.append(RetrievalBlock(f"g2:{sentence_count:04d}", 2, (leaf_id,), (span,), text, _text_digest(text)))
        sentence_count += 1
    if sentence_count == 0:  # Defensive: non-empty clean text still must expose g2.
        blocks.append(RetrievalBlock("g2:0000", 2, (leaf_id,), (full,), clean_text, _text_digest(clean_text)))
    del generation_artifact_uuid  # coordinate identity is carried by the projection envelope.
    return blocks
