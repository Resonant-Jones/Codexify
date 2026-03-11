"""
Typed contracts for the ResonantOS wallet scaffold plugin.

These models intentionally stop at read-model queries and unsigned intent
creation. Direct signing, private key custody, and outbound submission remain
outside this scaffold and must be handled by an external signer bridge.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_required_string(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("value must be non-empty")
    return value


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class WalletPluginCapability(BaseModel):
    """Declared scaffold capability with no signing surface."""

    id: Literal[
        "wallet_summary_read",
        "recent_transaction_read",
        "transfer_intent_create",
        "governance_vote_intent_create",
    ]
    category: Literal["read_model", "intent"]
    description: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str) -> str:
        return _normalize_required_string(value)


class WalletPluginManifest(BaseModel):
    """Manifest contract for the disabled ResonantOS wallet scaffold."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    enabled: bool = False
    autoload: bool = False
    status: Literal["disabled"] = "disabled"
    wiring_status: Literal["not_wired"] = "not_wired"
    runtime_mode: Literal["external_bridge"] = "external_bridge"
    signing_mode: Literal["delegated_signer"] = "delegated_signer"
    description: str = Field(min_length=1)
    capabilities: list[WalletPluginCapability] = Field(min_length=1)
    security_note: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("id", "name", "version", "description", "security_note")
    @classmethod
    def _validate_strings(cls, value: str) -> str:
        return _normalize_required_string(value)


class WalletAccountReference(BaseModel):
    """Reference to an externally managed wallet account."""

    account_ref: str = Field(
        min_length=1,
        description="Stable external wallet account reference.",
    )
    chain: str = Field(min_length=1)
    network: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("account_ref", "chain", "network")
    @classmethod
    def _validate_strings(cls, value: str) -> str:
        return _normalize_required_string(value)


class AssetReference(BaseModel):
    """Token or native asset identifier for intent construction."""

    asset_id: str = Field(
        min_length=1,
        description="Mint, contract, or native asset identifier.",
    )
    symbol: str | None = Field(default=None, max_length=64)

    model_config = ConfigDict(extra="forbid")

    @field_validator("asset_id")
    @classmethod
    def _validate_asset_id(cls, value: str) -> str:
        return _normalize_required_string(value)

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)


class WalletSummaryRequest(BaseModel):
    """Future read-model request for wallet summary data."""

    account: WalletAccountReference
    include_recent_transactions: bool = False

    model_config = ConfigDict(extra="forbid")


class RecentTransactionRequest(BaseModel):
    """Future read-model request for recent transaction history."""

    account: WalletAccountReference
    limit: int = Field(default=10, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")


class TransferIntentRequest(BaseModel):
    """Unsigned transfer intent request for a delegated signer bridge."""

    source_account: WalletAccountReference
    destination_account_ref: str = Field(min_length=1)
    asset: AssetReference
    amount: str = Field(
        min_length=1,
        description="String amount to preserve wallet-specific precision rules.",
    )
    memo: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(extra="forbid")

    @field_validator("destination_account_ref", "amount")
    @classmethod
    def _validate_strings(cls, value: str) -> str:
        return _normalize_required_string(value)

    @field_validator("memo")
    @classmethod
    def _validate_memo(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)


class TransferIntentPayload(BaseModel):
    """Normalized transfer payload returned by the scaffold plugin."""

    source_account: WalletAccountReference
    destination_account_ref: str = Field(min_length=1)
    asset: AssetReference
    amount: str = Field(min_length=1)
    memo: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(extra="forbid")

    @field_validator("destination_account_ref", "amount")
    @classmethod
    def _validate_strings(cls, value: str) -> str:
        return _normalize_required_string(value)

    @field_validator("memo")
    @classmethod
    def _validate_memo(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)


class TransferIntentResponse(BaseModel):
    """Unsigned transfer intent envelope for future wiring."""

    plugin_id: Literal["resonantos_wallet"] = "resonantos_wallet"
    intent_type: Literal["transfer"] = "transfer"
    created_at: str = Field(min_length=1)
    execution_mode: Literal[
        "external_signer_required"
    ] = "external_signer_required"
    ready_for_submission: bool = False
    submitted: bool = False
    normalized_payload: TransferIntentPayload

    model_config = ConfigDict(extra="forbid")

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: str) -> str:
        return _normalize_required_string(value)


class VoteIntentRequest(BaseModel):
    """Unsigned governance vote intent request for delegated signing."""

    voter_account: WalletAccountReference
    proposal_id: str = Field(min_length=1)
    vote_choice: str = Field(min_length=1)
    rationale: str | None = Field(default=None, max_length=2048)

    model_config = ConfigDict(extra="forbid")

    @field_validator("proposal_id", "vote_choice")
    @classmethod
    def _validate_strings(cls, value: str) -> str:
        return _normalize_required_string(value)

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)


class VoteIntentPayload(BaseModel):
    """Normalized governance vote payload returned by the scaffold plugin."""

    voter_account: WalletAccountReference
    proposal_id: str = Field(min_length=1)
    vote_choice: str = Field(min_length=1)
    rationale: str | None = Field(default=None, max_length=2048)

    model_config = ConfigDict(extra="forbid")

    @field_validator("proposal_id", "vote_choice")
    @classmethod
    def _validate_strings(cls, value: str) -> str:
        return _normalize_required_string(value)

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)


class VoteIntentResponse(BaseModel):
    """Unsigned governance vote intent envelope for future wiring."""

    plugin_id: Literal["resonantos_wallet"] = "resonantos_wallet"
    intent_type: Literal["governance_vote"] = "governance_vote"
    created_at: str = Field(min_length=1)
    execution_mode: Literal[
        "external_signer_required"
    ] = "external_signer_required"
    ready_for_submission: bool = False
    submitted: bool = False
    normalized_payload: VoteIntentPayload

    model_config = ConfigDict(extra="forbid")

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: str) -> str:
        return _normalize_required_string(value)


class PluginHealth(BaseModel):
    """Structured health response for a disabled, import-safe scaffold."""

    plugin_id: Literal["resonantos_wallet"] = "resonantos_wallet"
    healthy: bool = True
    enabled: bool = False
    autoload: bool = False
    status: Literal["disabled"] = "disabled"
    wiring_status: Literal["not_wired"] = "not_wired"
    runtime_mode: Literal["external_bridge"] = "external_bridge"
    signing_mode: Literal["delegated_signer"] = "delegated_signer"
    ready: bool = False
    network_configured: bool = False
    message: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        return _normalize_required_string(value)
