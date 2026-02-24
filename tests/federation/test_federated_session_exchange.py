"""Tests for federation manifest signing, token exchange, and relay channels.

Tests cover:
- Manifest generation and signing/verification
- JWT token exchange between nodes
- Relay session lifecycle management
- Message forwarding between nodes
- Error handling (expired tokens, invalid signatures, rate limiting)
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from guardian.core.auth import sign_federation_trust_policy
from guardian.federation.manager import FederationManager, RelaySession
from guardian.federation.manifest import (
    NodeManifest,
    generate_keypair,
    private_key_from_b64,
    public_key_from_b64,
    sign_manifest,
    verify_manifest,
)


def _signed_federation_settings(
    *,
    enabled: bool = True,
    require_signed_policy: bool = True,
    policy: dict | None = None,
) -> SimpleNamespace:
    policy_dict = policy or {
        "allowed_origins": ["https://peer.example.com"],
        "allowed_nodes": ["node-beta"],
        "allow_open_enrollment": False,
    }
    policy_json = json.dumps(policy_dict)
    signature = (
        sign_federation_trust_policy(policy_json, "policy-secret")
        if require_signed_policy
        else None
    )
    return SimpleNamespace(
        GUARDIAN_FEDERATION_ENABLED=enabled,
        GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY=require_signed_policy,
        GUARDIAN_FEDERATION_TRUST_POLICY_JSON=policy_json,
        GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE=signature,
        GUARDIAN_FEDERATION_POLICY_SIGNING_KEY="policy-secret",
    )


from guardian.routes.federation import (
    SessionRequestBody,
    accept_session,
    configure_federation,
)
from guardian.routes.federation import manager as route_manager
from guardian.routes.federation import request_session


class TestManifestSigningAndVerification:
    """Test NodeManifest signing and verification."""

    def test_generate_keypair(self):
        """Test keypair generation."""
        private_key, public_key = generate_keypair()

        assert private_key is not None
        assert public_key is not None
        assert len(private_key) > 0
        assert len(public_key) > 0
        assert private_key != public_key

    def test_sign_manifest(self):
        """Test manifest signing."""
        private_key, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key,
            capabilities=["share", "collab"],
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )

        signature = sign_manifest(manifest, private_key)
        assert signature is not None
        assert len(signature) > 0

    def test_verify_manifest_valid_signature(self):
        """Test verification of valid manifest signature."""
        private_key, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key,
            capabilities=["share", "collab"],
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )

        signature = sign_manifest(manifest, private_key)
        manifest.signature = signature

        assert verify_manifest(manifest) is True

    def test_verify_manifest_invalid_signature(self):
        """Test verification fails with invalid signature."""
        private_key, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key,
            capabilities=["share", "collab"],
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
            signature="invalid_signature_base64==",
        )

        assert verify_manifest(manifest) is False

    def test_verify_manifest_no_signature(self):
        """Test verification fails without signature."""
        private_key, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key,
            capabilities=["share", "collab"],
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )

        assert verify_manifest(manifest) is False

    def test_manifest_signature_tamper_detection(self):
        """Test that tampering is detected."""
        private_key1, public_key1 = generate_keypair()
        private_key2, public_key2 = generate_keypair()

        # Sign with key1
        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key1,
            capabilities=["share", "collab"],
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )
        signature = sign_manifest(manifest, private_key1)

        # Try to verify with key2
        manifest_tampered = NodeManifest(
            node_id="node-alpha",
            public_key=public_key2,  # Different key
            capabilities=["share", "collab"],
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
            signature=signature,
        )

        assert verify_manifest(manifest_tampered) is False


class TestJWTTokenExchange:
    """Test JWT token generation and verification."""

    def test_create_federation_token(self):
        """Test JWT token creation."""
        private_key, _ = generate_keypair()

        token_payload = {
            "relay_id": "relay-123",
            "source_node_id": "node-alpha",
            "target_node_id": "node-beta",
            "document_id": "doc-456",
            "thread_id": "thread-789",
            "user_id": "user-001",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "nonce": secrets.token_hex(16),
        }

        token = jwt.encode(
            token_payload, private_key_from_b64(private_key), algorithm="EdDSA"
        )
        assert token is not None
        assert len(token) > 0

    def test_verify_jwt_token_valid(self):
        """Test JWT token verification with valid token."""
        private_key, public_key = generate_keypair()

        token_payload = {
            "relay_id": "relay-123",
            "source_node_id": "node-alpha",
            "document_id": "doc-456",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        token = jwt.encode(
            token_payload, private_key_from_b64(private_key), algorithm="EdDSA"
        )
        decoded = jwt.decode(
            token, public_key_from_b64(public_key), algorithms=["EdDSA"]
        )

        assert decoded["relay_id"] == "relay-123"
        assert decoded["source_node_id"] == "node-alpha"
        assert decoded["document_id"] == "doc-456"

    def test_jwt_token_expiration(self):
        """Test JWT token expiration validation."""
        private_key, public_key = generate_keypair()

        # Token already expired
        token_payload = {
            "relay_id": "relay-123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }

        token = jwt.encode(
            token_payload, private_key_from_b64(private_key), algorithm="EdDSA"
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token, public_key_from_b64(public_key), algorithms=["EdDSA"]
            )

    def test_jwt_token_wrong_key(self):
        """Test JWT verification fails with wrong key."""
        private_key1, _ = generate_keypair()
        _private_key2, public_key2 = generate_keypair()

        token_payload = {"relay_id": "relay-123"}
        token = jwt.encode(
            token_payload, private_key_from_b64(private_key1), algorithm="EdDSA"
        )

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                token, public_key_from_b64(public_key2), algorithms=["EdDSA"]
            )


class TestFederationManager:
    """Test FederationManager relay session management."""

    def test_create_relay_session(self):
        """Test creating a relay session."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
            thread_id="thread-789",
            ttl_seconds=3600,
        )

        assert relay.relay_id == "relay-123"
        assert relay.source_node_id == "node-alpha"
        assert relay.target_node_id == "node-beta"
        assert relay.document_id == "doc-456"
        assert relay.thread_id == "thread-789"
        assert not relay.is_expired()

    def test_get_relay_session(self):
        """Test retrieving an existing relay session."""
        manager = FederationManager()

        manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        relay = manager.get_relay_session("relay-123")
        assert relay is not None
        assert relay.relay_id == "relay-123"

    def test_get_nonexistent_relay_session(self):
        """Test retrieving nonexistent relay returns None."""
        manager = FederationManager()
        relay = manager.get_relay_session("nonexistent")
        assert relay is None

    def test_relay_session_expiration(self):
        """Test relay session expiration detection."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
            ttl_seconds=1,  # Very short TTL
        )

        # Manually expire the session
        relay.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        assert relay.is_expired() is True

        # Getting expired session returns None and cleans up
        retrieved = manager.get_relay_session("relay-123")
        assert retrieved is None

    def test_connect_relay_source(self):
        """Test connecting source WebSocket to relay."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        ws_mock = MagicMock()
        result = manager.connect_relay_source("relay-123", ws_mock)

        assert result is True
        assert relay.source_ws == ws_mock

    def test_connect_relay_target(self):
        """Test connecting target WebSocket to relay."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        ws_mock = MagicMock()
        result = manager.connect_relay_target("relay-123", ws_mock)

        assert result is True
        assert relay.target_ws == ws_mock

    def test_close_relay_session(self):
        """Test closing a relay session."""
        manager = FederationManager()

        manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        manager.close_relay_session("relay-123")

        relay = manager.get_relay_session("relay-123")
        assert relay is None

    def test_relay_session_is_active(self):
        """Test relay active status."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="jwt_token_here",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        assert relay.is_active() is False

        # Connect both sides
        ws_source = MagicMock()
        ws_target = MagicMock()
        manager.connect_relay_source("relay-123", ws_source)
        manager.connect_relay_target("relay-123", ws_target)

        assert relay.is_active() is True

    def test_cache_peer_manifest(self):
        """Test caching peer manifests."""
        manager = FederationManager()
        _, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-beta",
            public_key=public_key,
            capabilities=["share", "collab"],
            relay_endpoint="wss://beta.example.com/api/federation/relay",
        )

        manager.cache_peer_manifest(manifest)

        cached = manager.get_peer_manifest("node-beta")
        assert cached is not None
        assert cached.node_id == "node-beta"

    def test_rate_limiting(self):
        """Test rate limiting for federation requests."""
        manager = FederationManager()

        # First 10 requests should pass
        for i in range(10):
            assert (
                manager.check_rate_limit(
                    "node-beta", limit=10, window_seconds=60
                )
                is True
            )

        # 11th request should fail
        assert (
            manager.check_rate_limit("node-beta", limit=10, window_seconds=60)
            is False
        )

    def test_get_active_relay_count(self):
        """Test counting active relay sessions."""
        manager = FederationManager()

        manager.create_relay_session(
            relay_id="relay-1",
            token="token1",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-1",
        )

        manager.create_relay_session(
            relay_id="relay-2",
            token="token2",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-2",
        )

        assert manager.get_active_relay_count() == 2

    def test_verify_relay_token(self):
        """Test token verification in manager."""
        manager = FederationManager()
        private_key, public_key = generate_keypair()

        token_payload = {"relay_id": "relay-123", "document_id": "doc-456"}
        token = jwt.encode(
            token_payload, private_key_from_b64(private_key), algorithm="EdDSA"
        )

        payload = manager.verify_relay_token(
            token, public_key_from_b64(public_key)
        )
        assert payload["relay_id"] == "relay-123"
        assert payload["document_id"] == "doc-456"

    def test_verify_invalid_relay_token(self):
        """Test verification of invalid token returns None."""
        manager = FederationManager()
        payload = manager.verify_relay_token("invalid_token", "secret")
        assert payload is None


