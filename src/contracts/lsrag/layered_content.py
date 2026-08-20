"""Strict, dependency-free validator for the NS1 layered-content wire shape."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.contracts.common.errors import MkbError

LAYERED_CONTENT_SCHEMA_VERSION = "layered_content.v1"
_TOP_LEVEL_KEYS = {"context_meta", "date", "knowledge_tree", "layered_content"}
_META_KEYS = {
    "title",
    "author",
    "publisher",
    "realm",
    "type",
    "tags",
    "channel",
    "default_locale",
    "source_name",
    "source_url",
}
_DATE_KEYS = {"processed_at", "published_at"}
_TREE_KEYS = {"original_file_uuid", "upstream_file_uuids", "downstream_file_uuids"}
_BLOCK_KEYS = {"block_id", "granularity", "original_content", "llm_summary"}
_CHANNEL_KEYS = {"title", "body"}
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_URI = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def layered_schema_path() -> Path:
    """Layered JSON Schema shipped next to this module (wheel-safe)."""

    packaged = Path(__file__).resolve().parent / "layered_content.v1.json"
    if packaged.is_file():
        return packaged
    repo = Path(__file__).resolve().parents[3] / "data" / "schemas" / "lsrag.layered_content.v1.json"
    if repo.is_file():
        return repo
    raise MkbError("STRUCTURE_SCHEMA_UNAVAILABLE", "Layered JSON schema bytes are unavailable", 503)


def layered_schema_sha256() -> str:
    path = layered_schema_path()
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise MkbError("STRUCTURE_SCHEMA_UNAVAILABLE", "Layered JSON schema bytes are unavailable", 503) from exc


def load_layered_json_schema() -> dict[str, Any]:
    path = layered_schema_path()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MkbError("STRUCTURE_SCHEMA_UNAVAILABLE", "Layered JSON schema is invalid", 503) from exc
    if not isinstance(loaded, dict) or not loaded:
        raise MkbError("STRUCTURE_SCHEMA_UNAVAILABLE", "Layered JSON schema is invalid", 503)
    return loaded


def normalize_layered_text(value: str) -> str:
    """Apply the S05 text recipe used before anchor matching."""

    if not isinstance(value, str):
        raise MkbError("STRUCTURE_SCHEMA_INVALID", "Layered content text must be a string", 422)
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def _object(value: object, name: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MkbError("STRUCTURE_SCHEMA_INVALID", f"{name} must be an object", 422)
    result = dict(value)
    unexpected = set(result) - allowed
    if unexpected:
        raise MkbError("STRUCTURE_SCHEMA_INVALID", f"{name} contains unknown fields", 422, {"fields": sorted(unexpected)})
    return result


def _nullable_text(value: object, name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise MkbError("STRUCTURE_SCHEMA_INVALID", f"{name} must be a string or null", 422)
    return value


def _channel(value: object, name: str, *, summary_required: bool = False) -> dict[str, Any]:
    result = _object(value, name, _CHANNEL_KEYS)
    if set(result) != _CHANNEL_KEYS:
        raise MkbError("STRUCTURE_SCHEMA_INVALID", f"{name} must contain title and body", 422)
    result["title"] = _nullable_text(result["title"], f"{name}.title")
    result["body"] = _nullable_text(result["body"], f"{name}.body")
    if summary_required and (not isinstance(result["body"], str) or not result["body"].strip()):
        raise MkbError("STRUCTURE_SUMMARY_INVALID", "C summary body must be non-empty", 422)
    return result


def validate_layered_content(
    payload: object,
    *,
    summary_required: bool = False,
    summaries_must_be_null: bool = False,
) -> dict[str, Any]:
    """Validate and return a JSON-safe copy of a layered-content candidate.

    This intentionally implements only the checked-in schema.  It does not
    normalize or invent content, and it rejects span fields rather than
    accepting model-supplied coordinates as authority.
    """

    result = _object(payload, "layered_content", _TOP_LEVEL_KEYS)
    if "context_meta" not in result or "layered_content" not in result:
        raise MkbError("STRUCTURE_SCHEMA_INVALID", "context_meta and layered_content are required", 422)
    result["context_meta"] = _object(result["context_meta"], "context_meta", _META_KEYS)
    for key in ("title", "author", "publisher", "realm", "type", "channel", "default_locale", "source_name", "source_url"):
        if key in result["context_meta"]:
            result["context_meta"][key] = _nullable_text(result["context_meta"][key], f"context_meta.{key}")
    if "tags" in result["context_meta"]:
        tags = result["context_meta"]["tags"]
        if tags is not None and (not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags)):
            raise MkbError("STRUCTURE_SCHEMA_INVALID", "context_meta.tags must be strings", 422)
    if "date" in result:
        result["date"] = _object(result["date"], "date", _DATE_KEYS)
        for key, value in result["date"].items():
            result["date"][key] = _nullable_text(value, f"date.{key}")
    if "knowledge_tree" in result:
        result["knowledge_tree"] = _object(result["knowledge_tree"], "knowledge_tree", _TREE_KEYS)
        tree = result["knowledge_tree"]
        if "original_file_uuid" in tree and tree["original_file_uuid"] is not None:
            if not isinstance(tree["original_file_uuid"], str) or not _UUID.match(tree["original_file_uuid"]):
                raise MkbError("STRUCTURE_SCHEMA_INVALID", "original_file_uuid must be a UUID string", 422)
        for key in ("upstream_file_uuids", "downstream_file_uuids"):
            if key not in tree:
                continue
            value = tree[key]
            if value is None:
                continue
            if not isinstance(value, list) or any(not isinstance(item, str) or not _UUID.match(item) for item in value):
                raise MkbError("STRUCTURE_SCHEMA_INVALID", f"{key} must be an array of UUID strings", 422)
    if "context_meta" in result and isinstance(result["context_meta"].get("source_url"), str):
        url = result["context_meta"]["source_url"]
        if url and not _URI.match(url):
            raise MkbError("STRUCTURE_SCHEMA_INVALID", "context_meta.source_url must be a URI", 422)
    if "date" in result:
        for key, value in result["date"].items():
            if isinstance(value, str) and value and not _DATETIME.match(value):
                raise MkbError("STRUCTURE_SCHEMA_INVALID", f"date.{key} must be date-time", 422)
    blocks = result["layered_content"]
    if not isinstance(blocks, list) or not blocks:
        raise MkbError("STRUCTURE_SCHEMA_INVALID", "layered_content must be a non-empty array", 422)
    validated: list[dict[str, Any]] = []
    for index, raw_block in enumerate(blocks):
        block = _object(raw_block, f"layered_content[{index}]", _BLOCK_KEYS)
        if set(block) != _BLOCK_KEYS:
            raise MkbError("STRUCTURE_SCHEMA_INVALID", "Each layered block must contain the four wire fields", 422)
        if isinstance(block["block_id"], bool) or not isinstance(block["block_id"], int) or block["block_id"] < 0:
            raise MkbError("STRUCTURE_SCHEMA_INVALID", "block_id must be a non-negative integer", 422)
        if isinstance(block["granularity"], bool) or not isinstance(block["granularity"], int) or block["granularity"] < 0:
            raise MkbError("STRUCTURE_SCHEMA_INVALID", "granularity must be a non-negative integer", 422)
        block["original_content"] = _channel(block["original_content"], f"layered_content[{index}].original_content")
        block["llm_summary"] = _channel(
            block["llm_summary"], f"layered_content[{index}].llm_summary", summary_required=summary_required
        )
        if summaries_must_be_null and any(value is not None for value in block["llm_summary"].values()):
            raise MkbError("STRUCTURE_SUMMARY_INVALID", "B candidate summaries must be null", 422)
        validated.append(block)
    if all(block["granularity"] != 0 for block in validated):
        raise MkbError("STRUCTURE_SCHEMA_INVALID", "layered_content must contain a granularity 0 block", 422)
    result["layered_content"] = validated
    return result


__all__ = [
    "LAYERED_CONTENT_SCHEMA_VERSION",
    "layered_schema_path",
    "layered_schema_sha256",
    "load_layered_json_schema",
    "normalize_layered_text",
    "validate_layered_content",
]
