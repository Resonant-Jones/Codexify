"""P1 regression: voice turns complete through the shared completion service.

The voice worker builds a `ChatCompletionTask` directly and calls
`run_chat_completion_task`, so it never passes through `enqueue_chat_completion`
and therefore never owns an accepted-chat attempt or its durable
`ChatCompletionAttempt` row. Checkpoint reconciliation must therefore not
reject a plain voice answer for lacking a checkpoint it was never able to
create.

These tests drive the real voice worker -> real completion service path with
only the STT, provider, and TTS boundaries mocked, so they exercise the
production gating rather than a helper in isolation.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa

from guardian.core import chat_completion_service, dependencies
from guardian.core.chatlog_postgres import PostgresChatLogDB
from guardian.core.db import GuardianDB
from guardian.db.models import ChatCompletionAttempt, ChatThread, User
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from guardian.tasks.types import ChatCompletionTask, VoiceTurnTask
from guardian.workers import voice_worker


@pytest.fixture
def disposable_database(monkeypatch: pytest.MonkeyPatch):
    psycopg = pytest.importorskip("psycopg")
    import os
    import uuid
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.engine import make_url

    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")
    database_name = f"codexify_voice_turn_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=database_name)
    admin_dsn = admin_url.render_as_string(hide_password=False)
    test_dsn = test_url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute(f"CREATE DATABASE {database_name}")
    config = Config(
        str(Path(__file__).resolve().parents[2] / "backend" / "alembic.ini")
    )
    config.set_main_option("sqlalchemy.url", test_dsn.replace("%", "%%"))
    try:
        command.upgrade(config, "head")
        monkeypatch.setenv("DATABASE_URL", test_dsn)
        yield test_dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {database_name}")


def _seed_thread(db: GuardianDB, *, account_id: str) -> int:
    with db.get_session() as session:
        session.add(
            User(
                id=account_id,
                username=account_id,
                password_hash="inert-test-hash",
                role="guest",
            )
        )
        thread = ChatThread(user_id=account_id, title="voice")
        session.add(thread)
        session.flush()
        thread_id = int(thread.id)
        session.commit()
    return thread_id


def _seed_accepted_attempt(
    db: GuardianDB,
    *,
    thread_id: int,
    account_id: str,
    task_id: str,
    request_id: str,
    turn_id: str,
) -> None:
    with db.get_session() as session:
        session.add(
            ChatCompletionAttempt(
                request_id=request_id,
                backend_task_id=task_id,
                thread_id=thread_id,
                turn_id=turn_id,
                accepted_at=sa.func.now(),
            )
        )
        session.commit()


def _seed_completion_service(
    monkeypatch: pytest.MonkeyPatch,
    chat_db: Any,
    *,
    answer: Any,
) -> list[str]:
    """Mock only the provider/retrieval boundaries; keep the real service."""

    monkeypatch.setattr(
        chat_completion_service, "get_settings", lambda: SimpleNamespace()
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_sanitized_payload_summary",
        lambda messages, _bundle, provider, model, **_kw: {
            "message_count": len(messages),
            "resolved_provider": provider,
            "resolved_model": model,
        },
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **_kw: (
            messages,
            {"image_routing_path": "none", "image_attachment_count": 0},
        ),
    )
    monkeypatch.setattr(
        chat_completion_service, "_task_routing_debug_metadata", lambda _task: {}
    )

    async def build_messages(_task: Any, **_kwargs: Any):
        return (
            [{"role": "user", "content": "What is the weather?"}],
            "groq",
            "voice-model",
            {"_prompt_meta": {}},
            {"source_mode": "project", "effective_policy": None},
        )

    monkeypatch.setattr(
        chat_completion_service, "build_messages_for_llm", build_messages
    )
    monkeypatch.setattr(chat_completion_service, "chat_with_ai", lambda *a, **k: answer)
    monkeypatch.setattr(dependencies, "chatlog_db", chat_db)
    return []


def _voice_task(*, thread_id: int, tts_enabled: bool = False) -> VoiceTurnTask:
    return VoiceTurnTask(
        thread_id=thread_id,
        audio_b64=base64.b64encode(b"fake-audio").decode("ascii"),
        audio_mime="audio/webm",
        completion_provider="groq",
        completion_model="voice-model",
        tts_enabled=tts_enabled,
        voice="alloy",
        output_format="mp3",
    )


@pytest.mark.integration
def test_voice_turn_persists_plain_assistant_answer_without_checkpoint(
    disposable_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requirement 1/3: a normal voice request answers and persists."""

    db = GuardianDB(disposable_database)
    chat_db = PostgresChatLogDB(disposable_database)
    thread_id = _seed_thread(db, account_id="voice-account")
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        voice_worker,
        "_safe_publish",
        lambda _task_id, event, data: published.append((event, dict(data))),
    )
    monkeypatch.setattr(
        voice_worker,
        "transcribe",
        lambda *a, **k: "What is the weather?",
    )
    monkeypatch.setattr(
        voice_worker, "get_voice_runtime_config", lambda: SimpleNamespace(
            stt_timeout_seconds=5,
            completion_timeout_seconds=30,
            tts_timeout_seconds=5,
            tts_provider="openai",
        )
    )
    monkeypatch.setattr(voice_worker, "is_cancelled", lambda _task_id: False)
    monkeypatch.setattr(voice_worker, "release_turn_lock", lambda *a, **k: None)
    _seed_completion_service(
        monkeypatch, chat_db, answer="It is sunny and mild."
    )

    voice_worker._run_voice_task(_voice_task(thread_id=thread_id))

    completed = [data for event, data in published if event == "task.completed"]
    assert not [data for event, data in published if event == "task.failed"]
    assert completed, f"voice turn did not complete; events={[e for e, _ in published]}"
    assert completed[0]["assistant_text"] == "It is sunny and mild."
    assert int(completed[0]["assistant_message_id"] or 0) > 0

    # The assistant answer is durably persisted, exactly once.
    with chat_db._sa_session() as session:
        rows = session.execute(
            sa.text(
                "SELECT role, content FROM chat_messages "
                "WHERE thread_id = :thread_id ORDER BY id"
            ),
            {"thread_id": thread_id},
        ).all()
    assistant = [row for row in rows if row[0] == "assistant"]
    assert len(assistant) == 1
    assert assistant[0][1] == "It is sunny and mild."


