"""Minimal Playwright-backed bridge used by browser session manager."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class BrowserPageBridge(Protocol):
    """Small, explicit surface exposed to the session manager."""

    def navigate(self, url: str) -> None:
        ...

    def screenshot(self, path: str | None = None) -> bytes:
        ...

    def click(self, selector: str) -> None:
        ...

    def type(self, selector: str, text: str, clear: bool = False) -> None:
        ...

    def content(self) -> str:
        ...

    def close(self) -> None:
        ...


class PlaywrightNotAvailableError(RuntimeError):
    """Raised when Playwright is not importable in this environment."""


class PlaywrightBridge:
    """Bridge backed by a persistent Chromium context."""

    def __init__(self, profile_dir: Path) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - env-dependent
            raise PlaywrightNotAvailableError(
                "Playwright is not installed in this environment"
            ) from exc

        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
        )
        pages = self._context.pages
        self._page = pages[0] if pages else self._context.new_page()

    def navigate(self, url: str) -> None:
        self._page.goto(url, wait_until="domcontentloaded")

    def screenshot(self, path: str | None = None) -> bytes:
        return self._page.screenshot(path=path)

    def click(self, selector: str) -> None:
        self._page.click(selector)

    def type(self, selector: str, text: str, clear: bool = False) -> None:
        if clear:
            self._page.fill(selector, "")
        self._page.fill(selector, text)

    def content(self) -> str:
        return self._page.content()

    def close(self) -> None:
        self._context.close()
        self._playwright.stop()


__all__ = [
    "BrowserPageBridge",
    "PlaywrightBridge",
    "PlaywrightNotAvailableError",
]
