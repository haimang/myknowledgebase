"""Hardened local browser supply with S16-prefetched, offline page execution."""

from __future__ import annotations

import asyncio
import base64
import os
import pwd
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from src.contracts.common.errors import MkbError
from src.runtime.http_acquisition import HttpAcquirer, HttpAcquisitionResult
from src.runtime.inference.facade import ConcurrencyGate
from src.runtime.intake.types import BrowserPrintResult, BrowserRenderResult

BrowserCapability = Literal["browser.render", "browser.print_pdf"]


@dataclass(frozen=True, slots=True)
class BrowserRuntimeObservation:
    profile_identity: str
    runtime_uid: int
    driver_uid: int
    launch_args: tuple[str, ...]
    rendered_dom: str
    pdf_bytes: bytes | None


class HardenedBrowserRuntime:
    """Share one reviewed browser/driver identity across two distinct caps.

    Network acquisition is performed by :class:`HttpAcquirer`, which checks
    and pins every redirect hop under S16.  The fetched HTML is then executed
    in a non-root browser with outbound HTTP(S) directed to a closed local
    proxy.  This keeps inline SPA execution real without allowing scripts or
    subresources to create an unreviewed second egress path.
    """

    def __init__(
        self,
        *,
        browser_binary: Path,
        webdriver_binary: Path,
        setpriv_binary: Path,
        acquirer: HttpAcquirer,
        gate: ConcurrencyGate,
        render_timeout_seconds: float = 20,
        print_timeout_seconds: float = 30,
        render_output_bytes: int = 8 * 1024 * 1024,
        print_output_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        if min(render_timeout_seconds, print_timeout_seconds) <= 0:
            raise ValueError("browser timeouts must be positive")
        if min(render_output_bytes, print_output_bytes) < 1:
            raise ValueError("browser output limits must be positive")
        self.browser_binary = browser_binary
        self.webdriver_binary = webdriver_binary
        self.setpriv_binary = setpriv_binary
        self._acquirer = acquirer
        self._gate = gate
        self.render_timeout_seconds = float(render_timeout_seconds)
        self.print_timeout_seconds = float(print_timeout_seconds)
        self.render_output_bytes = int(render_output_bytes)
        self.print_output_bytes = int(print_output_bytes)
        self.browser_version = _version(browser_binary)
        self.webdriver_version = _version(webdriver_binary)
        self.invocation_counts: dict[str, int] = {"browser.render": 0, "browser.print_pdf": 0}
        self.success_counts: dict[str, int] = {"browser.render": 0, "browser.print_pdf": 0}
        self.last_observation: BrowserRuntimeObservation | None = None

    @classmethod
    def discover(
        cls,
        *,
        acquirer: HttpAcquirer,
        gate: ConcurrencyGate,
        browser_binary: Path | None = None,
        webdriver_binary: Path | None = None,
        render_timeout_seconds: float = 20,
        print_timeout_seconds: float = 30,
        render_output_bytes: int = 8 * 1024 * 1024,
        print_output_bytes: int = 32 * 1024 * 1024,
    ) -> HardenedBrowserRuntime:
        direct_browser = Path("/snap/firefox/current/usr/lib/firefox/firefox")
        direct_driver = Path("/snap/firefox/current/usr/lib/firefox/geckodriver")
        return cls(
            browser_binary=browser_binary or (direct_browser if direct_browser.is_file() else _binary("firefox")),
            webdriver_binary=webdriver_binary or (direct_driver if direct_driver.is_file() else _binary("geckodriver")),
            setpriv_binary=_binary("setpriv"),
            acquirer=acquirer,
            gate=gate,
            render_timeout_seconds=render_timeout_seconds,
            print_timeout_seconds=print_timeout_seconds,
            render_output_bytes=render_output_bytes,
            print_output_bytes=print_output_bytes,
        )

    async def render(self, url: str) -> BrowserRenderResult:
        source = await self._acquire_html(url)
        observation = await self._execute(
            source.body,
            capability="browser.render",
            timeout_seconds=self.render_timeout_seconds,
            output_limit=self.render_output_bytes,
        )
        return BrowserRenderResult(
            body=observation.rendered_dom,
            profile_identity=observation.profile_identity,
            source_evidence=_source_evidence(source),
            runtime_uid=observation.runtime_uid,
            launch_args=observation.launch_args,
            timeout_seconds=self.render_timeout_seconds,
            output_limit_bytes=self.render_output_bytes,
        )

    async def print_pdf(self, url: str) -> BrowserPrintResult:
        source = await self._acquire_html(url)
        observation = await self._execute(
            source.body,
            capability="browser.print_pdf",
            timeout_seconds=self.print_timeout_seconds,
            output_limit=self.print_output_bytes,
        )
        assert observation.pdf_bytes is not None
        return BrowserPrintResult(
            body=observation.pdf_bytes,
            profile_identity=observation.profile_identity,
            source_evidence=_source_evidence(source),
            runtime_uid=observation.runtime_uid,
            launch_args=observation.launch_args,
            timeout_seconds=self.print_timeout_seconds,
            output_limit_bytes=self.print_output_bytes,
        )

    async def readiness(self, capability: BrowserCapability) -> bool:
        marker = f"MKB {capability} readiness"
        html = (
            "<!doctype html><main id='app'>static shell</main>"
            f"<script>document.getElementById('app').textContent={marker!r}</script>"
        ).encode()
        timeout = self.render_timeout_seconds if capability == "browser.render" else self.print_timeout_seconds
        limit = self.render_output_bytes if capability == "browser.render" else self.print_output_bytes
        try:
            observed = await self._execute(
                html,
                capability=capability,
                timeout_seconds=timeout,
                output_limit=limit,
            )
        except Exception:
            return False
        if marker not in observed.rendered_dom or "static shell" in observed.rendered_dom:
            return False
        if capability == "browser.print_pdf":
            return observed.pdf_bytes is not None and observed.pdf_bytes.startswith(b"%PDF-")
        return observed.pdf_bytes is None

    async def _acquire_html(self, url: str) -> HttpAcquisitionResult:
        source = await self._acquirer.acquire(url)
        if source.response_media_type not in {None, "text/html", "application/xhtml+xml"}:
            raise MkbError("BROWSER_MEDIA_UNSUPPORTED", "Browser source is not an HTML representation", 422)
        try:
            source.body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise MkbError("BROWSER_MEDIA_UNSUPPORTED", "Browser source is not valid UTF-8 HTML", 422) from exc
        return source

    async def _execute(
        self,
        html: bytes,
        *,
        capability: BrowserCapability,
        timeout_seconds: float,
        output_limit: int,
    ) -> BrowserRuntimeObservation:
        lease = await self._gate.try_acquire(capability)
        if lease is None:
            raise MkbError("INFERENCE_BACKPRESSURE", "Browser capability concurrency gate is full", 503)
        self.invocation_counts[capability] += 1
        try:
            observation = await asyncio.to_thread(
                self._execute_sync,
                html,
                capability=capability,
                timeout_seconds=timeout_seconds,
                output_limit=output_limit,
            )
            self.success_counts[capability] += 1
            self.last_observation = observation
            return observation
        except TimeoutError as exc:
            raise MkbError("BROWSER_TIMEOUT", "Browser capability exceeded its deadline", 422) from exc
        finally:
            await self._gate.release(lease)

    def _execute_sync(
        self,
        html: bytes,
        *,
        capability: BrowserCapability,
        timeout_seconds: float,
        output_limit: int,
    ) -> BrowserRuntimeObservation:
        run_root = Path(tempfile.mkdtemp(prefix="mkb-browser-"))
        process: subprocess.Popen[bytes] | None = None
        session_id: str | None = None
        endpoint = ""
        try:
            uid, gid = _prepare_run_root(run_root)
            port = _available_port()
            command = self._driver_command(port, uid=uid, gid=gid)
            endpoint = f"http://127.0.0.1:{port}"
            environment = {
                "PATH": "/usr/bin:/bin:/snap/bin",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "HOME": str(run_root),
                "TMPDIR": str(run_root),
                "XDG_RUNTIME_DIR": str(run_root),
                "MOZ_CRASHREPORTER_DISABLE": "1",
                "MOZ_DATA_REPORTING": "0",
                "http_proxy": "",
                "https_proxy": "",
                "HTTP_PROXY": "",
                "HTTPS_PROXY": "",
                "ALL_PROXY": "",
                "NO_PROXY": "",
            }
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environment,
                start_new_session=True,
            )
            deadline = time.monotonic() + timeout_seconds
            with httpx.Client(base_url=endpoint, timeout=timeout_seconds, trust_env=False) as client:
                _wait_for_webdriver(client, process, deadline)
                firefox_args = ["-headless"]
                if any("no-sandbox" in argument.casefold() for argument in firefox_args):
                    raise MkbError("BROWSER_SANDBOX_DISABLED", "Production browser sandbox cannot be disabled", 503)
                created = client.post(
                    "/session",
                    json={
                        "capabilities": {
                            "alwaysMatch": {
                                "browserName": "firefox",
                                "moz:firefoxOptions": {
                                    "args": firefox_args,
                                    "prefs": {
                                        "network.proxy.type": 1,
                                        "network.proxy.http": "127.0.0.1",
                                        "network.proxy.http_port": 9,
                                        "network.proxy.ssl": "127.0.0.1",
                                        "network.proxy.ssl_port": 9,
                                        "network.proxy.no_proxies_on": "",
                                        "network.proxy.socks_remote_dns": True,
                                        "network.dns.disablePrefetch": True,
                                        "network.prefetch-next": False,
                                        "network.http.speculative-parallel-limit": 0,
                                        "dom.serviceWorkers.enabled": False,
                                        "media.peerconnection.enabled": False,
                                        "dom.push.enabled": False,
                                        # CJK default serif maps ASCII digits to
                                        # unmapped CID glyphs; print must keep
                                        # a Latin ToUnicode path for pdftotext.
                                        "font.language.group": "x-western",
                                        "font.name.serif.x-western": "DejaVu Serif",
                                        "font.name.sans-serif.x-western": "DejaVu Sans",
                                        "font.name.monospace.x-western": "DejaVu Sans Mono",
                                        "font.name.serif.ja": "DejaVu Serif",
                                        "font.name.sans-serif.ja": "DejaVu Sans",
                                    },
                                },
                            }
                        }
                    },
                    timeout=_remaining(deadline),
                )
                created.raise_for_status()
                value = created.json()["value"]
                session_id = str(value["sessionId"])
                capabilities = value["capabilities"]
                browser_pid = int(capabilities["moz:processID"])
                encoded = base64.b64encode(_force_latin_print_font(html)).decode("ascii")
                navigated = client.post(
                    f"/session/{session_id}/url",
                    json={"url": f"data:text/html;charset=utf-8;base64,{encoded}"},
                    timeout=_remaining(deadline),
                )
                navigated.raise_for_status()
                size_response = client.post(
                    f"/session/{session_id}/execute/sync",
                    json={
                        "script": ("return new TextEncoder().encode(document.documentElement.outerHTML).length"),
                        "args": [],
                    },
                    timeout=_remaining(deadline),
                )
                size_response.raise_for_status()
                rendered_size = int(size_response.json()["value"])
                if rendered_size > output_limit:
                    raise MkbError("BROWSER_OUTPUT_LIMIT", "Browser DOM exceeded its configured cap", 422)
                dom_response = client.post(
                    f"/session/{session_id}/execute/sync",
                    json={"script": "return document.documentElement.outerHTML", "args": []},
                    timeout=_remaining(deadline),
                )
                dom_response.raise_for_status()
                rendered_dom = str(dom_response.json()["value"])
                if len(rendered_dom.encode("utf-8")) > output_limit:
                    raise MkbError("BROWSER_OUTPUT_LIMIT", "Browser DOM exceeded its configured cap", 422)
                pdf_bytes: bytes | None = None
                if capability == "browser.print_pdf":
                    printed = client.post(
                        f"/session/{session_id}/print",
                        json={"background": True, "page": {"width": 21.59, "height": 27.94}},
                        timeout=_remaining(deadline),
                    )
                    printed.raise_for_status()
                    pdf_bytes = base64.b64decode(printed.json()["value"], validate=True)
                    if not pdf_bytes.startswith(b"%PDF-"):
                        raise MkbError("BROWSER_PRINT_INVALID", "Browser print did not return PDF bytes", 502)
                    if len(pdf_bytes) > output_limit:
                        raise MkbError("BROWSER_OUTPUT_LIMIT", "Browser PDF exceeded its configured cap", 422)
                version = str(capabilities.get("browserVersion") or self.browser_version)
                profile = f"{capability}.v1;firefox/{version};geckodriver/{self.webdriver_version}"
                return BrowserRuntimeObservation(
                    profile_identity=profile,
                    runtime_uid=_process_uid(browser_pid),
                    driver_uid=_process_uid(process.pid),
                    launch_args=command,
                    rendered_dom=rendered_dom,
                    pdf_bytes=pdf_bytes,
                )
        except MkbError:
            raise
        except httpx.TimeoutException as exc:
            raise MkbError("BROWSER_TIMEOUT", "Browser capability exceeded its deadline", 422) from exc
        except (httpx.HTTPError, KeyError, TypeError, ValueError, OSError) as exc:
            raise MkbError("BROWSER_RUNTIME_UNAVAILABLE", "Hardened browser runtime failed", 503) from exc
        finally:
            if session_id is not None and endpoint:
                try:
                    with httpx.Client(base_url=endpoint, timeout=2, trust_env=False) as client:
                        client.delete(f"/session/{session_id}")
                except Exception:
                    pass
            if process is not None:
                _terminate_process_group(process)
            shutil.rmtree(run_root, ignore_errors=True)

    def _driver_command(self, port: int, *, uid: int, gid: int) -> tuple[str, ...]:
        command: list[str] = []
        if os.geteuid() == 0:
            command.extend(
                (
                    str(self.setpriv_binary),
                    f"--reuid={uid}",
                    f"--regid={gid}",
                    "--clear-groups",
                )
            )
        command.extend(
            (
                str(self.webdriver_binary),
                "--binary",
                str(self.browser_binary),
                "--port",
                str(port),
                "--log",
                "error",
            )
        )
        if any("no-sandbox" in argument.casefold() for argument in command):
            raise MkbError("BROWSER_SANDBOX_DISABLED", "Production browser sandbox cannot be disabled", 503)
        return tuple(command)


