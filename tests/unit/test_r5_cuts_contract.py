"""R5 cuts contract and validation unit tests."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.lsrag.cuts import CUTS_SCHEMA_VERSION, validate_cuts


def test_cuts_unknown_top_key_rejected() -> None:
    with pytest.raises(MkbError) as exc:
        validate_cuts(
            {
                "schema_version": CUTS_SCHEMA_VERSION,
                "cuts": [{"start": "A", "end": "B"}],
                "unknown_field": 123,
            }
        )
    assert exc.value.code == "CUTS_SCHEMA_INVALID"
    assert "unknown fields" in exc.value.message


def test_cuts_empty_rejected() -> None:
    with pytest.raises(MkbError) as exc:
        validate_cuts(
            {
                "schema_version": CUTS_SCHEMA_VERSION,
                "cuts": [],
            }
        )
    assert exc.value.code == "CUTS_EMPTY"


def test_cuts_forbidden_coordinate_keys() -> None:
    for key in (
        "span",
        "start_byte",
        "end_byte",
        "offset",
        "index",
        "body",
        "original",
        "clean",
        "layered_content",
        "block_id",
        "granularity",
    ):
        with pytest.raises(MkbError) as exc:
            validate_cuts(
                {
                    "schema_version": CUTS_SCHEMA_VERSION,
                    "cuts": [{"start": "A", "end": "B", key: "xyz"}],
                }
            )
        assert exc.value.code == "CUTS_SCHEMA_INVALID"
        assert f"forbidden field: {key}" in exc.value.message


def test_cuts_missing_start_end_rejected() -> None:
    with pytest.raises(MkbError) as exc:
        validate_cuts(
            {
                "schema_version": CUTS_SCHEMA_VERSION,
                "cuts": [{"title": "T"}],
            }
        )
    assert exc.value.code == "CUTS_SCHEMA_INVALID"


def test_cuts_wrong_schema_version_rejected() -> None:
    with pytest.raises(MkbError) as exc:
        validate_cuts(
            {
                "schema_version": "invalid.v1",
                "cuts": [{"start": "A", "end": "B"}],
            }
        )
    assert exc.value.code == "CUTS_SCHEMA_INVALID"


def test_cuts_valid_accepts() -> None:
    res = validate_cuts(
        {
            "schema_version": CUTS_SCHEMA_VERSION,
            "cuts": [{"title": "Chapter 1", "start": "Start here", "end": "End here"}],
        }
    )
    assert res["schema_version"] == CUTS_SCHEMA_VERSION
    assert len(res["cuts"]) == 1
    assert res["cuts"][0]["title"] == "Chapter 1"


def test_cuts_null_title_allowed() -> None:
    res = validate_cuts(
        {
            "schema_version": CUTS_SCHEMA_VERSION,
            "cuts": [{"title": None, "start": "Start", "end": "End"}],
        }
    )
    assert res["cuts"][0]["title"] is None


def test_cuts_context_meta_optional_object() -> None:
    res = validate_cuts(
        {
            "schema_version": CUTS_SCHEMA_VERSION,
            "cuts": [{"start": "Start", "end": "End"}],
            "context_meta": {"tag": "test"},
        }
    )
    assert res["context_meta"] == {"tag": "test"}
