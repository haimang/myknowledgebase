"""NH1-T06: real local process feasibility; this is not AP-NH6 production DoD."""

from __future__ import annotations

import pwd
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.app import create_app
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import sha256_bytes, stable_digest
from src.contracts.inference.models import GenerateRequest, InferenceBinding
from src.runtime.supply.nh1_runtime_spike import Nh1MultimodalProbeRequest, Nh1RuntimeSpike
from tests.local_runtime import local_mock_settings


@pytest.fixture(scope="module")
def runtime_smoke_material(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    root = tmp_path_factory.mktemp("nh1-runtime-smoke")
    app = create_app(
        local_mock_settings(
            database_path=root / "mkb.sqlite3",
            object_root=root / "objects",
            internal_token="nh1-runtime-smoke",
        )
    )
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.get("/ready").status_code == 200
        runtime = Nh1RuntimeSpike.discover()
        browser = runtime.render_spa_and_print(marker="NH1 SPA real DOM marker")
        text = runtime.extract_pdf_text(browser.pdf_bytes)
        encrypted = runtime.encrypt_pdf_fixture(browser.pdf_bytes)
        return {
            "runtime": runtime,
            "browser": browser,
            "text": text,
            "encrypted": encrypted,
            "inventory": runtime.supply_inventory(),
        }


def test_pdf_text_layer_local_port(runtime_smoke_material: dict[str, object]) -> None:
    text = runtime_smoke_material["text"]
    assert isinstance(text, str)
    assert "NH1 SPA real DOM marker" in text


def test_spa_render_and_print_pdf(runtime_smoke_material: dict[str, object]) -> None:
    browser = runtime_smoke_material["browser"]
    nobody_uid = pwd.getpwnam("nobody").pw_uid
    assert "NH1 SPA real DOM marker" in browser.rendered_dom  # type: ignore[union-attr]
    assert browser.pdf_bytes.startswith(b"%PDF-")  # type: ignore[union-attr]
    assert browser.browser_uid == nobody_uid  # type: ignore[union-attr]
    assert browser.driver_uid == nobody_uid  # type: ignore[union-attr]
    assert "injected-browser-renderer.v1" not in browser.browser_profile  # type: ignore[union-attr]
    assert all("no-sandbox" not in argument for argument in browser.launch_args)  # type: ignore[union-attr]


def test_binary_model_request_shape(runtime_smoke_material: dict[str, object]) -> None:
    browser = runtime_smoke_material["browser"]
    pdf_bytes = browser.pdf_bytes  # type: ignore[union-attr]
    request = Nh1MultimodalProbeRequest(
        prompt_ref="promptA.default.v1",
        prompt_digest=stable_digest({"prompt": "promptA.default.v1"}),
        model_key="nh1.reviewed-local-multimodal-binding",
        model_version="v1",
        media_type="application/pdf",
        content_digest=sha256_bytes(pdf_bytes),
        media_bytes=pdf_bytes,
    )
    assert request.media_bytes == pdf_bytes
    assert request.object_handle is None

    binding = InferenceBinding(
        capability_key="text_generate",
        adapter_kind="local_vllm",
        model_key="nh1-text-only-control",
        model_version="v1",
        binding_digest=stable_digest({"binding": "text-only"}),
    )
    with pytest.raises(ValidationError):
        GenerateRequest.model_validate(
            {
                "team_uuid": "nh1-team",
                "binding": binding,
                "prompt_ref": request.prompt_ref,
                "prompt_digest": request.prompt_digest,
                "media_type": request.media_type,
                "media_bytes": request.media_bytes,
            }
        )


def test_encrypted_pdf_is_typed_failure(runtime_smoke_material: dict[str, object]) -> None:
    runtime = runtime_smoke_material["runtime"]
    encrypted = runtime_smoke_material["encrypted"]
    with pytest.raises(MkbError) as raised:
        runtime.extract_pdf_text(encrypted)  # type: ignore[union-attr]
    assert raised.value.code == "NH1_PDF_ENCRYPTED"
    assert raised.value.status_code == 422


def test_records_pin_license_cve_isolation(runtime_smoke_material: dict[str, object]) -> None:
    inventory = runtime_smoke_material["inventory"]
    assert isinstance(inventory, dict)
    assert set(inventory) == {"pdf_parser", "browser"}
    for record in inventory.values():
        assert isinstance(record, dict)
        assert all(record.get(key) for key in ("identity", "version", "limits", "license", "cve_baseline", "isolation"))
    assert "network namespace" in str(inventory["pdf_parser"]["isolation"])
    assert "unprivileged uid" in str(inventory["browser"]["isolation"])

    source = Path("tests/e2e/test_nh1_runtime_smoke.py").read_text(encoding="utf-8")
    forbidden_assignments = ("_browser" + "_fetcher =", "_http" + "_fetcher =", "_clean" + "_llm =")
    assert all(token not in source for token in forbidden_assignments)
    dependencies = Path("pyproject.toml").read_text(encoding="utf-8").split("dependencies =", 1)[1]
    assert "playwright" not in dependencies.casefold()
    assert "pypdf" not in dependencies.casefold()
