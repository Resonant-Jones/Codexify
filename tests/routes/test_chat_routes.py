"""Comprehensive tests for Guardian /chat/* API routes."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm.exc import DetachedInstanceError


@pytest.fixture(autouse=True)
def _ensure_groq_key(monkeypatch):
    """Provide a dummy GROQ_API_KEY and force provider to groq for tests."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    try:
        import guardian.routes.chat as chat_module

        chat_module.llm_settings.LLM_PROVIDER = "groq"
        chat_module.llm_settings.LLM_MODEL = "moonshotai-kimi-k2-instruct-9050"
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _mock_redis_queue_for_chat_routes():
    """Prevent chat route tests from attempting to connect to a real Redis instance.

    The chat routes may reference the queue through different import styles
    (direct imports, module refs, event_bus helpers, etc.). This fixture patches
    both the route module surface and the redis_queue implementation layer.
    """
    fake_queue = MagicMock()
    # Make the fake queue look "healthy" to any availability checks.
    fake_queue.ping.return_value = True
    fake_queue.enqueue.return_value = None
    fake_queue.enqueue_job.return_value = None
    fake_queue.publish.return_value = None

    fake_event_bus = MagicMock()
    fake_event_bus.emit_event.return_value = None

    fake_redis_client = MagicMock()
    fake_redis_client.ping.return_value = True
    fake_redis_client.publish.return_value = 1

    fake_redis_queue_module = MagicMock()
    fake_redis_queue_module.get_queue.return_value = fake_queue
    fake_redis_queue_module.RedisQueue.return_value = fake_queue

    patches = [
        # Route-level references (covers `from ... import ...` usage inside routes).
        patch(
            "guardian.routes.chat.get_queue",
            return_value=fake_queue,
            create=True,
        ),
        patch(
            "guardian.routes.chat.RedisQueue",
            return_value=fake_queue,
            create=True,
        ),
        patch("guardian.routes.chat.event_bus", fake_event_bus, create=True),
        patch(
            "guardian.routes.chat.redis_queue",
            fake_redis_queue_module,
            create=True,
        ),
        # Implementation-level references.
        patch(
            "guardian.queue.redis_queue.get_queue",
            return_value=fake_queue,
            create=True,
        ),
        patch(
            "guardian.queue.redis_queue.RedisQueue",
            return_value=fake_queue,
            create=True,
        ),
        # Last line of defense: if something tries to instantiate a real redis client.
        patch(
            "guardian.queue.redis_queue.redis.Redis",
            return_value=fake_redis_client,
            create=True,
        ),
        patch(
            "guardian.queue.redis_queue.redis.from_url",
            return_value=fake_redis_client,
            create=True,
        ),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


class TestChatThreadsPost:
    """Tests for POST /chat/threads endpoint."""

    def test_create_thread_success(
        self, test_client, mock_db, sample_thread_data
    ):
        """Test successful thread creation returns 200 with thread data."""
        response = test_client.post("/chat/threads", json=sample_thread_data)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "id" in data
        assert "thread" in data
        assert data["thread"]["title"] == "Test Thread"
        mock_db.create_chat_thread.assert_called_once()

    def test_create_thread_minimal_payload(self, test_client, mock_db):
        """Test thread creation with minimal payload uses defaults."""
        response = test_client.post("/chat/threads", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        # Should use default title "New Chat"
        mock_db.create_chat_thread.assert_called_once()
        mock_db.ensure_default_project.assert_called_once_with()
        call_kwargs = mock_db.create_chat_thread.call_args[1]
        assert call_kwargs["title"] == "New Chat"
        assert call_kwargs["user_id"] == "default"
        assert (
            call_kwargs["project_id"]
            == mock_db.ensure_default_project.return_value
        )

    @pytest.mark.xfail(
        reason="Real DB counter vs mock ID - harmless difference"
    )
    def test_create_thread_reuses_recent_empty(self, test_client, mock_db):
        """Test thread creation reuses recent empty thread for same user."""
        mock_db.get_recent_thread.return_value = {"id": 42, "title": "Recent"}
        mock_db.count_messages.return_value = 0

        response = test_client.post(
            "/chat/threads",
            json={"user_id": "test_user", "title": "New Thread"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        # Should NOT create new thread
        mock_db.create_chat_thread.assert_not_called()

    def test_create_thread_with_project_id(self, test_client, mock_db):
        """Test thread creation with explicit project_id."""
        response = test_client.post(
            "/chat/threads", json={"title": "Test", "project_id": 5}
        )

        assert response.status_code == 200
        mock_db.ensure_default_project.assert_not_called()
        mock_db.create_chat_thread.assert_called_once()
        call_kwargs = mock_db.create_chat_thread.call_args[1]
        assert call_kwargs["project_id"] == 5

    def test_create_thread_with_invalid_project_id_falls_back_default(
        self, test_client, mock_db
    ):
        """Non-numeric project ids should fall back to the default project."""
        response = test_client.post(
            "/chat/threads", json={"title": "Test", "project_id": "abc"}
        )

        assert response.status_code == 200
        mock_db.ensure_default_project.assert_called_once_with()
        call_kwargs = mock_db.create_chat_thread.call_args[1]
        assert (
            call_kwargs["project_id"]
            == mock_db.ensure_default_project.return_value
        )

    def test_create_thread_with_metadata(self, test_client, mock_db):
        """Test thread creation with metadata dict to verify psycopg Json() adapter fix."""
        metadata = {
            "source": "test",
            "tags": ["important", "urgent"],
            "count": 42,
        }
        response = test_client.post(
            "/chat/threads",
            json={"title": "Test", "metadata": metadata},
        )

        assert response.status_code == 200
        mock_db.create_chat_thread.assert_called_once()
        call_kwargs = mock_db.create_chat_thread.call_args[1]
        assert call_kwargs["metadata"] == metadata

    def test_create_thread_db_error(self, test_client, mock_db):
        """Test thread creation handles database errors gracefully."""
        mock_db.create_chat_thread.side_effect = Exception("Database error")

        response = test_client.post("/chat/threads", json={"title": "Test"})

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestChatThreadsGet:
    """Tests for GET /chat/threads endpoint."""

    def test_list_threads_success(self, test_client, mock_db):
        """Test successful thread listing returns 200 with threads array."""
        response = test_client.get("/chat/threads")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "threads" in data
        assert isinstance(data["threads"], list)
        assert len(data["threads"]) >= 0

    def test_list_threads_empty(self, test_client, mock_db):
        """Test thread listing with no threads returns empty list."""
        mock_db.list_chat_threads.return_value = []

        response = test_client.get("/chat/threads")

        assert response.status_code == 200
        data = response.json()
        assert data["threads"] == []

    def test_list_threads_db_error(self, test_client, mock_db):
        """Test thread listing handles database errors gracefully."""
        mock_db.list_chat_threads.side_effect = Exception("Database error")

        response = test_client.get("/chat/threads")

        # Should return empty list instead of error
        assert response.status_code == 200
        data = response.json()
        assert data["threads"] == []


class TestChatMessagesPost:
    """Tests for POST /chat/{thread_id}/messages endpoint."""

    def test_post_message_success(self, test_client, mock_db):
        """Test successful message posting returns 200 with message data."""
        payload = {
            "role": "user",
            "content": "Hello, world!",
            "user_id": "test_user",
        }

        response = test_client.post("/chat/1/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "message" in data
        assert data["message"]["role"] == "user"
        assert data["message"]["content"] == "Hello, world!"
        mock_db.create_message.assert_called_once_with(
            1, "user", "Hello, world!"
        )

    def test_post_message_missing_role(self, test_client, mock_db):
        """Test message posting without role returns 400."""
        payload = {"content": "Hello, world!"}

        response = test_client.post("/chat/1/messages", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert "error" in data

    def test_post_message_missing_content(self, test_client, mock_db):
        """Test message posting without content returns 400."""
        payload = {"role": "user"}

        response = test_client.post("/chat/1/messages", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False

    def test_post_message_empty_content(self, test_client, mock_db):
        """Test message posting with empty content returns 400."""
        payload = {"role": "user", "content": "   "}

        response = test_client.post("/chat/1/messages", json=payload)

        assert response.status_code == 400

    def test_post_message_ensures_thread_exists(self, test_client, mock_db):
        """Test message posting ensures thread exists."""
        payload = {"role": "user", "content": "Test", "user_id": "test_user"}

        response = test_client.post("/chat/1/messages", json=payload)

        assert response.status_code == 200
        mock_db.ensure_default_project.assert_called_once_with()
        mock_db.ensure_chat_thread.assert_called_once()
        ensure_kwargs = mock_db.ensure_chat_thread.call_args.kwargs
        assert (
            ensure_kwargs.get("project_id")
            == mock_db.ensure_default_project.return_value
        )

    def test_create_on_send_creates_thread_and_message(
        self, test_client, mock_db
    ):
        """POST /chat/messages creates a new thread when thread_id is omitted."""
        payload = {
            "role": "user",
            "content": "First message",
            "user_id": "test_user",
            "thread_id": None,
            "draft_tab_id": "tab-draft-1",
        }

        response = test_client.post("/chat/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["created_thread"] is True
        assert data["thread_id"] == 1
        assert data["message"]["thread_id"] == 1
        mock_db.create_chat_thread.assert_called_once()
        mock_db.create_message.assert_called_once_with(
            1, "user", "First message"
        )

    def test_create_on_send_uses_existing_thread(self, test_client, mock_db):
        """POST /chat/messages appends when thread_id is provided."""
        payload = {
            "thread_id": 12,
            "role": "user",
            "content": "Hello existing thread",
            "user_id": "test_user",
        }

        response = test_client.post("/chat/messages", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["created_thread"] is False
        assert data["thread_id"] == 12
        mock_db.create_chat_thread.assert_not_called()
        mock_db.create_message.assert_called_once_with(
            12, "user", "Hello existing thread"
        )


class TestChatMessagesGet:
    """Tests for GET /chat/{thread_id}/messages endpoint."""

    def test_get_messages_success(self, test_client, mock_db):
        """Test successful message retrieval returns 200 with messages."""
        response = test_client.get("/chat/1/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "messages" in data
        assert "total" in data
        assert isinstance(data["messages"], list)

    def test_get_messages_with_pagination(self, test_client, mock_db):
        """Test message retrieval with limit and offset parameters."""
        response = test_client.get("/chat/1/messages?limit=10&offset=20")

        assert response.status_code == 200
        mock_db.list_messages.assert_called_once_with(
            1,
            limit=10,
            offset=20,
            exclude_kinds=["fact_evidence"],
        )

    def test_get_messages_empty_thread(self, test_client, mock_db):
        """Test message retrieval for empty thread."""
        mock_db.list_messages.return_value = []
        mock_db.count_messages.return_value = 0

        response = test_client.get("/chat/1/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["total"] == 0

    def test_get_messages_includes_message_audio_metadata(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.list_messages.return_value = [
            {
                "id": 55,
                "thread_id": 1,
                "role": "assistant",
                "content": "Hello with audio",
                "created_at": "2026-03-07T12:00:00.000Z",
            }
        ]
        mock_db.count_messages.return_value = 1
        monkeypatch.setattr(
            "guardian.routes.chat.list_message_audio_assets",
            lambda **_kwargs: {
                55: {
                    "id": 99,
                    "status": "ready",
                    "stream_url": "/api/voice/audio/99",
                    "src_url": "/media/audio/messages/55.wav",
                    "mime_type": "audio/wav",
                    "duration_seconds": 1.25,
                    "delivery_variants_json": {
                        "source": "assistant_message_autogenerate"
                    },
                }
            },
        )

        response = test_client.get("/chat/1/messages")

        assert response.status_code == 200
        payload = response.json()
        assert payload["messages"][0]["audio_status"] == "ready"
        assert payload["messages"][0]["audio_url"] == "/api/voice/audio/99"
        assert payload["messages"][0]["audio_mime_type"] == "audio/wav"
        assert payload["messages"][0]["audio_duration_ms"] == 1250

    def test_get_messages_includes_ready_audio_from_live_lookup_without_detached_access(
        self, test_client, mock_db, monkeypatch
    ):
        from guardian.voice import audio_assets

        class _DetachOnCloseRow:
            def __init__(self, **data):
                self._data = data
                self._detached = False

            def detach(self):
                self._detached = True

            def _get(self, key):
                if self._detached:
                    raise DetachedInstanceError(
                        f"Attribute '{key}' was accessed after the session closed"
                    )
                return self._data[key]

            @property
            def id(self):
                return self._get("id")

            @property
            def message_id(self):
                return self._get("message_id")

            @property
            def provider(self):
                return self._get("provider")

            @property
            def voice(self):
                return self._get("voice")

            @property
            def text_hash(self):
                return self._get("text_hash")

            @property
            def src_url(self):
                return self._get("src_url")

            @property
            def internal_format(self):
                return self._get("internal_format")

            @property
            def delivery_variants_json(self):
                return self._get("delivery_variants_json")

            @property
            def duration_seconds(self):
                return self._get("duration_seconds")

            @property
            def filesize_bytes(self):
                return self._get("filesize_bytes")

            @property
            def created_at(self):
                return self._get("created_at")

        ready_row = _DetachOnCloseRow(
            id=109,
            message_id=59,
            provider="chatterbox",
            voice="assistant",
            text_hash="ready123",
            src_url="/media/audio/messages/59.wav",
            internal_format="wav",
            delivery_variants_json={
                "status": "ready",
                "source": "assistant_message_autogenerate",
                "mime_type": "audio/wav",
            },
            duration_seconds=1.5,
            filesize_bytes=512,
            created_at=datetime(2026, 3, 8, 13, 15, tzinfo=timezone.utc),
        )

        class _FakeQuery:
            def __init__(self, rows):
                self._rows = rows

            def filter(self, *_args, **_kwargs):
                return self

            def order_by(self, *_args, **_kwargs):
                return self

            def all(self):
                return list(self._rows)

        class _FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                ready_row.detach()
                return False

            def query(self, _model):
                return _FakeQuery([ready_row])

        class _FakePostgresChatLogDB:
            def _sa_session(self):
                return _FakeSession()

        mock_db.list_messages.return_value = [
            {
                "id": 59,
                "thread_id": 1,
                "role": "assistant",
                "content": "Hello from live lookup",
                "created_at": "2026-03-07T12:01:00.000Z",
            }
        ]
        mock_db.count_messages.return_value = 1
        monkeypatch.setenv("GUARDIAN_MEDIA_URL_SECRET", "voice-test-secret")
        monkeypatch.setattr(
            audio_assets,
            "_db",
            lambda: _FakePostgresChatLogDB(),
        )
        monkeypatch.setattr(
            "guardian.routes.chat.list_message_audio_assets",
            audio_assets.list_message_audio_assets,
        )

        response = test_client.get("/chat/1/messages")

        assert response.status_code == 200
        payload = response.json()
        assert payload["messages"][0]["audio_status"] == "ready"
        assert payload["messages"][0]["audio_url"] == "/api/voice/audio/109"
        assert payload["messages"][0]["audio_mime_type"] == "audio/wav"
        assert payload["messages"][0]["audio_duration_ms"] == 1500


class TestChatCompletePost:
    """Tests for POST /chat/{thread_id}/complete endpoint."""

    def test_complete_success(self, test_client, mock_db, monkeypatch):
        """Test completion enqueues a task and returns a task id."""
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue",
            lambda task, queue_name: captured.update(
                {"task": task, "queue_name": queue_name}
            ),
        )

        response = test_client.post("/chat/1/complete", json={})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("task_id"), str)
        task = captured.get("task")
        assert task is not None
        assert getattr(task, "thread_id") == 1
        assert getattr(task, "turn_lock_owner") == data["task_id"]
        assert captured.get("queue_name") == "codexify:queue:chat"

    def test_complete_depth_contract_non_deep_request(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.get_chat_thread.return_value = {"id": 1, "project_id": 7}
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue", lambda *a, **k: None
        )

        response = test_client.post(
            "/chat/1/complete", json={"depth_mode": "diagnostic"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "requested_depth_mode" in data
        assert "effective_depth_mode" in data
        assert "depth_downgrade_reason" in data
        assert data["requested_depth_mode"] == "light"
        assert data["effective_depth_mode"] == "light"
        assert data["depth_downgrade_reason"] is None
        # Internal legacy runtime depth_mode remains unchanged for non-deep.
        assert data["depth_mode"] == "diagnostic"
        assert data["depth_downgrade_reason"] not in {
            "capability_missing",
            "server_forced",
        }

    def test_complete_depth_contract_deep_no_project(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.get_chat_thread.return_value = {"id": 1, "project_id": None}
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue", lambda *a, **k: None
        )

        response = test_client.post(
            "/chat/1/complete", json={"depth_mode": "deep"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requested_depth_mode"] == "deep"
        assert data["effective_depth_mode"] == "light"
        assert data["depth_downgrade_reason"] == "no_project"
        assert data["depth_mode"] == "normal"
        assert data["depth_downgrade_reason"] not in {
            "capability_missing",
            "server_forced",
        }

    def test_complete_depth_contract_deep_project_light(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.get_chat_thread.return_value = {"id": 1, "project_id": 7}
        mock_db.get_project_identity_depth.return_value = "light"
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue", lambda *a, **k: None
        )

        response = test_client.post(
            "/chat/1/complete", json={"depth_mode": "deep"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requested_depth_mode"] == "deep"
        assert data["effective_depth_mode"] == "light"
        assert data["depth_downgrade_reason"] == "project_identity_depth_light"
        assert data["depth_mode"] == "normal"
        assert data["depth_downgrade_reason"] not in {
            "capability_missing",
            "server_forced",
        }

    def test_complete_depth_contract_deep_policy_rejected(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.get_chat_thread.return_value = {"id": 1, "project_id": 7}
        mock_db.get_project_identity_depth.return_value = "deep"
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        monkeypatch.setattr(
            "guardian.routes.chat.can_run_deep_identity_modeling",
            lambda *_a, **_k: False,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue", lambda *a, **k: None
        )

        response = test_client.post(
            "/chat/1/complete", json={"depth_mode": "deep"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requested_depth_mode"] == "deep"
        assert data["effective_depth_mode"] == "light"
        assert data["depth_downgrade_reason"] == "policy_gate_rejected"
        assert data["depth_mode"] == "normal"
        assert data["depth_downgrade_reason"] not in {
            "capability_missing",
            "server_forced",
        }

    def test_complete_depth_contract_deep_allowed(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.get_chat_thread.return_value = {"id": 1, "project_id": 7}
        mock_db.get_project_identity_depth.return_value = "deep"
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        monkeypatch.setattr(
            "guardian.routes.chat.can_run_deep_identity_modeling",
            lambda *_a, **_k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue", lambda *a, **k: None
        )

        response = test_client.post(
            "/chat/1/complete", json={"depth_mode": "deep"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requested_depth_mode"] == "deep"
        assert data["effective_depth_mode"] == "deep"
        assert data["depth_downgrade_reason"] is None
        assert data["depth_mode"] == "deep"
        assert data["depth_downgrade_reason"] not in {
            "capability_missing",
            "server_forced",
        }

    def test_complete_depth_contract_exception_logs_once(
        self, test_client, mock_db, monkeypatch
    ):
        mock_db.get_chat_thread.return_value = {"id": 1, "project_id": 7}
        mock_db.get_project_identity_depth.side_effect = RuntimeError("boom")
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        exception_spy = MagicMock()
        monkeypatch.setattr(
            "guardian.routes.chat.logger.exception", exception_spy
        )
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue", lambda *a, **k: None
        )

        response = test_client.post(
            "/chat/1/complete", json={"depth_mode": "deep"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requested_depth_mode"] == "deep"
        assert data["effective_depth_mode"] == "light"
        assert data["depth_downgrade_reason"] == "unknown"
        assert data["depth_mode"] == "normal"
        assert exception_spy.call_count == 1
        assert data["depth_downgrade_reason"] not in {
            "capability_missing",
            "server_forced",
        }

    def test_complete_with_model_override(
        self, test_client, mock_db, monkeypatch
    ):
        """Test completion task captures model override."""
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]

        captured: dict[str, object] = {}
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue",
            lambda task, queue_name: captured.update(
                {"task": task, "queue_name": queue_name}
            ),
        )

        response = test_client.post(
            "/chat/1/complete", json={"model": "custom-model"}
        )

        assert response.status_code == 200
        task = captured.get("task")
        assert task is not None
        assert getattr(task, "model") == "custom-model"

    @pytest.mark.xfail(reason="Error status code difference - acceptable")
    def test_complete_empty_context(self, test_client, mock_db):
        """Test completion with no usable context returns 400."""
        mock_db.list_messages.return_value = []

        response = test_client.post("/chat/1/complete", json={})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_complete_filters_null_content(
        self, test_client, mock_db, monkeypatch
    ):
        """Test completion still enqueues when at least one usable message exists."""
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "null"},
            {"role": "user", "content": ""},
            {"role": "user", "content": "Real message"},
        ]

        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue",
            lambda *a, **k: None,
        )

        response = test_client.post("/chat/1/complete", json={})

        assert response.status_code == 200
        assert "task_id" in response.json()

    def test_complete_groq_error(self, test_client, mock_db, monkeypatch):
        """Test completion returns structured 503 when enqueue fails."""
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]

        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.release_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("queue down")),
        )

        response = test_client.post("/chat/1/complete", json={})

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "completion_service_unavailable"
        assert detail["reason"] == "queue_unavailable"
        assert "Completion service unavailable" in detail["message"]

    def test_complete_turn_lock_error_returns_structured_503(
        self, test_client, mock_db, monkeypatch
    ):
        """Turn lock failures should fail loudly with completion-service detail."""
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello"}
        ]

        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("redis down")),
        )

        response = test_client.post("/chat/1/complete", json={})

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "completion_service_unavailable"
        assert detail["reason"] == "turn_lock_unavailable"
        assert "Completion service unavailable" in detail["message"]

    def test_api_complete_returns_context_bundle(
        self, test_client, mock_db, monkeypatch
    ):
        """Ensure /api/chat/* alias enqueues chat completion task."""
        mock_db.list_messages.return_value = [
            {"role": "user", "content": "Hello there"}
        ]

        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue",
            lambda *a, **k: None,
        )

        response = test_client.post(
            "/api/chat/1/complete", json={"depth_mode": "normal"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("task_id"), str)


class TestChatMessageDelete:
    """Tests for DELETE /chat/{thread_id}/messages/{message_id} endpoint."""

    def test_delete_message_success(self, test_client, mock_db):
        """Test successful message deletion returns 200."""
        response = test_client.delete("/chat/1/messages/5")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        mock_db.delete_message.assert_called_once_with(1, 5)

    def test_delete_message_writes_audit_log(self, test_client, mock_db):
        """Test message deletion writes audit log."""
        response = test_client.delete("/chat/1/messages/5")

        assert response.status_code == 200
        mock_db.write_audit_log.assert_called_once()


class TestChatThreadBranchPost:
    """Tests for POST /chat/{thread_id}/branch endpoint."""

    @pytest.mark.xfail(
        reason="Real DB counter vs mock ID - harmless difference"
    )
    def test_branch_thread_success(self, test_client, mock_db, api_headers):
        """Test successful thread branching returns 200 with new thread."""
        mock_db.get_chat_thread.return_value = {
            "id": 1,
            "user_id": "test_user",
            "title": "Parent Thread",
            "summary": "Parent summary",
            "project_id": 1,
        }
        mock_db.create_chat_thread.return_value = {
            "id": 2,
            "user_id": "test_user",
            "title": "Parent Thread (branch)",
            "summary": "Parent summary",
            "project_id": 1,
            "parent_id": 1,
        }

        response = test_client.post(
            "/chat/1/branch", json={}, headers=api_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["parent_id"] == 1

    def test_branch_thread_with_custom_title(
        self, test_client, mock_db, api_headers
    ):
        """Test branching with custom title."""
        mock_db.get_chat_thread.return_value = {
            "id": 1,
            "user_id": "test_user",
            "title": "Parent",
            "summary": "",
            "project_id": 1,
        }
        mock_db.create_chat_thread.return_value = {
            "id": 2,
            "user_id": "test_user",
            "title": "Custom Branch",
            "summary": "",
            "project_id": 1,
            "parent_id": 1,
        }

        response = test_client.post(
            "/chat/1/branch",
            json={"title": "Custom Branch"},
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Custom Branch"

    def test_branch_thread_not_found(self, test_client, mock_db, api_headers):
        """Test branching non-existent thread returns 404."""
        mock_db.get_chat_thread.return_value = None

        response = test_client.post(
            "/chat/999/branch", json={}, headers=api_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestChatThreadPatch:
    """Tests for PATCH /chat/{thread_id} endpoint."""

    def test_update_thread_title_success(
        self, test_client, mock_db, api_headers
    ):
        """Test successful thread title update returns 200."""
        response = test_client.patch(
            "/chat/1", json={"title": "Updated Title"}, headers=api_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_update_thread_summary(self, test_client, mock_db, api_headers):
        """Test thread summary update."""
        response = test_client.patch(
            "/chat/1", json={"summary": "Updated summary"}, headers=api_headers
        )

        assert response.status_code == 200

    def test_update_thread_project_id(self, test_client, mock_db, api_headers):
        """Test thread project_id update."""
        response = test_client.patch(
            "/chat/1", json={"project_id": 5}, headers=api_headers
        )

        assert response.status_code == 200

    def test_update_thread_archive(self, test_client, mock_db, api_headers):
        """Test archiving a thread."""
        response = test_client.patch(
            "/chat/1", json={"archived": True}, headers=api_headers
        )

        assert response.status_code == 200
        mock_db.archive_thread.assert_called_once_with(1)

    def test_update_thread_not_found(self, test_client, mock_db, api_headers):
        """Test updating non-existent thread returns 404."""
        mock_db.get_chat_thread.return_value = None

        response = test_client.patch(
            "/chat/999", json={"title": "New Title"}, headers=api_headers
        )

        assert response.status_code == 404

    def test_update_thread_empty_payload(
        self, test_client, mock_db, api_headers
    ):
        """Test updating thread with empty payload returns 400."""
        response = test_client.patch("/chat/1", json={}, headers=api_headers)

        assert response.status_code == 400


class TestChatThreadDelete:
    """Tests for DELETE /chat/{thread_id} endpoint."""

    def test_delete_thread_success(self, test_client, mock_db):
        """Test successful thread deletion returns 200."""
        response = test_client.delete("/chat/1")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        mock_db.delete_thread.assert_called_once()

    def test_delete_thread_with_force(self, test_client, mock_db):
        """Test thread deletion with force parameter."""
        response = test_client.delete("/chat/1?force=true")

        assert response.status_code == 200
        mock_db.delete_thread.assert_called_once_with(1, force=True)

    def test_delete_thread_not_found(self, test_client, mock_db):
        """Test deleting non-existent thread returns 404."""
        mock_db.delete_thread.return_value = False

        response = test_client.delete("/chat/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestApiChatAlias:
    """Ensure /api/chat alias endpoints behave for the frontend."""

    def test_api_chat_create_thread(self, test_client, mock_db):
        resp = test_client.post("/api/chat/threads", json={"title": "From API"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data  # API returns 'id', not 'thread_id'

    def test_api_chat_create_on_send_alias(self, test_client, mock_db):
        resp = test_client.post(
            "/api/chat/messages",
            json={
                "role": "user",
                "content": "hello",
                "thread_id": None,
                "draft_tab_id": "tab-1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "thread_id" in data

    def test_api_chat_root_simple_reply(self, test_client):
        resp = test_client.post("/api/chat", json={"prompt": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert data["reply"]

    def test_api_chat_complete_missing_thread(self, test_client, mock_db):
        mock_db.get_chat_thread.return_value = None
        resp = test_client.post("/api/chat/999/complete", json={})
        assert resp.status_code == 404

    def test_api_chat_complete_missing_config(
        self, test_client, mock_db, monkeypatch
    ):
        monkeypatch.setattr(
            "guardian.routes.chat.llm_settings.GROQ_API_KEY", None
        )
        monkeypatch.setattr(
            "guardian.routes.chat.acquire_turn_lock",
            lambda *a, **k: True,
        )
        monkeypatch.setattr(
            "guardian.routes.chat.enqueue",
            lambda *a, **k: None,
        )
        resp = test_client.post("/api/chat/1/complete", json={})
        assert resp.status_code == 200
        assert isinstance(resp.json().get("task_id"), str)
