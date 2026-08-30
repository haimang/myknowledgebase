"""NH6-T07 L2: real OCR port failures never become admitted clean."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from intake.doc import clean_document
from src.contracts.common.errors import MkbError
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.inference.facade import ConcurrencyGate
from src.runtime.supply.deterministic_ocr import (
    IsolatedDeterministicOcr,
    render_fixture_pdf,
    render_fixture_png,
)


class _SleepingOcr(IsolatedDeterministicOcr):
    def command(self, media_type: str) -> tuple[str, ...]:
        del media_type
        return (sys.executable, "-I", "-c", "import time; time.sleep(30)")


@pytest.mark.asyncio
async def test_empty_bad_timeout_typed_fail_zero_admitted_clean(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "nh6-ocr.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    gate = ConcurrencyGate(4, capability_limits={"ocr.deterministic": 2})
    ocr = IsolatedDeterministicOcr.discover(gate=gate)
    try:
        successful = await clean_document(
            blob=render_fixture_png("MKB OCR 2026"),
            media_type="image/png",
            capability="clean.ocr.local",
            ocr=ocr,
        )
        assert successful.text == "MKB OCR 2026"
        assert successful.evidence["prompt_ref"] is None
        pdf_success = await ocr.recognize(render_fixture_pdf("PDF OCR"), media_type="application/pdf")
        assert pdf_success.text == "PDF OCR"

        errors: list[str] = []
        for blob in (render_fixture_png(" "), b"bad-png"):
            with pytest.raises(MkbError) as raised:
                await clean_document(
                    blob=blob,
                    media_type="image/png",
                    capability="clean.ocr.local",
                    ocr=ocr,
                )
            errors.append(raised.value.code)
        assert errors == ["OCR_EMPTY", "OCR_INPUT_INVALID"]

        sleeping = _SleepingOcr(
            python_binary=ocr.python_binary,
            worker_path=ocr.worker_path,
            pdftoppm_binary=ocr.pdftoppm_binary,
            unshare_binary=ocr.unshare_binary,
            prlimit_binary=ocr.prlimit_binary,
            setpriv_binary=ocr.setpriv_binary,
            gate=gate,
            timeout_seconds=0.1,
        )
        with pytest.raises(MkbError) as timed:
            await clean_document(
                blob=render_fixture_png("TIMEOUT"),
                media_type="image/png",
                capability="clean.ocr.local",
                ocr=sleeping,
            )
        assert timed.value.code == "OCR_TIMEOUT"

        async with persistence.transaction() as tx:
            admitted = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_intake_candidate_sets WHERE admission_result='auto_admitted'"
            )
        assert admitted == {"count": 0}
    finally:
        await persistence.close()
