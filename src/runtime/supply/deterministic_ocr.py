"""Network-denied deterministic OCR capability and typed failure surface."""

from __future__ import annotations

import asyncio
import hashlib
import os
import pwd
import shutil
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

from src.contracts.common.errors import MkbError
from src.runtime.inference.facade import ConcurrencyGate
from src.runtime.supply.glyph_ocr_worker import render_fixture_pdf, render_fixture_png


@dataclass(frozen=True, slots=True)
class DeterministicOcrResult:
    text: str
    engine_identity: str
    engine_version: str
    media_type: str

    def evidence(self) -> dict[str, object]:
        return {
            "producer": self.engine_identity,
            "producer_version": self.engine_version,
            "media_type": self.media_type,
            "execution_boundary": "isolated_no_network_subprocess",
            "prompt_ref": None,
        }


class IsolatedDeterministicOcr:
    def __init__(
        self,
        *,
        python_binary: Path,
        worker_path: Path,
        pdftoppm_binary: Path,
        unshare_binary: Path,
        prlimit_binary: Path,
        setpriv_binary: Path,
        gate: ConcurrencyGate,
        timeout_seconds: float = 10,
        max_input_bytes: int = 32 * 1024 * 1024,
        max_output_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        self.python_binary = python_binary
        self.worker_path = worker_path
        self.pdftoppm_binary = pdftoppm_binary
        self.unshare_binary = unshare_binary
        self.prlimit_binary = prlimit_binary
        self.setpriv_binary = setpriv_binary
        self._gate = gate
        self.timeout_seconds = float(timeout_seconds)
        self.max_input_bytes = int(max_input_bytes)
        self.max_output_bytes = int(max_output_bytes)
        self.engine_identity = "ocr.deterministic.glyph5x7.v1"
        self.engine_version = hashlib.sha256(worker_path.read_bytes()).hexdigest()
        self.active_pids: set[int] = set()
        self.last_pid: int | None = None
        self.invocation_count = 0

    @classmethod
    def discover(
        cls,
        *,
        gate: ConcurrencyGate,
        timeout_seconds: float = 10,
    ) -> IsolatedDeterministicOcr:
        return cls(
            python_binary=Path(sys.executable),
            worker_path=Path(__file__).with_name("glyph_ocr_worker.py"),
            pdftoppm_binary=_binary("pdftoppm"),
            unshare_binary=_binary("unshare"),
            prlimit_binary=_binary("prlimit"),
            setpriv_binary=_binary("setpriv"),
            gate=gate,
            timeout_seconds=timeout_seconds,
        )

    def command(self, media_type: str) -> tuple[str, ...]:
        command: list[str] = [str(self.unshare_binary)]
        if os.geteuid() != 0:
            command.extend(("-U", "--map-root-user"))
        command.extend(
            (
                "--net",
                "--",
                str(self.prlimit_binary),
            )
        )
        command.extend(
            (
                "--as=536870912",
                "--cpu=8",
                "--nofile=64",
                f"--fsize={self.max_output_bytes}",
                "--",
            )
        )
        if os.geteuid() == 0:
            account = pwd.getpwnam("nobody")
            command.extend(
                (
                    str(self.setpriv_binary),
                    f"--reuid={account.pw_uid}",
                    f"--regid={account.pw_gid}",
                    "--clear-groups",
                )
            )
        command.extend(
            (
                str(self.python_binary),
                "-I",
                str(self.worker_path),
                media_type,
                str(self.pdftoppm_binary),
            )
        )
        return tuple(command)

    async def recognize(self, blob: bytes, *, media_type: str) -> DeterministicOcrResult:
        if not blob:
            raise MkbError("OCR_INPUT_EMPTY", "Deterministic OCR input is empty", 422)
        if len(blob) > self.max_input_bytes:
            raise MkbError("OCR_INPUT_LIMIT", "Deterministic OCR input exceeded its cap", 413)
        if media_type not in {"image/png", "application/pdf"}:
            raise MkbError("OCR_MEDIA_UNSUPPORTED", "Deterministic OCR media type is unsupported", 422)
        lease = await self._gate.try_acquire("ocr.deterministic")
        if lease is None:
            raise MkbError("INFERENCE_BACKPRESSURE", "Deterministic OCR concurrency gate is full", 503)
        self.invocation_count += 1
        try:
            try:
                process = await asyncio.create_subprocess_exec(
                    *self.command(media_type),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={
                        "PATH": "/usr/bin:/bin",
                        "LANG": "C.UTF-8",
                        "LC_ALL": "C.UTF-8",
                        "http_proxy": "",
                        "https_proxy": "",
                        "HTTP_PROXY": "",
                        "HTTPS_PROXY": "",
                        "ALL_PROXY": "",
                        "NO_PROXY": "",
                    },
                    start_new_session=True,
                )
            except OSError as exc:
                raise MkbError("OCR_CAPABILITY_UNAVAILABLE", "Deterministic OCR process could not start", 503) from exc
            self.last_pid = process.pid
            self.active_pids.add(process.pid)
            try:
                try:
                    stdout, _stderr = await asyncio.wait_for(process.communicate(blob), timeout=self.timeout_seconds)
                except TimeoutError as exc:
                    await _terminate_process(process)
                    await process.communicate()
                    raise MkbError("OCR_TIMEOUT", "Deterministic OCR exceeded its deadline", 422) from exc
            finally:
                self.active_pids.discard(process.pid)
            if len(stdout) > self.max_output_bytes or process.returncode in {
                -signal.SIGXFSZ,
                128 + signal.SIGXFSZ,
            }:
                raise MkbError("OCR_OUTPUT_LIMIT", "Deterministic OCR output exceeded its cap", 422)
            if process.returncode == 3:
                raise MkbError("OCR_EMPTY", "Deterministic OCR found no admissible text", 422)
            if process.returncode != 0:
                raise MkbError("OCR_INPUT_INVALID", "Deterministic OCR rejected the media", 422)
            try:
                text = stdout.decode("utf-8", errors="strict").strip()
            except UnicodeDecodeError as exc:
                raise MkbError("OCR_OUTPUT_INVALID", "Deterministic OCR returned invalid text", 502) from exc
            if not text:
                raise MkbError("OCR_EMPTY", "Deterministic OCR found no admissible text", 422)
            return DeterministicOcrResult(
                text=text,
                engine_identity=self.engine_identity,
                engine_version=self.engine_version,
                media_type=media_type,
            )
        finally:
            await self._gate.release(lease)

    async def readiness(self) -> bool:
        try:
            result = await self.recognize(render_fixture_png("MKB OCR"), media_type="image/png")
            pdf_result = await self.recognize(render_fixture_pdf("PDF OCR"), media_type="application/pdf")
            try:
                await self.recognize(render_fixture_png(" "), media_type="image/png")
            except MkbError as negative:
                negative_ok = negative.code == "OCR_EMPTY"
            else:
                negative_ok = False
            return (
                result.text == "MKB OCR"
                and pdf_result.text == "PDF OCR"
                and not result.evidence()["prompt_ref"]
                and negative_ok
            )
        except Exception:
            return False


def _binary(name: str) -> Path:
    value = shutil.which(name)
    if value is None:
        raise MkbError("SUPPLY_BINARY_MISSING", f"Required runtime supply is unavailable: {name}", 503)
    return Path(value)


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


__all__ = [
    "DeterministicOcrResult",
    "IsolatedDeterministicOcr",
    "render_fixture_pdf",
    "render_fixture_png",
]
