"""NH6-T02: parser network/resource isolation and API survival."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.errors import MkbError
from src.runtime.supply.pdf_parser import IsolatedPdfParser, build_compressed_pdf_fixture
from tests.local_runtime import local_mock_settings


class _SleepingParser(IsolatedPdfParser):
    def command(self) -> tuple[str, ...]:
        return (
            *self.isolation_prefix(output_limit=self.max_output_bytes),
            sys.executable,
            "-I",
            "-c",
            "import time; time.sleep(30)",
        )


@pytest.mark.asyncio
async def test_parser_subprocess_has_no_network() -> None:
    parser = IsolatedPdfParser.discover()
    proof = await parser.isolation_probe()
    assert proof == {
        "network_denied": True,
        "namespace": "new_network_namespace",
        "uid": proof["uid"],
    }
    assert proof["uid"] != 0
    command = parser.command()
    assert "--net" in command
    assert not any("proxy" in argument.casefold() for argument in command)


@pytest.mark.asyncio
async def test_resource_kill_on_timeout() -> None:
    discovered = IsolatedPdfParser.discover(timeout_seconds=0.1)
    parser = _SleepingParser(
        parser_binary=discovered.parser_binary,
        unshare_binary=discovered.unshare_binary,
        prlimit_binary=discovered.prlimit_binary,
        setpriv_binary=discovered.setpriv_binary,
        timeout_seconds=0.1,
    )
    with pytest.raises(MkbError) as raised:
        await parser.parse(build_compressed_pdf_fixture("timeout"))
    assert raised.value.code == "PDF_PARSE_TIMEOUT"
    assert parser.active_pids == set()
    assert parser.last_pid is not None
    assert not Path(f"/proc/{parser.last_pid}").exists()


def test_malicious_pdf_does_not_kill_api(tmp_path: Path) -> None:
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token="nh6-parser-survival",
        )
    )
    parser = app.state.container.pdf_parser
    assert isinstance(parser, IsolatedPdfParser)
    api_pid = os.getpid()
    malformed = b"%PDF-1.7\n" + (b"1 0 obj << /Kids [1 0 R] >> endobj\n" * 20_000) + b"%%EOF"
    result = asyncio.run(parser.parse(malformed))
    assert result.text_layer in {"absent", "corrupt"}
    assert os.getpid() == api_pid
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json() == {"status": "live", "live": True}
