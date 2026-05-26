"""Guardian Delegation Loop v1 Phase 2A service helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import re
from typing import Any
from uuid import uuid4

from guardian.agents.store import AgentStore
from guardian.db.models import (
    ChatMessage,
    ChatThread,
    GuardianDelegationIntent,
)
from guardian.protocol_tokens import (
    ACCEPTANCE_STATUSES,
    AcceptanceStatus,
    GuardianDelegationApprovalMode,
    GuardianDelegationApprovalSource,
    GuardianDelegationApprovalState,
    GuardianDelegationContextSourceType,
    GuardianDelegationInteractionMode,
    GuardianDelegationIntentStatus,
    GuardianDelegationRunStatus,
)


def _new_external_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(blob.encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


_EXCLUDED_PERSONAL_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:i am|i'm)\s+(?:going through|dealing with)\s+(?:a\s+)?"
        r"(?:divorce|breakup|break-up|separation)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmy\s+(?:boss|client|manager|coworker|co-worker|team lead)\b.{0,48}"
        r"\b(?:frustrat(?:ing|ed)|annoy(?:ing|ed)|upset|angry|mad|furious|"
        r"terrible|awful|hate|driving me crazy|making me crazy)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:my|our)\s+(?:relationship|marriage)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmy\s+(?:wife|husband|boyfriend|girlfriend|partner|ex)\b",
        re.IGNORECASE,
    ),
)


class GuardianDelegationError(Exception):
    """Base service error with route-friendly status metadata."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class GuardianDelegationNotFoundError(GuardianDelegationError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=404, detail=detail)


class GuardianDelegationValidationError(GuardianDelegationError):
    def __init__(self, detail: str, *, status_code: int = 422) -> None:
        super().__init__(status_code=status_code, detail=detail)


class GuardianDelegationDispatchError(GuardianDelegationError):
    def __init__(self, detail: str = "guardian_delegation_dispatch_failed") -> None:
        super().__init__(status_code=503, detail=detail)


