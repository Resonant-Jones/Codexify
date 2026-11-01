"""Project qualification rubrics and run receipts into a registry document.

The projection is a pure function of repository state: the same rubrics, the
same receipts, and the same tip always produce the same registry. That
property is what makes drift detectable, which is the point of the
`--check` mode in `generate_registry.py`.

For each qualification surface the projection selects one *current* run —
the latest receipt for that surface — and reports:

* `status` — the verdict of that run, projected unchanged;
* `freshness` — whether that run still describes the current tip;
* `tested_commit` — the commit that run tested;
* `last_qualified_at` — the date of that run;
* `evidence` — the detailed proofs that run cites.

A qualification surface with no run receipt is projected as `HOLD` with null
run fields. It is never projected as `PASS`: absence of evidence is not
evidence of qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from scripts.qualification.lib.freshness import GitHistory, compute_freshness
from scripts.qualification.lib.parsing import (
    QualificationParseError,
    Rubric,
    RunReceipt,
    parse_rubric,
    parse_run_receipt,
)

REGISTRY_VERSION = 1
RELEASE_AUTHORITY = "docs/architecture/00-current-state.md"


@dataclass(frozen=True)
class ProjectionResult:
    """The projected registry plus any non-fatal observations."""

    registry: dict
    warnings: tuple[str, ...] = ()


def discover_rubrics(rubrics_dir: Path, repo_root: Path) -> list[Rubric]:
    """Parse every rubric document in `rubrics_dir`.

    `README.md` is directory documentation rather than a rubric, so it is
    skipped.
    """
    rubrics: list[Rubric] = []
    for path in sorted(rubrics_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        rubrics.append(parse_rubric(path, repo_root))
    return rubrics


def discover_receipts(runs_dir: Path, repo_root: Path) -> list[RunReceipt]:
    """Parse every run receipt document in `runs_dir`.

    `README.md` and `TEMPLATE.md` are directory documentation rather than
    receipts, so they are skipped.
    """
    receipts: list[RunReceipt] = []
    for path in sorted(runs_dir.glob("*.md")):
        if path.name in {"README.md", "TEMPLATE.md"}:
            continue
        receipts.append(parse_run_receipt(path, repo_root))
    return receipts


def _select_current_receipt(
    receipts: Sequence[RunReceipt],
) -> tuple[RunReceipt | None, list[RunReceipt]]:
    """Return the latest receipt for a surface and the ones it supersedes.

    "Latest" is determined by receipt date, then by commit, so the selection
    is stable and does not depend on filesystem ordering.
    """
    if not receipts:
        return None, []
    ordered = sorted(receipts, key=lambda item: (item.date, item.commit))
    return ordered[-1], ordered[:-1]


def build_registry(
    rubrics: Iterable[Rubric],
    receipts: Iterable[RunReceipt],
    *,
    repo_root: Path,
    tip_sha: str,
    history: GitHistory | None = None,
) -> ProjectionResult:
    """Project rubrics and receipts into a registry document."""
    rubric_list = list(rubrics)
    receipt_list = list(receipts)
    warnings: list[str] = []

    by_surface: dict[str, list[RunReceipt]] = {}
    for receipt in receipt_list:
        by_surface.setdefault(receipt.qualification_id, []).append(receipt)

    qualifications: dict[str, dict] = {}
    for rubric in sorted(rubric_list, key=lambda item: item.qualification_id):
        surface_receipts = by_surface.get(rubric.qualification_id, [])
        current, superseded = _select_current_receipt(surface_receipts)

        entry: dict = {
            "title": rubric.title,
            "scope": rubric.scope,
            "status": "HOLD",
            "freshness": "stale",
            "rubric": f"rubrics/{rubric.path.name}",
            "latest_run": None,
            "tested_commit": None,
            "last_qualified_at": None,
            "evidence": list(rubric.evidence),
            "metrics": _metrics_for(surface_receipts),
            "blockers": [
                "No qualification run receipt exists for this surface; the "
                "registry cannot project a qualification status without one."
            ],
        }

        if current is not None:
            freshness = "stale"
            reasons: list[str] = []
            blockers: list[str] = []
            if history is not None:
                freshness, reasons, blockers = compute_freshness(
                    rubric, current, history, tip_sha
                )
            if reasons:
                warnings.append(
                    f"{rubric.qualification_id}: not current "
                    f"({reasons[0]}); {len(reasons)} reason(s)"
                    if len(reasons) > 1
                    else f"{rubric.qualification_id}: not current ({reasons[0]})"
                )

            entry.update(
                {
                    "status": current.verdict,
                    "freshness": freshness,
                    "latest_run": f"runs/{current.path.name}",
                    "tested_commit": current.commit,
                    "last_qualified_at": current.date,
                    "evidence": _merge_evidence(rubric.evidence, current.evidence),
                    "blockers": _blockers_for(blockers, superseded),
                }
            )

        qualifications[rubric.qualification_id] = entry

    registry = {
        "registry_version": REGISTRY_VERSION,
        "generated_from_repository": True,
        "release_authority": RELEASE_AUTHORITY,
        "qualifications": qualifications,
    }
    return ProjectionResult(registry=registry, warnings=tuple(warnings))


def _merge_evidence(
    rubric_evidence: Sequence[str], receipt_evidence: Sequence[str]
) -> list[str]:
    """Combine standing rubric evidence with run-scoped receipt evidence."""
    merged: list[str] = []
    for reference in (*rubric_evidence, *receipt_evidence):
        if reference not in merged:
            merged.append(reference)
    return merged


def _metrics_for(receipts: Sequence[RunReceipt]) -> dict[str, int]:
    """Derive dashboard metrics from the receipts for one surface.

    `human_testers` counts distinct human tester aliases. An automated run
    is not a human tester, so it never contributes to that count — the
    distinction matters because the README treats independent human
    qualification as the strongest signal available.
    """
    human_aliases: set[str] = set()
    independent = 0
    for receipt in receipts:
        if receipt.tester_kind == "human" and receipt.tester_alias:
            human_aliases.add(receipt.tester_alias)
            if receipt.assistance_level_peak == 0:
                independent += 1
    return {
        "human_testers": len(human_aliases),
        "independent_completions": independent,
        "run_receipts": len(receipts),
    }


def _blockers_for(
    freshness_blockers: Sequence[str], superseded: Sequence[RunReceipt]
) -> list[str]:
    """Describe why a projected qualification is not a current PASS."""
    blockers = list(freshness_blockers)
    if superseded:
        blockers.append(
            f"{len(superseded)} earlier run receipt(s) for this surface were "
            "superseded by a later run."
        )
    return blockers
