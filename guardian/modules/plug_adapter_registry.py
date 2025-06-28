"""Plug Adapter Registry
======================

Central registry for Guardian plug-in adapters with explicit
permission scopes.

Usage example::

    from guardian.modules.plug_adapter_registry import AdapterRegistry, AdapterSpec

    registry = AdapterRegistry()
    spec = AdapterSpec(name="weather", allowed_scopes=["read"], can_pull=True)
    registry.register(spec)
    assert registry.allowed("weather", "read")
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class AdapterSpec(BaseModel):
    """Specification for a plug adapter."""

    name: str = Field(..., description="Adapter name")
    allowed_scopes: List[str] = Field(..., description="Data scopes")
    can_pull: bool = Field(False, description="Whether adapter can pull from AuraAPI")
    can_push: bool = Field(False, description="Whether adapter can push outbound")


class AdapterRegistry:
    """Registry for plug adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, AdapterSpec] = {}

    def register(self, spec: AdapterSpec) -> None:
        """Register a new adapter."""
        self._adapters[spec.name] = spec

    def allowed(self, name: str, scope: str) -> bool:
        """Check if adapter has permission for a scope."""
        spec = self._adapters.get(name)
        return bool(spec and scope in spec.allowed_scopes)
