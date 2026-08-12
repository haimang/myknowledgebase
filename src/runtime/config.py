"""Typed process configuration. Secrets are injected, never persisted."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MKB_", case_sensitive=False, extra="ignore")

    internal_tokens: str = ""
    internal_token: str | None = None
    internal_token_previous: str | None = None
    data_dir: Path = Path("data")
    database_path: Path | None = None
    object_root: Path | None = None
    # The local profile deliberately uses a deterministic exact scan rather
    # than silently labelling SQLite's compatibility B-tree as an ANN index.
    # A deployment that requires native ANN must opt in explicitly and will
    # fail readiness on this stock-SQLite adapter.
    vector_backend: Literal["deterministic_exact", "native_ann"] = "deterministic_exact"
    prompt_root_path: Path | None = None
    config_root_path: Path | None = None
    inference_vllm_base_url: str = "http://127.0.0.1:668"
    inference_probe_enabled: bool = False
    live_inference: bool = False
    inference_max_in_flight: int = Field(default=8, ge=1, le=256)
    inference_max_attempts: int = Field(default=3, ge=1, le=10)
    object_max_bytes: int = Field(default=256 * 1024 * 1024, ge=1, le=1024 * 1024 * 1024)
    rate_limit_ip_per_min: int = Field(default=120, ge=1, le=100_000)
    rate_limit_token_per_min: int = Field(default=600, ge=1, le=100_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    metrics_require_token: bool = False
    egress_max_redirects: int = Field(default=3, ge=0, le=3)
    egress_allow_literal_ip: bool = False
    egress_allow_private_default: bool = False
    egress_allow_http: bool = False
    acquisition_max_response_bytes: int = Field(default=8 * 1024 * 1024, ge=1, le=64 * 1024 * 1024)
    object_gc_enabled: bool = True
    object_gc_grace_seconds: int = Field(default=24 * 60 * 60, ge=1, le=365 * 24 * 60 * 60)
    object_gc_interval_seconds: int = Field(default=10 * 60, ge=1, le=24 * 60 * 60)
    object_gc_batch_size: int = Field(default=100, ge=1, le=10_000)

    @property
    def resolved_database_path(self) -> Path:
        return self.database_path or self.data_dir / "database" / "mkb_primary.db"

    @property
    def resolved_object_root(self) -> Path:
        return self.object_root or self.data_dir / "objects"

    @property
    def prompt_root(self) -> Path:
        # Prompt bytes are tracked source assets, not mutable runtime data.  A
        # test/deployment may explicitly mount another checked-out prompt tree,
        # but changing data_dir for DB/object isolation must not silently make
        # the registry lose its audited prompt source of truth.
        return self.prompt_root_path or Path(__file__).parents[2] / "data" / "prompts"

    @property
    def config_root(self) -> Path:
        """Checked-in L0 config, independently mountable for test/deploy profiles."""

        return self.config_root_path or Path(__file__).parents[2] / "data" / "config"

    @property
    def migration_directory(self) -> Path:
        return Path(__file__).parents[1] / "persistence" / "migrations"

    @property
    def active_tokens(self) -> tuple[str, ...]:
        items = [*self.internal_tokens.split(",")]
        if self.internal_token:
            items.append(self.internal_token)
        if self.internal_token_previous:
            items.append(self.internal_token_previous)
        # Preserve configured order but remove duplicates; the two-active cap is
        # checked by ActiveTokenSet, where the trust policy actually lives.
        return tuple(dict.fromkeys(item.strip() for item in items if item.strip()))