@pytest.mark.integration
def test_voice_turn_reaches_tts_downstream_lifecycle(
    disposable_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requirement 2: response generation continues into the TTS lifecycle."""

    db = GuardianDB(disposable_database)
    chat_db = PostgresChatLogDB(disposable_database)
    thread_id = _seed_thread(db, account_id="voice-account")
    published: list[tuple[str, dict]] = []
    synthesized: list[str] = []

    monkeypatch.setattr(
        voice_worker,
        "_safe_publish",
        lambda _task_id, event, data: published.append((event, dict(data))),
    )
    monkeypatch.setattr(
        voice_worker, "transcribe", lambda *a, **k: "Read the status aloud."
    )
    monkeypatch.setattr(
        voice_worker, "get_voice_runtime_config", lambda: SimpleNamespace(
            stt_timeout_seconds=5,
            completion_timeout_seconds=30,
            tts_timeout_seconds=5,
            tts_provider="openai",
        )
    )
    monkeypatch.setattr(voice_worker, "is_cancelled", lambda _task_id: False)
    monkeypatch.setattr(voice_worker, "release_turn_lock", lambda *a, **k: None)
    monkeypatch.setattr(
        voice_worker,
        "synthesize",
        lambda text, **_kw: (synthesized.append(text), (b"audio", "mp3"))[1],
    )
    monkeypatch.setattr(
        voice_worker,
        "save_message_audio_asset",
        lambda **kw: {"asset_id": "asset-1", "message_id": kw["message_id"]},
    )
    _seed_completion_service(
        monkeypatch, chat_db, answer="All systems are nominal."
    )

    voice_worker._run_voice_task(_voice_task(thread_id=thread_id, tts_enabled=True))

    assert not [data for event, data in published if event == "task.failed"]
    assert synthesized == ["All systems are nominal."]
    completed = [data for event, data in published if event == "task.completed"]
    assert completed
    assert completed[0]["audio_asset"] == {
        "asset_id": "asset-1",
        "message_id": completed[0]["assistant_message_id"],
    }


@pytest.mark.integration
def test_unbound_task_tool_decision_is_blocked_before_dispatch(
    disposable_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requirement 5: an unbound path cannot dispatch a tool command."""

    db = GuardianDB(disposable_database)
    chat_db = PostgresChatLogDB(disposable_database)
    thread_id = _seed_thread(db, account_id="voice-account")
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        voice_worker,
        "_safe_publish",
        lambda _task_id, event, data: published.append((event, dict(data))),
    )
    monkeypatch.setattr(voice_worker, "transcribe", lambda *a, **k: "Do something")
    monkeypatch.setattr(
        voice_worker, "get_voice_runtime_config", lambda: SimpleNamespace(
            stt_timeout_seconds=5,
            completion_timeout_seconds=30,
            tts_timeout_seconds=5,
            tts_provider="openai",
        )
    )
    monkeypatch.setattr(voice_worker, "is_cancelled", lambda _task_id: False)
    monkeypatch.setattr(voice_worker, "release_turn_lock", lambda *a, **k: None)

    def _seed(monkeypatch: pytest.MonkeyPatch) -> None:
        _seed_completion_service(
            monkeypatch,
            chat_db,
            answer=(
                '{"type":"tool_decision","command_id":"op::health_check",'
                '"arguments":{}}'
            ),
        )

    _seed(monkeypatch)
    # Advertise a tool to the unbound voice task to prove the gate does not
    # depend on the tool simply being absent.
    original_build_task = voice_worker.ChatCompletionTask

    def _task_with_tools(**kwargs: Any) -> Any:
        task = original_build_task(**kwargs)
        task.tools = [{"command_id": "op::health_check"}]
        return task

    monkeypatch.setattr(voice_worker, "ChatCompletionTask", _task_with_tools)

    voice_worker._run_voice_task(_voice_task(thread_id=thread_id))

    # No assistant answer is persisted and no terminal success is claimed.
    with chat_db._sa_session() as session:
        rows = session.execute(
            sa.text(
                "SELECT role FROM chat_messages WHERE thread_id = :thread_id"
            ),
            {"thread_id": thread_id},
        ).all()
    assert [row[0] for row in rows] == ["user"]
    assert not [data for event, data in published if event == "task.completed"]


