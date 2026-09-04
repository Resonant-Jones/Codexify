"""Canonical Persona Profile manifest contracts.

The manifest is authored configuration intent.  Account ownership and other
environmental authority are deliberately absent and remain server-owned.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PERSONA_PROFILE_API_VERSION = "codexify.persona/v1"


class _StrictManifestModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class PersonaIdentityConfig(_StrictManifestModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class PersonaPromptConfig(_StrictManifestModel):
    system_prompt: str = Field(
        min_length=1,
        alias="systemPrompt",
        serialization_alias="systemPrompt",
    )
    style_notes: str | None = Field(
        default=None,
        alias="styleNotes",
        serialization_alias="styleNotes",
    )
    directives: str | None = None


class PersonaModelConfig(_StrictManifestModel):
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=255)
    temperature: float = Field(ge=0.0, le=2.0)
    top_k: int | None = Field(
        default=None,
        gt=0,
        alias="topK",
        serialization_alias="topK",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        alias="topP",
        serialization_alias="topP",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        alias="maxTokens",
        serialization_alias="maxTokens",
    )

    @field_validator("provider")
    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        return value.lower()


class PersonaVoiceConfig(_StrictManifestModel):
    enabled: bool
    provider: str = Field(min_length=1, max_length=64)
    voice_preset: str = Field(
        alias="voicePreset",
        serialization_alias="voicePreset",
    )
    speed: float = Field(gt=0.0)
    wake_word: str = Field(
        alias="wakeWord",
        serialization_alias="wakeWord",
    )
    interruptible: bool


class PersonaCapabilityPermissions(_StrictManifestModel):
    web: bool
    email: bool
    calendar: bool
    cli: bool
    filesystem: bool


class PersonaCapabilityConfig(_StrictManifestModel):
    pinned_tools: list[str] = Field(
        alias="pinnedTools",
        serialization_alias="pinnedTools",
    )
    allowed_tools: list[str] = Field(
        alias="allowedTools",
        serialization_alias="allowedTools",
    )
    skills: list[str]
    permissions: PersonaCapabilityPermissions


class PersonaRetrievalConfig(_StrictManifestModel):
    enabled: bool
    mode: str = Field(min_length=1)
    top_k: int = Field(
        gt=0,
        alias="topK",
        serialization_alias="topK",
    )
    rerank: bool


class PersonaProfileManifestWrite(_StrictManifestModel):
    """Client-authored V1 manifest; revision is intentionally absent."""

    api_version: Literal[PERSONA_PROFILE_API_VERSION] = Field(
        alias="apiVersion",
        serialization_alias="apiVersion",
    )
    profile_identity: str = Field(
        min_length=1,
        max_length=128,
        alias="profileIdentity",
        serialization_alias="profileIdentity",
    )
    identity: PersonaIdentityConfig
    prompt: PersonaPromptConfig
    model: PersonaModelConfig
    voice: PersonaVoiceConfig | None = None
    capabilities: PersonaCapabilityConfig | None = None
    retrieval: PersonaRetrievalConfig | None = None


class PersonaProfileManifest(PersonaProfileManifestWrite):
    """Persisted immutable V1 manifest snapshot."""

    revision: int = Field(gt=0)


def assign_manifest_revision(
    manifest: PersonaProfileManifestWrite,
    revision: int,
) -> PersonaProfileManifest:
    """Create a persisted snapshot with a server-assigned revision."""
    payload = manifest.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    payload["revision"] = revision
    return PersonaProfileManifest.model_validate(payload)


def build_legacy_manifest(
    *,
    profile_identity: str,
    name: str,
    system_prompt: str,
    model_provider: str,
    model_id: str,
    temperature: float,
) -> PersonaProfileManifestWrite:
    """Build the smallest truthful manifest for the five-field seam."""
    return PersonaProfileManifestWrite.model_validate(
        {
            "apiVersion": PERSONA_PROFILE_API_VERSION,
            "profileIdentity": profile_identity,
            "identity": {"name": name},
            "prompt": {"systemPrompt": system_prompt},
            "model": {
                "provider": model_provider,
                "model": model_id,
                "temperature": temperature,
            },
        }
    )


def authored_manifest_dict(
    manifest: PersonaProfileManifestWrite | PersonaProfileManifest,
) -> dict[str, Any]:
    """Return normalized authored content without persistence revision."""
    payload = manifest.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    payload.pop("revision", None)
    return payload


def persisted_manifest_dict(
    manifest: PersonaProfileManifest,
) -> dict[str, Any]:
    """Return the canonical external representation of one snapshot."""
    return manifest.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )


__all__ = [
    "PERSONA_PROFILE_API_VERSION",
    "PersonaCapabilityConfig",
    "PersonaCapabilityPermissions",
    "PersonaIdentityConfig",
    "PersonaModelConfig",
    "PersonaProfileManifest",
    "PersonaProfileManifestWrite",
    "PersonaPromptConfig",
    "PersonaRetrievalConfig",
    "PersonaVoiceConfig",
    "assign_manifest_revision",
    "authored_manifest_dict",
    "build_legacy_manifest",
    "persisted_manifest_dict",
]
