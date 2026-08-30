"""SPIKE-ONLY local runtime feasibility slice for AP-NH1.

AP-NH6 owns production adapters, readiness, configuration, and supply-chain
policy.  This module proves that the current host can run bounded real
processes without adding a production Python dependency or freezing a library
choice as owner truth.
"""

from __future__ import annotations

import base64
import os
import pwd
import resource
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import httpx
from pydantic import Field, model_validator

from src.contracts.common.errors import MkbError
from src.contracts.common.models import StrictModel

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Nh1MultimodalProbeRequest(StrictModel):
    prompt_ref: Annotated[str, Field(min_length=1, max_length=256)]
    prompt_digest: Digest
    model_key: Annotated[str, Field(min_length=1, max_length=256)]
    model_version: Annotated[str, Field(min_length=1, max_length=128)]
    media_type: Annotated[str, Field(pattern=r"^(application/pdf|image/[a-z0-9.+-]+)$")]
    content_digest: Digest
    media_bytes: bytes | None = Field(default=None, max_length=20 * 1024 * 1024)
    object_handle: Annotated[str | None, Field(default=None, pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]

    @model_validator(mode="after")
    def require_exact_media_coordinate(self) -> Nh1MultimodalProbeRequest:
        if (self.media_bytes is None) == (self.object_handle is None):
            raise ValueError("exactly one of media_bytes or object_handle is required")
        if self.media_bytes is not None and not self.media_bytes:
            raise ValueError("media_bytes must not be empty")
        return self


@dataclass(frozen=True, slots=True)
class BrowserPrintSmoke:
    rendered_dom: str
    pdf_bytes: bytes
    browser_profile: str
    browser_uid: int
    driver_uid: int
    launch_args: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Nh1RuntimeSpike:
    pdf_text_binary: Path
    browser_binary: Path
    webdriver_binary: Path
    fixture_pdf_binary: Path
    unshare_binary: Path
    prlimit_binary: Path
    setpriv_binary: Path

    @classmethod
    def discover(cls) -> Nh1RuntimeSpike:
        direct_firefox = Path("/snap/firefox/current/usr/lib/firefox/firefox")
        direct_driver = Path("/snap/firefox/current/usr/lib/firefox/geckodriver")
        return cls(
            pdf_text_binary=_required_binary("pdftotext"),
            browser_binary=direct_firefox if direct_firefox.is_file() else _required_binary("firefox"),
            webdriver_binary=direct_driver if direct_driver.is_file() else _required_binary("geckodriver"),
            fixture_pdf_binary=_required_binary("gs"),
            unshare_binary=_required_binary("unshare"),
            prlimit_binary=_required_binary("prlimit"),
            setpriv_binary=_required_binary("setpriv"),
        )

    def extract_pdf_text(self, pdf_bytes: bytes, *, timeout_seconds: float = 8) -> str:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise MkbError("NH1_PDF_INVALID", "PDF input lacks a valid header", 422)
        nobody = pwd.getpwnam("nobody")
        command = [
            str(self.unshare_binary),
            "--net",
            "--",
            str(self.prlimit_binary),
            "--as=536870912",
            "--cpu=5",
            "--nofile=64",
            "--",
            str(self.setpriv_binary),
            f"--reuid={nobody.pw_uid}",
            f"--regid={nobody.pw_gid}",
            "--clear-groups",
            str(self.pdf_text_binary),
            "-enc",
            "UTF-8",
            "-",
            "-",
        ]
        try:
            completed = subprocess.run(
                command,
                input=pdf_bytes,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise MkbError("NH1_PDF_TIMEOUT", "Isolated PDF parser exceeded its deadline", 422) from exc
        stderr = completed.stderr.decode("utf-8", errors="replace")
        lowered = stderr.casefold()
        if "password" in lowered or "encrypted" in lowered:
            raise MkbError("NH1_PDF_ENCRYPTED", "Encrypted PDF cannot be read without credentials", 422)
        if completed.returncode != 0:
            raise MkbError("NH1_PDF_INVALID", "Isolated PDF parser rejected the input", 422)
        if len(completed.stdout) > 8 * 1024 * 1024:
            raise MkbError("NH1_PDF_OUTPUT_LIMIT", "Isolated PDF parser exceeded its output cap", 422)
        text = completed.stdout.decode("utf-8", errors="strict").strip()
        if not text:
            raise MkbError("NH1_PDF_TEXT_LAYER_ABSENT", "PDF has no observable text layer", 422)
        return text

    def render_spa_and_print(self, *, marker: str, timeout_seconds: float = 20) -> BrowserPrintSmoke:
        nobody = pwd.getpwnam("nobody")
        run_root = Path(tempfile.mkdtemp(prefix="nh1-browser-"))
        run_root.chmod(0o777)
        port = _available_port()
        command = (
            str(self.webdriver_binary),
            "--binary",
            str(self.browser_binary),
            "--port",
            str(port),
            "--log",
            "error",
        )
        environment = {
            **os.environ,
            "HOME": str(run_root),
            "XDG_RUNTIME_DIR": str(run_root),
            "MOZ_CRASHREPORTER_DISABLE": "1",
        }
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            start_new_session=True,
            preexec_fn=lambda: _drop_privileges(nobody.pw_uid, nobody.pw_gid),
        )
        session_id: str | None = None
        browser_pid: int | None = None
        endpoint = f"http://127.0.0.1:{port}"
        try:
            with httpx.Client(base_url=endpoint, timeout=timeout_seconds, trust_env=False) as client:
                _wait_for_webdriver(client, process, timeout_seconds)
                created = client.post(
                    "/session",
                    json={
                        "capabilities": {
                            "alwaysMatch": {
                                "browserName": "firefox",
                                "moz:firefoxOptions": {
                                    "args": ["-headless"],
                                    "prefs": {
                                        "font.language.group": "x-western",
                                        "font.name.serif.x-western": "DejaVu Serif",
                                        "font.name.sans-serif.x-western": "DejaVu Sans",
                                        "font.name.serif.ja": "DejaVu Serif",
                                        "font.name.sans-serif.ja": "DejaVu Sans",
                                    },
                                },
                            }
                        }
                    },
                )
                created.raise_for_status()
                value = created.json()["value"]
                session_id = str(value["sessionId"])
                capabilities = value["capabilities"]
                browser_pid = int(capabilities["moz:processID"])
                html = (
                    "<style>html,body,*{font-family:'DejaVu Sans',sans-serif !important}</style>"
                    "<main id='app'>static shell</main>"
                    f"<script>document.getElementById('app').textContent={marker!r}</script>"
                )
                navigated = client.post(f"/session/{session_id}/url", json={"url": f"data:text/html,{quote(html)}"})
                navigated.raise_for_status()
                dom_response = client.post(
                    f"/session/{session_id}/execute/sync",
                    json={"script": "return document.documentElement.outerHTML", "args": []},
                )
                dom_response.raise_for_status()
                rendered_dom = str(dom_response.json()["value"])
                printed = client.post(
                    f"/session/{session_id}/print",
                    json={"background": True, "page": {"width": 21.59, "height": 27.94}},
                )
                printed.raise_for_status()
                pdf_bytes = base64.b64decode(printed.json()["value"], validate=True)
                if marker not in rendered_dom or "static shell" in rendered_dom:
                    raise MkbError("NH1_BROWSER_RENDER_INVALID", "Browser did not execute the SPA fixture", 503)
                if not pdf_bytes.startswith(b"%PDF-"):
                    raise MkbError("NH1_BROWSER_PRINT_INVALID", "Browser print did not return PDF bytes", 503)
                browser_version = str(capabilities["browserVersion"])
                driver_version = _first_version_line(self.webdriver_binary)
                return BrowserPrintSmoke(
                    rendered_dom=rendered_dom,
                    pdf_bytes=pdf_bytes,
                    browser_profile=f"firefox/{browser_version};geckodriver/{driver_version}",
                    browser_uid=_process_uid(browser_pid),
                    driver_uid=_process_uid(process.pid),
                    launch_args=command,
                )
        except (httpx.HTTPError, KeyError, ValueError, OSError) as exc:
            raise MkbError("NH1_BROWSER_RUNTIME_UNAVAILABLE", "Real browser smoke failed", 503) from exc
        finally:
            if session_id is not None:
                try:
                    with httpx.Client(base_url=endpoint, timeout=5, trust_env=False) as client:
                        client.delete(f"/session/{session_id}")
                except Exception:
                    pass
            _terminate_process_group(process)
            shutil.rmtree(run_root, ignore_errors=True)

    def encrypt_pdf_fixture(self, pdf_bytes: bytes, *, password: str = "nh1-secret") -> bytes:
        root = Path(tempfile.mkdtemp(prefix="nh1-encrypted-pdf-"))
        source = root / "source.pdf"
        target = root / "encrypted.pdf"
        try:
            source.write_bytes(pdf_bytes)
            completed = subprocess.run(
                [
                    str(self.fixture_pdf_binary),
                    "-q",
                    "-dBATCH",
                    "-dNOPAUSE",
                    "-sDEVICE=pdfwrite",
                    "-dEncryptionR=3",
                    "-dKeyLength=128",
                    f"-sOwnerPassword={password}",
                    f"-sUserPassword={password}",
                    f"-sOutputFile={target}",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=15,
            )
            if completed.returncode != 0 or not target.is_file():
                raise MkbError(
                    "NH1_PDF_FIXTURE_INVALID",
                    "Could not create encrypted PDF fixture",
                    500,
                    {"stderr": completed.stderr.decode("utf-8", errors="replace")[:512]},
                )
            encrypted = target.read_bytes()
            if not encrypted.startswith(b"%PDF-"):
                raise MkbError("NH1_PDF_FIXTURE_INVALID", "Encrypted fixture is not PDF", 500)
            return encrypted
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def supply_inventory(self) -> dict[str, dict[str, object]]:
        return {
            "pdf_parser": {
                "identity": self.pdf_text_binary.name,
                "version": _first_version_line(self.pdf_text_binary),
                "limits": {"timeout_seconds": 8, "address_space_bytes": 536_870_912, "output_bytes": 8_388_608},
                "license": "GPL-family executable used as an isolated subprocess; not linked into MKB",
                "cve_baseline": "NH1 feasibility record; production acceptance and current CVE audit owned by NH6",
                "isolation": "new network namespace + unprivileged uid + CPU/address-space/fd caps",
            },
            "browser": {
                "identity": self.browser_binary.name,
                "version": _first_version_line(self.browser_binary),
                "driver_version": _first_version_line(self.webdriver_binary),
                "limits": {"timeout_seconds": 20, "fixture_egress": "data-url-only"},
                "license": "host browser/driver executables; not linked into MKB",
                "cve_baseline": "NH1 feasibility record; production acceptance and current CVE audit owned by NH6",
                "isolation": "unprivileged uid; headless; no no-sandbox argument; data URL fixture",
            },
        }


def _required_binary(name: str) -> Path:
    resolved = shutil.which(name)
    if resolved is None:
        raise MkbError("NH1_RUNTIME_BINARY_MISSING", f"Required NH1 smoke binary is unavailable: {name}", 503)
    return Path(resolved)


def _drop_privileges(uid: int, gid: int) -> None:
    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_webdriver(client: httpx.Client, process: subprocess.Popen[bytes], timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise MkbError("NH1_BROWSER_RUNTIME_UNAVAILABLE", "WebDriver exited before readiness", 503)
        try:
            response = client.get("/status", timeout=0.5)
            if response.status_code == 200 and response.json().get("value", {}).get("ready"):
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.05)
    raise MkbError("NH1_BROWSER_RUNTIME_UNAVAILABLE", "WebDriver readiness timed out", 503)


def _process_uid(pid: int) -> int:
    status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    line = next(item for item in status.splitlines() if item.startswith("Uid:"))
    return int(line.split()[1])


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, 15)
        process.wait(timeout=5)
    except Exception:
        try:
            os.killpg(process.pid, 9)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _first_version_line(binary: Path) -> str:
    for flag in ("--version", "-v"):
        try:
            completed = subprocess.run(
                [str(binary), flag],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=5,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode != 0:
            continue
        line = next((item.strip() for item in completed.stdout.splitlines() if item.strip()), "")
        if line:
            return line[:256]
    return "version-unavailable"


__all__ = [
    "BrowserPrintSmoke",
    "Nh1MultimodalProbeRequest",
    "Nh1RuntimeSpike",
]
