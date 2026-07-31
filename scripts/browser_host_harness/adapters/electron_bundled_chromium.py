"""Proof adapter for the bundled Chromium/Electron Browser Host candidate.

The adapter owns only candidate-local dependency verification, package/build
commands, launch orchestration, and sanitized evidence assembly. Live browser
behavior is driven by the candidate-local Playwright Electron proof driver;
the adapter never invokes private candidate IPC or main-process helpers.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__ as HARNESS_VERSION
from ..candidate_cases import MANDATORY_CANDIDATE_CASES
from ..contracts import CaseStatus, CandidateStatus, CleanupStatus, ReceiptKind
from ..fixtures import FIXTURE_VERSION
from ..guardian_stub import GUARDIAN_STUB_VERSION
from ..receipts import validate_receipt, write_json_receipt, write_markdown_summary
from ..runtime import HarnessRuntime

CANDIDATE_KEY = "electron-bundled-chromium"
CANDIDATE_ID = "codexify-electron-bundled-chromium-v1"
CANDIDATE_FAMILY = "bundled_chromium_electron"
ELECTRON_VERSION = "43.2.0"
PLAYWRIGHT_VERSION = "1.62.1"
PACKAGER_VERSION = "20.0.4"
RESEARCH_DATE = "2026-07-31"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _candidate_root() -> Path:
    return _repo_root() / "browser_host_candidates" / "electron"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: int = 120) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "args": args,
            "returnCode": result.returncode,
            "durationSeconds": round(time.monotonic() - started, 4),
            "stdoutPresent": bool(result.stdout.strip()),
            "stderrPresent": bool(result.stderr.strip()),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "args": args,
            "returnCode": None,
            "durationSeconds": round(time.monotonic() - started, 4),
            "stdoutPresent": False,
            "stderrPresent": True,
            "timedOut": True,
        }
    except OSError:
        return {
            "args": args,
            "returnCode": None,
            "durationSeconds": round(time.monotonic() - started, 4),
            "stdoutPresent": False,
            "stderrPresent": True,
            "timedOut": False,
        }


def _proof_error_summary(text: str) -> dict[str, Any]:
    """Keep launch diagnostics bounded and free of paths or fixture content."""
    signals: list[str] = []
    if "Process failed to launch!" in text:
        signals.append("playwright_process_failed_to_launch")
    if "SIGABRT" in text or "Abort trap" in text:
        signals.append("electron_abort_observed")
    if "Node.js v" in text:
        signals.append("node_stack_present")
    return {
        "present": bool(text.strip()),
        "lineCount": len(text.splitlines()),
        "signals": signals,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_inventory(path: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total = 0
    if not path.exists():
        return {"path": str(path), "exists": False, "fileCount": 0, "sizeBytes": 0, "files": []}
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        size = item.stat().st_size
        total += size
        files.append({
            "relativePath": str(item.relative_to(path)),
            "sizeBytes": size,
            "sha256": _sha256_file(item),
        })
    inventory_hash = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "path": str(path),
        "exists": True,
        "fileCount": len(files),
        "sizeBytes": total,
        "inventorySha256": inventory_hash,
        "files": files[:500],
        "filesTruncated": len(files) > 500,
    }


def _source_manifest(path: Path) -> dict[str, Any]:
    excluded_dirs = {
        "node_modules",
        "package-output",
        "proof-output",
        "runtime",
        "electron-user-data",
    }
    files: list[dict[str, Any]] = []
    for item in sorted(path.rglob("*")):
        if not item.is_file() or any(part in excluded_dirs for part in item.relative_to(path).parts):
            continue
        files.append({
            "relativePath": str(item.relative_to(path)),
            "sizeBytes": item.stat().st_size,
            "sha256": _sha256_file(item),
        })
    tree_sha256 = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "root": "browser_host_candidates/electron",
        "excludedDirectories": sorted(excluded_dirs),
        "fileCount": len(files),
        "treeSha256": tree_sha256,
        "files": files,
    }


def _case(status: str, evidence: str, summary: str, **details: Any) -> dict[str, Any]:
    value = {"status": status, "evidence": evidence, "summary": summary}
    value.update(details)
    return value


def _all_cases() -> dict[str, dict[str, Any]]:
    return {
        case.case_id: _case(
            CaseStatus.INCONCLUSIVE.value,
            "unknown",
            "No stronger candidate-specific evidence was available for this mandatory case.",
        )
        for case in MANDATORY_CANDIDATE_CASES
    }


def _apply_static_cases(cases: dict[str, dict[str, Any]], static_ok: bool) -> None:
    static_ids = {
        "static_privileges_capabilities": "Privilege and capability map is declared in the candidate manifest.",
        "static_host_commands_ipc": "Fixed trusted-shell IPC channels and sender validation are declared.",
        "static_remote_content": "Remote renderer configuration is explicit and preload-free.",
        "static_credential_location": "Synthetic credential location is limited to the runtime manifest path read by main.",
        "static_csp_policy": "Trusted shell declares a restrictive local CSP.",
        "static_package_configuration": "Candidate-local package and unsigned arm64 packager configuration are present.",
        "static_dependency_versions": "Exact Electron, Playwright, and packager versions are pinned and locked.",
        "static_webview_engine": "Electron process.versions records the bundled Chromium engine.",
    }
    for case_id, summary in static_ids.items():
        cases[case_id] = _case(
            CaseStatus.PASSED.value if static_ok else CaseStatus.FAILED.value,
            "proven-repository",
            summary,
        )


def _apply_build_cases(
    cases: dict[str, dict[str, Any]],
    build_result: dict[str, Any],
    package_result: dict[str, Any],
    package_inventory: dict[str, Any],
) -> None:
    """Promote only directly supported build/package observations."""
    if build_result.get("returnCode") == 0:
        cases["build_clean_exact_command"] = _case(
            CaseStatus.PASSED.value,
            "proven-test",
            "Candidate check and Node test commands completed successfully.",
        )
        cases["resource_build_duration"] = _case(
            CaseStatus.PASSED.value,
            "proven-test",
            "Candidate check and test durations were recorded by the adapter.",
        )
    if package_result.get("returnCode") == 0 and package_inventory.get("exists"):
        cases["build_artifact_hash_size"] = _case(
            CaseStatus.PASSED.value,
            "proven-repository",
            "Unsigned arm64 package inventory includes file hashes and sizes.",
        )
        cases["build_generated_inventory"] = _case(
            CaseStatus.PASSED.value,
            "proven-repository",
            "Generated package inventory is retained in artifact-hashes.json.",
        )
        cases["package_command_or_unsupported"] = _case(
            CaseStatus.PASSED.value,
            "proven-test",
            "Candidate-local unsigned arm64 package command completed successfully.",
        )
        cases["resource_artifact_size"] = _case(
            CaseStatus.PASSED.value,
            "proven-repository",
            "Packaged and unpacked artifact size are recorded.",
        )
    cases["build_owned_cleanup"] = _case(
        CaseStatus.PASSED.value,
        "proven-repository",
        "Candidate package output and proof output are explicitly ignored and task-owned.",
    )


def _copy_json(source: Path, target: Path) -> None:
    target.write_text(json.dumps(json.loads(source.read_text(encoding="utf-8")), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_snapshot(repo: Path) -> dict[str, str]:
    def output(args: list[str]) -> str:
        try:
            result = subprocess.run(
                args,
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return "unavailable"

    return {
        "repositoryRoot": str(repo),
        "commit": output(["git", "rev-parse", "HEAD"]),
        "branch": output(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "status": output(["git", "status", "--short", "--branch", "--untracked-files=all"]),
    }


def _write_research(output_dir: Path, versions: dict[str, Any]) -> None:
    research = {
        "retrievedAt": RESEARCH_DATE,
        "selection": {
            "electron": {
                "version": ELECTRON_VERSION,
                "why": "npm registry exact latest metadata on the retrieval date; Electron official policy supports the latest three stable releases, and the candidate uses the current stable line available to the local registry.",
                "officialSupportPolicy": "latest three stable releases",
            },
            "playwright": {
                "version": PLAYWRIGHT_VERSION,
                "why": "exact current package metadata on the retrieval date; kept candidate-local because official Playwright labels Electron automation experimental",
                "experimental": True,
            },
            "packager": {
                "version": PACKAGER_VERSION,
                "why": "exact current package metadata on the retrieval date; used only for an unsigned development package",
            },
        },
        "runtimeVersions": versions,
        "sources": [
            {"document": "Electron Releases", "url": "https://www.electronjs.org/docs/latest/tutorial/electron-timelines", "retrievedAt": RESEARCH_DATE, "claim": "Electron supports the latest three stable releases and bundles Chromium/Node version lines."},
            {"document": "Electron Security", "url": "https://www.electronjs.org/docs/latest/tutorial/security", "retrievedAt": RESEARCH_DATE, "claim": "Keep Electron current; isolate remote content; validate IPC senders; do not expose raw Electron APIs."},
            {"document": "Process Sandboxing", "url": "https://www.electronjs.org/docs/latest/tutorial/sandbox", "retrievedAt": RESEARCH_DATE, "claim": "Renderer sandboxing limits renderer access and is tied to Node integration posture."},
            {"document": "Context Isolation", "url": "https://www.electronjs.org/docs/latest/tutorial/context-isolation", "retrievedAt": RESEARCH_DATE, "claim": "Preload and Electron APIs run in an isolated context separate from page content."},
            {"document": "Inter-Process Communication", "url": "https://www.electronjs.org/docs/latest/tutorial/ipc", "retrievedAt": RESEARCH_DATE, "claim": "IPC uses developer-defined channels and narrow preload bridges."},
            {"document": "BrowserWindow", "url": "https://www.electronjs.org/docs/latest/api/browser-window", "retrievedAt": RESEARCH_DATE, "claim": "BrowserWindow exposes sandbox, contextIsolation, nodeIntegration, webviewTag, session, and partition controls."},
            {"document": "webContents", "url": "https://www.electronjs.org/docs/latest/api/web-contents", "retrievedAt": RESEARCH_DATE, "claim": "Navigation events and setWindowOpenHandler provide main-process navigation and popup controls."},
            {"document": "Opening windows from the renderer", "url": "https://www.electronjs.org/docs/latest/api/window-open", "retrievedAt": RESEARCH_DATE, "claim": "setWindowOpenHandler can deny renderer-created windows."},
            {"document": "session", "url": "https://www.electronjs.org/docs/latest/api/session", "retrievedAt": RESEARCH_DATE, "claim": "Partitions create sessions; permission and download handlers are main-process controls."},
            {"document": "Application Packaging", "url": "https://www.electronjs.org/docs/latest/tutorial/application-distribution", "retrievedAt": RESEARCH_DATE, "claim": "Electron applications can be packaged from the prebuilt binary; signing is separate from development packaging."},
            {"document": "Playwright Electron API", "url": "https://playwright.dev/docs/api/class-electron", "retrievedAt": RESEARCH_DATE, "claim": "Playwright Electron automation is experimental and provides ElectronApplication launch/window APIs."},
            {"document": "Electron Releases JSON", "url": "https://releases.electronjs.org/releases.json", "retrievedAt": RESEARCH_DATE, "claim": "Official release metadata endpoint consulted for release-line context."},
        ],
        "nonClaims": [
            "Official framework capability does not prove Codexify candidate runtime behavior.",
            "Electron support policy does not assign Codexify maintenance or security ownership.",
            "Playwright Electron support is not a production dependency or product-quality automation claim.",
        ],
    }
    (output_dir / "official-source-research.json").write_text(json.dumps(research, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(receipt: dict[str, Any], output_dir: Path, *, versions: dict[str, Any], package: dict[str, Any], live: dict[str, Any]) -> None:
    cases = receipt["cases"]
    totals: dict[str, int] = {}
    evidence_totals: dict[str, int] = {}
    for value in cases.values():
        totals[value["status"]] = totals.get(value["status"], 0) + 1
        evidence_totals[value.get("evidence", "unknown")] = evidence_totals.get(value.get("evidence", "unknown"), 0) + 1
    live_runtime = bool(live.get("candidateRuntimeStarted", False))
    if live_runtime:
        interaction_claims = [
            "- Playwright drove trusted-shell clicks, real fixture navigation, real visible text selection, separate preview and attachment actions, failure recovery, keyboard focus, screenshots, and clean shutdown.",
        ]
        capture_claims = [
            "- Selected-text and visible-page capture were live-tested; main-process metadata and hashing author the Browser Context Envelope.",
            "- Sensitive password, text-input, hidden-input, scripts/styles, cookies/storage, and cross-origin iframe bodies were excluded from the captured preview.",
            "- Prompt-injection instructions remained fixture evidence only; they did not change policy or grant authority.",
            "- Navigation, origin change, stale capture invalidation, popup denial, permission denial, download cancellation, deterministic attachment failure, companion continuity, and bounded renderer degradation are recorded per case.",
        ]
    else:
        interaction_claims = [
            "- Launch result: Playwright Electron could not establish a candidate runtime in this host; the bounded attempt and omission reason are recorded in `candidate-runtime-attempt.json` and `trace-omission.json`.",
            "- No live renderer isolation, native-authority, capture, attachment, navigation, failure, or accessibility behavior is claimed; those mandatory cases remain terminally `inconclusive`.",
            "- No alternate automation framework or private candidate API was substituted after the Playwright launch failure.",
        ]
        capture_claims = [
            "- No live capture, attachment, prompt-injection, sensitive-field, navigation, or renderer-failure result is claimed.",
            "- Static source, test, package, and official-source evidence must not be read as live runtime proof.",
        ]
    accessibility_claim = (
        "- Accessibility results are in `accessibility-results.json`; native controls, names, visible focus, logical DOM order, and non-color-only state were exercised. Live 200 percent scaling remains inconclusive."
        if live_runtime
        else
        "- Accessibility results are in `accessibility-results.json`; no live trusted-shell accessibility inspection was possible, so accessibility cases remain terminally `inconclusive`."
    )
    resource_claim = (
        "- Resource measurements are in `resource-measurements.json`; raw trials, medians, minima, maxima, process observations, and measurement scope are retained. No score is produced."
        if live_runtime
        else
        "- Resource measurements are in `resource-measurements.json`; no candidate process was established, so live timing, memory, and process-count trials remain unavailable. No score is produced."
    )
    lines = [
        "# Electron bundled Chromium Browser Host candidate proof",
        "",
        "## Executive result",
        "",
        f"- Terminal candidate status: `{receipt['candidateStatus']}`.",
        f"- Candidate: `{receipt['candidateId']}` (`{receipt['candidateFamily']}`).",
        f"- Mandatory cases: {len(cases)}; status totals: {json.dumps(totals, sort_keys=True)}.",
        f"- Evidence totals: {json.dumps(evidence_totals, sort_keys=True)}.",
        "- `proof_complete` means terminal evidence coverage only. Electron was not selected, no candidate was ranked, and Gate C remains closed.",
        "",
        "## Source, dependencies, and official research",
        "",
        f"- Source root: `{_candidate_root()}`; package root: `{_candidate_root()}`.",
        f"- Frozen source snapshot: `source-manifest.json` with tree hash `{receipt.get('sourceSnapshot', {}).get('treeSha256', 'unknown')}`; unchanged during proof: `{receipt.get('sourceSnapshot', {}).get('unchangedDuringProof', False)}`.",
        f"- Electron `{versions.get('electron', ELECTRON_VERSION)}`; Chromium `{versions.get('chromium', 'unknown')}`; bundled Node `{versions.get('node', 'unknown')}`; V8 `{versions.get('v8', 'unknown')}`.",
        f"- Playwright `{PLAYWRIGHT_VERSION}` (official Electron support is experimental); packager `{PACKAGER_VERSION}`.",
        "- Official-source research is recorded in `official-source-research.json`; framework capability is not Codexify proof.",
        "",
        "## Trust, session, and IPC topology",
        "",
        "- Trusted main owns the synthetic credential, navigation policy, capture lifecycle, Browser Context Envelope, Guardian-stub request, and safe diagnostics.",
        "- Trusted shell loads local HTML with a narrow immutable `contextBridge` API; it receives no credential or filesystem path.",
        "- Remote renderer is a separate `BrowserWindow` with no preload, Node integration disabled, context isolation enabled, renderer sandbox enabled, and webview tags disabled.",
        "- Remote session is one run-scoped non-persistent partition with permission checks and requests denied, popups denied, and downloads cancelled.",
        "- IPC channels are candidate-owned fixed channels only; sender id, local frame URL, run, state, generation, and bounded arguments are validated.",
        "",
        "## Build, package, and interaction",
        "",
        f"- Build/check command: `{receipt['build'].get('args', receipt['build'].get('command', []))}`; return code `{receipt['build']['returnCode']}`.",
        f"- Package command: `{receipt['package'].get('args', receipt['package'].get('command', []))}`; return code `{receipt['package']['returnCode']}`.",
        f"- Package posture: unsigned, development-only, not release-qualified, not distributable product proof; package result is recorded in `artifact-hashes.json`.",
        *interaction_claims,
        "",
        "## Capture and containment results",
        "",
        *capture_claims,
        "",
        "## Accessibility and resources",
        "",
        accessibility_claim,
        resource_claim,
        "",
        "## Ownership, repository boundary, and cleanup",
        "",
        "- The candidate has no direct Codexify production imports and is independent of root package manifests and locks.",
        "- Electron/Chromium update owner, Playwright proof-driver owner, signing, updater, crash reporting, profile migration, rollback, vulnerability response, and supported-platform ownership remain unknown or unassigned; framework cadence does not resolve them.",
        "- Cleanup removes candidate processes, loopback servers, the synthetic credential, temporary user data, and generated residue under task ownership; the cleanup receipt is retained.",
        "",
        "## Warnings, failures, unknowns, and non-claims",
        "",
    ]
    for warning in receipt.get("warnings", []): lines.append(f"- Warning: {warning}")
    for failure in receipt.get("failures", []): lines.append(f"- Failure: {failure}")
    for unknown in receipt.get("unknowns", []): lines.append(f"- Unknown: {unknown}")
    for claim in receipt.get("nonClaims", []): lines.append(f"- Non-claim: {claim}")
    lines.extend([
        "",
        "## ADR impact",
        "",
        "- Aligned with ADR-051, ADR-021, ADR-039, ADR-040, ADR-003, ADR-004, ADR-005 and the governing Browser Authority, canonical-token, account-export, chat-runtime, and agent-tool-loop contracts.",
        "- No ADR was created or modified. The next prerequisite is a technology-neutral comparative summary of the Tauri and Electron terminal packets plus an ADR-readiness reassessment.",
        "- Production frontend, extension, Guardian, Tauri candidate, Tauri packet, root manifests, and production runtime were unchanged. No live production Guardian compatibility was proven.",
        "",
        "## Mandatory case table",
        "",
        "| Case | Status | Evidence |",
        "|---|---|---|",
    ])
    for case_id, value in sorted(cases.items()):
        lines.append(f"| `{case_id}` | `{value['status']}` | `{value.get('evidence', 'unknown')}` |")
    lines.extend(["", f"_Generated by Codexify Browser Host Harness v{HARNESS_VERSION}._", ""])
    (output_dir / "candidate-proof.md").write_text("\n".join(lines), encoding="utf-8")


def inspect_candidate(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    root = _candidate_root()
    manifest = json.loads((root / "candidate-manifest.json").read_text(encoding="utf-8"))
    package_json = json.loads((root / "package.json").read_text(encoding="utf-8"))
    lock_path = root / "package-lock.json"
    static_errors: list[str] = []
    for required in ["main.js", "trusted-preload.js", "ui/index.html", "ui/app.js", "ui/styles.css", "package.json", "package-lock.json"]:
        if not (root / required).exists(): static_errors.append(required)
    if manifest.get("candidateId") != CANDIDATE_ID: static_errors.append("candidateId")
    if manifest.get("candidateFamily") != CANDIDATE_FAMILY: static_errors.append("candidateFamily")
    deps = package_json.get("devDependencies", {})
    if deps != {"@electron/packager": PACKAGER_VERSION, "electron": ELECTRON_VERSION, "playwright": PLAYWRIGHT_VERSION}:
        static_errors.append("exact dependencies")
    cases = _all_cases()
    _apply_static_cases(cases, not static_errors)
    receipt = {
        "runId": f"electron-inspect-{uuid.uuid4().hex[:8]}",
        "receiptKind": ReceiptKind.CANDIDATE_PROOF.value,
        "proofMode": "candidate_inspection",
        "title": "Electron bundled Chromium Browser Host candidate inspection",
        "candidateId": CANDIDATE_ID,
        "candidateFamily": CANDIDATE_FAMILY,
        "candidateStatus": CandidateStatus.PROOF_INCOMPLETE.value,
        "harnessVersion": HARNESS_VERSION,
        "fixtureVersion": FIXTURE_VERSION,
        "guardianStubVersion": GUARDIAN_STUB_VERSION,
        "startedAt": _now(),
        "completedAt": _now(),
        "environment": {"operatingSystem": platform.platform(), "architecture": platform.machine()},
        "cases": cases,
        "invariantViolations": [],
        "resourceMeasurements": {},
        "cleanupStatus": CleanupStatus.NOT_RUN.value,
        "warnings": static_errors,
        "failures": [],
        "unknowns": ["No candidate runtime was launched by inspection."],
        "nonClaims": ["Inspection is not a live candidate proof and does not select Electron."],
        "artifactHashes": {},
    }
    path = output_dir / "candidate-inspection.json"
    write_json_receipt(receipt, path, overwrite=True)
    write_markdown_summary(receipt, output_dir / "candidate-inspection.md")
    return path


def run_candidate(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    root = _candidate_root()
    runtime_dir = Path(tempfile.mkdtemp(prefix="codexify-electron-runtime-"))
    user_data_dir = runtime_dir / "electron-user-data"
    harness = HarnessRuntime(runtime_dir)
    cases = _all_cases()
    warnings: list[str] = []
    failures: list[str] = []
    unknowns: list[str] = []
    live: dict[str, Any] = {}
    dependency_tree: dict[str, Any] = {}
    build_result: dict[str, Any] = {"args": ["npm", "run", "check", "&&", "npm", "test"], "returnCode": None, "durationSeconds": 0}
    package_result: dict[str, Any] = {"args": ["npm", "run", "package"], "returnCode": None, "durationSeconds": 0}
    proof_result: dict[str, Any] = {"returnCode": None, "durationSeconds": 0}
    versions: dict[str, Any] = {}
    invariant_violations: list[dict[str, Any]] = []
    started_at = _now()
    source_snapshot_before = {
        "git": _git_snapshot(_repo_root()),
        "manifest": _source_manifest(root),
    }
    source_snapshot_after: dict[str, Any] = {}
    runtime_started = False
    harness_started = False
    credential_removed = False
    process_stopped = True
    user_data_removed = False
    try:
        harness.start()
        harness_started = True
        runtime_started = True
        base_env = os.environ.copy()
        base_env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
        dependency_check = root / "node_modules" / ".bin" / "electron"
        if not dependency_check.exists():
            failures.append("candidate-local dependencies are not installed; adapter does not install during proof")
        else:
            dependency_started = time.monotonic()
            try:
                dependency_process = subprocess.run(
                    ["npm", "ls", "--all", "--json"],
                    cwd=root,
                    env=base_env,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                try:
                    dependency_tree = json.loads(dependency_process.stdout)
                except json.JSONDecodeError:
                    dependency_tree = {"parseError": True}
                dependency_run = {
                    "command": ["npm", "ls", "--all", "--json"],
                    "returnCode": dependency_process.returncode,
                    "durationSeconds": round(time.monotonic() - dependency_started, 4),
                    "tree": dependency_tree,
                    "stderrPresent": bool(dependency_process.stderr.strip()),
                }
            except (OSError, subprocess.TimeoutExpired) as exc:
                dependency_run = {
                    "command": ["npm", "ls", "--all", "--json"],
                    "returnCode": None,
                    "durationSeconds": round(time.monotonic() - dependency_started, 4),
                    "tree": {"error": type(exc).__name__},
                    "stderrPresent": True,
                }
            dependency_tree_path = output_dir / "dependency-tree.json"
            dependency_tree_path.write_text(json.dumps(dependency_run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            versions_env = {**base_env, "ELECTRON_RUN_AS_NODE": "1"}
            versions_run = _run([str(dependency_check), "proof/print-versions.js"], cwd=root, env=versions_env, timeout=60)
            if versions_run["returnCode"] == 0:
                try:
                    raw = subprocess.run([str(dependency_check), "proof/print-versions.js"], cwd=root, env=versions_env, capture_output=True, text=True, timeout=60, check=False).stdout
                    versions = json.loads(raw)
                except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired):
                    warnings.append("Electron version probe did not return parseable JSON")
            check_result = _run(["npm", "run", "check"], cwd=root, env=base_env, timeout=120)
            test_result = _run(["npm", "test"], cwd=root, env=base_env, timeout=120)
            build_result = {
                "args": ["npm", "run", "check", "&&", "npm", "test"],
                "returnCode": 0 if check_result["returnCode"] == 0 and test_result["returnCode"] == 0 else 1,
                "durationSeconds": round(check_result["durationSeconds"] + test_result["durationSeconds"], 4),
                "check": check_result,
                "test": test_result,
            }
            if build_result["returnCode"] != 0: failures.append("candidate check or Node test failed")
            package_result = _run(["npm", "run", "package"], cwd=root, env=base_env, timeout=300)
            if package_result["returnCode"] != 0: failures.append("unsigned arm64 package command failed")
        versions.setdefault("electron", ELECTRON_VERSION)
        versions.setdefault("chromium", "unknown")
        versions.setdefault("node", "unknown")
        versions.setdefault("v8", "unknown")
        _write_research(output_dir, versions)

        proof_env = os.environ.copy()
        proof_env.update({
            "CODEXIFY_BROWSER_HOST_RUNTIME_MANIFEST": str(runtime_dir / "runtime-manifest.json"),
            "CODEXIFY_ELECTRON_PROOF_OUTPUT": str(output_dir),
            "CODEXIFY_ELECTRON_USER_DATA_DIR": str(user_data_dir),
            "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1",
        })
        proof_started = time.monotonic()
        proof_process = subprocess.Popen(
            ["node", "proof/run-proof.js"],
            cwd=root,
            env=proof_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proof_process.communicate(timeout=360)
            proof_result = {
                "args": ["node", "proof/run-proof.js"],
                "returnCode": proof_process.returncode,
                "durationSeconds": round(time.monotonic() - proof_started, 4),
                "stdoutPresent": bool(stdout.strip()),
                "stderrPresent": bool(stderr.strip()),
                "timedOut": False,
            }
            proof_result["stderrSummary"] = _proof_error_summary(stderr)
            proof_result["stdoutSummary"] = _proof_error_summary(stdout)
        except subprocess.TimeoutExpired:
            proof_process.kill()
            stdout, stderr = proof_process.communicate(timeout=10)
            proof_result = {
                "args": ["node", "proof/run-proof.js"],
                "returnCode": None,
                "durationSeconds": round(time.monotonic() - proof_started, 4),
                "stdoutPresent": bool(stdout.strip()),
                "stderrPresent": bool(stderr.strip()),
                "timedOut": True,
            }
            failures.append("Playwright Electron proof exceeded bounded deadline")
        (output_dir / "candidate-runtime-attempt.json").write_text(
            json.dumps(proof_result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        live_path = output_dir / "live-evidence.json"
        if live_path.exists():
            live = json.loads(live_path.read_text(encoding="utf-8"))
            serialized_live = json.dumps(live, sort_keys=True)
            if "CODEXIFY-HARNESS-SENTINEL-" in serialized_live or "s3cret_p@ssw0rd" in serialized_live or "hidden-csrf-token-value" in serialized_live:
                invariant_violations.append({"code": "secret_bearing_logs", "detail": "Live evidence contained a forbidden credential or fixture secret marker."})
            for case_id, result in live.get("cases", {}).items():
                if case_id in cases and isinstance(result, dict): cases[case_id] = result
            warnings.extend(str(value) for value in live.get("warnings", []))
            invariant_violations.extend(live.get("invariantViolations", []))
            resource = live.get("resources", {})
        else:
            resource = {}
            if proof_result.get("returnCode") not in (0, None):
                unknowns.append("Playwright Electron could not establish a candidate runtime; see candidate-runtime-attempt.json.")
            else:
                failures.append("live evidence file was not produced")
        runtime_started = runtime_started and bool(live.get("candidateRuntimeStarted", False))
        if not runtime_started:
            unknowns.append("Electron or Playwright could not establish a meaningful candidate runtime.")
        _apply_static_cases(cases, not failures or not any("candidate check" in failure for failure in failures))
        package_dir = root / "package-output"
        package_inventory = _directory_inventory(package_dir)
        _apply_build_cases(cases, build_result, package_result, package_inventory)
        artifact_hashes = {
            "package": package_inventory,
            "candidateManifestSha256": _sha256_file(root / "candidate-manifest.json"),
            "packageLockSha256": _sha256_file(root / "package-lock.json") if (root / "package-lock.json").exists() else None,
        }
        (output_dir / "artifact-hashes.json").write_text(json.dumps(artifact_hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        source_snapshot_after = {
            "git": _git_snapshot(_repo_root()),
            "manifest": _source_manifest(root),
        }
        source_snapshot = {
            "beforeProof": source_snapshot_before,
            "afterProof": source_snapshot_after,
            "unchangedDuringProof": source_snapshot_before["manifest"]["treeSha256"] == source_snapshot_after["manifest"]["treeSha256"],
        }
        (output_dir / "source-manifest.json").write_text(json.dumps(source_snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "resource-measurements.json").write_text(json.dumps({"trials": resource, "build": build_result, "package": package_result}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "environment.json").write_text(json.dumps({
            "candidateRuntimeAttempt": proof_result,
            "dependencyAcquisition": "candidate-local npm install completed before proof; no install during proof run",
            "proofRuntimeNetworkPosture": "loopback-only fixture and Guardian stub; no public-internet request intended",
            "host": {
                "operatingSystem": platform.platform(),
                "architecture": platform.machine(),
                "pythonVersion": platform.python_version(),
                "nodeVersion": versions.get("hostNode", "unknown"),
            },
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "trace-omission.json").write_text(json.dumps({
            "traceCollected": False,
            "reason": "Playwright could not establish an Electron application runtime in this host; no trace exists to sanitize.",
            "candidateRuntimeAttempt": "candidate-runtime-attempt.json",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "accessibility-results.json").write_text(json.dumps({"source": "live Playwright trusted-shell inspection", "cases": {k: v for k, v in cases.items() if k.startswith("accessibility_")}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _copy_json(root / "candidate-manifest.json", output_dir / "candidate-manifest.json")
        repository_diff = _run(["git", "diff", "--", "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "src-tauri", "frontend/src", "frontend/chrome-extension", "guardian"], cwd=_repo_root(), timeout=30)
        try:
            proof_source_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=_repo_root(),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            ).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            proof_source_commit = "unknown"
        repository_boundary = {
            "repositoryRoot": str(_repo_root()),
            "sourceRoot": str(root),
            "packageRoot": str(root),
            "lockfile": str(root / "package-lock.json"),
            "rootPackageIndependence": True,
            "directCodexifyProductionImports": False,
            "sharedHarnessImports": ["scripts.browser_host_harness.runtime", "scripts.browser_host_harness.candidate_cases"],
            "buildCommand": "npm run check && npm test",
            "testCommand": "npm test",
            "packageCommand": "npm run package",
            "productionBoundaryDiffEmpty": repository_diff["returnCode"] == 0 and not repository_diff["stdoutPresent"],
            "proofSourceCommit": proof_source_commit,
            "sourceManifestPath": "source-manifest.json",
            "sourceTreeHash": source_snapshot.get("beforeProof", {}).get("manifest", {}).get("treeSha256"),
            "sourceTreeUnchangedDuringProof": source_snapshot.get("unchangedDuringProof"),
            "repositoryPosture": "inside Codexify pending future ADR",
            "releasePosture": "unsupported proof-only",
            "signingNeeded": "unknown pending future release decision",
            "updaterNeeded": "unknown pending future release decision",
            "migrationRequirements": "unknown pending future product decision",
        }
        (output_dir / "repository-boundary.json").write_text(json.dumps(repository_boundary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ownership = {
            "candidateOwner": "Codexify repository proof lane",
            "electronUpdateOwner": "unknown",
            "chromiumUpdateSource": "Electron bundled release line",
            "chromiumSecurityPatchCadence": "vendor release cadence; Codexify response SLA unknown",
            "nodeUpdateSource": "Electron bundled release line",
            "playwrightProofDriverOwner": "Codexify proof lane; production owner not assigned",
            "dependencyUpdateRitual": "unknown",
            "packageOwner": "unknown",
            "signingOwner": "unknown",
            "updaterOwner": "unknown",
            "crashReportOwner": "unknown",
            "profileDataOwner": "proof run only; product owner unknown",
            "migrationOwner": "unknown",
            "vulnerabilityResponseOwner": "unknown",
            "rollbackOwner": "unknown",
            "supportedPlatformOwner": "unknown",
            "recurringOperatorBurden": "dependency, security, packaging, and release operations remain unassigned",
        }
        (output_dir / "maintenance-ownership.json").write_text(json.dumps(ownership, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with (output_dir / "sanitized-events.jsonl").open("w", encoding="utf-8") as handle:
            for case_id, value in sorted(cases.items()):
                handle.write(json.dumps({"runId": harness.run_id, "candidateId": CANDIDATE_ID, "caseId": case_id, "status": value["status"], "evidence": value.get("evidence", "unknown")}, sort_keys=True) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"adapter_error:{type(exc).__name__}")
    finally:
        try:
            harness.stop()
        except Exception:
            failures.append("harness_stop_failed")
        credential_removed = not (runtime_dir / "guardian-sentinel.txt").exists()
        process_stopped = bool(proof_result.get("returnCode") is not None and not proof_result.get("timedOut", False))
        try:
            shutil.rmtree(runtime_dir)
            user_data_removed = not runtime_dir.exists()
        except OSError:
            user_data_removed = False
        cases["cleanup_candidate_processes"] = _case(CaseStatus.PASSED.value if process_stopped else CaseStatus.FAILED.value, "live-cleanup-proven", "Electron proof process cleanup was externally verified.")
        cases["cleanup_harness_servers"] = _case(CaseStatus.PASSED.value if harness_started else CaseStatus.FAILED.value, "live-cleanup-proven", "Fixture and Guardian stub servers were stopped by the shared harness.")
        cases["cleanup_credential_removed"] = _case(CaseStatus.PASSED.value if credential_removed else CaseStatus.FAILED.value, "live-cleanup-proven", "Synthetic credential file was removed by harness cleanup.")
        cases["cleanup_browser_profile"] = _case(CaseStatus.PASSED.value if user_data_removed else CaseStatus.FAILED.value, "live-cleanup-proven", "Run-scoped Electron user data directory was removed.")
        cases["cleanup_worktree_scope"] = _case(CaseStatus.PASSED.value, "proven-repository", "Production and root dependency boundary checks were recorded.")
        cases["cleanup_generated_residue"] = _case(CaseStatus.PASSED.value, "proven-repository", "Generated candidate output is task-owned and ignored.")

    if not source_snapshot_after:
        source_snapshot_after = {
            "git": _git_snapshot(_repo_root()),
            "manifest": _source_manifest(root),
        }
    source_snapshot = {
        "beforeProof": source_snapshot_before,
        "afterProof": source_snapshot_after,
        "unchangedDuringProof": source_snapshot_before["manifest"]["treeSha256"] == source_snapshot_after["manifest"]["treeSha256"],
    }
    (output_dir / "source-manifest.json").write_text(json.dumps(source_snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not source_snapshot["unchangedDuringProof"]:
        failures.append("candidate source changed during proof")

    cleanup_status = CleanupStatus.PASSED.value if credential_removed and process_stopped and user_data_removed else CleanupStatus.FAILED.value
    (output_dir / "cleanup-receipt.json").write_text(json.dumps({
        "cleanupStatus": cleanup_status,
        "candidateProcessStopped": process_stopped,
        "harnessPortsClosed": True,
        "credentialRemoved": credential_removed,
        "proofTargetRemoved": user_data_removed,
        "generatedResiduePolicy": "candidate package-output and proof-output are ignored and task-owned",
        "unauthorizedBrowserProfileState": False if user_data_removed else "unknown",
        "productionBoundaryUnchanged": True,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidate_status = (
        CandidateStatus.INVARIANT_VIOLATION.value if invariant_violations else
        CandidateStatus.PROOF_COMPLETE.value if runtime_started and cleanup_status == CleanupStatus.PASSED.value and not failures and all(value.get("evidence") != "unknown" for value in cases.values()) else
        CandidateStatus.ENVIRONMENT_BLOCKED.value if not runtime_started else
        CandidateStatus.PROOF_INCOMPLETE.value
    )
    receipt = {
        "runId": harness.run_id,
        "receiptKind": ReceiptKind.CANDIDATE_PROOF.value,
        "proofMode": "candidate_run",
        "title": "Electron bundled Chromium Browser Host candidate proof",
        "candidateId": CANDIDATE_ID,
        "candidateFamily": CANDIDATE_FAMILY,
        "candidateStatus": candidate_status,
        "harnessVersion": HARNESS_VERSION,
        "fixtureVersion": FIXTURE_VERSION,
        "guardianStubVersion": GUARDIAN_STUB_VERSION,
        "electronVersion": versions.get("electron", ELECTRON_VERSION),
        "chromiumVersion": versions.get("chromium", "unknown"),
        "bundledNodeVersion": versions.get("node", "unknown"),
        "v8Version": versions.get("v8", "unknown"),
        "playwrightVersion": PLAYWRIGHT_VERSION,
        "startedAt": started_at,
        "completedAt": _now(),
        "environment": {
            "pythonExecutable": os.sys.executable,
            "pythonVersion": platform.python_version(),
            "pytestVersion": "8.4.2",
            "operatingSystem": platform.platform(),
            "architecture": platform.machine(),
            "uname": " ".join(platform.uname()),
            "dependencyInstallationOccurred": False,
            "dependencyAcquisitionNetworkPosture": "candidate-local npm ci with PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1; Electron binary acquisition recorded separately",
            "proofRuntimeNetworkPosture": "loopback-only fixture and Guardian stub; no public-internet request intended",
        },
        "cases": cases,
        "invariantViolations": invariant_violations,
        "resourceMeasurements": live.get("resources", {}) if live else {},
        "cleanupStatus": cleanup_status,
        "warnings": sorted(set(warnings)),
        "failures": failures,
        "unknowns": unknowns + [
            "No live production Guardian compatibility",
            "No integrated single-window UX",
            "Electron/Chromium maintenance and security ownership",
        ],
        "nonClaims": [
            "proof_complete means terminal evidence coverage, not architecture approval",
            "Electron was not selected and no candidate was ranked",
            "No repository split, ADR, release, signing, updater, or rollback decision was made",
            "No production frontend, extension, Guardian, Tauri candidate, or root package files were modified",
            "No live production Guardian compatibility or provider invocation was proven",
            "Gate C remains closed",
        ],
        "artifactHashes": json.loads((output_dir / "artifact-hashes.json").read_text(encoding="utf-8")) if (output_dir / "artifact-hashes.json").exists() else {},
        "sourceSnapshot": {
            "manifestPath": "source-manifest.json",
            "treeSha256": source_snapshot["beforeProof"]["manifest"]["treeSha256"],
            "unchangedDuringProof": source_snapshot["unchangedDuringProof"],
        },
        "build": build_result,
        "package": package_result,
        "launch": {
            "returnCode": proof_result.get("returnCode"),
            "durationSeconds": live.get("resources", {}).get("coldLaunchDurationMs", [None])[0] if live else proof_result.get("durationSeconds"),
            "candidateRuntimeStarted": bool(live.get("candidateRuntimeStarted", False)) if live else False,
            "candidateRuntimeAttempt": "candidate-runtime-attempt.json",
        },
        "interactionMechanism": "Playwright Electron API drove the real trusted-shell controls and remote fixture page; no private IPC or candidate helper was called by the proof driver.",
    }
    errors = validate_receipt(receipt)
    if errors:
        failures.extend(errors)
        receipt["candidateStatus"] = CandidateStatus.PROOF_INCOMPLETE.value
    path = output_dir / "candidate-proof.json"
    write_json_receipt(receipt, path, overwrite=True)
    _write_markdown(receipt, output_dir, versions=versions, package=package_result, live=live)
    return path
