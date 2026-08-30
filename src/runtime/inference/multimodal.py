"""Prompt-bound clean port backed by the S11 multimodal request sibling."""

from __future__ import annotations

import hashlib
import struct
import zlib

from intake.types import CleanPrompt
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import sha256_bytes, stable_digest
from src.contracts.inference.models import (
    InferenceBinding,
    MultimodalGenerateRequest,
    TextGenerateRequest,
)
from src.contracts.storage.models import ObjectHandle
from src.runtime.inference.facade import InferenceFacade
from src.storage.ports import ObjectStorePort


def configured_multimodal_binding(*, model_key: str, model_version: str) -> InferenceBinding:
    if model_key.casefold() == "latest" or model_version.casefold() == "latest":
        raise ValueError("multimodal model identity cannot float at latest")
    return InferenceBinding(
        capability_key="text_generate",
        adapter_kind="local_vllm",
        model_key=model_key,
        model_version=model_version,
        binding_digest=stable_digest(
            {
                "capability": "text_generate",
                "supply_capability": "s11.multimodal",
                "adapter_kind": "local_vllm",
                "model_key": model_key,
                "model_version": model_version,
            }
        ),
    )


class ObjectStoreMediaResolver:
    """Resolve Team-scoped S13 handles without exposing storage paths to S11."""

    def __init__(self, storage: ObjectStorePort) -> None:
        self._storage = storage

    async def resolve_media(self, team_uuid: str, object_handle: str) -> bytes:
        return await self._storage.read_verified(team_uuid, ObjectHandle(value=object_handle))


class S11CleanLanguageModel:
    """Bridge intake's narrow clean port to typed text/media S11 calls."""

    def __init__(
        self,
        facade: InferenceFacade,
        *,
        text_binding: InferenceBinding,
        multimodal_binding: InferenceBinding,
    ) -> None:
        self._facade = facade
        self.text_binding = text_binding
        self.multimodal_binding = multimodal_binding

    async def complete(
        self,
        *,
        prompt: str,
        text: str | None = None,
        blob: bytes | None = None,
        media_type: str | None = None,
    ) -> str:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        material = CleanPrompt(
            key="promptA.runtime",
            version="v1",
            text=prompt,
            content_sha256=digest,
        )
        return await self.complete_bound(
            team_uuid="mkb-runtime-clean",
            prompt=material,
            text=text,
            blob=blob,
            media_type=media_type,
            purpose="document_understanding",
        )

    async def complete_bound(
        self,
        *,
        team_uuid: str,
        prompt: CleanPrompt,
        text: str | None = None,
        blob: bytes | None = None,
        media_type: str | None = None,
        purpose: str = "document_understanding",
    ) -> str:
        if blob is not None:
            if not blob:
                raise MkbError("INFERENCE_MEDIA_INVALID", "Multimodal media is empty", 422)
            if not isinstance(media_type, str):
                raise MkbError("INFERENCE_MEDIA_INVALID", "Multimodal media type is unavailable", 422)
            request = MultimodalGenerateRequest(
                team_uuid=team_uuid,
                binding=self.multimodal_binding,
                prompt_ref=f"{prompt.key}@{prompt.version}",
                prompt_digest=prompt.content_sha256,
                prompt_text=prompt.text,
                input_text=text,
                media_type=media_type,
                media_digest=sha256_bytes(blob),
                media_bytes=blob,
                purpose=purpose,
            )
            response = await self._facade.multimodal_generate(request)
            return response.text
        if not isinstance(text, str) or not text.strip():
            raise MkbError("INFERENCE_INPUT_EMPTY", "Text generation input is empty", 422)
        response = await self._facade.text_generate(
            TextGenerateRequest(
                team_uuid=team_uuid,
                binding=self.text_binding,
                prompt_ref=f"{prompt.key}@{prompt.version}",
                prompt_digest=prompt.content_sha256,
                input_text=text,
                system_text=prompt.text,
            )
        )
        return response.text

    async def readiness(self) -> bool:
        """Exercise an actual media request; a model-list response cannot pass."""

        prompt_text = "Return a non-empty observation for this one-pixel image."
        prompt = CleanPrompt(
            key="promptA.multimodal-readiness",
            version="v1",
            text=prompt_text,
            content_sha256=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        )
        try:
            result = await self.complete_bound(
                team_uuid="mkb-runtime-readiness",
                prompt=prompt,
                blob=build_probe_png(),
                media_type="image/png",
                purpose="vision",
            )
            return bool(result.strip())
        except Exception:
            return False


def build_probe_png() -> bytes:
    """Return a deterministic 1x1 grayscale PNG for bounded live probes."""

    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    return (
        signature
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + chunk(b"IEND", b"")
    )


__all__ = [
    "ObjectStoreMediaResolver",
    "S11CleanLanguageModel",
    "build_probe_png",
    "configured_multimodal_binding",
]
