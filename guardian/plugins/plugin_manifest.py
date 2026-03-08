"""
Canonical service plugin manifest schema (v1).
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

_ALLOWED_BASE_URL_SCHEMES = {"http", "https"}


class PluginCapability(BaseModel):
    """Single capability declaration for service plugins."""

    id: str = Field(..., description="Capability namespace identifier")
    actions: list[str] = Field(
        ..., description="Actions exposed under this capability"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("id")
    @classmethod
    def _validate_capability_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("capability id must be non-empty")
        return value

    @field_validator("actions")
    @classmethod
    def _validate_actions(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("actions must contain at least one action")
        normalized: list[str] = []
        for action in values:
            action = action.strip()
            if not action:
                raise ValueError("action must be non-empty")
            normalized.append(action)
        return normalized


class PluginManifest(BaseModel):
    """Validated canonical service plugin manifest."""

    schema_version: Literal["1.0"] = Field(
        ..., description='Manifest schema version (must be "1.0")'
    )
    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version")
    description: str | None = Field(
        default=None, description="Optional plugin description"
    )
    base_url: str = Field(
        ...,
        description="Plugin service base URL, e.g. https://plugin.example.com",
    )
    capabilities: list[PluginCapability] = Field(
        ..., description="Capability/action declarations"
    )
    extensions: dict[str, Any] | None = Field(
        default=None,
        description="Non-authoritative metadata extensions",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("id", "name", "version")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must be non-empty")
        return value

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        scheme = parsed.scheme.lower()
        if scheme not in _ALLOWED_BASE_URL_SCHEMES:
            raise ValueError("base_url must use http or https")
        if not parsed.netloc:
            raise ValueError("base_url must include a host")
        if parsed.query or parsed.fragment:
            raise ValueError(
                "base_url must not include a query string or fragment"
            )
        if parsed.path not in ("", "/"):
            raise ValueError("base_url must not include a path")
        return f"{scheme}://{parsed.netloc}".rstrip("/")

    @model_validator(mode="after")
    def _validate_unique_operation_pairs(self) -> PluginManifest:
        seen: set[tuple[str, str]] = set()
        duplicates: set[tuple[str, str]] = set()
        for capability in self.capabilities:
            for action in capability.actions:
                pair = (capability.id, action)
                if pair in seen:
                    duplicates.add(pair)
                else:
                    seen.add(pair)
        if duplicates:
            duplicate_list = ", ".join(
                f"{capability}:{action}"
                for capability, action in sorted(duplicates)
            )
            raise ValueError(
                "duplicate capability/action pairs are not allowed: "
                f"{duplicate_list}"
            )
        return self

    def supports_operation(self, capability: str, action: str) -> bool:
        wanted = (capability.strip(), action.strip())
        return any(
            (decl.id, declared_action) == wanted
            for decl in self.capabilities
            for declared_action in decl.actions
        )

    @property
    def operation_pairs(self) -> set[tuple[str, str]]:
        return {
            (decl.id, action)
            for decl in self.capabilities
            for action in decl.actions
        }

    @property
    def entrypoint(self) -> str:
        """
        Back-compat alias for legacy callers still reading `entrypoint`.
        """
        return self.base_url
