"""Opt-in disposable PostgreSQL proof; never target an existing service database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from guardian.db.models import (
    Base,
    User,
    ChatThread,
    ChatCompletionAttempt,
    InferenceBudgetWindow,
)
from guardian.metering.budget import BudgetLedger, soft_thresholds

QUOTE = dict(
    version="test-v1",
    source="https://example.invalid/test-prices",
    effective_at="2026-01-01T00:00:00Z",
    unit_contract="bounded_text_tokens_only",
    input_usd_per_million="1",
    output_usd_per_million="2",
    cached_input_usd_per_million="0.5",
)


@pytest.fixture
def budget_db():
    url = os.getenv("CODEXIFY_BUDGET_TEST_DATABASE_URL")
    if not url:
        pytest.skip("explicit disposable PostgreSQL URL required")
    engine = create_engine(url)
    schema = "budget_test_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    # This fixture creates and drops ONLY its random schema, never a database.
    scoped = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(scoped)
        sessions = sessionmaker(scoped, expire_on_commit=False)
        with sessions.begin() as session:
            for n, account in enumerate(("one", "two"), 1):
                session.add(
                    User(
                        id=account,
                        username=account,
                        password_hash="unused",
                        role="guest",
                    )
                )
                session.flush()
                session.add(ChatThread(id=n, user_id=account, title="synthetic"))
                session.flush()
                session.add(
                    ChatCompletionAttempt(
                        request_id=account,
                        backend_task_id=account,
                        thread_id=n,
                        turn_id=account,
                        accepted_account_id=account,
                        accepted_at=datetime.now(timezone.utc),
                    )
                )
            now = datetime.now(timezone.utc)
            for id, kind, provider, cap in [
                ("month", "monthly", "*", 100_000_000),
                ("funding", "funding", "openai", 49_000_000),
            ]:
                session.add(
                    InferenceBudgetWindow(
                        id=id,
                        kind=kind,
                        payer_scope="operator",
                        provider=provider,
                        starts_at=now - timedelta(days=1),
                        ends_at=now + timedelta(days=30),
                        enabled=True,
                        limit_units=cap,
                    )
                )
        yield BudgetLedger(sessions), sessions
    finally:
        scoped.dispose()
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def reserve(ledger, id="attempt", **overrides):
    args = dict(
        attempt_id=id,
        account_id="one",
        request_id="one",
        payer_scope="operator",
        provider="openai",
        model="actual-dispatched-model",
        budget_ids=["month", "funding"],
        input_ceiling=1000,
        output_ceiling=1000,
        quote=QUOTE,
    )
    args.update(overrides)
    return ledger.reserve(**args)


def totals(sessions):
    with sessions() as session:
        return {
            w.id: (w.held_units, w.spent_units)
            for w in session.scalars(select(InferenceBudgetWindow))
        }


def response(input=100, output=50):
    return {
        "id": "synthetic-provider-response",
        "usage": {"prompt_tokens": input, "completion_tokens": output},
    }


def test_concurrent_reservation_never_exceeds_funding(budget_db):
    ledger, sessions = budget_db

    def admit(n):
        try:
            reserve(ledger, str(n))
            return True
        except PermissionError as exc:
            assert str(exc) == "budget_exhausted"
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(admit, range(40)))
    assert sum(results) == 16  # 16 * .003 fits .049; 17 does not.
    assert totals(sessions) == {"month": (48_000_000, 0), "funding": (48_000_000, 0)}


def test_duplicate_admission_and_single_claim(budget_db):
    ledger, sessions = budget_db
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(lambda _: reserve(ledger), range(12))) == [3_000_000] * 12
    assert totals(sessions)["month"] == (3_000_000, 0)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert (
            sum(
                pool.map(
                    lambda _: ledger.claim(attempt_id="attempt", account_id="one"),
                    range(12),
                )
            )
            == 1
        )
    assert not ledger.release_unclaimed(attempt_id="attempt", account_id="one")
    with pytest.raises(ValueError, match="idempotency_conflict"):
        reserve(ledger, output_ceiling=1001)


def test_unknown_error_disconnect_and_crash_hold(budget_db):
    ledger, sessions = budget_db
    reserve(ledger)
    assert ledger.claim(attempt_id="attempt", account_id="one")
    for output in (
        {},
        {"usage": {"prompt_tokens": 50}},
        {"usage": {"prompt_tokens": -1, "completion_tokens": 2}},
    ):
        assert not ledger.settle(attempt_id="attempt", account_id="one", output=output)
        assert totals(sessions)["month"] == (3_000_000, 0)
    # Fresh ledger process cannot reclaim a potentially dispatched attempt.
    assert not BudgetLedger(sessions).claim(attempt_id="attempt", account_id="one")
    assert not ledger.release_unclaimed(attempt_id="attempt", account_id="one")


def test_settlement_idempotency_and_overrun_truth(budget_db):
    ledger, sessions = budget_db
    reserve(ledger)
    ledger.claim(attempt_id="attempt", account_id="one")
    assert ledger.settle(attempt_id="attempt", account_id="one", output=response())
    assert ledger.settle(attempt_id="attempt", account_id="one", output=response())
    assert totals(sessions)["month"] == (0, 200_000)
    with pytest.raises(ValueError, match="settlement_conflict"):
        ledger.settle(attempt_id="attempt", account_id="one", output=response(101))
    reserve(ledger, "overrun")
    ledger.claim(attempt_id="overrun", account_id="one")
    ledger.settle(
        attempt_id="overrun", account_id="one", output=response(100_000, 100_000)
    )
    assert totals(sessions)["funding"] == (0, 300_200_000)
    with pytest.raises(PermissionError, match="exhausted"):
        reserve(ledger, "blocked")


def test_isolation_scope_and_expiry(budget_db):
    ledger, sessions = budget_db
    with pytest.raises(PermissionError, match="custody"):
        reserve(ledger, account_id="two")
    with pytest.raises(PermissionError, match="scope"):
        reserve(ledger, payer_scope="customer")
    reserve(ledger)
    with pytest.raises(PermissionError, match="not_owned"):
        ledger.claim(attempt_id="attempt", account_id="two")
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "month").enabled = False
    with pytest.raises(PermissionError, match="inactive"):
        ledger.claim(attempt_id="attempt", account_id="one")
    assert ledger.release_unclaimed(attempt_id="attempt", account_id="one")
    assert not ledger.release_unclaimed(attempt_id="attempt", account_id="one")
    assert totals(sessions)["month"] == (0, 0)


def test_missing_price_and_free_claims_rejected(budget_db):
    ledger, sessions = budget_db
    for key in ("version", "source", "effective_at"):
        quote = QUOTE | {key: ""}
        with pytest.raises(ValueError, match="provenance"):
            reserve(ledger, quote=quote)
    with pytest.raises(ValueError, match="billing_units"):
        reserve(ledger, quote=QUOTE | {"unit_contract": "tools_and_media"})
    with pytest.raises(ValueError):
        reserve(ledger, quote=QUOTE | {"input_usd_per_million": "NaN"})
    assert totals(sessions)["month"] == (0, 0)


def test_migration_roundtrip(budget_db):
    _, sessions = budget_db
    path = (
        Path(__file__).resolve().parents[2]
        / "guardian/db/migrations/versions/e723ba9046cd_inference_budget_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("budget_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sessions.kw["bind"]
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            migration.upgrade()
    with sessions() as session:
        assert list(session.scalars(select(InferenceBudgetWindow))) == []


def test_soft_thresholds_never_deny():
    result = soft_thresholds(observed_units=12, held_units=8, allowance_units=10)
    assert result == dict(
        reached_percent=[50, 80, 100],
        estimated_spend_units=12,
        unsettled_hold_units=8,
        deny_inference=False,
    )


def test_second_window_failure_rolls_back_all_counters(budget_db):
    ledger, sessions = budget_db
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "month").limit_units = 1
    with pytest.raises(PermissionError, match="exhausted"):
        reserve(ledger)
    assert totals(sessions) == {"month": (0, 0), "funding": (0, 0)}


def test_model_mismatch_retains_hold(budget_db):
    ledger, sessions = budget_db
    reserve(ledger)
    ledger.claim(attempt_id="attempt", account_id="one")
    assert not ledger.settle(
        attempt_id="attempt",
        account_id="one",
        output=response() | {"model": "different-actual-model"},
    )
    assert totals(sessions)["month"] == (3_000_000, 0)


def test_custody_revocation_blocks_dispatch_not_account_access(budget_db):
    ledger, sessions = budget_db
    reserve(ledger)
    with sessions.begin() as session:
        session.get(ChatCompletionAttempt, "one").accepted_account_id = None
    with pytest.raises(PermissionError, match="custody"):
        ledger.claim(attempt_id="attempt", account_id="one")
    with sessions() as session:
        assert session.get(ChatThread, 1).user_id == "one"
        assert session.get(User, "one") is not None


def test_expired_month_retains_unknown_liability_and_settlement(budget_db):
    ledger, sessions = budget_db
    reserve(ledger)
    ledger.claim(attempt_id="attempt", account_id="one")
    with sessions.begin() as session:
        window = session.get(InferenceBudgetWindow, "month")
        window.ends_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert not ledger.settle(attempt_id="attempt", account_id="one", output={})
    assert totals(sessions)["month"] == (3_000_000, 0)
    assert ledger.settle(attempt_id="attempt", account_id="one", output=response())
    assert totals(sessions)["month"] == (0, 200_000)


def test_quote_snapshot_cannot_be_repriced_by_duplicate(budget_db):
    ledger, sessions = budget_db
    reserve(ledger)
    with pytest.raises(ValueError, match="idempotency_conflict"):
        reserve(ledger, quote=QUOTE | {"version": "v2", "output_usd_per_million": "50"})
    assert totals(sessions)["month"] == (3_000_000, 0)


def test_overrun_blocks_already_reserved_dispatch(budget_db):
    ledger, sessions = budget_db
    reserve(ledger, "a")
    reserve(ledger, "b")
    ledger.claim(attempt_id="a", account_id="one")
    ledger.settle(attempt_id="a", account_id="one", output=response(100_000, 100_000))
    with pytest.raises(PermissionError, match="exhausted"):
        ledger.claim(attempt_id="b", account_id="one")
    assert ledger.release_unclaimed(attempt_id="b", account_id="one")
