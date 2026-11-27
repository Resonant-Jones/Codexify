"""Exercise an ordinary Guardian chat send through PostgreSQL and the task queue."""

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import fakeredis
import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core import ai_router
from guardian.core import chat_completion_service as service
from guardian.core import dependencies
from guardian.core.pgdb import PgDB
from guardian.queue import redis_queue
from guardian.queue.turn_lock import get_turn_lock, release_turn_lock
from guardian.routes import chat
from guardian.tasks.types import ChatCompletionTask
from tests.core.test_chat_completion_service_thread_config import (
    _seed_completion_service,
)
from tests.routes.test_chat_thinking_effort import ROUTE, capture
from tests.services.test_memory_vault_read_projection import (
    _create_disposable_database,
    _drop_database,
    _migrate_to_head,
)
from tests.utils import get_test_auth_headers

ACCOUNT = "authored-turn-account"
OTHER = "authored-turn-other"
STALE = "The authored message changed. Review the current turn and retry."


@pytest.fixture(scope="module")
def authored_database():
    admin = os.getenv("TEST_DATABASE_URL")
    if not admin:
        pytest.skip("TEST_DATABASE_URL is required for the disposable PostgreSQL proof")
    name = "authored_turn_" + uuid.uuid4().hex
    url = _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url.replace("postgresql://", "postgresql+psycopg://", 1))
        with psycopg.connect(url) as conn:
            for account in (ACCOUNT, OTHER):
                conn.execute(
                    "INSERT INTO users(id,username,password_hash) VALUES (%s,%s,'fixture')",
                    (account, account),
                )
        yield url
    finally:
        _drop_database(admin, name)


@pytest.fixture
def ordinary_chat(authored_database, capture, monkeypatch):
    settings, _, _ = capture
    db = PgDB(authored_database)
    thread = db.create_chat_thread(ACCOUNT, "Receipt test")
    redis = fakeredis.FakeRedis()
    monkeypatch.setattr(redis_queue, "_CLIENT", redis)
    monkeypatch.setattr(redis_queue, "_QUEUE_CLIENT", redis)
    monkeypatch.setattr(chat, "chatlog_db", db)
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    monkeypatch.setattr(chat, "llm_settings", settings)
    app = FastAPI()
    app.include_router(chat.api_chat_router)
    app.dependency_overrides[chat.get_request_user_scope] = (
        lambda: dependencies.RequestUserScope(
            user_id=ACCOUNT, account_id=ACCOUNT, multi_user_enabled=True
        )
    )
    with TestClient(app, headers=get_test_auth_headers()) as client:
        yield client, db, thread["id"]
    db._sa_engine.dispose()


def post_message(client, thread_id, content, **fields):
    response = client.post(
        f"/api/chat/{thread_id}/messages",
        json={"role": "user", "content": content, **fields},
    )
    assert response.status_code == 200, response.text
    return response.json()["message"]["id"]


def complete(
    client,
    thread_id,
    message_id=None,
    *,
    effort="default",
    request_id=None,
    with_receipt=True,
    **fields,
):
    payload = {
        "provider": ROUTE[0],
        "model": ROUTE[1],
        "reasoning_mode": "think",
        "depth_mode": "light",
        **fields,
    }
    if with_receipt:
        payload["expected_message_id"] = message_id
    if effort is not None:
        payload["thinking_effort"] = effort
    headers = {"X-Request-ID": request_id} if request_id else None
    return client.post(f"/api/chat/{thread_id}/complete", json=payload, headers=headers)


def queued_task():
    payload = redis_queue.dequeue(service.CHAT_COMPLETION_QUEUE_NAME, block=False)
    assert payload is not None
    return ChatCompletionTask.from_dict(payload)


