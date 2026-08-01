from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
INFO = "INFO"

EVIDENCE = "evidence"
RUNTIME_RISK = "runtime_risk"
DOCUMENTATION_DRIFT = "documentation_drift"
SCANNER_DRIFT = "scanner_drift"
PROOF_GAP = "manual_proof_required"
RELEASE_BOUNDARY = "release_boundary"

STATIC = "static"
DOCUMENTED = "documented"
TEST = "test"
LIVE_RUNTIME = "live_runtime"


@dataclass
class CheckResult:
    status: str
    label: str
    evidence: str
    finding_type: str = EVIDENCE
    evidence_level: str = STATIC


@dataclass
class DomainReport:
    name: str
    checks: list[CheckResult]
    summary: str
    manual_prompts: list[str]

    def count(self, status: str) -> int:
        return sum(check.status == status for check in self.checks)


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unknown git error")
    return result.stdout


def docs(name: str) -> tuple[str, ...]:
    return (f"docs/architecture/{name}", f"docs/{name}", name)


def first_path(candidates: Iterable[str]) -> Path | None:
    return next(
        (REPO_ROOT / candidate for candidate in candidates if (REPO_ROOT / candidate).exists()),
        None,
    )


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def exists(
    label: str,
    candidates: Iterable[str],
    *,
    missing_status: str = WARN,
    finding_type: str = EVIDENCE,
    evidence_level: str = STATIC,
) -> CheckResult:
    values = list(candidates)
    path = first_path(values)
    if path:
        return CheckResult(PASS, label, f"{relative(path)} exists", EVIDENCE, evidence_level)
    return CheckResult(
        missing_status,
        label,
        f"missing: {', '.join(values)}",
        finding_type,
        evidence_level,
    )


def contains(
    label: str,
    candidates: Iterable[str],
    patterns: Iterable[str],
    *,
    require_all: bool = False,
    contract_check: bool = False,
    evidence_level: str = DOCUMENTED,
) -> CheckResult:
    values = list(candidates)
    needles = list(patterns)
    path = first_path(values)
    if not path:
        return CheckResult(
            WARN,
            label,
            f"missing: {', '.join(values)}",
            DOCUMENTATION_DRIFT,
            evidence_level,
        )
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    matched = [needle for needle in needles if needle.lower() in text]
    if (require_all and len(matched) == len(needles)) or (not require_all and matched):
        return CheckResult(
            PASS,
            label,
            f"{relative(path)} matches {', '.join(repr(item) for item in matched[:3])}",
            EVIDENCE,
            evidence_level,
        )
    if contract_check:
        return CheckResult(
            WARN,
            label,
            f"{relative(path)} lacks expected contract text",
            DOCUMENTATION_DRIFT,
            evidence_level,
        )
    return CheckResult(
        INFO,
        label,
        f"{relative(path)} no longer matches scanner text",
        SCANNER_DRIFT,
        evidence_level,
    )


def proof_gap(label: str, evidence: str) -> CheckResult:
    return CheckResult(INFO, label, evidence, PROOF_GAP, LIVE_RUNTIME)


def current_state_freshness(max_age_days: int = 14) -> CheckResult:
    path = first_path(docs("00-current-state.md"))
    if not path:
        return CheckResult(
            FAIL,
            "Current-state freshness",
            "docs/architecture/00-current-state.md is missing",
            RELEASE_BOUNDARY,
            DOCUMENTED,
        )
    match = re.search(
        r"(?im)^## Last updated\s*\n\s*(\d{4}-\d{2}-\d{2})\s*$",
        path.read_text(encoding="utf-8", errors="ignore"),
    )
    if not match:
        return CheckResult(
            WARN,
            "Current-state freshness",
            "Last updated date is missing or unparsable",
            DOCUMENTATION_DRIFT,
            DOCUMENTED,
        )
    updated = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    age_days = (date.today() - updated).days
    if age_days < 0 or age_days > max_age_days:
        return CheckResult(
            WARN,
            "Current-state freshness",
            f"current-state age is {age_days} day(s)",
            RELEASE_BOUNDARY,
            DOCUMENTED,
        )
    return CheckResult(
        PASS,
        "Current-state freshness",
        f"current-state age is {age_days} day(s)",
        EVIDENCE,
        DOCUMENTED,
    )


