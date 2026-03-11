"""
Manifest declaration for the ResonantOS wallet scaffold plugin.
"""

from __future__ import annotations

from .types import WalletPluginManifest

RESONANTOS_WALLET_MANIFEST = WalletPluginManifest(
    id="resonantos_wallet",
    name="ResonantOS Wallet",
    version="0.1.0",
    enabled=False,
    autoload=False,
    status="disabled",
    wiring_status="not_wired",
    runtime_mode="external_bridge",
    signing_mode="delegated_signer",
    description=(
        "Scaffold-only plumbing for a future ResonantOS wallet bridge. "
        "This package is importable in isolation for tests and future wiring, "
        "but it is not loaded, registered, or invoked by Codexify startup."
    ),
    capabilities=[
        {
            "id": "wallet_summary_read",
            "category": "read_model",
            "description": (
                "Future wallet summary read-model contract only; no RPC wiring "
                "or signer interaction is implemented here."
            ),
        },
        {
            "id": "recent_transaction_read",
            "category": "read_model",
            "description": (
                "Future recent transaction read-model contract only; no network "
                "calls are performed by this scaffold."
            ),
        },
        {
            "id": "transfer_intent_create",
            "category": "intent",
            "description": (
                "Builds unsigned transfer intent payloads for an external "
                "delegated signer bridge."
            ),
        },
        {
            "id": "governance_vote_intent_create",
            "category": "intent",
            "description": (
                "Builds unsigned governance vote intent payloads for an "
                "external delegated signer bridge."
            ),
        },
    ],
    security_note=(
        "Private key custody, direct signing, and transaction submission are "
        "externalized. This scaffold is limited to read-model and unsigned "
        "intent plumbing."
    ),
)
