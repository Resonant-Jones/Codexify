from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from guardian.core import repository_import
from guardian.core.repository_authority import (
    ActiveBindingAlreadyExists,
    AccountProjectMismatch,
    SOURCE_CLASS_EXTERNAL_LINKED,
)
from guardian.core.repository_discovery import (
    DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION,
    GIT_EVIDENCE_DIRECTORY,
    AuthorizedDiscoveryRoot,
    RepositoryDiscoveryCandidate,
)
from guardian.db.models import Project


def _run_git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repository(path: Path) -> Path:
    path.mkdir(parents=True)
    _run_git("init", "--quiet", cwd=path)
    _run_git("config", "user.email", "fixture@example.invalid", cwd=path)
    _run_git("config", "user.name", "Fixture", cwd=path)
    fixture = path / "fixture.txt"
    fixture.write_text("repository import fixture\n")
    _run_git("add", "fixture.txt", cwd=path)
    _run_git("commit", "--quiet", "-m", "fixture", cwd=path)
    return path.resolve()


def _candidate(
    root: Path,
    *,
    relative: str = ".",
    actor: str = "account-a",
) -> RepositoryDiscoveryCandidate:
    return RepositoryDiscoveryCandidate(
        canonical_working_tree_root=root.resolve(),
        root_relative_path=Path(relative),
        discovery_root_provenance_class=(
            DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION
        ),
        authorized_actor_id=actor,
        git_evidence_kind=GIT_EVIDENCE_DIRECTORY,
        discovered_at=datetime.now(timezone.utc),
    )


class _FakeSession:
    def __init__(self, projects: dict[int, Project] | None = None) -> None:
        self.projects = projects or {}
        self.added: list[object] = []
        self.flush_count = 0
        self.commit_count = 0

    def get(self, model, project_id: int):
        assert model is Project
        return self.projects.get(project_id)

    def add(self, item: object) -> None:
        self.added.append(item)
        if isinstance(item, Project):
            item.id = max(self.projects, default=0) + 1
            self.projects[item.id] = item

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.commit_count += 1


def _patch_successful_binding(
    monkeypatch: pytest.MonkeyPatch,
    *,
    binding_id: str = "binding-1",
) -> dict[str, object]:
    calls: dict[str, object] = {}

    def create(session, **kwargs):
        calls.update(kwargs)
        return SimpleNamespace(id=binding_id)

    monkeypatch.setattr(repository_import, "create_repository_binding", create)
    monkeypatch.setattr(
        repository_import, "_active_bindings_for_canonical_root", lambda *_: []
    )
    return calls


@pytest.mark.parametrize("account_id", [None, "", " "])
def test_import_requires_authenticated_account_id(
    tmp_path: Path, account_id: str | None
) -> None:
    repository = _init_repository(tmp_path / "repository")
    with pytest.raises(repository_import.InvalidImportTarget):
        repository_import.import_repository_candidate(
            _FakeSession(),
            authenticated_account_id=account_id,
            candidate=_candidate(repository),
            project_name="Imported",
        )


@pytest.mark.parametrize(
    ("project_id", "project_name", "project_description"),
    [
        (1, "ambiguous", None),
        (None, None, None),
        (None, "   ", None),
        (1, None, "not valid for an existing target"),
        (0, None, None),
    ],
)
def test_target_mode_requires_exactly_one_valid_target(
    project_id: int | None,
    project_name: str | None,
    project_description: str | None,
) -> None:
    with pytest.raises(repository_import.InvalidImportTarget):
        repository_import._validate_import_target(
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
        )


@pytest.mark.parametrize(
    ("selector", "expected"),
    [(".", "."), ("nested/repository", "nested/repository")],
)
def test_safe_candidate_relative_selectors_are_accepted(
    selector: str, expected: str
) -> None:
    assert repository_import._normalize_candidate_selector(selector) == expected


@pytest.mark.parametrize("selector", ["", " ", "/absolute/repository", "../repo", "a/../repo", "a\\repo"])
def test_unsafe_candidate_relative_selectors_are_rejected(selector: str) -> None:
    with pytest.raises(repository_import.InvalidImportTarget):
        repository_import._normalize_candidate_selector(selector)


