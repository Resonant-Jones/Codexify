from __future__ import annotations

from dataclasses import MISSING, fields
from typing import get_args

import pytest

from guardian.agents.coding_agent_contracts import (
    CodingAgentAdapterKind,
    CodingAgentPermissionPolicy,
    CodingAgentResult,
    CodingExecutionBinding,
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
        provider_id="provider-a",
        model_id="model-a",
        credential_ref="credential-a",
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
        adapter_kind="pi",
        instructions="Run the parser validation loop.",
        repo_root="/workspace/repo",
        context_summary="Validation metadata should be optional.",
        permission_policy=policy,
        validation_command="pytest -q",
        max_validation_attempts=4,
        provider_id="provider-b",
        model_id="model-b",
        credential_ref="credential-b",
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
    assert "pi" in get_args(CodingAgentAdapterKind)
    assert "pi_sdk" in get_args(CodingAgentAdapterKind)
    assert "codex" not in get_args(CodingAgentAdapterKind)
    assert "claudecode" not in get_args(CodingAgentAdapterKind)
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
            adapter_kind="pi",
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
            provider_id="provider-a",
            model_id="model-a",
            credential_ref="credential-a",
        )

    with pytest.raises(TypeError):
        CodingAgentTaskEnvelope(
            coding_task_id="coding-task-123",
            thread_id="thread-123",
            source_message_id="message-456",
            user_id="local",
            project_id=None,
            adapter_kind="pi",
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
            provider_id="provider-a",
            model_id="model-a",
            credential_ref="credential-a",
        )


def test_execution_binding_carries_invocation_identity_without_secret_material() -> None:
    credential = {
        "credential_ref": "credential-account-a",
        "owner_scope": "account",
        "owner_id": "account-a",
        "provider_id": "provider-a",
        "credential_type": "api_key",
        "funding_route": "user_byok",
        "source_class": "account_api_key",
        "usage_policy_ref": None,
    }
    binding = CodingExecutionBinding.authorized(
        harness_id="pi",
        harness_selection_mode="default",
        provider_id="provider-a",
        model_id="model-a",
        placement="container",
        credential=credential,
        user_id="account-a",
        project_id="project-a",
        thread_id="thread-a",
        source_message_id="message-a",
        coding_task_id="coding-task-a",
        attempt_id="attempt-a",
        max_attempts=2,
    )

    payload = binding.to_dict()

    assert payload["provider_id"] == "provider-a"
    assert payload["model_id"] == "model-a"
    assert payload["credential_ref"] == "credential-account-a"
    assert payload["user_id"] == "account-a"
    assert payload["project_id"] == "project-a"
    assert payload["thread_id"] == "thread-a"
    assert payload["source_message_id"] == "message-a"
    assert payload["coding_task_id"] == "coding-task-a"
    assert "api_key" not in payload
    assert "secret" not in payload
    assert CodingExecutionBinding.from_dict(payload) == binding


def test_execution_bindings_support_distinct_provider_model_pairs_and_service_policy() -> None:
    common = {
        "credential_ref": "credential-service-a",
        "owner_scope": "service",
        "owner_id": "codexify-deployment-a",
        "provider_id": "provider-a",
        "credential_type": "api_key",
        "funding_route": "codexify_included",
        "source_class": "service_api_key",
        "usage_policy_ref": "policy-a",
    }
    bindings = [
        CodingExecutionBinding.authorized(
            harness_id="pi",
            harness_selection_mode="explicit",
            provider_id=provider,
            model_id=model,
            placement="container",
            credential={**common, "provider_id": provider},
            user_id="account-a",
            project_id=None,
            thread_id="thread-a",
            source_message_id=f"message-{index}",
            coding_task_id=f"coding-task-{index}",
            attempt_id=f"attempt-{index}",
            max_attempts=1,
        )
        for index, (provider, model) in enumerate(
            (("provider-a", "model-a"), ("provider-b", "model-b")),
            start=1,
        )
    ]

    assert [(item.provider_id, item.model_id) for item in bindings] == [
        ("provider-a", "model-a"),
        ("provider-b", "model-b"),
    ]
    assert all(item.harness_id == "pi" for item in bindings)
    assert all(item.usage_policy_ref == "policy-a" for item in bindings)
    with pytest.raises(ValueError, match="usage_policy_missing"):
        CodingExecutionBinding.from_dict(
            {**bindings[0].to_dict(), "usage_policy_ref": None}
        )
    with pytest.raises(ValueError, match="selection_mode_invalid"):
        CodingExecutionBinding.from_dict(
            {**bindings[0].to_dict(), "harness_selection_mode": "auto"}
        )
