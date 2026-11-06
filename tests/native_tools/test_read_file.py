"""Tests for the native ``native::fs::read_file`` command.

The command is read-only, in process, and self-authorizing: it resolves the
Project's repository binding for the authenticated account itself, so a
forged scope fails closed instead of widening the grant.
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

from guardian.command_bus.contracts import InvokeArguments
from guardian.core.repository_authority import (
    SOURCE_CLASS_EXTERNAL_LINKED,
    ResolvedRepositoryBinding,
)
from guardian.native_tools import command_specs as native_command_specs
from guardian.native_tools.handlers import read_file as read_file_handler
from guardian.native_tools.handlers.read_file import (
    MAX_FILE_BYTES,
    MAX_FILE_LINES,
    NativeToolError,
)

ACCOUNT_ID = "account-1"
PROJECT_ID = 7


class _FakeChatLogDB:
    """Minimal stand-in for the read authority store."""

    def __init__(self) -> None:
        self.session_opened = 0

    @contextmanager
    def get_session(self) -> Iterator[Any]:
        self.session_opened += 1
        yield object()


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text(
        "line one\nline two\nline three\n", encoding="utf-8"
    )
    return root


@pytest.fixture()
def fake_store(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> _FakeChatLogDB:
    store = _FakeChatLogDB()
    monkeypatch.setattr(
        "guardian.core.dependencies.chatlog_db",
        store,
        raising=False,
    )
    monkeypatch.setattr(
        "guardian.core.repository_authority.resolve_project_repository_binding",
        lambda *_args, **_kwargs: ResolvedRepositoryBinding(
            binding_id="binding-1",
            project_id=PROJECT_ID,
            source_class=SOURCE_CLASS_EXTERNAL_LINKED,
            canonical_root=repo_root,
        ),
    )
    return store


def _arguments(
    *,
    path: str | None = None,
    project_id: int | None = PROJECT_ID,
    extra: dict[str, Any] | None = None,
) -> InvokeArguments:
    body: dict[str, Any] = {}
    if path is not None:
        body["path"] = path
    if project_id is not None:
        body["scope"] = {"project_id": project_id}
    if extra:
        body.update(extra)
    return InvokeArguments(path_params={}, query={}, headers={}, body=body)


def _read(
    *,
    path: str | None = None,
    project_id: int | None = PROJECT_ID,
    extra: dict[str, Any] | None = None,
    auth_subject: str | None = ACCOUNT_ID,
) -> dict[str, Any]:
    return read_file_handler.execute_read_file(
        arguments=_arguments(path=path, project_id=project_id, extra=extra),
        auth_subject=auth_subject,
    )


# --- happy path ------------------------------------------------------------


def test_reads_a_project_file_as_line_numbered_text(fake_store: _FakeChatLogDB) -> None:
    result = _read(path="src/app.py")

    assert result["path"] == "src/app.py"
    assert result["content"] == "1\tline one\n2\tline two\n3\tline three\n"
    assert result["total_lines"] == 3
    assert result["returned_lines"] == 3
    assert result["truncated"] is False


def test_reading_binds_the_project_for_the_authenticated_account(
    fake_store: _FakeChatLogDB,
) -> None:
    _read(path="src/app.py")
    # The binding resolver is consulted on every call, never cached from the
    # caller's arguments.
    assert fake_store.session_opened == 1


def test_reading_is_repeatable(fake_store: _FakeChatLogDB) -> None:
    first = _read(path="src/app.py")
    second = _read(path="src/app.py")
    assert first == second


# --- containment ------------------------------------------------------------


def test_refuses_a_path_that_escapes_the_project_root(
    fake_store: _FakeChatLogDB,
) -> None:
    with pytest.raises(NativeToolError):
        _read(path="../../etc/passwd")


def test_refuses_an_absolute_path(fake_store: _FakeChatLogDB) -> None:
    with pytest.raises(NativeToolError):
        _read(path="/etc/passwd")


def test_refuses_a_symlink_that_points_outside_the_project(
    fake_store: _FakeChatLogDB,
    repo_root: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (repo_root / "link.txt").symlink_to(outside)

    with pytest.raises(NativeToolError):
        _read(path="link.txt")


def test_refuses_a_sensitive_filename(fake_store: _FakeChatLogDB, repo_root: Path) -> None:
    (repo_root / ".env").write_text("SECRET=1\n", encoding="utf-8")

    with pytest.raises(NativeToolError):
        _read(path=".env")


def test_refuses_a_directory(fake_store: _FakeChatLogDB) -> None:
    with pytest.raises(NativeToolError):
        _read(path="src")


def test_refuses_a_missing_file(fake_store: _FakeChatLogDB) -> None:
    with pytest.raises(NativeToolError):
        _read(path="src/missing.py")


# --- authority --------------------------------------------------------------


def test_refuses_a_request_with_no_scope(fake_store: _FakeChatLogDB) -> None:
    with pytest.raises(NativeToolError):
        _read(path="src/app.py", project_id=None)


def test_refuses_an_unauthenticated_request(fake_store: _FakeChatLogDB) -> None:
    with pytest.raises(NativeToolError):
        _read(path="src/app.py", auth_subject="")


def test_refuses_a_forged_scope_that_the_account_does_not_own(
    monkeypatch: pytest.MonkeyPatch,
    fake_store: _FakeChatLogDB,
) -> None:
    def _refuse(*_args: Any, **_kwargs: Any) -> ResolvedRepositoryBinding:
        raise RuntimeError("binding mismatch")

    monkeypatch.setattr(
        "guardian.core.repository_authority.resolve_project_repository_binding",
        _refuse,
    )

    with pytest.raises(NativeToolError):
        _read(path="src/app.py", project_id=999)


def test_refuses_when_no_authority_store_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "guardian.core.dependencies.chatlog_db",
        None,
        raising=False,
    )

    with pytest.raises(NativeToolError):
        _read(path="src/app.py")


# --- bounds -----------------------------------------------------------------


def test_bounds_the_number_of_returned_lines(
    fake_store: _FakeChatLogDB,
    repo_root: Path,
) -> None:
    (repo_root / "big.txt").write_text(
        "".join(f"line {index}\n" for index in range(MAX_FILE_LINES + 50)),
        encoding="utf-8",
    )

    result = _read(path="big.txt")

    assert result["returned_lines"] == MAX_FILE_LINES
    assert result["truncated"] is True
    assert result["total_lines"] == MAX_FILE_LINES + 50


def test_refuses_a_file_over_the_byte_limit(
    fake_store: _FakeChatLogDB,
    repo_root: Path,
) -> None:
    (repo_root / "huge.txt").write_text(
        "x" * (MAX_FILE_BYTES + 1),
        encoding="utf-8",
    )

    with pytest.raises(NativeToolError):
        _read(path="huge.txt")


def test_refuses_a_binary_file(fake_store: _FakeChatLogDB, repo_root: Path) -> None:
    (repo_root / "blob.bin").write_bytes(b"\x00\x01\x02binary")

    with pytest.raises(NativeToolError):
        _read(path="blob.bin")


# --- behaviour guarantees ---------------------------------------------------


def test_reading_writes_nothing(fake_store: _FakeChatLogDB, repo_root: Path) -> None:
    before = sorted(path.name for path in repo_root.rglob("*"))

    _read(path="src/app.py")

    assert sorted(path.name for path in repo_root.rglob("*")) == before


def test_reading_spawns_no_subprocess(
    fake_store: _FakeChatLogDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _forbid(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the native read-file tool must not spawn a subprocess")

    monkeypatch.setattr(subprocess, "run", _forbid)
    monkeypatch.setattr(subprocess, "Popen", _forbid)
    monkeypatch.setattr(subprocess, "check_output", _forbid)

    result = _read(path="src/app.py")

    assert result["total_lines"] == 3


def test_reading_does_not_use_the_network(
    fake_store: _FakeChatLogDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket

    def _forbid(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the native read-file tool must not use the network")

    monkeypatch.setattr(socket, "socket", _forbid)
    monkeypatch.setattr(socket, "create_connection", _forbid)

    result = _read(path="src/app.py")

    assert result["total_lines"] == 3


# --- command declaration ----------------------------------------------------


def test_command_declares_its_own_safety_facts() -> None:
    specs = native_command_specs.build_native_command_specs()

    assert len(specs) == 1
    spec = specs[0]
    assert spec.command_id == native_command_specs.NATIVE_READ_FILE_COMMAND_ID
    assert spec.layer == "internal"
    assert spec.method == "INTERNAL"
    assert spec.path_template == ""
    assert spec.effect == "read"
    assert spec.risk == "read_only"
    assert spec.idempotency == "safe"
    assert spec.approval_mode == "none"
    assert spec.open_world is False
    assert spec.justification


def test_command_body_contract_separates_path_from_scope() -> None:
    spec = native_command_specs.build_native_command_specs()[0]
    body = spec.input_schema["body"]

    assert set(body["properties"]) == {"path", "scope"}
    assert body["required"] == ["path"]
    assert body["additionalProperties"] is False


def test_native_command_ids_are_registered_explicitly() -> None:
    assert native_command_specs.NATIVE_READ_FILE_COMMAND_ID in (
        native_command_specs.NATIVE_COMMAND_IDS
    )
    assert "native::fs::not_a_command" not in native_command_specs.NATIVE_COMMAND_IDS