def _binary(name: str) -> Path:
    value = shutil.which(name)
    if value is None:
        raise MkbError("SUPPLY_BINARY_MISSING", f"Required runtime supply is unavailable: {name}", 503)
    return Path(value)


def _force_latin_print_font(html: bytes) -> bytes:
    """Keep print PDFs on a Latin ToUnicode font instead of the host CJK default."""

    snippet = (
        b"<style data-mkb-latin-font='dejavu'>"
        b'html,body,*{font-family:"DejaVu Sans","Liberation Sans",sans-serif !important}'
        b"</style>"
    )
    lowered = html.lower()
    head = lowered.find(b"<head")
    if head != -1:
        insert_at = html.find(b">", head)
        if insert_at != -1:
            return html[: insert_at + 1] + snippet + html[insert_at + 1 :]
    return snippet + html


def _source_evidence(source: HttpAcquisitionResult) -> dict[str, object]:
    evidence = source.evidence()
    return {key: value for key, value in evidence.items() if key not in {"raw_byte_digest", "raw_byte_size"}} | {
        "source_response_digest": source.content_digest,
        "source_response_size": source.size_bytes,
    }


def _version(binary: Path) -> str:
    for flag in ("--version", "-v"):
        try:
            completed = subprocess.run(
                (str(binary), flag),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=5,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        line = next((item.strip() for item in completed.stdout.splitlines() if item.strip()), "")
        if line:
            return line[:128]
    return "version-unavailable"


def _prepare_run_root(root: Path) -> tuple[int, int]:
    if os.geteuid() == 0:
        account = pwd.getpwnam("nobody")
        os.chown(root, account.pw_uid, account.pw_gid)
        root.chmod(0o700)
        return account.pw_uid, account.pw_gid
    root.chmod(0o700)
    return os.geteuid(), os.getegid()


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_webdriver(client: httpx.Client, process: subprocess.Popen[bytes], deadline: float) -> None:
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise MkbError("BROWSER_RUNTIME_UNAVAILABLE", "WebDriver exited before readiness", 503)
        try:
            response = client.get("/status", timeout=0.5)
            if response.status_code == 200 and response.json().get("value", {}).get("ready"):
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.05)
    raise MkbError("BROWSER_RUNTIME_UNAVAILABLE", "WebDriver readiness timed out", 503)


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise MkbError("BROWSER_TIMEOUT", "Browser capability exceeded its deadline", 422)
    return remaining


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


__all__ = ["BrowserCapability", "BrowserRuntimeObservation", "HardenedBrowserRuntime"]
