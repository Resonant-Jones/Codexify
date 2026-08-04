"""Fixture server tests.

Proves loopback binding, ephemeral ports, deterministic responses, CORS
posture, traversal rejection, and clean shutdown.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error

import pytest

from scripts.browser_host_harness.fixtures import (
    FIXTURE_VERSION,
    FIXTURE_BY_ID,
    OriginRole,
)
from scripts.browser_host_harness.fixture_server import FixtureServer


@pytest.fixture
def origin_a():
    """Start an Origin A fixture server on ephemeral port."""
    srv = FixtureServer(OriginRole.ORIGIN_A)
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
def origin_b():
    """Start an Origin B fixture server on ephemeral port."""
    srv = FixtureServer(OriginRole.ORIGIN_B)
    srv.start()
    yield srv
    srv.stop()


class TestFixtureServerBinding:
    def test_loopback_binding(self, origin_a):
        assert origin_a.port > 0
        assert origin_a.base_url.startswith("http://127.0.0.1:")

    def test_ephemeral_ports_are_distinct(self, origin_a, origin_b):
        assert origin_a.port != origin_b.port

    def test_is_running(self, origin_a):
        assert origin_a.is_running()

    def test_stop(self):
        srv = FixtureServer(OriginRole.ORIGIN_A)
        srv.start()
        assert srv.is_running()
        srv.stop()
        assert not srv.is_running()
        assert srv.port == 0


class TestFixtureServerManifest:
    def test_manifest_returns_json(self, origin_a):
        url = f"{origin_a.base_url}/manifest.json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
        assert data["fixtureVersion"] == FIXTURE_VERSION
        assert "fixtures" in data
        # Manifest lists all fixtures with their origin roles
        assert len(data["fixtures"]) == 12

    def test_health(self, origin_a):
        url = f"{origin_a.base_url}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["originRole"] == OriginRole.ORIGIN_A.value


class TestFixtureServerPages:
    def test_basic_visible_page(self, origin_a):
        url = f"{origin_a.base_url}/basic-visible"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "Basic Visible Page" in body

    def test_prompt_injection_page(self, origin_a):
        url = f"{origin_a.base_url}/prompt-injection"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "Prompt Injection Test Page" in body

    def test_form_secret_page(self, origin_a):
        url = f"{origin_a.base_url}/form-secret"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "Form Secret Page" in body
        # Password value is in the HTML (it's a fixture), but we check content
        assert 'type="password"' in body

    def test_cross_origin_iframe(self, origin_b):
        # Start Origin A with knowledge of Origin B for iframe src substitution
        from scripts.browser_host_harness.fixture_server import FixtureServer
        from scripts.browser_host_harness.fixtures import OriginRole
        origin_a = FixtureServer(OriginRole.ORIGIN_A)
        origin_a.start(origin_b_base=origin_b.base_url)
        try:
            url = f"{origin_a.base_url}/cross-origin-iframe"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "Cross-Origin Iframe Page" in body
            # The iframe src should reference Origin B
            assert origin_b.base_url in body
        finally:
            origin_a.stop()

    def test_origin_b_iframe_body_served_from_b(self, origin_b):
        url = f"{origin_b.base_url}/origin-b-iframe-body"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "Origin B Iframe Body" in body

    def test_oversized_page(self, origin_a):
        url = f"{origin_a.base_url}/oversized"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "Oversized Page" in body
        assert len(body) > 10000  # Should be large

    def test_navigation_race_page(self, origin_a):
        url = f"{origin_a.base_url}/navigation-race"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert "Navigation Race Page" in body
        assert 'data-version="1"' in body

    def test_origin_change_page(self, origin_a):
        url = f"{origin_a.base_url}/origin-change"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert "Origin Change Page" in body
        assert "goto-origin-b" in body

    def test_popup_attempt_page(self, origin_a):
        url = f"{origin_a.base_url}/popup-attempt"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert "Popup Attempt Page" in body
        assert "window.open" in body

    def test_download_attempt_page(self, origin_a):
        url = f"{origin_a.base_url}/download-attempt"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert "Download Attempt Page" in body
        assert "download-test.txt" in body

    def test_renderer_failure_page(self, origin_a):
        url = f"{origin_a.base_url}/renderer-failure"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert "Renderer Failure Trigger" in body
        assert "FAILURE_TRIGGER_ACTIVATED" in body
        assert "Activate Failure Trigger" in body

    def test_protected_target_page(self, origin_a):
        url = f"{origin_a.base_url}/protected-target"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        assert "Protected Target Metadata" in body
        assert "codexify-harness://protected/synthetic" in body


class TestFixtureServerCORS:
    def test_no_wildcard_cors(self, origin_a):
        url = f"{origin_a.base_url}/basic-visible"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "*"

    def test_cache_control_no_store(self, origin_a):
        url = f"{origin_a.base_url}/basic-visible"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            cc = resp.headers.get("Cache-Control", "")
        assert "no-store" in cc

    def test_options(self, origin_a):
        url = f"{origin_a.base_url}/basic-visible"
        req = urllib.request.Request(url, method="OPTIONS")
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 204


class TestFixtureServerRejection:
    def test_traversal_rejected(self, origin_a):
        url = f"{origin_a.base_url}/../etc/passwd"
        req = urllib.request.Request(url)
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 403

    def test_double_dot_dot_slash_rejected(self, origin_a):
        url = f"{origin_a.base_url}/scripts/../../etc/passwd"
        req = urllib.request.Request(url)
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 403

    def test_unknown_route_404(self, origin_a):
        url = f"{origin_a.base_url}/nonexistent-page"
        req = urllib.request.Request(url)
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 404

    def test_cross_origin_fixture_not_served(self, origin_a):
        """Origin A should not serve Origin B fixtures."""
        url = f"{origin_a.base_url}/origin-b-iframe-body"
        req = urllib.request.Request(url)
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 404

    def test_post_rejected(self, origin_a):
        url = f"{origin_a.base_url}/basic-visible"
        data = b"test"
        req = urllib.request.Request(url, data=data, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
        assert exc.value.code == 405
