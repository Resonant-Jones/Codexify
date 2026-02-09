from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from guardian.browser.session_manager import (
    BrowserAllowlistViolationError,
    BrowserSessionManager,
)


class _NoopBridge:
    def __init__(self, profile_dir: Path) -> None:
        self._profile_dir = profile_dir

    def navigate(self, url: str) -> None:
        _ = url

    def screenshot(self, path: str | None = None) -> bytes:
        _ = path
        return b""

    def click(self, selector: str) -> None:
        _ = selector

    def type(self, selector: str, text: str, clear: bool = False) -> None:
        _ = (selector, text, clear)

    def content(self) -> str:
        return ""

    def close(self) -> None:
        return None


def test_navigation_blocked_when_allowlist_empty(tmp_path: Path) -> None:
    manager = BrowserSessionManager(
        storage_base_path=tmp_path,
        max_sessions=1,
        ttl_seconds=60,
        url_allowlist=[],
        bridge_factory=lambda profile: _NoopBridge(profile),
        now_fn=lambda: datetime(2026, 2, 7, tzinfo=timezone.utc),
    )
    session = manager.create_session()

    with pytest.raises(BrowserAllowlistViolationError):
        manager.navigate(session.session_id, "https://example.com")
