"""Exercise the accepted-task knowledge dispatch path, not just schema helpers."""

from __future__ import annotations

import json

import pytest

from guardian.connections import chat_pilot
from guardian.core import chat_completion_service as completion
from tests.core.test_chat_completion_service_tool_loop import _build_task, _seed_service


def _run(
    monkeypatch,
    *,
    command_id,
    arguments,
    advertised=True,
    current=True,
    api_key="test-local-transport",
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-knowledge-pilot")
    task.request_id = "request-knowledge-pilot"
    provider = chat_pilot.COMMANDS[command_id][0]
    task.tools = [
        {
            "command_id": command_id,
            "description": "Read scoped external evidence",
            "input_schema": {
                "type": "object",
                "properties": chat_pilot.COMMANDS[command_id][2],
                "required": chat_pilot.COMMANDS[command_id][3],
                "additionalProperties": False,
            },
        }
    ]
    provider_calls = []
    invocations = []

    def prepare(prepared_task, **kwargs):
        evidence = completion._build_tool_exposure_evidence(
            automatic=True, tools=prepared_task.tools
        )
        if advertised:
            evidence["_knowledge_pilot_providers"] = frozenset({provider})
        return evidence

    monkeypatch.setattr(completion, "_prepare_chat_tool_exposure", prepare)
    monkeypatch.setattr(
        completion,
        "_knowledge_pilot_providers",
        lambda task: frozenset({provider}) if current else frozenset(),
    )
    monkeypatch.setattr(completion, "_repository_search_local_api_key", lambda: api_key)

    def invoke(**kwargs):
        invocations.append(kwargs)
        if not advertised or not current or not api_key:
            pytest.fail("authority failure must prevent invocation")
        return {
            "run_id": "run-knowledge",
            "status": "completed",
            "inline_result": {
                "status_code": 200,
                "body": {
                    "results": [
                        {
                            "title": "Release plan",
                            "external_url": "https://github.com/owner/repo/issues/12",
                            "source_system": provider,
                            "preview": "Bounded source evidence",
                        }
                    ]
                },
            },
        }

    monkeypatch.setattr(completion, "execute_invoke", invoke)

    def chat(messages, **kwargs):
        provider_calls.append({"messages": messages, "tools": kwargs.get("tools")})
        if len(provider_calls) == 1:
            return json.dumps(
                {
                    "type": "tool_decision",
                    "command_id": command_id,
                    "arguments": arguments,
                }
            )
        return "Answer from the scoped source."

    monkeypatch.setattr(completion, "chat_with_ai", chat)
    result = completion.run_chat_completion_task(task, persist_assistant_message=False)
    return task, invocations, provider_calls, result


@pytest.mark.parametrize(
    "command_id,arguments",
    [
        ("op::notion_content_search", {"query": "release plan"}),
        (
            "op::github_content_search",
            {"repository": "owner/repo", "query": "release plan"},
        ),
    ],
)
def test_flat_query_reaches_scoped_command_bus(monkeypatch, command_id, arguments):
    task, calls, provider_calls, result = _run(
        monkeypatch, command_id=command_id, arguments=arguments
    )
    assert len(calls) == 1
    call = calls[0]
    assert call["payload"].arguments.model_dump() == {
        "path_params": {},
        "query": arguments,
        "headers": {},
        "body": None,
    }
    assert call["payload"].actor.delegated_by == task.user_id
    assert call["auth_subject"] == task.user_id
    assert call["inbound_headers"] == {"X-API-Key": "test-local-transport"}
    assert call["allow_write_execution"] is False
    assert len(provider_calls) == 2
    assert "https://github.com/owner/repo/issues/12" in repr(
        provider_calls[1]["messages"]
    )
    assert "test-local-transport" not in repr(provider_calls)
    assert result["assistant_text"] == "Answer from the scoped source."


@pytest.mark.parametrize(
    "command_id,arguments,path_params",
    [
        (
            "op::notion_content_read",
            {"object_id": "22222222-2222-2222-2222-222222222222"},
            {"object_id": "22222222-2222-2222-2222-222222222222"},
        ),
        (
            "op::github_content_read",
            {"repository": "owner/repo", "number": 12},
            {"owner": "owner", "repo": "repo", "number": 12},
        ),
    ],
)
def test_flat_read_reaches_scoped_path(monkeypatch, command_id, arguments, path_params):
    _, calls, _, _ = _run(monkeypatch, command_id=command_id, arguments=arguments)
    assert calls[0]["payload"].arguments.path_params == path_params
    assert calls[0]["payload"].arguments.query == {}


@pytest.mark.parametrize(
    "authority", [{"advertised": False}, {"current": False}, {"api_key": None}]
)
@pytest.mark.parametrize(
    "command_id,arguments",
    [
        ("op::notion_content_search", {"query": "release plan"}),
        (
            "op::github_content_search",
            {"repository": "owner/repo", "query": "release plan"},
        ),
    ],
)
def test_missing_or_revoked_authority_blocks_before_invoke(
    monkeypatch, authority, command_id, arguments
):
    with pytest.raises(completion.ToolLoopExecutionError):
        _run(monkeypatch, command_id=command_id, arguments=arguments, **authority)


@pytest.mark.parametrize(
    "extra",
    [
        {"user_id": "someone-else"},
        {"headers": {"X-User-Id": "someone-else"}},
        {"body": {"account_id": "someone-else"}},
    ],
)
def test_model_cannot_override_account_or_transport(monkeypatch, extra):
    with pytest.raises(completion.ToolLoopExecutionError):
        _run(
            monkeypatch,
            command_id="op::notion_content_search",
            arguments={"query": "release plan", **extra},
        )
