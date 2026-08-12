"""Project-to-RepositoryBinding authority (Stage 2K.1 / ADR-065).

Guardian-owned durable Project-to-Git-working-tree authority. Repository
authority is derived, never model-supplied. Guardian Projects Directory is
configuration-owned. There is no cwd fallback, no nearest ``.git``
fallback, no ``CODEXIFY_WORKTREE_REPO_PATH`` fallback, no worktree
query-path authority, no application-checkout fallback, and no startup
filesystem scan.

This module deliberately exposes authority-side types only. It is NOT a
chat/tool/provider payload. Future capability advertisement (Stage 2K.5)
and repository.search (Stage 2K.4) consume its typed results; they do not
receive raw absolute roots or mounts.

ADR-065 invariants enforced here:

- Repository authority is Guardian-derived, never model-supplied.
- Guardian Projects Directory is configuration-owned.
- One Project has at most one active RepositoryBinding.
- Repository-less Projects remain valid.
- ``General`` receives no implicit RepositoryBinding.
- Project display names are not filesystem identity.
- Absolute repository roots remain authority-side data.
- ``guardian_managed`` roots remain beneath Guardian Projects Directory.
- ``external_linked`` roots may remain outside Guardian Projects Directory.
- symlink/path escape fails closed.
- missing roots fail closed.
- non-Git roots fail closed.
- nested subdirectories are not silently promoted to repository roots.
- ambiguous bindings fail closed.
- account/Project ownership mismatch fails closed.
- inactive bindings grant no authority.
- ``discovery_candidate`` is not binding authority.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from guardian.core.config import Settings, get_settings
from guardian.db.models import (
    Project,
    REPOSITORY_BINDING_SOURCE_CLASS_EXTERNAL_LINKED,
    REPOSITORY_BINDING_SOURCE_CLASS_GUARDIAN_MANAGED,
    RepositoryBinding,
)

# Canonical configuration key per ADR-065. Unset → fail closed.
GUARDIAN_PROJECTS_DIR_CONFIG_KEY = "CODEXIFY_GUARDIAN_PROJECTS_DIR"

# Source-class vocabulary (ADR-065). ``discovery_candidate`` is intentionally
# absent — it is not an active RepositoryBinding source class.
SOURCE_CLASS_GUARDIAN_MANAGED = REPOSITORY_BINDING_SOURCE_CLASS_GUARDIAN_MANAGED
SOURCE_CLASS_EXTERNAL_LINKED = REPOSITORY_BINDING_SOURCE_CLASS_EXTERNAL_LINKED
BINDING_SOURCE_CLASSES: tuple[str, ...] = (
    SOURCE_CLASS_GUARDIAN_MANAGED,
    SOURCE_CLASS_EXTERNAL_LINKED,
)
DISCOVERY_CANDIDATE_CLASS = "discovery_candidate"

# Bounded subprocess budget for the read-only git top-level probe.
DEFAULT_GIT_VALIDATION_TIMEOUT_SECONDS = 15.0

# RepositoryBinding provenance is evidence only. Keep this first storage
# slice intentionally narrow so it cannot become a side channel for secrets,
# prompts, repository contents, or discovery output.
PROVENANCE_ALLOWED_KEYS = frozenset(
    {
        "registration_source",
        "operation_class",
        "authority_context",
    }
)
PROVENANCE_MAX_CONTEXT_ITEMS = 8
PROVENANCE_MAX_KEY_LENGTH = 64
PROVENANCE_MAX_VALUE_LENGTH = 256
PROVENANCE_MAX_SERIALIZED_BYTES = 2048


class RepositoryAuthorityError(Exception):
    """Base class for Stage 2K.1 authority failures."""


class GuardianProjectsDirectoryUnconfigured(RepositoryAuthorityError):
    """``CODEXIFY_GUARDIAN_PROJECTS_DIR`` is unset or empty."""

    def __init__(self) -> None:
        super().__init__(
            "CODEXIFY_GUARDIAN_PROJECTS_DIR is not configured; "
            "repository-backed Project authority is unavailable."
        )


class GuardianProjectsDirectoryNotDirectory(RepositoryAuthorityError):
    """The configured root exists but is not a directory."""


class GuardianProjectsDirectoryNotAbsolute(RepositoryAuthorityError):
    """The configured Guardian Projects Directory is relative."""


class GuardianProjectsDirectoryOutsideAllowedRoot(
    RepositoryAuthorityError
):
    """A managed-root candidate is not contained beneath the configured root."""


class ManagedRootSymlinkEscape(RepositoryAuthorityError):
    """A managed-root candidate escapes via symlink or traversal."""


class GitValidationError(RepositoryAuthorityError):
    """The read-only git working-tree probe failed."""


class InvalidRepositoryRoot(GitValidationError):
    """The candidate path is not an exact Git working-tree root."""


class NestedRepositoryRejected(InvalidRepositoryRoot):
    """The candidate path is a subdirectory inside an existing Git root."""


class AccountProjectMismatch(RepositoryAuthorityError):
    """The authenticated account does not own the requested Project."""


class ProjectNotFound(RepositoryAuthorityError):
    """The requested Project does not exist."""


class UnsupportedSourceClass(RepositoryAuthorityError):
    """The proposed source class is not a binding-eligible class."""


class ActiveBindingAlreadyExists(RepositoryAuthorityError):
    """The Project already has an active RepositoryBinding."""


class BindingResolutionFailed(RepositoryAuthorityError):
    """No single active RepositoryBinding could be resolved for the Project."""


class InvalidRepositoryBindingProvenance(RepositoryAuthorityError):
    """Binding provenance exceeds the narrow authority-side evidence contract."""


@dataclass(frozen=True)
class ResolvedRepositoryBinding:
    """Authority-side result type. Not a chat/tool/provider payload."""

    binding_id: str
    project_id: int
    source_class: str
    canonical_root: Path

    def __post_init__(self) -> None:
        if not self.binding_id:
            raise ValueError("binding_id is required")
        if self.source_class not in BINDING_SOURCE_CLASSES:
            raise ValueError(
                f"source_class must be one of {BINDING_SOURCE_CLASSES!r}"
            )
        if not isinstance(self.canonical_root, Path):
            raise ValueError("canonical_root must be a Path")


def _resolve_symlink_aware(path: Path) -> Path:
    """Resolve ``path`` strictly and return an absolute Path.

    Falls back to ``Path.resolve(strict=False)`` when ``strict=True`` raises
    ``FileNotFoundError``. The loose path is still normalized and symlinks
    above existing components are resolved.
    """
    try:
        return path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError):
        return path.resolve(strict=False)


def _read_configured_projects_dir(
    settings: Settings | None,
) -> str | None:
    if settings is None:
        settings = get_settings()
    raw = getattr(settings, GUARDIAN_PROJECTS_DIR_CONFIG_KEY, None)
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return text


def resolve_guardian_projects_directory(
    *,
    settings: Settings | None = None,
    create: bool = False,
) -> Path | None:
    """Resolve the canonical Guardian Projects Directory path.

    Returns the absolute, symlink-resolved path. Returns ``None`` when the
    operator/instance key ``CODEXIFY_GUARDIAN_PROJECTS_DIR`` is unset.

    - Never falls back to ``Path.cwd()``, ``~``, ``./data``, the source
      checkout, or any container path.
    - Does not detect ``.git`` or scan the filesystem.
    - Does not create the directory unless ``create=True`` is explicitly
      passed by an authority-side caller.
    - Rejects the configured path when it exists as a non-directory file.
    """
    configured = _read_configured_projects_dir(settings)
    if configured is None:
        return None

    expanded = Path(configured).expanduser()
    if not expanded.is_absolute():
        raise GuardianProjectsDirectoryNotAbsolute(
            "CODEXIFY_GUARDIAN_PROJECTS_DIR must be an absolute host path."
        )
    try:
        canonical = expanded.resolve(strict=False)
    except RuntimeError as exc:  # pragma: no cover - symlink loop edge
        raise GuardianProjectsDirectoryUnconfigured() from exc

    if not canonical.exists():
        if not create:
            return canonical
        canonical.mkdir(parents=True, exist_ok=False)
        return _resolve_symlink_aware(canonical)

    canonical = _resolve_symlink_aware(canonical)
    if not canonical.is_dir():
        raise GuardianProjectsDirectoryNotDirectory(
            f"Guardian Projects Directory {canonical!s} exists but is not a "
            "directory."
        )
    return canonical


def guardian_managed_project_path(
    project_id: int,
    *,
    settings: Settings | None = None,
    managed_root: Path | None = None,
    create_root: bool = False,
    create_child: bool = False,
) -> Path:
    """Return the canonical on-disk path for a guardian_managed binding.

    The path is derived from a stable opaque Project ID, never from a
    mutable Project display name. The returned path is guaranteed to be
    beneath the resolved Guardian Projects Directory. Traversal and
    symlink escape fail closed. The directory is not created unless
    ``create_child=True`` is passed by an authority-side caller.
    """
    if not isinstance(project_id, int) or project_id <= 0:
        raise ValueError("project_id must be a positive integer")

    if managed_root is None:
        managed_root = resolve_guardian_projects_directory(
            settings=settings, create=create_root
        )
    if managed_root is None:
        raise GuardianProjectsDirectoryUnconfigured()
    managed_root = managed_root.expanduser()
    if not managed_root.is_absolute():
        raise GuardianProjectsDirectoryNotAbsolute(
            "Guardian Projects Directory must be an absolute host path."
        )
    if not managed_root.exists():
        if create_root:
            managed_root.mkdir(parents=True, exist_ok=False)
        else:
            raise GuardianProjectsDirectoryNotDirectory(
                f"Guardian Projects Directory {managed_root!s} does not exist."
            )
    canonical_root = _resolve_symlink_aware(managed_root)
    if not canonical_root.is_dir():
        raise GuardianProjectsDirectoryNotDirectory(
            f"Guardian Projects Directory {canonical_root!s} exists but "
            "is not a directory."
        )

    child = canonical_root / str(project_id)
    canonical_child = _resolve_symlink_aware(child)

    try:
        canonical_child.relative_to(canonical_root)
    except ValueError as exc:
        raise ManagedRootSymlinkEscape(
            f"Managed child {canonical_child!s} escapes {canonical_root!s}"
        ) from exc

    if canonical_child.exists() or canonical_child.is_symlink():
        if canonical_child.is_symlink():
            target = canonical_child.resolve(strict=False)
            try:
                target.relative_to(canonical_root)
            except ValueError as exc:
                raise ManagedRootSymlinkEscape(
                    f"Managed child {canonical_child!s} symlink-escapes to "
                    f"{target!s}"
                ) from exc
        if not canonical_child.is_dir():
            raise GuardianProjectsDirectoryNotDirectory(
                f"Managed child {canonical_child!s} exists but is not a "
                "directory."
            )
    elif create_child:
        canonical_child.mkdir(parents=True, exist_ok=False)
        canonical_child = _resolve_symlink_aware(canonical_child)

    return canonical_child


def validate_git_working_tree_root(
    candidate: Path | str,
    *,
    timeout_seconds: float = DEFAULT_GIT_VALIDATION_TIMEOUT_SECONDS,
    git_binary: str | None = None,
) -> Path:
    """Return the canonical Git top-level for ``candidate`` or fail closed.

    Executes only ``git -C <root> rev-parse --show-toplevel`` with argv-only
    invocation (no ``shell=True``) and ``GIT_OPTIONAL_LOCKS=0``. The
    returned path must equal the requested canonical root exactly. Nested
    subdirectories of a Git worktree are rejected because the canonical
    root returned by git would not match the requested path.
    """
    if isinstance(candidate, str):
        candidate_path = Path(candidate)
    else:
        candidate_path = candidate

    if not candidate_path.exists():
        raise InvalidRepositoryRoot(
            f"Repository root {candidate_path!s} does not exist."
        )
    if not candidate_path.is_dir():
        raise InvalidRepositoryRoot(
            f"Repository root {candidate_path!s} is not a directory."
        )

    canonical_requested = _resolve_symlink_aware(candidate_path)

    binary = git_binary or shutil.which("git") or "git"
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"

    try:
        completed = subprocess.run(
            [binary, "-C", str(canonical_requested), "rev-parse",
             "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitValidationError(
            f"git rev-parse timed out after {timeout_seconds}s for "
            f"{canonical_requested!s}"
        ) from exc
    except OSError as exc:
        raise GitValidationError(
            f"git invocation failed for {canonical_requested!s}: {exc}"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise InvalidRepositoryRoot(
            f"git rev-parse failed for {canonical_requested!s} "
            f"(rc={completed.returncode}): {stderr[:300]}"
        )

    stdout = (completed.stdout or "").strip()
    if not stdout:
        raise InvalidRepositoryRoot(
            f"git rev-parse returned empty stdout for "
            f"{canonical_requested!s}"
        )

    git_root = Path(stdout.splitlines()[-1].strip())
    canonical_git_root = _resolve_symlink_aware(git_root)

    if canonical_git_root != canonical_requested:
        # When ``canonical_requested`` is beneath ``canonical_git_root`` the
        # caller asked for a subdirectory of an existing Git root, which is
        # exactly the nested-repository case that must fail closed.
        try:
            canonical_requested.relative_to(canonical_git_root)
        except ValueError:
            # Not nested — but still not an exact match. Treat as invalid.
            raise InvalidRepositoryRoot(
                f"Git top-level {canonical_git_root!s} does not match "
                f"requested root {canonical_requested!s}"
            ) from None
        raise NestedRepositoryRejected(
            f"Nested repository subdirectory rejected: "
            f"requested {canonical_requested!s} lies inside Git root "
            f"{canonical_git_root!s}"
        )

    return canonical_git_root


def _coerce_provenance(
    provenance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Normalize a bounded provenance mapping to a JSONB-safe dict.

    Caller-supplied provenance is never trusted to grant authority. Only
    bounded registration metadata is permitted. The structure is
    deliberately shallow and serializable.
    """
    if provenance is None:
        return {}
    if not isinstance(provenance, Mapping):
        raise InvalidRepositoryBindingProvenance(
            "provenance must be a mapping or None"
        )

    normalized = {str(key): value for key, value in provenance.items()}
    unexpected = set(normalized) - PROVENANCE_ALLOWED_KEYS
    if unexpected:
        raise InvalidRepositoryBindingProvenance(
            "provenance contains unsupported keys: "
            f"{sorted(unexpected)!r}"
        )

    for key in ("registration_source", "operation_class"):
        value = normalized.get(key)
        if value is not None and (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > PROVENANCE_MAX_VALUE_LENGTH
        ):
            raise InvalidRepositoryBindingProvenance(
                f"provenance {key} must be a nonempty bounded string"
            )

    context = normalized.get("authority_context")
    if context is not None:
        if not isinstance(context, Mapping):
            raise InvalidRepositoryBindingProvenance(
                "authority_context must be a mapping"
            )
        if len(context) > PROVENANCE_MAX_CONTEXT_ITEMS:
            raise InvalidRepositoryBindingProvenance(
                "authority_context exceeds the bounded item limit"
            )
        normalized_context: dict[str, str | int | float | bool | None] = {}
        for raw_key, value in context.items():
            key = str(raw_key)
            if not key or len(key) > PROVENANCE_MAX_KEY_LENGTH:
                raise InvalidRepositoryBindingProvenance(
                    "authority_context keys must be bounded nonempty strings"
                )
            if isinstance(value, str):
                if len(value) > PROVENANCE_MAX_VALUE_LENGTH:
                    raise InvalidRepositoryBindingProvenance(
                        "authority_context string value exceeds the limit"
                    )
            elif not isinstance(value, (int, float, bool)) and value is not None:
                raise InvalidRepositoryBindingProvenance(
                    "authority_context values must be JSON scalar values"
                )
            normalized_context[key] = value
        normalized["authority_context"] = normalized_context

    serialized = repr(normalized).encode("utf-8")
    if len(serialized) > PROVENANCE_MAX_SERIALIZED_BYTES:
        raise InvalidRepositoryBindingProvenance(
            "provenance exceeds the bounded storage limit"
        )
    return normalized


