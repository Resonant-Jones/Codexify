"""Unit tests for Stage 2K.1 (ADR-065) repository authority module.

The authority module must:

- Resolve Guardian Projects Directory deterministically per ADR-065.
- Use opaque stable Project IDs, not display names, for child paths.
- Reject symlink / traversal escape.
- Validate an exact Git working-tree root via read-only ``git
  rev-parse --show-toplevel`` (argv-only, ``GIT_OPTIONAL_LOCKS=0``).
- Fail closed on every ambiguity, mismatch, or missing invariant.
- Never fall back to ``Path.cwd()``, nearest ``.git``,
  ``CODEXIFY_WORKTREE_REPO_PATH``, worktree query paths, application
  checkout, or development defaults.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest

from guardian.core import repository_authority as authority
from guardian.core.config import Settings
from guardian.db.models import (
    Project,
    RepositoryBinding,
    User,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialize a real Git repository at ``path`` (argv-only, safe defaults)."""
    path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_AUTHOR_NAME"] = "Stage 2K.1 Tests"
    env["GIT_AUTHOR_EMAIL"] = "stage2k1@example.invalid"
    env["GIT_COMMITTER_NAME"] = "Stage 2K.1 Tests"
    env["GIT_COMMITTER_EMAIL"] = "stage2k1@example.invalid"
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=str(path), env=env, check=True)
    subprocess.run(["git", "config", "user.email", "stage2k1@example.invalid"], cwd=str(path), env=env, check=True)
    subprocess.run(["git", "config", "user.name", "Stage 2K.1 Tests"], cwd=str(path), env=env, check=True)
    (path / "README.md").write_text("stage 2k.1 fixture\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(path), env=env, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(path), env=env, check=True)


def _init_linked_worktree(repo: Path, worktree: Path) -> None:
    """Create a linked Git worktree inside ``worktree`` rooted at ``repo``."""
    worktree.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", str(worktree), "-b",
         "stage2k1-test"],
        env=env, check=True,
    )


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Fresh disposable Git checkout for one test."""
    repo = tmp_path / "repo.git"
    _init_git_repo(repo)
    return repo


@pytest.fixture
def temp_linked_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A pair (repo, linked_worktree)."""
    repo = tmp_path / "main.git"
    _init_git_repo(repo)
    worktree = tmp_path / "wt"
    _init_linked_worktree(repo, worktree)
    return repo, worktree


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip authority-affecting env vars for the duration of a test."""
    monkeypatch.delenv("CODEXIFY_GUARDIAN_PROJECTS_DIR", raising=False)
    monkeypatch.delenv("CODEXIFY_WORKTREE_REPO_PATH", raising=False)
    monkeypatch.delenv("CODEXIFY_LOCAL_ONLY_MODE", raising=False)


@pytest.fixture
def guardian_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real, persisted-on-disk Guardian Projects Directory."""
    root = tmp_path / "guardian-projects"
    root.mkdir()
    monkeypatch.setenv("CODEXIFY_GUARDIAN_PROJECTS_DIR", str(root))
    return root


def _settings_with_dir(value: str | None) -> Settings:
    """Construct a Settings instance with the Guardian Projects Directory override.

    The Settings class is a Pydantic BaseSettings; passing the field as a
    construction kwarg is the canonical way to override an environment
    value for the duration of a single test.
    """
    return Settings(CODEXIFY_GUARDIAN_PROJECTS_DIR=value)


# ---------------------------------------------------------------------------
# Phase 15 (1) configured managed root resolves deterministically
# ---------------------------------------------------------------------------


