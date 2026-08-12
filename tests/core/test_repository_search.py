from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from guardian.core import repository_search
from guardian.core.repository_authority import ResolvedRepositoryBinding


def _run_git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repository(path: Path) -> Path:
    path.mkdir()
    _run_git("init", "--quiet", cwd=path)
    _run_git("config", "user.email", "fixture@example.invalid", cwd=path)
    _run_git("config", "user.name", "Fixture", cwd=path)
    return path.resolve()


def _commit_all(repository: Path, message: str = "fixture") -> None:
    _run_git("add", ".", cwd=repository)
    _run_git("commit", "--quiet", "-m", message, cwd=repository)


def _binding(repository: Path, project_id: int = 7) -> ResolvedRepositoryBinding:
    return ResolvedRepositoryBinding(
        binding_id="binding-fixture",
        project_id=project_id,
        source_class="external_linked",
        canonical_root=repository.resolve(),
    )


def _search(
    repository: Path,
    query: str,
    *,
    limit: int = 20,
    limits: repository_search.RepositorySearchLimits | None = None,
) -> repository_search.RepositorySearchResult:
    return repository_search._search_bound_repository(
        _binding(repository),
        normalized_query=repository_search._normalize_query(
            query,
            limits=limits or repository_search.RepositorySearchLimits(),
        ),
        result_limit=limit,
        limits=limits or repository_search.RepositorySearchLimits(),
    )


@pytest.mark.parametrize("query", ["", "   ", "x" * 257, "needle\x00", "needle\r", "needle\n"])
def test_invalid_queries_are_rejected(query: str) -> None:
    with pytest.raises(repository_search.InvalidRepositorySearchQuery):
        repository_search._normalize_query(
            query, limits=repository_search.RepositorySearchLimits()
        )


@pytest.mark.parametrize("limit", [0, -1, 21, True])
def test_invalid_result_limits_are_rejected(limit: int) -> None:
    with pytest.raises(repository_search.InvalidRepositorySearchQuery):
        repository_search._validate_result_limit(
            limit, limits=repository_search.RepositorySearchLimits()
        )


def test_search_project_repository_resolves_binding_before_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    (repository / "tracked.txt").write_text("Needle\n")
    _commit_all(repository)
    resolved_calls: list[dict[str, object]] = []

    def resolve(session, **kwargs):
        resolved_calls.append({"session": session, **kwargs})
        return _binding(repository, project_id=23)

    monkeypatch.setattr(
        repository_search, "resolve_project_repository_binding", resolve
    )
    result = repository_search.search_project_repository(
        object(),
        authenticated_account_id="account-a",
        project_id=23,
        query="needle",
        result_limit=5,
    )

    assert resolved_calls == [
        {
            "session": resolved_calls[0]["session"],
            "authenticated_account_id": "account-a",
            "project_id": 23,
            "timeout_seconds": 5.0,
        }
    ]
    assert result.matches[0].path == "tracked.txt"
    assert "canonical_root" not in result.to_payload()
    assert "repository_root" not in result.to_payload()


def test_search_requires_authenticated_account_at_binding_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject(*args, **kwargs):
        raise repository_search.AccountProjectMismatch("account required")

    monkeypatch.setattr(
        repository_search, "resolve_project_repository_binding", reject
    )
    with pytest.raises(repository_search.AccountProjectMismatch):
        repository_search.search_project_repository(
            object(),
            authenticated_account_id="",
            project_id=1,
            query="needle",
        )


def test_tracked_untracked_ignored_and_casefold_literal_search(
    tmp_path: Path,
) -> None:
    repository = _init_repository(tmp_path / "repository")
    (repository / "tracked.txt").write_text("First\nNEEDLE\n")
    (repository / ".gitignore").write_text("ignored.txt\n")
    _commit_all(repository)
    (repository / "untracked.txt").write_text("Needle in an untracked file\n")
    (repository / "ignored.txt").write_text("needle must remain hidden\n")
    (repository / "regex.txt").write_text("a[bc] literal\n")

    result = _search(repository, "needle")
    assert [(match.path, match.line) for match in result.matches] == [
        ("tracked.txt", 2),
        ("untracked.txt", 1),
    ]
    assert _search(repository, "[bc]").matches[0].path == "regex.txt"
    assert _search(repository, "needle").matches[0].path != str(repository)


def test_matches_are_deterministic_relative_and_line_bounded(
    tmp_path: Path,
) -> None:
    repository = _init_repository(tmp_path / "repository")
    (repository / "zeta.txt").write_text("needle zeta\n")
    (repository / "alpha.txt").write_text("first\nneedle alpha\n")
    _commit_all(repository)
    result = _search(repository, "needle")

    assert [(match.path, match.line) for match in result.matches] == [
        ("alpha.txt", 2),
        ("zeta.txt", 1),
    ]
    assert all(not Path(match.path).is_absolute() for match in result.matches)
    assert all(len(match.snippet) <= 400 for match in result.matches)
    assert str(repository) not in repr(result.to_payload())


def test_long_line_snippet_is_match_centered_and_bounded(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path / "repository")
    long_line = "a" * 500 + "needle" + "z" * 500
    (repository / "long.txt").write_text(long_line + "\n")
    _commit_all(repository)
    snippet = _search(repository, "needle").matches[0].snippet
    assert len(snippet) == 400
    assert "needle" in snippet
    assert snippet == _search(repository, "needle").matches[0].snippet


