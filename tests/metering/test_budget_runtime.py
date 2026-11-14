"""No real network: actual router normalization + disposable budget persistence."""

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from guardian.core import ai_router
from guardian.core.config import Settings
from guardian.db.models import InferenceBudgetWindow, InferenceBudgetReservation
from guardian.metering import runtime
from tests.metering.test_inference_budget import budget_db, QUOTE  # noqa: F401


@pytest.fixture
def configured(budget_db, monkeypatch):  # noqa: F811 - imported pytest fixture
    ledger, sessions = budget_db
    with sessions.begin() as session:
        for window in session.scalars(select(InferenceBudgetWindow)):
            window.limit_units = 10_000_000_000
    config = dict(
        mode="enforce",
        payer_scope="operator",
        monthly_window="month",
        funding_window="funding",
        max_output_tokens=1000,
        quote=QUOTE,
    )
    monkeypatch.setenv(runtime.ENV, json.dumps(config))
    monkeypatch.setattr(ai_router, "assert_egress_allowed", lambda *a, **kw: None)
    monkeypatch.setattr(
        ai_router, "provider_routing_requires_discovered_inventory", lambda _: False
    )
    db = SimpleNamespace(_sa_session=sessions.begin)
    task = SimpleNamespace(user_id="one", request_id="one", thread_id=1, task_id="one")
    return db, task, sessions


def response(*, usage=True):
    raw = dict(
        model=runtime.MODEL,
        id="synthetic-response",
        choices=[{"message": {"content": "hello"}}],
    )
    if usage:
        raw["usage"] = {"prompt_tokens": 100, "completion_tokens": 50}
    return SimpleNamespace(status_code=200, json=lambda: raw)


def settings():
    return Settings(
        OPENAI_API_KEY="synthetic-not-a-secret", DEFAULT_OPENAI_MODEL=runtime.MODEL
    )


def test_actual_normalized_model_and_raw_usage(configured, monkeypatch):
    db, task, sessions = configured
    sent = []

    def post(url, **kwargs):
        sent.append((url, kwargs))
        return response()

    monkeypatch.setattr(ai_router.requests, "post", post)
    with runtime.accepted_budget_context(task, "openai", db):
        result = ai_router.chat_with_ai(
            [{"role": "user", "content": "hi"}],
            provider="openai",
            model="gpt-4.1",
            settings=settings(),
        )
    assert result == "hello"
    assert sent[0][1]["json"]["model"] == runtime.MODEL
    assert sent[0][1]["json"]["max_tokens"] == 1000
    assert sent[0][1]["allow_redirects"] is False
    with sessions() as session:
        row = session.scalar(select(InferenceBudgetReservation))
        assert row.model == runtime.MODEL
        assert (
            row.reserved_units == 130_000_000
        )  # Full context, not guessed prompt tokens.
        assert row.settled_units == 200_000
        assert row.settlement_usage["input_tokens"] == 100
    # Re-delivery cannot run a second provider request, even with fresh context.
    with (
        runtime.accepted_budget_context(task, "openai", db),
        pytest.raises(HTTPException),
    ):
        ai_router.chat_with_ai(
            [{"role": "user", "content": "hi"}],
            provider="openai",
            model="gpt-4.1",
            settings=settings(),
        )
    assert len(sent) == 1


