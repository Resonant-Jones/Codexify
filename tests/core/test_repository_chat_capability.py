from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace
from typing import Any

import pytest

from guardian.core import repository_chat_capability as capability
from guardian.core.repository_authority import BindingResolutionFailed


class _Session:
    def __init__(self) -> None:
        self.commits = 0
        self.adds = 0

    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def add(self, _value: Any) -> None:
        self.adds += 1


class _ChatDb:
    def __init__(self, thread: Any = None) -> None:
        self.thread = thread
        self.session = _Session()
        self.thread_calls: list[int] = []

    def get_chat_thread(self, thread_id: int) -> Any:
        self.thread_calls.append(thread_id)
        return self.thread

    def get_session(self) -> _Session:
        return self.session


def _owned_thread(*, project_id: Any = 11, user_id: str = "account-a") -> dict[str, Any]:
    return {"id": 7, "user_id": user_id, "project_id": project_id}


def _resolve(
    monkeypatch: pytest.MonkeyPatch,
    *,
    error: Exception | None = None,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def _resolver(session: Any, **kwargs: Any) -> SimpleNamespace:
        calls.append({"session": session, **kwargs})
        if error is not None:
            raise error
        return SimpleNamespace(binding_id="binding-private", canonical_root="/private")

    monkeypatch.setattr(
        capability,
        "resolve_project_repository_binding",
        _resolver,
    )
    return calls


@pytest.mark.parametrize(
    ("account_id", "thread_id"),
    [
        ("", 7),
        ("   ", 7),
        (None, 7),
        ("account-a", 0),
        ("account-a", -1),
        ("account-a", True),
        ("account-a", "7"),
    ],
)
def test_missing_authenticated_account_or_invalid_thread_returns_no_context(
    account_id: str | None,
    thread_id: Any,
) -> None:
    db = _ChatDb(_owned_thread())

    assert (
        capability.resolve_repository_chat_capability(
            db,
            authenticated_account_id=account_id,
            thread_id=thread_id,
        )
        is None
    )
    assert db.thread_calls == []


def test_missing_chat_db_or_required_seams_returns_no_context() -> None:
    assert (
        capability.resolve_repository_chat_capability(
            None,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )
    assert (
        capability.resolve_repository_chat_capability(
            object(),
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )

    db_without_session = SimpleNamespace(
        get_chat_thread=lambda _thread_id: _owned_thread()
    )
    assert (
        capability.resolve_repository_chat_capability(
            db_without_session,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )


@pytest.mark.parametrize(
    "thread",
    [None, [], "not-a-thread", {"user_id": "account-b", "project_id": 11}],
)
def test_missing_invalid_or_cross_account_thread_returns_no_context(thread: Any) -> None:
    db = _ChatDb(thread)

    assert (
        capability.resolve_repository_chat_capability(
            db,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )


@pytest.mark.parametrize("project_id", [None, 0, -1, True, "11", 1.5])
def test_missing_or_invalid_thread_project_id_returns_no_context(project_id: Any) -> None:
    db = _ChatDb(_owned_thread(project_id=project_id))

    assert (
        capability.resolve_repository_chat_capability(
            db,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )


def test_valid_owned_thread_and_binding_returns_only_project_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _ChatDb(_owned_thread(project_id=42))
    calls = _resolve(monkeypatch)

    context = capability.resolve_repository_chat_capability(
        db,
        authenticated_account_id="account-a",
        thread_id=7,
    )

    assert context == capability.RepositoryChatCapabilityContext(project_id=42)
    assert [field.name for field in fields(context)] == ["project_id"]
    assert not hasattr(context, "binding_id")
    assert not hasattr(context, "canonical_root")
    assert calls == [
        {
            "session": db.session,
            "authenticated_account_id": "account-a",
            "project_id": 42,
        }
    ]


@pytest.mark.parametrize(
    "error",
    [
        BindingResolutionFailed("no active binding"),
        RuntimeError("database unavailable"),
    ],
)
def test_missing_stale_ambiguous_or_unexpected_binding_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    db = _ChatDb(_owned_thread())
    _resolve(monkeypatch, error=error)

    assert (
        capability.resolve_repository_chat_capability(
            db,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )
    assert db.session.commits == 0
    assert db.session.adds == 0


def test_thread_lookup_failure_fails_closed_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _ChatDb(_owned_thread())
    _resolve(monkeypatch)

    def _raise(_thread_id: int) -> None:
        raise RuntimeError("lookup failed")

    db.get_chat_thread = _raise  # type: ignore[method-assign]
    assert (
        capability.resolve_repository_chat_capability(
            db,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )
    assert db.session.commits == 0
    assert db.session.adds == 0


def test_resolution_never_mutates_thread_or_uses_fallback_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread = _owned_thread(project_id=19)
    snapshot = dict(thread)
    db = _ChatDb(thread)
    _resolve(monkeypatch, error=BindingResolutionFailed("repository-less"))

    assert (
        capability.resolve_repository_chat_capability(
            db,
            authenticated_account_id="account-a",
            thread_id=7,
        )
        is None
    )
    assert thread == snapshot
    assert db.session.commits == 0
    assert db.session.adds == 0
    source = open(capability.__file__, encoding="utf-8").read()
    for forbidden in (
        "Path.cwd()",
        "detect_project_root",
        "CODEXIFY_WORKTREE_REPO_PATH",
        "get_recent_thread",
        "discovery_candidate",
    ):
        assert forbidden not in source
