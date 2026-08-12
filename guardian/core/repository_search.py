"""Bounded, read-only repository search (Stage 2K.4 / ADR-065).

Filesystem authority is derived only from a previously resolved active
RepositoryBinding. The public Project entry point resolves that binding before
search; the lower-level engine accepts the typed authority result, never a
caller-supplied repository path. This module has no HTTP, model-tool, provider,
database-mutation, or shell-execution responsibility.
"""

from __future__ import annotations

import os
import select
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from sqlalchemy.orm import Session

from guardian.core.repository_authority import (
    AccountProjectMismatch,
    ProjectNotFound,
    RepositoryAuthorityError,
    ResolvedRepositoryBinding,
    resolve_project_repository_binding,
)


MAX_QUERY_CHARACTERS = 256
MAX_RETURNED_MATCHES = 20
MAX_CANDIDATE_FILE_ENTRIES = 5_000
MAX_GIT_FILE_LIST_BYTES = 2 * 1024 * 1024
MAX_INDIVIDUAL_FILE_BYTES = 1 * 1024 * 1024
MAX_AGGREGATE_FILE_BYTES = 32 * 1024 * 1024
MAX_SNIPPET_CHARACTERS = 400
MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS = 512
MAX_SEARCH_SECONDS = 5.0
_LISTING_READ_CHUNK_BYTES = 64 * 1024
_PROCESS_WAIT_SECONDS = 0.25

STOP_REASON_COMPLETED = "completed"
STOP_REASON_RESULT_LIMIT_REACHED = "result_limit_reached"
STOP_REASON_FILE_LIMIT_REACHED = "file_limit_reached"
STOP_REASON_LISTING_LIMIT_REACHED = "listing_limit_reached"
STOP_REASON_BYTE_LIMIT_REACHED = "byte_limit_reached"
STOP_REASON_TIMEOUT_REACHED = "timeout_reached"
STOP_REASONS = frozenset(
    {
        STOP_REASON_COMPLETED,
        STOP_REASON_RESULT_LIMIT_REACHED,
        STOP_REASON_FILE_LIMIT_REACHED,
        STOP_REASON_LISTING_LIMIT_REACHED,
        STOP_REASON_BYTE_LIMIT_REACHED,
        STOP_REASON_TIMEOUT_REACHED,
    }
)

_SENSITIVE_BASENAMES = frozenset(
    {
        ".env",
        ".netrc",
        ".npmrc",
        ".pypirc",
        ".git-credentials",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
)
_SENSITIVE_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
)


class RepositorySearchError(Exception):
    """Base class for bounded repository-search failures."""


class InvalidRepositorySearchQuery(RepositorySearchError):
    """Query or requested result limit is outside the fixed search envelope."""


class RepositorySearchUnavailable(RepositorySearchError):
    """The Project binding cannot safely provide search authority."""


class RepositorySearchEnumerationFailed(RepositorySearchError):
    """Read-only Git file-list enumeration could not complete safely."""


@dataclass(frozen=True)
class RepositorySearchLimits:
    """Fixed Stage 2K.4 safety envelope; callers cannot widen it."""

    max_query_characters: int = MAX_QUERY_CHARACTERS
    max_returned_matches: int = MAX_RETURNED_MATCHES
    max_candidate_file_entries: int = MAX_CANDIDATE_FILE_ENTRIES
    max_git_file_list_bytes: int = MAX_GIT_FILE_LIST_BYTES
    max_individual_file_bytes: int = MAX_INDIVIDUAL_FILE_BYTES
    max_aggregate_file_bytes: int = MAX_AGGREGATE_FILE_BYTES
    max_snippet_characters: int = MAX_SNIPPET_CHARACTERS
    max_path_characters: int = MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS
    max_wall_clock_seconds: float = MAX_SEARCH_SECONDS

    def __post_init__(self) -> None:
        positive_ints = (
            self.max_query_characters,
            self.max_returned_matches,
            self.max_candidate_file_entries,
            self.max_git_file_list_bytes,
            self.max_individual_file_bytes,
            self.max_aggregate_file_bytes,
            self.max_snippet_characters,
            self.max_path_characters,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in positive_ints
        ):
            raise ValueError("repository search integer limits must be positive")
        if (
            not isinstance(self.max_wall_clock_seconds, (int, float))
            or isinstance(self.max_wall_clock_seconds, bool)
            or self.max_wall_clock_seconds <= 0
        ):
            raise ValueError("repository search wall-clock limit must be positive")


