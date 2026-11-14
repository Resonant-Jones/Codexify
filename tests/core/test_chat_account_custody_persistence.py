"""Isolated helper tests: no deployed database or authenticated route claims."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from guardian.core.db import create_chat_completion_attempt


def _db(owner="account-a", account="account-a"):
    session = Mock()
    session.query.return_value.filter_by.return_value.with_for_update.return_value.scalar.side_effect = [
        owner,
        account,
    ]

    @contextmanager
    def scope():
        yield session

    return SimpleNamespace(_sa_session=scope), session


def _create(db, **kwargs):
    create_chat_completion_attempt(
        db,
        request_id="req-1",
        backend_task_id="task-1",
        thread_id=1,
        turn_id="turn-1",
        **kwargs,
    )


def test_persists_explicit_matching_custody():
    db, session = _db()
    _create(db, accepted_account_id="account-a")
    row = session.add.call_args.args[0]
    assert row.accepted_account_id == "account-a"
    assert (row.request_id, row.backend_task_id, row.thread_id, row.turn_id) == (
        "req-1",
        "task-1",
        1,
        "turn-1",
    )
    assert (
        session.query.return_value.filter_by.return_value.with_for_update.call_count
        == 2
    )


@pytest.mark.parametrize(
    "owner,account",
    [(None, "account-a"), ("account-b", "account-a"), ("account-a", None)],
)
def test_rejects_missing_or_conflicting_canonical_owner(owner, account):
    db, session = _db(owner, account)
    with pytest.raises(ValueError, match="custody unavailable"):
        _create(db, accepted_account_id="account-a")
    session.add.assert_not_called()


@pytest.mark.parametrize(
    "value", ["", " ", " a", "a ", "a b", "a\n", "a\x00", "a\x7f", "a" * 256, 1, True]
)
def test_rejects_invalid_snapshot_without_database_use(value):
    db, session = _db()
    with pytest.raises(ValueError, match="Invalid accepted account custody"):
        _create(db, accepted_account_id=value)
    session.query.assert_not_called()
    session.add.assert_not_called()


def test_legacy_creation_keeps_null_without_inventing_authority():
    db, session = _db()
    _create(db)
    assert session.add.call_args.args[0].accepted_account_id is None
    session.query.assert_not_called()


def test_bounded_255_character_canonical_id_is_preserved():
    account = "a" * 255
    db, session = _db(account, account)
    _create(db, accepted_account_id=account)
    assert session.add.call_args.args[0].accepted_account_id == account
