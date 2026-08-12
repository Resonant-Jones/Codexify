"""Explicit repository candidate import (Stage 2K.3 / ADR-065).

This module promotes one freshly rediscovered, authenticated-user-selected
repository candidate into durable Project-to-RepositoryBinding authority.  It
does not move repository files, expose a model/tool payload, or own a database
transaction.  The HTTP route is responsible for authentication transport and
commit or rollback.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from guardian.core.repository_authority import (
    ActiveBindingAlreadyExists,
    AccountProjectMismatch,
    DISCOVERY_CANDIDATE_CLASS,
    ProjectNotFound,
    RepositoryAuthorityError,
    RepositoryBinding,
    SOURCE_CLASS_EXTERNAL_LINKED,
    create_repository_binding,
    validate_git_working_tree_root,
)
from guardian.core.repository_discovery import (
    RepositoryDiscoveryCandidate,
    authorize_explicit_discovery_root,
    discover_repository_candidates,
)
from guardian.db.models import Project


PROJECT_NAME_MAX_LENGTH = 255
PROJECT_DESCRIPTION_MAX_LENGTH = 4096
IMPORT_REGISTRATION_SOURCE = "repository_candidate_import"
IMPORT_OPERATION_CLASS = "external_link"


class RepositoryImportError(Exception):
    """Base class for bounded repository-import failures."""


class InvalidImportTarget(RepositoryImportError):
    """The caller did not select exactly one valid Project target."""


class CandidateActorMismatch(RepositoryImportError):
    """A discovery candidate belongs to a different authenticated actor."""


class CandidateNotFound(RepositoryImportError):
    """The requested relative candidate was absent from a fresh scan."""


class CandidateRevalidationFailed(RepositoryImportError):
    """The observed candidate no longer resolves to the same Git root."""


class RepositoryAlreadyLinked(RepositoryImportError):
    """A root is already linked to a different Project for this account."""


class RepositoryBindingAmbiguous(RepositoryImportError):
    """Multiple active bindings resolve to one canonical working-tree root."""


class RepositoryBindingOwnedByAnotherAccount(RepositoryImportError):
    """A root is already linked under another account."""


@dataclass(frozen=True)
class RepositoryImportResult:
    """Bounded result for the authenticated API layer, never a tool payload."""

    project_id: int
    binding_id: str
    created_project: bool
    reused_existing: bool
    source_class: str = SOURCE_CLASS_EXTERNAL_LINKED

    def __post_init__(self) -> None:
        if self.source_class != SOURCE_CLASS_EXTERNAL_LINKED:
            raise ValueError("repository imports must be external_linked")


@dataclass(frozen=True)
class _ImportTarget:
    project_id: int | None
    project_name: str | None
    project_description: str | None

    @property
    def creates_project(self) -> bool:
        return self.project_id is None


def _require_authenticated_account_id(
    authenticated_account_id: str | None,
) -> str:
    account_id = str(authenticated_account_id or "").strip()
    if not account_id:
        raise InvalidImportTarget("authenticated account identity is required")
    return account_id


def _normalize_candidate_selector(candidate_relative_path: str) -> str:
    """Return one safe POSIX relative candidate token without traversal."""
    raw = str(candidate_relative_path or "").strip()
    if not raw or "\\" in raw:
        raise InvalidImportTarget("candidate selector must be a POSIX path")

    selector = PurePosixPath(raw)
    if selector.is_absolute() or ".." in selector.parts:
        raise InvalidImportTarget("candidate selector must stay below root")

    normalized = selector.as_posix()
    if not normalized or normalized == "..":
        raise InvalidImportTarget("candidate selector is invalid")
    return normalized


def _validate_import_target(
    *,
    project_id: int | None,
    project_name: str | None,
    project_description: str | None,
) -> _ImportTarget:
    if project_id is not None and (
        not isinstance(project_id, int) or isinstance(project_id, bool) or project_id <= 0
    ):
        raise InvalidImportTarget("project_id must be a positive integer")
    if project_id is not None and project_name is not None:
        raise InvalidImportTarget("select an existing Project or a new Project")
    if project_id is not None:
        if project_description is not None:
            raise InvalidImportTarget(
                "project_description is valid only for a new Project"
            )
        return _ImportTarget(
            project_id=project_id,
            project_name=None,
            project_description=None,
        )

    name = str(project_name or "").strip()
    if not name:
        raise InvalidImportTarget("new Project name is required")
    if len(name) > PROJECT_NAME_MAX_LENGTH:
        raise InvalidImportTarget("new Project name exceeds the allowed length")

    description = None
    if project_description is not None:
        description = str(project_description).strip()
        if len(description) > PROJECT_DESCRIPTION_MAX_LENGTH:
            raise InvalidImportTarget(
                "new Project description exceeds the allowed length"
            )
    return _ImportTarget(
        project_id=None,
        project_name=name,
        project_description=description,
    )


def _candidate_selector(candidate: RepositoryDiscoveryCandidate) -> str:
    relative_path = candidate.root_relative_path
    if relative_path.is_absolute():
        raise CandidateRevalidationFailed("candidate relative identity is invalid")
    if ".." in relative_path.parts:
        raise CandidateRevalidationFailed("candidate relative identity is invalid")
    return PurePosixPath(relative_path.as_posix()).as_posix()


def _find_candidate(
    candidates: tuple[RepositoryDiscoveryCandidate, ...],
    selector: str,
) -> RepositoryDiscoveryCandidate:
    matches = [
        candidate
        for candidate in candidates
        if _candidate_selector(candidate) == selector
    ]
    if not matches:
        raise CandidateNotFound("selected repository candidate was not found")
    if len(matches) != 1:
        raise CandidateRevalidationFailed(
            "selected repository candidate is ambiguous"
        )
    return matches[0]


def _load_owned_project(
    session: Session,
    *,
    project_id: int,
    authenticated_account_id: str,
) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise ProjectNotFound("Project does not exist")
    if str(project.user_id) != authenticated_account_id:
        raise AccountProjectMismatch(
            "Project does not belong to the authenticated account"
        )
    return project


def _active_bindings_for_canonical_root(
    session: Session,
    canonical_root: Path,
) -> list[tuple[RepositoryBinding, Project]]:
    statement = (
        select(RepositoryBinding, Project)
        .join(Project, RepositoryBinding.project_id == Project.id)
        .where(
            RepositoryBinding.is_active.is_(True),
            RepositoryBinding.canonical_root == str(canonical_root),
        )
    )
    return list(session.execute(statement).all())


def _candidate_provenance(
    candidate: RepositoryDiscoveryCandidate,
) -> dict[str, Any]:
    """Build the Stage 2K.1 bounded provenance payload without paths."""
    return {
        "registration_source": IMPORT_REGISTRATION_SOURCE,
        "operation_class": IMPORT_OPERATION_CLASS,
        "authority_context": {
            "discovery_provenance_class": (
                candidate.discovery_root_provenance_class
            ),
            "git_evidence_kind": candidate.git_evidence_kind,
            "candidate_observed_at": candidate.discovered_at.isoformat(),
        },
    }


def _result_for_existing(
    binding: RepositoryBinding,
    project: Project,
) -> RepositoryImportResult:
    return RepositoryImportResult(
        project_id=int(project.id),
        binding_id=str(binding.id),
        created_project=False,
        reused_existing=True,
    )


def _revalidate_candidate(
    candidate: RepositoryDiscoveryCandidate,
    *,
    authenticated_account_id: str,
) -> Path:
    if candidate.source_class != DISCOVERY_CANDIDATE_CLASS:
        raise CandidateRevalidationFailed("candidate source class is invalid")
    if candidate.authorized_actor_id != authenticated_account_id:
        raise CandidateActorMismatch(
            "candidate does not belong to the authenticated account"
        )
    try:
        canonical_root = validate_git_working_tree_root(
            candidate.canonical_working_tree_root
        )
    except RepositoryAuthorityError as exc:
        raise CandidateRevalidationFailed(
            "candidate Git working tree could not be revalidated"
        ) from exc
    if canonical_root != candidate.canonical_working_tree_root:
        raise CandidateRevalidationFailed(
            "candidate Git working tree identity changed"
        )
    return canonical_root


def _new_project_description(
    value: str | None,
    *,
    canonical_root: Path,
) -> str | None:
    if value is None:
        return None
    if str(canonical_root) in value:
        raise InvalidImportTarget(
            "new Project description must not contain repository paths"
        )
    return value


def import_repository_candidate(
    session: Session,
    *,
    authenticated_account_id: str | None,
    candidate: RepositoryDiscoveryCandidate,
    project_id: int | None = None,
    project_name: str | None = None,
    project_description: str | None = None,
) -> RepositoryImportResult:
    """Import one actual discovery candidate in the caller-owned transaction."""
    account_id = _require_authenticated_account_id(authenticated_account_id)
    target = _validate_import_target(
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
    )
    canonical_root = _revalidate_candidate(
        candidate, authenticated_account_id=account_id
    )

    requested_project: Project | None = None
    if target.project_id is not None:
        requested_project = _load_owned_project(
            session,
            project_id=target.project_id,
            authenticated_account_id=account_id,
        )

    existing_bindings = _active_bindings_for_canonical_root(
        session, canonical_root
    )
    if len(existing_bindings) > 1:
        raise RepositoryBindingAmbiguous(
            "multiple active bindings resolve to the selected repository"
        )
    if existing_bindings:
        binding, project = existing_bindings[0]
        if str(project.user_id) != account_id:
            raise RepositoryBindingOwnedByAnotherAccount(
                "selected repository is already linked"
            )
        if target.creates_project:
            return _result_for_existing(binding, project)
        if requested_project is not None and project.id == requested_project.id:
            return _result_for_existing(binding, project)
        raise RepositoryAlreadyLinked(
            "selected repository is linked to a different Project"
        )

    created_project = False
    if requested_project is None:
        description = _new_project_description(
            target.project_description, canonical_root=canonical_root
        )
        requested_project = Project(
            user_id=account_id,
            name=target.project_name or "",
            description=description,
        )
        session.add(requested_project)
        session.flush()
        created_project = True

    binding = create_repository_binding(
        session,
        authenticated_account_id=account_id,
        project_id=int(requested_project.id),
        source_class=SOURCE_CLASS_EXTERNAL_LINKED,
        working_tree_root=canonical_root,
        provenance=_candidate_provenance(candidate),
    )
    return RepositoryImportResult(
        project_id=int(requested_project.id),
        binding_id=str(binding.id),
        created_project=created_project,
        reused_existing=False,
    )


def import_explicit_repository_candidate(
    session: Session,
    *,
    authenticated_account_id: str | None,
    discovery_root: Path | str,
    candidate_relative_path: str,
    project_id: int | None = None,
    project_name: str | None = None,
    project_description: str | None = None,
) -> RepositoryImportResult:
    """Rediscover and import one authenticated explicit-root candidate."""
    account_id = _require_authenticated_account_id(authenticated_account_id)
    _validate_import_target(
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
    )
    selector = _normalize_candidate_selector(candidate_relative_path)
    authorized_root = authorize_explicit_discovery_root(
        authorized_actor_id=account_id,
        root=discovery_root,
    )
    discovery_result = discover_repository_candidates(authorized_root)
    candidate = _find_candidate(discovery_result.candidates, selector)
    if candidate.authorized_actor_id != account_id:
        raise CandidateActorMismatch(
            "candidate does not belong to the authenticated account"
        )
    return import_repository_candidate(
        session,
        authenticated_account_id=account_id,
        candidate=candidate,
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
    )