def test_accepted_task_without_durable_attempt_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requirement 4: an accepted claim with no durable row still fails closed."""

    task = ChatCompletionTask(
        user_id="accepted-account",
        task_id="task-accepted-no-row",
        thread_id=11,
        provider="groq",
        model="mock-model",
        origin="api:chat.complete|turn_id=11111111-1111-4111-8111-111111111111",
    )
    for name, value in build_accepted_chat_task_deadline(
        datetime.now(timezone.utc)
    ).to_dict().items():
        setattr(task, name, value)
    task.turn_id = "11111111-1111-4111-8111-111111111111"
    task.latest_turn_message_id = 1

    class _Boom:
        def _sa_session(self):
            raise RuntimeError("no accepted attempt row")

    def _frozen_lookup(_db, **_values):
        raise RuntimeError("accepted_tool_attempt_unavailable")

    monkeypatch.setattr(
        chat_completion_service, "get_chat_tool_checkpoint", _frozen_lookup
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_execute_completion_attempt",
        lambda **_kwargs: SimpleNamespace(
            output="plain answer",
            attempt_id="attempt-1",
            response_correlation={},
            terminal=None,
            runtime_provenance=None,
        ),
    )
    monkeypatch.setattr(
        chat_completion_service, "_claims_accepted_chat_attempt", lambda _task: True
    )

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as excinfo:
        chat_completion_service._execute_bounded_tool_turn_completion(
            task,
            messages_for_llm=[{"role": "user", "content": "hi"}],
            provider="groq",
            model="mock-model",
            bundle={},
            trace=None,
            base_payload_summary={},
            tool_exposure={},
        )
    assert excinfo.value.args[0] == "tool_checkpoint_unavailable"


def test_unbound_task_claim_detection_is_snapshot_based() -> None:
    """The gate keys off the acceptance snapshot, never request-id presence."""

    unbound = ChatCompletionTask(
        user_id="voice-account",
        thread_id=3,
        provider="groq",
        model="mock-model",
        origin="worker:voice_turn",
    )
    # Every task receives a synthesized request id; that must not imply authority.
    assert unbound.request_id
    assert chat_completion_service._claims_accepted_chat_attempt(unbound) is False

    accepted = ChatCompletionTask(
        user_id="accepted-account",
        thread_id=3,
        provider="groq",
        model="mock-model",
        origin="api:chat.complete|turn_id=11111111-1111-4111-8111-111111111111",
    )
    for name, value in build_accepted_chat_task_deadline(
        datetime.now(timezone.utc)
    ).to_dict().items():
        setattr(accepted, name, value)
    assert chat_completion_service._claims_accepted_chat_attempt(accepted) is True

    # A present-but-incomplete snapshot still claims acceptance (fail closed).
    corrupt = ChatCompletionTask(
        user_id="accepted-account",
        thread_id=3,
        provider="groq",
        model="mock-model",
    )
    corrupt.accepted_at = datetime.now(timezone.utc).isoformat()
    assert chat_completion_service._claims_accepted_chat_attempt(corrupt) is True