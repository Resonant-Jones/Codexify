"""Inactive core proof with synthetic rates and explicitly owned disposable PG.

The neighboring fixture creates/drops only its random schema. No live service,
provider, credential, policy issuer or runtime transport is used by these tests.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import socket

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import delete, inspect, select

from guardian.db.models import (
    ChatCompletionAttempt,
    ChatMessage,
    ChatThread,
    InferenceBudgetWindow,
    Project,
    User,
    VoiceBudgetAllocation,
    VoiceBudgetDispatch,
    VoiceBudgetReservation,
)
from guardian.metering.budget import BudgetLedger
from guardian.metering.tokens import (
    VoiceBillingUnit,
    VoiceBudgetService,
    VoicePayerKind,
)
from guardian.metering import voice_budget as vb
from guardian.metering.voice_budget import (
    VoiceBudgetBinding,
    VoiceBudgetLedger,
    VoicePriceQuote,
    VoicePayerDescriptor,
    assistant_content_hash,
)
from tests.metering import test_inference_budget as existing_budget_tests

TOKEN_QUOTE = existing_budget_tests.QUOTE
budget_db = existing_budget_tests.budget_db

TEXT = "  Synthetic assistant reply — café.  "
WIRE = "d" * 64


@pytest.fixture(autouse=True)
def no_python_network(monkeypatch):
    original = socket.socket.connect

    def connect(sock, address):
        if sock.family != socket.AF_UNIX:
            raise AssertionError("Network forbidden in voice ledger proof")
        return original(sock, address)

    def dns(*args, **kwargs):
        raise AssertionError("DNS forbidden in voice ledger proof")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", dns)


def binding(**changes):
    return replace(
        VoiceBudgetBinding(
            account_id="one",
            thread_id=1,
            project_id=1,
            settings_digest="a" * 64,
            payer=sponsor_payer(),
            policy_digest="b" * 64,
            endpoint="https://api.deepgram.com/v1/speak",
            model="aura-2-jupiter-en",
            message_id=101,
            content_hash=assistant_content_hash(TEXT),
        ),
        **changes,
    )


def sponsor_payer(**changes):
    return replace(
        VoicePayerDescriptor(
            kind=VoicePayerKind.SPONSOR,
            payer_scope="operator",
            credential_ref="synthetic-credential-reference",
        ),
        **changes,
    )


def quote(**changes):
    now = datetime.now(timezone.utc)
    return replace(
        VoicePriceQuote(
            version="synthetic-only-v1",
            source="https://example.invalid/synthetic-price",
            effective_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
            unit_contract=VoiceBillingUnit.SYNTHESIS_CHARACTERS,
            unit_size=1000,
            unit_price_units=3_000_000,
        ),
        **changes,
    )


@pytest.fixture
def voice_db(budget_db):
    _, sessions = budget_db
    with sessions.begin() as session:
        session.add(Project(id=1, user_id="one", name="synthetic-project"))
        session.flush()
        session.get(ChatThread, 1).project_id = 1
        session.add(
            ChatMessage(
                id=101, thread_id=1, user_id="one", role="assistant", content=TEXT
            )
        )
        session.add(
            ChatMessage(
                id=201,
                thread_id=2,
                user_id="two",
                role="assistant",
                content="Foreign synthetic reply",
            )
        )
        now = datetime.now(timezone.utc)
        session.add(
            InferenceBudgetWindow(
                id="voice-funding",
                kind="funding",
                payer_scope="operator",
                provider="deepgram",
                starts_at=now - timedelta(days=1),
                ends_at=now + timedelta(days=30),
                enabled=True,
                limit_units=49_000_000,
            )
        )
    yield VoiceBudgetLedger(sessions), sessions


def reserve(ledger, attempt="voice-attempt", **changes):
    args = dict(
        attempt_id=attempt,
        binding=binding(),
        payer_scope="operator",
        budget_ids=["month", "voice-funding"],
        quantity_ceiling=1000,
        quote=quote(),
        dispatch_digest=WIRE,
    )
    args.update(changes)
    return ledger.reserve(**args)


def claim(ledger, attempt="voice-attempt", **changes):
    return ledger.claim(
        **(dict(attempt_id=attempt, binding=binding(), dispatch_digest=WIRE) | changes)
    )


def settle(ledger, attempt="voice-attempt", **changes):
    return ledger.settle(
        **(
            dict(
                attempt_id=attempt,
                account_id="one",
                observed_quantity=100,
                provider_request_id="synthetic-provider-receipt",
                reported_model="aura-2-jupiter-en",
            )
            | changes
        )
    )


def totals(sessions):
    with sessions() as session:
        return {
            w.id: (w.held_units, w.spent_units)
            for w in session.scalars(select(InferenceBudgetWindow))
        }


def test_quote_rounding_minimum_fixed_and_snapshot():
    q = quote(
        unit_size=3,
        unit_price_units=5,
        quantity_increment=4,
        minimum_quantity=8,
        fixed_units=2,
    )
    assert q.price(0) == 16  # ceil(8*5/3)+2
    assert q.price(9) == 22  # ceil(12*5/3)+2
    assert VoicePriceQuote.from_snapshot(q.snapshot()) == q
    with pytest.raises(FrozenInstanceError):
        q.unit_size = 4


@pytest.mark.parametrize(
    "changes",
    [
        {"unit_contract": "bounded_text_tokens_only"},
        {"unit_size": True},
        {"unit_price_units": 0},
        {"unit_price_units": float("nan")},
        {"quantity_increment": -1},
        {"fixed_units": -1},
        {"minimum_quantity": False},
        {"effective_at": datetime(2026, 1, 1)},
        {"version": ""},
        {"source": ""},
        {"expires_at": datetime(2020, 1, 1, tzinfo=timezone.utc)},
    ],
)
def test_invalid_quotes_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        quote(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"mip_opt_out": False},
        {"mip_opt_out": 1},
        {"settings_digest": ""},
        {"payer": None},
        {"thread_id": True},
        {"project_id": 0},
        {"endpoint": "https://api.deepgram.com/v1/speak?key=forbidden"},
        {"endpoint": "https://user:password@api.deepgram.com/v1/speak"},
        {"endpoint": "https://api.eu.deepgram.com/v1/speak"},
        {"session_id": "session"},
        {"message_id": None},
    ],
)
def test_invalid_bindings_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        binding(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "sponsor"},
        {"payer_scope": ""},
        {"credential_ref": "has spaces"},
        {"owner_account_id": "one"},
        {"kind": VoicePayerKind.ACCOUNT_OWNED},
    ],
)
def test_payer_descriptor_is_mandatory_and_typed(changes):
    with pytest.raises(ValueError):
        sponsor_payer(**changes)


def test_account_payer_requires_exact_invoking_owner():
    payer = VoicePayerDescriptor(
        VoicePayerKind.ACCOUNT_OWNED,
        "account-one-pool",
        "synthetic-account-key-ref",
        "two",
    )
    with pytest.raises(PermissionError, match="payer_account_mismatch"):
        binding(payer=payer)
    assert binding().service == VoiceBudgetService.SPEAK


def account_payer():
    return VoicePayerDescriptor(
        VoicePayerKind.ACCOUNT_OWNED,
        "account-one-pool",
        "synthetic-account-key-ref",
        "one",
    )


def add_account_pools(sessions):
    now = datetime.now(timezone.utc)
    with sessions.begin() as session:
        for id, kind, provider in (
            ("account-month", "monthly", "*"),
            ("account-funding", "funding", "deepgram"),
        ):
            session.add(
                InferenceBudgetWindow(
                    id=id,
                    kind=kind,
                    provider=provider,
                    payer_scope="account-one-pool",
                    starts_at=now - timedelta(days=1),
                    ends_at=now + timedelta(days=1),
                    enabled=True,
                    limit_units=9_000_000,
                )
            )


def test_explicit_payer_scopes_stay_separate_without_fallback(voice_db):
    ledger, sessions = voice_db
    add_account_pools(sessions)
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "voice-funding").limit_units = 1
    with pytest.raises(PermissionError, match="exhausted"):
        reserve(ledger)
    values = totals(sessions)
    assert values["month"] == values["account-month"] == (0, 0)
    payer = account_payer()
    b = binding(payer=payer)
    with pytest.raises(PermissionError, match="payer_scope_mismatch"):
        reserve(ledger, binding=b)
    with pytest.raises(PermissionError, match="scope_mismatch"):
        reserve(ledger, binding=b, payer_scope=payer.payer_scope)
    assert (
        reserve(
            ledger,
            binding=b,
            payer_scope=payer.payer_scope,
            budget_ids=["account-month", "account-funding"],
        )
        == 3_000_000
    )
    assert claim(ledger, binding=b)
    with pytest.raises(PermissionError, match="dispatch_mismatch"):
        claim(ledger)  # No fallback/reclassification of the same paid operation.
    values = totals(sessions)
    assert values["month"] == (0, 0)
    assert values["account-month"] == (3_000_000, 0)


def test_one_committed_claim_and_restart_replay(voice_db):
    ledger, sessions = voice_db
    q = quote()
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert (
            list(pool.map(lambda _: reserve(ledger, quote=q), range(12)))
            == [3_000_000] * 12
        )
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(lambda _: claim(ledger), range(12))) == 1
    assert not claim(VoiceBudgetLedger(sessions))
    assert not ledger.release_unclaimed(attempt_id="voice-attempt", account_id="one")
    with sessions() as session:
        assert len(list(session.scalars(select(VoiceBudgetDispatch)))) == 1
    assert totals(sessions)["month"] == (3_000_000, 0)


@pytest.mark.parametrize(
    "changes",
    [
        {"quantity_ceiling": 1001},
        {"dispatch_digest": "e" * 64},
        {"binding": binding(settings_digest="e" * 64)},
        {"binding": binding(policy_digest="e" * 64)},
        {"binding": binding(payer=sponsor_payer(credential_ref="different-reference"))},
    ],
)
def test_conflicting_reservation_rejected(voice_db, changes):
    ledger, _ = voice_db
    q = quote()
    reserve(ledger, quote=q)
    with pytest.raises(ValueError, match="idempotency_conflict"):
        reserve(ledger, **(dict(quote=q) | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"dispatch_digest": "e" * 64},
        {"binding": binding(settings_digest="e" * 64)},
        {"binding": binding(policy_digest="e" * 64)},
        {"binding": binding(payer=sponsor_payer(credential_ref="different-reference"))},
        {"binding": binding(model="aura-2-phoebe-en")},
    ],
)
def test_claim_requires_exact_saved_descriptor(voice_db, changes):
    ledger, sessions = voice_db
    reserve(ledger)
    with pytest.raises(PermissionError, match="dispatch_mismatch"):
        claim(ledger, **changes)
    assert totals(sessions)["month"] == (3_000_000, 0)


def test_current_canonical_custody_and_content(voice_db):
    ledger, sessions = voice_db
    reserve(ledger)
    with pytest.raises(PermissionError):
        reserve(ledger, "foreign", binding=binding(account_id="two"))
    with pytest.raises(PermissionError):
        claim(ledger, binding=binding(account_id="two"))
    with sessions.begin() as session:
        session.get(ChatMessage, 101).content = "Changed body"
    with pytest.raises(PermissionError, match="message_custody"):
        claim(ledger)
    with sessions.begin() as session:
        session.get(ChatMessage, 101).content = TEXT
        session.get(ChatMessage, 101).role = "user"
    with pytest.raises(PermissionError, match="message_custody"):
        claim(ledger)
    with sessions.begin() as session:
        session.get(ChatMessage, 101).role = "assistant"
        session.get(ChatMessage, 101).user_id = "two"
    with pytest.raises(PermissionError, match="message_custody"):
        claim(ledger)


@pytest.mark.parametrize(
    "mutation",
    [
        "thread_owner",
        "thread_project",
        "project_owner",
        "project_conflict",
        "thread_archive",
        "project_archive",
    ],
)
def test_live_thread_project_changes_revoke_claim(voice_db, mutation):
    ledger, sessions = voice_db
    reserve(ledger)
    with sessions.begin() as session:
        thread, project = session.get(ChatThread, 1), session.get(Project, 1)
        if mutation == "thread_owner":
            thread.user_id = "two"
        elif mutation == "thread_project":
            thread.project_id = None
        elif mutation == "project_owner":
            project.user_id = "two"
        elif mutation == "project_conflict":
            project.description = json.dumps(
                {"__codexify_project_owner__": True, "owner_user_id": "two"}
            )
        elif mutation == "thread_archive":
            thread.archived_at = datetime.now(timezone.utc)
        else:
            project.archived_at = datetime.now(timezone.utc)
    with pytest.raises(PermissionError, match="custody"):
        claim(ledger)


def test_preview_eligibility_is_current(voice_db, monkeypatch):
    ledger, _ = voice_db
    reserve(ledger)
    monkeypatch.setattr(vb, "is_private_preview", lambda: True)
    monkeypatch.setattr(vb, "role_for_preview_email", lambda _: None)
    with pytest.raises(PermissionError, match="preview_ineligible"):
        claim(ledger)


def test_unit_source_and_future_expired_quotes_refused(voice_db, monkeypatch):
    ledger, _ = voice_db
    with pytest.raises(ValueError, match="billing_source"):
        reserve(ledger, quote=quote(unit_contract=VoiceBillingUnit.CONNECTION_MS))
    q = quote()
    reserve(ledger, quote=q)
    monkeypatch.setattr(vb, "_now", lambda: q.expires_at)
    with pytest.raises(PermissionError, match="quote_inactive"):
        claim(ledger)
    with pytest.raises(PermissionError, match="quote_inactive"):
        reserve(ledger, "expired", quote=q)


def test_quote_expiry_after_window_lock_wait_refuses_claim(voice_db, monkeypatch):
    ledger, _ = voice_db
    q = quote()
    reserve(ledger, quote=q)
    original = ledger._windows

    def after_lock(session, ids):
        result = original(session, ids)
        monkeypatch.setattr(vb, "_now", lambda: q.expires_at)
        return result

    monkeypatch.setattr(ledger, "_windows", after_lock)
    with pytest.raises(PermissionError, match="quote_inactive"):
        claim(ledger)


def test_session_binding_uses_connection_units(voice_db):
    ledger, _ = voice_db
    b = binding(
        session_id="synthetic-session",
        message_id=None,
        content_hash=None,
        endpoint="wss://agent.deepgram.com/v1/agent/converse",
        model="synthetic-byo-agent",
    )
    reserve(
        ledger, binding=b, quote=quote(unit_contract=VoiceBillingUnit.CONNECTION_MS)
    )
    assert claim(ledger, binding=b)
    assert not claim(ledger, binding=b)
    with pytest.raises(ValueError, match="endpoint"):
        replace(b, endpoint="wss://api.eu.deepgram.com/v1/agent/converse")


@pytest.mark.parametrize(
    "mutation", ["disabled", "expired", "payer", "provider", "missing", "substituted"]
)
def test_exact_original_windows_required_at_claim(voice_db, mutation):
    ledger, sessions = voice_db
    reserve(ledger)
    with sessions.begin() as session:
        window = session.get(InferenceBudgetWindow, "voice-funding")
        if mutation == "disabled":
            window.enabled = False
        elif mutation == "expired":
            window.ends_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        elif mutation == "payer":
            window.payer_scope = "wrong"
        elif mutation == "provider":
            window.provider = "wrong"
        else:
            session.execute(
                delete(VoiceBudgetAllocation).where(
                    VoiceBudgetAllocation.window_id == "voice-funding"
                )
            )
            if mutation == "substituted":
                session.add(
                    VoiceBudgetAllocation(
                        attempt_id="voice-attempt", window_id="funding"
                    )
                )
    with pytest.raises((PermissionError, ValueError)):
        claim(ledger)
    assert totals(sessions)["month"] == (3_000_000, 0)


def test_chat_and_voice_compete_atomically(voice_db):
    voice, sessions = voice_db
    chat = BudgetLedger(sessions)
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "month").limit_units = 10_000_000

    def model(attempt):
        return chat.reserve(
            attempt_id=attempt,
            account_id="one",
            request_id="one",
            payer_scope="operator",
            provider="openai",
            model="synthetic-model",
            budget_ids=["month", "funding"],
            input_ceiling=1000,
            output_ceiling=1000,
            quote=TOKEN_QUOTE,
        )

    model("chat-first")
    reserve(voice, "voice-first")

    def contender(n):
        try:
            (model if n % 2 else lambda name: reserve(voice, name))(f"race-{n}")
            return True
        except PermissionError as exc:
            assert "exhausted" in str(exc)
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(contender, range(30))) == 1
    values = totals(sessions)
    assert values["month"] == (9_000_000, 0)
    assert values["funding"][0] + values["voice-funding"][0] == 9_000_000


def test_unknown_chunk_and_cancellation_liability_is_retained(voice_db):
    ledger, sessions = voice_db
    reserve(ledger, "chunk-0")
    reserve(ledger, "chunk-1", dispatch_digest="e" * 64)
    assert claim(ledger, "chunk-0")
    for values in (
        {"observed_quantity": None},
        {"provider_request_id": None},
        {"reported_model": None},
        {"reported_model": "wrong-model"},
    ):
        assert not settle(ledger, "chunk-0", **values)
    assert not ledger.release_unclaimed(attempt_id="chunk-0", account_id="one")
    assert ledger.release_unclaimed(attempt_id="chunk-1", account_id="one")
    assert not claim(ledger, "chunk-1", dispatch_digest="e" * 64)
    assert not claim(VoiceBudgetLedger(sessions), "chunk-0")
    assert totals(sessions)["month"] == (3_000_000, 0)


@pytest.mark.parametrize("action", ["claim", "release", "settle"])
def test_inconsistent_held_counters_refuse_mutation(voice_db, action):
    ledger, sessions = voice_db
    reserve(ledger)
    if action == "settle":
        claim(ledger)
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "voice-funding").held_units = 1
    with pytest.raises(ValueError, match="hold_inconsistent"):
        if action == "claim":
            claim(ledger)
        elif action == "release":
            ledger.release_unclaimed(attempt_id="voice-attempt", account_id="one")
        else:
            settle(ledger)
    assert totals(sessions)["month"] == (3_000_000, 0)


@pytest.mark.parametrize("value", [True, -1, float("nan"), "100"])
def test_malformed_settlement_keeps_hold(voice_db, value):
    ledger, sessions = voice_db
    reserve(ledger)
    claim(ledger)
    with pytest.raises(ValueError):
        settle(ledger, observed_quantity=value)
    assert totals(sessions)["month"] == (3_000_000, 0)


def test_original_quote_settlement_and_conflicting_receipts(voice_db):
    ledger, sessions = voice_db
    reserve(ledger)
    claim(ledger)
    assert settle(ledger)
    assert settle(ledger)
    with pytest.raises(ValueError, match="settlement_conflict"):
        settle(ledger, observed_quantity=101)
    assert totals(sessions)["month"] == (0, 300_000)
    with sessions() as session:
        row = session.get(VoiceBudgetReservation, "voice-attempt")
        data = json.dumps(
            dict(
                binding=row.binding_snapshot,
                quote=row.price_snapshot,
                receipt=row.settlement_usage,
            )
        )
        assert TEXT.strip() not in data
        assert set(row.settlement_usage) == {
            "quantity",
            "provider_request_id",
            "reported_model",
            "dispatch_digest",
        }


def test_overrun_blocks_already_reserved_and_new_claims(voice_db):
    ledger, sessions = voice_db
    reserve(ledger, "overrun")
    reserve(ledger, "queued")
    claim(ledger, "overrun")
    assert settle(ledger, "overrun", observed_quantity=100_000)
    assert totals(sessions)["voice-funding"] == (3_000_000, 300_000_000)
    with pytest.raises(PermissionError, match="exhausted"):
        claim(ledger, "queued")
    with pytest.raises(PermissionError, match="exhausted"):
        reserve(ledger, "blocked")
    assert ledger.release_unclaimed(attempt_id="queued", account_id="one")


def test_settlement_after_window_retirement_and_account_deletion(voice_db):
    ledger, sessions = voice_db
    reserve(ledger)
    reserve(ledger, "never-claimed")
    claim(ledger)
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "voice-funding").enabled = False
        session.execute(
            delete(ChatCompletionAttempt).where(
                ChatCompletionAttempt.accepted_account_id == "one"
            )
        )
        session.execute(delete(ChatMessage).where(ChatMessage.user_id == "one"))
        session.execute(delete(ChatThread).where(ChatThread.user_id == "one"))
        session.execute(delete(Project).where(Project.user_id == "one"))
        session.execute(delete(User).where(User.id == "one"))
    assert settle(ledger)
    assert ledger.release_unclaimed(attempt_id="never-claimed", account_id="one")
    assert totals(sessions)["month"] == (0, 300_000)


def test_ambiguous_committed_claim_cannot_be_retried(voice_db):
    ledger, sessions = voice_db
    reserve(ledger)

    class CommitThenError:
        @contextmanager
        def begin(self):
            with sessions.begin() as session:
                yield session
            raise RuntimeError("synthetic lost commit acknowledgement")

    with pytest.raises(RuntimeError, match="acknowledgement"):
        claim(VoiceBudgetLedger(CommitThenError()))
    assert not claim(VoiceBudgetLedger(sessions))
    assert not ledger.release_unclaimed(attempt_id="voice-attempt", account_id="one")


def test_migration_roundtrip_and_no_seeded_allowances(voice_db):
    _, sessions = voice_db
    path = (
        Path(__file__).resolve().parents[2]
        / "guardian/db/migrations/versions/1b6c8d9e2f40_inactive_voice_budget.py"
    )
    spec = importlib.util.spec_from_file_location("voice_budget_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "e723ba9046cd"
    engine = sessions.kw["bind"]
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            migration.upgrade()
        for table in (
            "voice_budget_reservations",
            "voice_budget_dispatches",
            "voice_budget_allocations",
        ):
            assert table in inspect(conn).get_table_names()
    with sessions() as session:
        assert list(session.scalars(select(VoiceBudgetReservation))) == []
        assert len(list(session.scalars(select(InferenceBudgetWindow)))) == 3


def test_no_cascading_content_or_account_foreign_keys():
    assert not VoiceBudgetReservation.__table__.foreign_keys
    assert "api_key" not in asdict(binding())
