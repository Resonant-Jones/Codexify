from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    status: str
    label: str
    evidence: str


@dataclass
class DomainReport:
    name: str
    checks: list[CheckResult]
    summary: str
    manual_prompts: list[str]
    suggested_score: str

    def count(self, status: str) -> int:
        return sum(1 for check in self.checks if check.status == status)


def doc_candidates(name: str) -> tuple[str, ...]:
    return (f"docs/architecture/{name}", f"docs/{name}", name)


def relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def existing_path(candidates: tuple[str, ...] | list[str]) -> Path | None:
    for candidate in candidates:
        path = REPO_ROOT / candidate
        if path.exists():
            return path
    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def contains_patterns(
    candidates: tuple[str, ...] | list[str],
    patterns: tuple[str, ...] | list[str],
    *,
    require_all: bool,
) -> tuple[Path, list[str]] | None:
    lowered = [pattern.lower() for pattern in patterns]
    for candidate in candidates:
        path = REPO_ROOT / candidate
        if not path.exists():
            continue
        text = read_text(path).lower()
        matched = [
            pattern
            for pattern, lowered_pattern in zip(patterns, lowered)
            if lowered_pattern in text
        ]
        if require_all and len(matched) == len(patterns):
            return path, matched
        if not require_all and matched:
            return path, matched
    return None


def render_candidate_list(candidates: tuple[str, ...] | list[str]) -> str:
    return ", ".join(str(candidate) for candidate in candidates)


def check_exists(
    label: str,
    candidates: tuple[str, ...] | list[str],
    *,
    missing_status: str,
) -> CheckResult:
    path = existing_path(candidates)
    if path is not None:
        return CheckResult("PASS", label, f"{relative_path(path)} exists")
    return CheckResult(
        missing_status,
        label,
        f"missing expected path(s): {render_candidate_list(candidates)}",
    )


def check_contains(
    label: str,
    candidates: tuple[str, ...] | list[str],
    patterns: tuple[str, ...] | list[str],
    *,
    require_all: bool,
    missing_status: str,
) -> CheckResult:
    matched = contains_patterns(candidates, patterns, require_all=require_all)
    if matched is not None:
        path, found_patterns = matched
        detail = ", ".join(repr(pattern) for pattern in found_patterns[:3])
        return CheckResult(
            "PASS",
            label,
            f"{relative_path(path)} matches {detail}",
        )

    path = existing_path(candidates)
    if path is not None:
        return CheckResult(
            missing_status,
            label,
            f"{relative_path(path)} did not match expected text: {', '.join(repr(pattern) for pattern in patterns)}",
        )

    return CheckResult(
        "FAIL" if missing_status == "FAIL" else missing_status,
        label,
        f"missing expected path(s): {render_candidate_list(candidates)}",
    )


def warning_if_contains(
    label: str,
    candidates: tuple[str, ...] | list[str],
    patterns: tuple[str, ...] | list[str],
) -> CheckResult | None:
    matched = contains_patterns(candidates, patterns, require_all=False)
    if matched is None:
        return None

    path, found_patterns = matched
    return CheckResult(
        "WARN",
        label,
        f"{relative_path(path)} contains {repr(found_patterns[0])}",
    )


def suggest_score(name: str, checks: list[CheckResult]) -> str:
    pass_count = sum(1 for check in checks if check.status == "PASS")
    warn_count = sum(1 for check in checks if check.status == "WARN")
    fail_count = sum(1 for check in checks if check.status == "FAIL")

    if fail_count:
        return "0-1 likely"

    if name == "Federation Readiness":
        if warn_count >= 2:
            return "0-1 likely"
        if pass_count >= 4:
            return "1-2 likely"
        return "manual review required"

    if name in {"Alternate Surface Readiness", "Governance Readiness"}:
        if pass_count >= 3:
            return "manual review required"
        return "0-1 likely"

    if pass_count >= 5 and warn_count == 0:
        return "2 likely"
    if pass_count >= 4:
        return "1-2 likely"
    return "manual review required"


def make_domain(
    name: str,
    checks: list[CheckResult],
    summary: str,
    manual_prompts: list[str],
) -> DomainReport:
    return DomainReport(
        name=name,
        checks=checks,
        summary=summary,
        manual_prompts=manual_prompts,
        suggested_score=suggest_score(name, checks),
    )


def score_rank(label: str) -> int:
    ranks = {
        "2 likely": 3,
        "1-2 likely": 2,
        "manual review required": 1,
        "0-1 likely": 0,
    }
    return ranks.get(label, 0)


