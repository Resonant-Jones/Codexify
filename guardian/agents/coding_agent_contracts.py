"""Typed contracts for Guardian-mediated coding-agent execution.

This module is intentionally dependency-light and does not execute adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

# `pi_codex_runner` remains the canonical worker target for now because it is
# already persisted in runtime state. The name is legacy-compatible only and
# does not imply direct Codex CLI execution; it is the Pi broker lane.
CodingAgentAdapterKind = Literal[
    "pi",
    "pi_sdk",
    "pi_codex_runner",
]
CodingAgentTaskStatus = Literal[
    "queued",
    "dispatching",
    "running",
    "completed",
    "failed_retryable",
    "failed_fatal",
    "cancelled",
]


@dataclass(frozen=True)
class CodingAgentPermissionPolicy:
    allow_shell: bool
    allow_network: bool
    allow_write: bool
    allowed_paths: tuple[str, ...]
    max_runtime_seconds: int


@dataclass(frozen=True)
class CodingAgentTaskEnvelope:
    coding_task_id: str
    thread_id: str
    source_message_id: str
    attempt_id: str
    user_id: str
    project_id: str | None
    adapter_kind: CodingAgentAdapterKind
    instructions: str
    repo_root: str | None
    context_summary: str | None
    permission_policy: CodingAgentPermissionPolicy
    provider_id: str
    model_id: str
    credential_ref: str
    harness_selection_mode: Literal["default", "explicit", "auto"] = "default"
    campaign_id: str | None = None
    work_order_id: str | None = None
    # Optional supervised validation command executed once after adapter return.
    validation_command: str | None = None
    max_validation_attempts: int = 1
    worktree_lease_id: str | None = None
    require_worktree_lease: bool = False
    commit_after_validation: bool = False
    commit_message: str | None = None
    require_human_review_before_merge: bool = True


@dataclass(frozen=True)
class CodingExecutionBinding:
    """Secret-free Guardian authorization bound to one coding invocation."""

    binding_id: str
    schema_version: int
    harness_id: str
    harness_selection_mode: str
    provider_id: str
    model_id: str
    funding_route: str
    placement: str
    credential_ref: str
    credential_owner_scope: str
    credential_owner_id: str
    credential_type: str
    credential_source_class: str
    usage_policy_ref: str | None
    user_id: str
    project_id: str | None
    thread_id: str
    source_message_id: str
    coding_task_id: str
    attempt_id: str
    max_attempts: int
    authorization_evidence_ref: str

    @classmethod
    def authorized(
        cls,
        *,
        harness_id: str,
        harness_selection_mode: str,
        provider_id: str,
        model_id: str,
        placement: str,
        credential: dict[str, object],
        user_id: str,
        project_id: str | None,
        thread_id: str,
        source_message_id: str,
        coding_task_id: str,
        attempt_id: str,
        max_attempts: int,
    ) -> "CodingExecutionBinding":
        binding_id = f"xeb_{uuid4().hex}"
        return cls(
            binding_id=binding_id,
            schema_version=1,
            harness_id=harness_id,
            harness_selection_mode=harness_selection_mode,
            provider_id=provider_id,
            model_id=model_id,
            funding_route=str(credential["funding_route"]),
            placement=placement,
            credential_ref=str(credential["credential_ref"]),
            credential_owner_scope=str(credential["owner_scope"]),
            credential_owner_id=str(credential["owner_id"]),
            credential_type=str(credential["credential_type"]),
            credential_source_class=str(credential["source_class"]),
            usage_policy_ref=(
                str(credential["usage_policy_ref"])
                if credential.get("usage_policy_ref") is not None
                else None
            ),
            user_id=user_id,
            project_id=project_id,
            thread_id=thread_id,
            source_message_id=source_message_id,
            coding_task_id=coding_task_id,
            attempt_id=attempt_id,
            max_attempts=max_attempts,
            authorization_evidence_ref=binding_id,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "CodingExecutionBinding":
        required = (
            "binding_id",
            "harness_id",
            "harness_selection_mode",
            "provider_id",
            "model_id",
            "funding_route",
            "placement",
            "credential_ref",
            "credential_owner_scope",
            "credential_owner_id",
            "credential_type",
            "credential_source_class",
            "user_id",
            "thread_id",
            "source_message_id",
            "coding_task_id",
            "attempt_id",
            "authorization_evidence_ref",
        )
        if any(not str(payload.get(key) or "").strip() for key in required):
            raise ValueError("execution_binding_incomplete")
        if int(payload.get("schema_version") or 0) != 1:
            raise ValueError("execution_binding_version_unsupported")
        if payload.get("harness_selection_mode") not in {"default", "explicit"}:
            raise ValueError("execution_binding_selection_mode_invalid")
        if payload.get("credential_owner_scope") == "service" and not str(
            payload.get("usage_policy_ref") or ""
        ).strip():
            raise ValueError("execution_binding_usage_policy_missing")
        max_attempts = int(payload.get("max_attempts") or 0)
        if max_attempts < 1 or max_attempts > 3:
            raise ValueError("execution_binding_attempt_limit_invalid")
        project_id = payload.get("project_id")
        return cls(
            binding_id=str(payload["binding_id"]),
            schema_version=1,
            harness_id=str(payload["harness_id"]),
            harness_selection_mode=str(payload["harness_selection_mode"]),
            provider_id=str(payload["provider_id"]),
            model_id=str(payload["model_id"]),
            funding_route=str(payload["funding_route"]),
            placement=str(payload["placement"]),
            credential_ref=str(payload["credential_ref"]),
            credential_owner_scope=str(payload["credential_owner_scope"]),
            credential_owner_id=str(payload["credential_owner_id"]),
            credential_type=str(payload["credential_type"]),
            credential_source_class=str(payload["credential_source_class"]),
            usage_policy_ref=(
                str(payload["usage_policy_ref"])
                if payload.get("usage_policy_ref") is not None
                else None
            ),
            user_id=str(payload["user_id"]),
            project_id=str(project_id) if project_id is not None else None,
            thread_id=str(payload["thread_id"]),
            source_message_id=str(payload["source_message_id"]),
            coding_task_id=str(payload["coding_task_id"]),
            attempt_id=str(payload["attempt_id"]),
            max_attempts=max_attempts,
            authorization_evidence_ref=str(payload["authorization_evidence_ref"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "schema_version": self.schema_version,
            "harness_id": self.harness_id,
            "harness_selection_mode": self.harness_selection_mode,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "funding_route": self.funding_route,
            "placement": self.placement,
            "credential_ref": self.credential_ref,
            "credential_owner_scope": self.credential_owner_scope,
            "credential_owner_id": self.credential_owner_id,
            "credential_type": self.credential_type,
            "credential_source_class": self.credential_source_class,
            "usage_policy_ref": self.usage_policy_ref,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "thread_id": self.thread_id,
            "source_message_id": self.source_message_id,
            "coding_task_id": self.coding_task_id,
            "attempt_id": self.attempt_id,
            "max_attempts": self.max_attempts,
            "authorization_evidence_ref": self.authorization_evidence_ref,
        }


@dataclass(frozen=True)
class CodingAgentResult:
    coding_task_id: str
    attempt_id: str
    status: CodingAgentTaskStatus
    summary: str
    files_changed: tuple[str, ...]
    artifacts: tuple[str, ...]
    logs_summary: str | None
    error_code: str | None
    error_message: str | None
    adapter_session_ref: str | None
    validation_results: dict[str, object] | None = None


__all__ = [
    "CodingAgentAdapterKind",
    "CodingAgentPermissionPolicy",
    "CodingAgentResult",
    "CodingAgentTaskEnvelope",
    "CodingAgentTaskStatus",
    "CodingExecutionBinding",
]