def _load_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise ProjectNotFound(
            f"Project id={project_id} does not exist."
        )
    return project


def _verify_account_ownership(
    project: Project,
    authenticated_account_id: str | None,
) -> None:
    if not authenticated_account_id:
        raise AccountProjectMismatch(
            "Authenticated account identity is required."
        )
    if str(project.user_id) != str(authenticated_account_id):
        raise AccountProjectMismatch(
            "Authenticated account does not own Project "
            f"id={project.id}."
        )


def _ensure_supported_source_class(source_class: str) -> None:
    if source_class == DISCOVERY_CANDIDATE_CLASS:
        raise UnsupportedSourceClass(
            "discovery_candidate is not a binding source class."
        )
    if source_class not in BINDING_SOURCE_CLASSES:
        raise UnsupportedSourceClass(
            f"Unsupported source class: {source_class!r}. Expected one of "
            f"{BINDING_SOURCE_CLASSES!r}."
        )


def _ensure_managed_containment(
    *,
    source_class: str,
    canonical_root: Path,
    settings: Settings | None,
) -> None:
    if source_class != SOURCE_CLASS_GUARDIAN_MANAGED:
        return
    managed_root = resolve_guardian_projects_directory(settings=settings)
    if managed_root is None:
        raise GuardianProjectsDirectoryUnconfigured()
    canonical_managed_root = _resolve_symlink_aware(managed_root)
    try:
        canonical_root.relative_to(canonical_managed_root)
    except ValueError as exc:
        raise GuardianProjectsDirectoryOutsideAllowedRoot(
            f"guardian_managed root {canonical_root!s} escapes Guardian "
            f"Projects Directory {canonical_managed_root!s}"
        ) from exc
    if canonical_root == canonical_managed_root:
        raise GuardianProjectsDirectoryOutsideAllowedRoot(
            "guardian_managed root must be a child of Guardian Projects "
            f"Directory {canonical_managed_root!s}"
        )


