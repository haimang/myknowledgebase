"""Deterministic, fail-closed S06--S08 content contracts.

This package deliberately has no persistence or workflow dependency.  It is the
small kernel used by a worker to turn a selected clean artifact into the three
generation-local artifact shapes.  Persisting bytes, accepting generation
pointers, invoking a model, and writing vectors remain concerns of S06/S07/S08
workers respectively.
"""

from src.services.lsrag_compiler.compiler import LsragContractCompiler
from src.services.lsrag_compiler.models import (
    ChannelRecord,
    ConstructionDocument,
    ConstructionUnit,
    DualChannelProjection,
    RetrievalBlock,
    RetrievalBlockProjection,
    StructureDocument,
    StructureNode,
    SummaryPlan,
    TextSpan,
    VectorizationPlan,
    VectorizationUnit,
    content_full,
)
from src.services.lsrag_compiler.payloads import (
    construction_document_digest,
    construction_payload,
    deterministic_summaries,
    dual_channel_payload,
    parse_retrieval_projection_payload,
    parse_structure_payload,
    projection_digest,
    retrieval_projection_payload,
    structure_document_digest,
    structure_payload,
    summary_plan,
)

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