@pytest.mark.parametrize(
    ("effort", "provider_effort", "with_receipt"),
    [
        ("default", None, True),
        ("max", "max", True),
        (None, "high", True),
        (None, "high", False),
    ],
    ids=["provider-default", "max", "omitted-effort", "no-receipt"],
)
def test_long_chat_preserves_authored_target_and_default(
    ordinary_chat, capture, monkeypatch, effort, provider_effort, with_receipt
):
    client, db, thread_id = ordinary_chat
    settings, _, transports = capture
    older = [db.create_message(thread_id, "user", f"old {i}") for i in range(55)]
    prior = db.create_message(thread_id, "user", "bounded prior question")
    answer = db.create_message(thread_id, "assistant", "bounded prior reply")
    target = post_message(client, thread_id, "Answer this exact message")
    with db._connect() as conn:
        conn.execute(
            "UPDATE chat_messages SET extra_meta = extra_meta || %s::jsonb WHERE id = %s",
            ('{"embedding_status":"ready"}', target),
        )
    db.create_message(thread_id, "assistant", "a reply after the target")

    response = complete(
        client,
        thread_id,
        target,
        effort=effort,
        with_receipt=with_receipt,
        **({"max_context": 3} if with_receipt else {}),
    )
    assert response.status_code == 200, response.text
    task = queued_task()
    assert task.task_id == response.json()["task_id"]
    assert task.thinking_effort == effort
    assert (task.provider, task.model, task.reasoning_mode) == (*ROUTE[:2], "think")
    with db._connect() as conn:
        receipt = conn.execute(
            "SELECT accepted_account_id, accepted_at FROM chat_completion_attempts "
            "WHERE backend_task_id = %s",
            (task.task_id,),
        ).fetchone()
    assert receipt is not None
    assert receipt["accepted_account_id"] == ACCOUNT
    assert receipt["accepted_at"] is not None

    # Move the newest window entirely past the accepted row, including a later
    # insertion with an earlier display timestamp.
    assert release_turn_lock(thread_id, task.task_id)
    for i in range(4):
        post_message(client, thread_id, f"later turn {i}")
    db.create_message(
        thread_id, "user", "later backdated turn", created_at="2020-01-01T00:00:00Z"
    )

    _seed_completion_service(monkeypatch, thread_row=db.get_chat_thread(thread_id))
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "resolve_thread_system_profile", lambda *a, **kw: None)
    messages, provider, model, bundle, trace = asyncio.run(
        service.build_messages_for_llm(task, user_id=ACCOUNT)
    )
    assembly = bundle["_completion_assembly"]
    ai_router.chat_with_ai(
        messages,
        provider=provider,
        model=model,
        reasoning_mode=task.reasoning_mode,
        thinking_effort=task.thinking_effort,
        settings=settings,
        accepted_deadline=service.accepted_chat_deadline_for_task(task),
    )
    (request,) = transports
    sent = [m["content"] for m in request["messages"] if m["role"] == "user"]
    assert sent[-2:] == [
        "bounded prior question",
        "Answer this exact message",
    ], f"accepted {task.latest_turn_message_id} for authored {target}, provider saw {sent[-2:]}"
    assert task.latest_turn_message_id == target
    assert assembly["latest_turn"]["id"] == target
    expected_history = (
        [prior, answer] if with_receipt else [*older[-47:], prior, answer]
    )
    assert [message["id"] for message in assembly["history"]] == expected_history
    assert trace["retrieval_query"] == "Answer this exact message"
    assert request["thinking"] == {"type": "enabled"}
    if provider_effort is None:
        assert "reasoning_effort" not in request
    else:
        assert request["reasoning_effort"] == provider_effort