def _count_active_bindings(session: Session, project_id: int) -> int:
    stmt = select(RepositoryBinding).where(
        RepositoryBinding.project_id == project_id,
        RepositoryBinding.is_active.is_(True),
    )
    return len(list(session.execute(stmt).scalars().all()))


def create_repository_binding(
    session: Session,
    *,
    authenticated_account_id: str | None,
    project_id: int,
    source_class: str,
    working_tree_root: Path | str,
    provenance: Mapping[str, Any] | None = None,
    settings: Settings | None = None,
    timeout_seconds: float = DEFAULT_GIT_VALIDATION_TIMEOUT_SECONDS,
) -> RepositoryBinding:
    """Create a new RepositoryBinding record (authority-side metadata).

    Caller owns the surrounding transaction. ``session.flush()`` is
    performed to assign surrogate state, but no commit is issued. Fails
    closed on every invariant violation.
    """
    project = _load_project(session, project_id)
    _verify_account_ownership(project, authenticated_account_id)
    _ensure_supported_source_class(source_class)

    canonical_root = validate_git_working_tree_root(
        working_tree_root, timeout_seconds=timeout_seconds
    )

    _ensure_managed_containment(
        source_class=source_class,
        canonical_root=canonical_root,
        settings=settings,
    )

    if _count_active_bindings(session, project_id) > 0:
        raise ActiveBindingAlreadyExists(
            f"Project id={project_id} already has an active "
            "RepositoryBinding."
        )

    now = datetime.now(timezone.utc)
    binding = RepositoryBinding(
        id=str(uuid.uuid4()),
        project_id=project_id,
        source_class=source_class,
        canonical_root=str(canonical_root),
        is_active=True,
        provenance=_coerce_provenance(provenance),
        created_at=now,
        updated_at=now,
    )
    session.add(binding)
    session.flush()
    return binding


