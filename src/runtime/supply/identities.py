"""Closed runtime-supply identities; implementation/library pins live in SBOM evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from src.contracts.common.models import StrictModel

SupplyCapability = Literal[
    "pdf.parse",
    "browser.render",
    "browser.print_pdf",
    "ocr.deterministic",
    "s11.multimodal",
]


class SupplyLimits(StrictModel):
    timeout_seconds: float = Field(gt=0, le=300)
    input_bytes: int = Field(ge=1, le=1024 * 1024 * 1024)
    output_bytes: int = Field(ge=1, le=1024 * 1024 * 1024)
    concurrency: int = Field(ge=1, le=128)
    address_space_bytes: int | None = Field(default=None, ge=64 * 1024 * 1024)
    cpu_seconds: int | None = Field(default=None, ge=1, le=300)


class SupplyIdentity(StrictModel):
    capability_key: SupplyCapability
    contract_version: Literal["v1"] = "v1"
    implementation_identity_slot: str = Field(min_length=1, max_length=128)
    implementation_version_slot: str = Field(min_length=1, max_length=128)
    readiness_key: str = Field(pattern=r"^supply_[a-z0-9_]+$")
    execution_boundary: Literal["isolated_local", "hardened_browser", "s11_inference"]
    network_policy: Literal["denied", "s16_egress", "inference_binding"]
    prompt_required: bool
    model_required: bool
    limits: SupplyLimits


SUPPLY_IDENTITIES: tuple[SupplyIdentity, ...] = (
    SupplyIdentity(
        capability_key="pdf.parse",
        implementation_identity_slot="PDF_PARSER_BINARY_IDENTITY",
        implementation_version_slot="PDF_PARSER_BINARY_VERSION",
        readiness_key="supply_pdf_parse",
        execution_boundary="isolated_local",
        network_policy="denied",
        prompt_required=False,
        model_required=False,
        limits=SupplyLimits(
            timeout_seconds=8,
            input_bytes=64 * 1024 * 1024,
            output_bytes=8 * 1024 * 1024,
            concurrency=2,
            address_space_bytes=512 * 1024 * 1024,
            cpu_seconds=5,
        ),
    ),
    SupplyIdentity(
        capability_key="browser.render",
        implementation_identity_slot="BROWSER_RUNTIME_IDENTITY",
        implementation_version_slot="BROWSER_RENDER_PROFILE_VERSION",
        readiness_key="supply_browser_render",
        execution_boundary="hardened_browser",
        network_policy="s16_egress",
        prompt_required=False,
        model_required=False,
        limits=SupplyLimits(
            timeout_seconds=20,
            input_bytes=8 * 1024 * 1024,
            output_bytes=8 * 1024 * 1024,
            concurrency=2,
        ),
    ),
    SupplyIdentity(
        capability_key="browser.print_pdf",
        implementation_identity_slot="BROWSER_RUNTIME_IDENTITY",
        implementation_version_slot="BROWSER_PRINT_PROFILE_VERSION",
        readiness_key="supply_browser_print_pdf",
        execution_boundary="hardened_browser",
        network_policy="s16_egress",
        prompt_required=False,
        model_required=False,
        limits=SupplyLimits(
            timeout_seconds=30,
            input_bytes=8 * 1024 * 1024,
            output_bytes=32 * 1024 * 1024,
            concurrency=1,
        ),
    ),
    SupplyIdentity(
        capability_key="ocr.deterministic",
        implementation_identity_slot="DETERMINISTIC_OCR_IDENTITY",
        implementation_version_slot="DETERMINISTIC_OCR_VERSION",
        readiness_key="supply_ocr_deterministic",
        execution_boundary="isolated_local",
        network_policy="denied",
        prompt_required=False,
        model_required=False,
        limits=SupplyLimits(
            timeout_seconds=10,
            input_bytes=32 * 1024 * 1024,
            output_bytes=4 * 1024 * 1024,
            concurrency=2,
        ),
    ),
    SupplyIdentity(
        capability_key="s11.multimodal",
        implementation_identity_slot="MULTIMODAL_ADAPTER_IDENTITY",
        implementation_version_slot="MULTIMODAL_MODEL_VERSION",
        readiness_key="supply_s11_multimodal",
        execution_boundary="s11_inference",
        network_policy="inference_binding",
        prompt_required=True,
        model_required=True,
        limits=SupplyLimits(
            timeout_seconds=180,
            input_bytes=20 * 1024 * 1024,
            output_bytes=4 * 1024 * 1024,
            concurrency=2,
        ),
    ),
)

SUPPLY_BY_CAPABILITY = {identity.capability_key: identity for identity in SUPPLY_IDENTITIES}

if len(SUPPLY_BY_CAPABILITY) != len(SUPPLY_IDENTITIES):
    raise RuntimeError("runtime supply capability identities must be unique")
if len({identity.readiness_key for identity in SUPPLY_IDENTITIES}) != len(SUPPLY_IDENTITIES):
    raise RuntimeError("runtime supply readiness identities must be unique")


__all__ = ["SUPPLY_BY_CAPABILITY", "SUPPLY_IDENTITIES", "SupplyCapability", "SupplyIdentity", "SupplyLimits"]
