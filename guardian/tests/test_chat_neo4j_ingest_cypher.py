from __future__ import annotations

import logging
import re
from types import SimpleNamespace

from guardian.routes import chat as chat_routes


class _StubChatlogDB:
    def __init__(self, *, message_id: int = 9001) -> None:
        self._message_id = message_id
        self._thread: dict[str, object] = {
            "id": 0,
            "title": "",
            "project_id": None,
        }

    def ensure_chat_thread(self, **_kwargs) -> None:
        return None

    def create_message(self, thread_id: int, role: str, content: str) -> int:
        _ = (thread_id, role, content)
        return self._message_id

    def write_audit_log(self, *_args, **_kwargs) -> None:
        return None

    def get_chat_thread(self, thread_id: int) -> dict[str, object]:
        self._thread["id"] = thread_id
        return self._thread

    def count_messages(self, _thread_id: int) -> int:
        return 1

    def update_thread(self, _thread_id: int, **_kwargs) -> None:
        return None


class _CapturedNeo4jDB:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def cypher_query(self, query: str, params: dict[str, object]):
        self.calls.append((query, params))
        return [[("message-element-id",)]], None


def _run_live_ingest(
    monkeypatch,
    *,
    graph_logging_enabled: bool,
    debug_flag_enabled: bool,
    content: str = "super secret live ingest body",
):
    fake_neo4j = _CapturedNeo4jDB()

    monkeypatch.setattr(chat_routes, "chatlog_db", _StubChatlogDB())
    monkeypatch.setattr(
        chat_routes.event_bus, "emit_event", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        chat_routes, "_emit_thread_update_event", lambda **_kwargs: None
    )
    monkeypatch.setattr(chat_routes, "_embed_message", lambda *_a, **_k: None)
    monkeypatch.setattr(
        chat_routes, "acquire_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_routes, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(chat_routes, "connect_neo4j", lambda: None)
    monkeypatch.setattr(chat_routes, "neo4j_db", fake_neo4j)
    monkeypatch.setattr(chat_routes, "NEO4J_SYNC_AVAILABLE", True)
    monkeypatch.setattr(
        chat_routes,
        "llm_settings",
        SimpleNamespace(GUARDIAN_ENABLE_GRAPH_LOGGING=graph_logging_enabled),
    )
    if debug_flag_enabled:
        monkeypatch.setenv("GUARDIAN_ENABLE_GRAPH_INGEST_QUERY_DEBUG", "1")
    else:
        monkeypatch.delenv(
            "GUARDIAN_ENABLE_GRAPH_INGEST_QUERY_DEBUG", raising=False
        )

    result = chat_routes._persist_message_to_thread(
        thread_id=321,
        role="user",
        content=content,
        owner="user-42",
    )
    return fake_neo4j, result


def _normalize_query(query: str) -> str:
    return " ".join(query.split())


def _assert_query_shape_is_safe(query: str) -> None:
    normalized = _normalize_query(query)
    assert normalized.count("MERGE ") >= 5
    assert " WITH " in normalized
    assert re.search(r"MERGE\s*\([^)]*\)\s+ON CREATE SET", normalized)
    assert re.search(
        r"WITH\s+.+\s+MERGE\s*\([^)]*\)-\[[^]]*\]->\([^)]*\)", normalized
    )
    assert (
        re.search(
            r"MATCH\s*\([^)]*\)\s*,\s*\([^)]*\)",
            query,
            re.IGNORECASE | re.DOTALL,
        )
        is None
    )
    assert (
        re.search(
            r".MATCH.(?:(?!.WITH.).)*.MATCH.", query, re.IGNORECASE | re.DOTALL
        )
        is None
    )


def _ingest_log_messages(caplog) -> list[str]:
    return [
        record.message
        for record in caplog.records
        if record.name == chat_routes.logger.name
        and record.message.startswith("[chat.ingest.neo4j]")
    ]


def test_live_message_ingest_uses_approved_safe_query_shape(monkeypatch):
    fake_neo4j, result = _run_live_ingest(
        monkeypatch,
        graph_logging_enabled=True,
        debug_flag_enabled=False,
    )

    assert result["id"] == 9001
    assert len(fake_neo4j.calls) == 1

    query, params = fake_neo4j.calls[0]
    _assert_query_shape_is_safe(query)
    assert params["message_id"] == "9001"
    assert params["thread_id"] == "321"
    assert params["user_id"] == "user-42"


def test_live_message_ingest_logs_query_and_param_keys_only(
    monkeypatch, caplog
):
    secret_content = "super secret live ingest body"

    caplog.set_level(logging.DEBUG, logger=chat_routes.logger.name)
    with caplog.at_level(logging.DEBUG, logger=chat_routes.logger.name):
        fake_neo4j, _result = _run_live_ingest(
            monkeypatch,
            graph_logging_enabled=True,
            debug_flag_enabled=True,
            content=secret_content,
        )

    assert len(fake_neo4j.calls) == 1

    logs = _ingest_log_messages(caplog)
    assert len(logs) == 1

    query, params = fake_neo4j.calls[0]
    log_message = logs[0]

    assert query.strip() in log_message
    assert "param_keys=" in log_message
    for key in sorted(params.keys()):
        assert key in log_message

    assert secret_content not in caplog.text
    assert "user-42" not in caplog.text
    assert "321" not in caplog.text
    assert "9001" not in caplog.text


def test_live_message_ingest_query_logging_requires_both_flags(
    monkeypatch, caplog
):
    cases = [
        (True, False, 1, False),
        (False, True, 0, False),
        (True, True, 1, True),
    ]

    for (
        graph_logging_enabled,
        debug_flag_enabled,
        query_calls,
        expect_log,
    ) in cases:
        caplog.clear()
        caplog.set_level(logging.DEBUG, logger=chat_routes.logger.name)
        with caplog.at_level(logging.DEBUG, logger=chat_routes.logger.name):
            fake_neo4j, _result = _run_live_ingest(
                monkeypatch,
                graph_logging_enabled=graph_logging_enabled,
                debug_flag_enabled=debug_flag_enabled,
            )

        assert len(fake_neo4j.calls) == query_calls
        logs = _ingest_log_messages(caplog)
        assert (len(logs) == 1) is expect_log