def test_explicit_import_authorizes_freshly_discovers_and_revalidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "selected-root"
    repository = _init_repository(root / "nested-repository")
    candidate = _candidate(repository, relative="nested-repository")
    session = _FakeSession()
    binding_calls = _patch_successful_binding(monkeypatch)
    authorized_calls: list[tuple[str, Path]] = []
    discovery_calls: list[object] = []

    authorized_root = AuthorizedDiscoveryRoot(
        authorized_actor_id="account-a",
        canonical_root=root,
        provenance_class=DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION,
        authorized_at=datetime.now(timezone.utc),
    )

    def authorize(*, authorized_actor_id: str, root: Path | str):
        authorized_calls.append((authorized_actor_id, Path(root)))
        return authorized_root

    def discover(value):
        discovery_calls.append(value)
        return SimpleNamespace(candidates=(candidate,))

    monkeypatch.setattr(
        repository_import, "authorize_explicit_discovery_root", authorize
    )
    monkeypatch.setattr(
        repository_import, "discover_repository_candidates", discover
    )

    result = repository_import.import_explicit_repository_candidate(
        session,
        authenticated_account_id="account-a",
        discovery_root=root,
        candidate_relative_path="nested-repository",
        project_name="  Imported Project  ",
        project_description="A project description.",
    )

    assert authorized_calls == [("account-a", root)]
    assert discovery_calls == [authorized_root]
    assert result.project_id == 1
    assert result.binding_id == "binding-1"
    assert result.created_project is True
    assert result.reused_existing is False
    assert binding_calls["working_tree_root"] == repository
    assert binding_calls["source_class"] == SOURCE_CLASS_EXTERNAL_LINKED
    assert session.projects[1].user_id == "account-a"
    assert session.projects[1].name == "Imported Project"
    assert session.commit_count == 0


