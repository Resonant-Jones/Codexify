from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


OUTPUT_ROOT = Path("docs/guardian/work-briefs")
GENERATED_FILES = (
    "axis-brief.md",
    "codex-next-task-packet.md",
    "truth-ledger.md",
    "decision-log.md",
)
EXPECTED_ARCHITECTURE_FILES = (
    "docs/architecture/00-current-state.md",
    "docs/architecture/README.md",
    "docs/architecture/adr/ADR Index.md",
    "docs/architecture/adr/adr-index.md",
    "docs/architecture/agent-protocol-operations.md",
    "docs/architecture/config-and-ops.md",
)
CURRENT_STATE_PATH = Path("docs/architecture/00-current-state.md")

GIT_LFS_SAFE_CONFIG = (
    "-c",
    "filter.lfs.process=",
    "-c",
    "filter.lfs.clean=cat",
    "-c",
    "filter.lfs.required=false",
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RepoSnapshot:
    repo_root: Path
    branch: str
    head: str
    upstream: str | None
    ahead: int | None
    behind: int | None
    status_lines: tuple[str, ...]
    status_error: str
    architecture_files: tuple[tuple[str, bool], ...]


def run_command(args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
    completed = subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def run_git(repo_root: Path | None, *args: str) -> CommandResult:
    return run_command(("git", *GIT_LFS_SAFE_CONFIG, *args), cwd=repo_root)


def resolve_repo_root() -> Path:
    override = os.environ.get("GUARDIAN_BRIEF_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    result = run_git(None, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise RuntimeError(
            "Could not resolve repo root with git rev-parse --show-toplevel: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return Path(result.stdout.strip()).resolve()


def resolve_brief_date() -> str:
    override = os.environ.get("GUARDIAN_BRIEF_DATE")
    if override:
        datetime.strptime(override, "%Y-%m-%d")
        return override
    return datetime.now(timezone.utc).date().isoformat()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def markdown_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    body_start = text.find("\n", start)
    if body_start == -1:
        return ""
    next_heading = text.find("\n## ", body_start + 1)
    if next_heading == -1:
        return text[body_start + 1 :].strip()
    return text[body_start + 1 : next_heading].strip()


def bullet_lines(section: str) -> list[str]:
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            lines.append(line[2:].strip())
        elif len(line) > 3 and line[0].isdigit() and line[1:3] == ". ":
            lines.append(line[3:].strip())
        elif line and lines:
            lines[-1] = f"{lines[-1]} {line}"
    return lines


def current_state_summary(repo_root: Path) -> dict[str, object]:
    text = read_text(repo_root / CURRENT_STATE_PATH)
    return {
        "path": CURRENT_STATE_PATH.as_posix(),
        "last_updated": markdown_section(text, "Last updated"),
        "current_phase": markdown_section(text, "Current phase"),
        "supported_reality": bullet_lines(
            markdown_section(text, "Current supported reality")
        ),
        "do_not_assume": bullet_lines(
            markdown_section(text, "Not yet true / do not assume")
        ),
        "active_blockers": bullet_lines(markdown_section(text, "Active blockers")),
    }


def status_path(line: str) -> str | None:
    if line.startswith("## ") or len(line) < 4:
        return None
    return line[3:].strip()


def filter_generated_status_lines(
    lines: Sequence[str], *, brief_date: str
) -> tuple[str, ...]:
    generated_prefix = (OUTPUT_ROOT / brief_date).as_posix() + "/"
    filtered: list[str] = []
    for line in lines:
        path = status_path(line)
        if path and path.startswith(generated_prefix):
            continue
        filtered.append(line)
    return tuple(filtered)


def collect_snapshot(repo_root: Path, brief_date: str) -> RepoSnapshot:
    branch = run_git(repo_root, "branch", "--show-current")
    if branch.returncode != 0 or not branch.stdout.strip():
        branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    head = run_git(repo_root, "rev-parse", "--short=12", "HEAD")
    upstream = run_git(
        repo_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    status = run_git(
        repo_root, "status", "--short", "--branch", "--untracked-files=all"
    )

    upstream_ref = upstream.stdout.strip() if upstream.returncode == 0 else None
    ahead: int | None = None
    behind: int | None = None
    if upstream_ref:
        counts = run_git(repo_root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
        if counts.returncode == 0:
            parts = counts.stdout.strip().split()
            if len(parts) == 2:
                ahead = int(parts[0])
                behind = int(parts[1])

    architecture_files = tuple(
        (path, (repo_root / path).exists()) for path in EXPECTED_ARCHITECTURE_FILES
    )

    raw_status_lines = tuple(line for line in status.stdout.splitlines() if line.strip())

    return RepoSnapshot(
        repo_root=repo_root,
        branch=branch.stdout.strip() if branch.returncode == 0 else "unknown",
        head=head.stdout.strip() if head.returncode == 0 else "unknown",
        upstream=upstream_ref,
        ahead=ahead,
        behind=behind,
        status_lines=filter_generated_status_lines(
            raw_status_lines, brief_date=brief_date
        ),
        status_error=status.stderr.strip(),
        architecture_files=architecture_files,
    )


def format_bullets(items: Sequence[str], *, empty: str = "None recorded.") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def format_architecture_files(snapshot: RepoSnapshot) -> str:
    return "\n".join(
        f"- `{path}`: {'present' if exists else 'missing'}"
        for path, exists in snapshot.architecture_files
    )


def format_status(snapshot: RepoSnapshot) -> str:
    if not snapshot.status_lines and not snapshot.status_error:
        return "clean"
    lines = list(snapshot.status_lines)
    if snapshot.status_error:
        lines.append(f"status stderr: {snapshot.status_error}")
    return "\n".join(lines)


def upstream_summary(snapshot: RepoSnapshot) -> str:
    if not snapshot.upstream:
        return "No upstream configured"
    if snapshot.ahead is None or snapshot.behind is None:
        return f"{snapshot.upstream}; ahead/behind unavailable"
    return f"{snapshot.upstream}; ahead {snapshot.ahead}, behind {snapshot.behind}"


def generated_paths(brief_date: str) -> list[str]:
    return [
        (OUTPUT_ROOT / brief_date / filename).as_posix()
        for filename in GENERATED_FILES
    ]


def render_axis_brief(
    brief_date: str, snapshot: RepoSnapshot, current_state: dict[str, object]
) -> str:
    phase = str(current_state.get("current_phase") or "Not found.")
    blockers = current_state.get("active_blockers") or []
    do_not_assume = current_state.get("do_not_assume") or []

    return f"""# Guardian Work Brief - Axis Brief - {brief_date}

## Scope
Restore and use the repeatable Guardian Work Brief generation path for {brief_date}. This packet is reporting-only. It does not generate marketing packets, daily audits, heartbeat bundles, public exports, release claims, or runtime proof.

## Current Workspace State
- Repo root: `{snapshot.repo_root}`
- Branch: `{snapshot.branch}`
- Head: `{snapshot.head}`
- Upstream: {upstream_summary(snapshot)}
- Status command: `git status --short --branch --untracked-files=all`

```text
{format_status(snapshot)}
```

Expected architecture files:
{format_architecture_files(snapshot)}

## Runtime Truth Boundary
`docs/architecture/00-current-state.md` remains the short-horizon authority for supported release truth. Runtime paths were not re-proven by this generator.

Current phase from the truth boundary:

> {phase}

Do not widen release claims from this packet:
{format_bullets(do_not_assume if isinstance(do_not_assume, list) else [])}

## Axis Read
The useful move is to make the operator brief repeatable while keeping it below runtime machinery. Treat this packet as a drift and decision surface, not as evidence that queues, workers, providers, databases, SSE, Docker Compose, frontend paths, or model runtimes are healthy today.

## Minimal Viable Network
- Nodes: local operator workstation, local git checkout, generated work-brief directory, and human reviewer.
- Trust boundaries: repository boundary, branch/worktree boundary, and current-state documentation boundary.
- Threat model: honest-but-buggy automation and branch drift. This task does not model malicious peers or compromised runtime nodes.
- State ownership: git owns repository state; `00-current-state.md` owns release-truth interpretation; generated briefs own only dated reporting.
- Consistency target: deterministic local reporting for the same date and repo snapshot.
- Conflict policy: human-in-the-loop; `00-current-state.md` wins over older planning docs.

## What Breaks First
{format_bullets(blockers if isinstance(blockers, list) else [])}

## Recommended Focus
Review the generated evidence, classify any branch/worktree drift, and select the next human-approved implementation or verification slice. Do not treat this brief as runtime proof.
"""


def render_codex_packet(
    brief_date: str, snapshot: RepoSnapshot, current_state: dict[str, object]
) -> str:
    blockers = current_state.get("active_blockers") or []
    dirty = [line for line in snapshot.status_lines if not line.startswith("## ")]
    if snapshot.behind:
        next_task = "Decide whether to synchronize this branch before gathering release evidence."
        why = "The branch is behind upstream, so release-facing interpretation may be stale."
    elif dirty:
        next_task = "Classify local worktree changes before starting a broader implementation slice."
        why = "Dirty state can blur which evidence belongs to this reporting task."
    elif blockers:
        next_task = str(blockers[0])
        why = "The current-state blocker is the strongest local steering signal."
    else:
        next_task = "Select one supported-path proof or implementation slice for human review."
        why = "The generator found no stronger branch or worktree blocker."

    return f"""# Guardian Work Brief - Codex Next-Task Packet - {brief_date}

## Next Task
{next_task}

## Why This Task
{why}

## Acceptance Criteria
- Outcome is recorded as `go`, `hold`, or `next-proof-needed`.
- Any follow-up stays inside one explicit implementation or verification slice.
- Validation commands are recorded with pass/fail results.
- Release claims remain bounded by `docs/architecture/00-current-state.md`.

## Suggested Implementation Slice
1. Read the generated truth ledger and decision log.
2. Classify branch/worktree drift before editing runtime or release-facing surfaces.
3. Pick one narrow proof or repair task only after the drift is understood.

## Validation
- This packet was generated by `make guardian-brief`.
- Runtime validation was not run by this generator.
- If the next task touches runtime behavior, choose separate targeted tests for that task.

## Non-Goals
- No runtime route, worker, provider, queue, schema, command bus, or UI changes.
- No Docker Compose startup.
- No marketing, audit, heartbeat, public export, or campaign generation.
- No release claim expansion.
"""


def render_truth_ledger(
    brief_date: str, snapshot: RepoSnapshot, current_state: dict[str, object]
) -> str:
    supported = current_state.get("supported_reality") or []
    blockers = current_state.get("active_blockers") or []
    paths = generated_paths(brief_date)

    return f"""# Guardian Work Brief - Truth Ledger - {brief_date}

## Evidence Gathered
- Generator command path: `make guardian-brief` -> `python3 scripts/guardian/generate_work_brief.py`.
- Repo root: `{snapshot.repo_root}`
- Branch: `{snapshot.branch}`
- HEAD: `{snapshot.head}`
- Upstream: {upstream_summary(snapshot)}
- Status command captured before writing files: `git status --short --branch --untracked-files=all`
- Expected architecture file presence was checked.
- `docs/architecture/00-current-state.md` was read as the release-truth boundary.
- `docs/architecture/README.md` was checked as the architecture KB entrypoint.

Status snapshot:

```text
{format_status(snapshot)}
```

Architecture file presence:
{format_architecture_files(snapshot)}

## Proven
- The generator resolved a local git checkout.
- The generator captured branch, HEAD, upstream, ahead/behind when available, dirty state, and expected architecture file presence before writing.
- The generator wrote the four canonical Guardian Work Brief markdown files for `{brief_date}`.
- The current-state document remains the release-truth boundary for interpreting this packet.

Current supported reality copied only as documentary context:
{format_bullets(supported if isinstance(supported, list) else [])}

## Code-Path Only / Not Re-Proven Today
- No backend runtime path was exercised.
- No queue, worker, provider, Redis, Postgres, frontend, SSE, browser, Docker Compose, or model runtime path was tested.
- No marketing generation, daily audit generation, heartbeat bundle generation, public export generation, or release machinery was invoked.
- Any runtime capability mentioned here remains documentary context unless backed by a separate supported-path proof.

## Blockers
{format_bullets(blockers if isinstance(blockers, list) else [])}

## Changed Files From This Run
{format_bullets(paths)}
"""


def render_decision_log(brief_date: str, snapshot: RepoSnapshot) -> str:
    return f"""# Guardian Work Brief - Decision Log - {brief_date}

## Decisions

### D1: Generated packet through repeatable automation
- Decision: Generate the Guardian Work Brief through `make guardian-brief`.
- Reason: Repeatable local reporting is safer than manual packet reconstruction.
- Result: Four markdown reporting artifacts were written for `{brief_date}`.

### D2: Preserve branch state
- Decision: Report branch, upstream, and dirty state without fixing it.
- Reason: The generator is an operator-facing truth surface, not a branch repair tool.
- Current state: branch `{snapshot.branch}`, head `{snapshot.head}`, upstream {upstream_summary(snapshot)}.

### D3: No release claim expansion
- Decision: Keep this packet below runtime proof and release readiness.
- Reason: Reporting artifacts do not prove runtime health.
- Boundary: `docs/architecture/00-current-state.md` remains the release-truth authority.

### D4: Next task remains human-selected after reviewing generated evidence
- Decision: The generated Codex packet can recommend focus, but it does not approve execution.
- Reason: Human review is still required before runtime, release, or architecture-contract changes.
- Consequence: Treat the next task as `next-proof-needed` until a human selects it.
"""


def write_outputs(brief_date: str, snapshot: RepoSnapshot) -> list[Path]:
    current_state = current_state_summary(snapshot.repo_root)
    output_dir = snapshot.repo_root / OUTPUT_ROOT / brief_date
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "axis-brief.md": render_axis_brief(brief_date, snapshot, current_state),
        "codex-next-task-packet.md": render_codex_packet(
            brief_date, snapshot, current_state
        ),
        "truth-ledger.md": render_truth_ledger(brief_date, snapshot, current_state),
        "decision-log.md": render_decision_log(brief_date, snapshot),
    }

    written: list[Path] = []
    for filename in GENERATED_FILES:
        path = output_dir / filename
        path.write_text(outputs[filename], encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    try:
        repo_root = resolve_repo_root()
        brief_date = resolve_brief_date()
        snapshot = collect_snapshot(repo_root, brief_date)
        written = write_outputs(brief_date, snapshot)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"Guardian Work Brief generation failed: {exc}", file=sys.stderr)
        return 1

    print("Guardian Work Brief generated")
    for path in written:
        print(f"  {path.relative_to(repo_root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
