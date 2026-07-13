#!/usr/bin/env python3
"""Collect bounded machine and Git identity for a future audit manifest.

This module observes local identity only. It does not produce an evidence
manifest, execute a proof, or mutate Git or filesystem state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


RESULT_SCHEMA_VERSION = "canonical_audit_evidence_identity_result.v1"
COLLECTOR_VERSION = "canonical_audit_evidence_identity_collector.v1"
DEFAULT_TIMEOUT_SECONDS = 5.0
VALID_MACHINE_ROLES = {
    "canonical_evidence_host",
    "provisional_development_host",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CollectorError(Exception):
    """A stable, user-safe collector failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _safe_text(value: str) -> str:
    """Keep subprocess errors bounded and free of environment-like content."""
    text = " ".join(value.split())
    text = re.sub(r"(?i)(https?://)([^/@\s]+):[^/@\s]+@", r"\1[redacted]@", text)
    text = re.sub(r"(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*\S+", r"\1=[redacted]", text)
    return text[:240]


def _hostname() -> str:
    value = socket.gethostname().strip().lower().rstrip(".")
    if not value:
        raise CollectorError("machine_identity_incomplete", "Hostname is empty.")
    return value


def _run_git(repo_path: Path, args: Sequence[str], timeout: float) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CollectorError("git_command_timeout", "A Git identity probe timed out.") from exc
    except OSError as exc:
        raise CollectorError("git_command_failed", "Git could not be executed.") from exc
    if completed.returncode != 0:
        detail = _safe_text(completed.stderr or completed.stdout)
        raise CollectorError(
            "git_command_failed",
            f"A Git identity probe failed{': ' + detail if detail else '.'}",
        )
    return completed.stdout.strip()


def _try_git(repo_path: Path, args: Sequence[str], timeout: float) -> tuple[str | None, str | None]:
    try:
        return _run_git(repo_path, args, timeout), None
    except CollectorError as exc:
        return None, exc.code


def _portable_remote_identity(remotes: list[str], commit_sha: str) -> str:
    safe: list[str] = []
    for remote in remotes:
        value = remote.strip()
        if "@" in value and "://" in value:
            value = re.sub(r"(://)[^/@]+@", r"\1", value)
        if "@" in value and "://" not in value and ":" in value:
            value = value.split("@", 1)[-1]
        safe.append(value)
    basis = "\n".join(sorted(safe)) or f"local:{commit_sha}"
    return f"git:{hashlib.sha256(basis.encode('utf-8')).hexdigest()}"


def _portable_worktree_identity(common_dir: str, commit_sha: str) -> str:
    # The common-dir path is intentionally reduced to a stable Git object.
    # It is an identity token, not a disclosed local path.
    basis = f"git-common-dir:{Path(common_dir).name}:{commit_sha}"
    return f"worktree:{hashlib.sha256(basis.encode('utf-8')).hexdigest()}"


