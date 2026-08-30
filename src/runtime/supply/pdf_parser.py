"""Isolated, network-denied PDF text-layer supply."""

from __future__ import annotations

import asyncio
import os
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from src.contracts.common.errors import MkbError
from src.runtime.inference.facade import ConcurrencyGate


@dataclass(frozen=True, slots=True)
class PdfParseResult:
    text: str
    text_layer: str
    parser_identity: str
    parser_version: str
    page_count_hint: int | None = None

    def evidence(self) -> dict[str, object]:
        return {
            "decoder": self.parser_identity,
            "observer_version": self.parser_version,
            "canonicalizer": "utf8-lf-nfc.v1",
            "text_layer": self.text_layer,
            "page_count_hint": self.page_count_hint,
        }


class IsolatedPdfParser:
    def __init__(
        self,
        *,
        parser_binary: Path,
        unshare_binary: Path,
        prlimit_binary: Path,
        setpriv_binary: Path,
        timeout_seconds: float = 8,
        max_input_bytes: int = 64 * 1024 * 1024,
        max_output_bytes: int = 8 * 1024 * 1024,
        gate: ConcurrencyGate | None = None,
    ) -> None:
        self.parser_binary = parser_binary
        self.unshare_binary = unshare_binary
        self.prlimit_binary = prlimit_binary
        self.setpriv_binary = setpriv_binary
        self.timeout_seconds = timeout_seconds
        self.max_input_bytes = max_input_bytes
        self.max_output_bytes = max_output_bytes
        self.parser_version = _version(parser_binary)
        self._gate = gate
        self.active_pids: set[int] = set()
        self.last_pid: int | None = None
        self.subprocess_call_count = 0

    @classmethod
    def discover(
        cls,
        *,
        parser_binary: Path | None = None,
        timeout_seconds: float = 8,
        gate: ConcurrencyGate | None = None,
    ) -> IsolatedPdfParser:
        return cls(
            parser_binary=parser_binary or _binary("pdftotext"),
            unshare_binary=_binary("unshare"),
            prlimit_binary=_binary("prlimit"),
            setpriv_binary=_binary("setpriv"),
            timeout_seconds=timeout_seconds,
            gate=gate,
        )

    def isolation_prefix(self, *, output_limit: int | None = None) -> tuple[str, ...]:
        prefix: list[str] = [str(self.unshare_binary), "--net", "--", str(self.prlimit_binary)]
        prefix.extend(("--as=536870912", "--cpu=5", "--nofile=64"))
        if output_limit is not None:
            prefix.append(f"--fsize={output_limit}")
        prefix.append("--")
        if os.geteuid() == 0:
            nobody = pwd.getpwnam("nobody")
            prefix.extend(
                (
                    str(self.setpriv_binary),
                    f"--reuid={nobody.pw_uid}",
                    f"--regid={nobody.pw_gid}",
                    "--clear-groups",
                )
            )
        return tuple(prefix)

    def command(self) -> tuple[str, ...]:
        prefix = list(self.isolation_prefix(output_limit=self.max_output_bytes))
        prefix.extend((str(self.parser_binary), "-enc", "UTF-8", "-", "-"))
        return tuple(prefix)

    async def parse(self, pdf_bytes: bytes) -> PdfParseResult:
        lease = None
        if self._gate is not None:
            lease = await self._gate.try_acquire("pdf.parse")
            if lease is None:
                raise MkbError("INFERENCE_BACKPRESSURE", "PDF parser concurrency gate is full", 503)
        try:
            return await self._parse_with_process(pdf_bytes)
        finally:
            if lease is not None:
                await self._gate.release(lease)

    async def _parse_with_process(self, pdf_bytes: bytes) -> PdfParseResult:
        if not pdf_bytes.startswith(b"%PDF-"):
            return self._result("", "corrupt")
        if len(pdf_bytes) > self.max_input_bytes:
            raise MkbError("PDF_PARSE_INPUT_LIMIT", "PDF parser input exceeded its configured cap", 413)
        with tempfile.TemporaryDirectory(prefix="mkb-pdf-parse-") as root_value:
            root = Path(root_value)
            _prepare_run_root(root)
            output_path = root / "stdout.txt"
            diagnostic_path = root / "stderr.txt"
            environment = {
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "HOME": str(root),
                "TMPDIR": str(root),
                "http_proxy": "",
                "https_proxy": "",
                "HTTP_PROXY": "",
                "HTTPS_PROXY": "",
                "ALL_PROXY": "",
                "NO_PROXY": "",
            }
            try:
                with output_path.open("w+b") as output, diagnostic_path.open("w+b") as diagnostic_output:
                    self.subprocess_call_count += 1
                    process = await asyncio.create_subprocess_exec(
                        *self.command(),
                        stdin=asyncio.subprocess.PIPE,
                        stdout=output,
                        stderr=diagnostic_output,
                        env=environment,
                        start_new_session=True,
                    )
                    self.last_pid = process.pid
                    self.active_pids.add(process.pid)
                    try:
                        await asyncio.wait_for(process.communicate(pdf_bytes), timeout=self.timeout_seconds)
                    except TimeoutError as exc:
                        await _terminate_process(process)
                        await process.communicate()
                        raise MkbError("PDF_PARSE_TIMEOUT", "Isolated PDF parser exceeded its deadline", 422) from exc
                    finally:
                        self.active_pids.discard(process.pid)
                    output.flush()
                    observed_output = output.tell()
                    output.seek(0)
                    stdout = output.read(self.max_output_bytes + 1)
                    diagnostic_output.flush()
                    observed_diagnostic = diagnostic_output.tell()
                    diagnostic_output.seek(0)
                    stderr = diagnostic_output.read(1024 * 1024 + 1)
            except OSError as exc:
                raise MkbError(
                    "PDF_PARSE_CAPABILITY_UNAVAILABLE",
                    "Isolated PDF parser could not start",
                    503,
                ) from exc
        if (
            observed_output >= self.max_output_bytes
            or len(stdout) > self.max_output_bytes
            or observed_diagnostic > 1024 * 1024
            or len(stderr) > 1024 * 1024
            or process.returncode in {-signal.SIGXFSZ, 128 + signal.SIGXFSZ}
        ):
            raise MkbError("PDF_PARSE_OUTPUT_LIMIT", "PDF parser output exceeded its configured cap", 422)
        diagnostic = stderr.decode("utf-8", errors="replace").casefold()
        if "password" in diagnostic or "encrypted" in diagnostic or b"/Encrypt" in pdf_bytes:
            return self._result("", "encrypted")
        if process.returncode != 0:
            return self._result("", "corrupt")
        try:
            text = stdout.decode("utf-8", errors="strict").replace("\f", "").strip()
        except UnicodeDecodeError:
            return self._result("", "corrupt")
        return self._result(text, "present" if text else "absent")

    async def readiness(self) -> bool:
        try:
            result = await self.parse(build_compressed_pdf_fixture("MKB PDF parser readiness"))
            negative = await self.parse(b"%PDF-1.7\n1 0 obj << /Encrypt 2 0 R >> endobj\n%%EOF")
            isolation = await self.isolation_probe()
            return (
                result.text_layer == "present"
                and "MKB PDF parser readiness" in result.text
                and negative.text_layer == "encrypted"
                and isolation["network_denied"] is True
            )
        except Exception:
            return False

    async def isolation_probe(self) -> dict[str, object]:
        """Prove that the exact parser sandbox cannot reach a host listener."""

        script = (
            "import socket,sys; s=socket.socket(); s.settimeout(0.5); "
            "r=s.connect_ex(('127.0.0.1',9)); sys.stdout.write('denied' if r else 'connected')"
        )
        command = (*self.isolation_prefix(output_limit=4096), sys.executable, "-I", "-c", script)
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                start_new_session=True,
            )
            self.last_pid = process.pid
            self.active_pids.add(process.pid)
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=min(self.timeout_seconds, 3))
            except TimeoutError:
                await _terminate_process(process)
                await process.communicate()
                return {"network_denied": False, "reason": "probe_timeout"}
            finally:
                self.active_pids.discard(process.pid)
        except OSError:
            return {"network_denied": False, "reason": "probe_unavailable"}
        return {
            "network_denied": process.returncode == 0 and stdout == b"denied",
            "namespace": "new_network_namespace",
            "uid": pwd.getpwnam("nobody").pw_uid if os.geteuid() == 0 else os.geteuid(),
        }

    def _result(self, text: str, text_layer: str) -> PdfParseResult:
        return PdfParseResult(
            text=text,
            text_layer=text_layer,
            parser_identity="pdf.parse.v1",
            parser_version=self.parser_version,
        )