@dataclass(frozen=True)
class RepositorySearchMatch:
    """One bounded repository-relative text match."""

    path: str
    line: int
    snippet: str

    def __post_init__(self) -> None:
        candidate = PurePosixPath(self.path)
        if (
            not self.path
            or candidate.is_absolute()
            or ".." in candidate.parts
            or len(self.path) > MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS
        ):
            raise ValueError("repository search match path must be relative")
        if not isinstance(self.line, int) or self.line <= 0:
            raise ValueError("repository search match line must be positive")
        if len(self.snippet) > MAX_SNIPPET_CHARACTERS:
            raise ValueError("repository search snippet exceeds fixed bound")


@dataclass(frozen=True)
class RepositorySearchResult:
    """Bounded, path-private result for the route and Command Bus."""

    matches: tuple[RepositorySearchMatch, ...]
    count: int
    truncated: bool
    stop_reason: str
    scanned_files: int
    scanned_bytes: int
    skipped_binary_files: int
    skipped_oversized_files: int
    skipped_sensitive_files: int
    skipped_symlink_files: int

    def __post_init__(self) -> None:
        if self.stop_reason not in STOP_REASONS:
            raise ValueError("unsupported repository search stop reason")
        if self.count != len(self.matches):
            raise ValueError("repository search count must match returned matches")
        counters = (
            self.scanned_files,
            self.scanned_bytes,
            self.skipped_binary_files,
            self.skipped_oversized_files,
            self.skipped_sensitive_files,
            self.skipped_symlink_files,
        )
        if any(not isinstance(value, int) or value < 0 for value in counters):
            raise ValueError("repository search counters must be non-negative")

    def to_payload(self) -> dict[str, object]:
        """Return only the approved route and Command Bus result surface."""
        return {
            "matches": [
                {
                    "path": match.path,
                    "line": match.line,
                    "snippet": match.snippet,
                }
                for match in self.matches
            ],
            "count": self.count,
            "truncated": self.truncated,
            "stop_reason": self.stop_reason,
            "scanned_files": self.scanned_files,
            "scanned_bytes": self.scanned_bytes,
            "skipped_binary_files": self.skipped_binary_files,
            "skipped_oversized_files": self.skipped_oversized_files,
            "skipped_sensitive_files": self.skipped_sensitive_files,
            "skipped_symlink_files": self.skipped_symlink_files,
        }


@dataclass(frozen=True)
class _EnumerationResult:
    paths: tuple[str, ...]
    stop_reason: str


def _normalize_query(query: str, *, limits: RepositorySearchLimits) -> str:
    raw_value = str(query or "")
    if "\x00" in raw_value or "\r" in raw_value or "\n" in raw_value:
        raise InvalidRepositorySearchQuery("repository search query is invalid")
    value = raw_value.strip()
    if not value:
        raise InvalidRepositorySearchQuery("repository search query is required")
    if len(value) > limits.max_query_characters:
        raise InvalidRepositorySearchQuery("repository search query is invalid")
    return value


def _validate_result_limit(
    result_limit: int, *, limits: RepositorySearchLimits
) -> int:
    if (
        not isinstance(result_limit, int)
        or isinstance(result_limit, bool)
        or result_limit < 1
        or result_limit > limits.max_returned_matches
    ):
        raise InvalidRepositorySearchQuery(
            "repository search result limit is invalid"
        )
    return result_limit


def _remaining_seconds(deadline: float, monotonic: Callable[[], float]) -> float:
    return max(0.0, deadline - monotonic())


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=_PROCESS_WAIT_SECONDS)
    except (subprocess.TimeoutExpired, OSError):
        try:
            process.kill()
            process.wait(timeout=_PROCESS_WAIT_SECONDS)
        except (subprocess.TimeoutExpired, OSError):
            pass


def _valid_repository_relative_path(
    raw_path: bytes,
    *,
    limits: RepositorySearchLimits,
) -> str | None:
    try:
        path = raw_path.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    if not path or len(path) > limits.max_path_characters:
        return None
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    normalized = candidate.as_posix()
    if (
        not normalized
        or normalized == "."
        or len(normalized) > limits.max_path_characters
    ):
        return None
    return normalized


