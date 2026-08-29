"""NH3-T02: byte signatures stay distinct from declared media labels."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.intake.types import _sniff_media_type, _verified_media_type


def test_zip_and_opc_never_become_plain_text() -> None:
    payload = b"PK\x03\x04word/document.xml plain-ascii-tail"
    assert _sniff_media_type(payload) == "application/zip"
    assert (
        _verified_media_type(
            declared="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            detected="application/zip",
        )
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    pipeline = IntakePipeline(None, None, None)  # type: ignore[arg-type]
    acquired = pipeline._representation_from_bytes(  # noqa: SLF001
        payload,
        declared_media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        capability="intake.acquire.local_object",
        source_kind="local_object",
        mode="logical_object",
    )
    assert acquired.is_binary
    assert acquired.media_type.endswith("wordprocessingml.document")
    assert acquired.evidence["declared_media_type"] == acquired.media_type
    assert acquired.evidence["detected_media_type"] == "application/zip"


def test_opaque_high_bytes_do_not_pass_utf8_text_decode() -> None:
    pipeline = IntakePipeline(None, None, None)  # type: ignore[arg-type]
    acquired = pipeline._representation_from_bytes(  # noqa: SLF001
        b"\xd0\xcf\x11\xe0opaque-office",
        declared_media_type="application/msword",
        capability="intake.acquire.local_object",
        source_kind="local_object",
        mode="logical_object",
    )
    assert acquired.is_binary
    assert acquired.media_type == "application/msword"
    assert acquired.evidence["detected_media_type"] == "application/octet-stream"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b'{"b":2,"a":1}', "application/json"),
        (b"<!doctype html><main>x</main>", "text/html"),
        ("plain café".encode(), "text/plain"),
    ],
)
def test_naked_utf8_families_remain_text(payload: bytes, expected: str) -> None:
    assert _sniff_media_type(payload) == expected


@pytest.mark.parametrize(
    ("declared", "detected"),
    [
        ("application/pdf", "text/plain"),
        ("image/png", "image/jpeg"),
    ],
)
def test_critical_declared_media_lies_fail_closed(declared: str, detected: str) -> None:
    with pytest.raises(MkbError) as raised:
        _verified_media_type(declared=declared, detected=detected)
    assert raised.value.code == "ACQUISITION_MEDIA_MISMATCH"
    assert raised.value.status_code == 422
