"""Browser session manager with TTL, allowlist, and session limits."""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from guardian.browser.cdp_bridge import BrowserPageBridge, PlaywrightBridge

_DEFAULT_STORAGE_BASE_PATH = "/app/media"
_DEFAULT_MAX_SESSIONS = 2
_DEFAULT_TTL_SECONDS = 900


class BrowserSessionError(RuntimeError):
    """Base browser session error."""


class BrowserSessionNotFoundError(BrowserSessionError):
    """Raised when the requested session does not exist."""


class BrowserSessionExpiredError(BrowserSessionError):
    """Raised when the requested session is expired."""


class BrowserSessionLimitExceededError(BrowserSessionError):
    """Raised when max sessions constraint is reached."""


class BrowserAllowlistViolationError(BrowserSessionError):
    """Raised when navigating to a non-allowlisted host."""


@dataclass
class ManagedBrowserSession:
    session_id: str
    profile_dir: Path
    bridge: BrowserPageBridge
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BrowserSessionManager:
    """Manages lifecycle and policy checks for browser sessions."""

    def __init__(
        self,
        *,
        storage_base_path: str | Path | None = None,
        max_sessions: int | None = None,
        ttl_seconds: int | None = None,
        url_allowlist: list[str] | None = None,
        bridge_factory: Callable[[Path], BrowserPageBridge] | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        resolved_base = storage_base_path or os.getenv(
            "STORAGE_BASE_PATH", _DEFAULT_STORAGE_BASE_PATH
        )
        self._profiles_root = Path(resolved_base) / "browser_profiles"
        self._profiles_root.mkdir(parents=True, exist_ok=True)

        self._max_sessions = int(
            max_sessions
            if max_sessions is not None
            else os.getenv("BROWSER_MAX_SESSIONS", _DEFAULT_MAX_SESSIONS)
        )
        self._ttl_seconds = int(
            ttl_seconds
            if ttl_seconds is not None
            else os.getenv("BROWSER_SESSION_TTL_SECONDS", _DEFAULT_TTL_SECONDS)
        )
        self._allowlist = url_allowlist or self._parse_allowlist(
            os.getenv("BROWSER_URL_ALLOWLIST", "")
        )
        self._bridge_factory = bridge_factory or PlaywrightBridge
        self._now_fn = now_fn or _utc_now
        self._sessions: dict[str, ManagedBrowserSession] = {}

    @property
    def profiles_root(self) -> Path:
        return self._profiles_root

    def create_session(self) -> ManagedBrowserSession:
        self.prune_expired_sessions()
        if len(self._sessions) >= self._max_sessions:
            raise BrowserSessionLimitExceededError(
                f"session limit exceeded (max={self._max_sessions})"
            )

        session_id = str(uuid.uuid4())
        profile_dir = self._profiles_root / session_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        bridge = self._bridge_factory(profile_dir)

        now = self._now_fn()
        session = ManagedBrowserSession(
            session_id=session_id,
            profile_dir=profile_dir,
            bridge=bridge,
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> ManagedBrowserSession:
        self.prune_expired_sessions()
        session = self._sessions.get(session_id)
        if session is None:
            raise BrowserSessionNotFoundError(f"session not found: {session_id}")
        self._touch(session)
        return session

    def list_sessions(self) -> list[ManagedBrowserSession]:
        self.prune_expired_sessions()
        return list(self._sessions.values())

    def close_session(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        session.bridge.close()
        shutil.rmtree(session.profile_dir, ignore_errors=True)
        return True

    def prune_expired_sessions(self) -> list[str]:
        now = self._now_fn()
        expired: list[str] = []
        for session_id, session in list(self._sessions.items()):
            if now >= session.expires_at:
                self.close_session(session_id)
                expired.append(session_id)
        return expired

    def navigate(self, session_id: str, url: str) -> None:
        self._ensure_url_allowed(url)
        session = self.get_session(session_id)
        session.bridge.navigate(url)

    def screenshot(self, session_id: str, path: str | None = None) -> bytes:
        session = self.get_session(session_id)
        return session.bridge.screenshot(path=path)

    def click(self, session_id: str, selector: str) -> None:
        session = self.get_session(session_id)
        session.bridge.click(selector)

    def type(
        self,
        session_id: str,
        selector: str,
        text: str,
        *,
        clear: bool = False,
    ) -> None:
        session = self.get_session(session_id)
        session.bridge.type(selector, text, clear=clear)

    def content(self, session_id: str) -> str:
        session = self.get_session(session_id)
        return session.bridge.content()

    def _touch(self, session: ManagedBrowserSession) -> None:
        now = self._now_fn()
        if now >= session.expires_at:
            self.close_session(session.session_id)
            raise BrowserSessionExpiredError(
                f"session expired: {session.session_id}"
            )
        session.last_used_at = now

    def _ensure_url_allowed(self, url: str) -> None:
        host = (urlparse(url).hostname or "").strip().lower()
        if not host:
            raise BrowserAllowlistViolationError("url missing hostname")
        if not self._allowlist:
            raise BrowserAllowlistViolationError(
                "url allowlist is empty; navigation is blocked"
            )
        for pattern in self._allowlist:
            if pattern.startswith("*."):
                suffix = pattern[1:]
                if host.endswith(suffix):
                    return
            elif host == pattern:
                return
        raise BrowserAllowlistViolationError(
            f"host not allowlisted: {host}"
        )

    @staticmethod
    def _parse_allowlist(value: str) -> list[str]:
        return [
            part.strip().lower()
            for part in value.split(",")
            if part.strip()
        ]


__all__ = [
    "BrowserAllowlistViolationError",
    "BrowserSessionError",
    "BrowserSessionExpiredError",
    "BrowserSessionLimitExceededError",
    "BrowserSessionManager",
    "BrowserSessionNotFoundError",
    "ManagedBrowserSession",
]