def test_rejects_invalid_foreign_ineligible_and_stale_receipts(ordinary_chat):
    client, db, thread_id = ordinary_chat
    foreign_thread = db.create_chat_thread(OTHER, "Foreign thread")["id"]
    sibling_thread = db.create_chat_thread(ACCOUNT, "Sibling thread")["id"]
    wrong_thread = post_message(client, sibling_thread, "belongs to a sibling")
    foreign = db.create_native_user_message(foreign_thread, "user", "foreign")
    wrong_account = db.create_native_user_message(
        thread_id, "user", "wrong account in this thread", user_id=OTHER
    )
    assistant = db.create_message(thread_id, "assistant", "not a user")
    older = post_message(client, thread_id, "older authored turn")
    newest = post_message(client, thread_id, "newest authored turn")
    imported = db.create_message(
        thread_id, "user", "imported row", extra_meta={"origin": "chatgpt_import"}
    )
    unproven = db.create_message(thread_id, "user", "no ordinary send receipt")
    ineligible = db.create_native_user_message(thread_id, "user", "not chat evidence")
    with db._connect() as conn:
        conn.execute(
            "UPDATE chat_messages SET kind = 'fact_evidence' WHERE id = %s",
            (ineligible,),
        )

    for receipt_id in (
        None,
        wrong_thread,
        foreign,
        wrong_account,
        assistant,
        imported,
        unproven,
        older,
        ineligible,
        newest + 100_000,
    ):
        response = complete(client, thread_id, receipt_id)
        assert response.status_code == 409, (receipt_id, response.text)
        assert response.json()["detail"] == STALE
    for receipt_id in (0, "1", True):
        assert complete(client, thread_id, receipt_id).status_code == 422
    assert complete(client, foreign_thread, foreign).status_code == 403
    assert redis_queue.dequeue(service.CHAT_COMPLETION_QUEUE_NAME, block=False) is None
    assert get_turn_lock(thread_id) is None

    response = complete(client, thread_id, newest)
    assert response.status_code == 200, response.text
    assert queued_task().latest_turn_message_id == newest


