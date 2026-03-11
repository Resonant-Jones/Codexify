"""
Side-effect-free ResonantOS wallet plugin scaffold.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .manifest import RESONANTOS_WALLET_MANIFEST
from .types import (
    PluginHealth,
    TransferIntentPayload,
    TransferIntentRequest,
    TransferIntentResponse,
    VoteIntentPayload,
    VoteIntentRequest,
    VoteIntentResponse,
    WalletPluginManifest,
)


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


class ResonantOSWalletPlugin:
    """
    Scaffold-only wallet bridge contract.

    Direct signing, private key custody, and outbound RPC submission are out
    of scope. This class only returns structured manifest, health, and intent
    payloads for future external bridge wiring.
    """

    def __init__(
        self,
        *,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._now_factory = now_factory or _default_now

    def manifest(self) -> WalletPluginManifest:
        return RESONANTOS_WALLET_MANIFEST.model_copy(deep=True)

    def health_check(self) -> PluginHealth:
        return PluginHealth(
            message=(
                "ResonantOS wallet scaffold is disabled and not wired into "
                "Codexify startup."
            )
        )

    def create_transfer_intent(
        self, request: TransferIntentRequest
    ) -> TransferIntentResponse:
        payload = TransferIntentPayload(
            source_account=request.source_account.model_copy(deep=True),
            destination_account_ref=request.destination_account_ref,
            asset=request.asset.model_copy(deep=True),
            amount=request.amount,
            memo=request.memo,
        )
        return TransferIntentResponse(
            created_at=_format_timestamp(self._now_factory()),
            normalized_payload=payload,
        )

    def create_vote_intent(
        self, request: VoteIntentRequest
    ) -> VoteIntentResponse:
        payload = VoteIntentPayload(
            voter_account=request.voter_account.model_copy(deep=True),
            proposal_id=request.proposal_id,
            vote_choice=request.vote_choice,
            rationale=request.rationale,
        )
        return VoteIntentResponse(
            created_at=_format_timestamp(self._now_factory()),
            normalized_payload=payload,
        )