def release_truth_domain() -> DomainReport:
    return DomainReport(
        "Current Release Truth",
        [
            exists(
                "Current-state release truth present",
                docs("00-current-state.md"),
                missing_status=FAIL,
                finding_type=RELEASE_BOUNDARY,
                evidence_level=DOCUMENTED,
            ),
            current_state_freshness(),
            contains(
                "Supported install path is explicit",
                docs("00-current-state.md"),
                ["Local Docker Compose is the supported install path"],
                contract_check=True,
            ),
            contains(
                "Active blockers are explicit",
                docs("00-current-state.md"),
                ["Active blockers"],
                contract_check=True,
            ),
            contains(
                "Browser work is fenced from release claims",
                docs("00-current-state.md"),
                [
                    "Browser campaign",
                    "not shipped beta behavior",
                    "does not widen the default release promise",
                ],
            ),
            proof_gap(
                "Fresh main runtime proof remains separate",
                "A static scan cannot establish current supported-path runtime health.",
            ),
        ],
        "Checks the authority, freshness, supported path, blockers, and Browser release fence.",
        [
            "does current-state still match main and the supported profile?",
            "are release claims backed by fresh evidence at the claimed proof level?",
        ],
    )


def core_loop_domain() -> DomainReport:
    return DomainReport(
        "Core Loop Integrity",
        [
            exists("Chat completion route present", ["guardian/routes/chat.py"], missing_status=FAIL),
            exists("Chat worker present", ["guardian/workers/chat_worker.py"], missing_status=FAIL),
            exists("Redis queue adapter present", ["guardian/queue/redis_queue.py"], missing_status=FAIL),
            exists("Task event transport present", ["guardian/queue/task_events.py"], missing_status=FAIL),
            contains(
                "Chat route contains completion enqueue seam",
                ["guardian/routes/chat.py"],
                ["/api/chat/{thread_id}/complete", "enqueue("],
                require_all=True,
                evidence_level=STATIC,
            ),
            contains(
                "Current-state records queue coupling",
                docs("00-current-state.md"),
                ["Queue-coupled chat still requires healthy Redis"],
                contract_check=True,
            ),
            proof_gap(
                "Terminal completion and persistence require live proof",
                "Route and worker presence do not prove dequeue, terminal events, or durable assistant output.",
            ),
        ],
        "Separates static loop structure, documented queue risk, and live completion proof.",
        [
            "can crashes leave locks or duplicate turns?",
            "is Redis degradation explicit to operators and users?",
        ],
    )


def browser_host_domain() -> DomainReport:
    proofs = sorted(REPO_ROOT.glob("docs/architecture/proofs/browser-host/**/proof.json"))
    proof_check = (
        CheckResult(
            PASS,
            "Browser Host proof packets present",
            f"{len(proofs)} proof packet(s); first: {relative(proofs[0])}",
            EVIDENCE,
            TEST,
        )
        if proofs
        else CheckResult(
            WARN,
            "Browser Host proof packets present",
            "no proof.json files found under docs/architecture/proofs/browser-host",
            PROOF_GAP,
            TEST,
        )
    )
    return DomainReport(
        "Browser Host Readiness",
        [
            exists("Browser Host package present", ["browser_host/package.json"]),
            exists("Browser Host main process present", ["browser_host/src/main.js"]),
            exists("Browser Host navigation policy present", ["browser_host/src/runtime/navigation-policy.js"]),
            exists("Browser Host Guardian client present", ["browser_host/src/runtime/guardian-client.js"]),
            exists("Browser Host fixture index present", ["browser_host/contracts/fixtures/fixture-index.json"]),
            exists(
                "Browser Host Guardian contract documented",
                docs("browser-host-guardian-contract.md"),
                finding_type=DOCUMENTATION_DRIFT,
                evidence_level=DOCUMENTED,
            ),
            exists(
                "Browser Host topology ADR present",
                ["docs/architecture/adr/054-browser-host-topology-and-release-ownership.md"],
                finding_type=DOCUMENTATION_DRIFT,
                evidence_level=DOCUMENTED,
            ),
            proof_check,
            contains(
                "Browser Host remains outside supported beta",
                docs("00-current-state.md"),
                [
                    "Browser campaign",
                    "not shipped beta behavior",
                    "does not widen the default release promise",
                ],
            ),
            proof_gap(
                "Browser Host release qualification remains unproven",
                "Scaffolds and proof packets do not prove supported packaging, updates, recovery, or release ownership.",
            ),
        ],
        "Makes Browser Host a first-class domain while keeping release qualification manual and fenced.",
        [
            "does the latest proof match current contracts?",
            "are denial, consent, retention, and cleanup proven?",
            "is Browser Host still fenced from beta claims?",
        ],
    )


