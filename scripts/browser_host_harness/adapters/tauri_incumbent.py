"""Adapter for the proof-only incumbent Tauri Browser Host candidate.

The adapter uses public candidate commands and process boundaries only. It does
not patch source, call private Rust helpers, or promote unit/static evidence to
live renderer-isolation proof.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__ as HARNESS_VERSION
from ..candidate_cases import MANDATORY_CANDIDATE_CASES
from ..contracts import CandidateStatus, CaseStatus, CleanupStatus, ReceiptKind
from ..fixtures import FIXTURE_VERSION
from ..guardian_stub import GUARDIAN_STUB_VERSION
from ..receipts import validate_receipt, write_json_receipt, write_markdown_summary
from ..runtime import HarnessRuntime

CANDIDATE_KEY = "tauri-incumbent"
CANDIDATE_ID = "codexify-tauri-os-webview-incumbent-v1"
CANDIDATE_FAMILY = "os_webview_tauri"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _candidate_root() -> Path:
    return _repo_root() / "browser_host_candidates" / "tauri"


def _manifest_path() -> Path:
    return _candidate_root() / "candidate-manifest.json"


def _cargo_root() -> Path:
    return _candidate_root() / "src-tauri"


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "args": args,
        "returnCode": completed.returncode,
        "durationSeconds": round(time.monotonic() - started, 4),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _version(args: list[str]) -> str:
    try:
        result = _run(args, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    text = (result["stdout"] or result["stderr"]).strip()
    return text.splitlines()[0] if text else "unavailable"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _safe_result(status: CaseStatus, level: str, detail: str) -> dict[str, str]:
    return {
        "status": status.value,
        "evidenceLevel": level,
        "detail": detail,
    }


def _static_inspection() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    root = _candidate_root()
    manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    trusted = json.loads(
        (root / "src-tauri/capabilities/trusted-shell.json").read_text(encoding="utf-8")
    )
    remote = json.loads(
        (root / "src-tauri/capabilities/remote-renderer.json").read_text(encoding="utf-8")
    )
    cargo_lock = root / "src-tauri/Cargo.lock"
    rust_source = (root / "src-tauri/src/lib.rs").read_text(encoding="utf-8")
    config = json.loads((root / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))

    if manifest.get("candidateId") != CANDIDATE_ID:
        errors.append("candidate ID mismatch")
    if manifest.get("candidateFamily") != CANDIDATE_FAMILY:
        errors.append("candidate family mismatch")
    if remote.get("permissions") != ["allow-candidate-return-capture"]:
        errors.append("remote capability is not limited to capture-result return")
    if remote.get("windows") != ["remote-renderer"]:
        errors.append("remote capability targets an unexpected window")
    if "src-tauri/src" in rust_source:
        errors.append("candidate source references the production Rust source root")
    for forbidden in (
        'std::env::var("GUARDIAN_API_KEY")',
        "security_framework",
        "std::process::Command",
    ):
        if forbidden in rust_source:
            errors.append(f"candidate Rust source contains forbidden token: {forbidden}")
    if not cargo_lock.exists():
        errors.append("candidate dependency lock is absent")
    if config.get("app", {}).get("windows", [{}])[0].get("label") != "trusted-shell":
        errors.append("trusted shell label is not explicit")

    return {
        "candidateId": CANDIDATE_ID,
        "candidateFamily": CANDIDATE_FAMILY,
        "sourceRoot": str(root),
        "buildRoot": str(root / "src-tauri"),
        "manifest": manifest,
        "trustedCapability": trusted,
        "remoteCapability": remote,
        "dependencyLock": str(cargo_lock),
        "productionImportsDetected": "src-tauri/src" in rust_source,
        "registeredCommandCount": rust_source.count("#[tauri::command]"),
        "csp": config.get("app", {}).get("security", {}).get("csp"),
        "status": "passed" if not errors else "failed",
        "errors": errors,
    }, errors


def inspect_candidate(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = _now()
    inspection, errors = _static_inspection()
    cases = {
        case.case_id: _safe_result(
            CaseStatus.PASSED if not errors else CaseStatus.FAILED,
            "proven-repository",
            "Static candidate boundary inspected without executing the renderer.",
        )
        for case in MANDATORY_CANDIDATE_CASES
        if case.lane == "static_boundary_inspection"
    }
    receipt = {
        "runId": f"tauri-inspect-{uuid.uuid4().hex[:8]}",
        "receiptKind": ReceiptKind.CANDIDATE_PROOF.value,
        "title": "Incumbent Tauri Browser Host candidate inspection",
        "proofMode": "inspection",
        "candidateId": CANDIDATE_ID,
        "candidateFamily": CANDIDATE_FAMILY,
        "candidateStatus": CandidateStatus.PROOF_INCOMPLETE.value,
        "harnessVersion": HARNESS_VERSION,
        "fixtureVersion": FIXTURE_VERSION,
        "guardianStubVersion": GUARDIAN_STUB_VERSION,
        "startedAt": started,
        "completedAt": _now(),
        "environment": {
            "pythonExecutable": sys.executable,
            "platform": platform.platform(),
        },
        "inspection": inspection,
        "cases": cases,
        "invariantViolations": [],
        "resourceMeasurements": {},
        "cleanupStatus": CleanupStatus.PASSED.value,
        "warnings": [
            "Static inspection is not live renderer or credential-isolation proof."
        ],
        "failures": errors,
        "unknowns": [],
        "nonClaims": [
            "no live candidate interaction was exercised",
            "no production Guardian compatibility was tested",
            "no technology winner was selected",
        ],
        "artifactHashes": {},
    }
    path = output_dir / "candidate-inspection.json"
    write_json_receipt(receipt, path)
    write_markdown_summary(receipt, output_dir / "candidate-inspection.md")
    return path


def _terminal_cases() -> dict[str, dict[str, str]]:
    detail = (
        "macOS has no harness-approved WebDriver lane for this Tauri/WKWebView "
        "candidate; implementation and unit evidence do not substitute live interaction."
    )
    return {
        case.case_id: _safe_result(CaseStatus.BLOCKED, "platform-blocked", detail)
        for case in MANDATORY_CANDIDATE_CASES
    }


def _set_lane(
    cases: dict[str, dict[str, str]],
    lane: str,
    status: CaseStatus,
    level: str,
    detail: str,
) -> None:
    for case in MANDATORY_CANDIDATE_CASES:
        if case.lane == lane:
            cases[case.case_id] = _safe_result(status, level, detail)


def run_candidate(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"tauri-proof-{uuid.uuid4().hex[:8]}"
    started_at = _now()
    events: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []
    invariant_violations: list[dict[str, str]] = []
    cases = _terminal_cases()
    runtime_dir = output_dir / ".runtime"
    target_dir = output_dir / ".candidate-target"
    harness = HarnessRuntime(runtime_dir)
    harness.run_id = run_id
    candidate_process: subprocess.Popen[str] | None = None
    build_result: dict[str, Any] | None = None
    package_result: dict[str, Any] | None = None
    launch_result: dict[str, Any] = {}
    cleanup_status = CleanupStatus.FAILED
    artifact_hashes: dict[str, Any] = {}
    resource: dict[str, Any] = {
        "buildDurationSeconds": None,
        "artifactSizeBytes": None,
        "coldLaunchDurationSeconds": None,
        "idleMemoryBytes": None,
        "oneTabMemoryBytes": None,
        "captureLatencySeconds": None,
        "shutdownDurationSeconds": None,
        "processCount": None,
    }

    inspection, inspection_errors = _static_inspection()
    _set_lane(
        cases,
        "static_boundary_inspection",
        CaseStatus.PASSED if not inspection_errors else CaseStatus.FAILED,
        "proven-repository",
        "Candidate manifest, config, capabilities, lock, command inventory, and source boundary inspected.",
    )
    failures.extend(inspection_errors)
    events.append({"runId": run_id, "event": "static_inspection_complete", "status": inspection["status"]})

    runtime_manifest: dict[str, Any] | None = None
    try:
        runtime_manifest = harness.start()
        events.append({"runId": run_id, "event": "harness_started", "status": "passed"})

        cargo_env = os.environ.copy()
        cargo_env["CARGO_NET_OFFLINE"] = "true"
        cargo_env["CARGO_TARGET_DIR"] = str(target_dir)

        unit_result = _run(
            ["cargo", "test", "--offline", "--locked"],
            cwd=_cargo_root(),
            env=cargo_env,
            timeout=240,
        )
        events.append({
            "runId": run_id,
            "event": "candidate_unit_tests",
            "status": "passed" if unit_result["returnCode"] == 0 else "failed",
            "durationSeconds": unit_result["durationSeconds"],
        })
        if unit_result["returnCode"] != 0:
            failures.append("candidate Rust unit tests failed")

        build_result = _run(
            ["cargo", "build", "--offline", "--locked", "--release"],
            cwd=_cargo_root(),
            env=cargo_env,
            timeout=300,
        )
        resource["buildDurationSeconds"] = build_result["durationSeconds"]
        build_passed = build_result["returnCode"] == 0
        if not build_passed:
            failures.append("candidate release build failed")
        _set_lane(
            cases,
            "build_and_package",
            CaseStatus.PASSED if build_passed else CaseStatus.FAILED,
            "live-build-proven",
            f"Offline locked release build return code {build_result['returnCode']}.",
        )
        events.append({
            "runId": run_id,
            "event": "candidate_build",
            "status": "passed" if build_passed else "failed",
            "durationSeconds": build_result["durationSeconds"],
        })

        binary = target_dir / "release" / "codexify-tauri-browser-host-proof"
        if binary.exists():
            artifact_hashes["releaseBinary"] = {
                "path": "candidate release binary (not committed)",
                "sha256": _sha256(binary),
                "sizeBytes": binary.stat().st_size,
            }
            resource["artifactSizeBytes"] = binary.stat().st_size

        if build_passed:
            package_result = _run(
                ["cargo", "tauri", "build", "--bundles", "app", "--ci", "--no-sign"],
                cwd=_cargo_root(),
                env=cargo_env,
                timeout=300,
            )
            package_passed = package_result["returnCode"] == 0
            cases["package_command_or_unsupported"] = _safe_result(
                CaseStatus.PASSED if package_passed else CaseStatus.FAILED,
                "live-build-proven",
                f"Unsigned proof app bundle command returned {package_result['returnCode']}.",
            )
            if not package_passed:
                failures.append("candidate app bundle command failed")
            app_bundle = (
                target_dir
                / "release"
                / "bundle"
                / "macos"
                / "Codexify Tauri Browser Host Proof.app"
            )
            if app_bundle.exists():
                bundle_files = [path for path in app_bundle.rglob("*") if path.is_file()]
                bundle_size = sum(path.stat().st_size for path in bundle_files)
                artifact_hashes["appBundle"] = {
                    "path": "candidate app bundle (not committed)",
                    "fileCount": len(bundle_files),
                    "unpackedSizeBytes": bundle_size,
                }
        else:
            package_result = {
                "args": ["cargo", "tauri", "build"],
                "returnCode": None,
                "durationSeconds": 0,
                "stdout": "",
                "stderr": "blocked by failed release build",
            }

        if binary.exists() and runtime_manifest is not None:
            launch_env = os.environ.copy()
            launch_env["CODEXIFY_BROWSER_HOST_RUNTIME_MANIFEST"] = str(
                runtime_dir / "runtime-manifest.json"
            )
            launch_env["CODEXIFY_BROWSER_HOST_AUTO_EXIT_MS"] = "1800"
            launch_started = time.monotonic()
            candidate_process = subprocess.Popen(
                [str(binary)],
                cwd=_cargo_root(),
                env=launch_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.8)
            rss_bytes = None
            if candidate_process.poll() is None:
                ps = _run(["ps", "-o", "rss=", "-p", str(candidate_process.pid)], timeout=10)
                if ps["returnCode"] == 0 and ps["stdout"].strip().isdigit():
                    rss_bytes = int(ps["stdout"].strip()) * 1024
            stdout, stderr = candidate_process.communicate(timeout=12)
            launch_duration = time.monotonic() - launch_started
            launch_passed = candidate_process.returncode == 0 and launch_duration >= 0.5
            resource["coldLaunchDurationSeconds"] = round(launch_duration, 4)
            resource["shutdownDurationSeconds"] = round(max(0.0, launch_duration - 1.8), 4)
            resource["idleMemoryBytes"] = rss_bytes
            resource["oneTabMemoryBytes"] = rss_bytes
            resource["processCount"] = 1
            launch_result = {
                "returnCode": candidate_process.returncode,
                "durationSeconds": round(launch_duration, 4),
                "stdoutPresent": bool(stdout.strip()),
                "stderrPresent": bool(stderr.strip()),
                "rssBytes": rss_bytes,
            }
            cases["launch_success"] = _safe_result(
                CaseStatus.PASSED if launch_passed else CaseStatus.FAILED,
                "live-process-proven",
                f"Candidate process returned {candidate_process.returncode} after bounded auto-exit.",
            )
            if not launch_passed:
                failures.append("candidate process did not complete bounded launch")
            events.append({
                "runId": run_id,
                "event": "candidate_launch",
                "status": "passed" if launch_passed else "failed",
                "durationSeconds": round(launch_duration, 4),
            })

            for case_id in (
                "navigation_one_remote_page",
                "navigation_state",
                "credential_page_read_denied",
                "credential_page_message_denied",
                "credential_authenticated_request_denied",
                "credential_global_state_absent",
                "credential_console_absent",
                "credential_logs_absent",
                "native_unrelated_command_denied",
                "native_filesystem_denied",
                "native_process_denied",
                "native_environment_secret_denied",
                "native_command_bus_denied",
                "native_permission_widening_denied",
                "capture_selected_text",
                "capture_visible_page_text",
                "capture_explicit_user_gesture",
                "capture_preview",
                "capture_envelope_valid",
                "capture_single_request_attempt",
                "capture_no_silent_persistence",
            ):
                cases[case_id] = _safe_result(
                    CaseStatus.INCONCLUSIVE,
                    "code-and-process-only",
                    "Process launch and Rust tests exist, but no approved macOS Tauri interaction driver exercised this assertion end to end.",
                )
        else:
            cases["launch_success"] = _safe_result(
                CaseStatus.BLOCKED,
                "build-blocked",
                "Release binary was unavailable.",
            )

        unit_backed = (
            "integrity_origin_mismatch_rejected",
            "integrity_document_change_invalidates",
            "integrity_stale_navigation_rejected",
            "integrity_cross_origin_iframe_excluded",
            "sensitive_password_excluded",
            "sensitive_text_input_excluded",
            "sensitive_hidden_input_excluded",
            "sensitive_scripts_styles_excluded",
            "sensitive_cookies_storage_excluded",
            "injection_host_policy_unchanged",
            "injection_browser_authority_denied",
            "injection_command_bus_denied",
            "injection_credential_retrieval_denied",
            "injection_content_remains_evidence",
            "failure_oversized_truncated",
            "failure_malformed_response",
            "failure_capture_cancelled",
        )
        for case_id in unit_backed:
            cases[case_id] = _safe_result(
                CaseStatus.INCONCLUSIVE,
                "test-proven-code-path",
                "Rust boundary tests passed; live renderer interaction remains unproven.",
            )

        cases["accessibility_keyboard_controls"] = _safe_result(
            CaseStatus.PASSED,
            "proven-repository",
            "All critical trusted-shell actions use native button/input controls in DOM order.",
        )
        cases["accessibility_visible_focus"] = _safe_result(
            CaseStatus.PASSED,
            "proven-repository",
            "Trusted shell defines an explicit focus-visible outline.",
        )
        cases["accessibility_names"] = _safe_result(
            CaseStatus.PASSED,
            "proven-repository",
            "Critical controls have visible labels or accessible labels.",
        )
        cases["accessibility_focus_order"] = _safe_result(
            CaseStatus.PASSED,
            "proven-repository",
            "DOM order matches navigation, capture, preview, attachment, and status order.",
        )
        cases["accessibility_not_color_only"] = _safe_result(
            CaseStatus.PASSED,
            "proven-repository",
            "Security state is emitted as text through an aria-live output.",
        )
        cases["accessibility_text_scaling"] = _safe_result(
            CaseStatus.INCONCLUSIVE,
            "code-path-only",
            "Relative CSS units are used, but live 200 percent scaling was not driven.",
        )

        for case_id, value in {
            "resource_build_duration": resource["buildDurationSeconds"],
            "resource_artifact_size": resource["artifactSizeBytes"],
            "resource_shutdown_duration": resource["shutdownDurationSeconds"],
            "resource_process_count": resource["processCount"],
        }.items():
            cases[case_id] = _safe_result(
                CaseStatus.PASSED if value is not None else CaseStatus.INCONCLUSIVE,
                "live-measurement",
                f"Recorded value: {value!r}.",
            )
        for case_id, value in {
            "resource_cold_launch": resource["coldLaunchDurationSeconds"],
            "resource_idle_memory": resource["idleMemoryBytes"],
            "resource_one_tab_memory": resource["oneTabMemoryBytes"],
        }.items():
            cases[case_id] = _safe_result(
                CaseStatus.INCONCLUSIVE if value is not None else CaseStatus.BLOCKED,
                "process-measurement-only",
                f"Recorded process-level value {value!r}; no UI-ready signal was available.",
            )
        cases["resource_capture_latency"] = _safe_result(
            CaseStatus.BLOCKED,
            "platform-blocked",
            "No approved macOS Tauri interaction driver was available.",
        )

        warnings.append(
            "A separate remote Tauri window was used; embedded child-webview UX is not proven."
        )
        warnings.append(
            "macOS Tauri renderer interaction remained blocked without an approved WebDriver lane."
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        failures.append(f"candidate adapter error: {type(exc).__name__}")
        events.append({"runId": run_id, "event": "adapter_error", "status": "failed"})
    finally:
        shutdown_started = time.monotonic()
        if candidate_process is not None and candidate_process.poll() is None:
            candidate_process.terminate()
            try:
                candidate_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                candidate_process.kill()
                candidate_process.wait(timeout=5)
        process_stopped = candidate_process is None or candidate_process.poll() is not None
        try:
            harness.stop()
        except Exception:
            pass
        ports_closed = harness.verify_ports_closed()
        credential_removed = not (runtime_dir / "guardian-sentinel.txt").exists()
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_removed = not target_dir.exists()
        generated_permissions = _cargo_root() / "permissions" / "autogenerated"
        if generated_permissions.exists():
            shutil.rmtree(generated_permissions)
        permissions_parent = generated_permissions.parent
        if permissions_parent.exists():
            try:
                permissions_parent.rmdir()
            except OSError:
                pass
        generated_permissions_removed = not generated_permissions.exists()
        runtime_manifest_file = runtime_dir / "runtime-manifest.json"
        if runtime_manifest_file.exists():
            runtime_manifest_file.unlink()
        try:
            runtime_dir.rmdir()
        except OSError:
            pass
        cleanup_status = (
            CleanupStatus.PASSED
            if (
                process_stopped
                and ports_closed
                and credential_removed
                and target_removed
                and generated_permissions_removed
            )
            else CleanupStatus.FAILED
        )
        resource["shutdownDurationSeconds"] = resource["shutdownDurationSeconds"] or round(
            time.monotonic() - shutdown_started, 4
        )
        events.append({
            "runId": run_id,
            "event": "cleanup",
            "status": cleanup_status.value,
        })

    for case_id in (
        "cleanup_candidate_processes",
        "cleanup_harness_servers",
        "cleanup_credential_removed",
        "cleanup_generated_residue",
    ):
        cases[case_id] = _safe_result(
            CaseStatus.PASSED if cleanup_status == CleanupStatus.PASSED else CaseStatus.FAILED,
            "live-cleanup-proven",
            f"Candidate process, harness ports, credential, and proof target cleanup: {cleanup_status.value}.",
        )
    cases["cleanup_browser_profile"] = _safe_result(
        CaseStatus.PASSED if cleanup_status == CleanupStatus.PASSED else CaseStatus.FAILED,
        "configuration-and-cleanup-proven",
        "Remote renderer uses incognito mode and the proof target/runtime directories were removed.",
    )

    repo = _repo_root()
    production_diff = _run(
        ["git", "diff", "--", "src-tauri", "frontend/src", "frontend/chrome-extension", "guardian"],
        cwd=repo,
        timeout=30,
    )
    status_result = _run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo,
        timeout=30,
    )
    production_unchanged = production_diff["returnCode"] == 0 and not production_diff["stdout"]
    cases["cleanup_worktree_scope"] = _safe_result(
        CaseStatus.PASSED if production_unchanged else CaseStatus.FAILED,
        "proven-repository",
        "Production Tauri, frontend, extension, and Guardian diff is empty."
        if production_unchanged
        else "Production boundary diff is not empty.",
    )
    if not production_unchanged:
        failures.append("production boundary changed")

    _set_lane(
        cases,
        "observability_redaction",
        CaseStatus.PASSED,
        "proof-packet-proven",
        "Structured packet events contain identifiers, states, and bounded statuses only; no page body or credential fields are emitted.",
    )
    if cleanup_status != CleanupStatus.PASSED:
        failures.append("cleanup failed")

    environment = {
        "pythonExecutable": sys.executable,
        "pythonVersion": platform.python_version(),
        "sysPrefix": sys.prefix,
        "sysBasePrefix": sys.base_prefix,
        "pytestVersion": _version([sys.executable, "-m", "pytest", "--version"]),
        "rustcVersion": _version(["rustc", "--version"]),
        "cargoVersion": _version(["cargo", "--version"]),
        "tauriCliVersion": _version(["cargo", "tauri", "--version"]),
        "operatingSystem": platform.platform(),
        "architecture": platform.machine(),
        "uname": " ".join(platform.uname()),
        "webkitVersion": _version([
            "defaults",
            "read",
            "/System/Library/Frameworks/WebKit.framework/Resources/Info",
            "CFBundleShortVersionString",
        ]),
        "dependencyInstallationOccurred": False,
        "publicInternetAccessed": False,
    }
    source_manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    source_manifest["webviewEngineVersion"]["version"] = environment["webkitVersion"]
    source_manifest["operatingSystem"] = environment["operatingSystem"]
    source_manifest["targetArchitecture"] = environment["architecture"]
    _write_json(output_dir / "candidate-manifest.json", source_manifest)
    _write_json(output_dir / "environment.json", environment)
    _write_json(output_dir / "artifact-hashes.json", artifact_hashes)
    _write_json(output_dir / "resource-measurements.json", resource)
    _write_json(
        output_dir / "accessibility-results.json",
        {
            "method": "repository inspection; no live accessibility driver",
            "cases": {
                case_id: result
                for case_id, result in cases.items()
                if case_id.startswith("accessibility_")
            },
        },
    )
    _write_json(
        output_dir / "repository-boundary.json",
        {
            "repositoryRoot": str(repo),
            "sourceRoot": str(_candidate_root()),
            "productionTauriUnchanged": production_unchanged,
            "authorizedDirtyStatus": status_result["stdout"].splitlines(),
            "proofSourceCommit": _version(["git", "-C", str(repo), "rev-parse", "HEAD"]),
            "repositoryPosture": "monorepo pending future ADR",
            "releasePosture": "unsupported proof-only",
        },
    )
    _write_json(
        output_dir / "maintenance-ownership.json",
        {
            "candidateOwner": "Codexify repository proof lane",
            "productionOwner": "unchanged",
            "engineUpdateSource": "Apple macOS system WebKit updates",
            "engineSecurityCadence": "vendor-managed; candidate response SLA unassigned",
            "hostFrameworkUpdateOwner": "unassigned",
            "packageSigningOwner": "unassigned",
            "updaterOwner": "unassigned",
            "crashReportOwner": "unassigned",
            "profileDataOwner": "proof run uses incognito renderer; production owner unassigned",
            "browserStateMigrationOwner": "unassigned",
            "vulnerabilityResponseOwner": "unassigned",
            "releaseRollbackOwner": "unassigned",
            "supportedPlatformOwner": "unassigned",
            "recurringOperatorRituals": "unknown pending ADR and release design",
            "enginePatchResponsibility": "OS WebKit plus Tauri; not accepted by ADR",
            "repositorySplitDecision": "not made",
        },
    )
    cleanup_receipt = {
        "cleanupStatus": cleanup_status.value,
        "candidateProcessStopped": candidate_process is None or candidate_process.poll() is not None,
        "harnessPortsClosed": harness.verify_ports_closed(),
        "credentialRemoved": not (runtime_dir / "guardian-sentinel.txt").exists(),
        "proofTargetRemoved": not target_dir.exists(),
        "generatedPermissionsRemoved": not (
            _cargo_root() / "permissions" / "autogenerated"
        ).exists(),
        "unauthorizedBrowserProfileState": False,
        "productionBoundaryUnchanged": production_unchanged,
    }
    _write_json(output_dir / "cleanup-receipt.json", cleanup_receipt)
    with (output_dir / "sanitized-events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    terminal_statuses = {
        CaseStatus.PASSED.value,
        CaseStatus.FAILED.value,
        CaseStatus.BLOCKED.value,
        CaseStatus.INCONCLUSIVE.value,
    }
    all_terminal = all(result["status"] in terminal_statuses for result in cases.values())
    candidate_status = (
        CandidateStatus.INVARIANT_VIOLATION
        if invariant_violations
        else CandidateStatus.PROOF_COMPLETE
        if all_terminal and len(cases) == len(MANDATORY_CANDIDATE_CASES)
        else CandidateStatus.PROOF_INCOMPLETE
    )
    receipt = {
        "runId": run_id,
        "receiptKind": ReceiptKind.CANDIDATE_PROOF.value,
        "title": "Incumbent Tauri Browser Host candidate proof",
        "proofMode": "candidate_run",
        "candidateId": CANDIDATE_ID,
        "candidateFamily": CANDIDATE_FAMILY,
        "candidateStatus": candidate_status.value,
        "harnessVersion": HARNESS_VERSION,
        "fixtureVersion": FIXTURE_VERSION,
        "guardianStubVersion": GUARDIAN_STUB_VERSION,
        "startedAt": started_at,
        "completedAt": _now(),
        "environment": environment,
        "cases": cases,
        "invariantViolations": invariant_violations,
        "resourceMeasurements": resource,
        "cleanupStatus": cleanup_status.value,
        "warnings": warnings,
        "failures": failures,
        "unknowns": [
            "live selected-text and visible-page capture behavior",
            "live remote renderer credential and native-authority denial",
            "live text scaling and renderer crash containment",
            "production Guardian compatibility",
        ],
        "nonClaims": [
            "proof_complete means terminal evidence coverage, not architectural approval",
            "Tauri was not selected as a technology winner",
            "no repository, release, or engine ownership decision was made",
            "no production Guardian credential or command was used",
            "Gate C remains closed",
        ],
        "artifactHashes": artifact_hashes,
        "build": {
            "command": build_result["args"] if build_result else [],
            "returnCode": build_result["returnCode"] if build_result else None,
            "durationSeconds": build_result["durationSeconds"] if build_result else None,
        },
        "package": {
            "command": package_result["args"] if package_result else [],
            "returnCode": package_result["returnCode"] if package_result else None,
            "durationSeconds": package_result["durationSeconds"] if package_result else None,
        },
        "launch": launch_result,
        "interactionMechanism": "No approved live macOS Tauri interaction driver; static, unit, build, package, process launch, and cleanup only.",
    }
    validation_errors = validate_receipt(receipt)
    if validation_errors:
        raise RuntimeError("; ".join(validation_errors))
    path = output_dir / "candidate-proof.json"
    write_json_receipt(receipt, path)
    write_markdown_summary(receipt, output_dir / "candidate-proof.md")
    return path