def collect_identity(
    repo_path: str | Path = ".",
    *,
    machine_id: str = "local",
    machine_role: str = "provisional_development_host",
    authority_basis: str = "operator_not_asserted",
    assert_canonical_machine: bool = False,
    diagnostic_working_path: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    hostname: str | None = None,
) -> dict[str, Any]:
    """Return a JSON-serializable, deterministic identity observation."""
    if machine_role not in VALID_MACHINE_ROLES:
        raise CollectorError("invalid_machine_role", "Machine role is not accepted vocabulary.")
    if not machine_id.strip() or not authority_basis.strip():
        raise CollectorError(
            "authority_fields_incomplete",
            "machine_id and authority_basis must be non-empty.",
        )
    if assert_canonical_machine and (
        machine_id != "vaultnode"
        or machine_role != "canonical_evidence_host"
        or not authority_basis.strip()
        ):
        raise CollectorError(
            "canonical_machine_authority_inconsistent",
            "Canonical machine assertion requires compatible explicit authority inputs.",
        )
    safe_machine_id = _safe_text(machine_id.strip())
    safe_authority_basis = _safe_text(authority_basis.strip())

    selected = Path(repo_path).expanduser()
    if not selected.exists() or not selected.is_dir():
        raise CollectorError("path_not_git_worktree", "Path is not a directory in a Git worktree.")
    selected = selected.resolve()
    root_text, root_error = _try_git(selected, ["rev-parse", "--show-toplevel"], timeout)
    if root_text is None:
        raise CollectorError("path_not_git_worktree", "Path is not inside a Git worktree.")
    root = Path(root_text).resolve()

    commit_sha, _ = _try_git(selected, ["rev-parse", "HEAD^{commit}"], timeout)
    if commit_sha is None or not SHA_RE.fullmatch(commit_sha.lower()):
        raise CollectorError("repository_identity_incomplete", "Checked-out commit SHA is incomplete.")
    commit_sha = commit_sha.lower()
    symbolic_head, _ = _try_git(selected, ["symbolic-ref", "--quiet", "--short", "HEAD"], timeout)
    branch = symbolic_head if symbolic_head else "DETACHED_HEAD"
    status = _run_git(selected, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], timeout)
    dirty = bool(status)
    common_dir = _run_git(selected, ["rev-parse", "--git-common-dir"], timeout)
    remotes_raw = _run_git(selected, ["remote", "-v"], timeout)
    remote_lines = [line for line in remotes_raw.splitlines() if line.strip()]
    remote_refs = sorted({line.split()[1] for line in remote_lines if len(line.split()) >= 2})
    upstream_ref, upstream_error = _try_git(
        selected, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], timeout
    )
    configured_upstream = False
    if upstream_ref is None and symbolic_head:
        configured_upstream = bool(
            _try_git(selected, ["config", "--get", f"branch.{symbolic_head}.remote"], timeout)[0]
            and _try_git(selected, ["config", "--get", f"branch.{symbolic_head}.merge"], timeout)[0]
        )
    upstream_sha: str | None = None
    upstream_resolution_error: str | None = None
    if upstream_ref is not None:
        upstream_sha, upstream_resolution_error = _try_git(
            selected, ["rev-parse", "@{upstream}^{commit}"], timeout
        )
        if upstream_sha is not None:
            upstream_sha = upstream_sha.lower()
            if not SHA_RE.fullmatch(upstream_sha):
                upstream_sha = None
                upstream_resolution_error = "repository_identity_incomplete"

    machine = {
        "machine_id": safe_machine_id,
        "machine_role": machine_role,
        "hostname": (hostname.strip().lower().rstrip(".") if hostname is not None else _hostname()),
        "authority_basis": safe_authority_basis,
        "authority_assertion_complete": (
            machine_id == "vaultnode" and machine_role == "canonical_evidence_host" and bool(authority_basis.strip())
        ),
    }
    repository: dict[str, Any] = {
        "repository_root_identity": _portable_remote_identity(remote_refs, commit_sha),
        "branch": branch,
        "commit_sha": commit_sha,
        "upstream_ref": upstream_ref,
        "upstream_sha": upstream_sha,
        "dirty": dirty,
        "worktree_identity": _portable_worktree_identity(common_dir, commit_sha),
    }
    if diagnostic_working_path:
        repository["diagnostic_working_path"] = str(selected)

    reason_codes: list[str] = []
    if not machine["authority_assertion_complete"]:
        reason_codes.append("canonical_machine_authority_not_asserted")
    if symbolic_head is None:
        reason_codes.append("detached_head")
    if branch != "main":
        reason_codes.append("wrong_branch")
    if dirty:
        reason_codes.append("dirty_worktree")
    if upstream_ref is None and not configured_upstream:
        reason_codes.append("missing_upstream")
    if upstream_ref is None and configured_upstream:
        reason_codes.append("unresolved_upstream")
    if upstream_ref is not None and upstream_sha is None:
        reason_codes.append("unresolved_upstream")
    if upstream_sha is not None and upstream_sha != commit_sha:
        reason_codes.append("commit_upstream_mismatch")
    if upstream_error == "git_command_timeout" or upstream_resolution_error == "git_command_timeout":
        reason_codes.append("git_command_timeout")
    if upstream_error == "git_command_failed" or upstream_resolution_error == "git_command_failed":
        reason_codes.append("git_command_failed")
    reason_codes = sorted(set(reason_codes))

    repository_identity_complete = bool(
        branch
        and SHA_RE.fullmatch(commit_sha)
        and upstream_ref
        and upstream_sha
        and SHA_RE.fullmatch(upstream_sha)
    )
    canonical_repository_candidate = repository_identity_complete and not any(
        code in reason_codes
        for code in ("detached_head", "wrong_branch", "dirty_worktree", "missing_upstream", "unresolved_upstream", "commit_upstream_mismatch")
    )
    observation_complete = repository_identity_complete and bool(machine["hostname"])
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "observation_complete": observation_complete,
        "machine": machine,
        "repository": repository,
        "eligibility": {
            "repository_identity_complete": repository_identity_complete,
            "canonical_repository_candidate": canonical_repository_candidate,
            "canonical_machine_candidate": bool(machine["authority_assertion_complete"]),
            "reason_codes": reason_codes,
        },
    }


# Descriptive public alias for callers that prefer the task-level name.
collect_canonical_evidence_identity = collect_identity


def _error_result(exc: CollectorError) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "observation_complete": False,
        "error": {"code": exc.code, "message": exc.message},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect bounded canonical audit evidence identity.")
    parser.add_argument("--repo", default=".", help="Repository or directory inside a Git worktree.")
    parser.add_argument("--machine-id", default="local")
    parser.add_argument("--machine-role", default="provisional_development_host")
    parser.add_argument("--authority-basis", default="operator_not_asserted")
    parser.add_argument("--assert-canonical-machine", action="store_true")
    parser.add_argument("--diagnostic-working-path", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        result = collect_identity(
            args.repo,
            machine_id=args.machine_id,
            machine_role=args.machine_role,
            authority_basis=args.authority_basis,
            assert_canonical_machine=args.assert_canonical_machine,
            diagnostic_working_path=args.diagnostic_working_path,
            timeout=args.timeout,
        )
    except CollectorError as exc:
        print(json.dumps(_error_result(exc), indent=2, sort_keys=True))
        return 2 if exc.code in {"path_not_git_worktree", "git_command_failed", "git_command_timeout", "invalid_machine_role", "authority_fields_incomplete", "canonical_machine_authority_inconsistent"} else 1
    print(json.dumps(result, indent=2, sort_keys=True))
    eligible = result["eligibility"]
    only_provisional_reason = eligible["reason_codes"] == [
        "canonical_machine_authority_not_asserted"
    ]
    return 0 if result["observation_complete"] and (
        eligible["canonical_repository_candidate"] or only_provisional_reason
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