def platform_contracts_domain() -> DomainReport:
    return DomainReport(
        "Platform Contracts",
        [
            exists("Primary data models present", ["guardian/db/models.py"], missing_status=FAIL),
            exists("Command bus route present", ["guardian/routes/command_bus.py"], missing_status=FAIL),
            exists("Command bus contracts present", ["guardian/command_bus/contracts.py"], missing_status=FAIL),
            exists("Cron worker present", ["guardian/workers/cron_worker.py"], missing_status=FAIL),
            exists("Health route present", ["guardian/routes/health.py"], missing_status=FAIL),
            exists(
                "Runtime protocol token contract present",
                docs("runtime-protocol-token-contract.md"),
                finding_type=DOCUMENTATION_DRIFT,
                evidence_level=DOCUMENTED,
            ),
            exists(
                "Agent protocol operations index present",
                docs("agent-protocol-operations.md"),
                finding_type=DOCUMENTATION_DRIFT,
                evidence_level=DOCUMENTED,
            ),
            contains(
                "Storage docs enumerate invariants",
                docs("data-and-storage.md"),
                ["Key Entities and Collections", "Hard invariants"],
                require_all=True,
            ),
            contains(
                "Ownership docs enumerate subsystem seams",
                docs("modules-and-ownership.md"),
                ["Subsystem Matrix", "Ownership Guidance"],
                require_all=True,
            ),
            proof_gap(
                "Operator truth requires live surface agreement",
                "Static health, catalog, queue, worker, and supported-profile surfaces must agree at runtime.",
            ),
        ],
        "Checks current contracts and ownership seams without using wording drift as a runtime warning.",
        [
            "are governance rules enforced where enforcement matters?",
            "can failed work replay without duplicate effects?",
            "does restart preserve diagnostic traceability?",
        ],
    )


def build_reports() -> list[DomainReport]:
    return [
        release_truth_domain(),
        core_loop_domain(),
        browser_host_domain(),
        platform_contracts_domain(),
    ]


def collect_repo_metadata() -> dict[str, object]:
    branch = head = error = ""
    status_lines: list[str] = []
    try:
        branch = run_git(["branch", "--show-current"]).strip()
        head = run_git(["rev-parse", "HEAD"]).strip()
        status_lines = [
            line
            for line in run_git(["status", "--short", "--untracked-files=all"]).splitlines()
            if line.strip()
        ]
    except RuntimeError as exc:
        error = str(exc)
    return {
        "branch": branch or (f"detached@{head[:7]}" if head else ""),
        "head": head,
        "dirty": bool(status_lines) if not error else None,
        "status_lines": status_lines,
        "status_error": error,
    }


def build_payload(reports: list[DomainReport]) -> dict[str, object]:
    checks = [(report, check) for report in reports for check in report.checks]
    summary = {
        "pass": sum(check.status == PASS for _, check in checks),
        "warn": sum(check.status == WARN for _, check in checks),
        "fail": sum(check.status == FAIL for _, check in checks),
        "info": sum(check.status == INFO for _, check in checks),
    }
    finding_counts: dict[str, int] = {}
    for _, check in checks:
        finding_counts[check.finding_type] = finding_counts.get(check.finding_type, 0) + 1

    def findings(status: str) -> list[dict[str, str]]:
        return [
            {
                "domain": report.name,
                "label": check.label,
                "evidence": check.evidence,
                "finding_type": check.finding_type,
                "evidence_level": check.evidence_level,
            }
            for report, check in checks
            if check.status == status
        ]

    return {
        "mode": "json",
        "audit_version": 2,
        "repo_root_relative": ".",
        "repo": collect_repo_metadata(),
        "summary": summary,
        "finding_counts": dict(sorted(finding_counts.items())),
        "domains": [
            {
                "name": report.name,
                "summary": report.summary,
                "manual_prompts": report.manual_prompts,
                "checks": [asdict(check) for check in report.checks],
                "pass_count": report.count(PASS),
                "warn_count": report.count(WARN),
                "fail_count": report.count(FAIL),
                "info_count": report.count(INFO),
            }
            for report in reports
        ],
        "warnings": findings(WARN),
        "failures": findings(FAIL),
        "informational": findings(INFO),
    }


def render_text(reports: list[DomainReport]) -> None:
    payload = build_payload(reports)
    print("Codexify Platform Readiness Audit v2")
    print("Evidence-classified repo scan")
    print()
    for report in reports:
        print("=" * 80)
        print(report.name)
        for check in report.checks:
            print(
                f"  [{check.status}][{check.finding_type}][{check.evidence_level}] "
                f"{check.label}: {check.evidence}"
            )
        print(f"Evidence summary:\n  {report.summary}")
        for prompt in report.manual_prompts:
            print(f"  - Manual review required: {prompt}")
        print()
    print("=" * 80)
    print("Final Summary")
    print(json.dumps(payload["summary"], sort_keys=True))
    print(f"Finding classes: {json.dumps(payload['finding_counts'], sort_keys=True)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the evidence-classified Codexify audit.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reports = build_reports()
    if args.json:
        print(json.dumps(build_payload(reports), indent=2, sort_keys=True))
    else:
        render_text(reports)
    return 1 if any(check.status == FAIL for report in reports for check in report.checks) else 0


if __name__ == "__main__":
    sys.exit(main())
