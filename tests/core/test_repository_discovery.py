"""Unit coverage for the bounded, non-authorizing Stage 2K.2 scanner."""

from __future__ import annotations

import ast
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from guardian.core import repository_discovery as discovery
from guardian.core.repository_authority import (
    GuardianProjectsDirectoryUnconfigured,
    InvalidRepositoryRoot,
)


def _run_git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repository(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _run_git("init", "--quiet", str(path))
    return path


def _authorized_root(
    path: Path,
    *,
    limits: discovery.RepositoryDiscoveryLimits | None = None,
) -> discovery.AuthorizedDiscoveryRoot:
    return discovery.authorize_explicit_discovery_root(
        authorized_actor_id="account-test",
        root=path,
        limits=limits,
    )


def _nested_directory(root: Path, depth: int) -> Path:
    current = root
    for index in range(depth):
        current = current / f"depth-{index}"
        current.mkdir()
    return current


def test_default_limits_match_adr_065_exactly() -> None:
    limits = discovery.RepositoryDiscoveryLimits()

    assert limits.max_depth == 4
    assert limits.max_candidates == 128
    assert limits.timeout_seconds == 10.0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_depth": -1}, "max_depth"),
        ({"max_depth": 1.5}, "max_depth"),
        ({"max_candidates": 0}, "max_candidates"),
        ({"max_candidates": 1.5}, "max_candidates"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"timeout_seconds": -1.0}, "timeout_seconds"),
    ],
)
def test_invalid_limits_are_rejected(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        discovery.RepositoryDiscoveryLimits(**kwargs)


def test_scanner_rejects_naked_arbitrary_path(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="AuthorizedDiscoveryRoot"):
        discovery.discover_repository_candidates(tmp_path)  # type: ignore[arg-type]


def test_typed_root_cannot_bypass_canonical_forbidden_root_check() -> None:
    with pytest.raises(discovery.ForbiddenDiscoveryRoot):
        discovery.AuthorizedDiscoveryRoot(
            authorized_actor_id="account-test",
            canonical_root=Path("/"),
            provenance_class=(
                discovery.DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION
            ),
            authorized_at=datetime.now(timezone.utc),
        )


def test_authorized_actor_is_required(tmp_path: Path) -> None:
    with pytest.raises(discovery.DiscoveryRootAuthorizationError):
        discovery.authorize_explicit_discovery_root(
            authorized_actor_id=" ", root=tmp_path
        )


def test_nonexistent_and_file_discovery_roots_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(discovery.InvalidDiscoveryRoot):
        discovery.authorize_explicit_discovery_root(
            authorized_actor_id="account-test", root=tmp_path / "absent"
        )

    file_root = tmp_path / "not-a-directory"
    file_root.write_text("not a directory")
    with pytest.raises(discovery.InvalidDiscoveryRoot):
        discovery.authorize_explicit_discovery_root(
            authorized_actor_id="account-test", root=file_root
        )


@pytest.mark.parametrize("broad_root", [Path("/"), Path("/Users"), Path("/Volumes")])
def test_forbidden_broad_roots_are_rejected_when_present(broad_root: Path) -> None:
    if not broad_root.exists():
        pytest.skip(f"{broad_root} is not present on this host")

    with pytest.raises(discovery.ForbiddenDiscoveryRoot):
        discovery.authorize_explicit_discovery_root(
            authorized_actor_id="account-test", root=broad_root
        )


def test_exact_home_is_rejected_but_explicit_bounded_child_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    bounded_child = fake_home / "selected-library"
    bounded_child.mkdir()
    monkeypatch.setattr(
        discovery.Path, "home", classmethod(lambda cls: fake_home)
    )

    with pytest.raises(discovery.ForbiddenDiscoveryRoot):
        discovery.authorize_explicit_discovery_root(
            authorized_actor_id="account-test", root=fake_home
        )

    root = discovery.authorize_explicit_discovery_root(
        authorized_actor_id="account-test", root=bounded_child
    )
    assert root.canonical_root == bounded_child.resolve()


def test_guardian_projects_root_uses_stage_2k1_resolver(tmp_path: Path) -> None:
    managed_root = tmp_path / "managed"
    managed_root.mkdir()
    settings = SimpleNamespace(CODEXIFY_GUARDIAN_PROJECTS_DIR=str(managed_root))

    root = discovery.authorize_guardian_projects_discovery_root(
        authorized_actor_id="account-test", settings=settings
    )

    assert root.canonical_root == managed_root.resolve()
    assert (
        root.provenance_class
        == discovery.DISCOVERY_ROOT_PROVENANCE_GUARDIAN_PROJECTS_DIRECTORY
    )


def test_unconfigured_guardian_projects_root_fails_closed() -> None:
    settings = SimpleNamespace(CODEXIFY_GUARDIAN_PROJECTS_DIR="")
    with pytest.raises(GuardianProjectsDirectoryUnconfigured):
        discovery.authorize_guardian_projects_discovery_root(
            authorized_actor_id="account-test", settings=settings
        )


def test_evidence_backed_and_connector_roots_require_bounded_evidence(
    tmp_path: Path,
) -> None:
    with pytest.raises(discovery.DiscoveryRootAuthorizationError):
        discovery.authorize_evidence_backed_discovery_root(
            authorized_actor_id="account-test",
            root=tmp_path,
            evidence_reference=" ",
        )
    with pytest.raises(discovery.DiscoveryRootAuthorizationError):
        discovery.authorize_connector_discovery_root(
            authorized_actor_id="account-test",
            root=tmp_path,
            evidence_reference="x" * 257,
        )

    root = discovery.authorize_evidence_backed_discovery_root(
        authorized_actor_id="account-test",
        root=tmp_path,
        evidence_reference="guardian-receipt-001",
    )
    assert (
        root.provenance_class
        == discovery.DISCOVERY_ROOT_PROVENANCE_EVIDENCE_BACKED_LOCAL_ROOT
    )


@pytest.mark.parametrize("depth", [0, 1, 4])
def test_scanner_detects_real_repository_at_supported_depths(
    tmp_path: Path, depth: int
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    repository = _init_repository(_nested_directory(scan_root, depth))

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.stop_reason == discovery.STOP_REASON_COMPLETED
    assert [candidate.canonical_working_tree_root for candidate in result.candidates] == [
        repository.resolve()
    ]
    assert result.candidates[0].root_relative_path == repository.relative_to(
        scan_root
    )
    assert result.candidates[0].source_class == "discovery_candidate"
    assert result.candidates[0].git_evidence_kind == discovery.GIT_EVIDENCE_DIRECTORY


def test_scanner_does_not_descend_to_depth_five(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    _init_repository(_nested_directory(scan_root, 5))

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.candidates == ()
    assert result.stop_reason == discovery.STOP_REASON_COMPLETED


def test_scanner_detects_linked_worktree_file_evidence(tmp_path: Path) -> None:
    base_repository = _init_repository(tmp_path / "base")
    (base_repository / "README.md").write_text("fixture\n")
    _run_git("config", "user.email", "fixture@example.invalid", cwd=base_repository)
    _run_git("config", "user.name", "Fixture", cwd=base_repository)
    _run_git("add", "README.md", cwd=base_repository)
    _run_git("commit", "--quiet", "-m", "fixture", cwd=base_repository)

    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    linked_worktree = scan_root / "linked"
    _run_git("worktree", "add", "--quiet", "--detach", str(linked_worktree), "HEAD", cwd=base_repository)

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert len(result.candidates) == 1
    assert result.candidates[0].canonical_working_tree_root == linked_worktree.resolve()
    assert (
        result.candidates[0].git_evidence_kind
        == discovery.GIT_EVIDENCE_WORKTREE_FILE
    )


def test_git_evidence_symlink_is_not_trusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    fake_repository = scan_root / "fake"
    fake_repository.mkdir()
    git_data = fake_repository / "git-data"
    git_data.mkdir()
    (fake_repository / ".git").symlink_to(git_data, target_is_directory=True)
    calls: list[Path] = []
    monkeypatch.setattr(
        discovery,
        "validate_git_working_tree_root",
        lambda path, **kwargs: calls.append(Path(path).resolve()),
    )

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.candidates == ()
    assert result.skipped_symlink_count >= 1
    assert calls == []


def test_directory_symlink_is_not_traversed(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    outside_repository = _init_repository(tmp_path / "outside-repository")
    (scan_root / "repository-alias").symlink_to(
        outside_repository, target_is_directory=True
    )

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.candidates == ()
    assert result.skipped_symlink_count == 1


def test_successful_repository_stops_descending_below_it(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    outer_repository = _init_repository(scan_root / "outer")
    _init_repository(outer_repository / "nested")

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert [candidate.canonical_working_tree_root for candidate in result.candidates] == [
        outer_repository.resolve()
    ]


def test_invalid_git_evidence_is_counted_but_not_a_candidate(
    tmp_path: Path,
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    invalid = scan_root / "invalid-evidence"
    invalid.mkdir()
    (invalid / ".git").write_text("not a worktree pointer")

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.candidates == ()
    assert result.invalid_git_evidence_count == 1


def test_non_git_directories_do_not_trigger_git_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    (scan_root / "ordinary").mkdir()
    calls: list[Path] = []
    monkeypatch.setattr(
        discovery,
        "validate_git_working_tree_root",
        lambda path, **kwargs: calls.append(Path(path)),
    )

    discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert calls == []


def test_canonical_duplicate_candidate_is_returned_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    for name in ("first", "second"):
        candidate = scan_root / name
        candidate.mkdir()
        (candidate / ".git").mkdir()
    canonical_repository = _init_repository(tmp_path / "canonical")
    monkeypatch.setattr(
        discovery,
        "validate_git_working_tree_root",
        lambda path, **kwargs: canonical_repository.resolve(),
    )

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert len(result.candidates) == 1
    assert result.duplicate_candidate_count == 1
    assert result.candidates[0].root_relative_path == Path("first")


def test_candidate_limit_stops_at_exactly_128(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    for index in range(129):
        candidate = scan_root / f"candidate-{index:03d}"
        candidate.mkdir()
        (candidate / ".git").mkdir()

    monkeypatch.setattr(
        discovery,
        "validate_git_working_tree_root",
        lambda path, **kwargs: Path(path).resolve(),
    )
    limits = discovery.RepositoryDiscoveryLimits(max_candidates=128)
    result = discovery.discover_repository_candidates(
        _authorized_root(scan_root, limits=limits)
    )

    assert len(result.candidates) == 128
    assert result.stop_reason == discovery.STOP_REASON_CANDIDATE_LIMIT_REACHED


def test_root_wide_timeout_stops_without_sleeping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    clock_values = iter([0.0, 10.1, 10.1])
    monkeypatch.setattr(discovery.time, "monotonic", lambda: next(clock_values))

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.stop_reason == discovery.STOP_REASON_TIMEOUT_REACHED
    assert result.elapsed_seconds == 10.0


def test_successful_bounded_scan_reports_completed(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    (scan_root / "ordinary.txt").write_text("not inspected as source")

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.stop_reason == discovery.STOP_REASON_COMPLETED
    assert result.scanned_directory_count == 1
    assert result.elapsed_seconds <= 10.0


def test_scanner_does_not_mutate_fixture_content(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    fixture = scan_root / "fixture.txt"
    fixture.write_text("must remain unchanged")
    before_content = fixture.read_bytes()
    before_mtime_ns = fixture.stat().st_mtime_ns

    discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert fixture.read_bytes() == before_content
    assert fixture.stat().st_mtime_ns == before_mtime_ns


def test_scanner_never_executes_project_code(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    repository = _init_repository(scan_root / "repository")
    marker = repository / "project_code.py"
    marker.write_text("raise RuntimeError('must not execute')\n")

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert len(result.candidates) == 1
    assert marker.exists()


def test_scanner_reuses_stage_2k1_exact_git_validation_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    candidate = scan_root / "candidate"
    candidate.mkdir()
    (candidate / ".git").mkdir()
    calls: list[tuple[Path, float]] = []

    def canonical_validator(path: Path | str, *, timeout_seconds: float) -> Path:
        calls.append((Path(path).resolve(), timeout_seconds))
        return Path(path).resolve()

    monkeypatch.setattr(
        discovery, "validate_git_working_tree_root", canonical_validator
    )
    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert len(result.candidates) == 1
    assert calls[0][0] == candidate.resolve()
    assert 0 < calls[0][1] <= 10.0


def test_module_has_no_persistence_or_unbounded_path_fallbacks() -> None:
    source_path = Path(discovery.__file__)
    source = source_path.read_text()
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert not any(module.startswith("sqlalchemy") for module in imported_modules)
    assert not any(module.startswith("guardian.db") for module in imported_from_modules)
    for prohibited in (
        "CODEXIFY_WORKTREE_REPO_PATH",
        "detect_project_root",
        "subprocess.",
        "fetch",
        "pull",
        "checkout",
        ".mkdir(",
        ".write_text(",
        ".unlink(",
    ):
        assert prohibited not in source


def test_candidates_are_ephemeral_and_never_auto_scan_other_locations(
    tmp_path: Path,
) -> None:
    scan_root = tmp_path / "explicit-root"
    scan_root.mkdir()
    repository = _init_repository(scan_root / "repository")
    outside = _init_repository(tmp_path / "outside")

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert [candidate.canonical_working_tree_root for candidate in result.candidates] == [
        repository.resolve()
    ]
    assert outside.resolve() not in {
        candidate.canonical_working_tree_root for candidate in result.candidates
    }
    assert result.candidates[0].discovered_at.tzinfo is not None


def test_candidate_type_rejects_authorizing_source_class(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-authorizing"):
        discovery.RepositoryDiscoveryCandidate(
            canonical_working_tree_root=tmp_path.resolve(),
            root_relative_path=Path("."),
            discovery_root_provenance_class=(
                discovery.DISCOVERY_ROOT_PROVENANCE_EXPLICIT_AUTHENTICATED_SELECTION
            ),
            authorized_actor_id="account-test",
            git_evidence_kind=discovery.GIT_EVIDENCE_DIRECTORY,
            discovered_at=datetime.now(timezone.utc),
            source_class="external_linked",
        )


def test_invalid_git_validator_failure_does_not_escape_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    candidate = scan_root / "candidate"
    candidate.mkdir()
    (candidate / ".git").mkdir()
    monkeypatch.setattr(
        discovery,
        "validate_git_working_tree_root",
        lambda path, **kwargs: (_ for _ in ()).throw(
            InvalidRepositoryRoot("fixture invalid")
        ),
    )

    result = discovery.discover_repository_candidates(_authorized_root(scan_root))

    assert result.candidates == ()
    assert result.invalid_git_evidence_count == 1