def resolve_project_repository_binding(
    session: Session,
    *,
    authenticated_account_id: str | None,
    project_id: int,
    settings: Settings | None = None,
    timeout_seconds: float = DEFAULT_GIT_VALIDATION_TIMEOUT_SECONDS,
) -> ResolvedRepositoryBinding:
    """Resolve exactly one active RepositoryBinding for a Project.

    Fail closed on every invariant violation: missing Project, account
    mismatch, zero active bindings, multiple active bindings, inactive
    binding only, missing root, non-directory root, invalid Git root,
    stored/canonical root mismatch, managed-root escape.
    """
    project = _load_project(session, project_id)
    _verify_account_ownership(project, authenticated_account_id)

    stmt = (
        select(RepositoryBinding)
        .where(
            RepositoryBinding.project_id == project_id,
            RepositoryBinding.is_active.is_(True),
        )
        .order_by(RepositoryBinding.created_at.asc())
    )
    bindings = list(session.execute(stmt).scalars().all())
    if not bindings:
        raise BindingResolutionFailed(
            f"Project id={project_id} has no active RepositoryBinding."
        )
    if len(bindings) > 1:
        raise BindingResolutionFailed(
            f"Project id={project_id} has {len(bindings)} active "
            "RepositoryBindings; ambiguous resolution fails closed."
        )

    binding = bindings[0]
    _ensure_supported_source_class(binding.source_class)
    canonical_root = validate_git_working_tree_root(
        binding.canonical_root, timeout_seconds=timeout_seconds
    )

    _ensure_managed_containment(
        source_class=binding.source_class,
        canonical_root=canonical_root,
        settings=settings,
    )

    if str(canonical_root) != str(binding.canonical_root):
        raise BindingResolutionFailed(
            "Stored canonical root does not match observed Git top-level "
            f"({binding.canonical_root!s} vs {canonical_root!s})."
        )

    return ResolvedRepositoryBinding(
        binding_id=binding.id,
        project_id=project_id,
        source_class=binding.source_class,
        canonical_root=canonical_root,
    )
