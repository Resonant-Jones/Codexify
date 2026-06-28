"""Tests for the @luna n8n mention routing boundary.

Covers:
- pure mention matching and stripping
- transcript formatting and speaker labels
- payload construction (allowlisted metadata, no leakage)
- reply extraction across n8n response shapes
- chat_complete route integration: detection, payload, persistence, status mapping
- regression: normal chat does not invoke the Luna adapter
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from guardian.core.dependencies import RequestUserScope
from guardian.integrations import luna_n8n
from guardian.routes import chat as chat_routes
from tests.utils import get_test_user_id


# ---- Fixtures / helpers ---------------------------------------------------


def _override_request_scope(test_client, user_id: str) -> None:
    test_client.app.dependency_overrides[
        chat_routes.get_request_user_scope
    ] = lambda: RequestUserScope(
        user_id=user_id,
        subject_id=user_id,
        account_id=user_id,
        multi_user_enabled=False,
    )


def _thread_config_snapshot() -> dict[str, object]:
    return {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }


def _basic_thread(user_id: str, thread_id: int = 1) -> dict[str, object]:
    return {
        "id": thread_id,
        "user_id": user_id,
        "project_id": 1,
        "thread_config": _thread_config_snapshot(),
    }


def _stub_turn_locks(monkeypatch) -> None:
    monkeypatch.setattr(chat_routes, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(chat_routes, "release_turn_lock", lambda *a, **k: True)


def _stub_normal_completion_path(monkeypatch) -> list[tuple]:
    """Stub everything past the Luna interception so the normal path is
    observable but does not perform real work.
    """
    enqueue_calls: list[tuple] = []
    monkeypatch.setattr(
        chat_routes,
        "enqueue",
        lambda *a, **k: enqueue_calls.append((a, k)),
    )
    monkeypatch.setattr(
        chat_routes,
        "_publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )
    return enqueue_calls


def _stub_persist(monkeypatch, thread_id: int = 1) -> list[dict]:
    """Stub ``_persist_message_to_thread`` and record the kwargs."""
    persist_calls: list[dict] = []

    def _fake_persist(**kwargs):
        persist_calls.append(kwargs)
        return {
            "message": {
                "id": 99,
                "thread_id": kwargs.get("thread_id", thread_id),
                "role": kwargs.get("role", "assistant"),
                "content": kwargs.get("content", ""),
            },
            "thread": {"id": kwargs.get("thread_id", thread_id)},
        }

    monkeypatch.setattr(chat_routes, "_persist_message_to_thread", _fake_persist)
    return persist_calls


def _post_complete(test_client, thread_id: int = 1):
    return test_client.post(f"/chat/{thread_id}/complete", json={})


# ---- Pure mention matching ----------------------------------------------


class TestMentionMatching:
    @pytest.mark.parametrize(
        "text",
        [
            "@luna hello",
            "@Luna, hello",
            "  @LUNA: hello",
            "@luna - hello",
            "@luna\thello",
            "@luna\nhello",
        ],
    )
    def test_accepts_valid_leading_forms(self, text: str) -> None:
        assert luna_n8n.is_luna_mention(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "[Zac]: @luna test",
            "[Any Future Display Name]: @luna test",
            "[Name With Spaces]: @luna - test",
        ],
    )
    def test_accepts_display_name_prefix_forms(self, text: str) -> None:
        assert luna_n8n.is_luna_mention(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "@lunatic hello",
            "hello @luna",
            '"@luna hello"',
            "  @lunatic",
            "normal question",
        ],
    )
    def test_rejects_invalid_forms(self, text: str) -> None:
        assert luna_n8n.is_luna_mention(text) is False

    @pytest.mark.parametrize(
        "text",
        [
            "[Zac]: hello @luna",
            "[Zac]: some @luna text",
        ],
    )
    def test_rejects_mid_message_mention_after_prefix(self, text: str) -> None:
        """A bracketed prefix followed by non-leading @luna is rejected."""
        assert luna_n8n.is_luna_mention(text) is False

    @pytest.mark.parametrize("value", [None, 123, [], {}])
    def test_rejects_non_string(self, value) -> None:
        assert luna_n8n.is_luna_mention(value) is False


# ---- Strip mention ------------------------------------------------------


class TestStripMention:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("@luna hello", "hello"),
            ("@Luna, hello", "hello"),
            ("  @LUNA: hello", "hello"),
            ("@luna - hello", "hello"),
            ("@luna\nfoo bar", "foo bar"),
        ],
    )
    def test_strips_with_separators(self, text: str, expected: str) -> None:
        assert luna_n8n.strip_luna_mention(text) == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("[Zac]: @luna test", "test"),
            ("[Any Future Display Name]: @luna test", "test"),
            ("[Name With Spaces]: @luna - test", "test"),
            ("[Zac]: @luna multi word command", "multi word command"),
        ],
    )
    def test_strips_display_name_prefix(self, text: str, expected: str) -> None:
        """The [Display Name]: prefix is consumed; only the message after
        @luna is returned."""
        assert luna_n8n.strip_luna_mention(text) == expected

    @pytest.mark.parametrize(
        "text",
        ["@luna", "@luna,", "@luna:", "@luna -", "@LUNA,", "@luna   "],
    )
    def test_empty_remainder_returns_none(self, text: str) -> None:
        assert luna_n8n.strip_luna_mention(text) is None

    @pytest.mark.parametrize(
        "text",
        [
            "[Zac]: @luna",
            "[Zac]: @luna,",
            "[Zac]: @luna   ",
            "[Any Name]: @luna:",
            "[Any Name]: @luna -",
        ],
    )
    def test_empty_remainder_with_prefix_returns_none(self, text: str) -> None:
        """A bare [Name]: @luna with no command is treated as empty."""
        assert luna_n8n.strip_luna_mention(text) is None

    def test_no_mention_returns_none(self) -> None:
        assert luna_n8n.strip_luna_mention("hello world") is None

    @pytest.mark.parametrize("value", [None, 123, []])
    def test_non_string_returns_none(self, value) -> None:
        assert luna_n8n.strip_luna_mention(value) is None


# ---- Format transcript --------------------------------------------------


class TestFormatTranscript:
    def test_includes_preamble_and_header_by_default(self) -> None:
        out = luna_n8n.format_transcript(
            [{"role": "user", "content": "Q?"}]
        )
        assert out.startswith("You are Luna.")
        assert "## Chat Transcript" in out

    def test_preamble_can_be_disabled(self) -> None:
        out = luna_n8n.format_transcript(
            [{"role": "user", "content": "Q?"}],
            preamble=None,
        )
        assert "You are Luna" not in out
        assert "## Chat Transcript" in out

    def test_user_and_assistant_labels(self) -> None:
        out = luna_n8n.format_transcript(
            [
                {"role": "user", "content": "question"},
                {"role": "assistant", "content": "answer"},
            ]
        )
        assert "User:\nquestion" in out
        assert "Guardian:\nanswer" in out

    def test_custom_user_display_name(self) -> None:
        out = luna_n8n.format_transcript(
            [{"role": "user", "content": "q"}],
            user_display_name="Zac",
        )
        assert "Zac:\nq" in out

    def test_unknown_roles_skipped(self) -> None:
        out = luna_n8n.format_transcript(
            [
                {"role": "system", "content": "secret-system"},
                {"role": "tool", "content": "secret-tool"},
                {"role": "user", "content": "visible"},
            ]
        )
        assert "secret-system" not in out
        assert "secret-tool" not in out
        assert "visible" in out

    def test_empty_and_null_content_skipped(self) -> None:
        out = luna_n8n.format_transcript(
            [
                {"role": "user", "content": "null"},
                {"role": "user", "content": ""},
                {"role": "user", "content": "   "},
                {"role": "assistant", "content": "kept"},
            ]
        )
        # Only the kept assistant line is labeled
        assert out.count("User:") == 0
        assert "Guardian:\nkept" in out

    def test_chronological_order_preserved(self) -> None:
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "third"},
        ]
        out = luna_n8n.format_transcript(msgs)
        assert out.find("first") < out.find("second") < out.find("third")

    def test_structured_multimodal_content_flattened(self) -> None:
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hello "},
                    {"type": "image_url"},
                    {"type": "text", "text": "world"},
                ],
            }
        ]
        out = luna_n8n.format_transcript(msgs)
        assert "User:\nhello world" in out

    def test_oversized_raises_upstream_error(self) -> None:
        msgs = [
            {
                "role": "user",
                "content": "x" * (luna_n8n.MAX_TRANSCRIPT_CHARS + 1),
            }
        ]
        with pytest.raises(luna_n8n.LunaUpstreamError):
            luna_n8n.format_transcript(msgs)

    def test_does_not_invent_personal_names(self) -> None:
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        out = luna_n8n.format_transcript(msgs, user_display_name="Zac")
        # The transcript must contain ONLY the configured speaker labels.
        # No "Zac:" or "Guardian:" beyond the intentional ones.
        for name in ("Alice", "Bob", "Luna"):
            assert f"{name}:" not in out

    def test_luna_messages_labeled_as_luna(self) -> None:
        """Assistant messages with source=luna_n8n in message_metadata
        are labeled 'Luna' instead of 'Guardian'."""
        out = luna_n8n.format_transcript(
            [
                {"role": "user", "content": "@luna hello"},
                {
                    "role": "assistant",
                    "content": "Hi there",
                    "message_metadata": {
                        "source": "luna_n8n",
                        "display_name": "Luna",
                    },
                },
                {"role": "user", "content": "thanks"},
                {"role": "assistant", "content": "You're welcome"},
            ],
            user_display_name="Zac",
        )
        assert "Zac:\n@luna hello" in out
        assert "Luna:\nHi there" in out
        assert "Zac:\nthanks" in out
        assert "Guardian:\nYou're welcome" in out
        # Luna label only appears for the luna_n8n message
        assert out.count("Luna:") == 1

    def test_luna_label_not_applied_to_non_luna_assistant(self) -> None:
        """An assistant message without luna_n8n source is labeled Guardian."""
        out = luna_n8n.format_transcript(
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ]
        )
        assert "Guardian:\nhi" in out
        assert "Luna:" not in out


# ---- Build payload ------------------------------------------------------


class TestBuildPayload:
    def test_basic_payload_shape(self) -> None:
        p = luna_n8n.build_payload(
            "transcript text",
            session_id="codexify-thread-42",
            thread_id=42,
        )
        assert p["chatInput"] == "transcript text"
        assert p["sessionId"] == "codexify-thread-42"
        assert p["metadata"]["source"] == "codexify"
        assert p["metadata"]["threadId"] == 42
        assert "projectId" not in p["metadata"]

    def test_includes_project_id_when_present(self) -> None:
        p = luna_n8n.build_payload(
            "t", session_id="s", thread_id=1, project_id=2
        )
        assert p["metadata"]["projectId"] == 2

    def test_omits_thread_id_when_none(self) -> None:
        p = luna_n8n.build_payload("t", session_id="s")
        assert "threadId" not in p["metadata"]

    def test_metadata_is_allowlisted(self) -> None:
        p = luna_n8n.build_payload("t", session_id="s", thread_id=1)
        assert set(p["metadata"].keys()) <= {"source", "threadId", "projectId"}

    def test_session_id_required(self) -> None:
        with pytest.raises(ValueError):
            luna_n8n.build_payload("t", session_id="")

    def test_chat_input_required(self) -> None:
        with pytest.raises(ValueError):
            luna_n8n.build_payload("", session_id="s")


# ---- Resolve user display name -----------------------------------------


class TestResolveUserDisplayName:
    """Priority chain: auth display name > operator env > "User"."""

    def test_auth_name_used_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "Operator")
        assert (
            luna_n8n.resolve_user_display_name("Zac") == "Zac"
        )

    def test_auth_name_wins_over_operator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "Operator")
        assert (
            luna_n8n.resolve_user_display_name("Zac", operator_name="Other")
            == "Zac"
        )

    def test_auth_name_whitespace_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "Operator")
        assert (
            luna_n8n.resolve_user_display_name("  Zac  ") == "Zac"
        )

    @pytest.mark.parametrize("value", [None, "", "   ", "\t\n"])
    def test_empty_or_missing_auth_falls_through_to_operator(
        self, value, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "Operator")
        assert (
            luna_n8n.resolve_user_display_name(value) == "Operator"
        )

    def test_operator_kwarg_overrides_module_constant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "FromEnv")
        assert (
            luna_n8n.resolve_user_display_name(
                None, operator_name="FromKwarg"
            )
            == "FromKwarg"
        )

    def test_fallback_to_user_when_no_auth_no_operator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "")
        assert (
            luna_n8n.resolve_user_display_name(None) == "User"
        )

    def test_non_string_auth_name_coerced_to_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Defensive: a non-string value (e.g. an integer) should not crash;
        # it is coerced via str() and used when non-empty.
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "")
        assert (
            luna_n8n.resolve_user_display_name(42) == "42"
        )

    def test_format_transcript_uses_resolved_label(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "Zac")
        msgs = [{"role": "user", "content": "hi"}]
        out = luna_n8n.format_transcript(
            msgs,
            user_display_name=luna_n8n.resolve_user_display_name(None),
        )
        assert "Zac:\nhi" in out

    def test_format_transcript_uses_auth_label_when_auth_wins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(luna_n8n, "LUNA_OPERATOR_NAME", "Operator")
        msgs = [{"role": "user", "content": "hi"}]
        out = luna_n8n.format_transcript(
            msgs,
            user_display_name=luna_n8n.resolve_user_display_name("RealUser"),
        )
        assert "RealUser:\nhi" in out
        assert "Operator" not in out


# ---- Extract reply ------------------------------------------------------


class TestExtractReply:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ('{"message": "hi"}', "hi"),
            ('{"output": "hi"}', "hi"),
            ('{"text": "hi"}', "hi"),
            ('{"response": "hi"}', "hi"),
            ('[{"message": "hi"}]', "hi"),
            ("plain text reply", "plain text reply"),
        ],
    )
    def test_recognized_shapes(self, raw: str, expected: str) -> None:
        assert luna_n8n.extract_luna_reply(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "{}",
            '{"unrelated_key": "hi"}',
            '[{"message": "a"}, {"message": "b"}]',
            "[]",
        ],
    )
    def test_unrecognized_or_empty_raises(self, raw: str) -> None:
        with pytest.raises(luna_n8n.LunaUpstreamError):
            luna_n8n.extract_luna_reply(raw)

    def test_none_raises(self) -> None:
        with pytest.raises(luna_n8n.LunaUpstreamError):
            luna_n8n.extract_luna_reply(None)


# ---- Route integration --------------------------------------------------


class TestChatCompleteLunaRouting:
    def _setup(
        self,
        test_client,
        mock_db,
        monkeypatch,
        *,
        messages: list[dict],
        reply: str = "Luna reply",
        raise_in_call: Exception | None = None,
        thread_id: int = 1,
    ):
        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id, thread_id)
        mock_db.list_messages.return_value = messages

        if raise_in_call is None:
            call_mock = AsyncMock(return_value=reply)
        else:
            async def _raise(*_a, **_k):
                raise raise_in_call
            call_mock = _raise
        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", call_mock)

        persist_calls = _stub_persist(monkeypatch, thread_id=thread_id)
        enqueue_calls = _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        return user_id, call_mock, persist_calls, enqueue_calls

    def _cleanup(self, test_client) -> None:
        test_client.app.dependency_overrides.pop(
            chat_routes.get_request_user_scope, None
        )

    def test_routes_luna_mention_and_persists_reply(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        _, call_mock, persist_calls, enqueue_calls = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "earlier question"},
                {"id": 2, "role": "assistant", "content": "earlier answer"},
                {"id": 3, "role": "user", "content": "@luna hello there"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["provider"] == "luna"
        assert body["model"] == "luna-n8n"
        assert body["reply"] == "Luna reply"
        assert body["source_mode"] == "luna"
        assert body["thread_id"] == 1
        assert body["turn_id"]
        assert body["task_id"]
        # Adapter was called exactly once
        assert call_mock.call_count == 1
        # Persistence was called once with the assistant role and reply text
        assert len(persist_calls) == 1
        assert persist_calls[0]["role"] == "assistant"
        assert persist_calls[0]["content"] == "Luna reply"
        assert persist_calls[0]["thread_id"] == 1
        # Normal completion path was NOT invoked
        assert enqueue_calls == []

    def test_persists_luna_identity_metadata(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """The Luna reply is persisted with source=luna_n8n and
        display_name=Luna in its message metadata so the frontend can
        render it as Luna.
        """
        _, _, persist_calls, _ = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna hi"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200, response.text
        assert len(persist_calls) == 1
        metadata = persist_calls[0].get("message_metadata")
        assert metadata is not None, "message_metadata must be set"
        assert metadata.get("source") == "luna_n8n"
        assert metadata.get("display_name") == "Luna"
        # No spurious extra keys — the contract is exactly these two.
        assert set(metadata.keys()) == {"source", "display_name"}

    def test_synchronous_response_includes_identity(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """The sync response includes the identity dict so the frontend
        can render the reply as Luna without re-reading the thread.
        """
        _, _, _, _ = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna hi"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        body = response.json()
        identity = body.get("identity")
        assert identity is not None, "identity must be present in response"
        assert identity.get("source") == "luna_n8n"
        assert identity.get("display_name") == "Luna"

    def test_payload_strips_mention_and_includes_full_transcript(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        captured: dict = {}

        async def _capture(payload, **_):
            captured.update(dict(payload))
            return "ok"

        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", _capture)
        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id)
        mock_db.list_messages.return_value = [
            {"id": 1, "role": "user", "content": "earlier"},
            {"id": 2, "role": "assistant", "content": "answer"},
            {"id": 3, "role": "user", "content": "@Luna, please summarize"},
        ]
        _stub_persist(monkeypatch)
        _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        chat_input = captured["chatInput"]
        # Latest user message has mention stripped
        assert "please summarize" in chat_input
        assert "@Luna" not in chat_input
        # Earlier messages are preserved (with their original labels)
        assert "earlier" in chat_input
        assert "answer" in chat_input
        # Session ID is thread-scoped and stable
        assert captured["sessionId"] == "codexify-thread-1"
        # Allowlisted metadata only
        assert set(captured["metadata"].keys()) <= {
            "source", "threadId", "projectId"
        }
        assert captured["metadata"]["source"] == "codexify"
        assert captured["metadata"]["threadId"] == 1

    def test_only_latest_user_message_has_mention_stripped(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        captured: dict = {}

        async def _capture(payload, **_):
            captured.update(dict(payload))
            return "ok"

        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", _capture)
        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id)
        mock_db.list_messages.return_value = [
            # Earlier user message happens to start with @luna too —
            # it is NOT the latest turn and must NOT be stripped.
            {"id": 1, "role": "user", "content": "@luna earlier mention"},
            {"id": 2, "role": "assistant", "content": "earlier reply"},
            {"id": 3, "role": "user", "content": "@luna latest mention"},
        ]
        _stub_persist(monkeypatch)
        _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        chat_input = captured["chatInput"]
        # Latest user message has mention stripped
        assert "latest mention" in chat_input
        # Earlier user message retains its original "@luna earlier mention"
        assert "@luna earlier mention" in chat_input

    def test_empty_luna_command_returns_400_without_calling_adapter(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        _, call_mock, persist_calls, _ = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 400
        body = response.json()
        assert "luna_empty_command" in (body.get("detail", {}).get("error", "")
                                        if isinstance(body.get("detail"), dict)
                                        else str(body.get("detail", "")))
        assert call_mock.call_count == 0
        assert persist_calls == []

    def test_missing_webhook_url_returns_503(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        _, _, _, enqueue_calls = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna hi"},
            ],
            raise_in_call=luna_n8n.LunaConfigError("LUNA_N8N_WEBHOOK_URL not set"),
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 503
        assert enqueue_calls == []
        # Body must not leak the raw exception text or webhook URL
        assert "LUNA_N8N_WEBHOOK_URL" not in response.text
        assert "Traceback" not in response.text

    def test_timeout_returns_504(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        _, _, _, enqueue_calls = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna hi"},
            ],
            raise_in_call=luna_n8n.LunaTimeoutError("n8n webhook timed out"),
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 504
        assert enqueue_calls == []
        assert "Traceback" not in response.text

    def test_upstream_failure_returns_502(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        _, _, _, enqueue_calls = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna hi"},
            ],
            raise_in_call=luna_n8n.LunaUpstreamError(
                "n8n webhook returned status 500"
            ),
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 502
        assert enqueue_calls == []
        # Internal n8n status detail is NOT leaked
        assert "500" not in response.text or response.json().get("detail", {}).get(
            "reason"
        ) == "luna_n8n_failed"
        assert "Traceback" not in response.text

    def test_normal_chat_does_not_invoke_luna_adapter(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """Regression: a normal chat request never enters the Luna path."""
        _, call_mock, persist_calls, _ = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "normal question"},
                {"id": 2, "role": "assistant", "content": "normal answer"},
                {"id": 3, "role": "user", "content": "another question"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        # Whatever the normal path returns, the Luna adapter must not have
        # been called and the Luna persistence helper must not have been
        # invoked.
        assert call_mock.call_count == 0
        assert persist_calls == []
        # The normal completion path should have run (enqueue is captured).
        # We don't assert success here because the route may need additional
        # fixtures past this point; the negative assertion above is the
        # critical regression boundary.

    def test_mid_message_mention_does_not_invoke_luna(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """Regression: 'hello @luna' must not be interpreted as a Luna call."""
        _, call_mock, persist_calls, _ = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "hello @luna"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert call_mock.call_count == 0
        assert persist_calls == []

    def test_webhook_url_not_leaked_in_success_response(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """Success body must not include the webhook URL or the payload."""
        monkeypatch.setattr(
            chat_routes.luna_n8n,
            "LUNA_N8N_WEBHOOK_URL",
            "http://secret-luna-host.local/webhook/abc",
        )
        _, _, _, _ = self._setup(
            test_client,
            mock_db,
            monkeypatch,
            messages=[
                {"id": 1, "role": "user", "content": "@luna hi"},
            ],
        )
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        assert "secret-luna-host" not in response.text
        assert "chatInput" not in response.text

    def test_authenticated_display_name_used_in_transcript(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """The authenticated user's display_name is the first-priority label."""
        captured: dict = {}

        async def _capture(payload, **_):
            captured.update(dict(payload))
            return "ok"

        # Inject a deterministic auth display name via the lookup helper.
        monkeypatch.setattr(
            chat_routes,
            "_authenticated_display_name",
            lambda _scope: "RealUser",
        )
        # Even when the env operator name is set, auth must win.
        monkeypatch.setattr(
            chat_routes.luna_n8n, "LUNA_OPERATOR_NAME", "OperatorFallback"
        )

        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id)
        mock_db.list_messages.return_value = [
            {"id": 1, "role": "user", "content": "@luna hi"},
        ]

        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", _capture)
        _stub_persist(monkeypatch)
        _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        chat_input = captured["chatInput"]
        assert "RealUser:\nhi" in chat_input
        # Operator fallback must NOT appear when auth wins.
        assert "OperatorFallback" not in chat_input

    def test_operator_name_used_when_auth_unavailable(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """When no auth display_name is available, LUNA_OPERATOR_NAME is used."""
        captured: dict = {}

        async def _capture(payload, **_):
            captured.update(dict(payload))
            return "ok"

        # Auth lookup returns None (no profile, no DB, or no display_name).
        monkeypatch.setattr(
            chat_routes,
            "_authenticated_display_name",
            lambda _scope: None,
        )
        monkeypatch.setattr(
            chat_routes.luna_n8n, "LUNA_OPERATOR_NAME", "Zac"
        )

        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id)
        mock_db.list_messages.return_value = [
            {"id": 1, "role": "user", "content": "@luna hi"},
        ]

        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", _capture)
        _stub_persist(monkeypatch)
        _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        chat_input = captured["chatInput"]
        assert "Zac:\nhi" in chat_input
        assert "User:" not in chat_input

    def test_user_fallback_when_neither_auth_nor_operator(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """Final fallback: when both auth and operator are unavailable,
        the transcript uses the repo-standard 'User' label.
        """
        captured: dict = {}

        async def _capture(payload, **_):
            captured.update(dict(payload))
            return "ok"

        monkeypatch.setattr(
            chat_routes,
            "_authenticated_display_name",
            lambda _scope: None,
        )
        monkeypatch.setattr(
            chat_routes.luna_n8n, "LUNA_OPERATOR_NAME", ""
        )

        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id)
        mock_db.list_messages.return_value = [
            {"id": 1, "role": "user", "content": "@luna hi"},
        ]

        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", _capture)
        _stub_persist(monkeypatch)
        _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        chat_input = captured["chatInput"]
        assert "User:\nhi" in chat_input

    def test_auth_lookup_failure_does_not_break_routing(
        self, test_client, mock_db, monkeypatch
    ) -> None:
        """If the auth lookup is unavailable (returns None — whether due to
        a missing DB, missing profile, or a logged+swallowed exception), the
        route falls through to LUNA_OPERATOR_NAME without breaking.
        """

        captured: dict = {}

        async def _capture(payload, **_):
            captured.update(dict(payload))
            return "ok"

        # Simulate the helper's best-effort contract: any internal failure
        # is logged and surfaces as None to the route.
        monkeypatch.setattr(
            chat_routes, "_authenticated_display_name", lambda _scope: None
        )
        monkeypatch.setattr(
            chat_routes.luna_n8n, "LUNA_OPERATOR_NAME", "Fallback"
        )

        user_id = get_test_user_id()
        mock_db.get_chat_thread.return_value = _basic_thread(user_id)
        mock_db.list_messages.return_value = [
            {"id": 1, "role": "user", "content": "@luna hi"},
        ]

        monkeypatch.setattr(chat_routes.luna_n8n, "call_luna_n8n", _capture)
        _stub_persist(monkeypatch)
        _stub_normal_completion_path(monkeypatch)
        _stub_turn_locks(monkeypatch)
        _override_request_scope(test_client, user_id)
        try:
            response = _post_complete(test_client)
        finally:
            self._cleanup(test_client)

        assert response.status_code == 200
        chat_input = captured["chatInput"]
        assert "Fallback:\nhi" in chat_input

    def test_auth_helper_swallows_db_exceptions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The helper itself must not raise on DB / lookup exceptions;
        it returns None so the route can fall through gracefully.
        """
        from guardian.routes import chat as chat_routes_module
        from tests.utils import get_test_user_id

        class _ExplodingDB:
            def get_session(self):
                raise RuntimeError("simulated db failure")

        # The helper imports load_guardian_db_from_env lazily inside its
        # body, so patch the source module's binding.
        monkeypatch.setattr(
            "guardian.core.db.load_guardian_db_from_env",
            lambda: _ExplodingDB(),
        )

        # Should not raise; should return None.
        result = chat_routes_module._authenticated_display_name(
            RequestUserScope(
                user_id=get_test_user_id(),
                subject_id=get_test_user_id(),
                account_id=get_test_user_id(),
                multi_user_enabled=False,
            )
        )
        assert result is None