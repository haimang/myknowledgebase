"""NH5-T07 L2: semantic facets constrain SQL candidates before LIMIT/rank."""

from __future__ import annotations

import inspect

import pytest

from src.services.retrieval import RetrievalService
from src.services.retrieval.models import _SearchInput


class _Tx:
    def __init__(self) -> None:
        self.sql = ""
        self.params: tuple = ()

    async def fetchall(self, sql: str, params: tuple):
        self.sql = sql
        self.params = params
        return []


@pytest.mark.asyncio
async def test_facet_predicates_are_in_candidate_sql_before_limit() -> None:
    service = RetrievalService(None)  # type: ignore[arg-type]
    tx = _Tx()
    query = _SearchInput(
        team_uuid="11111111-1111-4111-8111-111111111111",
        query="query",
        namespace_key="namespace",
        namespace_uuid=None,
        return_k=3,
        recall_k=10,
        threshold=0.0,
        filters={"realm": "alpha", "semantic_channel": "policy", "vector_channel": "summary"},
        include_pack=True,
        schema_version="mkb.retrieval.v2",
    )
    await service._fetch_candidate_rows(  # noqa: SLF001
        tx,  # type: ignore[arg-type]
        {"namespace_uuid": "22222222-2222-4222-8222-222222222222"},
        query,
    )
    where_at = tx.sql.index("WHERE")
    limit_at = tx.sql.index("LIMIT")
    assert where_at < tx.sql.index("mkb_vector_record_facets") < limit_at
    assert tx.sql.count("EXISTS (SELECT 1 FROM mkb_vector_record_facets") == 2
    assert "r.channel=?" in tx.sql
    assert "realm" in tx.params and "alpha" in tx.params
    assert "channel" in tx.params and "policy" in tx.params
    assert "summary" in tx.params


def test_rank_path_has_no_python_semantic_postfilter() -> None:
    source = inspect.getsource(RetrievalService._rank_ann_candidates)
    assert "realm" not in source
    assert "semantic_channel" not in source
    assert "facet" not in source
