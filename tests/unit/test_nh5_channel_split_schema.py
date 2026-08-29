"""NH5-T05/T06: retrieval vector and business channel axes are versioned."""

from __future__ import annotations

import pytest

from src.contracts.api.models import parse_retrieval_request
from src.contracts.common.errors import MkbError
from src.services.retrieval import RetrievalService


def _request(schema: str, filters: dict) -> dict:
    return {
        "schema_version": schema,
        "team_uuid": "11111111-1111-4111-8111-111111111111",
        "namespace_key": "deterministic|v1|64",
        "query": "query",
        "filters": filters,
    }


def test_new_schema_accepts_semantic_and_vector_channel_together() -> None:
    request = parse_retrieval_request(
        _request(
            "mkb.retrieval.v2",
            {"semantic_channel": "sold", "vector_channel": "summary", "realm": "realestate"},
        )
    )
    normalized = RetrievalService(None)._normalise_request(request)  # type: ignore[arg-type]  # noqa: SLF001
    assert normalized.filters == {
        "semantic_channel": "sold",
        "vector_channel": "summary",
        "realm": "realestate",
    }


@pytest.mark.parametrize("channel", ["original", "summary"])
def test_v1_channel_maps_only_to_vector_channel(channel: str) -> None:
    request = parse_retrieval_request(_request("mkb.retrieval.v1", {"channel": channel}))
    normalized = RetrievalService(None)._normalise_request(request)  # type: ignore[arg-type]  # noqa: SLF001
    assert normalized.filters == {"vector_channel": channel}
    assert normalized.legacy_channel_used is True


def test_v1_business_channel_and_v2_legacy_key_are_rejected() -> None:
    v1 = parse_retrieval_request(_request("mkb.retrieval.v1", {"channel": "sold"}))
    with pytest.raises(MkbError) as raised:
        RetrievalService(None)._normalise_request(v1)  # type: ignore[arg-type]  # noqa: SLF001
    assert raised.value.code == "RETRIEVE_FILTER_INVALID"
    with pytest.raises(MkbError) as raised:
        parse_retrieval_request(_request("mkb.retrieval.v2", {"channel": "summary"}))
    assert raised.value.code == "RETRIEVE_FILTER_INVALID"
