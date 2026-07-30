"""CLI entry point for the Browser Host comparative proof harness.

Commands:
  self-test          Run the scaffold self-test.
  serve              Start the three servers for development.
  validate-receipt   Validate a proof receipt JSON file.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__ as HARNESS_VERSION
from .contracts import CaseStatus, CleanupStatus
from .fixtures import FIXTURE_VERSION, FIXTURES, REQUIRED_FIXTURE_IDS, FixtureRecord
from .fixture_server import FixtureServer
from .guardian_stub import GUARDIAN_STUB_VERSION, GuardianStub
from .receipts import (
    ReceiptValidationError,
    build_scaffold_self_test_receipt,
    validate_receipt,
    write_json_receipt,
    write_markdown_summary,
)
from .runtime import HarnessRuntime, read_credential

_ISO_NOW = lambda: datetime.now(timezone.utc).isoformat()


def _main() -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m scripts.browser_host_harness",
        description="Browser Host comparative proof harness scaffold",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # self-test
    st = sub.add_parser("self-test", help="Run the scaffold self-test")
    st.add_argument("--output-dir", required=True, type=Path, help="Output directory for receipts")

    # serve
    sv = sub.add_parser("serve", help="Start harness servers for development")
    sv.add_argument("--runtime-dir", required=True, type=Path, help="Runtime directory")

    # validate-receipt
    vr = sub.add_parser("validate-receipt", help="Validate a proof receipt")
    vr.add_argument("path", type=Path, help="Path to receipt JSON file")

    args = parser.parse_args()

    if args.command == "self-test":
        return _cmd_self_test(args.output_dir)
    elif args.command == "serve":
        return _cmd_serve(args.runtime_dir)
    elif args.command == "validate-receipt":
        return _cmd_validate_receipt(args.path)
    else:
        return 1


def _cmd_self_test(output_dir: Path) -> int:
    """Run the scaffold self-test."""
    runtime_dir = Path(tempfile.mkdtemp(prefix="codexify-harness-"))
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"self-test-{uuid.uuid4().hex[:8]}"
    started_at = _ISO_NOW()

    cases: dict[str, str] = {}
    warnings: list[str] = []
    failures: list[str] = []
    overall_pass = True

    harness = HarnessRuntime(runtime_dir)
    harness.run_id = run_id

    def _record(case_id: str, passed: bool, msg: str = ""):
        nonlocal overall_pass
        cases[case_id] = CaseStatus.PASSED.value if passed else CaseStatus.FAILED.value
        if not passed:
            overall_pass = False
            failures.append(f"{case_id}: {msg}" if msg else case_id)
        else:
            print(f"  PASS: {case_id}")

    print(f"[{_ISO_NOW()}] Starting scaffold self-test (run={run_id})")
    print(f"  Runtime dir: {runtime_dir}")
    print(f"  Output dir:  {output_dir}")

    try:
        # 1. Start servers
        print("\n--- Phase 1: Start servers ---")
        manifest = harness.start()
        print(f"  Origin A:     {harness.origin_a_url}")
        print(f"  Origin B:     {harness.origin_b_url}")
        print(f"  Guardian:     {harness.guardian_url}")
        print(f"  Manifest:     {runtime_dir / 'runtime-manifest.json'}")
        _record("servers_started", True)

        sentinel = read_credential(harness._credential_file)
        auth_headers = {"Authorization": f"Bearer {sentinel}"}

        # 2. Fetch and validate fixture manifest
        print("\n--- Phase 2: Fixture manifest ---")
        import urllib.request

        manifest_url = f"{harness.origin_a_url}/manifest.json"
        try:
            req = urllib.request.Request(manifest_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                manifest_data = json.loads(resp.read().decode("utf-8"))
            fixture_ids = [f["fixtureId"] for f in manifest_data.get("fixtures", [])]
            for required_id in REQUIRED_FIXTURE_IDS:
                if required_id in fixture_ids:
                    _record(f"fixture_manifest_has_{required_id}", True)
                else:
                    _record(f"fixture_manifest_has_{required_id}", False, f"missing from manifest")
            _record("fixture_manifest_valid", True)
        except Exception as e:
            _record("fixture_manifest_valid", False, str(e))

        # 3. Probe every non-protected HTTP fixture
        print("\n--- Phase 3: Probe fixtures ---")
        for fixture in FIXTURES:
            url = (
                f"{harness.origin_a_url}{fixture.relative_route}"
                if fixture.requires_origin_a
                else f"{harness.origin_b_url}{fixture.relative_route}"
            )
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read().decode("utf-8")
                # Basic checks
                ok = (
                    fixture.expected_title in body
                    and resp.status == 200
                    and "Content-Type" in resp.headers
                )
                _record(f"fixture_served_{fixture.fixture_id}", ok, f"status={resp.status}")
            except Exception as e:
                _record(f"fixture_served_{fixture.fixture_id}", False, str(e))

        # 4. Verify Origin A and B are distinct
        print("\n--- Phase 4: Origin distinctness ---")
        _record(
            "origins_distinct",
            harness.origin_a_url != harness.origin_b_url,
            f"A={harness.origin_a_url} B={harness.origin_b_url}",
        )

        # 5. Verify cross-origin iframe references Origin B
        print("\n--- Phase 5: Cross-origin iframe ---")
        try:
            iframe_url = f"{harness.origin_a_url}/cross-origin-iframe"
            req = urllib.request.Request(iframe_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                iframe_body = resp.read().decode("utf-8")
            _record("cross_origin_iframe_refs_b", harness.origin_b_url in iframe_body)
        except Exception as e:
            _record("cross_origin_iframe_refs_b", False, str(e))

        # 6. Guardian stub: unauthenticated health
        print("\n--- Phase 6: Guardian stub auth and routes ---")
        try:
            health_url = f"{harness.guardian_url}/health"
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            _record("guardian_health", health.get("stub") is True, str(health))
        except Exception as e:
            _record("guardian_health", False, str(e))

        # 7. Verify protected routes reject missing credentials
        print("\n--- Phase 7: Auth rejection ---")
        for protected_path in ["/api/session", "/api/companion"]:
            try:
                url = f"{harness.guardian_url}{protected_path}"
                req = urllib.request.Request(url)
                _req_with_status(req, 401)
                _record(f"auth_required_{protected_path.replace('/', '_')}", True)
            except Exception as e:
                status = getattr(e, "code", None) if hasattr(e, "code") else None
                _record(
                    f"auth_required_{protected_path.replace('/', '_')}",
                    status == 401,
                    f"status={status} err={e}",
                )

        # 8. Verify invalid credential -> 401
        try:
            url = f"{harness.guardian_url}/api/session"
            req = urllib.request.Request(url, headers={"Authorization": "Bearer invalid-cred"})
            _req_with_status(req, 401)
            _record("auth_invalid_credential", True)
        except Exception as e:
            status = getattr(e, "code", None) if hasattr(e, "code") else None
            _record("auth_invalid_credential", status == 401, f"status={status}")

        # 9. Verify fixture origins receive no authority-bearing CORS
        print("\n--- Phase 8: CORS boundary ---")
        try:
            # Request from "Origin A" to guardian protected route
            url = f"{harness.guardian_url}/api/session"
            req = urllib.request.Request(
                url,
                headers={
                    "Origin": harness.origin_a_url,
                    "Authorization": f"Bearer {sentinel}",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                acao = resp.headers.get("Access-Control-Allow-Origin", "")
            cors_denied = acao != harness.origin_a_url and acao != "*"
            _record("cors_no_fixture_origin_grant", cors_denied, f"ACAO={acao}")
        except Exception as e:
            _record("cors_no_fixture_origin_grant", False, str(e))

        # 10. Submit valid context envelope
        print("\n--- Phase 9: Context attachment ---")
        import hashlib

        content_text = "This is deterministic visible text for capture verification."
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
        content_bytes = content_text.encode("utf-8")

        valid_envelope = {
            "contextId": f"ctx-{uuid.uuid4().hex[:8]}",
            "captureRequestId": f"cap-{uuid.uuid4().hex[:8]}",
            "sourceKind": "visible-text",
            "sourceUrl": f"{harness.origin_a_url}/basic-visible",
            "sourceOrigin": harness.origin_a_url,
            "sourceTitle": "Basic Visible Page",
            "capturedAt": _ISO_NOW(),
            "captureMode": "visible-extraction",
            "contentType": "text/html",
            "content": content_text,
            "contentHash": content_hash,
            "contentLength": len(content_bytes),
            "truncated": False,
            "extractorVersion": "test-1.0",
            "permissionScope": "visible-text",
            "retentionClass": "ephemeral",
            "userInitiated": True,
            "requestId": f"req-{uuid.uuid4().hex[:8]}",
            "attemptNumber": 1,
            "runId": run_id,
        }

        try:
            resp_data, status = _post_json(
                f"{harness.guardian_url}/api/context/attach",
                valid_envelope,
                auth_headers,
            )
            ok = status == 200 and resp_data.get("status") == "attached"
            _record("context_attach_valid", ok, f"status={status}")
            # Verify no raw content in receipt
            if ok:
                raw = json.dumps(resp_data)
                no_content = content_text not in raw
                _record("receipt_no_raw_content", no_content)
        except Exception as e:
            _record("context_attach_valid", False, str(e))

        # 11. Submit malformed envelopes
        print("\n--- Phase 10: Malformed envelope rejection ---")

        # Missing fields
        malformed = {"contextId": "ctx-bad"}
        _, status = _post_json(
            f"{harness.guardian_url}/api/context/attach",
            malformed,
            auth_headers,
        )
        _record("reject_malformed_envelope", status == 422 or status == 400, f"status={status}")

        # Origin mismatch
        origin_mismatch = dict(valid_envelope)
        origin_mismatch["sourceOrigin"] = "http://different-origin:9999"
        origin_mismatch["contextId"] = f"ctx-{uuid.uuid4().hex[:8]}"
        _, status = _post_json(
            f"{harness.guardian_url}/api/context/attach",
            origin_mismatch,
            auth_headers,
        )
        _record("reject_origin_mismatch", status == 422, f"status={status}")

        # Hash mismatch
        hash_mismatch = dict(valid_envelope)
        hash_mismatch["contentHash"] = "0" * 64
        hash_mismatch["contextId"] = f"ctx-{uuid.uuid4().hex[:8]}"
        _, status = _post_json(
            f"{harness.guardian_url}/api/context/attach",
            hash_mismatch,
            auth_headers,
        )
        _record("reject_hash_mismatch", status == 422, f"status={status}")

        # Non-user-initiated
        non_ui = dict(valid_envelope)
        non_ui["userInitiated"] = False
        non_ui["contextId"] = f"ctx-{uuid.uuid4().hex[:8]}"
        _, status = _post_json(
            f"{harness.guardian_url}/api/context/attach",
            non_ui,
            auth_headers,
        )
        _record("reject_non_user_initiated", status == 422, f"status={status}")

        # Secret-bearing
        secret_env = dict(valid_envelope)
        secret_env["password"] = "s3cret_p@ssw0rd"
        secret_env["contextId"] = f"ctx-{uuid.uuid4().hex[:8]}"
        _, status = _post_json(
            f"{harness.guardian_url}/api/context/attach",
            secret_env,
            auth_headers,
        )
        _record("reject_secret_bearing", status == 422, f"status={status}")

        # 12. Deterministic attachment failure
        print("\n--- Phase 11: Attachment failure ---")
        _, fail_status = _post_json(
            f"{harness.guardian_url}/api/context/attach-fail",
            valid_envelope,
            auth_headers,
        )
        _record("attachment_failure_deterministic", fail_status == 422, f"status={fail_status}")

        # 13. Companion continuity after failure
        print("\n--- Phase 12: Companion continuity ---")
        try:
            req = urllib.request.Request(
                f"{harness.guardian_url}/api/companion",
                headers=auth_headers,
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                companion = json.loads(resp.read().decode("utf-8"))
            _record("companion_after_failure", companion.get("stub") is True, str(companion))
        except Exception as e:
            _record("companion_after_failure", False, str(e))

        # 14. Write receipts
        print("\n--- Phase 13: Receipts ---")
        completed_at = _ISO_NOW()
        receipt = build_scaffold_self_test_receipt(
            run_id=run_id,
            harness_version=HARNESS_VERSION,
            fixture_version=FIXTURE_VERSION,
            guardian_stub_version=GUARDIAN_STUB_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            cases=cases,
            cleanup_status=CleanupStatus.NOT_RUN.value,
            warnings=warnings,
            failures=failures,
        )

        json_path = output_dir / "scaffold-self-test.json"
        md_path = output_dir / "scaffold-self-test.md"
        try:
            write_json_receipt(receipt, json_path, overwrite=True)
            write_markdown_summary(receipt, md_path)
            print(f"  JSON receipt: {json_path}")
            print(f"  MD summary:   {md_path}")
        except Exception as e:
            print(f"  ERROR writing receipts: {e}")
            _record("receipts_written", False, str(e))

        # 15. Stop servers and cleanup
        print("\n--- Phase 14: Cleanup ---")
        harness.stop()

        # Verify credential file removed
        cred_file = harness._credential_file
        if cred_file and not cred_file.exists():
            _record("credential_file_removed", True)
        else:
            _record("credential_file_removed", False)

        # Verify ports closed
        time.sleep(0.5)
        ports_closed = harness.verify_ports_closed()
        _record("all_ports_closed", ports_closed)

        cleanup_ok = (
            cases.get("credential_file_removed") == CaseStatus.PASSED.value
            and cases.get("all_ports_closed") == CaseStatus.PASSED.value
        )

        # Update receipt with final cleanup
        receipt["cases"] = cases
        receipt["cleanupStatus"] = (
            CleanupStatus.PASSED.value if cleanup_ok else CleanupStatus.FAILED.value
        )
        receipt["completedAt"] = _ISO_NOW()
        try:
            write_json_receipt(receipt, json_path, overwrite=True)
            write_markdown_summary(receipt, md_path)
        except Exception as e:
            print(f"  WARNING: could not update receipt: {e}")

    except Exception as e:
        print(f"\nFATAL: {e}")
        overall_pass = False
        try:
            harness.stop()
        except Exception:
            pass

    # Clean up temp runtime dir
    try:
        import shutil

        shutil.rmtree(runtime_dir, ignore_errors=True)
    except Exception:
        pass

    print(f"\n[{_ISO_NOW()}] Self-test {'PASSED' if overall_pass else 'FAILED'}")
    print(f"  Cases: {len(cases)} total")
    passed_count = sum(1 for v in cases.values() if v == CaseStatus.PASSED.value)
    failed_count = sum(1 for v in cases.values() if v == CaseStatus.FAILED.value)
    print(f"  Passed: {passed_count}, Failed: {failed_count}")

    return 0 if overall_pass else 1


def _cmd_serve(runtime_dir: Path) -> int:
    """Start harness servers and wait for SIGINT/SIGTERM."""
    harness = HarnessRuntime(runtime_dir)
    manifest = harness.start()

    print(f"Harness running (run={harness.run_id})")
    print(f"  Origin A:     {harness.origin_a_url}")
    print(f"  Origin B:     {harness.origin_b_url}")
    print(f"  Guardian:     {harness.guardian_url}")
    print(f"  Manifest:     {runtime_dir / 'runtime-manifest.json'}")
    print(f"  Credential:   {harness._credential_file}")
    print()
    print("Press Ctrl+C to stop.")

    stop_event = threading.Event()

    def _handler(signum, frame):
        print("\nShutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    try:
        while not stop_event.wait(timeout=1):
            pass
    except KeyboardInterrupt:
        pass

    harness.stop()
    print("Shutdown complete.")
    return 0


def _cmd_validate_receipt(path: Path) -> int:
    """Validate a proof receipt JSON file."""
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1

    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: cannot parse receipt: {e}", file=sys.stderr)
        return 1

    errors = validate_receipt(receipt)
    if errors:
        print("Receipt validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Receipt validation PASSED")
    kind = receipt.get("receiptKind", "unknown")
    run_id = receipt.get("runId", "?")
    print(f"  Kind:  {kind}")
    print(f"  Run:   {run_id}")
    if receipt.get("candidateId"):
        print(f"  Candidate: {receipt['candidateId']} ({receipt.get('candidateFamily', '?')})")
        print(f"  Status:    {receipt.get('candidateStatus', '?')}")
    return 0


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _req_with_status(req: urllib.request.Request, expected_status: int) -> None:
    """Make request and raise if status doesn't match expected."""
    import urllib.request
    import urllib.error

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != expected_status:
                raise urllib.error.HTTPError(
                    req.full_url, resp.status, "", resp.headers, None
                )
    except urllib.error.HTTPError as e:
        if e.code != expected_status:
            raise


def _post_json(
    url: str, payload: dict, headers: dict | None = None
) -> tuple[dict, int]:
    """POST JSON and return (parsed_body, status_code)."""
    import urllib.request
    import urllib.error

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else "{}"
        try:
            return json.loads(body), e.code
        except json.JSONDecodeError:
            return {}, e.code


if __name__ == "__main__":
    sys.exit(_main())