def test_low_budget_sends_no_request(configured, monkeypatch):
    db, task, sessions = configured
    with sessions.begin() as session:
        session.get(InferenceBudgetWindow, "funding").limit_units = 1
    sent = []
    monkeypatch.setattr(ai_router.requests, "post", lambda *a, **kw: sent.append(kw))
    with (
        runtime.accepted_budget_context(task, "openai", db),
        pytest.raises(HTTPException),
    ):
        ai_router.call_openai(
            [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
        )
    assert not sent


def test_no_account_context_or_unsupported_model_sends_nothing(configured, monkeypatch):
    db, task, sessions = configured
    sent = []
    monkeypatch.setattr(ai_router.requests, "post", lambda *a, **kw: sent.append(kw))
    with pytest.raises(HTTPException):
        ai_router.call_openai(
            [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
        )
    with (
        runtime.accepted_budget_context(task, "openai", db),
        pytest.raises(HTTPException),
    ):
        ai_router.call_openai(
            [{"role": "user", "content": "hi"}], "gpt-4o", settings=settings()
        )
    assert not sent


def test_timeout_and_missing_usage_never_free_hold(configured, monkeypatch):
    db, task, sessions = configured
    monkeypatch.setattr(
        ai_router.requests, "post", lambda *a, **kw: response(usage=False)
    )
    with runtime.accepted_budget_context(task, "openai", db):
        ai_router.call_openai(
            [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
        )
    with sessions() as session:
        row = session.scalar(select(InferenceBudgetReservation))
        assert row.state == "dispatched" and row.settled_units is None
        assert session.get(InferenceBudgetWindow, "funding").held_units == 130_000_000


def test_payload_extras_and_media_are_rejected(configured):
    db, task, _ = configured
    base = dict(model=runtime.MODEL, messages=[{"role": "user", "content": "hi"}])
    for payload in (
        base | {"n": 2},
        base | {"stream": True},
        base | {"tools": []},
        base | {"messages": [{"role": "user", "content": [{"type": "image_url"}]}]},
    ):
        with (
            runtime.accepted_budget_context(task, "openai", db),
            pytest.raises(HTTPException),
        ):
            runtime.guarded_http(
                runtime.ENDPOINT, payload, lambda *a: pytest.fail("sent")
            )


def test_disabled_is_unchanged_and_local_survives_bad_config(monkeypatch):
    monkeypatch.delenv(runtime.ENV, raising=False)
    assert runtime.guarded_http(
        "https://api.openai.com/v1/chat/completions", {}, lambda p, b: (p, b)
    ) == ({}, False)
    monkeypatch.setenv(runtime.ENV, "not-json")
    with runtime.accepted_budget_context(None, "local", None):
        runtime.require_context("local")
        assert (
            runtime.guarded_http("http://127.0.0.1:8000/chat", {}, lambda p, b: "local")
            == "local"
        )
    with pytest.raises(HTTPException):
        runtime.require_context("openai")


def test_invalid_temperature_rejected_before_claim(configured):
    db, task, sessions = configured
    for temperature in (float("nan"), float("inf"), -1, 3, "0.5", True):
        payload = dict(
            model=runtime.MODEL,
            messages=[{"role": "user", "content": "hi"}],
            temperature=temperature,
        )
        with (
            runtime.accepted_budget_context(task, "openai", db),
            pytest.raises(HTTPException),
        ):
            runtime.guarded_http(
                runtime.ENDPOINT, payload, lambda *a: pytest.fail("sent")
            )
    with sessions() as session:
        assert session.scalar(select(InferenceBudgetReservation)) is None


def test_operator_readback_keeps_liabilities_separate(configured, monkeypatch):
    from guardian.metering.budget import budget_status

    db, task, sessions = configured
    monkeypatch.setattr(
        ai_router.requests, "post", lambda *a, **kw: response(usage=False)
    )
    with runtime.accepted_budget_context(task, "openai", db):
        ai_router.call_openai(
            [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
        )
    with sessions() as session:
        result = budget_status(
            session,
            monthly_window="month",
            funding_window="funding",
            account_allowances={"one": 1_000_000},
        )
    account = result["accounts"][0]
    assert account["estimated_settled_units"] == 0
    assert account["unsettled_hold_units"] == 130_000_000
    assert account["unresolved_dispatches"] == 1
    assert account["soft_thresholds"]["deny_inference"] is False


@pytest.mark.parametrize("failure", ["timeout", "transport", "http", "malformed"])
def test_real_failure_paths_hold_and_refuse_retry(configured, monkeypatch, failure):
    import requests

    db, task, sessions = configured
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        if failure == "timeout":
            raise requests.ReadTimeout("synthetic timeout")
        if failure == "transport":
            raise requests.ConnectionError("synthetic failure")
        if failure == "http":
            return SimpleNamespace(
                status_code=503,
                text="unavailable",
                json=lambda: {"error": {"message": "unavailable"}},
            )

        def malformed():
            raise ValueError("synthetic malformed JSON")

        return SimpleNamespace(status_code=200, json=malformed)

    monkeypatch.setattr(ai_router.requests, "post", post)
    for _ in range(2):
        with (
            runtime.accepted_budget_context(task, "openai", db),
            pytest.raises(HTTPException),
        ):
            ai_router.call_openai(
                [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
            )
    assert len(calls) == 1
    with sessions() as session:
        assert session.get(InferenceBudgetWindow, "funding").held_units == 130_000_000


def test_actual_completion_context_with_pgdb_session_wrapper(configured, monkeypatch):
    from guardian.core import chat_completion_service as service
    from guardian.core.pgdb import PgDB

    _, _, sessions = configured
    db = PgDB.__new__(PgDB)
    db._SessionLocal = sessions
    task = SimpleNamespace(
        user_id="one",
        request_id="one",
        task_id="one",
        thread_id=1,
        origin="api:chat.complete",
    )
    monkeypatch.setattr(service.dependencies, "chatlog_db", db)
    monkeypatch.setattr(service, "get_settings", settings)
    monkeypatch.setattr(
        service, "_provider_request_capture_observer", lambda *a, **kw: None
    )
    monkeypatch.setattr(ai_router.requests, "post", lambda *a, **kw: response())
    result = service._execute_completion_attempt(
        task=task,
        messages_for_llm=[{"role": "user", "content": "hi"}],
        provider="openai",
        model="gpt-4.1",
        bundle=None,
    )
    assert result.output == "hello"
    with sessions() as session:
        row = session.scalar(select(InferenceBudgetReservation))
        assert row.state == "settled" and row.model == runtime.MODEL


def test_accepted_deadline_transport_guard(configured, monkeypatch):
    db, task, sessions = configured
    sent = []

    class Transport:
        def __init__(self, deadline):
            pass

        def post(self, url, **kwargs):
            sent.append(kwargs["json"])
            return SimpleNamespace(
                status_code=200,
                headers={},
                content=json.dumps(response().json()).encode(),
                response=SimpleNamespace(encoding="utf-8"),
            )

        def close(self):
            pass

    monkeypatch.setattr(ai_router, "AcceptedDeadlineTransport", Transport)
    with runtime.accepted_budget_context(task, "openai", db):
        value = ai_router.call_openai(
            [{"role": "user", "content": "hi"}],
            runtime.MODEL,
            settings=settings(),
            accepted_deadline=object(),
        )
    assert value == "hello" and sent[0]["max_tokens"] == 1000
    with sessions() as session:
        assert session.scalar(select(InferenceBudgetReservation)).state == "settled"


def test_tool_bearing_task_refused_before_reservation(configured):
    db, task, sessions = configured
    task.tools = [{"name": "some-tool"}]
    with (
        pytest.raises(HTTPException),
        runtime.accepted_budget_context(task, "openai", db),
    ):
        pytest.fail("tool-bearing context admitted")
    with sessions() as session:
        assert session.scalar(select(InferenceBudgetReservation)) is None


@pytest.mark.parametrize(
    "field,value", [("thread_id", 2), ("task_id", "not-the-accepted-task")]
)
def test_foreign_task_binding_sends_nothing(configured, monkeypatch, field, value):
    db, task, sessions = configured
    setattr(task, field, value)
    sent = []
    monkeypatch.setattr(ai_router.requests, "post", lambda *a, **kw: sent.append(kw))
    with (
        runtime.accepted_budget_context(task, "openai", db),
        pytest.raises(HTTPException),
    ):
        ai_router.call_openai(
            [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
        )
    assert not sent


def test_missing_acceptance_receipt_does_not_override_custody(configured, monkeypatch):
    # ADR-091: accepted_at follows queue publish and can be missing after a
    # receipt failure. Immutable custody remains the authority, not timestamp.
    from guardian.db.models import ChatCompletionAttempt

    db, task, sessions = configured
    with sessions.begin() as session:
        session.get(ChatCompletionAttempt, "one").accepted_at = None
    sent = []

    def post(*args, **kwargs):
        sent.append(kwargs)
        return response()

    monkeypatch.setattr(ai_router.requests, "post", post)
    with runtime.accepted_budget_context(task, "openai", db):
        assert (
            ai_router.call_openai(
                [{"role": "user", "content": "hi"}], runtime.MODEL, settings=settings()
            )
            == "hello"
        )
    assert len(sent) == 1
