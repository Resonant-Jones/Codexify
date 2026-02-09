from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from guardian.browser.session_manager import (
    BrowserAllowlistViolationError,
    BrowserSessionLimitExceededError,
    BrowserSessionManager,
    BrowserSessionNotFoundError,
)


@dataclass
class _FakeClock:
    now: datetime = field(
        default_factory=lambda: datetime(2026, 2, 7, tzinfo=timezone.utc)
    )

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


class _FakeBridge:
    def __init__(self, profile_dir: Path) -> None:
        self.profile_dir = profile_dir
        self.closed = False
        self.last_url: str | None = None

    def navigate(self, url: str) -> None:
        self.last_url = url

    def screenshot(self, path: str | None = None) -> bytes:
        if path:
            Path(path).write_bytes(b"img")
        return b"img"

    def click(self, selector: str) -> None:
        _ = selector

    def type(self, selector: str, text: str, clear: bool = False) -> None:
        _ = (selector, text, clear)

    def content(self) -> str:
        return "<html></html>"

    def close(self) -> None:
        self.closed = True


def _manager(tmp_path: Path, clock: _FakeClock) -> BrowserSessionManager:
    return BrowserSessionManager(
        storage_base_path=tmp_path,
        max_sessions=2,
        ttl_seconds=30,
        url_allowlist=["example.com", "*.example.org"],
        bridge_factory=lambda profile: _FakeBridge(profile),
        now_fn=clock,
    )


def test_session_lifecycle_create_get_list_close(tmp_path: Path) -> None:
    clock = _FakeClock()
    manager = _manager(tmp_path, clock)

    session = manager.create_session()
    assert session.session_id
    assert session.profile_dir.exists()
    assert len(manager.list_sessions()) == 1

    fetched = manager.get_session(session.session_id)
    assert fetched.session_id == session.session_id

    assert manager.close_session(session.session_id) is True
    assert manager.close_session(session.session_id) is False
    with pytest.raises(BrowserSessionNotFoundError):
        manager.get_session(session.session_id)


def test_max_sessions_enforced(tmp_path: Path) -> None:
    clock = _FakeClock()
    manager = _manager(tmp_path, clock)
    manager.create_session()
    manager.create_session()

    with pytest.raises(BrowserSessionLimitExceededError):
        manager.create_session()


def test_ttl_expiration_prunes_and_closes(tmp_path: Path) -> None:
    clock = _FakeClock()
    manager = _manager(tmp_path, clock)
    session = manager.create_session()
    bridge = session.bridge
    profile_dir = session.profile_dir

    clock.advance(31)
    expired = manager.prune_expired_sessions()

    assert session.session_id in expired
    assert bridge.closed is True
    assert not profile_dir.exists()
    assert manager.list_sessions() == []


def test_allowlist_blocks_forbidden_hosts(tmp_path: Path) -> None:
    clock = _FakeClock()
    manager = _manager(tmp_path, clock)
    session = manager.create_session()

    manager.navigate(session.session_id, "https://example.com/path")

    with pytest.raises(BrowserAllowlistViolationError):
        manager.navigate(session.session_id, "https://forbidden.local/path")
