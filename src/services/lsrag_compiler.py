"""Deterministic, fail-closed S06--S08 content contracts.

This module deliberately has no persistence or workflow dependency.  It is the
small kernel used by a worker to turn a selected clean artifact into the three
generation-local artifact shapes.  Persisting bytes, accepting generation
pointers, invoking a model, and writing vectors remain concerns of S06/S07/S08
workers respectively.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.lsrag.layered_content import normalize_layered_text, validate_layered_content

_NODE_KINDS = frozenset({"document", "section", "paragraph", "list", "list_item", "table", "table_row", "table_cell", "code", "quote", "media_ref", "heading"})
_CHANNELS = frozenset({"original", "summary"})
_HEADER_KEY = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_SENTENCE = re.compile(r"\S(?:.*?)(?:[.!?。！？](?=\s|$)|$)", re.DOTALL)
_ADOPTED_BLOCK_ID = re.compile(r"^g[0-2]:b(\d{4})$")


def _fail(code: str, message: str) -> None:
    raise MkbError(code, message, 422)


def _text_digest(value: str) -> str:
    """Fingerprint UTF-8 text through the project canonical digest primitive."""

    # Keep the existing artifact/vector text-digest recipe so the compiler can
    # validate current persisted S05/S06 values without a migration shim.
    return stable_digest({"text": value})


def _span_text(value: str, start_byte: int, end_byte: int) -> str:
    encoded = value.encode("utf-8")
    if start_byte < 0 or end_byte < start_byte or end_byte > len(encoded):
        _fail("STRUCTURE_ANCHOR_INVALID", "A source anchor is outside the selected clean artifact")
    try:
        return encoded[start_byte:end_byte].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MkbError("STRUCTURE_ANCHOR_INVALID", "A source anchor splits a UTF-8 code point", 422) from exc


def _byte_offset(value: str, char_offset: int) -> int:
    return len(value[:char_offset].encode("utf-8"))


def _block_number(block_id: str) -> int:
    match = _ADOPTED_BLOCK_ID.fullmatch(block_id)
    if match is None:
        _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Projection block identity is not an adopted layered block")
    return int(match.group(1))


@dataclass(frozen=True, slots=True)
class TextSpan:
    start_byte: int
    end_byte: int


@dataclass(frozen=True, slots=True)
class StructureNode:
    node_id: str
    node_kind: str
    parent_node_id: str | None
    sibling_ordinal: int
    depth: int
    reading_ordinal: int
    content_role: str
    source_anchor: TextSpan | None
    content_digest: str | None
    subtree_digest: str


@dataclass(frozen=True, slots=True)
class StructureDocument:
    generation_artifact_uuid: str
    clean_artifact_uuid: str
    clean_digest: str
    document_root_node_id: str
    nodes: tuple[StructureNode, ...]
    proof_digest: str


@dataclass(frozen=True, slots=True)
class RetrievalBlock:
    block_id: str
    granularity: int
    source_node_refs: tuple[str, ...]
    ordered_source_spans: tuple[TextSpan, ...]
    original_text: str
    original_digest: str


@dataclass(frozen=True, slots=True)
class RetrievalBlockProjection:
    generation_artifact_uuid: str
    structure_generation_artifact_uuid: str
    structure_document_digest: str
    blocks: tuple[RetrievalBlock, ...]
    proof_digest: str


@dataclass(frozen=True, slots=True)
class ChannelRecord:
    channel: str
    body: str
    body_digest: str
    content_full: str
    content_full_digest: str
    grounds_coordinate: str
    reattach_status: str


@dataclass(frozen=True, slots=True)
class ConstructionUnit:
    unit_id: str
    granularity: int
    coordinate: str
    original: ChannelRecord
    summary: ChannelRecord


@dataclass(frozen=True, slots=True)
class ConstructionDocument:
    generation_artifact_uuid: str
    structure_generation_artifact_uuid: str
    projection_generation_artifact_uuid: str
    structure_document_digest: str
    projection_digest: str
    units: tuple[ConstructionUnit, ...]
    metadata_projection_digest: str
    content_full_recipe_version: str
    proof_digest: str


@dataclass(frozen=True, slots=True)
class DualChannelProjection:
    generation_artifact_uuid: str
    construction_generation_artifact_uuid: str
    construction_document_digest: str
    units: tuple[ConstructionUnit, ...]
    proof_digest: str


@dataclass(frozen=True, slots=True)
class VectorizationUnit:
    unit_id: str
    granularity: int
    channel: str
    coordinate: str
    content_full: str
    content_full_digest: str


@dataclass(frozen=True, slots=True)
class VectorizationPlan:
    required: tuple[VectorizationUnit, ...]
    skipped: tuple[str, ...]
    required_digest: str


@dataclass(frozen=True, slots=True)
class SummaryPlan:
    """Deterministic ordered summary workset for a projection generation."""

    block_ids: tuple[str, ...]
    plan_digest: str


def content_full(*, body: str, metadata_headers: Mapping[str, str] | None = None, recipe_version: str = "content_full.v1") -> str:
    """Materialize the S07/S08 re-computable text recipe.

    Only a closed, caller-projected metadata mapping is accepted.  This helper
    does not treat metadata as filter authority; it only deterministically
    renders already-authorized display context.
    """

    if recipe_version != "content_full.v1":
        _fail("CONSTRUCT_RECIPE_UNSUPPORTED", "The content_full recipe version is unsupported")
    if not isinstance(body, str):
        _fail("CONSTRUCT_KERNEL_BODY_INVALID", "Channel body must be UTF-8 text")
    headers = metadata_headers or {}
    lines: list[str] = []
    for key in sorted(headers):
        value = headers[key]
        if not _HEADER_KEY.fullmatch(key) or not isinstance(value, str) or "\x00" in value or "\n" in value or "\r" in value:
            _fail("CONSTRUCT_METADATA_PROJECTION_INVALID", "Content header projection is invalid")
        lines.append(f"{key}: {value}")
    if not lines:
        return body
    header = "\n".join(lines)
    return f"{header}\n\n{body}"


def structure_document_digest(document: StructureDocument) -> str:
    return stable_digest(
        {
            "generation": document.generation_artifact_uuid,
            "clean_artifact": document.clean_artifact_uuid,
            "clean_digest": document.clean_digest,
            "root": document.document_root_node_id,
            "nodes": [
                {
                    "id": node.node_id,
                    "kind": node.node_kind,
                    "parent": node.parent_node_id,
                    "sibling": node.sibling_ordinal,
                    "depth": node.depth,
                    "reading": node.reading_ordinal,
                    "role": node.content_role,
                    "span": None if node.source_anchor is None else (node.source_anchor.start_byte, node.source_anchor.end_byte),
                    "content": node.content_digest,
                    "subtree": node.subtree_digest,
                }
                for node in document.nodes
            ],
            "proof": document.proof_digest,
        }
    )


def projection_digest(projection: RetrievalBlockProjection) -> str:
    return stable_digest(
        {
            "generation": projection.generation_artifact_uuid,
            "structure_generation": projection.structure_generation_artifact_uuid,
            "structure_digest": projection.structure_document_digest,
            "blocks": [
                {
                    "id": block.block_id,
                    "g": block.granularity,
                    "nodes": block.source_node_refs,
                    "spans": [(span.start_byte, span.end_byte) for span in block.ordered_source_spans],
                    "original": block.original_digest,
                }
                for block in projection.blocks
            ],
            "proof": projection.proof_digest,
        }
    )


class LsragContractCompiler:
    """Pure deterministic compiler for the accepted S06--S08 artifact shapes."""

    @staticmethod
    def _declared_granularities(granularity_set: tuple[int, ...] | list[int] | None) -> tuple[int, ...]:
        declared = tuple(sorted(set(granularity_set or (0, 1, 2))))
        if not declared or any(isinstance(item, bool) or item not in {0, 1, 2} for item in declared) or 0 not in declared:
            _fail("STRUCTURE_PROFILE_INVALID", "A layered profile must declare a closed set containing g0")
        return declared

    def normalize_layered_candidate(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        granularity_set: tuple[int, ...] | list[int] | None = None,
    ) -> dict[str, object]:
        """Return the kernel-owned, summary-empty candidate used by S06.

        This is intentionally separate from :meth:`adopt_layered_json` so the
        accepted candidate can be carried to S07 without asking a later stage
        to infer blocks from the projection.  The only invention allowed here
        is the frozen g0 clean-text tunnel.
        """

        clean = normalize_layered_text(clean_text)
        declared = self._declared_granularities(granularity_set)
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

    def structurize(
        self,
        *,
        clean_text: str,
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None = None,
        clean_artifact_uuid: str,
        clean_digest: str | None = None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection]:
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
        blocks = self._project_blocks(clean_text=clean_text, generation_artifact_uuid=generation_artifact_uuid, leaf_id=leaf_id)
        projection = RetrievalBlockProjection(
            projection_generation_artifact_uuid,
            generation_artifact_uuid,
            structure_document_digest(document),
            tuple(blocks),
            stable_digest({"coverage": [(block.block_id, block.original_digest) for block in blocks], "required_g": [0, 1, 2]}),
        )
        self.validate_structure(document=document, projection=projection, clean_text=clean_text)
        return document, projection

    def adopt_layered_json(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None = None,
        clean_artifact_uuid: str,
        clean_digest: str | None = None,
        granularity_set: tuple[int, ...] | list[int] | None = None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection]:
        """Admit a B.json candidate and project it into the S06 contract.

        ``structurize`` remains available for historical fixture tests only.
        Production callers must provide this candidate path: the model owns no
        coordinates, and this kernel derives every anchor/digest from clean
        bytes.  The exact profile set is supplied by the frozen json catalog
        row, never inferred from the candidate or from sentence boundaries.
        """

        structure, projection, _report = self._adopt_layered_json(
            clean_text=clean_text,
            layered_json=layered_json,
            generation_artifact_uuid=generation_artifact_uuid,
            projection_generation_artifact_uuid=projection_generation_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=clean_digest,
            granularity_set=granularity_set,
        )
        return structure, projection

    def adopt_layered_json_with_report(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None = None,
        clean_artifact_uuid: str,
        clean_digest: str | None = None,
        granularity_set: tuple[int, ...] | list[int] | None = None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection, dict[str, object]]:
        """The same admission API with the auditable anchor report."""

        return self._adopt_layered_json(
            clean_text=clean_text,
            layered_json=layered_json,
            generation_artifact_uuid=generation_artifact_uuid,
            projection_generation_artifact_uuid=projection_generation_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=clean_digest,
            granularity_set=granularity_set,
        )

    def _adopt_layered_json(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None,
        clean_artifact_uuid: str,
        clean_digest: str | None,
        granularity_set: tuple[int, ...] | list[int] | None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection, dict[str, object]]:
        clean = normalize_layered_text(clean_text)
        if not clean.strip():
            _fail("STRUCTURE_KERNEL_EMPTY", "A structure document requires non-empty clean text")
        if not generation_artifact_uuid or not clean_artifact_uuid:
            _fail("STRUCTURE_BINDING_INVALID", "Generation and clean artifact identities are required")
        projection_generation_artifact_uuid = projection_generation_artifact_uuid or f"{generation_artifact_uuid}:projection"
        if projection_generation_artifact_uuid == generation_artifact_uuid:
            _fail("STRUCTURE_BINDING_INVALID", "Structure and projection artifact identities must be distinct")
        declared = self._declared_granularities(granularity_set)
        observed_clean_digest = _text_digest(clean)
        if clean_digest is not None and clean_digest != observed_clean_digest:
            _fail("STRUCTURE_BINDING_CLEAN_DIGEST", "The selected clean artifact digest does not match its bytes")

        candidate = self.normalize_layered_candidate(
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
            first_char = clean.find(normalized_body)
            if first_char < 0:
                _fail("STRUCTURE_ANCHOR_MISSING", "A layered body has no exact clean anchor")
            occurrence_count = 0
            cursor = first_char
            while cursor >= 0:
                occurrence_count += 1
                cursor = clean.find(normalized_body, cursor + 1)
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
        self.validate_structure(
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

    @staticmethod
    def layered_summary_map(
        *,
        layered_json: Mapping[str, object],
        projection: RetrievalBlockProjection,
        accepted_layered_json: Mapping[str, object] | None = None,
    ) -> dict[str, str]:
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

    @staticmethod
    def fill_layered_summaries(
        *,
        accepted_layered_json: Mapping[str, object],
        projection: RetrievalBlockProjection,
        summaries_by_block_id: Mapping[str, str],
    ) -> dict[str, object]:
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

    def _project_blocks(self, *, clean_text: str, generation_artifact_uuid: str, leaf_id: str) -> list[RetrievalBlock]:
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

    def validate_structure(
        self,
        *,
        document: StructureDocument,
        projection: RetrievalBlockProjection,
        clean_text: str,
        required_granularities: frozenset[int] = frozenset({0, 1, 2}),
    ) -> None:
        if document.clean_digest != _text_digest(clean_text):
            _fail("STRUCTURE_BINDING_CLEAN_DIGEST", "The structure is not bound to these clean bytes")
        if (
            projection.structure_generation_artifact_uuid != document.generation_artifact_uuid
            or projection.generation_artifact_uuid == document.generation_artifact_uuid
        ):
            _fail("STRUCTURE_BINDING_CROSS_GENERATION", "Structure and projection generations differ")
        if projection.structure_document_digest != structure_document_digest(document):
            _fail("STRUCTURE_BINDING_DIGEST", "Projection does not bind this exact structure document")
        roots = [node for node in document.nodes if node.parent_node_id is None]
        if len(roots) != 1 or roots[0].node_id != document.document_root_node_id or roots[0].node_kind != "document":
            _fail("STRUCTURE_TREE_ROOT", "Structure documents require exactly one document root")
        ids = {node.node_id for node in document.nodes}
        if len(ids) != len(document.nodes):
            _fail("STRUCTURE_TREE_DUPLICATE_NODE", "Structure node identities must be unique")
        if any(node.node_kind not in _NODE_KINDS for node in document.nodes):
            _fail("STRUCTURE_NODE_KIND_INVALID", "Structure node kind is not in the schema closed set")
        if [node.reading_ordinal for node in document.nodes] != list(range(len(document.nodes))):
            _fail("STRUCTURE_ORDER_INVALID", "Structure reading order must be complete and contiguous")
        children: dict[str, list[StructureNode]] = {}
        for node in document.nodes:
            if node.parent_node_id is not None:
                if node.parent_node_id not in ids:
                    _fail("STRUCTURE_TREE_PARENT", "Structure node has an unknown parent")
                children.setdefault(node.parent_node_id, []).append(node)
                parent = next(candidate for candidate in document.nodes if candidate.node_id == node.parent_node_id)
                if node.depth != parent.depth + 1:
                    _fail("STRUCTURE_TREE_DEPTH", "Structure node depth is inconsistent")
        for members in children.values():
            if sorted(member.sibling_ordinal for member in members) != list(range(len(members))):
                _fail("STRUCTURE_ORDER_INVALID", "Sibling ordinals must be contiguous")
        leaves = [node for node in document.nodes if node.node_id not in children]
        spans: list[TextSpan] = []
        for leaf in leaves:
            if leaf.content_role == "content":
                if leaf.source_anchor is None:
                    _fail("STRUCTURE_ANCHOR_MISSING", "Content leaves require exact clean anchors")
                anchored = _span_text(clean_text, leaf.source_anchor.start_byte, leaf.source_anchor.end_byte)
                if leaf.content_digest != _text_digest(anchored):
                    _fail("STRUCTURE_ANCHOR_DIGEST", "Content leaf digest does not match its anchor")
                spans.append(leaf.source_anchor)
        # The content leaves are the authoritative partition of the admitted
        # clean bytes.  Checking only min/max would accept a tree that skips
        # or duplicates bytes in the middle, which makes later reattachment
        # ambiguous.  Preserve tree reading order rather than normalising it:
        # an out-of-order candidate is invalid kernel output, not something a
        # worker may silently repair.
        expected_start = 0
        for span in spans:
            _span_text(clean_text, span.start_byte, span.end_byte)
            if span.start_byte != expected_start or span.end_byte <= span.start_byte:
                _fail("STRUCTURE_COVERAGE_INVALID", "Content leaf anchors must be an ordered, gap-free clean-byte partition")
            expected_start = span.end_byte
        if not spans or expected_start != len(clean_text.encode("utf-8")):
            _fail("STRUCTURE_COVERAGE_INVALID", "Content leaf anchors must cover the selected clean artifact")
        block_ids: set[str] = set()
        granularities: set[int] = set()
        for block in projection.blocks:
            if block.block_id in block_ids or block.granularity not in {0, 1, 2} or not block.source_node_refs or not block.ordered_source_spans:
                _fail("STRUCTURE_PROJECTION_INVALID", "Projection block shape is invalid")
            block_ids.add(block.block_id)
            granularities.add(block.granularity)
            if any(node_id not in ids for node_id in block.source_node_refs):
                _fail("STRUCTURE_PROJECTION_NODE", "Projection block references an unknown structure node")
            previous_end = -1
            pieces: list[str] = []
            for span in block.ordered_source_spans:
                if span.start_byte < previous_end or span.end_byte <= span.start_byte:
                    _fail("STRUCTURE_PROJECTION_ORDER", "Projection source spans must be ordered and non-overlapping")
                pieces.append(_span_text(clean_text, span.start_byte, span.end_byte))
                previous_end = span.end_byte
            original = "".join(pieces)
            if original != block.original_text or block.original_digest != _text_digest(original):
                _fail("STRUCTURE_PROJECTION_ORIGINAL", "Projection original body is not an anchored clean slice")
        if granularities != set(required_granularities) or not any(
            block.granularity == 0 and block.original_text.strip() for block in projection.blocks
        ):
            _fail("STRUCTURE_PROJECTION_G0_REQUIRED", "Projection granularities do not match the frozen profile")

    def construct(
        self,
        *,
        structure: StructureDocument,
        projection: RetrievalBlockProjection,
        clean_text: str,
        construction_generation_artifact_uuid: str,
        dual_channel_generation_artifact_uuid: str | None = None,
        summaries_by_block_id: Mapping[str, str],
        metadata_headers: Mapping[str, str] | None = None,
        recipe_version: str = "content_full.v1",
        required_granularities: frozenset[int] | None = None,
    ) -> tuple[ConstructionDocument, DualChannelProjection]:
        expected_granularities = required_granularities or frozenset(block.granularity for block in projection.blocks)
        self.validate_structure(
            document=structure,
            projection=projection,
            clean_text=clean_text,
            required_granularities=expected_granularities,
        )
        dual_channel_generation_artifact_uuid = dual_channel_generation_artifact_uuid or f"{construction_generation_artifact_uuid}:dual"
        if not construction_generation_artifact_uuid or not dual_channel_generation_artifact_uuid:
            _fail("CONSTRUCT_BINDING_INVALID", "Construction generation identity is required")
        if dual_channel_generation_artifact_uuid == construction_generation_artifact_uuid:
            _fail("CONSTRUCT_BINDING_INVALID", "Construction and dual-channel artifact identities must be distinct")
        units: list[ConstructionUnit] = []
        for block in projection.blocks:
            summary = summaries_by_block_id.get(block.block_id)
            if not isinstance(summary, str) or not summary.strip():
                _fail("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Every non-empty original projection block needs a grounded summary")
            coordinate = f"{structure.generation_artifact_uuid}:{projection.generation_artifact_uuid}:{block.block_id}"
            original_full = content_full(body=block.original_text, metadata_headers=metadata_headers, recipe_version=recipe_version)
            summary_full = content_full(body=summary, metadata_headers=metadata_headers, recipe_version=recipe_version)
            units.append(
                ConstructionUnit(
                    block.block_id,
                    block.granularity,
                    coordinate,
                    ChannelRecord("original", block.original_text, block.original_digest, original_full, _text_digest(original_full), coordinate, "native_full" if block.granularity == 0 else "reattached"),
                    ChannelRecord("summary", summary, _text_digest(summary), summary_full, _text_digest(summary_full), coordinate, "not_applicable"),
                )
            )
        metadata_digest = stable_digest(dict(sorted((metadata_headers or {}).items())))
        provisional = ConstructionDocument(
            construction_generation_artifact_uuid,
            structure.generation_artifact_uuid,
            projection.generation_artifact_uuid,
            structure_document_digest(structure),
            projection_digest(projection),
            tuple(units),
            metadata_digest,
            recipe_version,
            "",
        )
        proof = stable_digest({"alignment": [(unit.unit_id, unit.coordinate) for unit in units], "full_valid": True, "g0": True})
        document = ConstructionDocument(
            provisional.generation_artifact_uuid, provisional.structure_generation_artifact_uuid, provisional.projection_generation_artifact_uuid,
            provisional.structure_document_digest, provisional.projection_digest, provisional.units, provisional.metadata_projection_digest,
            provisional.content_full_recipe_version, proof,
        )
        dual = DualChannelProjection(
            dual_channel_generation_artifact_uuid,
            construction_generation_artifact_uuid,
            construction_document_digest(document),
            tuple(units),
            stable_digest({"units": [(unit.unit_id, unit.original.content_full_digest, unit.summary.content_full_digest) for unit in units]}),
        )
        self.validate_construction(document=document, dual=dual, metadata_headers=metadata_headers)
        return document, dual

    def validate_construction(self, *, document: ConstructionDocument, dual: DualChannelProjection, metadata_headers: Mapping[str, str] | None = None) -> None:
        if (
            document.generation_artifact_uuid != dual.construction_generation_artifact_uuid
            or document.generation_artifact_uuid == dual.generation_artifact_uuid
            or document.structure_generation_artifact_uuid == document.projection_generation_artifact_uuid
            or dual.construction_document_digest != construction_document_digest(document)
        ):
            _fail("CONSTRUCT_BINDING_DIGEST", "Dual-channel projection does not bind this construction document")
        if not document.units or tuple(unit.unit_id for unit in document.units) != tuple(unit.unit_id for unit in dual.units):
            _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Construction and dual-channel units must align 1:1")
        g0_original = False
        for unit in dual.units:
            if unit.original.channel != "original" or unit.summary.channel != "summary" or not unit.coordinate:
                _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Construction unit channel identities are invalid")
            for channel in (unit.original, unit.summary):
                if channel.channel not in _CHANNELS or channel.grounds_coordinate != unit.coordinate or not channel.body.strip():
                    _fail("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Construction channels must be non-empty and grounded")
                recomputed = content_full(body=channel.body, metadata_headers=metadata_headers, recipe_version=document.content_full_recipe_version)
                if recomputed != channel.content_full or channel.content_full_digest != _text_digest(recomputed):
                    _fail("CONSTRUCT_CONTENT_MISMATCH", "A content_full recipe digest does not match its channel body")
            if unit.granularity == 0 and unit.original.body.strip() and unit.original.reattach_status in {"reattached", "native_full"}:
                g0_original = True
        if not g0_original:
            _fail("CONSTRUCT_G0_ORIGINAL_REQUIRED", "Full-valid construction requires a reattached g0 original")

    def vectorization_plan(
        self,
        *,
        document: ConstructionDocument,
        dual: DualChannelProjection,
        metadata_headers: Mapping[str, str] | None = None,
        max_content_full_bytes: int = 8 * 1024 * 1024,
    ) -> VectorizationPlan:
        self.validate_construction(document=document, dual=dual, metadata_headers=metadata_headers)
        if max_content_full_bytes < 1:
            _fail("VECTORIZE_BUDGET_INVALID", "Vectorization byte budget must be positive")
        required: list[VectorizationUnit] = []
        skipped: list[str] = []
        g0_original_ready = False
        for unit in dual.units:
            for channel in (unit.original, unit.summary):
                recomputed = content_full(body=channel.body, metadata_headers=metadata_headers, recipe_version=document.content_full_recipe_version)
                if channel.content_full_digest != _text_digest(recomputed) or channel.content_full != recomputed:
                    _fail("VECTORIZE_CONTENT_MISMATCH", "Vectorization must recompute and verify content_full")
                if unit.granularity == 0 and channel.channel == "original":
                    if recomputed.strip() and unit.original.reattach_status in {"reattached", "native_full"}:
                        g0_original_ready = True
                    continue
                if not recomputed.strip():
                    skipped.append(f"{unit.unit_id}:{channel.channel}")
                    continue
                if len(recomputed.encode("utf-8")) > max_content_full_bytes:
                    _fail("VECTORIZE_BUDGET_CONTENT_FULL", "A vectorization input exceeds the configured byte budget")
                required.append(VectorizationUnit(unit.unit_id, unit.granularity, channel.channel, unit.coordinate, recomputed, _text_digest(recomputed)))
        required.sort(key=lambda item: (item.granularity, item.unit_id, item.channel))
        if not g0_original_ready:
            _fail("ORIGINAL_NOT_REATTACHED", "Vectorize requires a reattached non-empty g0 original in construct; that channel is not a vector unit")
        if not any(item.granularity == 0 and item.channel == "summary" and item.content_full.strip() for item in required):
            _fail("G0_SUMMARY_REQUIRED", "Non-empty g0 summary must remain a required vectorization unit")
        return VectorizationPlan(tuple(required), tuple(sorted(skipped)), stable_digest([item.content_full_digest for item in required]))


def construction_document_digest(document: ConstructionDocument) -> str:
    return stable_digest(
        {
            "generation": document.generation_artifact_uuid,
            "structure_generation": document.structure_generation_artifact_uuid,
            "projection_generation": document.projection_generation_artifact_uuid,
            "structure_digest": document.structure_document_digest,
            "projection_digest": document.projection_digest,
            "units": [
                (unit.unit_id, unit.granularity, unit.coordinate, unit.original.content_full_digest, unit.summary.content_full_digest)
                for unit in document.units
            ],
            "metadata": document.metadata_projection_digest,
            "recipe": document.content_full_recipe_version,
            "proof": document.proof_digest,
        }
    )


def structure_payload(document: StructureDocument) -> dict[str, object]:
    """Return deterministic JSON-ready bytes shape for a structure artifact."""

    return {
        "schema_version": "mkb.structure-document.v1",
        "generation_artifact_uuid": document.generation_artifact_uuid,
        "clean_artifact_uuid": document.clean_artifact_uuid,
        "clean_digest": document.clean_digest,
        "document_root_node_id": document.document_root_node_id,
        "nodes": [
            {
                "node_id": node.node_id,
                "node_kind": node.node_kind,
                "parent_node_id": node.parent_node_id,
                "sibling_ordinal": node.sibling_ordinal,
                "depth": node.depth,
                "reading_ordinal": node.reading_ordinal,
                "content_role": node.content_role,
                "source_anchor": None
                if node.source_anchor is None
                else {"kind": "text_span", "start_byte": node.source_anchor.start_byte, "end_byte": node.source_anchor.end_byte},
                "content_digest": node.content_digest,
                "subtree_digest": node.subtree_digest,
            }
            for node in document.nodes
        ],
        "proof_digest": document.proof_digest,
    }


def retrieval_projection_payload(projection: RetrievalBlockProjection) -> dict[str, object]:
    """Return deterministic JSON-ready bytes shape for a S06 projection artifact."""

    return {
        "schema_version": "mkb.retrieval-block-projection.v1",
        "generation_artifact_uuid": projection.generation_artifact_uuid,
        "structure_generation_artifact_uuid": projection.structure_generation_artifact_uuid,
        "structure_document_digest": projection.structure_document_digest,
        "blocks": [
            {
                "block_id": block.block_id,
                "granularity": block.granularity,
                "source_node_refs": list(block.source_node_refs),
                "ordered_source_spans": [
                    {"start_byte": span.start_byte, "end_byte": span.end_byte} for span in block.ordered_source_spans
                ],
                "original": block.original_text,
                "original_digest": block.original_digest,
            }
            for block in projection.blocks
        ],
        "proof_digest": projection.proof_digest,
    }


def construction_payload(document: ConstructionDocument) -> dict[str, object]:
    """Return deterministic JSON-ready envelope for the S07 document member."""

    return {
        "schema_version": "mkb.construction-document.v1",
        "generation_artifact_uuid": document.generation_artifact_uuid,
        "structure_generation_artifact_uuid": document.structure_generation_artifact_uuid,
        "projection_generation_artifact_uuid": document.projection_generation_artifact_uuid,
        "structure_document_digest": document.structure_document_digest,
        "projection_digest": document.projection_digest,
        "metadata_projection_digest": document.metadata_projection_digest,
        "recipe_version": document.content_full_recipe_version,
        "units": [
            {"unit_id": unit.unit_id, "granularity": unit.granularity, "coordinate": unit.coordinate}
            for unit in document.units
        ],
        "proof_digest": document.proof_digest,
    }


def dual_channel_payload(dual: DualChannelProjection) -> dict[str, object]:
    """Return the strict direct-channel shape accepted by retrieval access.

    This intentionally avoids embedding generated ``content_full`` strings in
    the retrieval hydration contract.  The vector worker receives those only
    through the typed compiler plan and verifies their recipe digest again.
    """

    return {
        "schema_version": "mkb.dual-channel-projection.v1",
        "generation_artifact_uuid": dual.generation_artifact_uuid,
        "recipe_version": "content_full.v1",
        "units": [
            {
                "unit_id": unit.unit_id,
                "granularity": unit.granularity,
                "original": unit.original.body,
                "summary": unit.summary.body,
                "original_digest": unit.original.body_digest,
                "summary_digest": unit.summary.body_digest,
            }
            for unit in dual.units
        ],
    }


def parse_structure_payload(payload: Mapping[str, object]) -> StructureDocument:
    """Parse an immutable S06 structure member without rebuilding a tree."""

    expected_keys = {
        "schema_version",
        "generation_artifact_uuid",
        "clean_artifact_uuid",
        "clean_digest",
        "document_root_node_id",
        "nodes",
        "proof_digest",
    }
    if set(payload) != expected_keys or payload.get("schema_version") != "mkb.structure-document.v1":
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure payload shape is invalid")
    nodes_raw = payload.get("nodes")
    if not isinstance(nodes_raw, list):
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure nodes are invalid")
    nodes: list[StructureNode] = []
    node_keys = {
        "node_id",
        "node_kind",
        "parent_node_id",
        "sibling_ordinal",
        "depth",
        "reading_ordinal",
        "content_role",
        "source_anchor",
        "content_digest",
        "subtree_digest",
    }
    for raw in nodes_raw:
        if not isinstance(raw, Mapping) or set(raw) != node_keys:
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure node shape is invalid")
        span_raw = raw["source_anchor"]
        span: TextSpan | None
        if span_raw is None:
            span = None
        elif isinstance(span_raw, Mapping) and set(span_raw) == {"kind", "start_byte", "end_byte"} and span_raw["kind"] == "text_span":
            span = TextSpan(int(span_raw["start_byte"]), int(span_raw["end_byte"]))
        else:
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure source anchor is invalid")
        nodes.append(
            StructureNode(
                str(raw["node_id"]),
                str(raw["node_kind"]),
                None if raw["parent_node_id"] is None else str(raw["parent_node_id"]),
                int(raw["sibling_ordinal"]),
                int(raw["depth"]),
                int(raw["reading_ordinal"]),
                str(raw["content_role"]),
                span,
                None if raw["content_digest"] is None else str(raw["content_digest"]),
                str(raw["subtree_digest"]),
            )
        )
    return StructureDocument(
        str(payload["generation_artifact_uuid"]),
        str(payload["clean_artifact_uuid"]),
        str(payload["clean_digest"]),
        str(payload["document_root_node_id"]),
        tuple(nodes),
        str(payload["proof_digest"]),
    )


def parse_retrieval_projection_payload(payload: Mapping[str, object]) -> RetrievalBlockProjection:
    """Parse an immutable S06 projection member without sentence inference."""

    expected_keys = {
        "schema_version",
        "generation_artifact_uuid",
        "structure_generation_artifact_uuid",
        "structure_document_digest",
        "blocks",
        "proof_digest",
    }
    if set(payload) != expected_keys or payload.get("schema_version") != "mkb.retrieval-block-projection.v1":
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection payload shape is invalid")
    blocks_raw = payload.get("blocks")
    if not isinstance(blocks_raw, list):
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection blocks are invalid")
    blocks: list[RetrievalBlock] = []
    block_keys = {"block_id", "granularity", "source_node_refs", "ordered_source_spans", "original", "original_digest"}
    for raw in blocks_raw:
        if not isinstance(raw, Mapping) or set(raw) != block_keys:
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection block shape is invalid")
        refs = raw["source_node_refs"]
        spans_raw = raw["ordered_source_spans"]
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs) or not isinstance(spans_raw, list):
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection references are invalid")
        spans: list[TextSpan] = []
        for span_raw in spans_raw:
            if not isinstance(span_raw, Mapping) or set(span_raw) != {"start_byte", "end_byte"}:
                _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection span shape is invalid")
            spans.append(TextSpan(int(span_raw["start_byte"]), int(span_raw["end_byte"])))
        blocks.append(
            RetrievalBlock(
                str(raw["block_id"]),
                int(raw["granularity"]),
                tuple(refs),
                tuple(spans),
                str(raw["original"]),
                str(raw["original_digest"]),
            )
        )
    return RetrievalBlockProjection(
        str(payload["generation_artifact_uuid"]),
        str(payload["structure_generation_artifact_uuid"]),
        str(payload["structure_document_digest"]),
        tuple(blocks),
        str(payload["proof_digest"]),
    )


def summary_plan(projection: RetrievalBlockProjection) -> SummaryPlan:
    """Freeze an ordered S07 plan before an inference caller fills summaries."""

    block_ids = tuple(block.block_id for block in sorted(projection.blocks, key=lambda item: (item.granularity, item.block_id)))
    if not block_ids:
        _fail("CONSTRUCT_KERNEL_EMPTY", "A summary plan requires projection blocks")
    return SummaryPlan(block_ids, stable_digest({"projection": projection_digest(projection), "blocks": block_ids}))


def deterministic_summaries(projection: RetrievalBlockProjection, *, max_chars: int = 480) -> dict[str, str]:
    """Offline deterministic summary implementation for the local profile.

    A production S07 worker normally substitutes an S11 result after freezing
    :func:`summary_plan`; this bounded fallback keeps tests and local operation
    grounded without introducing a hidden fourth prompt.
    """

    if max_chars < 1:
        _fail("CONSTRUCT_BUDGET_INVALID", "Summary character budget must be positive")
    return {
        block.block_id: block.original_text if len(block.original_text) <= max_chars else f"{block.original_text[: max_chars - 1].rstrip()}…"
        for block in projection.blocks
    }


__all__ = [
    "ChannelRecord",
    "ConstructionDocument",
    "ConstructionUnit",
    "DualChannelProjection",
    "LsragContractCompiler",
    "RetrievalBlock",
    "RetrievalBlockProjection",
    "StructureDocument",
    "StructureNode",
    "SummaryPlan",
    "TextSpan",
    "VectorizationPlan",
    "VectorizationUnit",
    "construction_document_digest",
    "construction_payload",
    "content_full",
    "deterministic_summaries",
    "dual_channel_payload",
    "projection_digest",
    "parse_retrieval_projection_payload",
    "parse_structure_payload",
    "retrieval_projection_payload",
    "structure_payload",
    "structure_document_digest",
    "summary_plan",
]
