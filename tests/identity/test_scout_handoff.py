import base64
import hashlib
import json

import pytest

from guardian.core.scout_handoff import (
    HandoffUnavailable,
    ScoutHandoffStore,
    challenge_for,
)


class AtomicFixture:
    """Unit storage fixture; live Redis Lua qualification remains separate."""

    def __init__(self):
        self.values = {}
        self.expiry = {}

    def set(self, key, value, *, ex, nx):
        assert nx
        self.values[key] = value
        self.expiry[key] = ex
        return True

    def eval(self, script, key_count, key, challenge):
        assert key_count == 1
        value = self.values.get(key)
        if value and json.loads(value)["challenge"] == challenge:
            return self.values.pop(key)
        return None


def test_pkce_verifier_and_single_use_preserve_existing_session():
    client = AtomicFixture()
    store = ScoutHandoffStore(client)
    verifier = "v" * 43
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert challenge_for(verifier) == expected
    code = store.create(
        challenge=expected,
        state="s" * 43,
        token="fixture-existing-account",
        user_id="fixture-user",
        expires_at=123,
    )
    assert list(client.expiry.values()) == [60]
    assert "fixture-existing-account" not in next(iter(client.values))
    with pytest.raises(HandoffUnavailable):
        store.consume(code=code, verifier="w" * 43)
    grant = store.consume(code=code, verifier=verifier)
    assert grant["token"] == "fixture-existing-account"
    assert grant["user_id"] == "fixture-user"
    with pytest.raises(HandoffUnavailable):
        store.consume(code=code, verifier=verifier)


def test_expired_missing_or_malformed_grants_fail_closed():
    store = ScoutHandoffStore(AtomicFixture())
    for code in ("c" * 43, "", "../other", "c" * 44):
        with pytest.raises(HandoffUnavailable):
            store.consume(code=code, verifier="v" * 43)
    for verifier in ("", "v" * 42, "v" * 129, "=" * 43):
        with pytest.raises(HandoffUnavailable):
            challenge_for(verifier)
