"""Private local-network fixtures for NH6 browser supply tests."""

from __future__ import annotations

import base64
import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.runtime.config import Settings
from src.runtime.supply.glyph_ocr_worker import GlyphOcrError, recognize_png
from src.runtime.supply.pdf_parser import build_compressed_pdf_fixture
from tests.local_runtime import local_mock_settings


class _SpaHandler(BaseHTTPRequestHandler):
    marker = "NH6 real SPA DOM marker"
    observed_paths: list[str] = []
    observed_lock = threading.Lock()

    def do_GET(self) -> None:  # noqa: N802
        with self.observed_lock:
            self.observed_paths.append(self.path)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/spa")
            self.end_headers()
            return
        if self.path == "/restricted-redirect":
            self.send_response(302)
            self.send_header("Location", "http://metadata.google.internal/latest/meta-data")
            self.end_headers()
            return
        if self.path.startswith("/document.pdf"):
            body = build_compressed_pdf_fixture("pdf capability text")
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/static"):
            body = b"<main>static capability text</main>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/empty-spa"):
            body = (
                "<!doctype html><html><body><main id='app'></main>"
                f"<script>document.getElementById('app').textContent={self.marker!r}</script>"
                "</body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        egress_script = (
            f"fetch('http://{self.headers.get('host')}/beacon').catch(() => undefined);"
            if self.path == "/egress-attempt"
            else ""
        )
        body = (
            "<!doctype html><html><body><main id='app'>static shell</main>"
            f"<script>document.getElementById('app').textContent={self.marker!r};{egress_script}</script>"
            "</body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        del args


@contextmanager
def local_spa_server() -> Iterator[tuple[str, str]]:
    with _SpaHandler.observed_lock:
        _SpaHandler.observed_paths.clear()
    server = ThreadingHTTPServer(("0.0.0.0", 0), _SpaHandler)
    thread = threading.Thread(target=server.serve_forever, name="nh6-spa-fixture", daemon=True)
    thread.start()
    host = socket.gethostbyname(socket.gethostname())
    if host.startswith("127."):
        server.shutdown()
        server.server_close()
        raise RuntimeError("NH6 browser fixture requires one non-loopback local address")
    try:
        yield f"http://{host}:{server.server_port}", _SpaHandler.marker
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def browser_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_path": tmp_path / "mkb.sqlite3",
        "object_root": tmp_path / "objects",
        "internal_token": "nh6-browser",
        "egress_allow_http": True,
        "egress_allow_literal_ip": True,
        "egress_allow_private_default": True,
        "inference_max_in_flight": 8,
        "browser_render_concurrency": 2,
        "browser_print_concurrency": 1,
        "rate_limit_ip_per_min": 10_000,
        "rate_limit_token_per_min": 20_000,
    }
    values.update(overrides)
    return local_mock_settings(**values)  # type: ignore[arg-type]


def observed_spa_paths() -> tuple[str, ...]:
    with _SpaHandler.observed_lock:
        return tuple(_SpaHandler.observed_paths)


class _MultimodalHandler(BaseHTTPRequestHandler):
    model_key = "mkb/glyph-vision-5x7"
    payloads: list[dict[str, object]] = []
    payload_lock = threading.Lock()

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/v1/models":
            self.send_error(404)
            return
        self._json(200, {"data": [{"id": self.model_key}]})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            if length < 1 or length > 24 * 1024 * 1024:
                raise ValueError("request size")
            payload = json.loads(self.rfile.read(length))
            messages = payload["messages"]
            parts = messages[-1]["content"]
            if isinstance(parts, str):
                text = f"DOC LLM OBSERVED {parts.strip()}".strip()
            elif isinstance(parts, list):
                media_url = next(part["image_url"]["url"] for part in parts if part.get("type") == "image_url")
                header, encoded = media_url.split(",", 1)
                media = base64.b64decode(encoded, validate=True)
                if header.startswith("data:image/png;base64"):
                    try:
                        text = recognize_png(media)
                    except GlyphOcrError:
                        text = "VISUAL INPUT OBSERVED"
                    text = text or "VISUAL INPUT OBSERVED"
                elif header.startswith("data:application/pdf;base64") and media.startswith(b"%PDF-"):
                    text = "PDF INPUT OBSERVED"
                else:
                    raise ValueError("unsupported media")
            else:
                raise ValueError("content is not parts")
            with self.payload_lock:
                self.payloads.append(payload)
            self._json(
                200,
                {
                    "model": payload["model"],
                    "choices": [{"message": {"role": "assistant", "content": text}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid multimodal request"})

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        del args


@contextmanager
def local_multimodal_server() -> Iterator[tuple[str, str, list[dict[str, object]]]]:
    with _MultimodalHandler.payload_lock:
        _MultimodalHandler.payloads.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MultimodalHandler)
    thread = threading.Thread(target=server.serve_forever, name="nh6-multimodal-fixture", daemon=True)
    thread.start()
    try:
        yield (
            f"http://127.0.0.1:{server.server_port}",
            _MultimodalHandler.model_key,
            _MultimodalHandler.payloads,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


class _ModelsOnlyHandler(_MultimodalHandler):
    def do_POST(self) -> None:  # noqa: N802
        self._json(400, {"error": "media generation unavailable"})


@contextmanager
def local_models_only_server() -> Iterator[tuple[str, str]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ModelsOnlyHandler)
    thread = threading.Thread(target=server.serve_forever, name="nh6-models-only-fixture", daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _ModelsOnlyHandler.model_key
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


__all__ = [
    "browser_settings",
    "local_multimodal_server",
    "local_models_only_server",
    "local_spa_server",
    "observed_spa_paths",
]
