"""Deterministic fixture HTTP server for the Browser Host comparative proof harness.

Serves only the bounded in-memory fixture route table.  Rejects arbitrary
filesystem access, path traversal, wildcard CORS, and proxy requests.

Every server instance binds loopback-only on an ephemeral port.
"""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

from .fixtures import (
    FIXTURES,
    FIXTURE_BY_ROUTE,
    FIXTURE_VERSION,
    FixtureRecord,
    OriginRole,
    _basic_visible_page,
    _cross_origin_iframe_origin_a,
    _download_attempt_page,
    _form_secret_page,
    _navigation_race_page,
    _origin_b_iframe_body,
    _origin_change_page,
    _oversized_page,
    _popup_attempt_page,
    _prompt_injection_page,
    _protected_target_metadata,
    _renderer_failure_page,
)

# A small harmless download payload.
_DOWNLOAD_CONTENT = b"This is a deterministic harmless download test payload.\n"


class FixtureServerError(Exception):
    """Raised when fixture server operations fail."""


# Map fixture-id -> html generator for the two origins.
_FIXTURE_GENERATORS: dict[str, Callable[[], tuple[str, str]]] = {
    "basic-visible": _basic_visible_page,
    "prompt-injection": _prompt_injection_page,
    "form-secret": _form_secret_page,
    "cross-origin-iframe": _cross_origin_iframe_origin_a,
    "origin-b-iframe-body": _origin_b_iframe_body,
    "oversized": _oversized_page,
    "navigation-race": _navigation_race_page,
    "origin-change": _origin_change_page,
    "popup-attempt": _popup_attempt_page,
    "download-attempt": _download_attempt_page,
    "renderer-failure": _renderer_failure_page,
    "protected-target": _protected_target_metadata,
}


def _build_manifest(origin_a_base: str, origin_b_base: str) -> dict:
    entries: list[dict] = []
    for f in FIXTURES:
        base = origin_a_base if f.requires_origin_a else origin_b_base
        entries.append(
            {
                "fixtureId": f.fixture_id,
                "fixtureVersion": f.fixture_version,
                "route": f.relative_route,
                "origin": f.expected_origin.value,
                "originUrl": urljoin(base, f.relative_route),
                "expectedTitle": f.expected_title,
                "visibleTextHash": f.visible_text_hash,
                "expectedExcluded": sorted(f.expected_excluded),
                "expectedPosture": f.expected_posture.value,
                "flags": sorted(flag.value for flag in f.flags),
            }
        )
    return {
        "fixtureVersion": FIXTURE_VERSION,
        "fixtures": entries,
    }


def _build_fixture_html(fixture: FixtureRecord, origin_b_base: str) -> bytes:
    gen = _FIXTURE_GENERATORS.get(fixture.fixture_id)
    if gen is None:
        raise FixtureServerError(f"No generator for fixture {fixture.fixture_id}")

    html, _ = gen()

    # Substitute origin-b placeholder for cross-origin iframe
    if "__FIXTURE_B_ORIGIN__" in html:
        html = html.replace("__FIXTURE_B_ORIGIN__", origin_b_base.rstrip("/"))

    return html.encode("utf-8")


class _FixtureRequestHandler(BaseHTTPRequestHandler):
    """Loopback-only handler serving deterministic fixture content."""

    # Set by the server instance before serving
    origin_role: OriginRole = OriginRole.ORIGIN_A
    origin_b_base: str = ""
    _safe_logger: Callable[..., None] | None = None

    @staticmethod
    def _log_safe(component: str, **kwargs: object) -> None:
        """Bridge to the module-level safe logger."""
        # Overridden per-handler class; default no-op
        return

    def log_message(self, fmt, *args):  # type: ignore[override]
        self._log_safe("fixture_server", route=args[0] if args else "-", status=self.command)
        # Suppress default stderr log

    def _reject_traversal(self) -> bool:
        """Return True and send 403 if path contains traversal attempts."""
        path = self.path or "/"
        if ".." in path or "//" in path or "\\" in path:
            self.send_error(403, "Forbidden")
            return True
        return False

    def _set_cors(self, status_only: bool = False) -> None:
        if not status_only:
            self.send_header("Access-Control-Allow-Origin", "null")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _send_html(self, content: bytes, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._set_cors()
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._set_cors(status_only=True)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self._reject_traversal():
            return

        path = self.path or "/"

        if path == "/favicon.ico":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # Fixture manifest
        if path == "/manifest.json":
            origin_a = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"
            manifest = _build_manifest(origin_a, self.origin_b_base)
            self._send_json(manifest)
            return

        # Health / root
        if path == "/" or path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "originRole": self.origin_role.value,
                    "fixtureVersion": FIXTURE_VERSION,
                }
            )
            return

        # Download test file
        if path == "/download-test.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="harmless-test.txt"')
            self._set_cors()
            self.send_header("Content-Length", str(len(_DOWNLOAD_CONTENT)))
            self.end_headers()
            self.wfile.write(_DOWNLOAD_CONTENT)
            return

        # Fixture pages
        fixture = FIXTURE_BY_ROUTE.get(path)
        if fixture is not None:
            # Only serve fixtures belonging to this origin
            if fixture.expected_origin != self.origin_role:
                self.send_error(404, "Fixture not available on this origin")
                return
            html = _build_fixture_html(fixture, self.origin_b_base)
            self._send_html(html)
            return

        # Not found
        self.send_error(404, f"No fixture at {path}")

    def do_POST(self) -> None:
        self.send_error(405, "Method not allowed")


class FixtureServer:
    """Loopback-only HTTP server serving the deterministic fixture corpus.

    Each instance serves either Origin A or Origin B fixtures.  All requests
    are handled purely from in-memory content; no filesystem access occurs.
    """

    def __init__(self, origin_role: OriginRole, safe_logger: Callable[..., None] | None = None):
        self.origin_role = origin_role
        self._safe_logger = safe_logger
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int = 0

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    def start(self, origin_b_base: str = "") -> None:
        """Start the fixture server on a loopback ephemeral port."""
        handler = _make_handler(
            self.origin_role, origin_b_base, self._safe_logger
        )
        self._httpd = HTTPServer(("127.0.0.1", 0), handler)
        self._port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shut down the fixture server."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._port = 0

    def is_running(self) -> bool:
        return self._httpd is not None and self._port > 0


def _make_handler(
    origin_role: OriginRole,
    origin_b_base: str,
    safe_logger_fn: Callable[..., None] | None,
) -> type[_FixtureRequestHandler]:
    """Create a handler class pre-configured with origin role and safe logger."""

    if safe_logger_fn is not None:

        def _log_bridge(component: str, **kwargs: object) -> None:
            safe_logger_fn(component=component, **kwargs)

    else:

        def _log_bridge(component: str, **kwargs: object) -> None:
            return

    _log_safe_sm = staticmethod(_log_bridge)

    class ConfiguredHandler(_FixtureRequestHandler):
        _log_safe = _log_safe_sm

    ConfiguredHandler.origin_role = origin_role  # type: ignore[attr-defined]
    ConfiguredHandler.origin_b_base = origin_b_base  # type: ignore[attr-defined]
    return ConfiguredHandler
