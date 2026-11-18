from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from guardian import slash_commands
from guardian.core import auth_dependencies, session_store
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.routes import chat

MANIFEST = "/api/chat/slash-commands/manifest"
SEARCH = "/api/chat/slash-commands/search"
CHAT_INTENTS = {
    "thread",
    "doc",
    "project",
    "workspace",
    "profile",
    "flow",
    "secure",
    "connect",
    "obsidian",
    "codex_entry",
    "help",
}
COMPOSER_CONTROLS = {"project", "provider", "model", "mode", "retrieval"}


@pytest.fixture
def discovery_client():
    app = FastAPI()
    app.include_router(chat.api_chat_router)
    with TestClient(app, headers={"X-API-Key": "test-api-key"}) as client:
        yield client


def test_manifest_inventory_and_stable_wire_contract(discovery_client):
    response = discovery_client.get(MANIFEST)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == discovery_client.get(MANIFEST).content

    body = response.json()
    assert set(body) == {"schemaVersion", "manifestRevision", "commands"}
    assert body["schemaVersion"] == 1
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", body["manifestRevision"])

    commands = body["commands"]
    ids = CHAT_INTENTS | COMPOSER_CONTROLS
    assert {command["id"] for command in commands} == ids
    assert [command["token"] for command in commands] == sorted(
        f"/{command_id}" for command_id in ids
    )
    for command in commands:
        assert set(command) == {
            "id",
            "token",
            "label",
            "description",
            "aliases",
            "keywords",
            "scaffold",
            "interactionModes",
            "effects",
            "availability",
            "availabilityReason",
        }
        assert command["scaffold"] == command["token"]
        assert command["label"] and command["description"] and command["keywords"]
        modes = []
        if command["id"] in CHAT_INTENTS:
            modes.append("chat_intent")
            assert set(command["effects"]) == {"intentKind", "retrievalHint"}
        else:
            assert command["effects"] is None
        if command["id"] in COMPOSER_CONTROLS:
            modes.append("composer_control")
        assert command["interactionModes"] == modes
        assert command["availability"] == "unknown"
        assert command["availabilityReason"] == "eligibility_not_evaluated"

    project = next(command for command in commands if command["id"] == "project")
    assert project["aliases"] == ["repo"]
    assert project["effects"] == {"intentKind": "workspace", "retrievalHint": "project"}


def test_revision_changes_with_manifest_metadata():
    manifest = slash_commands.SLASH_COMMAND_MANIFEST
    first, *rest = manifest.commands
    same = first.model_copy()
    changed = first.model_copy(update={"description": "Changed description."})

    assert slash_commands._manifest_revision((same, *rest)) == manifest.manifestRevision
    assert (
        slash_commands._manifest_revision((changed, *rest)) != manifest.manifestRevision
    )


def test_index_rejects_duplicate_ids_tokens_and_ambiguous_aliases():
    project = slash_commands.resolve_slash_command("/project")
    workspace = slash_commands.resolve_slash_command("/workspace")
    assert project is not None and workspace is not None
    assert slash_commands.resolve_slash_command("/REPO") is project
    assert slash_commands.resolve_slash_command(
        "/obs"
    ) is slash_commands.resolve_slash_command("/obsidian")

    with pytest.raises(ValueError, match="duplicate slash command ID"):
        slash_commands._build_token_index((workspace, workspace))
    with pytest.raises(ValueError, match="duplicate canonical slash command token"):
        slash_commands._build_token_index(
            (project, workspace.model_copy(update={"token": "/PROJECT"}))
        )
    for aliases in (("Workspace",), ("ROOT",), ("repo", "/REPO")):
        with pytest.raises(ValueError, match="collides with a token or alias"):
            slash_commands._build_token_index(
                (project.model_copy(update={"aliases": aliases}), workspace)
            )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (" /ObS  ", ["obsidian"]),
        ("/ob", ["obsidian"]),
        ("/workspace", ["workspace"]),
        ("/project", ["project"]),
        ("rep", ["project", "thread"]),
        ("Pro", ["profile", "project", "provider", "flow"]),
        ("note", ["obsidian", "codex_entry", "doc"]),
        ("inference", ["mode", "model", "provider"]),
        ("/?", ["help"]),
        ("history.search", []),
        ("not-a-command", []),
        ("/", []),
    ],
)
def test_search_order_and_projection(discovery_client, query, expected):
    manifest = discovery_client.get(MANIFEST).json()
    by_id = {command["id"]: command for command in manifest["commands"]}

    params = {"q": query}
    response = discovery_client.get(SEARCH, params=params)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == discovery_client.get(SEARCH, params=params).content
    assert response.json() == {
        "schemaVersion": manifest["schemaVersion"],
        "manifestRevision": manifest["manifestRevision"],
        "commands": [by_id[command_id] for command_id in expected],
    }


def test_search_validates_bounds(discovery_client):
    response = discovery_client.get(SEARCH, params={"q": "pro", "limit": 2})
    assert [command["id"] for command in response.json()["commands"]] == [
        "profile",
        "project",
    ]
    for params in (
        {"q": "pro", "limit": 0},
        {"q": "pro", "limit": 26},
        {"q": "x" * 129},
        {},
    ):
        assert discovery_client.get(SEARCH, params=params).status_code == 422


