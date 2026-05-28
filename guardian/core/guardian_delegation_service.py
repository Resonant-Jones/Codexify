"""Guardian Delegation Loop v1 Phase 3 service helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import json
import os
import re
from typing import Any
from uuid import uuid4

from guardian.db.models import (
    ChatMessage,
    ChatThread,
    GeneratedDocument,
    GuardianDelegationIntent,
    ProjectDocumentLink,
    UploadedDocument,
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
    GuardianDelegationVisibilityStatus,
    GUARDIAN_DELEGATION_VISIBILITY_STATUSES,
)


def _new_external_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(blob.encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _new_agent_store() -> Any:
    from guardian.agents.store import AgentStore

    return AgentStore()


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

_EXCLUDED_KB_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    *_EXCLUDED_PERSONAL_CONTEXT_PATTERNS,
    re.compile(r"\b(?:chat|conversation)\s+history\b", re.IGNORECASE),
    re.compile(r"\b(?:prior|previous|unrelated)\s+conversation\b", re.IGNORECASE),
    re.compile(r"\b(?:diary|journal|personal note|private note)\b", re.IGNORECASE),
    re.compile(r"(?m)^\s*(?:user|assistant)\s*:", re.IGNORECASE),
)

_PROJECT_KB_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "by",
        "for",
        "from",
        "help",
        "in",
        "into",
        "keep",
        "me",
        "need",
        "of",
        "on",
        "or",
        "please",
        "the",
        "this",
        "to",
        "update",
        "with",
    }
)

_MAX_PROJECT_KB_DOCS = 3
_MAX_PROJECT_KB_LINK_SCAN = 12
_MAX_SAFE_KB_EXCERPT_CHARS = 240
_MAX_SAFE_RESULT_SUMMARY_CHARS = 320
_MAX_SAFE_VALIDATION_FIELD_CHARS = 220
_MAX_SAFE_RENDERED_FILES = 20

_REDACTED_UNSAFE_VALIDATION_DETAIL = "[redacted unsafe validation detail]"
_REDACTED_UNSAFE_PATH = "[redacted unsafe path]"

_GUARDIAN_RESULT_INTERNAL_MARKERS: tuple[str, ...] = (
    "context_basis",
    "kb_context",
    "project_kb_reference",
    "selected_turn_content_hash",
    "selected_turn_content_length",
    "standardized_task_prompt",
    "hidden prompt",
    "system prompt",
)

_SECRET_LIKE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:api[_-]?key|secret|token|password)\b\s*(?:=|:)\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\bsk-[A-Za-z0-9]{12,}\b"),
    re.compile(
        r"-----BEGIN\s+(?:RSA|OPENSSH|EC|DSA|PGP)?\s*PRIVATE KEY-----",
        re.IGNORECASE,
    ),
)

_UNSAFE_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|/)\.ssh(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)\.env(?:\.[^/]+)?$", re.IGNORECASE),
    re.compile(r"(^|/)\.aws/credentials$", re.IGNORECASE),
    re.compile(r"(^|/)\.kube/config$", re.IGNORECASE),
    re.compile(r"(^|/)\.npmrc$", re.IGNORECASE),
    re.compile(r"(^|/)\.pypirc$", re.IGNORECASE),
    re.compile(r"(^|/)\.netrc$", re.IGNORECASE),
    re.compile(r"(^|/)(?:id_rsa|id_ed25519|known_hosts)$", re.IGNORECASE),
    re.compile(r"\.(?:pem|p12|pfx|key)$", re.IGNORECASE),
)


def build_guardian_delegation_result_delivery_key(
    *, intent_id: str, run_id: str
) -> str:
    return f"guardian_delegation:{intent_id}:{run_id}:thread_result"


def _collapse_whitespace(value: Any) -> str:
    return " ".join(str(value or "").split())


def _known_repo_prefixes() -> tuple[str, ...]:
    prefixes = ["/app/", "/Volumes/Dev_SSD/Codexify-main/"]
    cwd = os.getcwd().replace("\\", "/").rstrip("/")
    if cwd:
        prefixes.insert(0, cwd + "/")
    return tuple(dict.fromkeys(prefixes))


def _rewrite_known_repo_prefixes(value: str) -> str:
    rewritten = value.replace("\\", "/")
    for prefix in _known_repo_prefixes():
        if rewritten.startswith(prefix):
            rewritten = rewritten[len(prefix) :]
            break
        rewritten = rewritten.replace(prefix, "")
    return rewritten


def _contains_unsafe_result_text(
    value: str,
    *,
    blocked_literals: list[str] | None = None,
) -> bool:
    lowered = value.lower()
    if any(marker in lowered for marker in _GUARDIAN_RESULT_INTERNAL_MARKERS):
        return True
    for literal in blocked_literals or []:
        normalized_literal = _collapse_whitespace(literal)
        if normalized_literal and normalized_literal in value:
            return True
    for pattern in (
        *_EXCLUDED_PERSONAL_CONTEXT_PATTERNS,
        *_EXCLUDED_KB_CONTEXT_PATTERNS,
        *_SECRET_LIKE_PATTERNS,
        *_UNSAFE_PATH_PATTERNS,
    ):
        if pattern.search(value):
            return True
    return False


def _sanitize_guardian_display_text(
    value: Any,
    *,
    max_chars: int,
    placeholder: str | None = None,
    allow_token_status: bool = False,
    blocked_literals: list[str] | None = None,
) -> str | None:
    normalized = _collapse_whitespace(value)
    if not normalized:
        return None
    normalized = _rewrite_known_repo_prefixes(normalized)
    if allow_token_status and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", normalized):
        return normalized
    if _contains_unsafe_result_text(
        normalized,
        blocked_literals=blocked_literals,
    ):
        return placeholder
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def sanitize_guardian_result_files_for_display(
    files_changed: list[Any] | None,
) -> list[str]:
    safe_paths: list[str] = []
    redacted_unsafe_path = False
    for raw_path in list(files_changed or [])[:_MAX_SAFE_RENDERED_FILES]:
        normalized = _collapse_whitespace(raw_path)
        if not normalized:
            continue
        normalized = _rewrite_known_repo_prefixes(normalized)
        if (
            not normalized
            or normalized in {".", ".."}
            or normalized.startswith("../")
            or normalized.startswith("/")
            or _contains_unsafe_result_text(normalized)
        ):
            redacted_unsafe_path = True
            continue
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if not normalized or _contains_unsafe_result_text(normalized):
            redacted_unsafe_path = True
            continue
        safe_paths.append(normalized[:220])
    if redacted_unsafe_path:
        safe_paths.append(_REDACTED_UNSAFE_PATH)
    return safe_paths[:_MAX_SAFE_RENDERED_FILES]


def sanitize_guardian_validation_results_for_display(
    validation_results: Any | None,
    *,
    blocked_literals: list[str] | None = None,
) -> dict[str, str] | None:
    if not isinstance(validation_results, dict):
        return None

    safe_validation: dict[str, str] = {}
    validation_status = _sanitize_guardian_display_text(
        validation_results.get("status"),
        max_chars=64,
        placeholder=_REDACTED_UNSAFE_VALIDATION_DETAIL,
        allow_token_status=True,
        blocked_literals=blocked_literals,
    )
    if validation_status:
        safe_validation["status"] = validation_status

    validation_command = _sanitize_guardian_display_text(
        validation_results.get("command"),
        max_chars=_MAX_SAFE_VALIDATION_FIELD_CHARS,
        placeholder=_REDACTED_UNSAFE_VALIDATION_DETAIL,
        blocked_literals=blocked_literals,
    )
    if validation_command:
        safe_validation["command"] = validation_command

    validation_error = _sanitize_guardian_display_text(
        validation_results.get("error_message"),
        max_chars=_MAX_SAFE_VALIDATION_FIELD_CHARS,
        placeholder=_REDACTED_UNSAFE_VALIDATION_DETAIL,
        blocked_literals=blocked_literals,
    )
    if validation_error:
        safe_validation["error_message"] = validation_error

    return safe_validation or None


def _safe_guardian_result_summary(
    summary: Any,
    *,
    blocked_literals: list[str] | None = None,
) -> str | None:
    normalized = _sanitize_guardian_display_text(
        summary,
        max_chars=_MAX_SAFE_RESULT_SUMMARY_CHARS,
        blocked_literals=blocked_literals,
    )
    if not normalized:
        return None
    return normalized


def build_guardian_delegation_result_message_content(
    *,
    intent_id: str,
    run_id: str,
    status: str,
    summary: Any,
    files_changed: list[str],
    validation_results: Any | None,
    commit_hash: str | None,
    blocked_literals: list[str] | None = None,
) -> str:
    content_parts = ["## Guardian Delegation Result\n\n"]
    content_parts.append(f"**Status**: {str(status or '').upper()}\n\n")
    content_parts.append(f"**Intent ID**: `{intent_id}`\n\n")
    content_parts.append(f"**Run ID**: `{run_id}`\n\n")

    safe_summary = _safe_guardian_result_summary(
        summary,
        blocked_literals=blocked_literals,
    )
    if safe_summary:
        content_parts.append(f"**Summary**: {safe_summary}\n\n")

    safe_files = sanitize_guardian_result_files_for_display(files_changed)
    if safe_files:
        content_parts.append("**Files Changed**:\n")
        for path in safe_files:
            content_parts.append(f"- `{path}`\n")
        content_parts.append("\n")

    if commit_hash:
        content_parts.append(f"**Commit Hash**: `{commit_hash}`\n\n")

    safe_validation = sanitize_guardian_validation_results_for_display(
        validation_results,
        blocked_literals=blocked_literals,
    )
    if isinstance(safe_validation, dict):
        validation_status = safe_validation.get("status")
        validation_command = safe_validation.get("command")
        validation_error = safe_validation.get("error_message")
        if validation_status:
            content_parts.append(
                f"**Validation Status**: `{validation_status}`\n\n"
            )
        if validation_command:
            content_parts.append(
                f"**Validation Command**: `{validation_command}`\n\n"
            )
        if validation_error:
            content_parts.append(
                f"**Validation Error**: {validation_error}\n\n"
            )

    return "".join(content_parts)


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
    agent_store: Any = field(default_factory=_new_agent_store)

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

            selected_turn_text = str(source_message.content or "").strip()
            thread_owner_id = str(thread.user_id)
            selected_turn_reference = self._build_selected_turn_reference(
                thread_id=thread.id,
                source_message_id=source_message.id,
                selected_turn_role=source_message.role,
                selected_turn_content=selected_turn_text,
            )
            resolved_project_id = self._resolve_project_id(
                requested_project_id=project_id,
                thread_project_id=thread.project_id,
            )
            project_kb_context = self._collect_project_kb_context(
                session=session,
                project_id=resolved_project_id,
                user_id=thread_owner_id,
                selected_turn_text=selected_turn_text,
            )
            plan_summary = self._build_phase2b_plan(
                thread_id=thread.id,
                source_message_id=source_message.id,
                project_id=resolved_project_id,
                selected_turn_reference=selected_turn_reference,
                project_kb_context=project_kb_context,
            )
            context_basis = self._build_context_basis(
                thread_id=thread.id,
                source_message_id=source_message.id,
                selected_turn_reference=selected_turn_reference,
                project_kb_context=project_kb_context,
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
                visibility_status=(
                    GuardianDelegationVisibilityStatus.NOT_POSTED.value
                ),
                plan_summary=plan_summary,
                context_basis=context_basis,
            )
            session.add(row)
            session.commit()

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
            row.result_delivery_key = (
                build_guardian_delegation_result_delivery_key(
                    intent_id=intent_id,
                    run_id=str(run["run_id"]),
                )
            )
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
                "phase": "phase3",
                "suppress_source_thread_delivery": False,
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
        # Guardian Delegation Loop v1 Phase 3 still uses a direct Guardian-owned
        # route. Intent-spine unification remains deferred even though
        # source-thread result delivery is now proven for Guardian-owned runs.
        return self.agent_store.create_run(
            deployment_id=str(deployment["deployment_id"]),
            thread_id=thread_id,
            runtime_target="container",
            rollback_mode="auto",
            status="queued",
        )

    def _build_phase2b_plan(
        self,
        *,
        thread_id: int,
        source_message_id: int,
        project_id: int | None,
        selected_turn_reference: dict[str, Any],
        project_kb_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        standardized_task_prompt_lines = [
            "Guardian Delegation Loop v1 Phase 3 task.",
            f"thread_id: {thread_id}",
            f"source_message_id: {source_message_id}",
            f"project_id: {project_id if project_id is not None else 'none'}",
            "Use only the selected source message as explicit task input by reference.",
            "Use only policy-allowed local Project KB references included in plan_summary.kb_context when present.",
            "Do not use broad chat history, personal facts, identity-derived facts, or unrelated conversation context.",
            "Do not use GitHub, web, or external connector context in this phase.",
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
        ]
        if project_kb_context:
            standardized_task_prompt_lines.append(
                f"project_kb_context_count: {len(project_kb_context)}"
            )
            for entry in project_kb_context:
                standardized_task_prompt_lines.append(
                    "project_kb_reference: "
                    f"source_type={entry['source_type']} "
                    f"source_id={entry['source_id']} "
                    f"title={entry['title']}"
                )
        else:
            standardized_task_prompt_lines.append(
                "project_kb_context_count: 0"
            )
        standardized_task_prompt_lines.extend(
            [
                "If a safe work-only task cannot be reconstructed from these references, request clarification instead of dispatching.",
                "Phase 3 constraints:",
                "- selected turn lineage by reference only",
                "- local Project KB context only when policy-allowed",
                "- no GitHub context",
                "- no intent-spine unification",
            ]
        )
        standardized_task_prompt = "\n".join(standardized_task_prompt_lines)
        kb_context = [
            self._serialize_plan_kb_entry(entry) for entry in project_kb_context
        ]
        dependencies = [
            "selected source message reference",
            "existing AgentRun storage",
        ]
        if kb_context:
            dependencies.append("policy-allowed local project KB references")
        return {
            "standardized_task_prompt": standardized_task_prompt,
            "purpose": (
                "Normalize the selected user turn by lineage reference into a "
                "work-scoped coding-agent task summary with local Project KB "
                "references when policy-allowed."
            ),
            "in_scope": [
                "selected source message lineage reference",
                "policy-filtered local project KB references",
                "existing AgentRun backbone linkage",
                "scoped auto-approval",
                "Guardian-owned source-thread result delivery",
            ],
            "out_of_scope": [
                "Command Center transcript UI",
                "human approval endpoints",
                "GitHub context expansion",
                "broad chat history",
                "intent-spine unification",
            ],
            "acceptance_criteria": [
                "persist GuardianDelegationIntent with source lineage",
                "record selected_turn context_basis",
                "record policy-allowed Project KB context when available",
                "link a durable AgentRun run_id",
                "preserve separate visibility state while enabling guarded source-thread delivery",
            ],
            "blast_radius": (
                "Guardian-owned delegation persistence, AgentRun linkage, "
                "and source-thread result delivery only."
            ),
            "dependencies": dependencies,
            "unknowns": [
                "broader approval lifecycle remains deferred after Phase 3",
                "GitHub context and broader retrieval widening remain deferred",
            ],
            "risk_class": "medium",
            "approval_requirements": [
                "approval_mode=scoped_auto",
                "approval_source=auto",
                "work-scoped context only",
            ],
            "kb_context": kb_context,
        }

    def _build_context_basis(
        self,
        *,
        thread_id: int,
        source_message_id: int,
        selected_turn_reference: dict[str, Any],
        project_kb_context: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        context_basis = [
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
        for entry in project_kb_context:
            context_basis.append(self._serialize_context_basis_kb_entry(entry))
        return context_basis

    def _collect_project_kb_context(
        self,
        *,
        session: Any,
        project_id: int | None,
        user_id: str,
        selected_turn_text: str,
    ) -> list[dict[str, Any]]:
        if project_id is None:
            return []

        search_terms = self._extract_relevance_terms(selected_turn_text)
        if not search_terms:
            return []

        links = (
            session.query(ProjectDocumentLink)
            .filter(ProjectDocumentLink.project_id == project_id)
            .filter(ProjectDocumentLink.is_enabled.is_(True))
            .order_by(ProjectDocumentLink.attached_at.desc())
            .limit(_MAX_PROJECT_KB_LINK_SCAN)
            .all()
        )

        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for attached_rank, link in enumerate(links, start=1):
            doc_type = self._normalize_project_doc_type(
                getattr(link, "document_type", None)
            )
            doc_id = str(getattr(link, "document_id", "") or "").strip()
            if not doc_type or not doc_id:
                continue
            dedupe_key = (doc_type, doc_id)
            if dedupe_key in seen:
                continue
            candidate = self._build_project_kb_candidate(
                session=session,
                project_id=project_id,
                user_id=user_id,
                doc_id=doc_id,
                doc_type=doc_type,
                search_terms=search_terms,
                attached_rank=attached_rank,
            )
            if candidate is None:
                continue
            seen.add(dedupe_key)
            candidates.append(candidate)

        candidates.sort(
            key=lambda entry: (
                -int(entry["score"]),
                int(entry["attached_rank"]),
                str(entry["source_id"]),
            )
        )

        selected: list[dict[str, Any]] = []
        for rank, candidate in enumerate(candidates[:_MAX_PROJECT_KB_DOCS], start=1):
            selected.append(
                {
                    **candidate,
                    "rank": rank,
                }
            )
        return selected

    def _build_project_kb_candidate(
        self,
        *,
        session: Any,
        project_id: int,
        user_id: str,
        doc_id: str,
        doc_type: str,
        search_terms: list[str],
        attached_rank: int,
    ) -> dict[str, Any] | None:
        row = self._load_project_document_row(
            session=session,
            project_id=project_id,
            user_id=user_id,
            doc_id=doc_id,
            doc_type=doc_type,
        )
        if row is None:
            return None

        title = str(row.get("title") or "").strip()
        filename = str(row.get("filename") or "").strip()
        raw_content = str(row.get("raw_content") or "").strip()
        filter_text = "\n".join(part for part in [title, filename, raw_content] if part)
        if self._contains_excluded_kb_context(filter_text):
            return None

        safe_excerpt = self._build_safe_kb_excerpt(raw_content)
        source_type = self._classify_project_kb_source_type(
            title=title,
            filename=filename,
        )
        score = self._score_project_kb_candidate(
            search_terms=search_terms,
            title=title,
            filename=filename,
            raw_content=raw_content,
            source_type=source_type,
        )
        if score <= 0:
            return None

        safe_excerpt_hash = _hash_text(safe_excerpt) if safe_excerpt else None
        content_hash_source = raw_content or title or filename
        return {
            "source_type": source_type,
            "source_id": f"{doc_type}:{doc_id}",
            "title": title or filename or doc_id,
            "filename": filename or None,
            "project_id": project_id,
            "thread_id": row.get("thread_id"),
            "content_hash": _hash_text(content_hash_source),
            "excerpt_hash": safe_excerpt_hash,
            "excerpt_length": len(safe_excerpt),
            "excerpt": safe_excerpt or None,
            "selection_reason": (
                "project-linked local KB document matched the selected work "
                "request via deterministic keyword overlap"
            ),
            "reason": (
                "project-linked local KB document is within active project "
                "scope and passed the Phase 2B policy filter"
            ),
            "confidence": "high",
            "policy_allowed": True,
            "included_fields": [
                "document.title",
                "document.filename",
                "document.project_id",
                "document.content_hash",
                "document.safe_excerpt_hash",
                "document.safe_excerpt_length",
            ],
            "score": score,
            "attached_rank": attached_rank,
        }

    def _load_project_document_row(
        self,
        *,
        session: Any,
        project_id: int,
        user_id: str,
        doc_id: str,
        doc_type: str,
    ) -> dict[str, Any] | None:
        if doc_type == "generated":
            row = (
                session.query(GeneratedDocument)
                .filter(GeneratedDocument.id == doc_id)
                .filter(GeneratedDocument.project_id == project_id)
                .filter(GeneratedDocument.deleted_at.is_(None))
                .first()
            )
            if row is None:
                return None
            row_user_id = getattr(row, "user_id", None)
            if row_user_id is not None and str(row_user_id) != user_id:
                return None
            title = str(getattr(row, "title", "") or "")
            return {
                "title": title,
                "filename": title,
                "raw_content": str(getattr(row, "content", "") or ""),
                "thread_id": getattr(row, "thread_id", None),
            }

        row = (
            session.query(UploadedDocument)
            .filter(UploadedDocument.id == doc_id)
            .filter(UploadedDocument.project_id == project_id)
            .filter(UploadedDocument.deleted_at.is_(None))
            .first()
        )
        if row is None:
            return None
        if str(getattr(row, "user_id", "") or "") != user_id:
            return None
        return {
            "title": str(getattr(row, "filename", "") or ""),
            "filename": str(getattr(row, "filename", "") or ""),
            "raw_content": str(getattr(row, "parsed_text", "") or ""),
            "thread_id": getattr(row, "thread_id", None),
        }

    def _normalize_project_doc_type(self, value: Any) -> str | None:
        normalized = str(value or "").strip().lower()
        if normalized.startswith("gen"):
            return "generated"
        if normalized.startswith("up"):
            return "uploaded"
        return None

    def _classify_project_kb_source_type(
        self,
        *,
        title: str,
        filename: str,
    ) -> str:
        label = f"{title} {filename}".strip().lower()
        if re.search(r"\badr(?:[-_\s]?\d+)?\b", label):
            return GuardianDelegationContextSourceType.ADR.value
        if "architecture" in label:
            return GuardianDelegationContextSourceType.ARCHITECTURE_DOC.value
        if "protocol" in label:
            return GuardianDelegationContextSourceType.PROTOCOL_DOC.value
        if "task" in label:
            return GuardianDelegationContextSourceType.TASK_FILE.value
        if "linked" in label:
            return GuardianDelegationContextSourceType.LINKED_DOCUMENT.value
        return GuardianDelegationContextSourceType.PROJECT_KB.value

    def _score_project_kb_candidate(
        self,
        *,
        search_terms: list[str],
        title: str,
        filename: str,
        raw_content: str,
        source_type: str,
    ) -> int:
        title_text = f"{title} {filename}".strip().lower()
        content_text = raw_content.lower()
        score = 0
        for term in search_terms:
            if term in title_text:
                score += 3
                continue
            if re.search(rf"\b{re.escape(term)}\b", content_text):
                score += 1
        if score > 0 and source_type != GuardianDelegationContextSourceType.PROJECT_KB.value:
            score += 1
        return score

    def _extract_relevance_terms(self, text: str) -> list[str]:
        terms: list[str] = []
        seen: set[str] = set()
        normalized = str(text or "").lower().replace("/", " ").replace(".", " ")
        for token in re.findall(r"[a-z][a-z0-9_]{2,}", normalized):
            if token in _PROJECT_KB_STOP_WORDS:
                continue
            if token in seen:
                continue
            seen.add(token)
            terms.append(token)
            if len(terms) >= 8:
                break
        return terms

    def _contains_excluded_kb_context(self, text: str) -> bool:
        normalized = str(text or "").strip()
        return any(
            pattern.search(normalized)
            for pattern in _EXCLUDED_KB_CONTEXT_PATTERNS
        )

    def _build_safe_kb_excerpt(self, raw_content: str) -> str:
        normalized = " ".join(str(raw_content or "").split())
        if not normalized:
            return ""
        if len(normalized) <= _MAX_SAFE_KB_EXCERPT_CHARS:
            return normalized
        return normalized[:_MAX_SAFE_KB_EXCERPT_CHARS].rstrip() + "..."

    def _serialize_plan_kb_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": entry["source_type"],
            "source_id": entry["source_id"],
            "title": entry["title"],
            "filename": entry.get("filename"),
            "project_id": entry.get("project_id"),
            "content_hash": entry["content_hash"],
            "excerpt_hash": entry.get("excerpt_hash"),
            "excerpt_length": entry.get("excerpt_length", 0),
            "excerpt": entry.get("excerpt"),
            "rank": entry["rank"],
            "selection_reason": entry["selection_reason"],
        }

    def _serialize_context_basis_kb_entry(
        self, entry: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "source_type": entry["source_type"],
            "source_id": entry["source_id"],
            "included_fields": list(entry["included_fields"]),
            "reason": entry["reason"],
            "confidence": entry["confidence"],
            "policy_allowed": bool(entry["policy_allowed"]),
            "title": entry["title"],
            "filename": entry.get("filename"),
            "project_id": entry.get("project_id"),
            "thread_id": entry.get("thread_id"),
            "content_hash": entry["content_hash"],
            "excerpt_hash": entry.get("excerpt_hash"),
            "excerpt_length": entry.get("excerpt_length", 0),
            "rank": entry["rank"],
            "selection_reason": entry["selection_reason"],
        }

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

        # Phase 3 keeps selected-turn privacy hardening fail-closed for mixed
        # personal/work turns. Require a work-only restatement instead.
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
        visibility_status = str(row.visibility_status or "").strip()
        if visibility_status not in GUARDIAN_DELEGATION_VISIBILITY_STATUSES:
            raise GuardianDelegationValidationError(
                "unknown_visibility_status",
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
            "visibility_status": visibility_status,
            "result_message_id": row.result_message_id,
            "result_delivered_at": self._serialize_timestamp(
                row.result_delivered_at
            ),
            "context_basis": list(row.context_basis or []),
            "plan_summary": dict(row.plan_summary or {}),
        }

    def _require_db(self) -> Any:
        if self.db is None or not hasattr(self.db, "get_session"):
            raise GuardianDelegationDispatchError(
                "guardian_delegation_db_unavailable"
            )
        return self.db

    def _serialize_timestamp(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:  # pragma: no cover - defensive branch
                return str(value)
        return str(value)


__all__ = [
    "build_guardian_delegation_result_delivery_key",
    "build_guardian_delegation_result_message_content",
    "sanitize_guardian_result_files_for_display",
    "sanitize_guardian_validation_results_for_display",
    "GuardianDelegationDispatchError",
    "GuardianDelegationError",
    "GuardianDelegationNotFoundError",
    "GuardianDelegationService",
    "GuardianDelegationValidationError",
]
