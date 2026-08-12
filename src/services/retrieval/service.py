"""RetrievalService composition root."""

from __future__ import annotations

from src.services.retrieval.retrieval_pack import RetrievalPackMixin
from src.services.retrieval.retrieval_rank import RetrievalRankMixin
from src.services.retrieval.retrieval_request import RetrievalRequestMixin


class RetrievalService(
    RetrievalRequestMixin,
    RetrievalRankMixin,
    RetrievalPackMixin,
):
    """RetrievalService facade."""