@dataclass
class GuardianDelegationService:
    """Persist selected-turn delegation intents and link them to AgentRuns."""

    db: Any | None = None
    agent_store: AgentStore = field(default_factory=AgentStore)

    def __post_init__(self) -> None:
        self.agent_store.configure_db(self.db)

    def configure_db(self, db: Any | None) -> None:
        self.db = db
        self.agent_store.configure_db(db)

    def create_intent(
        self,
        *,
        thread_id: int,
        source_message_id: int,
        project_id: int | None = None,
        interaction_mode: str = GuardianDelegationInteractionMode.NON_BLOCKING.value,
        approval_mode: str = GuardianDelegationApprovalMode.SCOPED_AUTO.value,
    ) -> dict[str, Any]:
        db = self._require_db()
        if interaction_mode != GuardianDelegationInteractionMode.NON_BLOCKING.value:
            raise GuardianDelegationValidationError("invalid_interaction_mode")
        if approval_mode != GuardianDelegationApprovalMode.SCOPED_AUTO.value:
            raise GuardianDelegationValidationError("invalid_approval_mode")

        with db.get_session() as session:
            thread = (
                session.query(ChatThread).filter_by(id=thread_id).first()
            )
            if thread is None:
                raise GuardianDelegationNotFoundError("thread_not_found")
            source_message = (
                session.query(ChatMessage)
                .filter_by(id=source_message_id)
                .first()
            )
            if source_message is None:
                raise GuardianDelegationNotFoundError("source_message_not_found")
            if int(source_message.thread_id) != int(thread_id):
                raise GuardianDelegationValidationError(
                    "source_message_thread_mismatch"
                )
            if str(source_message.role or "").strip().lower() != "user":
                raise GuardianDelegationValidationError(
                    "source_message_must_be_user_authored"
                )

            selected_turn_reference = self._build_selected_turn_reference(
                thread_id=thread.id,
                source_message_id=source_message.id,
                selected_turn_role=source_message.role,
                selected_turn_content=source_message.content,
            )
            resolved_project_id = self._resolve_project_id(
                requested_project_id=project_id,
                thread_project_id=thread.project_id,
            )
            plan_summary = self._build_phase2a_plan(
                thread_id=thread.id,
                source_message_id=source_message.id,
                project_id=resolved_project_id,
                selected_turn_reference=selected_turn_reference,
            )
            context_basis = self._build_context_basis(
                thread_id=thread.id,
                source_message_id=source_message.id,
                selected_turn_reference=selected_turn_reference,
            )
            intent_id = _new_external_id("gdi")
            row = GuardianDelegationIntent(
                intent_id=intent_id,
                thread_id=thread.id,
                source_message_id=source_message.id,
                project_id=resolved_project_id,
                interaction_mode=interaction_mode,
                approval_mode=approval_mode,
                approval_state=GuardianDelegationApprovalState.APPROVED.value,
                approval_source=GuardianDelegationApprovalSource.AUTO.value,
                acceptance_status=AcceptanceStatus.ACCEPTED.value,
                intent_status=GuardianDelegationIntentStatus.PLANNING.value,
                plan_summary=plan_summary,
                context_basis=context_basis,
            )
            session.add(row)
            session.commit()

            # Detach the values we need before the store opens its own sessions.
            thread_owner_id = str(thread.user_id)

        try:
            run = self._create_agent_run_link(
                intent_id=intent_id,
                thread_id=thread_id,
                source_message_id=source_message_id,
                project_id=resolved_project_id,
                user_id=thread_owner_id,
                plan_summary=plan_summary,
                context_basis=context_basis,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            with db.get_session() as session:
                row = (
                    session.query(GuardianDelegationIntent)
                    .filter_by(intent_id=intent_id)
                    .first()
                )
                if row is not None:
                    row.intent_status = (
                        GuardianDelegationIntentStatus.FAILED.value
                    )
                    row.acceptance_status = (
                        AcceptanceStatus.ACCEPTED_DEGRADED.value
                    )
                    session.commit()
            raise GuardianDelegationDispatchError() from exc

        with db.get_session() as session:
            row = (
                session.query(GuardianDelegationIntent)
                .filter_by(intent_id=intent_id)
                .first()
            )
            if row is None:  # pragma: no cover - defensive branch
                raise GuardianDelegationNotFoundError(
                    "guardian_delegation_intent_missing_after_create"
                )
            row.run_id = str(run["run_id"])
            row.intent_status = GuardianDelegationIntentStatus.ACCEPTED.value
            session.commit()
            session.refresh(row)
            return self._serialize_intent(
                row,
                run_status=self.project_run_status(run.get("status")),
            )

    def get_intent(self, intent_id: str) -> dict[str, Any]:
        db = self._require_db()
        with db.get_session() as session:
            row = (
                session.query(GuardianDelegationIntent)
                .filter_by(intent_id=intent_id)
                .first()
            )
            if row is None:
                raise GuardianDelegationNotFoundError(
                    "guardian_delegation_intent_not_found"
                )
            run_status = GuardianDelegationRunStatus.NOT_ENQUEUED.value
            if row.run_id:
                run = self.agent_store.get_run(str(row.run_id))
                if run is None:
                    raise GuardianDelegationValidationError(
                        "linked_agent_run_missing",
                        status_code=500,
                    )
                run_status = self.project_run_status(run.get("status"))
            return self._serialize_intent(row, run_status=run_status)

    def project_run_status(self, agent_run_status: Any | None) -> str:
        if agent_run_status is None or not str(agent_run_status).strip():
            return GuardianDelegationRunStatus.NOT_ENQUEUED.value

        normalized = str(agent_run_status).strip().lower()
        if normalized == "queued":
            return GuardianDelegationRunStatus.QUEUED.value
        if normalized == "running":
            return GuardianDelegationRunStatus.RUNNING.value
        if normalized == "succeeded":
            return GuardianDelegationRunStatus.COMPLETED.value
        if normalized in {"failed", "escalated"}:
            return GuardianDelegationRunStatus.FAILED.value
        if normalized in {"canceled", "cancelled"}:
            return GuardianDelegationRunStatus.CANCELLED.value
        raise GuardianDelegationValidationError(
            "unknown_agent_run_status",
            status_code=500,
        )

    def _create_agent_run_link(
        self,
        *,
        intent_id: str,
        thread_id: int,
        source_message_id: int,
        project_id: int | None,
        user_id: str,
        plan_summary: dict[str, Any],
        context_basis: list[dict[str, Any]],
    ) -> dict[str, Any]:
        deployment_spec = {
            "guardian_delegation": {
                "ownership": "guardian_delegation_intent",
                "intent_id": intent_id,
                "phase": "phase2a",
                "suppress_source_thread_delivery": True,
            },
            "source_thread_id": thread_id,
            "source_message_id": source_message_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "project_id": project_id,
            "adapter_kind": "pi_codex_runner",
            "instructions": plan_summary["standardized_task_prompt"],
            "plan_summary": plan_summary,
            "context_basis": context_basis,
        }
        deployment = self.agent_store.create_deployment(
            flow_id=f"guardian_delegation_{intent_id}",
            thread_id=thread_id,
            spec_json=deployment_spec,
            spec_hash=_stable_hash(deployment_spec),
            trust_state="supervised",
        )
        # Phase 2A intentionally stops at durable AgentRun creation. Full queue
        # dispatch remains deferred until the hybrid loop can prove execution
        # without relying on source-thread result delivery.
        return self.agent_store.create_run(
            deployment_id=str(deployment["deployment_id"]),
            thread_id=thread_id,
            runtime_target="container",
            rollback_mode="auto",
            status="queued",
        )

    def _build_phase2a_plan(
        self,
        *,
        thread_id: int,
        source_message_id: int,
        project_id: int | None,
        selected_turn_reference: dict[str, Any],
    ) -> dict[str, Any]:
        standardized_task_prompt = "\n".join(
            [
                "Guardian Delegation Loop v1 Phase 2A task.",
                f"thread_id: {thread_id}",
                f"source_message_id: {source_message_id}",
                f"project_id: {project_id if project_id is not None else 'none'}",
                "Use only the selected source message as explicit task input by reference.",
                "Do not use broad chat history, personal facts, identity-derived facts, or unrelated conversation context.",
                "Resolve the work request from the selected source turn by lineage reference only.",
                "Do not persist or restate raw selected-turn text in downstream artifacts.",
                f"selected_turn_role: {selected_turn_reference['role']}",
                (
                    "selected_turn_content_hash: "
                    f"{selected_turn_reference['content_hash']}"
                ),
                (
                    "selected_turn_content_length: "
                    f"{selected_turn_reference['content_length']}"
                ),
                "If a safe work-only task cannot be reconstructed from this reference, request clarification instead of dispatching.",
                "Phase 2A constraints:",
                "- selected_turn-only context_basis",
                "- no source-thread result delivery",
                "- no Project KB or GitHub context expansion",
                "- no intent-spine unification",
            ]
        )
        return {
            "standardized_task_prompt": standardized_task_prompt,
            "purpose": (
                "Normalize the selected user turn by lineage reference into a "
                "work-scoped coding-agent task summary."
            ),
            "in_scope": [
                "selected source message lineage reference",
                "existing AgentRun backbone linkage",
                "scoped auto-approval",
            ],
            "out_of_scope": [
                "thread result reinjection",
                "Command Center transcript UI",
                "human approval endpoints",
                "Project KB or GitHub context expansion",
                "intent-spine unification",
            ],
            "acceptance_criteria": [
                "persist GuardianDelegationIntent with source lineage",
                "record selected_turn-only context_basis",
                "link a durable AgentRun run_id",
            ],
            "blast_radius": (
                "Guardian-owned delegation persistence and AgentRun linkage "
                "only."
            ),
            "dependencies": [
                "selected source message reference",
                "existing AgentRun storage",
            ],
            "unknowns": [
                "live queue dispatch remains deferred in Phase 2A",
            ],
            "risk_class": "medium",
            "approval_requirements": [
                "approval_mode=scoped_auto",
                "approval_source=auto",
                "work-scoped context only",
            ],
        }

    def _build_context_basis(
        self,
        *,
        thread_id: int,
        source_message_id: int,
        selected_turn_reference: dict[str, Any],
    ) -> list[dict[str, Any]]:
        # Phase 2A intentionally records selected-turn-only context. Project
        # KB, repository expansion, linked artifacts, and work-scoped
        # preferences are deferred to Phase 2B under the contract.
        return [
            {
                "source_type": (
                    GuardianDelegationContextSourceType.SELECTED_TURN.value
                ),
                "source_id": str(source_message_id),
                "included_fields": [
                    "message.role",
                    "message.thread_id",
                    "message.id",
                    "message.content_hash",
                    "message.content_length",
                ],
                "reason": "selected authored turn is the explicit task source",
                "confidence": "high",
                "policy_allowed": True,
                "thread_id": thread_id,
                "message_role": selected_turn_reference["role"],
                "content_hash": selected_turn_reference["content_hash"],
                "content_length": selected_turn_reference["content_length"],
            }
        ]

    def _build_selected_turn_reference(
        self,
        *,
        thread_id: int,
        source_message_id: int,
        selected_turn_role: Any,
        selected_turn_content: Any,
    ) -> dict[str, Any]:
        selected_turn_text = str(selected_turn_content or "").strip()
        if not selected_turn_text:
            raise GuardianDelegationValidationError(
                "selected_turn_requires_clarification"
            )

        # Phase 2A does not try to extract a clean coding task from mixed
        # personal/work turns deterministically. Require a work-only restatement.
        if self._contains_obvious_excluded_personal_context(selected_turn_text):
            raise GuardianDelegationValidationError(
                "selected_turn_requires_clarification"
            )

        return {
            "thread_id": thread_id,
            "source_message_id": source_message_id,
            "role": str(selected_turn_role or "user").strip().lower() or "user",
            "content_hash": _hash_text(selected_turn_text),
            "content_length": len(selected_turn_text),
        }

    def _contains_obvious_excluded_personal_context(self, text: str) -> bool:
        normalized = " ".join(str(text or "").split())
        return any(
            pattern.search(normalized)
            for pattern in _EXCLUDED_PERSONAL_CONTEXT_PATTERNS
        )

    def _resolve_project_id(
        self,
        *,
        requested_project_id: int | None,
        thread_project_id: int | None,
    ) -> int | None:
        if requested_project_id is None:
            return thread_project_id
        if thread_project_id is not None and requested_project_id != thread_project_id:
            raise GuardianDelegationValidationError("project_id_mismatch")
        return requested_project_id

    def _serialize_intent(
        self,
        row: GuardianDelegationIntent,
        *,
        run_status: str,
    ) -> dict[str, Any]:
        acceptance_status = str(row.acceptance_status or "").strip()
        if acceptance_status not in ACCEPTANCE_STATUSES:
            raise GuardianDelegationValidationError(
                "unknown_acceptance_status",
                status_code=500,
            )
        return {
            "intent_id": row.intent_id,
            "thread_id": int(row.thread_id),
            "source_message_id": int(row.source_message_id),
            "project_id": row.project_id,
            "acceptance_status": acceptance_status,
            "approval_state": str(row.approval_state),
            "approval_source": str(row.approval_source),
            "intent_status": str(row.intent_status),
            "run_id": row.run_id,
            "run_status": run_status,
            "context_basis": list(row.context_basis or []),
            "plan_summary": dict(row.plan_summary or {}),
        }

    def _require_db(self) -> Any:
        if self.db is None or not hasattr(self.db, "get_session"):
            raise GuardianDelegationDispatchError(
                "guardian_delegation_db_unavailable"
            )
        return self.db


__all__ = [
    "GuardianDelegationDispatchError",
    "GuardianDelegationError",
    "GuardianDelegationNotFoundError",
    "GuardianDelegationService",
    "GuardianDelegationValidationError",
]