def build_core_loop_integrity() -> DomainReport:
    checks = [
        check_exists(
            "Chat completion route present",
            ["guardian/routes/chat.py"],
            missing_status="FAIL",
        ),
        check_contains(
            "Chat route exposes async completion enqueue path",
            ["guardian/routes/chat.py"],
            ["/api/chat/{thread_id}/complete", "enqueue("],
            require_all=True,
            missing_status="WARN",
        ),
        check_exists(
            "Chat worker present",
            ["guardian/workers/chat_worker.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Redis queue adapter present",
            ["guardian/queue/redis_queue.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Task event transport present",
            ["guardian/queue/task_events.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Completion pipeline documentation present",
            doc_candidates("completion_pipeline.md"),
            missing_status="WARN",
        ),
    ]
    warning = warning_if_contains(
        "Architecture docs still flag chat-loop dependency coupling",
        [
            *doc_candidates("tech-debt-and-risks.md"),
            *doc_candidates("roadmap-signals.md"),
        ],
        [
            "Chat completion availability is tightly coupled to Redis queue health",
            "The primary chat loop is queue-coupled.",
        ],
    )
    if warning is not None:
        checks.append(warning)

    return make_domain(
        "Core Loop Integrity",
        checks,
        "Chat route, worker, queue, task-event, and completion-pipeline anchors are all present. The repo also explicitly records Redis and worker coupling as an operational risk, so restart and degraded-mode behavior still need human validation.",
        [
            "does provider-output validation reliably reject malformed responses before persistence?",
            "can worker crashes or restarts leave threads locked or duplicate turns in edge cases?",
            "is degraded behavior for Redis outage explicit to operators and end users?",
        ],
    )


def build_primitive_stability() -> DomainReport:
    checks = [
        check_exists(
            "Primary data models present",
            ["guardian/db/models.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Data and storage documentation present",
            doc_candidates("data-and-storage.md"),
            missing_status="WARN",
        ),
        check_exists(
            "Modules and ownership documentation present",
            doc_candidates("modules-and-ownership.md"),
            missing_status="WARN",
        ),
        check_contains(
            "Data and storage docs enumerate entities and invariants",
            doc_candidates("data-and-storage.md"),
            ["Key Entities and Collections", "Hard invariants"],
            require_all=True,
            missing_status="WARN",
        ),
        check_contains(
            "Modules docs describe subsystem ownership seams",
            doc_candidates("modules-and-ownership.md"),
            ["Subsystem Matrix", "Ownership Guidance"],
            require_all=True,
            missing_status="WARN",
        ),
    ]
    warning = warning_if_contains(
        "Repo-local docs warn about contract drift in tool primitives",
        [
            *doc_candidates("tech-debt-and-risks.md"),
            *doc_candidates("roadmap-signals.md"),
        ],
        [
            "Legacy `/tools` behavior and command bus behavior coexist",
            "tool execution unification",
        ],
    )
    if warning is not None:
        checks.append(warning)

    return make_domain(
        "Primitive Stability",
        checks,
        "The repo has a central models file plus current docs for entities, invariants, subsystem seams, and ownership guidance. Contract-drift warnings around legacy tools versus the command bus suggest at least one primitive family is still in transition.",
        [
            "are lifecycle transitions for threads, documents, jobs, and events stable across migrations and releases?",
            "do schema changes preserve backward compatibility for existing API and worker flows?",
            "are ownership and identity constraints enforced consistently in code, not just described in docs?",
        ],
    )


def build_extension_boundary() -> DomainReport:
    legacy_tools_patterns = (
        "legacy `/tools` compatibility shim",
        "legacy tools shim",
        "compatibility shim",
    )
    legacy_tools_docs = [
        *doc_candidates("system-overview.md"),
        *doc_candidates("flows.md"),
        *doc_candidates("modules-and-ownership.md"),
        *doc_candidates("tech-debt-and-risks.md"),
        *doc_candidates("legacy-tools-shim-inventory.md"),
    ]
    checks = [
        check_exists(
            "Command bus route present",
            ["guardian/routes/command_bus.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Command bus contracts present",
            ["guardian/command_bus/contracts.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Cron route present",
            ["guardian/routes/cron.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Cron worker present",
            ["guardian/workers/cron_worker.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Guardian intent spine route present",
            ["guardian/routes/agent_orchestration.py"],
            missing_status="WARN",
        ),
        check_exists(
            "Agent orchestration persistence seams present",
            ["guardian/agents/store.py", "guardian/agents/events.py"],
            missing_status="WARN",
        ),
        check_exists(
            "Guardian-mediated coding worker seam present",
            ["guardian/workers/coding_worker.py"],
            missing_status="WARN",
        ),
        check_contains(
            "Architecture docs describe command bus, cron, and coding-agent seams",
            [
                *doc_candidates("system-overview.md"),
                *doc_candidates("flows.md"),
                *doc_candidates("00-current-state.md"),
            ],
            [
                "command bus",
                "Cron and job execution",
                "Coding results now return through Guardian",
            ],
            require_all=True,
            missing_status="WARN",
        ),
    ]
    legacy_tools_route = existing_path(["guardian/routes/tools.py"])
    legacy_tools_mention = contains_patterns(
        legacy_tools_docs,
        legacy_tools_patterns,
        require_all=False,
    )
    if legacy_tools_route is not None:
        checks.append(
            CheckResult(
                "PASS",
                "Legacy /tools compatibility route status",
                f"{relative_path(legacy_tools_route)} exists as compatibility surface",
            )
        )
    elif legacy_tools_mention is not None:
        mention_path, matched_patterns = legacy_tools_mention
        checks.append(
            CheckResult(
                "WARN",
                "Legacy /tools compatibility route status",
                f"{relative_path(mention_path)} references {repr(matched_patterns[0])}; route is absent and should remain compatibility-only if reintroduced",
            )
        )
    else:
        checks.append(
            CheckResult(
                "PASS",
                "Legacy /tools compatibility route status",
                "guardian/routes/tools.py is absent and not required by current architecture docs",
            )
        )

    return make_domain(
        "Extension Boundary",
        checks,
        "Command bus, cron execution, Guardian intent-orchestration seams, and the Guardian-mediated coding result path provide the current extension boundary evidence. This remains a cautionary domain because extension governance and cross-surface maturity still require manual review.",
        [
            "does the extension boundary allow new workflows without kernel edits?",
            "can new automation paths continue to prefer durable command-bus and cron lanes over ad hoc process-local behavior?",
            "do Guardian intent-spine and coding-agent return-path seams stay policy-governed across chat, automation, and future plugin entrypoints?",
            "is self-extending plugin governance explicit enough to prevent capability drift at install and runtime binding boundaries?",
        ],
    )


def build_observability() -> DomainReport:
    checks = [
        check_exists(
            "Health route present",
            ["guardian/routes/health.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Config and ops documentation present",
            doc_candidates("config-and-ops.md"),
            missing_status="WARN",
        ),
        check_contains(
            "Config and ops docs enumerate health and metrics surfaces",
            doc_candidates("config-and-ops.md"),
            ["GET /health", "GET /metrics", "GET /api/tasks/{task_id}/events"],
            require_all=True,
            missing_status="WARN",
        ),
        check_exists(
            "Task event transport present",
            ["guardian/queue/task_events.py"],
            missing_status="FAIL",
        ),
        check_contains(
            "Sync API exposes a health endpoint",
            ["guardian/sync/api.py"],
            ["/health/sync"],
            require_all=False,
            missing_status="WARN",
        ),
    ]
    warning = warning_if_contains(
        "Observability docs leave some logging guarantees unverified",
        doc_candidates("config-and-ops.md"),
        [
            "Structured JSON logger setup is `Unverified`",
            "Live UI events stop after restart",
        ],
    )
    if warning is not None:
        checks.append(warning)

    return make_domain(
        "Observability",
        checks,
        "Repo-local evidence shows explicit health endpoints, task-event streaming, metrics, and sync health reporting. The docs still label parts of the logging and event-delivery story as unverified or restart-sensitive, so incident-debug depth needs manual confirmation.",
        [
            "do logs include enough request, task, and identity context to debug failures without reproducing them locally?",
            "are queue depth, worker liveness, and dependency health observable enough for operational triage?",
            "do restart scenarios preserve enough traceability across task events, outbox events, and sync subscribers?",
        ],
    )


def build_durability_and_recovery() -> DomainReport:
    checks = [
        check_exists(
            "Primary data models present",
            ["guardian/db/models.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Redis queue adapter present",
            ["guardian/queue/redis_queue.py"],
            missing_status="FAIL",
        ),
        check_contains(
            "Data docs define Postgres as source of truth and queue-backed execution",
            doc_candidates("data-and-storage.md"),
            ["Postgres is the source of truth", "queue-backed"],
            require_all=True,
            missing_status="WARN",
        ),
        check_contains(
            "Models include durable run and idempotency anchors",
            ["guardian/db/models.py"],
            ['__tablename__ = "cron_runs"', "uq_command_idempotency_key"],
            require_all=True,
            missing_status="WARN",
        ),
        check_contains(
            "Sync API acknowledges idempotent event ingestion",
            ["guardian/sync/api.py"],
            ["idempotent upsert", '"idempotent": not is_new'],
            require_all=True,
            missing_status="WARN",
        ),
    ]
    warning_one = warning_if_contains(
        "Roadmap docs warn that sync delivery is not yet durable",
        [
            *doc_candidates("roadmap-signals.md"),
            *doc_candidates("tech-debt-and-risks.md"),
        ],
        [
            "Durable sync path:",
            "Sync subscriptions are process-local",
        ],
    )
    if warning_one is not None:
        checks.append(warning_one)
    warning_two = warning_if_contains(
        "Risk register warns about Redis persistence or replay gaps",
        [
            *doc_candidates("tech-debt-and-risks.md"),
            *doc_candidates("roadmap-signals.md"),
        ],
        [
            "Redis in Compose is configured without durable persistence",
            "retry/replay ergonomics are weak",
        ],
    )
    if warning_two is not None:
        checks.append(warning_two)

    return make_domain(
        "Durability & Recovery",
        checks,
        "The repo contains durable Postgres models, queue-backed execution, and explicit idempotency anchors for some run types. At the same time, repo-local docs warn about non-durable sync delivery, Redis persistence limits in Compose, and incomplete replay ergonomics.",
        [
            "are degraded modes explicit for Redis outage?",
            "can failed chat, ingestion, and cron work be replayed without duplicate side effects?",
            "are restart, retry, and dead-letter expectations documented strongly enough for operators to recover safely?",
        ],
    )


def build_alternate_surface_readiness() -> DomainReport:
    checks = [
        check_exists(
            "System overview documentation present",
            doc_candidates("system-overview.md"),
            missing_status="WARN",
        ),
        check_contains(
            "System overview documents multiple client surfaces",
            doc_candidates("system-overview.md"),
            ["React frontend", "Desktop shell"],
            require_all=True,
            missing_status="WARN",
        ),
        check_contains(
            "System overview describes a frontend API/runtime layer",
            doc_candidates("system-overview.md"),
            ["Frontend API/runtime layer"],
            require_all=False,
            missing_status="WARN",
        ),
        check_contains(
            "Config and ops docs record desktop/runtime overrides",
            doc_candidates("config-and-ops.md"),
            ["desktop backend/share envs", "browser-stored overrides"],
            require_all=True,
            missing_status="WARN",
        ),
        check_exists(
            "Chat API route present",
            ["guardian/routes/chat.py"],
            missing_status="FAIL",
        ),
    ]
    warning = warning_if_contains(
        "Repo-local docs still describe shell-level coupling",
        [
            *doc_candidates("roadmap-signals.md"),
            *doc_candidates("tech-debt-and-risks.md"),
        ],
        [
            "Frontend routing and shell orchestration are mostly hand-rolled",
            "Browser-side state is spread across manual pathname logic",
        ],
    )
    if warning is not None:
        checks.append(warning)

    return make_domain(
        "Alternate Surface Readiness",
        checks,
        "Codexify clearly serves at least web and desktop surfaces through shared backend APIs, and the docs describe runtime overrides for those clients. The scanned evidence does not prove that headless, mobile, or automation clients are first-class enough to justify a machine-suggested score without human review.",
        [
            "do non-web clients use the same auth, event, and workflow contracts as the web UI without special-case backend logic?",
            "can CLI, voice, or agent surfaces complete the core loop without relying on browser-only state assumptions?",
            "are surface-specific UX choices cleanly separated from core service behavior?",
        ],
    )


def build_federation_readiness() -> DomainReport:
    checks = [
        check_exists(
            "Federation route present",
            ["guardian/routes/federation.py"],
            missing_status="FAIL",
        ),
        check_exists(
            "Sync API present", ["guardian/sync/api.py"], missing_status="FAIL"
        ),
        check_contains(
            "Federation route includes trust-policy and version anchors",
            ["guardian/routes/federation.py"],
            ["trust policy", "base_version"],
            require_all=True,
            missing_status="WARN",
        ),
        check_contains(
            "Architecture docs describe federation and sync flow",
            [
                *doc_candidates("system-overview.md"),
                *doc_candidates("flows.md"),
                *doc_candidates("config-and-ops.md"),
            ],
            ["federation", "sync"],
            require_all=True,
            missing_status="WARN",
        ),
    ]
    warning_one = warning_if_contains(
        "Roadmap docs warn that sync subscriptions are process-local",
        [
            *doc_candidates("roadmap-signals.md"),
            *doc_candidates("tech-debt-and-risks.md"),
            *doc_candidates("flows.md"),
        ],
        [
            "process-local SSE subscription bus",
            "Sync subscriptions are process-local",
            "process restart because the bus is process-local",
        ],
    )
    if warning_one is not None:
        checks.append(warning_one)
    warning_two = warning_if_contains(
        "Risk register warns that federation remains security- and config-sensitive",
        [
            *doc_candidates("tech-debt-and-risks.md"),
            *doc_candidates("roadmap-signals.md"),
        ],
        [
            "Federation is security- and config-sensitive",
            "Federation remains a high-blast-radius area",
        ],
    )
    if warning_two is not None:
        checks.append(warning_two)

    return make_domain(
        "Federation Readiness",
        checks,
        "Federation routes, trust-policy checks, sync endpoints, and version-aware diff handling exist in the repo. The same repo-local evidence also says sync delivery is process-local and federation is still a high-blast-radius, config-sensitive area, so the likely band remains low.",
        [
            "can peers verify identity, rotation, revocation, and trust-policy changes safely over time?",
            "are conflict resolution and replay semantics strong enough under partitions or restart gaps?",
            "are degraded federation modes explicit when relays, trust policy, or egress checks fail?",
        ],
    )


def build_governance_readiness() -> DomainReport:
    checks = [
        check_exists(
            "Modules and ownership documentation present",
            doc_candidates("modules-and-ownership.md"),
            missing_status="WARN",
        ),
        check_exists(
            "Roadmap signals documentation present",
            doc_candidates("roadmap-signals.md"),
            missing_status="WARN",
        ),
        check_exists(
            "Tech debt and risks documentation present",
            doc_candidates("tech-debt-and-risks.md"),
            missing_status="WARN",
        ),
        check_exists(
            "IDDB policy documentation present",
            ["docs/iddb_policy_v1.md", "iddb_policy_v1.md"],
            missing_status="WARN",
        ),
        check_contains(
            "Data docs describe hard invariants and explicit access boundaries",
            doc_candidates("data-and-storage.md"),
            ["Hard invariants", "explicit, not ambient"],
            require_all=True,
            missing_status="WARN",
        ),
        check_contains(
            "System overview states that enforcement lives in code and policy layers",
            doc_candidates("system-overview.md"),
            ["enforcement is in route/auth/policy code, not in prompts"],
            require_all=False,
            missing_status="WARN",
        ),
    ]
    warning = warning_if_contains(
        "Ownership authority is still informal in the scanned docs",
        doc_candidates("modules-and-ownership.md"),
        ["This repo does not declare formal team ownership in code"],
    )
    if warning is not None:
        checks.append(warning)

    return make_domain(
        "Governance Readiness",
        checks,
        "The repo has a current ownership map, risk register, roadmap signal doc, identity policy, and documented hard invariants. Those are solid governance inputs, but the scanned evidence still leaves extension authority and enforcement coverage too cross-cutting for a truthful machine score.",
        [
            "are governance invariants documented and enforced?",
            "is extension authority explicit enough to prevent accidental policy or boundary regressions?",
            "are versioning, migration, and compatibility expectations strong enough to support rolling architectural change?",
        ],
    )


def build_reports() -> list[DomainReport]:
    return [
        build_core_loop_integrity(),
        build_primitive_stability(),
        build_extension_boundary(),
        build_observability(),
        build_durability_and_recovery(),
        build_alternate_surface_readiness(),
        build_federation_readiness(),
        build_governance_readiness(),
    ]


def strongest_domains(reports: list[DomainReport]) -> list[str]:
    ranked = sorted(
        reports,
        key=lambda report: (
            score_rank(report.suggested_score),
            report.count("PASS"),
            -report.count("WARN"),
            -report.count("FAIL"),
        ),
        reverse=True,
    )
    return [report.name for report in ranked[:3] if report.count("PASS") > 0]


def weakest_domains(reports: list[DomainReport]) -> list[str]:
    ranked = sorted(
        reports,
        key=lambda report: (
            report.count("FAIL"),
            3 - score_rank(report.suggested_score),
            report.count("WARN"),
            -report.count("PASS"),
        ),
        reverse=True,
    )
    return [
        report.name
        for report in ranked[:3]
        if report.count("WARN") or report.count("FAIL")
    ]


def build_summary(reports: list[DomainReport]) -> dict[str, object]:
    return {
        "pass": sum(report.count("PASS") for report in reports),
        "warn": sum(report.count("WARN") for report in reports),
        "fail": sum(report.count("FAIL") for report in reports),
    }


def report_to_dict(report: DomainReport) -> dict[str, object]:
    return {
        "name": report.name,
        "suggested_score": report.suggested_score,
        "summary": report.summary,
        "manual_prompts": report.manual_prompts,
        "checks": [
            {
                "status": check.status,
                "label": check.label,
                "evidence": check.evidence,
            }
            for check in report.checks
        ],
        "pass_count": report.count("PASS"),
        "warn_count": report.count("WARN"),
        "fail_count": report.count("FAIL"),
    }


def collect_repo_metadata() -> dict[str, object]:
    branch = ""
    head = ""
    status_lines: list[str] = []
    status_error = ""

    try:
        branch = run_git(["branch", "--show-current"]).strip()
        head = run_git(["rev-parse", "HEAD"]).strip()
    except RuntimeError as exc:
        status_error = str(exc)

    if not branch and head:
        branch = f"detached@{head[:7]}"

    try:
        status_output = run_git(["status", "--short", "--untracked-files=all"])
        status_lines = [
            line.rstrip() for line in status_output.splitlines() if line.strip()
        ]
    except RuntimeError as exc:
        if not status_error:
            status_error = str(exc)
    return {
        "branch": branch,
        "head": head,
        "dirty": bool(status_lines) if status_error == "" else None,
        "status_lines": status_lines,
        "status_error": status_error,
    }


def build_json_payload(reports: list[DomainReport]) -> dict[str, object]:
    warnings = [
        {
            "domain": report.name,
            "label": check.label,
            "evidence": check.evidence,
        }
        for report in reports
        for check in report.checks
        if check.status == "WARN"
    ]
    failures = [
        {
            "domain": report.name,
            "label": check.label,
            "evidence": check.evidence,
        }
        for report in reports
        for check in report.checks
        if check.status == "FAIL"
    ]

    return {
        "mode": "json",
        "repo_root_relative": ".",
        "repo": collect_repo_metadata(),
        "summary": build_summary(reports),
        "strongest_domains": strongest_domains(reports),
        "weakest_domains": weakest_domains(reports),
        "domains": [report_to_dict(report) for report in reports],
        "warnings": warnings,
        "failures": failures,
    }


def render_report(reports: list[DomainReport]) -> None:
    summary = build_summary(reports)

    print("Codexify Platform Readiness Audit")
    print("Repo-local evidence pass")
    print(f"Repo root: {REPO_ROOT}")
    print()

    for report in reports:
        print("=" * 80)
        print(report.name)
        print(f"Suggested score band: {report.suggested_score}")
        print("Automatic evidence checks:")
        for check in report.checks:
            print(f"  [{check.status}] {check.label}: {check.evidence}")
        print("Evidence summary:")
        print(f"  {report.summary}")
        print("Manual review prompts:")
        for prompt in report.manual_prompts:
            print(f"  - Manual review required: {prompt}")
        print()

    print("=" * 80)
    print("Final Summary")
    print(f"  PASS: {summary['pass']}")
    print(f"  WARN: {summary['warn']}")
    print(f"  FAIL: {summary['fail']}")
    print(
        "  Domains needing manual review: "
        "Alternate Surface Readiness and Governance Readiness remain fully manual; "
        "all other domains still include targeted review prompts."
    )
    print(
        f"  Strongest objective evidence: {', '.join(strongest_domains(reports)) or 'none'}"
    )
    print(
        f"  Clearest structural weakness signals: {', '.join(weakest_domains(reports)) or 'none'}"
    )


def render_json_report(reports: list[DomainReport]) -> None:
    print(json.dumps(build_json_payload(reports), indent=2, sort_keys=True))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Codexify platform readiness audit."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reports = build_reports()
    if args.json:
        render_json_report(reports)
    else:
        render_report(reports)
    return (
        1
        if any(
            check.status == "FAIL"
            for report in reports
            for check in report.checks
        )
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
