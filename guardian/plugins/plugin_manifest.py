"""Canonical v1 service-plugin manifest types and validation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class PluginCapability(BaseModel):
    """Capability declaration for a service plugin."""

    id: str = Field(..., min_length=1)
    actions: list[str] = Field(..., min_length=1)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("capability id must be non-empty")
        return cleaned

    @field_validator("actions")
    @classmethod
    def _validate_actions(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for action in value:
            normalized = action.strip()
            if not normalized:
                raise ValueError("capability actions must be non-empty")
            cleaned.append(normalized)
        return cleaned


class PluginManifest(BaseModel):
    """Canonical v1 manifest schema for HTTP service plugins."""

    schema_version: str = Field(...)
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str | None = None
    base_url: str = Field(...)
    capabilities: list[PluginCapability] = Field(...)
    extensions: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("schema_version must be '1.0'")
        return value

    @field_validator("id", "name", "version")
    @classmethod
    def _validate_text_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field must be non-empty")
        return cleaned

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        cleaned = value.strip()
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url must use http or https")
        if not parsed.netloc:
            raise ValueError("base_url must include a host")
        if parsed.path not in ("", "/"):
            raise ValueError("base_url must not include a path")
        if parsed.query:
            raise ValueError("base_url must not include a query")
        if parsed.fragment:
            raise ValueError("base_url must not include a fragment")
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    @field_validator("capabilities")
    @classmethod
    def _validate_capabilities_present(
        cls, value: list[PluginCapability]
    ) -> list[PluginCapability]:
        if not value:
            raise ValueError("capabilities must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_no_duplicate_operations(self) -> PluginManifest:
        operations: set[tuple[str, str]] = set()
        duplicates: set[tuple[str, str]] = set()
        for capability in self.capabilities:
            for action in capability.actions:
                key = (capability.id, action)
                if key in operations:
                    duplicates.add(key)
                operations.add(key)

        if duplicates:
            dupes = ", ".join(f"{cap}:{act}" for cap, act in sorted(duplicates))
            raise ValueError(f"duplicate capability/action pairs: {dupes}")

        return self

    def supports_operation(self, capability: str, action: str) -> bool:
        """Return True when the manifest declares the capability/action pair."""
        return (capability, action) in self.operations()

    def operations(self) -> set[tuple[str, str]]:
        """Callable operations represented as (capability, action) pairs."""
        return {
            (capability.id, action)
            for capability in self.capabilities
            for action in capability.actions
        }