class TestRelaySessionPresenceTracking:
    """Test presence tracking in relay sessions."""

    def test_track_presence_join(self):
        """Test tracking user join in relay."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="token",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        assert len(relay.active_users) == 0

        # Simulate presence.join
        relay.active_users.add("user-001")
        relay.active_users.add("user-002")

        assert len(relay.active_users) == 2
        assert "user-001" in relay.active_users
        assert "user-002" in relay.active_users

    def test_track_presence_leave(self):
        """Test tracking user leave in relay."""
        manager = FederationManager()

        relay = manager.create_relay_session(
            relay_id="relay-123",
            token="token",
            source_node_id="node-alpha",
            target_node_id="node-beta",
            document_id="doc-456",
        )

        relay.active_users.add("user-001")
        relay.active_users.add("user-002")

        relay.active_users.discard("user-001")

        assert len(relay.active_users) == 1
        assert "user-001" not in relay.active_users
        assert "user-002" in relay.active_users


class TestFederationConfiguration:
    """Test federation configuration."""

    def test_configure_federation(self):
        """Test configuring federation."""
        private_key, public_key = generate_keypair()

        configure_federation(
            node_id="node-alpha",
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
            private_key=private_key,
            public_key=public_key,
        )

        # Configuration successful if no exception raised
        assert True

    def test_configure_federation_auto_keypair(self):
        """Test federation auto-generates keypair if not provided."""
        configure_federation(
            node_id="node-alpha",
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )

        # Configuration should succeed with auto-generated keys
        assert True

    @pytest.mark.asyncio
    async def test_request_session_blocked_when_federation_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        settings = _signed_federation_settings(enabled=False)
        monkeypatch.setattr(
            "guardian.routes.federation.get_settings",
            lambda: settings,
        )

        with pytest.raises(HTTPException) as exc:
            await request_session(
                SessionRequestBody(
                    target_node_url="https://peer.example.com",
                    document_id="doc-123",
                    user_id="user-123",
                )
            )

        assert exc.value.status_code == 403
        assert "disabled" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_request_session_requires_signed_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        settings = _signed_federation_settings()
        settings.GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE = None
        monkeypatch.setattr(
            "guardian.routes.federation.get_settings",
            lambda: settings,
        )

        with pytest.raises(HTTPException) as exc:
            await request_session(
                SessionRequestBody(
                    target_node_url="https://peer.example.com",
                    document_id="doc-123",
                    user_id="user-123",
                )
            )

        assert exc.value.status_code == 503
        assert "signature" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_request_session_rejects_disallowed_target_origin(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        settings = _signed_federation_settings(
            policy={
                "allowed_origins": ["https://trusted.example.com"],
                "allowed_nodes": ["node-beta"],
            }
        )
        monkeypatch.setattr(
            "guardian.routes.federation.get_settings",
            lambda: settings,
        )

        with pytest.raises(HTTPException) as exc:
            await request_session(
                SessionRequestBody(
                    target_node_url="https://peer.example.com",
                    document_id="doc-123",
                    user_id="user-123",
                )
            )

        assert exc.value.status_code == 403
        assert "origin" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_accept_session_rejects_untrusted_source_node(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        private_key, public_key = generate_keypair()
        configure_federation(
            node_id="node-alpha",
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
            private_key=private_key,
            public_key=public_key,
        )
        settings = _signed_federation_settings(
            policy={
                "allowed_origins": ["https://peer.example.com"],
                "allowed_nodes": ["node-trusted"],
            }
        )
        monkeypatch.setattr(
            "guardian.routes.federation.get_settings",
            lambda: settings,
        )
        route_manager.peer_manifests.clear()
        source_private, source_public = generate_keypair()
        route_manager.cache_peer_manifest(
            NodeManifest(
                node_id="node-untrusted",
                public_key=source_public,
                capabilities=["share", "collab"],
                relay_endpoint="wss://untrusted.example.com/api/federation/relay",
            )
        )
        token = jwt.encode(
            {
                "relay_id": "relay-123",
                "source_node_id": "node-untrusted",
                "target_node_id": "node-alpha",
                "document_id": "doc-1",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            },
            private_key_from_b64(source_private),
            algorithm="EdDSA",
        )

        with pytest.raises(HTTPException) as exc:
            await accept_session(relay_id="relay-123", token=token)

        assert exc.value.status_code == 403
        assert "source node" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_request_session_blocked_by_egress_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        settings = _signed_federation_settings()
        monkeypatch.setattr(
            "guardian.routes.federation.get_settings",
            lambda: settings,
        )
        private_key, public_key = generate_keypair()
        configure_federation(
            node_id="node-alpha",
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
            private_key=private_key,
            public_key=public_key,
        )
        monkeypatch.delenv("CODEXIFY_LOCAL_ONLY_MODE", raising=False)
        monkeypatch.delenv("CODEXIFY_EGRESS_ALLOWLIST", raising=False)

        with pytest.raises(HTTPException) as exc:
            await request_session(
                SessionRequestBody(
                    target_node_url="https://peer.example.com",
                    document_id="doc-123",
                    user_id="user-123",
                )
            )

        assert exc.value.status_code == 403
        assert "LOCAL_ONLY_MODE" in str(exc.value.detail)


class TestManifestCapabilities:
    """Test manifest capability checking."""

    def test_manifest_default_capabilities(self):
        """Test manifest has default capabilities."""
        _, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key,
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )

        assert "share" in manifest.capabilities
        assert "collab" in manifest.capabilities
        assert "autosave" in manifest.capabilities

    def test_manifest_custom_capabilities(self):
        """Test manifest with custom capabilities."""
        _, public_key = generate_keypair()

        manifest = NodeManifest(
            node_id="node-alpha",
            public_key=public_key,
            capabilities=["share"],  # Only share capability
            relay_endpoint="wss://alpha.example.com/api/federation/relay",
        )

        assert "share" in manifest.capabilities
        assert "collab" not in manifest.capabilities