def build_compressed_pdf_fixture(text: str) -> bytes:
    """Build a deterministic one-page Flate-compressed PDF test/probe fixture."""

    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 18 Tf 72 720 Td ({safe}) Tj ET".encode("latin-1")
    compressed = zlib.compress(stream)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(compressed)).encode()
        + b" /Filter /FlateDecode >>\nstream\n"
        + compressed
        + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for ordinal, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{ordinal} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _binary(name: str) -> Path:
    value = shutil.which(name)
    if value is None:
        raise MkbError("SUPPLY_BINARY_MISSING", f"Required runtime supply is unavailable: {name}", 503)
    return Path(value)


def _prepare_run_root(root: Path) -> None:
    root.chmod(0o700)
    if os.geteuid() == 0:
        nobody = pwd.getpwnam("nobody")
        os.chown(root, nobody.pw_uid, nobody.pw_gid)


async def _terminate_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=1)
    except TimeoutError:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


def _version(binary: Path) -> str:
    for flag in ("-v", "--version"):
        try:
            result = subprocess.run(
                (str(binary), flag),
                capture_output=True,
                check=False,
                timeout=3,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = "\n".join((result.stdout, result.stderr))
        line = next((line.strip() for line in output.splitlines() if line.strip()), "")
        if line:
            return line[:128]
    return "version-unavailable"


__all__ = ["IsolatedPdfParser", "PdfParseResult", "build_compressed_pdf_fixture"]
