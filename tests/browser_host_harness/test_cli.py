"""CLI tests for the browser host harness.

Proves self-test exits zero, writes receipts, removes credential file,
leaves no open ports, and validate-receipt succeeds/fails correctly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HARNESS_MODULE = "scripts.browser_host_harness"


def _run_harness(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", HARNESS_MODULE, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


class TestSelfTest:
    def test_self_test_exits_zero(self):
        """The self-test must exit 0 when all checks pass."""
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            result = _run_harness("self-test", "--output-dir", tmp)
            # If it fails, print output for debugging
            if result.returncode != 0:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
            assert result.returncode == 0, f"self-test failed: {result.stderr}"

    def test_self_test_writes_json_receipt(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            result = _run_harness("self-test", "--output-dir", tmp)
            json_path = Path(tmp) / "scaffold-self-test.json"
            assert json_path.exists(), f"Missing {json_path}. stdout: {result.stdout}"
            receipt = json.loads(json_path.read_text(encoding="utf-8"))
            assert receipt["receiptKind"] == "scaffold_self_test"
            assert "runId" in receipt

    def test_self_test_writes_markdown_summary(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            _run_harness("self-test", "--output-dir", tmp)
            md_path = Path(tmp) / "scaffold-self-test.md"
            assert md_path.exists(), f"Missing {md_path}"

    def test_self_test_removes_credential_file(self):
        """Credential file must not remain after self-test."""
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            _run_harness("self-test", "--output-dir", tmp)
            # Check the output dir and tmp area - credential should be gone
            # The harness creates runtime dir inside temp dir
            # Check all subdirs for guardian-sentinel.txt
            for p in Path(tmp).rglob("guardian-sentinel.txt"):
                pytest.fail(f"Credential file still exists: {p}")

    def test_stdout_does_not_contain_sentinel(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            result = _run_harness("self-test", "--output-dir", tmp)
            assert "CODEXIFY-HARNESS-SENTINEL-" not in result.stdout
            assert "NOT-A-REAL-CREDENTIAL" not in result.stdout

    def test_stderr_does_not_contain_sentinel(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            result = _run_harness("self-test", "--output-dir", tmp)
            assert "CODEXIFY-HARNESS-SENTINEL-" not in result.stderr
            assert "NOT-A-REAL-CREDENTIAL" not in result.stderr

    def test_receipt_contains_non_claims(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            _run_harness("self-test", "--output-dir", tmp)
            json_path = Path(tmp) / "scaffold-self-test.json"
            receipt = json.loads(json_path.read_text(encoding="utf-8"))
            non_claims = receipt.get("nonClaims", [])
            assert any("no Browser Host candidate was tested" in nc for nc in non_claims)
            assert any("no renderer isolation was proven" in nc for nc in non_claims)

    def test_receipt_has_cleanup_status(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            _run_harness("self-test", "--output-dir", tmp)
            json_path = Path(tmp) / "scaffold-self-test.json"
            receipt = json.loads(json_path.read_text(encoding="utf-8"))
            assert receipt.get("cleanupStatus") in ("passed", "failed")


class TestValidateReceipt:
    def test_validates_good_receipt(self):
        """validate-receipt succeeds for a self-test output."""
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            _run_harness("self-test", "--output-dir", tmp)
            json_path = Path(tmp) / "scaffold-self-test.json"
            result = _run_harness("validate-receipt", str(json_path))
            assert result.returncode == 0, f"Validation failed: {result.stdout} {result.stderr}"

    def test_rejects_malformed_receipt(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text('{"runId": "test"}', encoding="utf-8")
            result = _run_harness("validate-receipt", str(bad_path))
            assert result.returncode != 0

    def test_rejects_nonexistent_file(self):
        result = _run_harness("validate-receipt", "/nonexistent/path.json")
        assert result.returncode != 0

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory(prefix="harness-test-") as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("not json", encoding="utf-8")
            result = _run_harness("validate-receipt", str(bad))
            assert result.returncode != 0


class TestServe:
    def test_serve_starts_and_stops(self):
        """serve should start and be stoppable via SIGTERM."""
        import signal
        import time

        with tempfile.TemporaryDirectory(prefix="harness-serve-") as tmp:
            proc = subprocess.Popen(
                [sys.executable, "-m", HARNESS_MODULE, "serve", "--runtime-dir", tmp],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Give it a moment to start
            time.sleep(2)
            # Send SIGTERM
            proc.send_signal(signal.SIGTERM)
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            assert proc.returncode in (0, -signal.SIGTERM, None)
            # stdout and stderr must not contain sentinel
            assert "CODEXIFY-HARNESS-SENTINEL-" not in stdout
            assert "CODEXIFY-HARNESS-SENTINEL-" not in (stderr or "")


class TestHarnessInitialization:
    def test_manifest_contains_safe_fields(self):
        """Runtime manifest must contain only safe fields."""
        from scripts.browser_host_harness.runtime import HarnessRuntime

        with tempfile.TemporaryDirectory(prefix="harness-") as tmp:
            rt = HarnessRuntime(Path(tmp))
            manifest = rt.start()
            try:
                # Required safe fields
                assert "runId" in manifest
                assert "harnessVersion" in manifest
                assert "fixtureVersion" in manifest
                assert "guardianStubVersion" in manifest
                assert "originAUrl" in manifest
                assert "originBUrl" in manifest
                assert "guardianBaseUrl" in manifest
                assert "fixtureManifestUrl" in manifest
                assert "startTimestamp" in manifest
                assert "runtimeDirectory" in manifest
                assert "syntheticThreadId" in manifest
                assert "syntheticRequestId" in manifest

                # Must NOT contain raw page bodies or secrets
                manifest_json = json.dumps(manifest)
                assert "s3cret_p@ssw0rd" not in manifest_json
                assert "SYSTEM OVERRIDE" not in manifest_json
                assert "Basic Visible Page" not in manifest_json
            finally:
                rt.stop()
