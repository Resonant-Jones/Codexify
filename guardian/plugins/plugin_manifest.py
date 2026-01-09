"""
Plugin Manifest Schema
~~~~~~~~~~~~~~~~~~~~~~

Defines the manifest schema for Codexify plugins. Plugins use this
schema to register themselves, expose capabilities, and optionally
render UI panels.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """
    Schema for plugin manifests.

    Plugins register themselves via a manifest.json file that conforms
    to this schema. The manifest declares the plugin's identity,
    entrypoint, required permissions, and optional UI configuration.
    """

    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    entrypoint: str = Field(
        ..., description="Plugin entrypoint URL (e.g., 'http://localhost:8080/rpc')"
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="Required permissions (e.g., 'threads.read', 'document.write')",
    )
    ui_panel: Optional[bool] = Field(
        default=False, description="Whether the plugin renders a UI panel"
    )
    ui_position: Optional[Literal["left", "right", "floating"]] = Field(
        default="right", description="Position of the UI panel"
    )

    class Config:
        """Pydantic config for PluginManifest."""

        json_schema_extra = {
            "example": {
                "id": "codex",
                "name": "Codex Plugin",
                "entrypoint": "http://localhost:8081/rpc",
                "permissions": ["threads.read", "document.write"],
                "ui_panel": True,
                "ui_position": "right",
            }
        }
