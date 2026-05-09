from __future__ import annotations

from dataclasses import MISSING, fields
from typing import get_args

import pytest

from guardian.agents.coding_agent_contracts import (
    CodingAgentAdapterKind,
    CodingAgentPermissionPolicy,
    CodingAgentResult,
    CodingAgentTaskEnvelope,
    CodingAgentTaskStatus,
)


def test_valid_coding_agent_task_envelope_can_be_constructed() -> None:
    policy = CodingAgentPermissionPolicy(
        allow_shell=True,
        allow_network=False,
        allow_write=True,
        allowed_paths=("/workspace/repo", "/workspace/repo/src"),
        max_runtime_seconds=900,
    )

    envelope = CodingAgentTaskEnvelope(
        coding_task_id="coding-task-123",
        thread_id="thread-123",
        source_message_id="message-456",
        attempt_id="attempt-789",
        user_id="local",
        project_id=None,
        adapter_kind="pi_sdk",
        instructions="Update the failing parser and keep the change narrow.",
        repo_root="/workspace/repo",
        context_summary="Guardian-supplied summary of the active thread and files.",
        validation_command="pytest -q",
        max_validation_attempts=4,
        permission_policy=policy,
    )

    assert envelope.coding_task_id == "coding-task-123"
    assert envelope.permission_policy == policy
    assert envelope.adapter_kind == "pi_sdk"
    assert envelope.validation_command == "pytest -q"
    assert envelope.max_validation_attempts == 4


def test_coding_agent_task_envelope_can_include_validation_metadata() -> None:
    policy = CodingAgentPermissionPolicy(
        allow_shell=True,
        allow_network=False,
        allow_write=False,
        allowed_paths=("/workspace/repo",),
        max_runtime_seconds=300,
    )

    envelope = CodingAgentTaskEnvelope(
        coding_task_id="coding-task-321",
        thread_id="thread-321",
        source_message_id="message-321",
        attempt_id="attempt-321",
        user_id="local",
        project_id=7,
        adapter_kind="mock",
        instructions="Run the parser validation loop.",
        repo_root="/workspace/repo",
        context_summary="Validation metadata should be optional.",
        permission_policy=policy,
        validation_command="pytest -q",
        max_validation_attempts=4,
    )

    assert envelope.validation_command == "pytest -q"
    assert envelope.max_validation_attempts == 4


def test_valid_coding_agent_result_can_be_constructed() -> None:
    result = CodingAgentResult(
        coding_task_id="coding-task-123",
        attempt_id="attempt-789",
        status="completed",
        summary="Patched the parser and added a regression test.",
        files_changed=("guardian/routes/chat.py", "tests/test_parser.py"),
        artifacts=("diff-summary.txt",),
        logs_summary="One adapter run completed successfully.",
        error_code=None,
        error_message=None,
        adapter_session_ref="pi-session-abc",
        validation_results={"status": "passed"},
    )

    assert result.status == "completed"
    assert result.files_changed == (
        "guardian/routes/chat.py",
        "tests/test_parser.py",
    )
    assert result.validation_results == {"status": "passed"}


def test_permission_policy_keeps_allowed_paths_as_immutable_tuple() -> None:
    policy = CodingAgentPermissionPolicy(
        allow_shell=False,
        allow_network=False,
        allow_write=False,
        allowed_paths=("/workspace/repo",),
        max_runtime_seconds=300,
    )

    assert isinstance(policy.allowed_paths, tuple)
    assert policy.allowed_paths == ("/workspace/repo",)
    assert not hasattr(policy.allowed_paths, "append")


def test_adapter_kind_and_status_literals_include_expected_values() -> None:
    assert "pi_sdk" in get_args(CodingAgentAdapterKind)
    assert "completed" in get_args(CodingAgentTaskStatus)
    assert "failed_retryable" in get_args(CodingAgentTaskStatus)


def test_source_message_and_attempt_ids_are_separate_required_fields() -> None:
    envelope_fields = {
        field.name: field for field in fields(CodingAgentTaskEnvelope)
    }
    assert "source_message_id" in envelope_fields
    assert "attempt_id" in envelope_fields
    assert envelope_fields["source_message_id"].default is MISSING
    assert envelope_fields["attempt_id"].default is MISSING
    assert envelope_fields["source_message_id"].default_factory is MISSING
    assert envelope_fields["attempt_id"].default_factory is MISSING

    with pytest.raises(TypeError):
        CodingAgentTaskEnvelope(
            coding_task_id="coding-task-123",
            thread_id="thread-123",
            attempt_id="attempt-789",
            user_id="local",
            project_id=None,
            adapter_kind="mock",
            instructions="Do the thing.",
            repo_root=None,
            context_summary=None,
            permission_policy=CodingAgentPermissionPolicy(
                allow_shell=False,
                allow_network=False,
                allow_write=False,
                allowed_paths=(),
                max_runtime_seconds=60,
            ),
        )

    with pytest.raises(TypeError):
        CodingAgentTaskEnvelope(
            coding_task_id="coding-task-123",
            thread_id="thread-123",
            source_message_id="message-456",
            user_id="local",
            project_id=None,
            adapter_kind="mock",
            instructions="Do the thing.",
            repo_root=None,
            context_summary=None,
            permission_policy=CodingAgentPermissionPolicy(
                allow_shell=False,
                allow_network=False,
                allow_write=False,
                allowed_paths=(),
                max_runtime_seconds=60,
            ),
        )