def _enumerate_repository_paths(
    root: Path,
    *,
    deadline: float,
    limits: RepositorySearchLimits,
    monotonic: Callable[[], float] = time.monotonic,
    popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> _EnumerationResult:
    """Stream bounded Git file-list output without unbounded capture."""
    git_binary = shutil.which("git") or "git"
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        process = popen_factory(
            [
                git_binary,
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            env=environment,
        )
    except OSError as exc:
        raise RepositorySearchEnumerationFailed(
            "repository file enumeration could not start"
        ) from exc

    if process.stdout is None:
        _terminate_process(process)
        raise RepositorySearchEnumerationFailed(
            "repository file enumeration did not provide stdout"
        )

    output_bytes = 0
    pending = b""
    accepted_paths: set[str] = set()
    stop_reason = STOP_REASON_COMPLETED
    try:
        while True:
            remaining = _remaining_seconds(deadline, monotonic)
            if remaining <= 0:
                stop_reason = STOP_REASON_TIMEOUT_REACHED
                break
            ready, _, _ = select.select([process.stdout], [], [], remaining)
            if not ready:
                if process.poll() is None:
                    stop_reason = STOP_REASON_TIMEOUT_REACHED
                    break
                chunk = process.stdout.read1(_LISTING_READ_CHUNK_BYTES)
            else:
                chunk = process.stdout.read1(
                    min(
                        _LISTING_READ_CHUNK_BYTES,
                        limits.max_git_file_list_bytes - output_bytes + 1,
                    )
                )

            if not chunk:
                if process.poll() is None:
                    continue
                break
            output_bytes += len(chunk)
            if output_bytes > limits.max_git_file_list_bytes:
                stop_reason = STOP_REASON_LISTING_LIMIT_REACHED
                break

            pending += chunk
            entries = pending.split(b"\0")
            pending = entries.pop()
            for raw_path in entries:
                normalized = _valid_repository_relative_path(
                    raw_path, limits=limits
                )
                if normalized is None:
                    continue
                accepted_paths.add(normalized)
                if len(accepted_paths) >= limits.max_candidate_file_entries:
                    stop_reason = STOP_REASON_FILE_LIMIT_REACHED
                    break
            if stop_reason != STOP_REASON_COMPLETED:
                break

        if stop_reason != STOP_REASON_COMPLETED:
            _terminate_process(process)
        else:
            try:
                returncode = process.wait(
                    timeout=_remaining_seconds(deadline, monotonic)
                )
            except subprocess.TimeoutExpired:
                _terminate_process(process)
                return _EnumerationResult(
                    paths=tuple(sorted(accepted_paths)),
                    stop_reason=STOP_REASON_TIMEOUT_REACHED,
                )
            if returncode != 0:
                raise RepositorySearchEnumerationFailed(
                    "repository file enumeration failed"
                )
    finally:
        if process.stdout is not None:
            process.stdout.close()

    return _EnumerationResult(
        paths=tuple(sorted(accepted_paths)),
        stop_reason=stop_reason,
    )


def _is_sensitive_path(relative_path: str) -> bool:
    basename = PurePosixPath(relative_path).name.casefold()
    return (
        basename in _SENSITIVE_BASENAMES
        or basename.startswith(".env.")
        or basename.endswith(_SENSITIVE_SUFFIXES)
    )


def _resolved_regular_file(
    root: Path, relative_path: str
) -> tuple[Path | None, bool]:
    """Return a contained regular file and whether a symlink was rejected."""
    candidate = root.joinpath(*PurePosixPath(relative_path).parts)
    try:
        if candidate.is_symlink():
            return None, True
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None, False
    if not resolved.is_file():
        return None, False
    return resolved, False


def _casefold_match_span(
    line: str, query_casefold: str
) -> tuple[int, int] | None:
    folded_parts: list[str] = []
    source_positions: list[int] = []
    for index, character in enumerate(line):
        folded = character.casefold()
        folded_parts.append(folded)
        source_positions.extend([index] * len(folded))
    folded_line = "".join(folded_parts)
    start = folded_line.find(query_casefold)
    if start < 0:
        return None
    end_folded = start + len(query_casefold) - 1
    if not source_positions or end_folded >= len(source_positions):
        return None
    return source_positions[start], source_positions[end_folded] + 1


def _bounded_snippet(
    line: str,
    *,
    match_start: int,
    match_end: int,
    max_characters: int,
) -> str:
    if len(line) <= max_characters:
        return line
    match_width = max(1, match_end - match_start)
    available = max(0, max_characters - min(match_width, max_characters))
    window_start = max(0, match_start - (available // 2))
    window_start = min(window_start, len(line) - max_characters)
    return line[window_start : window_start + max_characters]


def _search_bound_repository(
    binding: ResolvedRepositoryBinding,
    *,
    normalized_query: str,
    result_limit: int,
    limits: RepositorySearchLimits,
    monotonic: Callable[[], float] = time.monotonic,
    deadline: float | None = None,
) -> RepositorySearchResult:
    """Search only one typed, validated binding root under fixed bounds."""
    if not isinstance(binding, ResolvedRepositoryBinding):
        raise TypeError("repository search requires ResolvedRepositoryBinding")
    resolved_deadline = deadline or (
        monotonic() + limits.max_wall_clock_seconds
    )
    if _remaining_seconds(resolved_deadline, monotonic) <= 0:
        return RepositorySearchResult(
            matches=(),
            count=0,
            truncated=True,
            stop_reason=STOP_REASON_TIMEOUT_REACHED,
            scanned_files=0,
            scanned_bytes=0,
            skipped_binary_files=0,
            skipped_oversized_files=0,
            skipped_sensitive_files=0,
            skipped_symlink_files=0,
        )
    enumeration = _enumerate_repository_paths(
        binding.canonical_root,
        deadline=resolved_deadline,
        limits=limits,
        monotonic=monotonic,
    )

    matches: list[RepositorySearchMatch] = []
    scanned_files = 0
    scanned_bytes = 0
    skipped_binary_files = 0
    skipped_oversized_files = 0
    skipped_sensitive_files = 0
    skipped_symlink_files = 0
    stop_reason = enumeration.stop_reason
    query_casefold = normalized_query.casefold()

    for relative_path in enumeration.paths:
        if stop_reason != STOP_REASON_COMPLETED:
            break
        if _remaining_seconds(resolved_deadline, monotonic) <= 0:
            stop_reason = STOP_REASON_TIMEOUT_REACHED
            break
        if _is_sensitive_path(relative_path):
            skipped_sensitive_files += 1
            continue

        candidate, rejected_symlink = _resolved_regular_file(
            binding.canonical_root, relative_path
        )
        if rejected_symlink:
            skipped_symlink_files += 1
            continue
        if candidate is None:
            continue
        try:
            size = candidate.stat().st_size
        except OSError:
            continue
        if size > limits.max_individual_file_bytes:
            skipped_oversized_files += 1
            continue
        if scanned_bytes + size > limits.max_aggregate_file_bytes:
            stop_reason = STOP_REASON_BYTE_LIMIT_REACHED
            break
        if _remaining_seconds(resolved_deadline, monotonic) <= 0:
            stop_reason = STOP_REASON_TIMEOUT_REACHED
            break
        try:
            content = candidate.read_bytes()
        except OSError:
            continue
        scanned_files += 1
        scanned_bytes += len(content)
        if b"\0" in content:
            skipped_binary_files += 1
            continue
        try:
            text = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            skipped_binary_files += 1
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            span = _casefold_match_span(line, query_casefold)
            if span is None:
                continue
            matches.append(
                RepositorySearchMatch(
                    path=relative_path,
                    line=line_number,
                    snippet=_bounded_snippet(
                        line,
                        match_start=span[0],
                        match_end=span[1],
                        max_characters=limits.max_snippet_characters,
                    ),
                )
            )
            if len(matches) >= result_limit:
                stop_reason = STOP_REASON_RESULT_LIMIT_REACHED
                break
        if stop_reason != STOP_REASON_COMPLETED:
            break

    return RepositorySearchResult(
        matches=tuple(matches),
        count=len(matches),
        truncated=stop_reason != STOP_REASON_COMPLETED,
        stop_reason=stop_reason,
        scanned_files=scanned_files,
        scanned_bytes=scanned_bytes,
        skipped_binary_files=skipped_binary_files,
        skipped_oversized_files=skipped_oversized_files,
        skipped_sensitive_files=skipped_sensitive_files,
        skipped_symlink_files=skipped_symlink_files,
    )


def search_project_repository(
    session: Session,
    *,
    authenticated_account_id: str | None,
    project_id: int,
    query: str,
    result_limit: int = MAX_RETURNED_MATCHES,
) -> RepositorySearchResult:
    """Resolve Project authority, then run one bounded read-only search."""
    active_limits = RepositorySearchLimits()
    started_at = time.monotonic()
    deadline = started_at + active_limits.max_wall_clock_seconds
    try:
        binding = resolve_project_repository_binding(
            session,
            authenticated_account_id=authenticated_account_id,
            project_id=project_id,
            timeout_seconds=active_limits.max_wall_clock_seconds,
        )
    except (AccountProjectMismatch, ProjectNotFound):
        raise
    except RepositoryAuthorityError as exc:
        raise RepositorySearchUnavailable(
            "repository search authority is unavailable"
        ) from exc

    normalized_query = _normalize_query(query, limits=active_limits)
    requested_limit = _validate_result_limit(result_limit, limits=active_limits)
    return _search_bound_repository(
        binding,
        normalized_query=normalized_query,
        result_limit=requested_limit,
        limits=active_limits,
        deadline=deadline,
    )
