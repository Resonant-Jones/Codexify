"""Fixture corpus tests.

Proves every required fixture exists with stable IDs, versions, deterministic
titles and hashes, correct origin mapping, excluded fields, and safe triggers.
"""

from __future__ import annotations

import pytest

from scripts.browser_host_harness.fixtures import (
    FIXTURE_VERSION,
    FIXTURES,
    FIXTURE_BY_ID,
    REQUIRED_FIXTURE_IDS,
    FixtureFlag,
    FixtureRecord,
    OriginRole,
)


class TestFixtureInventory:
    def test_all_required_fixtures_exist(self):
        for fid in REQUIRED_FIXTURE_IDS:
            assert fid in FIXTURE_BY_ID, f"Missing fixture: {fid}"

    def test_fixture_count(self):
        assert len(FIXTURES) == len(REQUIRED_FIXTURE_IDS)

    def test_stable_ids(self):
        for fid in REQUIRED_FIXTURE_IDS:
            fixture = FIXTURE_BY_ID[fid]
            assert fixture.fixture_id == fid

    def test_stable_versions(self):
        for fixture in FIXTURES:
            assert fixture.fixture_version == FIXTURE_VERSION

    def test_deterministic_titles(self):
        titles = {
            "basic-visible": "Basic Visible Page",
            "prompt-injection": "Prompt Injection Test Page",
            "form-secret": "Form Secret Page",
            "cross-origin-iframe": "Cross-Origin Iframe Page (Origin A)",
            "origin-b-iframe-body": "Origin B Iframe Body",
            "oversized": "Oversized Page",
            "navigation-race": "Navigation Race Page",
            "origin-change": "Origin Change Page",
            "popup-attempt": "Popup Attempt Page",
            "download-attempt": "Download Attempt Page",
            "renderer-failure": "Renderer Failure Trigger Page",
            "protected-target": "Protected Target Metadata",
        }
        for fid, expected_title in titles.items():
            fixture = FIXTURE_BY_ID[fid]
            assert fixture.expected_title == expected_title, f"{fid}: {fixture.expected_title} != {expected_title}"

    def test_deterministic_hashes(self):
        """Visible-text hashes must be stable (non-empty, hex string)."""
        for fixture in FIXTURES:
            if fixture.visible_text_hash is not None:
                assert len(fixture.visible_text_hash) == 64
                assert all(c in "0123456789abcdef" for c in fixture.visible_text_hash)

    def test_hashes_are_unique(self):
        """Each fixture with a hash should have a unique visible-text hash."""
        hashes = [
            f.visible_text_hash
            for f in FIXTURES
            if f.visible_text_hash is not None
        ]
        assert len(hashes) == len(set(hashes)), "Fixture hashes are not unique"

    def test_origin_mapping(self):
        origin_b_ids = {"origin-b-iframe-body"}
        for fid in REQUIRED_FIXTURE_IDS:
            fixture = FIXTURE_BY_ID[fid]
            if fid in origin_b_ids:
                assert fixture.expected_origin == OriginRole.ORIGIN_B, f"{fid} should be Origin B"
            else:
                assert fixture.expected_origin == OriginRole.ORIGIN_A, f"{fid} should be Origin A"

    def test_excluded_fields(self):
        """Verify expected excluded fields are present."""
        assert "password-value" in FIXTURE_BY_ID["form-secret"].expected_excluded
        assert "hidden-input-value" in FIXTURE_BY_ID["form-secret"].expected_excluded
        assert "hidden-div-content" in FIXTURE_BY_ID["prompt-injection"].expected_excluded
        assert "iframe-body" in FIXTURE_BY_ID["cross-origin-iframe"].expected_excluded

    def test_no_external_url_dependency(self):
        """No fixture route references external URLs."""
        for fixture in FIXTURES:
            assert not fixture.relative_route.startswith("http")
            assert "://" not in fixture.relative_route

    def test_safe_triggers(self):
        """Popup, download, and failure fixtures must not auto-trigger."""
        popup = FIXTURE_BY_ID["popup-attempt"]
        assert FixtureFlag.NO_AUTO_POPUP in popup.flags

        download = FIXTURE_BY_ID["download-attempt"]
        assert FixtureFlag.NO_AUTO_DOWNLOAD in download.flags

        nav_race = FIXTURE_BY_ID["navigation-race"]
        assert FixtureFlag.NO_AUTO_NAVIGATE in nav_race.flags

        origin_change = FIXTURE_BY_ID["origin-change"]
        assert FixtureFlag.NO_AUTO_NAVIGATE in origin_change.flags

        renderer_fail = FIXTURE_BY_ID["renderer-failure"]
        assert FixtureFlag.OPT_IN_FAILURE in renderer_fail.flags

    def test_all_safe_for_server_test(self):
        for fixture in FIXTURES:
            assert FixtureFlag.SAFE_FOR_SERVER_TEST in fixture.flags, (
                f"{fixture.fixture_id} must be SAFE_FOR_SERVER_TEST"
            )
