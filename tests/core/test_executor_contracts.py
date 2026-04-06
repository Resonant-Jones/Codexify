from __future__ import annotations

from guardian.core.executors.base import (
    CanonicalEscalation,
    CanonicalTaskSummary,
    CodexifyExecutorContextBundle,
    CodexifyExecutorRequest,
    ExecutorEscalationEvent,
    ExecutorTerminalResult,
)
from guardian.core.executors.registry import ExecutorId
from guardian.protocol_tokens import ExecutorEscalationKind, ExecutorEventType


def test_canonical_request_envelope_construction() -> None:
    context_bundle = CodexifyExecutorContextBundle(
        workspace_path="/workspace/codexify",
        thread_context={"thread_subject": "executor contracts"},
        routing={"provider": "openai", "model": "gpt-5"},
    )
    request = CodexifyExecutorRequest(
        request_id="req-123",
        thread_id=42,
        source_message_id=17,
        project_id=9,
        executor_id=ExecutorId.CODEX,
        title="Normalize executor registry",
        canonical_task_prompt="Build the canonical executor contract layer.",
        context_bundle=context_bundle,
        permissions={"workspace": "read"},
        tags=["delegation", "core"],
        delegation_id="delegation-123",
        task_id="task-123",
        repo_path="/workspace/codexify",
        task_prompt="Build the canonical executor contract layer.",
        context={"thread_subject": "executor contracts"},
    )

    payload = request.to_dict()

    assert request.request_id == "req-123"
    assert request.executor_id == ExecutorId.CODEX
    assert request.executor == "codex"
    assert request.canonical_task_prompt == (
        "Build the canonical executor contract layer."
    )
    assert request.context_bundle.routing == {
        "provider": "openai",
        "model": "gpt-5",
    }
    assert request.executor_id != request.context_bundle.routing["provider"]
    assert payload["executorId"] == "codex"
    assert payload["contextBundle"]["routing"]["provider"] == "openai"
    assert payload["delegationId"] == "delegation-123"
    assert payload["taskId"] == "task-123"


def test_escalation_payload_preserves_provenance() -> None:
    escalation = CanonicalEscalation(
        kind=ExecutorEscalationKind.NEEDS_PERMISSION,
        severity="hard",
        reason_code="permission_required",
        reason="Need approval before writing to disk.",
        preserved_worktree=True,
        payload={"path": "/workspace/codexify"},
        provenance={
            "request_id": "req-456",
            "executor_id": "claude_code",
            "thread_id": 42,
            "source_message_id": 17,
        },
    )
    event = ExecutorEscalationEvent(
        request_id="req-456",
        thread_id=42,
        source_message_id=17,
        executor_id=ExecutorId.CLAUDE_CODE,
        title="Need approval",
        tags=["delegation"],
        escalation=escalation,
    )

    payload = event.to_dict()

    assert event.event_type == ExecutorEventType.ESCALATION.value
    assert event.escalation.provenance["request_id"] == "req-456"
    assert event.escalation.provenance["executor_id"] == "claude_code"
    assert payload["escalation"]["reason_code"] == "permission_required"
    assert payload["escalation"]["provenance"]["thread_id"] == 42


def test_terminal_result_preserves_summary_shape_and_tags() -> None:
    summary = CanonicalTaskSummary(
        request_id="req-789",
        delegation_id="delegation-789",
        task_id="task-789",
        thread_id=42,
        source_message_id=17,
        project_id=9,
        executor_id=ExecutorId.OPENCODE,
        title="Normalize executor result",
        status="completed",
        summary="Executor contracts normalized.",
        files_changed=["guardian/core/executors/contracts.py"],
        commands_run=["pytest -v tests/core/test_executor_contracts.py"],
        key_changes=["Added canonical request/result shapes"],
        unresolved_questions=[],
        tags=["core", "delegation"],
        result={"files_changed": ["guardian/core/executors/contracts.py"]},
        metadata={"executor": "opencode"},
        lineage={"source": "thread"},
    )
    result = ExecutorTerminalResult(
        request_id="req-789",
        delegation_id="delegation-789",
        task_id="task-789",
        thread_id=42,
        source_message_id=17,
        project_id=9,
        executor_id=ExecutorId.OPENCODE,
        title="Normalize executor result",
        status="completed",
        summary="Executor contracts normalized.",
        task_summary=summary,
        tags=["core", "delegation"],
        result={"summary": "Executor contracts normalized."},
        metadata={"executor": "opencode"},
    )

    payload = result.to_dict()

    assert result.summary == "Executor contracts normalized."
    assert result.tags == ["core", "delegation"]
    assert result.task_summary is not None
    assert result.task_summary.tags == ["core", "delegation"]
    assert result.task_summary.lineage["request_id"] == "req-789"
    assert result.task_summary.lineage["executor_id"] == "opencode"
    assert payload["taskSummary"]["tags"] == ["core", "delegation"]
    assert payload["taskSummary"]["lineage"]["source"] == "thread"