@pytest.mark.parametrize("with_receipt", [True, False], ids=["receipt", "no-receipt"])
def test_rechecks_selected_turn_inside_attempt_transaction(
    ordinary_chat, monkeypatch, with_receipt
):
    client, db, thread_id = ordinary_chat
    target = post_message(client, thread_id, "about to become stale")
    preliminary_read_done = Event()
    later_saved = Event()
    build_doc_context = chat._build_doc_context_override

    async def wait_for_later_send(**kwargs):
        preliminary_read_done.set()
        assert await asyncio.to_thread(later_saved.wait, 5)
        return await build_doc_context(**kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(chat, "_build_doc_context_override", wait_for_later_send)
        with ThreadPoolExecutor() as executor:
            pending = executor.submit(
                complete,
                client,
                thread_id,
                target,
                with_receipt=with_receipt,
                effort="default" if with_receipt else None,
            )
            try:
                assert preliminary_read_done.wait(timeout=5)
                newer = post_message(client, thread_id, "newer before acceptance")
            finally:
                later_saved.set()
            response = pending.result(timeout=5)
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == STALE
    assert redis_queue.dequeue(service.CHAT_COMPLETION_QUEUE_NAME, block=False) is None
    assert get_turn_lock(thread_id) is None
    with db._connect() as conn:
        assert (
            conn.execute(
                "SELECT count(*) AS total FROM chat_completion_attempts WHERE thread_id = %s",
                (thread_id,),
            ).fetchone()["total"]
            == 0
        )

    response = complete(client, thread_id, newer)
    assert response.status_code == 200, response.text
    assert queued_task().latest_turn_message_id == newer


def test_concurrent_submissions_and_replay_keep_request_identity(
    ordinary_chat, monkeypatch
):
    client, db, thread_id = ordinary_chat
    target = post_message(client, thread_id, "same authored receipt")
    request_ids = [f"req_{uuid.uuid4().hex}" for _ in range(3)]
    ready = Barrier(2)
    build_doc_context = chat._build_doc_context_override

    async def meet_other_request(**kwargs):
        await asyncio.to_thread(ready.wait, 5)
        return await build_doc_context(**kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(chat, "_build_doc_context_override", meet_other_request)
        with ThreadPoolExecutor(max_workers=2) as executor:
            submissions = [
                executor.submit(complete, client, thread_id, target, request_id=req)
                for req in request_ids[:2]
            ]
            responses = [future.result(timeout=10) for future in submissions]
    assert sorted(response.status_code for response in responses) == [200, 429]
    accepted = queued_task()
    assert accepted.latest_turn_message_id == target
    assert redis_queue.dequeue(service.CHAT_COMPLETION_QUEUE_NAME, block=False) is None
    assert release_turn_lock(thread_id, accepted.task_id)

    duplicate = complete(client, thread_id, target, request_id=accepted.request_id)
    assert duplicate.status_code == 503, duplicate.text
    assert duplicate.json()["detail"]["reason"] == "attempt_persistence_unavailable"
    assert redis_queue.dequeue(service.CHAT_COMPLETION_QUEUE_NAME, block=False) is None
    assert get_turn_lock(thread_id) is None

    replay = complete(client, thread_id, target, request_id=request_ids[2])
    assert replay.status_code == 200, replay.text
    retried = queued_task()
    assert retried.latest_turn_message_id == target
    assert retried.request_id == request_ids[2]
    assert retried.task_id != accepted.task_id
    assert release_turn_lock(thread_id, retried.task_id)

    newest = post_message(client, thread_id, "next authored turn")
    stale_replay = complete(client, thread_id, target, request_id=request_ids[2])
    assert stale_replay.status_code == 409, stale_replay.text
    assert redis_queue.dequeue(service.CHAT_COMPLETION_QUEUE_NAME, block=False) is None
    assert db.resolve_authored_chat_turn(thread_id, user_id=ACCOUNT, message_id=newest)


def test_no_receipt_accepts_unmarked_structured_ordinary_turn(ordinary_chat):
    client, db, thread_id = ordinary_chat
    post_message(client, thread_id, "Older native message")
    original = [
        {"type": "text", "text": "Current legacy attachment"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,aW1hZ2U="}},
    ]
    legacy = db.create_message(
        thread_id,
        "user",
        "Current legacy attachment [Image attached]",
        extra_meta={"original_content": original},
    )
    db.create_native_user_message(thread_id, "user", "different account", user_id=OTHER)
    db.create_message(
        thread_id, "user", "imported", extra_meta={"origin": "chatgpt_import"}
    )

    response = complete(client, thread_id, effort=None, with_receipt=False)
    assert response.status_code == 200, response.text
    task = queued_task()
    assert task.latest_turn_message_id == legacy
    assert task.latest_turn_messages == original


def test_pinned_history_preserves_baseline_image_inputs(
    ordinary_chat, capture, monkeypatch
):
    client, db, thread_id = ordinary_chat
    settings, _, _ = capture
    source = "data:image/png;base64,aW1hZ2U="
    post_message(
        client,
        thread_id,
        f"<!-- cfy-media:image:prior -->\n<!-- cfy-media-src:{source} -->\nMarked image",
    )
    post_message(
        client,
        thread_id,
        [
            {"type": "text", "text": "Structured image"},
            {"type": "image_url", "image_url": {"url": source}},
        ],
    )
    target = post_message(client, thread_id, "Follow-up question")
    response = complete(client, thread_id, effort=None, with_receipt=False)
    assert response.status_code == 200, response.text
    task = queued_task()
    assert task.latest_turn_message_id == target

    _seed_completion_service(monkeypatch, thread_row=db.get_chat_thread(thread_id))
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "resolve_thread_system_profile", lambda *a, **kw: None)
    monkeypatch.setattr(
        service, "resolve_model_vision_capability_state", lambda *a, **kw: True
    )
    unpinned = ChatCompletionTask.from_dict(task.to_dict())
    unpinned.latest_turn_message_id = None

    def user_inputs(completion):
        messages, *_ = asyncio.run(
            service.build_messages_for_llm(completion, user_id=ACCOUNT)
        )
        return [message["content"] for message in messages if message["role"] == "user"]

    assert (
        user_inputs(task)
        == user_inputs(unpinned)
        == [
            [
                {"type": "text", "text": "Marked image"},
                {"type": "image_url", "image_url": {"url": source}},
            ],
            "Structured image [Image attached]",
            "Follow-up question",
        ]
    )