def test_result_cap_file_entry_and_listing_byte_bounds(
    tmp_path: Path,
) -> None:
    repository = _init_repository(tmp_path / "repository")
    for index in range(4):
        (repository / f"{index}.txt").write_text("needle\n")
    _commit_all(repository)

    capped = _search(repository, "needle", limit=2)
    assert capped.count == 2
    assert capped.truncated is True
    assert capped.stop_reason == "result_limit_reached"

    file_limited = _search(
        repository,
        "needle",
        limits=repository_search.RepositorySearchLimits(
            max_candidate_file_entries=2
        ),
    )
    assert file_limited.truncated is True
    assert file_limited.stop_reason == "file_limit_reached"

    listing_limited = _search(
        repository,
        "needle",
        limits=repository_search.RepositorySearchLimits(
            max_git_file_list_bytes=3
        ),
    )
    assert listing_limited.truncated is True
    assert listing_limited.stop_reason == "listing_limit_reached"


def test_aggregate_byte_limit_and_individual_oversize_skip(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path / "repository")
    (repository / "one.txt").write_text("needle small\n")
    (repository / "two.txt").write_text("needle another\n")
    (repository / "large.txt").write_text("needle " + ("x" * 80))
    _commit_all(repository)
    byte_limited = _search(
        repository,
        "needle",
        limits=repository_search.RepositorySearchLimits(
            max_aggregate_file_bytes=15
        ),
    )
    assert byte_limited.truncated is True
    assert byte_limited.stop_reason == "byte_limit_reached"

    oversized = _search(
        repository,
        "needle",
        limits=repository_search.RepositorySearchLimits(
            max_individual_file_bytes=10
        ),
    )
    assert oversized.skipped_oversized_files >= 1


def test_binary_invalid_utf8_and_sensitive_paths_are_not_read(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path / "repository")
    (repository / "binary.bin").write_bytes(b"needle\x00bytes")
    (repository / "invalid.txt").write_bytes(b"needle\xff")
    (repository / ".env").write_text("needle=secret\n")
    (repository / ".env.local").write_text("needle=secret\n")
    (repository / "id_rsa").write_text("needle secret\n")
    (repository / "certificate.pem").write_text("needle secret\n")
    (repository / "safe.txt").write_text("needle safe\n")
    _commit_all(repository)

    result = _search(repository, "needle")
    assert [match.path for match in result.matches] == ["safe.txt"]
    assert result.skipped_binary_files == 2
    assert result.skipped_sensitive_files == 4


def test_symlinks_and_escape_paths_are_never_followed(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path / "repository")
    outside = tmp_path / "outside.txt"
    outside.write_text("needle outside\n")
    os.symlink(outside, repository / "link.txt")
    (repository / "safe.txt").write_text("needle safe\n")
    _commit_all(repository)

    result = _search(repository, "needle")
    assert [match.path for match in result.matches] == ["safe.txt"]
    assert result.skipped_symlink_files == 1


def test_enumeration_uses_only_read_only_git_argv_and_optional_locks(
    tmp_path: Path,
) -> None:
    repository = _init_repository(tmp_path / "repository")
    (repository / "tracked.txt").write_text("needle\n")
    _commit_all(repository)
    captured: dict[str, object] = {}
    original_popen = subprocess.Popen

    def recording_popen(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return original_popen(*args, **kwargs)

    result = repository_search._enumerate_repository_paths(
        repository,
        deadline=repository_search.time.monotonic() + 5,
        limits=repository_search.RepositorySearchLimits(),
        popen_factory=recording_popen,
    )
    command = captured["args"][0]
    assert command[1:] == [
        "-C",
        str(repository),
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    ]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["env"]["GIT_OPTIONAL_LOCKS"] == "0"
    assert result.paths == ("tracked.txt",)


def test_deadline_is_enforced_without_filesystem_or_git_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _init_repository(tmp_path / "repository")
    fixture = repository / "fixture.txt"
    fixture.write_text("needle fixture\n")
    _commit_all(repository)
    before_bytes = fixture.read_bytes()
    before_head = _run_git("rev-parse", "HEAD", cwd=repository)
    before_branch = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=repository)

    monkeypatch.setattr(
        repository_search,
        "_enumerate_repository_paths",
        lambda *_args, **_kwargs: repository_search._EnumerationResult(
            paths=("fixture.txt",),
            stop_reason=repository_search.STOP_REASON_COMPLETED,
        ),
    )
    clock_values = iter((0.0, 0.0, 6.0))
    result = repository_search._search_bound_repository(
        _binding(repository),
        normalized_query="needle",
        result_limit=20,
        limits=repository_search.RepositorySearchLimits(),
        monotonic=lambda: next(clock_values),
    )

    assert result.stop_reason == "timeout_reached"
    assert result.matches == ()
    assert fixture.read_bytes() == before_bytes
    assert _run_git("rev-parse", "HEAD", cwd=repository) == before_head
    assert _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=repository) == before_branch


def test_search_has_no_path_only_public_authority_entry_point() -> None:
    source = Path(repository_search.__file__).read_text()
    assert "Path.cwd()" not in source
    assert "CODEXIFY_WORKTREE_REPO_PATH" not in source
    assert "detect_project_root" not in source
    assert "fs.search" not in source
    assert "subprocess.run" not in source
    with pytest.raises(TypeError):
        repository_search._search_bound_repository(  # type: ignore[arg-type]
            SimpleNamespace(canonical_root=Path("/")),
            normalized_query="needle",
            result_limit=1,
            limits=repository_search.RepositorySearchLimits(),
        )