def test_missing_candidate_is_rejected_after_fresh_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "selected-root"
    root.mkdir()
    authorized_root = AuthorizedDiscoveryRoot(
        authorized_actor_id="account-a",
        canonical_root=root,
        provenance_class=DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION,
        authorized_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(
        repository_import,
        "authorize_explicit_discovery_root",
        lambda **_: authorized_root,
    )
    monkeypatch.setattr(
        repository_import,
        "discover_repository_candidates",
        lambda _: SimpleNamespace(candidates=()),
    )

    with pytest.raises(repository_import.CandidateNotFound):
        repository_import.import_explicit_repository_candidate(
            _FakeSession(),
            authenticated_account_id="account-a",
            discovery_root=root,
            candidate_relative_path="not-found",
            project_name="Imported",
        )


def test_candidate_actor_and_source_class_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    _patch_successful_binding(monkeypatch)
    with pytest.raises(repository_import.CandidateActorMismatch):
        repository_import.import_repository_candidate(
            _FakeSession(),
            authenticated_account_id="account-a",
            candidate=_candidate(repository, actor="account-b"),
            project_name="Imported",
        )

    invalid_source = _candidate(repository)
    object.__setattr__(invalid_source, "source_class", "external_linked")
    with pytest.raises(repository_import.CandidateRevalidationFailed):
        repository_import.import_repository_candidate(
            _FakeSession(),
            authenticated_account_id="account-a",
            candidate=invalid_source,
            project_name="Imported",
        )


def test_stale_or_changed_candidate_root_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_root = (tmp_path / "missing").resolve()
    stale = _candidate(missing_root)
    _patch_successful_binding(monkeypatch)
    with pytest.raises(repository_import.CandidateRevalidationFailed):
        repository_import.import_repository_candidate(
            _FakeSession(),
            authenticated_account_id="account-a",
            candidate=stale,
            project_name="Imported",
        )

    repository = _init_repository(tmp_path / "repository")
    monkeypatch.setattr(
        repository_import,
        "validate_git_working_tree_root",
        lambda _: (tmp_path / "other-root").resolve(),
    )
    with pytest.raises(repository_import.CandidateRevalidationFailed):
        repository_import.import_repository_candidate(
            _FakeSession(),
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_name="Imported",
        )


def test_new_project_is_owned_path_safe_and_uses_bounded_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    session = _FakeSession()
    binding_calls = _patch_successful_binding(monkeypatch)
    result = repository_import.import_repository_candidate(
        session,
        authenticated_account_id="account-a",
        candidate=_candidate(repository),
        project_name="Imported",
        project_description="Safe description",
    )

    assert result.source_class == SOURCE_CLASS_EXTERNAL_LINKED
    assert session.projects[result.project_id].user_id == "account-a"
    assert session.projects[result.project_id].description == "Safe description"
    assert binding_calls["source_class"] == SOURCE_CLASS_EXTERNAL_LINKED
    provenance = binding_calls["provenance"]
    assert set(provenance) == {
        "registration_source",
        "operation_class",
        "authority_context",
    }
    assert provenance["registration_source"] == "repository_candidate_import"
    assert provenance["operation_class"] == "external_link"
    assert provenance["authority_context"][
        "discovery_provenance_class"
    ] == DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION
    assert provenance["authority_context"]["git_evidence_kind"] == GIT_EVIDENCE_DIRECTORY
    assert provenance["authority_context"]["candidate_observed_at"].endswith("+00:00")
    assert str(repository) not in repr(provenance)
    assert "root_relative_path" not in repr(provenance)

    with pytest.raises(repository_import.InvalidImportTarget):
        repository_import.import_repository_candidate(
            _FakeSession(),
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_name="Reject path",
            project_description=f"Do not persist {repository}",
        )


def test_existing_project_requires_ownership_and_can_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    owned_project = Project(id=7, user_id="account-a", name="Owned")
    session = _FakeSession({7: owned_project})
    _patch_successful_binding(monkeypatch, binding_id="binding-owned")
    result = repository_import.import_repository_candidate(
        session,
        authenticated_account_id="account-a",
        candidate=_candidate(repository),
        project_id=7,
    )
    assert result == repository_import.RepositoryImportResult(
        project_id=7,
        binding_id="binding-owned",
        created_project=False,
        reused_existing=False,
    )
    assert session.added == []

    foreign_session = _FakeSession(
        {8: Project(id=8, user_id="account-b", name="Foreign")}
    )
    with pytest.raises(AccountProjectMismatch):
        repository_import.import_repository_candidate(
            foreign_session,
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_id=8,
        )


def test_duplicate_root_cases_are_idempotent_or_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    own_project = Project(id=4, user_id="account-a", name="Owned")
    other_project = Project(id=5, user_id="account-a", name="Other")
    binding = SimpleNamespace(id="existing-binding")
    session = _FakeSession({4: own_project, 5: other_project})
    monkeypatch.setattr(
        repository_import,
        "_active_bindings_for_canonical_root",
        lambda *_: [(binding, own_project)],
    )

    same = repository_import.import_repository_candidate(
        session,
        authenticated_account_id="account-a",
        candidate=_candidate(repository),
        project_id=4,
    )
    new_target = repository_import.import_repository_candidate(
        session,
        authenticated_account_id="account-a",
        candidate=_candidate(repository),
        project_name="Would not be created",
    )
    assert same.reused_existing is True
    assert new_target.project_id == 4
    assert len(session.projects) == 2
    with pytest.raises(repository_import.RepositoryAlreadyLinked):
        repository_import.import_repository_candidate(
            session,
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_id=5,
        )

    foreign_project = Project(id=9, user_id="account-b", name="Foreign")
    monkeypatch.setattr(
        repository_import,
        "_active_bindings_for_canonical_root",
        lambda *_: [(binding, foreign_project)],
    )
    with pytest.raises(repository_import.RepositoryBindingOwnedByAnotherAccount):
        repository_import.import_repository_candidate(
            session,
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_name="Must not exist",
        )

    monkeypatch.setattr(
        repository_import,
        "_active_bindings_for_canonical_root",
        lambda *_: [(binding, own_project), (binding, own_project)],
    )
    with pytest.raises(repository_import.RepositoryBindingAmbiguous):
        repository_import.import_repository_candidate(
            session,
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_name="Must not exist",
        )


def test_existing_project_with_active_binding_is_left_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    project = Project(id=4, user_id="account-a", name="Already bound")
    session = _FakeSession({4: project})
    monkeypatch.setattr(
        repository_import, "_active_bindings_for_canonical_root", lambda *_: []
    )

    def reject_binding(*args, **kwargs):
        raise ActiveBindingAlreadyExists("already bound")

    monkeypatch.setattr(
        repository_import, "create_repository_binding", reject_binding
    )
    with pytest.raises(ActiveBindingAlreadyExists):
        repository_import.import_repository_candidate(
            session,
            authenticated_account_id="account-a",
            candidate=_candidate(repository),
            project_id=4,
        )
    assert session.added == []
    assert session.commit_count == 0


def test_import_is_filesystem_and_git_immutable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    fixture = repository / "fixture.txt"
    before_bytes = fixture.read_bytes()
    before_stat = fixture.stat()
    before_head = _run_git("rev-parse", "HEAD", cwd=repository)
    before_branch = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=repository)
    binding_calls = _patch_successful_binding(monkeypatch)

    repository_import.import_repository_candidate(
        _FakeSession(),
        authenticated_account_id="account-a",
        candidate=_candidate(repository),
        project_name="No mutation",
    )

    assert fixture.read_bytes() == before_bytes
    assert fixture.stat().st_mtime_ns == before_stat.st_mtime_ns
    assert _run_git("rev-parse", "HEAD", cwd=repository) == before_head
    assert _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=repository) == before_branch
    assert binding_calls["working_tree_root"] == repository
    source = Path(repository_import.__file__).read_text()
    assert "Workspace" not in source
    assert "remote" not in source.lower()
    assert "source_class" not in str(
        repository_import.import_explicit_repository_candidate.__annotations__
    )
