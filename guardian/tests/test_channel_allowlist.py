from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from guardian.channels import allowlist


@pytest.fixture(autouse=True)
def _reset() -> None:
    allowlist.reset_state()


def test_create_pairing_code_returns_string() -> None:
    code = allowlist.create_pairing_code("sender-1", "channel-1", ttl_seconds=60)
    assert isinstance(code, str)
    assert code


def test_redeem_pairing_code_before_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 2, 7, tzinfo=timezone.utc)
    monkeypatch.setattr(allowlist, "_utcnow", lambda: now)
    code = allowlist.create_pairing_code("sender-1", "channel-1", ttl_seconds=60)

    sender_id, channel_id = allowlist.redeem_pairing_code(code)

    assert (sender_id, channel_id) == ("sender-1", "channel-1")
    assert allowlist.is_allowed("sender-1", "channel-1")


def test_redeem_pairing_code_after_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 2, 7, tzinfo=timezone.utc)
    monkeypatch.setattr(allowlist, "_utcnow", lambda: now)
    code = allowlist.create_pairing_code("sender-1", "channel-1", ttl_seconds=1)
    monkeypatch.setattr(allowlist, "_utcnow", lambda: now + timedelta(seconds=2))

    with pytest.raises(allowlist.PairingCodeError, match="expired"):
        allowlist.redeem_pairing_code(code)


def test_redeem_pairing_code_single_use(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 2, 7, tzinfo=timezone.utc)
    monkeypatch.setattr(allowlist, "_utcnow", lambda: now)
    code = allowlist.create_pairing_code("sender-1", "channel-1", ttl_seconds=60)

    allowlist.redeem_pairing_code(code)

    with pytest.raises(allowlist.PairingCodeError, match="already used"):
        allowlist.redeem_pairing_code(code)

