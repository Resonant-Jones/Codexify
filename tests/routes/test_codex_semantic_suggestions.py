"""Tests for advisory Codex Entry semantic suggestion routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.codex import service as codex_service
from guardian.protocol_tokens import CodexEntryCreatedFrom
from guardian.routes import codex as codex_routes

API_HEADERS = {"X-API-Key": "test"}


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(codex_routes.router)
    return app


def test_explicit_capture_language_returns_suggestion(tmp_path, monkeypatch):
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/suggest",
        json={
            "threadId": 44,
            "recentMessages": [
                {
                    "id": 100,
                    "thread_id": 44,
                    "role": "assistant",
                    "content": "Use append-only logs for receipts and rebuild views from events.",
                },
                {
                    "id": 101,
                    "thread_id": 44,
                    "role": "user",
                    "content": "Save this for later.",
                },
            ],
        },
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["suggested"] is True
    assert payload["confidence"] >= 0.8
    assert payload["reason"] == "capture_language"
    assert payload["label"] == "Codex Entry"
    assert payload["sourceMessageIds"] == ["100"]
    assert payload["threadId"] == "44"
    assert (
        payload["createdFrom"]
        == CodexEntryCreatedFrom.SEMANTIC_SUGGESTION.value
    )
    assert payload["retrievalEnabled"] is False
    assert payload["suppressionKey"]
    assert list(codex_root.glob("**/*.cdx")) == []


def test_ordinary_conversation_returns_no_suggestion():
    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/suggest",
        json={
            "threadId": 45,
            "recentMessages": [
                {
                    "id": 110,
                    "thread_id": 45,
                    "role": "user",
                    "content": "What is the next task?",
                },
                {
                    "id": 111,
                    "thread_id": 45,
                    "role": "assistant",
                    "content": "The next task is to run focused tests.",
                },
            ],
        },
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"suggested": False}


def test_slash_command_text_alone_is_not_suggestion_source():
    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/suggest",
        json={
            "threadId": 46,
            "recentMessages": [
                {
                    "id": 120,
                    "thread_id": 46,
                    "role": "user",
                    "content": "/codex_entry",
                },
            ],
        },
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"suggested": False}


def test_inline_pattern_language_can_use_its_own_source_message():
    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/suggest",
        json={
            "threadId": 47,
            "recentMessages": [
                {
                    "id": 130,
                    "thread_id": 47,
                    "role": "user",
                    "content": (
                        "This is a pattern: keep semantic suggestions advisory "
                        "and require explicit confirmation before persistence."
                    ),
                },
            ],
        },
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["suggested"] is True
    assert payload["sourceMessageIds"] == ["130"]
    assert payload["sourceSummary"] == "1 messages (1 user, 0 assistant)"


def test_suppression_keys_are_stable_and_honored():
    client = TestClient(_make_app())
    request = {
        "threadId": 48,
        "recentMessages": [
            {
                "id": 140,
                "thread_id": 48,
                "role": "assistant",
                "content": "Conflict policy should be explicit and human-reviewable.",
            },
            {
                "id": 141,
                "thread_id": 48,
                "role": "user",
                "content": "Capture this.",
            },
        ],
    }

    first = client.post(
        "/api/codex/entries/suggest",
        json=request,
        headers=API_HEADERS,
    )
    second = client.post(
        "/api/codex/entries/suggest",
        json=request,
        headers=API_HEADERS,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["suppressionKey"] == second_payload["suppressionKey"]

    suppressed = client.post(
        "/api/codex/entries/suggest",
        json={
            **request,
            "seenSuppressionKeys": [first_payload["suppressionKey"]],
        },
        headers=API_HEADERS,
    )

    assert suppressed.status_code == 200
    assert suppressed.json() == {"suggested": False}


def test_no_usable_prior_context_returns_no_suggestion():
    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/suggest",
        json={
            "threadId": 49,
            "recentMessages": [
                {
                    "id": 150,
                    "thread_id": 49,
                    "role": "user",
                    "content": "Save this.",
                },
            ],
        },
        headers=API_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {"suggested": False}
