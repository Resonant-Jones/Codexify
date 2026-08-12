"""Bounded, read-only repository candidate discovery (Stage 2K.2 / ADR-065).

This module observes possible Git working trees below one already-authorized
Guardian-side root. An observation is ephemeral and non-authorizing: it is
not a Project, a durable registration, a Workspace member, or a model/tool
payload. Discovery finds; later, separately-authorized stages decide whether
to import and bind.

The scanner has no default roots and no path-only entry point. Callers must
first construct an :class:`AuthorizedDiscoveryRoot` through a narrow
authority-side factory. Traversal is bounded by the accepted ADR-065 limits,
does not follow symlinks, and only invokes the Stage 2K.1 exact-working-tree
validator after immediate ``.git`` evidence is present.
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from guardian.core.config import Settings
from guardian.core.repository_authority import (
    DISCOVERY_CANDIDATE_CLASS,
    GitValidationError,
    GuardianProjectsDirectoryUnconfigured,
    resolve_guardian_projects_directory,
    validate_git_working_tree_root,
)


# ADR-065's fixed Stage 2K.2 scanner envelope. These defaults are deliberately
# not configuration values: an operator cannot accidentally widen the first
# discovery capability at runtime.
DEFAULT_REPOSITORY_DISCOVERY_MAX_DEPTH = 4
DEFAULT_REPOSITORY_DISCOVERY_MAX_CANDIDATES = 128
DEFAULT_REPOSITORY_DISCOVERY_TIMEOUT_SECONDS = 10.0

DISCOVERY_ROOT_PROVENANCE_GUARDIAN_PROJECTS_DIRECTORY = (
    "guardian_projects_directory"
)
DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION = (
    "explicit_authenticated_user_selection"
)
DISCOVERY_ROOT_PROVENANCE_EVIDENCE_BACKED_LOCAL_ROOT = (
    "evidence_backed_local_root"
)
DISCOVERY_ROOT_PROVENANCE_CONNECTOR_AUTHORIZED_ROOT = (
    "connector_authorized_root"
)
DISCOVERY_ROOT_PROVENANCE_CLASSES = frozenset(
    {
        DISCOVERY_ROOT_PROVENANCE_GUARDIAN_PROJECTS_DIRECTORY,
        DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION,
        DISCOVERY_ROOT_PROVENANCE_EVIDENCE_BACKED_LOCAL_ROOT,
        DISCOVERY_ROOT_PROVENANCE_CONNECTOR_AUTHORIZED_ROOT,
    }
)

GIT_EVIDENCE_DIRECTORY = "git_directory"
GIT_EVIDENCE_WORKTREE_FILE = "git_worktree_file"
GIT_EVIDENCE_KINDS = frozenset(
    {GIT_EVIDENCE_DIRECTORY, GIT_EVIDENCE_WORKTREE_FILE}
)

STOP_REASON_COMPLETED = "completed"
STOP_REASON_CANDIDATE_LIMIT_REACHED = "candidate_limit_reached"
STOP_REASON_TIMEOUT_REACHED = "timeout_reached"
DISCOVERY_STOP_REASONS = frozenset(
    {
        STOP_REASON_COMPLETED,
        STOP_REASON_CANDIDATE_LIMIT_REACHED,
        STOP_REASON_TIMEOUT_REACHED,
    }
)

EVIDENCE_REFERENCE_MAX_LENGTH = 256


class RepositoryDiscoveryError(Exception):
    """Base class for bounded repository discovery failures."""


class InvalidDiscoveryRoot(RepositoryDiscoveryError):
    """A proposed authority-side discovery root is not a usable directory."""


class ForbiddenDiscoveryRoot(RepositoryDiscoveryError):
    """A proposed root is too broad to authorize for discovery."""


class DiscoveryRootAuthorizationError(RepositoryDiscoveryError):
    """The caller did not supply the required root authorization evidence."""


@dataclass(frozen=True)
class RepositoryDiscoveryLimits:
    """Fixed per-root traversal limits selected by ADR-065."""

    max_depth: int = DEFAULT_REPOSITORY_DISCOVERY_MAX_DEPTH
    max_candidates: int = DEFAULT_REPOSITORY_DISCOVERY_MAX_CANDIDATES
    timeout_seconds: float = DEFAULT_REPOSITORY_DISCOVERY_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if (
            not isinstance(self.max_depth, int)
            or isinstance(self.max_depth, bool)
            or self.max_depth < 0
        ):
            raise ValueError("max_depth must be a non-negative integer")
        if (
            not isinstance(self.max_candidates, int)
            or isinstance(self.max_candidates, bool)
            or self.max_candidates <= 0
        ):
            raise ValueError("max_candidates must be a positive integer")
        if (
            not isinstance(self.timeout_seconds, (int, float))
            or isinstance(self.timeout_seconds, bool)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class AuthorizedDiscoveryRoot:
    """One already-authorized internal root eligible for bounded observation."""

    authorized_actor_id: str
    canonical_root: Path
    provenance_class: str
    authorized_at: datetime
    limits: RepositoryDiscoveryLimits = field(
        default_factory=RepositoryDiscoveryLimits
    )
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.authorized_actor_id.strip():
            raise DiscoveryRootAuthorizationError(
                "authorized_actor_id is required for repository discovery"
            )
        if self.provenance_class not in DISCOVERY_ROOT_PROVENANCE_CLASSES:
            raise DiscoveryRootAuthorizationError(
                "unsupported discovery root provenance class"
            )
        canonical_root = _canonicalize_discovery_directory(self.canonical_root)
        object.__setattr__(self, "canonical_root", canonical_root)
        if not isinstance(self.limits, RepositoryDiscoveryLimits):
            raise TypeError("limits must be RepositoryDiscoveryLimits")
        if not isinstance(self.authorized_at, datetime) or self.authorized_at.tzinfo is None:
            raise DiscoveryRootAuthorizationError(
                "authorized_at must carry timezone information"
            )
        if self.provenance_class in {
            DISCOVERY_ROOT_PROVENANCE_EVIDENCE_BACKED_LOCAL_ROOT,
            DISCOVERY_ROOT_PROVENANCE_CONNECTOR_AUTHORIZED_ROOT,
        }:
            _validate_evidence_reference(self.evidence_reference)


@dataclass(frozen=True)
class RepositoryDiscoveryCandidate:
    """An internal, non-authorizing observation of one Git working-tree root."""

    canonical_working_tree_root: Path
    root_relative_path: Path
    discovery_root_provenance_class: str
    authorized_actor_id: str
    git_evidence_kind: str
    discovered_at: datetime
    source_class: str = DISCOVERY_CANDIDATE_CLASS

    def __post_init__(self) -> None:
        if self.source_class != DISCOVERY_CANDIDATE_CLASS:
            raise ValueError("repository discovery candidates are non-authorizing")
        if not self.canonical_working_tree_root.is_absolute():
            raise ValueError("candidate root must be canonical and absolute")
        if self.git_evidence_kind not in GIT_EVIDENCE_KINDS:
            raise ValueError("unsupported Git evidence kind")


@dataclass(frozen=True)
class RepositoryDiscoveryResult:
    """Ephemeral bounded observations and privacy-safe traversal counters."""

    candidates: tuple[RepositoryDiscoveryCandidate, ...]
    scanned_directory_count: int
    skipped_symlink_count: int
    invalid_git_evidence_count: int
    duplicate_candidate_count: int
    elapsed_seconds: float
    limits: RepositoryDiscoveryLimits
    stop_reason: str

    def __post_init__(self) -> None:
        if self.stop_reason not in DISCOVERY_STOP_REASONS:
            raise ValueError("unsupported discovery stop reason")


def _validate_evidence_reference(evidence_reference: str | None) -> str:
    if evidence_reference is None:
        raise DiscoveryRootAuthorizationError("evidence_reference is required")
    normalized = str(evidence_reference).strip()
    if not normalized or len(normalized) > EVIDENCE_REFERENCE_MAX_LENGTH:
        raise DiscoveryRootAuthorizationError(
            "evidence_reference must be a nonempty bounded string"
        )
    return normalized


def _canonicalize_discovery_directory(root: Path | str) -> Path:
    candidate = Path(root).expanduser()
    try:
        canonical_root = candidate.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise InvalidDiscoveryRoot("discovery root must exist") from exc
    if not canonical_root.is_dir():
        raise InvalidDiscoveryRoot("discovery root must be a directory")

    forbidden_roots = {
        Path("/").resolve(),
        Path("/Users").resolve(),
        Path("/Volumes").resolve(),
        Path.home().resolve(),
    }
    if canonical_root in forbidden_roots:
        raise ForbiddenDiscoveryRoot(
            "discovery root is broader than the accepted authority boundary"
        )
    return canonical_root


def _authorized_root(
    *,
    authorized_actor_id: str,
    root: Path | str,
    provenance_class: str,
    limits: RepositoryDiscoveryLimits | None,
    evidence_reference: str | None = None,
    authorized_at: datetime | None = None,
) -> AuthorizedDiscoveryRoot:
    actor_id = str(authorized_actor_id).strip()
    if not actor_id:
        raise DiscoveryRootAuthorizationError("authorized_actor_id is required")
    canonical_root = _canonicalize_discovery_directory(root)
    return AuthorizedDiscoveryRoot(
        authorized_actor_id=actor_id,
        canonical_root=canonical_root,
        provenance_class=provenance_class,
        authorized_at=authorized_at or datetime.now(timezone.utc),
        limits=limits or RepositoryDiscoveryLimits(),
        evidence_reference=evidence_reference,
    )


def authorize_guardian_projects_discovery_root(
    *,
    authorized_actor_id: str,
    settings: Settings | None = None,
    limits: RepositoryDiscoveryLimits | None = None,
    authorized_at: datetime | None = None,
) -> AuthorizedDiscoveryRoot:
    """Authorize only the Stage 2K.1 configured Guardian Projects Directory."""
    configured_root = resolve_guardian_projects_directory(
        settings=settings, create=False
    )
    if configured_root is None:
        raise GuardianProjectsDirectoryUnconfigured()
    return _authorized_root(
        authorized_actor_id=authorized_actor_id,
        root=configured_root,
        provenance_class=DISCOVERY_ROOT_PROVENANCE_GUARDIAN_PROJECTS_DIRECTORY,
        limits=limits,
        authorized_at=authorized_at,
    )


def authorize_explicit_discovery_root(
    *,
    authorized_actor_id: str,
    root: Path | str,
    limits: RepositoryDiscoveryLimits | None = None,
    authorized_at: datetime | None = None,
) -> AuthorizedDiscoveryRoot:
    """Authorize one explicit authenticated-user selection without inference."""
    return _authorized_root(
        authorized_actor_id=authorized_actor_id,
        root=root,
        provenance_class=(
            DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION
        ),
        limits=limits,
        authorized_at=authorized_at,
    )


def authorize_evidence_backed_discovery_root(
    *,
    authorized_actor_id: str,
    root: Path | str,
    evidence_reference: str,
    limits: RepositoryDiscoveryLimits | None = None,
    authorized_at: datetime | None = None,
) -> AuthorizedDiscoveryRoot:
    """Authorize an already-evidenced local root; this performs no discovery."""
    return _authorized_root(
        authorized_actor_id=authorized_actor_id,
        root=root,
        provenance_class=DISCOVERY_ROOT_PROVENANCE_EVIDENCE_BACKED_LOCAL_ROOT,
        limits=limits,
        evidence_reference=_validate_evidence_reference(evidence_reference),
        authorized_at=authorized_at,
    )


def authorize_connector_discovery_root(
    *,
    authorized_actor_id: str,
    root: Path | str,
    evidence_reference: str,
    limits: RepositoryDiscoveryLimits | None = None,
    authorized_at: datetime | None = None,
) -> AuthorizedDiscoveryRoot:
    """Authorize a connector-provided root only with equivalent evidence."""
    return _authorized_root(
        authorized_actor_id=authorized_actor_id,
        root=root,
        provenance_class=DISCOVERY_ROOT_PROVENANCE_CONNECTOR_AUTHORIZED_ROOT,
        limits=limits,
        evidence_reference=_validate_evidence_reference(evidence_reference),
        authorized_at=authorized_at,
    )


def _remaining_seconds(
    *, deadline: float, monotonic: Callable[[], float]
) -> float:
    return max(0.0, deadline - monotonic())


def _elapsed_seconds(
    *, started_at: float, monotonic: Callable[[], float], limit: float
) -> float:
    return min(limit, max(0.0, monotonic() - started_at))


def _git_evidence_kind(directory: Path) -> tuple[str | None, bool]:
    """Return immediate Git evidence and whether it was a rejected symlink."""
    dot_git = directory / ".git"
    if dot_git.is_symlink():
        return None, True
    if dot_git.is_dir():
        return GIT_EVIDENCE_DIRECTORY, False
    if dot_git.is_file():
        return GIT_EVIDENCE_WORKTREE_FILE, False
    return None, False


def discover_repository_candidates(
    root: AuthorizedDiscoveryRoot,
) -> RepositoryDiscoveryResult:
    """Return bounded, ephemeral Git working-tree observations below ``root``.

    The parameter intentionally accepts no ``str`` or ``Path`` alternative:
    discovery-root authorization must happen before traversal. The scanner uses
    deterministic breadth-first ordering, does not follow symlinks, validates
    only immediate Git evidence, and never performs filesystem writes.
    """
    if not isinstance(root, AuthorizedDiscoveryRoot):
        raise TypeError("discover_repository_candidates requires AuthorizedDiscoveryRoot")

    monotonic = time.monotonic
    started_at = monotonic()
    deadline = started_at + root.limits.timeout_seconds
    pending: deque[tuple[Path, int]] = deque([(root.canonical_root, 0)])
    candidates: list[RepositoryDiscoveryCandidate] = []
    observed_roots: set[Path] = set()
    scanned_directory_count = 0
    skipped_symlink_count = 0
    invalid_git_evidence_count = 0
    duplicate_candidate_count = 0
    stop_reason = STOP_REASON_COMPLETED

    while pending:
        if _remaining_seconds(deadline=deadline, monotonic=monotonic) <= 0:
            stop_reason = STOP_REASON_TIMEOUT_REACHED
            break

        directory, depth = pending.popleft()
        scanned_directory_count += 1
        evidence_kind, rejected_git_symlink = _git_evidence_kind(directory)
        if rejected_git_symlink:
            skipped_symlink_count += 1

        if evidence_kind is not None:
            remaining_seconds = _remaining_seconds(
                deadline=deadline, monotonic=monotonic
            )
            if remaining_seconds <= 0:
                stop_reason = STOP_REASON_TIMEOUT_REACHED
                break
            try:
                canonical_root = validate_git_working_tree_root(
                    directory, timeout_seconds=remaining_seconds
                )
            except GitValidationError:
                invalid_git_evidence_count += 1
            else:
                if canonical_root in observed_roots:
                    duplicate_candidate_count += 1
                else:
                    observed_roots.add(canonical_root)
                    candidates.append(
                        RepositoryDiscoveryCandidate(
                            canonical_working_tree_root=canonical_root,
                            root_relative_path=directory.relative_to(
                                root.canonical_root
                            ),
                            discovery_root_provenance_class=root.provenance_class,
                            authorized_actor_id=root.authorized_actor_id,
                            git_evidence_kind=evidence_kind,
                            discovered_at=datetime.now(timezone.utc),
                        )
                    )
                    if len(candidates) >= root.limits.max_candidates:
                        stop_reason = STOP_REASON_CANDIDATE_LIMIT_REACHED
                        break
                # A successfully validated repository is a traversal boundary,
                # including deterministic aliases of an already observed root.
                continue

        if depth >= root.limits.max_depth:
            continue

        try:
            with os.scandir(directory) as entries:
                ordered_entries = sorted(entries, key=lambda entry: entry.name)
        except OSError:
            # Traversal is best-effort under the fixed envelope. Do not expose
            # inaccessible local path details through this internal result.
            continue

        for entry in ordered_entries:
            if _remaining_seconds(deadline=deadline, monotonic=monotonic) <= 0:
                stop_reason = STOP_REASON_TIMEOUT_REACHED
                break
            if entry.name == ".git":
                continue
            if entry.is_symlink():
                skipped_symlink_count += 1
                continue
            try:
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_directory:
                pending.append((Path(entry.path), depth + 1))
        if stop_reason == STOP_REASON_TIMEOUT_REACHED:
            break

    return RepositoryDiscoveryResult(
        candidates=tuple(candidates),
        scanned_directory_count=scanned_directory_count,
        skipped_symlink_count=skipped_symlink_count,
        invalid_git_evidence_count=invalid_git_evidence_count,
        duplicate_candidate_count=duplicate_candidate_count,
        elapsed_seconds=_elapsed_seconds(
            started_at=started_at,
            monotonic=monotonic,
            limit=root.limits.timeout_seconds,
        ),
        limits=root.limits,
        stop_reason=stop_reason,
    )