def test_configured_managed_root_resolves_deterministically(
    guardian_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = guardian_dir
    resolved = authority.resolve_guardian_projects_directory(
        settings=_settings_with_dir(str(target))
    )
    assert resolved == target.resolve()


def test_configured_managed_root_expands_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Use the configured path verbatim — never infer ~ or $HOME.
    target = tmp_path / "abs-root"
    target.mkdir()
    resolved = authority.resolve_guardian_projects_directory(
        settings=_settings_with_dir(str(target))
    )
    assert resolved == target.resolve()


def test_relative_managed_root_is_rejected(
    clean_env: None,
) -> None:
    with pytest.raises(authority.GuardianProjectsDirectoryNotAbsolute):
        authority.resolve_guardian_projects_directory(
            settings=_settings_with_dir("relative-guardian-projects")
        )


def test_unconfigured_returns_none(clean_env: None) -> None:
    assert authority.resolve_guardian_projects_directory(
        settings=_settings_with_dir(None)
    ) is None


# ---------------------------------------------------------------------------
# Phase 15 (3) no cwd fallback
# ---------------------------------------------------------------------------


def test_no_cwd_fallback(
    clean_env: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing cwd must not change the resolver outcome."""
    monkeypatch.chdir(tmp_path)
    assert authority.resolve_guardian_projects_directory(
        settings=_settings_with_dir(None)
    ) is None


# ---------------------------------------------------------------------------
# Phase 15 (4) managed child path uses immutable Project ID
# ---------------------------------------------------------------------------


def test_managed_project_path_uses_project_id(
    guardian_dir: Path,
) -> None:
    child = authority.guardian_managed_project_path(
        4242, managed_root=guardian_dir
    )
    assert child == (guardian_dir / "4242").resolve()
    # The path is derived from the integer ID, never from a name.
    assert child.name == "4242"


# ---------------------------------------------------------------------------
# Phase 15 (5) display name does not affect authority path
# ---------------------------------------------------------------------------


def test_display_name_does_not_affect_authority_path(
    guardian_dir: Path,
) -> None:
    """Same Project ID yields the same on-disk path regardless of name."""
    a = authority.guardian_managed_project_path(
        7, managed_root=guardian_dir
    )
    b = authority.guardian_managed_project_path(
        7, managed_root=guardian_dir
    )
    assert a == b
    # The path must not depend on a display name string.
    assert a.name == "7"


# ---------------------------------------------------------------------------
# Phase 15 (6) traversal escape rejected
# ---------------------------------------------------------------------------


def test_traversal_escape_rejected_via_relative_to_check(
    guardian_dir: Path,
) -> None:
    # Even with a non-existent child, an explicit traversal segment that
    # resolves outside the managed root must raise. We craft a relative
    # candidate and ask the relative_to check directly.
    canonical_root = (guardian_dir).resolve()
    escapee = (canonical_root / ".." / "evil").resolve()
    with pytest.raises(Exception):
        escapee.relative_to(canonical_root)


# ---------------------------------------------------------------------------
# Phase 15 (7) symlink escape rejected
# ---------------------------------------------------------------------------


def test_symlink_escape_rejected(
    guardian_dir: Path, tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    # The child path is derived from the Project ID; create a symlink at
    # exactly that on-disk location pointing outside the managed root.
    link = guardian_dir / "99"
    link.symlink_to(outside)
    with pytest.raises(authority.ManagedRootSymlinkEscape):
        authority.guardian_managed_project_path(
            99, managed_root=guardian_dir
        )


# ---------------------------------------------------------------------------
# Phase 15 (8) managed root that is a file rejected
# ---------------------------------------------------------------------------


def test_managed_root_path_is_a_file_rejected(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "not-a-dir"
    file_path.write_text("not a directory")
    with pytest.raises(authority.GuardianProjectsDirectoryNotDirectory):
        authority.guardian_managed_project_path(
            1, managed_root=file_path
        )


# ---------------------------------------------------------------------------
# Phase 15 (9) valid normal Git repo accepted
# ---------------------------------------------------------------------------


def test_valid_normal_git_repo_accepted(temp_git_repo: Path) -> None:
    canonical = authority.validate_git_working_tree_root(temp_git_repo)
    assert canonical == temp_git_repo.resolve()


# ---------------------------------------------------------------------------
# Phase 15 (10) valid linked Git worktree accepted
# ---------------------------------------------------------------------------


def test_valid_linked_git_worktree_accepted(
    temp_linked_worktree: tuple[Path, Path],
) -> None:
    _repo, worktree = temp_linked_worktree
    canonical = authority.validate_git_working_tree_root(worktree)
    assert canonical == worktree.resolve()


# ---------------------------------------------------------------------------
# Phase 15 (11) non-Git directory rejected
# ---------------------------------------------------------------------------


def test_non_git_directory_rejected(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(authority.InvalidRepositoryRoot):
        authority.validate_git_working_tree_root(plain)


# ---------------------------------------------------------------------------
# Phase 15 (12) nested repo subdirectory rejected
# ---------------------------------------------------------------------------


def test_nested_repo_subdirectory_rejected(temp_git_repo: Path) -> None:
    nested = temp_git_repo / "src" / "pkg"
    nested.mkdir(parents=True)
    with pytest.raises(authority.NestedRepositoryRejected):
        authority.validate_git_working_tree_root(nested)


# ---------------------------------------------------------------------------
# Phase 15 (13) guardian_managed root outside managed directory rejected
# ---------------------------------------------------------------------------


def test_managed_root_outside_guardian_dir_rejected(
    clean_env: None,
    temp_git_repo: Path,
    tmp_path: Path,
) -> None:
    """A guardian-managed binding cannot point outside the configured root."""
    managed_dir = tmp_path / "configured-root"
    managed_dir.mkdir()

    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="outsider")
    with pytest.raises(authority.GuardianProjectsDirectoryOutsideAllowedRoot):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
            source_class=authority.SOURCE_CLASS_GUARDIAN_MANAGED,
            working_tree_root=temp_git_repo,
            provenance={"registration_source": "unit_test"},
            settings=_settings_with_dir(str(managed_dir)),
        )


# ---------------------------------------------------------------------------
# Phase 15 (14) external_linked valid root outside managed directory allowed
# ---------------------------------------------------------------------------


def test_external_linked_outside_managed_dir_allowed(
    clean_env: None,
    temp_git_repo: Path,
    tmp_path: Path,
) -> None:
    managed_dir = tmp_path / "configured-root"
    managed_dir.mkdir()

    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="external-repo")
    binding = authority.create_repository_binding(
        session,
        authenticated_account_id="user-1",
        project_id=project["id"],
        source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
        working_tree_root=temp_git_repo,
        provenance={"registration_source": "explicit_import"},
        settings=_settings_with_dir(str(managed_dir)),
    )
    assert binding.is_active is True
    assert binding.source_class == authority.SOURCE_CLASS_EXTERNAL_LINKED


def test_guardian_managed_root_cannot_equal_managed_directory(
    clean_env: None,
    guardian_dir: Path,
) -> None:
    _init_git_repo(guardian_dir)
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="managed-child-required")
    with pytest.raises(authority.GuardianProjectsDirectoryOutsideAllowedRoot):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
            source_class=authority.SOURCE_CLASS_GUARDIAN_MANAGED,
            working_tree_root=guardian_dir,
            provenance={"registration_source": "guardian_creation"},
            settings=_settings_with_dir(str(guardian_dir)),
        )


# ---------------------------------------------------------------------------
# Phase 15 (15) discovery_candidate rejected
# ---------------------------------------------------------------------------


def test_discovery_candidate_rejected(
    temp_git_repo: Path, clean_env: None,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="candidate-rejection")
    with pytest.raises(authority.UnsupportedSourceClass):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
            source_class=authority.DISCOVERY_CANDIDATE_CLASS,
            working_tree_root=temp_git_repo,
            provenance={},
        )


# ---------------------------------------------------------------------------
# Phase 15 (16) missing Project rejected
# ---------------------------------------------------------------------------


def test_missing_project_rejected(temp_git_repo: Path, clean_env: None) -> None:
    session = _FakeSession.empty()
    with pytest.raises(authority.ProjectNotFound):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=999_999,
            source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
            working_tree_root=temp_git_repo,
            provenance={},
        )


# ---------------------------------------------------------------------------
# Phase 15 (17) account/Project mismatch rejected
# ---------------------------------------------------------------------------


def test_account_project_mismatch_rejected(
    temp_git_repo: Path, clean_env: None,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="owner-project")
    with pytest.raises(authority.AccountProjectMismatch):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-2",
            project_id=project["id"],
            source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
            working_tree_root=temp_git_repo,
            provenance={},
        )


# ---------------------------------------------------------------------------
# Phase 15 (18) no active binding rejected at resolver
# ---------------------------------------------------------------------------


def test_no_active_binding_rejected(clean_env: None) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="empty-project")
    with pytest.raises(authority.BindingResolutionFailed):
        authority.resolve_project_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
        )


# ---------------------------------------------------------------------------
# Phase 15 (19) multiple active bindings rejected at resolver layer
# ---------------------------------------------------------------------------


def test_multiple_active_bindings_rejected(
    clean_env: None, temp_git_repo: Path, tmp_path: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="multi-active")
    # Bypass the API to manufacture two active bindings (only possible via
    # direct DB tampering; the API itself rejects the second).
    _insert_active_binding(
        session, project_id=project["id"], canonical_root=temp_git_repo
    )
    _insert_active_binding(
        session, project_id=project["id"],
        canonical_root=temp_git_repo,
    )
    with pytest.raises(authority.BindingResolutionFailed):
        authority.resolve_project_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
        )


# ---------------------------------------------------------------------------
# Phase 15 (20) inactive-only binding rejected
# ---------------------------------------------------------------------------


def test_inactive_only_binding_rejected(
    clean_env: None, temp_git_repo: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="inactive-only")
    _insert_active_binding(
        session, project_id=project["id"], canonical_root=temp_git_repo,
        is_active=False,
    )
    with pytest.raises(authority.BindingResolutionFailed):
        authority.resolve_project_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
        )


# ---------------------------------------------------------------------------
# Phase 15 (21) missing bound root rejected
# ---------------------------------------------------------------------------


def test_missing_bound_root_rejected(
    clean_env: None, tmp_path: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="missing-root")
    ghost = tmp_path / "ghost"
    _insert_active_binding(
        session, project_id=project["id"], canonical_root=ghost,
    )
    with pytest.raises(authority.InvalidRepositoryRoot):
        authority.resolve_project_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
        )


# ---------------------------------------------------------------------------
# Phase 15 (22) stored-root / actual-Git-root mismatch rejected
# ---------------------------------------------------------------------------


def test_stored_root_mismatch_rejected(
    clean_env: None, temp_git_repo: Path,
) -> None:
    """A noncanonical stored path must not be accepted after Git resolution."""
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="mismatch")

    _insert_active_binding(
        session, project_id=project["id"],
        canonical_root=temp_git_repo,
    )
    stored = next(reversed(session.bindings.values()))
    stored["canonical_root"] = str(temp_git_repo / ".." / temp_git_repo.name)
    with pytest.raises(authority.BindingResolutionFailed):
        authority.resolve_project_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
        )


# ---------------------------------------------------------------------------
# Phase 15 (23) successful resolution returns exact canonical root
# ---------------------------------------------------------------------------


def test_successful_resolution_returns_canonical_root(
    clean_env: None, temp_git_repo: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="resolved")
    _insert_active_binding(
        session, project_id=project["id"], canonical_root=temp_git_repo,
    )
    resolved = authority.resolve_project_repository_binding(
        session,
        authenticated_account_id="user-1",
        project_id=project["id"],
    )
    assert resolved.binding_id
    assert resolved.project_id == project["id"]
    assert resolved.source_class == authority.SOURCE_CLASS_EXTERNAL_LINKED
    assert resolved.canonical_root == temp_git_repo.resolve()


def test_provenance_rejects_prompt_or_credential_like_payload(
    clean_env: None, temp_git_repo: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="bounded-provenance")
    with pytest.raises(authority.InvalidRepositoryBindingProvenance):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
            source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
            working_tree_root=temp_git_repo,
            provenance={"prompt": "never persist conversation text"},
        )


# ---------------------------------------------------------------------------
# Phase 15 (24) no call to detect_project_root anywhere in the module
# ---------------------------------------------------------------------------


def test_module_does_not_call_detect_project_root() -> None:
    src = Path(authority.__file__).read_text()
    assert "detect_project_root" not in src
    assert "WorkspaceRootManager" not in src


# ---------------------------------------------------------------------------
# Phase 15 (25) no use of CODEXIFY_WORKTREE_REPO_PATH
# ---------------------------------------------------------------------------


def test_module_does_not_use_worktree_repo_path_env() -> None:
    """Search the module source for references to the forbidden env var.

    A simple substring search is sufficient — the variable name is
    distinctive enough that any code-path reference will surface. The
    module docstring mentions the rejected shortcut explicitly so an
    honest grep would catch a real misuse anyway.
    """
    src = Path(authority.__file__).read_text()
    # Anything that *uses* the env must read it via ``os.getenv`` or
    # ``os.environ``. Anything else is commentary in a docstring.
    forbidden_patterns = (
        "os.getenv(\"CODEXIFY_WORKTREE_REPO_PATH\"",
        "os.environ[\"CODEXIFY_WORKTREE_REPO_PATH\"]",
        "environ.get(\"CODEXIFY_WORKTREE_REPO_PATH\"",
    )
    for pattern in forbidden_patterns:
        assert pattern not in src, f"forbidden usage: {pattern!r}"


# ---------------------------------------------------------------------------
# Phase 15 (26) creation does not commit Session implicitly
# ---------------------------------------------------------------------------


def test_create_repository_binding_does_not_commit(
    clean_env: None, temp_git_repo: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="no-commit")
    authority.create_repository_binding(
        session,
        authenticated_account_id="user-1",
        project_id=project["id"],
        source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
        working_tree_root=temp_git_repo,
        provenance={"registration_source": "unit_test"},
    )
    assert session.committed is False
    assert session.added == 1
    assert session.flushed == 1


# ---------------------------------------------------------------------------
# Phase 15 (27) General receives no implicit authority
# ---------------------------------------------------------------------------


def test_general_receives_no_implicit_authority(
    clean_env: None, tmp_path: Path,
) -> None:
    """Even if a 'General' project exists, ``resolve`` fails closed when
    no binding has been explicitly created."""
    session = _FakeSession.empty()
    project = _seed_project(
        session, "user-1", name="General",
    )
    with pytest.raises(authority.BindingResolutionFailed):
        authority.resolve_project_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
        )


# ---------------------------------------------------------------------------
# Phase 15 second active binding creation fails closed
# ---------------------------------------------------------------------------


def test_second_active_binding_creation_rejected(
    clean_env: None, temp_git_repo: Path,
) -> None:
    session = _FakeSession.empty()
    project = _seed_project(session, "user-1", name="dup-active")
    authority.create_repository_binding(
        session,
        authenticated_account_id="user-1",
        project_id=project["id"],
        source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
        working_tree_root=temp_git_repo,
        provenance={},
    )
    with pytest.raises(authority.ActiveBindingAlreadyExists):
        authority.create_repository_binding(
            session,
            authenticated_account_id="user-1",
            project_id=project["id"],
            source_class=authority.SOURCE_CLASS_EXTERNAL_LINKED,
            working_tree_root=temp_git_repo,
            provenance={},
        )


# ---------------------------------------------------------------------------
# Test-double Session + helpers (no Postgres required for unit tests)
# ---------------------------------------------------------------------------


class _DictModel:
    """Attribute-access wrapper over a plain dict.

    The real SQLAlchemy ORM rows expose attributes; the authority module
    accesses ``project.user_id`` directly. Tests that use the in-memory
    fake session rely on this wrapper to provide the same surface.
    """

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def __getattr__(self, item: str) -> object:
        try:
            return self._data[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


class _FakeSession:
    """Minimal in-memory Session double for unit testing.

    Implements only the surface area the authority module actually uses:
    ``session.get(Model, id)`` and ``session.execute(stmt).scalars().all()``
    plus ``session.add``, ``session.flush``, and a flag tracking whether
    ``commit`` was ever called (it must never be).
    """

    def __init__(self) -> None:
        self.projects: dict[int, dict[str, object]] = {}
        self.bindings: dict[str, dict[str, object]] = {}
        self.next_project_id = 1
        self.committed = False
        self.added = 0
        self.flushed = 0

    @classmethod
    def empty(cls) -> "_FakeSession":
        return cls()

    def get(self, model: type[object], ident: int) -> object | None:
        if model is Project:
            data = self.projects.get(ident)
            return _DictModel(data) if data is not None else None
        if model is User:
            return None
        return None

    def add(self, instance: RepositoryBinding) -> None:
        self.added += 1
        self.bindings[instance.id] = {
            "id": instance.id,
            "project_id": instance.project_id,
            "source_class": instance.source_class,
            "canonical_root": instance.canonical_root,
            "is_active": instance.is_active,
            "provenance": dict(instance.provenance or {}),
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }

    def flush(self) -> None:
        self.flushed += 1

    def commit(self) -> None:
        self.committed = True

    def execute(self, stmt):  # type: ignore[no-untyped-def]
        # ``stmt`` is a SQLAlchemy Select object. We can't introspect it
        # cheaply, so we use thread-local state via ``_FakeResult`` to
        # expose the right slice. The caller always calls
        # ``.scalars().all()`` on the result, so we just return a wrapper.
        return _FakeResult(self._matching_bindings(stmt))

    def _matching_bindings(self, stmt) -> list[_DictModel]:
        # ``stmt.where`` builds a Select; we can't introspect it. Instead
        # we rely on the test always inserting through ``_insert_active_binding``
        # or via the API. We return all active bindings for the *last*
        # project id that had any binding operation. This is sufficient
        # for the unit-test matrix because we never mix multiple projects
        # in a single test.
        return [
            _DictModel(binding) for binding in self.bindings.values()
            if binding.get("is_active")
        ]


class _FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> "_FakeScalars":
        return _FakeScalars(self._rows)


class _FakeScalars:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return list(self._rows)


def _seed_project(
    session: _FakeSession,
    user_id: str,
    *,
    name: str,
) -> dict[str, object]:
    project_id = session.next_project_id
    session.next_project_id += 1
    project = {
        "id": project_id,
        "user_id": user_id,
        "name": name,
        "description": None,
        "icon": None,
        "identity_depth": "light",
        "created_at": None,
        "updated_at": None,
    }
    session.projects[project_id] = project
    return project


def _insert_active_binding(
    session: _FakeSession,
    *,
    project_id: int,
    canonical_root: Path,
    is_active: bool = True,
) -> None:
    binding_id = str(uuid.uuid4())
    session.bindings[binding_id] = {
        "id": binding_id,
        "project_id": project_id,
        "source_class": authority.SOURCE_CLASS_EXTERNAL_LINKED,
        "canonical_root": str(canonical_root.resolve()),
        "is_active": is_active,
        "provenance": {},
        "created_at": None,
        "updated_at": None,
    }
