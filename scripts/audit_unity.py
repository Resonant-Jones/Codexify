from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "audits" / "unity"
DEFAULT_JSON_PATH = DEFAULT_OUTPUT_DIR / "latest.json"
DEFAULT_MARKDOWN_PATH = DEFAULT_OUTPUT_DIR / "latest.md"
STATUS_ORDER = ("PASS", "WARN", "FAIL", "UNKNOWN")


@dataclass(frozen=True)
class RepoState:
    branch: str
    head: str
    dirty: bool | str


@dataclass(frozen=True)
class LensReport:
    name: str
    status: str
    summary: str
    evidence: list[str]
    warnings: list[str]
    manual_review_prompts: list[str]


def relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def path_exists(*parts: str) -> Path | None:
    path = repo_path(*parts)
    return path if path.exists() else None


def contains_any(text: str, patterns: list[str] | tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def add_evidence(evidence: list[str], path: Path, note: str) -> None:
    evidence.append(f"{relative_path(path)}: {note}")


def add_missing_warning(warnings: list[str], path_text: str, note: str) -> None:
    warnings.append(f"{path_text}: {note}")


def determine_status(
    required_ok: bool, warnings: list[str], evidence: list[str]
) -> str:
    if not required_ok:
        return "FAIL"
    if warnings:
        return "WARN"
    if evidence:
        return "PASS"
    return "UNKNOWN"


def git_output(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def get_repo_state() -> RepoState:
    branch = (
        git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    )
    head = git_output(["git", "rev-parse", "HEAD"]) or "unknown"
    dirty_output = git_output(["git", "status", "--porcelain"])
    dirty: bool | str
    if dirty_output is None:
        dirty = "unknown"
    else:
        dirty = bool(dirty_output)
    return RepoState(branch=branch, head=head, dirty=dirty)


def build_runtime_truth() -> LensReport:
    evidence: list[str] = []
    warnings: list[str] = []
    current_state = path_exists("docs", "architecture", "00-current-state.md")
    latest_json = path_exists("docs", "audits", "latest.json")
    latest_md = path_exists("docs", "audits", "latest.md")

    required_ok = current_state is not None
    if current_state is not None:
        text = read_text(current_state)
        add_evidence(
            evidence,
            current_state,
            "current-state release truth anchor present",
        )
        if contains_any(
            text,
            [
                "fresh live evidence exists",
                "live runtime proof",
                "proof-driven",
            ],
        ):
            add_evidence(
                evidence,
                current_state,
                "explicitly distinguishes live evidence and runtime proof from broader architecture docs",
            )
        if contains_any(
            text,
            [
                "runtime proof must be refreshed",
                "live runtime proof remains required",
                "doctrine-first unity audit framing",
            ],
        ):
            warnings.append(
                "docs/architecture/00-current-state.md warns that live runtime proof still requires refresh and that Unity Audit is a coherence lens only."
            )
    else:
        add_missing_warning(
            warnings,
            "docs/architecture/00-current-state.md",
            "required current-state truth anchor is missing",
        )

    if latest_json is not None:
        add_evidence(
            evidence,
            latest_json,
            "repo-local latest audit JSON artifact present",
        )
    if latest_md is not None:
        add_evidence(
            evidence,
            latest_md,
            "repo-local latest audit Markdown artifact present",
        )
    if latest_json is None and latest_md is None:
        warnings.append(
            "docs/audits/latest.json and docs/audits/latest.md are both absent, so no latest repo-local audit artifact was available to cross-check runtime truth cues."
        )

    summary = "Checks whether current-state release truth and repo-local audit artifacts exist, while preserving the rule that document presence is not live proof."
    manual_prompts = [
        "Which supported-path live proof artifact is the freshness anchor for the current main tip?",
        "Do current health surfaces and worker proofs still match the claims in 00-current-state.md?",
        "If runtime behavior drifted recently, has current-state been refreshed before using this audit for release confidence?",
    ]
    return LensReport(
        name="Runtime Truth",
        status=determine_status(required_ok, warnings, evidence),
        summary=summary,
        evidence=evidence,
        warnings=warnings,
        manual_review_prompts=manual_prompts,
    )


def build_contract_integrity() -> LensReport:
    evidence: list[str] = []
    warnings: list[str] = []
    required_files = [
        (
            "docs/architecture/chat-runtime-contract.md",
            "chat runtime contract present",
        ),
        (
            "docs/architecture/runtime-protocol-token-contract.md",
            "runtime protocol token contract present",
        ),
        (
            "docs/architecture/account-export-restore-contract.md",
            "account export and restore contract present",
        ),
        (
            "docs/architecture/canonical-token-philosophy.md",
            "canonical token philosophy present",
        ),
    ]

    required_ok = True
    for relative, note in required_files:
        path = REPO_ROOT / relative
        if path.exists():
            add_evidence(evidence, path, note)
        else:
            required_ok = False
            add_missing_warning(
                warnings, relative, "required contract file is missing"
            )

    token_contract = path_exists(
        "docs", "architecture", "runtime-protocol-token-contract.md"
    )
    if token_contract is not None:
        text = read_text(token_contract)
        if contains_any(
            text, ["do not by themselves prove", "must be verified"]
        ):
            warnings.append(
                "docs/architecture/runtime-protocol-token-contract.md says canonical tokens are shared vocabulary, not proof that every state is emitted end-to-end."
            )
    else:
        warnings.append(
            "Runtime Protocol Token Contract could not be inspected for interpretation caveats."
        )

    summary = "Checks that the core contract corpus exists and that canonical runtime vocabulary is explicitly separated from implementation proof."
    manual_prompts = [
        "Do provider state, request state, and message-versus-attempt identity still match the live runtime and shared frontend surfaces?",
        "Are export and restore lineage guarantees enforced in code for the currently supported artifact families?",
        "Have any newer docs or routes started using ad hoc runtime literals outside the canonical token lane?",
    ]
    return LensReport(
        name="Contract Integrity",
        status=determine_status(required_ok, warnings, evidence),
        summary=summary,
        evidence=evidence,
        warnings=warnings,
        manual_review_prompts=manual_prompts,
    )


def build_surface_coherence() -> LensReport:
    evidence: list[str] = []
    warnings: list[str] = []
    required_paths = [
        ("docs/architecture/system-overview.md", "system overview present"),
        (
            "docs/architecture/runtime-diagrams-v1.md",
            "runtime diagrams present",
        ),
        ("docs/architecture/ui-diagrams-v1.md", "UI diagrams present"),
        (
            "docs/architecture/codexify_workspace_surface_spec_v_1.md",
            "workspace surface spec present",
        ),
    ]

    required_ok = True
    for relative, note in required_paths:
        path = REPO_ROOT / relative
        if path.exists():
            add_evidence(evidence, path, note)
        else:
            required_ok = False
            add_missing_warning(
                warnings, relative, "required surface document is missing"
            )

    diagram_governance = path_exists(
        "docs", "architecture", "diagram-governance.md"
    )
    if diagram_governance is not None:
        text = read_text(diagram_governance)
        add_evidence(
            evidence,
            diagram_governance,
            "diagram governance and freshness workflow present",
        )
        if contains_any(
            text, ["diagram review marker", "review-marker", "warns by default"]
        ):
            warnings.append(
                "docs/architecture/diagram-governance.md defines separate review-marker freshness checks; this scaffold does not run those freshness validations."
            )

    kb_matrix = path_exists("docs", "architecture", "kb-validity-matrix.md")
    if kb_matrix is not None:
        text = read_text(kb_matrix)
        if contains_any(
            text,
            [
                "quarantined from first-pass diagramming",
                "supplementary_verify_against_code",
            ],
        ):
            warnings.append(
                "docs/architecture/kb-validity-matrix.md warns that some supporting docs are supplementary or quarantined, so cross-surface alignment still requires human judgment."
            )

    summary = "Checks that the major overview, diagram, and workspace-surface documents exist, while surfacing that diagram freshness and validity are governed separately."
    manual_prompts = [
        "Do the runtime and UI diagram packs still match the supported path after recent shell and runtime-state changes?",
        "Does the workspace surface spec stay clearly separated from runtime/operator truth in surrounding docs?",
        "If a contributor started from the README, would they reach the right authoritative surface before reading diagrams?",
    ]
    return LensReport(
        name="Surface Coherence",
        status=determine_status(required_ok, warnings, evidence),
        summary=summary,
        evidence=evidence,
        warnings=warnings,
        manual_review_prompts=manual_prompts,
    )


def build_governance_integrity() -> LensReport:
    evidence: list[str] = []
    warnings: list[str] = []
    required_paths = [
        (
            "docs/architecture/agent-protocol-operations.md",
            "agent protocol operations index present",
        ),
        (
            "docs/architecture/kb-validity-matrix.md",
            "KB validity matrix present",
        ),
        (
            "docs/architecture/tech-debt-and-risks.md",
            "tech debt and risks register present",
        ),
    ]

    required_ok = True
    for relative, note in required_paths:
        path = REPO_ROOT / relative
        if path.exists():
            add_evidence(evidence, path, note)
        else:
            required_ok = False
            add_missing_warning(
                warnings, relative, "required governance document is missing"
            )

    iddb_policy = path_exists("docs", "iddb_policy_v1.md")
    if iddb_policy is not None:
        add_evidence(
            evidence, iddb_policy, "IDDB policy present at canonical repo path"
        )
    else:
        warnings.append(
            "docs/iddb_policy_v1.md is absent, so identity-data governance was only partially inspectable from the requested canonical path."
        )

    if required_ok:
        warnings.append(
            "Governance docs describe boundaries and rituals, but repo-local presence alone does not prove enforcement coverage across every route, worker, or extension seam."
        )

    summary = "Checks whether the main governance, validity, and risk surfaces exist, while preserving that governance text is not the same thing as enforced coverage."
    manual_prompts = [
        "Which identity, sovereignty, and permission boundaries are enforced in code today versus documented as doctrine only?",
        "Does current release language still stay narrower than the governance corpus, especially around delegation, plugins, and autonomy?",
        "Are known tech-debt items tracked in the places an operator will actually read before signoff?",
    ]
    return LensReport(
        name="Governance Integrity",
        status=determine_status(required_ok, warnings, evidence),
        summary=summary,
        evidence=evidence,
        warnings=warnings,
        manual_review_prompts=manual_prompts,
    )


def build_extension_discipline() -> LensReport:
    evidence: list[str] = []
    warnings: list[str] = []
    required_paths = [
        (
            "docs/architecture/self-extending-agent-plugin-system.md",
            "self-extending agent plugin system doc present",
        ),
        (
            "docs/architecture/agent-tool-loop-contract.md",
            "agent tool-loop contract present",
        ),
        (
            "guardian/routes/command_bus.py",
            "command bus route source present",
        ),
        (
            "guardian/command_bus/contracts.py",
            "command bus contract source present",
        ),
        (
            "guardian/command_bus/invoke.py",
            "command bus invoke path present",
        ),
    ]

    required_ok = True
    for relative, note in required_paths:
        path = REPO_ROOT / relative
        if path.exists():
            add_evidence(evidence, path, note)
        else:
            required_ok = False
            add_missing_warning(
                warnings,
                relative,
                "required extension boundary anchor is missing",
            )

    pi_contract = path_exists(
        "docs", "architecture", "pi-invocation-boundary-contract.md"
    )
    if pi_contract is not None:
        add_evidence(
            evidence, pi_contract, "Pi invocation boundary contract present"
        )

    plugin_doc = path_exists(
        "docs", "architecture", "self-extending-agent-plugin-system.md"
    )
    if plugin_doc is not None:
        text = read_text(plugin_doc)
        if contains_any(
            text,
            [
                "does not claim runtime implementation",
                "autonomous runtime execution",
                "plugin execution do not",
            ],
        ):
            warnings.append(
                "docs/architecture/self-extending-agent-plugin-system.md explicitly says several extension surfaces remain bounded, deferred, or non-runtime."
            )

    current_state = path_exists("docs", "architecture", "00-current-state.md")
    if current_state is not None:
        text = read_text(current_state)
        if contains_any(
            text,
            [
                "do not assume command bus",
                "internal/manual",
                "not part of the present release promise",
            ],
        ):
            warnings.append(
                "docs/architecture/00-current-state.md keeps command bus and adjacent extension surfaces outside the present release promise."
            )

    summary = "Checks that extension doctrine, bounded tool-loop contract, Pi boundary contract, and canonical command-bus source paths are present without promoting deferred execution surfaces into shipped authority."
    manual_prompts = [
        "Are any UI, docs, or operator surfaces implying autonomous extension execution that the bounded command-bus lane does not actually provide?",
        "Does Pi-like invocation remain clearly separated from provider ownership, transcript ownership, and command-bus authority?",
        "If an extension feature is described as available, can the repo prove whether it is manual, bounded, internal-only, or release-supported?",
    ]
    return LensReport(
        name="Extension Discipline",
        status=determine_status(required_ok, warnings, evidence),
        summary=summary,
        evidence=evidence,
        warnings=warnings,
        manual_review_prompts=manual_prompts,
    )


def build_narrative_readiness() -> LensReport:
    evidence: list[str] = []
    warnings: list[str] = []
    architecture_readme = path_exists("docs", "architecture", "README.md")
    atlas = path_exists("docs", "architecture", "architecture-atlas.md")
    current_state = path_exists("docs", "architecture", "00-current-state.md")
    doctrine = path_exists("docs", "architecture", "unity-audit-doctrine.md")

    required_ok = True
    for path, note in [
        (architecture_readme, "architecture KB entrypoint present"),
        (atlas, "architecture atlas present"),
        (current_state, "current-state release definition anchor present"),
        (doctrine, "Unity Audit doctrine present"),
    ]:
        if path is None:
            required_ok = False
            continue
        add_evidence(evidence, path, note)

    if architecture_readme is None:
        add_missing_warning(
            warnings,
            "docs/architecture/README.md",
            "required KB entrypoint is missing",
        )
    else:
        text = read_text(architecture_readme)
        if contains_any(text, ["unity audit doctrine"]):
            add_evidence(
                evidence,
                architecture_readme,
                "README references the Unity Audit doctrine",
            )
        else:
            warnings.append(
                "docs/architecture/README.md does not currently reference the Unity Audit doctrine."
            )

    if current_state is None:
        add_missing_warning(
            warnings,
            "docs/architecture/00-current-state.md",
            "required current-state file is missing",
        )
    else:
        text = read_text(current_state)
        if contains_any(text, ["release definition right now"]):
            add_evidence(
                evidence,
                current_state,
                "current-state includes an explicit release definition section",
            )
        if contains_any(
            text,
            [
                "runtime proof must be refreshed",
                "fresh live evidence exists",
                "live runtime proof remains required",
            ],
        ):
            warnings.append(
                "docs/architecture/00-current-state.md keeps release narrative dependent on fresh live proof rather than documentation presence alone."
            )

    summary = "Checks that the architecture entrypoint, atlas, doctrine, and current-state release framing exist and that the public-facing narrative still defers to fresh live proof."
    manual_prompts = [
        "Would a new reader understand that Unity Audit is a coherence scaffold, not a governance oracle or runtime proof engine?",
        "Does the architecture README route release-confidence questions to current-state before broader narrative docs?",
        "Are any outward-facing summaries claiming more readiness than the latest live supported-path proof actually demonstrates?",
    ]
    return LensReport(
        name="Narrative Readiness",
        status=determine_status(required_ok, warnings, evidence),
        summary=summary,
        evidence=evidence,
        warnings=warnings,
        manual_review_prompts=manual_prompts,
    )


def build_lenses() -> list[LensReport]:
    return [
        build_runtime_truth(),
        build_contract_integrity(),
        build_surface_coherence(),
        build_governance_integrity(),
        build_extension_discipline(),
        build_narrative_readiness(),
    ]


def make_report() -> dict[str, object]:
    repo_state = get_repo_state()
    lenses = build_lenses()
    summary = {
        "pass": sum(1 for lens in lenses if lens.status == "PASS"),
        "warn": sum(1 for lens in lenses if lens.status == "WARN"),
        "fail": sum(1 for lens in lenses if lens.status == "FAIL"),
        "unknown": sum(1 for lens in lenses if lens.status == "UNKNOWN"),
    }
    return {
        "audit": "unity",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "repo": {
            "branch": repo_state.branch,
            "head": repo_state.head,
            "dirty": repo_state.dirty,
        },
        "summary": summary,
        "lenses": [
            {
                "name": lens.name,
                "status": lens.status,
                "summary": lens.summary,
                "evidence": lens.evidence,
                "warnings": lens.warnings,
                "manual_review_prompts": lens.manual_review_prompts,
            }
            for lens in lenses
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    repo = report["repo"]
    summary = report["summary"]
    lenses = report["lenses"]
    lines = [
        "# Unity Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Repo branch: `{repo['branch']}`",
        f"- Repo head: `{repo['head']}`",
        f"- Repo dirty: `{repo['dirty']}`",
        "",
        "## Summary",
        "",
        "| PASS | WARN | FAIL | UNKNOWN |",
        "| --- | --- | --- | --- |",
        f"| {summary['pass']} | {summary['warn']} | {summary['fail']} | {summary['unknown']} |",
        "",
    ]

    manual_review_required: list[str] = []
    seen_prompts: set[str] = set()

    for lens in lenses:
        lines.extend(
            [
                f"## {lens['name']}",
                "",
                f"- Status: `{lens['status']}`",
                f"- Summary: {lens['summary']}",
                "",
                "### Evidence",
            ]
        )
        if lens["evidence"]:
            lines.extend(f"- {item}" for item in lens["evidence"])
        else:
            lines.append("- None found.")
        lines.extend(["", "### Warnings"])
        if lens["warnings"]:
            lines.extend(f"- {item}" for item in lens["warnings"])
        else:
            lines.append("- None.")
        lines.extend(["", "### Manual Review Prompts"])
        if lens["manual_review_prompts"]:
            for prompt in lens["manual_review_prompts"]:
                lines.append(f"- {prompt}")
                if prompt not in seen_prompts:
                    seen_prompts.add(prompt)
                    manual_review_required.append(prompt)
        else:
            lines.append("- None.")
        lines.append("")

    lines.extend(["## Manual Review Required", ""])
    if manual_review_required:
        lines.extend(f"- {prompt}" for prompt in manual_review_required)
    else:
        lines.append("- No additional manual review prompts were generated.")
    lines.extend(
        [
            "",
            "This audit is a coherence scaffold. It does not replace live runtime proof, ADR review, or release signoff.",
            "",
        ]
    )
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a repo-local Unity Audit coherence scaffold."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the JSON report to stdout.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print the Markdown report to stdout.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)),
        help="Output directory for latest.json and latest.md.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write output files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = make_report()
    json_text = json.dumps(report, indent=2) + "\n"
    markdown_text = render_markdown(report)

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    json_path = output_dir / "latest.json"
    markdown_path = output_dir / "latest.md"

    if not args.no_write:
        write_output(json_path, json_text)
        write_output(markdown_path, markdown_text)

    stdout_modes = []
    if args.json:
        stdout_modes.append(json_text.rstrip())
    if args.markdown:
        stdout_modes.append(markdown_text.rstrip())

    if stdout_modes:
        sys.stdout.write("\n\n".join(stdout_modes) + "\n")
    elif not args.no_write:
        sys.stdout.write(
            f"Wrote {relative_path(json_path)} and {relative_path(markdown_path)}\n"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
