"""Typed process configuration. Secrets are injected, never persisted."""

from __future__ import annotations

from pathlib import Path

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
    inference_vllm_base_url: str = "http://127.0.0.1:668"
    inference_probe_enabled: bool = False
    live_inference: bool = False
    inference_max_in_flight: int = Field(default=8, ge=1, le=256)
    inference_max_attempts: int = Field(default=3, ge=1, le=10)
    object_max_bytes: int = Field(default=256 * 1024 * 1024, ge=1, le=1024 * 1024 * 1024)
    rate_limit_ip_per_min: int = Field(default=120, ge=1, le=100_000)
    rate_limit_token_per_min: int = Field(default=600, ge=1, le=100_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    @property
    def resolved_database_path(self) -> Path:
        return self.database_path or self.data_dir / "database" / "mkb_primary.db"

    @property
    def resolved_object_root(self) -> Path:
        return self.object_root or self.data_dir / "objects"

    @property
    def prompt_root(self) -> Path:
        return self.data_dir / "prompts"

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