@pytest.mark.parametrize("path", [MANIFEST, f"{SEARCH}?q=obs"])
def test_discovery_requires_local_authentication_without_account_hints(
    discovery_client, path
):
    discovery_client.headers.clear()
    response = discovery_client.get(
        path,
        params={"account_id": "account-a", "q": "obs"},
        headers={"X-User-Id": "account-a"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("path", [MANIFEST, f"{SEARCH}?q=obs"])
def test_remote_discovery_uses_existing_session_gate(
    discovery_client, monkeypatch, path
):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "slash-command-test-secret")
    sessions: dict[str, str] = {}
    store = SimpleNamespace(verify=sessions.get)
    for module in (auth_dependencies, session_store):
        monkeypatch.setattr(module, "get_session_store", lambda: store)

    def session(subject, purpose):
        token, _ = issue_session_token(subject=subject, ttl_seconds=60, purpose=purpose)
        sessions[token] = subject
        return token

    assert discovery_client.get(path).status_code == 401  # Local key alone.
    discovery_client.headers.clear()
    operator = session("operator", OPERATOR_SESSION_PURPOSE)
    assert (
        discovery_client.get(
            path, headers={"Authorization": f"Bearer {operator}"}
        ).status_code
        == 401
    )

    account_a = session("account-a", ACCOUNT_SESSION_PURPOSE)
    account_b = session("account-b", ACCOUNT_SESSION_PURPOSE)
    headers_a = {"Authorization": f"Bearer {account_a}"}
    response_a = discovery_client.get(path, headers=headers_a)
    response_a_with_hints = discovery_client.get(
        path,
        params={
            "accountId": "account-b",
            "user_id": "account-b",
            **({"q": "obs"} if path.startswith(SEARCH) else {}),
        },
        headers={**headers_a, "X-User-Id": "account-b"},
    )
    response_b = discovery_client.get(
        path, headers={"Cookie": f"gc_session={account_b}"}
    )
    assert (
        response_a.status_code
        == response_a_with_hints.status_code
        == response_b.status_code
        == 200
    )
    # With eligibility unevaluated, both signed accounts get the same catalog.
    assert response_a.content == response_a_with_hints.content == response_b.content
    assert response_b.headers["cache-control"] == "private, no-store"
    assert (
        b"account-a" not in response_a.content
        and b"account-b" not in response_b.content
    )
    assert (
        discovery_client.get(
            path, headers={**headers_a, "Cookie": f"gc_session={operator}"}
        ).status_code
        == 400
    )


def test_discovery_does_not_use_chat_state_or_execution(discovery_client, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("discovery must be read-only"))
    db = Mock()
    monkeypatch.setattr(chat, "chatlog_db", db)
    for name in (
        "enqueue",
        "enqueue_chat_completion",
        "resolve_context_request_plans",
        "_build_doc_context_override",
        "get_event_writer",
    ):
        monkeypatch.setattr(chat, name, forbidden)

    assert discovery_client.get(MANIFEST).status_code == 200
    assert discovery_client.get(SEARCH, params={"q": "/obsidian"}).status_code == 200
    assert (
        discovery_client.post(MANIFEST, json={"commandId": "obsidian"}).status_code
        == 405
    )
    assert (
        discovery_client.post(SEARCH, json={"commandId": "obsidian"}).status_code == 405
    )
    forbidden.assert_not_called()
    assert db.mock_calls == []
    # The raw Command Bus manifest derives its routes from OpenAPI.
    assert {MANIFEST, SEARCH}.isdisjoint(discovery_client.app.openapi()["paths"])


def test_slash_intent_accepts_only_existing_ids_and_preserves_request_metadata():
    for command_id in CHAT_INTENTS:
        assert (
            chat.SlashIntentRequest(
                commandId=command_id, intentKind="help", rawToken=f"/{command_id}"
            ).commandId
            == command_id
        )

    for command_id in (COMPOSER_CONTROLS - CHAT_INTENTS) | {
        "/project",
        "PROJECT",
        "repo",
        "obs",
        "history.search",
    }:
        with pytest.raises(ValidationError, match="commandId"):
            chat.SlashIntentRequest(
                commandId=command_id, intentKind="help", rawToken="/help"
            )
    assert (
        set(
            chat.SlashIntentRequest.model_json_schema()["properties"]["commandId"][
                "enum"
            ]
        )
        == CHAT_INTENTS
    )

    payload = {
        "commandId": "project",
        "rawInput": "/workspace legacy client text",
        "intentKind": "workspace",
        "retrievalHint": "conversation",
    }
    request = chat.ChatCompletionRequest.model_validate({"slashIntent": payload})
    assert request.slash_intent.model_dump(exclude_none=True) == payload
    assert chat._retrieval_override_from_slash_intent(request.slash_intent) == {
        "mode": "conversation",
        "reason": "slash_conversation_hint",
    }
