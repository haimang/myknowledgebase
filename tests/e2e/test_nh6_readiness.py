"""NH6-T09: supply readiness is an actual positive/negative capability probe."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.runtime.health import HealthAggregator
from tests.nh6_runtime_support import (
    browser_settings,
    local_models_only_server,
    local_multimodal_server,
)


@pytest.fixture(scope="module")
def positive_readiness(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    root = tmp_path_factory.mktemp("nh6-positive-ready")
    with local_multimodal_server() as (base_url, model_key, payloads):
        app = create_app(
            browser_settings(
                root,
                runtime_supply_readiness_required=True,
                multimodal_enabled=True,
                multimodal_model_key=model_key,
                multimodal_model_version="v1",
                inference_vllm_base_url=base_url,
            )
        )
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/ready")
            yield app, response, payloads


def test_positive_probe_matches_presence(positive_readiness) -> None:  # type: ignore[no-untyped-def]
    app, response, payloads = positive_readiness
    assert response.status_code == 200, response.text
    components = {item["name"]: item["ok"] for item in response.json()["components"]}
    assert all(components[key] for key in HealthAggregator.SUPPLY_REQUIRED)
    container = app.state.container
    assert all(
        value is not None
        for value in (
            container.pdf_parser,
            container.browser_runtime,
            container.deterministic_ocr,
            container.clean_llm,
        )
    )
    assert payloads, "multimodal readiness must execute one media request"


def test_missing_binary_component_not_overall_green(tmp_path: Path) -> None:
    with local_multimodal_server() as (base_url, model_key, _payloads):
        app = create_app(
            browser_settings(
                tmp_path,
                runtime_supply_readiness_required=True,
                multimodal_enabled=True,
                multimodal_model_key=model_key,
                multimodal_model_version="v1",
                inference_vllm_base_url=base_url,
                pdf_parser_binary=tmp_path / "missing-pdf-parser",
                browser_binary=tmp_path / "missing-browser",
            )
        )
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    components = {item["name"]: item for item in body["components"]}
    assert components["supply_pdf_parse"] == {
        "name": "supply_pdf_parse",
        "ok": False,
        "code": "not_ready",
    }
    assert components["supply_browser_render"]["ok"] is False
    assert components["supply_browser_print_pdf"]["ok"] is False


def test_models_list_insufficient_for_ready(tmp_path: Path) -> None:
    with local_models_only_server() as (base_url, model_key):
        adapter = LocalVllmAdapter(base_url)
        assert asyncio.run(adapter.probe(model_key=model_key)) is True
        asyncio.run(adapter.aclose())
        app = create_app(
            browser_settings(
                tmp_path,
                runtime_supply_readiness_required=True,
                multimodal_enabled=True,
                multimodal_model_key=model_key,
                multimodal_model_version="v1",
                inference_vllm_base_url=base_url,
            )
        )
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/ready")
    assert response.status_code == 503
    components = {item["name"]: item["ok"] for item in response.json()["components"]}
    assert components["supply_s11_multimodal"] is False
    assert components["inference_binding"] is True


def test_create_app_readiness_without_patch(positive_readiness) -> None:  # type: ignore[no-untyped-def]
    app, response, _payloads = positive_readiness
    assert response.status_code == 200
    source = inspect.getsource(__import__(__name__, fromlist=["*"]))
    for left, right in (("_browser", "_fetcher ="), ("_http", "_fetcher ="), ("_clean", "_llm =")):
        assert left + right not in source
    assert app.state.container.workflow_worker.handler._pdf_parser is app.state.container.pdf_parser  # noqa: SLF001
