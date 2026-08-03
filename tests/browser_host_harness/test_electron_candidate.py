"""Enrollment and boundary tests for the Electron comparative candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from scripts.browser_host_harness import __version__ as HARNESS_VERSION
from scripts.browser_host_harness.adapters import electron_bundled_chromium as adapter
from scripts.browser_host_harness.candidate_cases import MANDATORY_CANDIDATE_CASE_IDS


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_ROOT = ROOT / "browser_host_candidates" / "electron"


def test_electron_adapter_identity_and_harness_registration():
    assert adapter.CANDIDATE_KEY == "electron-bundled-chromium"
    assert adapter.CANDIDATE_ID == "codexify-electron-bundled-chromium-v1"
    assert adapter.CANDIDATE_FAMILY == "bundled_chromium_electron"
    assert adapter.HARNESS_VERSION == HARNESS_VERSION


def test_electron_candidate_local_manifest_and_lockfile_contract():
    manifest = json.loads((CANDIDATE_ROOT / "candidate-manifest.json").read_text())
    package = json.loads((CANDIDATE_ROOT / "package.json").read_text())
    assert manifest["candidateId"] == adapter.CANDIDATE_ID
    assert manifest["candidateFamily"] == adapter.CANDIDATE_FAMILY
    assert package["devDependencies"] == {
        "@electron/packager": adapter.PACKAGER_VERSION,
        "electron": adapter.ELECTRON_VERSION,
        "playwright": adapter.PLAYWRIGHT_VERSION,
    }
    assert (CANDIDATE_ROOT / "package-lock.json").exists()


def test_electron_candidate_does_not_change_root_dependency_paths():
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "HEAD",
            "--",
            "package.json",
            "pnpm-lock.yaml",
            "pnpm-workspace.yaml",
        ],
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0


def test_adapter_receipt_case_catalog_matches_common_registry():
    cases = adapter._all_cases()
    assert set(cases) == set(MANDATORY_CANDIDATE_CASE_IDS)
    assert all(value["status"] in {"passed", "failed", "blocked", "inconclusive"} for value in cases.values())
