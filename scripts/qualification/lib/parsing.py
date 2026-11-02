"""Parse qualification rubrics and run receipts into structured records.

The `docs/qualification/README.md` contract defines four layers:

    Rubric -> defines what must be proven
    Run    -> records what was actually attempted
    Evidence -> supports each observation
    Registry -> projects current qualification status

Rubrics are Markdown documents under `docs/qualification/rubrics/`. Run
receipts are Markdown documents under `docs/qualification/runs/`. Both carry
machine-readable metadata in a fenced YAML block so the registry can be
projected deterministically instead of being hand-maintained.

The metadata block is deliberately small and explicit:

    ```yaml qualification-metadata
    qualification_id: supported-compose
    version: 1
    title: Supported Compose
    scope: One line describing exactly what this surface covers.
    surface_paths:
      - guardian/routes/**
    evidence:
      - docs/architecture/proofs/supported-compose/some-proof.md
    ```

    Run receipts additionally declare their verdict and the commit they tested:

    ```yaml qualification-metadata
    qualification_id: supported-compose
    rubric_version: 1
    verdict: HOLD
    commit: 5da79431fa059b7da80688380550cf29d4854b18
    date: 2026-09-22
    tester_alias: automated-architecture-proof
    tester_kind: automated
    assistance_level_peak: 0
    ```

`evidence` on a rubric is *standing* evidence: proof artifacts that document
the surface regardless of whether a qualification run has been recorded. On
a receipt it is *run-scoped* evidence: what that specific run cited. The
registry projects the union, so a surface with no run still links the proofs
that describe it without ever being projected as qualified.

Every parser here is strict. A malformed metadata block is an error rather
than a silently skipped surface, because a qualification surface that
disappears from the registry is indistinguishable from one that was never
qualified.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

METADATA_FENCE_OPEN = "```yaml qualification-metadata"
METADATA_FENCE_CLOSE = "```"

QUALIFICATION_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
VERDICTS = ("PASS", "HOLD", "FAIL")
FRESHNESS = ("current", "stale", "superseded")


class QualificationParseError(ValueError):
    """A rubric or run receipt could not be parsed into a usable record."""

    def __init__(self, code: str, message: str, *, path: Path | None = None) -> None:
        self.code = code
        self.path = path
        location = f"{path}: " if path is not None else ""
        super().__init__(f"{location}{code}: {message}")


@dataclass(frozen=True)
class Rubric:
    """One qualification surface definition."""

    qualification_id: str
    version: int
    title: str
    scope: str
    surface_paths: tuple[str, ...]
    path: Path
    repo_root: Path
    evidence: tuple[str, ...] = ()

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(self.repo_root).as_posix()


@dataclass(frozen=True)
class RunReceipt:
    """One qualification attempt record."""

    qualification_id: str
    rubric_version: int
    verdict: str
    commit: str
    date: str
    path: Path
    repo_root: Path
    evidence: tuple[str, ...] = ()
    tester_alias: str = ""
    tester_kind: str = ""
    assistance_level_peak: int | None = None

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(self.repo_root).as_posix()


@dataclass
class ParsedDocument:
    """A parsed Markdown document plus its declared metadata."""

    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


def extract_metadata_block(text: str, path: Path) -> dict[str, Any]:
    """Return the YAML metadata block declared by a Markdown document.

    Raises `QualificationParseError` when the block is missing, unparseable,
    or not a mapping. A missing block is an error rather than an empty
    mapping so that a truncated or hand-mangled document cannot silently
    remove a qualification surface from the registry.
    """
    start = text.find(METADATA_FENCE_OPEN)
    if start == -1:
        raise QualificationParseError(
            "metadata_block_missing",
            "document does not declare a '```yaml qualification-metadata' block",
            path=path,
        )

    body_start = start + len(METADATA_FENCE_OPEN)
    close = text.find(METADATA_FENCE_CLOSE, body_start)
    if close == -1:
        raise QualificationParseError(
            "metadata_block_unterminated",
            "metadata block is not terminated by a closing fence",
            path=path,
        )

    raw = text[body_start:close]
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise QualificationParseError(
            "metadata_block_invalid_yaml",
            f"metadata block is not valid YAML: {exc}",
            path=path,
        ) from exc

    if not isinstance(loaded, dict):
        raise QualificationParseError(
            "metadata_block_not_mapping",
            "metadata block must decode to a mapping",
            path=path,
        )
    return loaded


def _require_str(
    metadata: dict[str, Any], key: str, path: Path, *, code_prefix: str
) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QualificationParseError(
            f"{code_prefix}_{key}_missing",
            f"metadata must declare a non-empty string '{key}'",
            path=path,
        )
    return value.strip()


def _require_int(
    metadata: dict[str, Any], key: str, path: Path, *, code_prefix: str
) -> int:
    value = metadata.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise QualificationParseError(
            f"{code_prefix}_{key}_invalid",
            f"metadata must declare an integer '{key}'",
            path=path,
        )
    return value


def _optional_str(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise QualificationParseError(
            f"{key}_invalid",
            f"metadata '{key}' must be a string when present",
        )
    return value.strip()


def _optional_str_list(metadata: dict[str, Any], key: str) -> tuple[str, ...]:
    raw = metadata.get(key, [])
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise QualificationParseError(
            f"{key}_invalid",
            f"metadata '{key}' must be a list when present",
        )
    values: list[str] = []
    for entry in raw:
        if not isinstance(entry, str) or not entry.strip():
            raise QualificationParseError(
                f"{key}_invalid",
                f"metadata '{key}' entries must be non-empty strings",
            )
        values.append(entry.strip())
    return tuple(values)


def _require_commit(
    metadata: dict[str, Any], key: str, path: Path, *, code_prefix: str
) -> str:
    """Return a commit SHA declared under `key`.

    YAML resolves an all-digit SHA to an integer, so a receipt that writes
    such a commit unquoted must still parse. The value is coerced back to
    its literal digits and then checked against the SHA shape.
    """
    value = metadata.get(key)
    if isinstance(value, bool):
        value = None
    elif isinstance(value, int):
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise QualificationParseError(
            f"{code_prefix}_{key}_missing",
            f"metadata must declare a non-empty commit '{key}'",
            path=path,
        )
    commit = value.strip()
    if not COMMIT_RE.match(commit):
        raise QualificationParseError(
            f"{code_prefix}_{key}_invalid",
            f"commit '{commit}' must be a full 40-character lowercase SHA",
            path=path,
        )
    return commit


def _require_date(
    metadata: dict[str, Any], key: str, path: Path, *, code_prefix: str
) -> str:
    """Return an ISO date string declared under `key`.

    YAML resolves an unquoted `2026-09-22` to a `datetime.date`, so a
    receipt that writes the date the natural way must still parse. Both the
    quoted string form and the resolved date form are accepted; anything
    else is rejected.
    """
    value = metadata.get(key)
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
        return value.strip()
    raise QualificationParseError(
        f"{code_prefix}_{key}_invalid",
        f"metadata must declare an ISO date '{key}' (YYYY-MM-DD)",
        path=path,
    )


def parse_rubric(path: Path, repo_root: Path) -> Rubric:
    """Parse one rubric document into a `Rubric`."""
    text = path.read_text(encoding="utf-8")
    metadata = extract_metadata_block(text, path)

    qualification_id = _require_str(
        metadata, "qualification_id", path, code_prefix="rubric"
    )
    if not QUALIFICATION_ID_RE.match(qualification_id):
        raise QualificationParseError(
            "rubric_qualification_id_invalid",
            f"qualification_id '{qualification_id}' must match "
            f"{QUALIFICATION_ID_RE.pattern}",
            path=path,
        )

    surface_paths = metadata.get("surface_paths")
    if not isinstance(surface_paths, list) or not surface_paths:
        raise QualificationParseError(
            "rubric_surface_paths_missing",
            "rubric must declare a non-empty 'surface_paths' list so that "
            "freshness can be computed against meaningful changes",
            path=path,
        )
    normalized: list[str] = []
    for entry in surface_paths:
        if not isinstance(entry, str) or not entry.strip():
            raise QualificationParseError(
                "rubric_surface_paths_invalid",
                "'surface_paths' entries must be non-empty strings",
                path=path,
            )
        normalized.append(entry.strip())

    return Rubric(
        qualification_id=qualification_id,
        version=_require_int(metadata, "version", path, code_prefix="rubric"),
        title=_require_str(metadata, "title", path, code_prefix="rubric"),
        scope=_require_str(metadata, "scope", path, code_prefix="rubric"),
        surface_paths=tuple(normalized),
        path=path,
        repo_root=repo_root,
        evidence=_optional_str_list(metadata, "evidence"),
    )


def parse_run_receipt(path: Path, repo_root: Path) -> RunReceipt:
    """Parse one run receipt document into a `RunReceipt`."""
    text = path.read_text(encoding="utf-8")
    metadata = extract_metadata_block(text, path)

    verdict = _require_str(metadata, "verdict", path, code_prefix="receipt")
    if verdict not in VERDICTS:
        raise QualificationParseError(
            "receipt_verdict_invalid",
            f"verdict '{verdict}' must be one of {', '.join(VERDICTS)}",
            path=path,
        )

    commit = _require_commit(metadata, "commit", path, code_prefix="receipt")

    date = _require_date(metadata, "date", path, code_prefix="receipt")

    evidence_raw = metadata.get("evidence", [])
    if not isinstance(evidence_raw, list):
        raise QualificationParseError(
            "receipt_evidence_invalid",
            "'evidence' must be a list when present",
            path=path,
        )
    evidence: list[str] = []
    for entry in evidence_raw:
        if not isinstance(entry, str) or not entry.strip():
            raise QualificationParseError(
                "receipt_evidence_invalid",
                "'evidence' entries must be non-empty strings",
                path=path,
            )
        evidence.append(entry.strip())

    assistance = metadata.get("assistance_level_peak")
    if assistance is not None and (
        isinstance(assistance, bool) or not isinstance(assistance, int)
    ):
        raise QualificationParseError(
            "receipt_assistance_level_invalid",
            "metadata 'assistance_level_peak' must be an integer when present",
            path=path,
        )

    return RunReceipt(
        qualification_id=_require_str(
            metadata, "qualification_id", path, code_prefix="receipt"
        ),
        rubric_version=_require_int(
            metadata, "rubric_version", path, code_prefix="receipt"
        ),
        verdict=verdict,
        commit=commit,
        date=date,
        path=path,
        repo_root=repo_root,
        evidence=tuple(evidence),
        tester_alias=_optional_str(metadata, "tester_alias"),
        tester_kind=_optional_str(metadata, "tester_kind"),
        assistance_level_peak=assistance,
    )
