from __future__ import annotations

import importlib
import socket
from datetime import datetime, timezone

from guardian.plugins.resonantos_wallet import (
    RESONANTOS_WALLET_MANIFEST,
    ResonantOSWalletPlugin,
)
from guardian.plugins.resonantos_wallet.types import (
    AssetReference,
    TransferIntentRequest,
    VoteIntentRequest,
    WalletAccountReference,
)


def _fixed_now() -> datetime:
    return datetime(2026, 3, 10, 15, 30, 0, tzinfo=timezone.utc)


def _block_network(*args, **kwargs):
    raise AssertionError("network calls are out of scope for this scaffold")


def test_manifest_is_disabled_by_default() -> None:
    capability_ids = [
        capability.id for capability in RESONANTOS_WALLET_MANIFEST.capabilities
    ]

    assert RESONANTOS_WALLET_MANIFEST.id == "resonantos_wallet"
    assert RESONANTOS_WALLET_MANIFEST.name == "ResonantOS Wallet"
    assert RESONANTOS_WALLET_MANIFEST.version == "0.1.0"
    assert RESONANTOS_WALLET_MANIFEST.enabled is False
    assert RESONANTOS_WALLET_MANIFEST.autoload is False
    assert RESONANTOS_WALLET_MANIFEST.status == "disabled"
    assert RESONANTOS_WALLET_MANIFEST.wiring_status == "not_wired"
    assert RESONANTOS_WALLET_MANIFEST.runtime_mode == "external_bridge"
    assert RESONANTOS_WALLET_MANIFEST.signing_mode == "delegated_signer"
    assert capability_ids == [
        "wallet_summary_read",
        "recent_transaction_read",
        "transfer_intent_create",
        "governance_vote_intent_create",
    ]


def test_plugin_imports_cleanly_without_external_wallet_software() -> None:
    module = importlib.import_module("guardian.plugins.resonantos_wallet")

    assert module.ResonantOSWalletPlugin is ResonantOSWalletPlugin
    assert module.RESONANTOS_WALLET_MANIFEST.id == "resonantos_wallet"


def test_health_check_reports_disabled_not_wired() -> None:
    plugin = ResonantOSWalletPlugin()

    health = plugin.health_check()

    assert health.plugin_id == "resonantos_wallet"
    assert health.healthy is True
    assert health.enabled is False
    assert health.autoload is False
    assert health.status == "disabled"
    assert health.wiring_status == "not_wired"
    assert health.runtime_mode == "external_bridge"
    assert health.signing_mode == "delegated_signer"
    assert health.ready is False
    assert health.network_configured is False
    assert "disabled" in health.message.lower()
    assert "not wired" in health.message.lower()


def test_create_transfer_intent_returns_structured_unsigned_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(socket, "create_connection", _block_network)
    plugin = ResonantOSWalletPlugin(now_factory=_fixed_now)
    request = TransferIntentRequest(
        source_account=WalletAccountReference(
            account_ref="wallet://primary",
            chain="solana",
            network="mainnet-beta",
        ),
        destination_account_ref="wallet://counterparty",
        asset=AssetReference(
            asset_id="So11111111111111111111111111111111111111112",
            symbol="SOL",
        ),
        amount="1.250000",
        memo="rent settlement",
    )

    response = plugin.create_transfer_intent(request)

    assert response.plugin_id == "resonantos_wallet"
    assert response.intent_type == "transfer"
    assert response.created_at == "2026-03-10T15:30:00Z"
    assert response.execution_mode == "external_signer_required"
    assert response.ready_for_submission is False
    assert response.submitted is False
    assert response.normalized_payload.model_dump(mode="json") == {
        "source_account": {
            "account_ref": "wallet://primary",
            "chain": "solana",
            "network": "mainnet-beta",
        },
        "destination_account_ref": "wallet://counterparty",
        "asset": {
            "asset_id": "So11111111111111111111111111111111111111112",
            "symbol": "SOL",
        },
        "amount": "1.250000",
        "memo": "rent settlement",
    }


def test_create_vote_intent_returns_structured_unsigned_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(socket, "create_connection", _block_network)
    plugin = ResonantOSWalletPlugin(now_factory=_fixed_now)
    request = VoteIntentRequest(
        voter_account=WalletAccountReference(
            account_ref="wallet://governance",
            chain="solana",
            network="mainnet-beta",
        ),
        proposal_id="proposal-42",
        vote_choice="approve",
        rationale="aligns with treasury policy",
    )

    response = plugin.create_vote_intent(request)

    assert response.plugin_id == "resonantos_wallet"
    assert response.intent_type == "governance_vote"
    assert response.created_at == "2026-03-10T15:30:00Z"
    assert response.execution_mode == "external_signer_required"
    assert response.ready_for_submission is False
    assert response.submitted is False
    assert response.normalized_payload.model_dump(mode="json") == {
        "voter_account": {
            "account_ref": "wallet://governance",
            "chain": "solana",
            "network": "mainnet-beta",
        },
        "proposal_id": "proposal-42",
        "vote_choice": "approve",
        "rationale": "aligns with treasury policy",
    }
