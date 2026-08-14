"""Internal operator-only prompt catalog contract models."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from src.contracts.common.models import StrictModel


class PromptCatalogWrite(StrictModel):
    prompt_id: Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")]
    prompt_version: Annotated[str, Field(pattern=r"^v[0-9]+(?:[.-][A-Za-z0-9_.-]+)?$")]
    role: Literal["clean", "markdown", "json", "summarizer"]
    git_relative_path: Annotated[str, Field(min_length=1, max_length=512)]
    granularity_set: list[int] | None = None

    @field_validator("git_relative_path")
    @classmethod
    def validate_path_shape(cls, value: str) -> str:
        from pathlib import Path

        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            raise ValueError("git_relative_path must be a relative Markdown path")
        return path.as_posix()

    @model_validator(mode="after")
    def validate_granularity(self) -> PromptCatalogWrite:
        if self.role == "json":
            if self.granularity_set is None or self.granularity_set != sorted(set(self.granularity_set)):
                raise ValueError("json prompts require a sorted closed granularity_set")
            if not self.granularity_set or any(item not in {0, 1, 2} for item in self.granularity_set):
                raise ValueError("granularity_set must be a non-empty subset of 0,1,2")
        elif self.granularity_set is not None:
            raise ValueError("only json prompts may declare granularity_set")
        return self


class PromptCatalogPatch(StrictModel):
    """Update is intentionally a new immutable version, never an in-place edit."""

    prompt_version: Annotated[str, Field(pattern=r"^v[0-9]+(?:[.-][A-Za-z0-9_.-]+)?$")]
    role: Literal["clean", "markdown", "json", "summarizer"]
    git_relative_path: Annotated[str, Field(min_length=1, max_length=512)]
    granularity_set: list[int] | None = None

    @field_validator("git_relative_path")
    @classmethod
    def validate_path_shape(cls, value: str) -> str:
        from pathlib import Path

        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            raise ValueError("git_relative_path must be a relative Markdown path")
        return path.as_posix()

    @model_validator(mode="after")
    def validate_granularity(self) -> PromptCatalogPatch:
        if self.role == "json":
            if self.granularity_set is None or self.granularity_set != sorted(set(self.granularity_set)):
                raise ValueError("json prompts require a sorted closed granularity_set")
            if not self.granularity_set or any(item not in {0, 1, 2} for item in self.granularity_set):
                raise ValueError("granularity_set must be a non-empty subset of 0,1,2")
        elif self.granularity_set is not None:
            raise ValueError("only json prompts may declare granularity_set")
        return self
