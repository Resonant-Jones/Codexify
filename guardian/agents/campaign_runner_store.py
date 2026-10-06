"""Durable persistence helpers for Campaign Runner MVP control-plane state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from guardian.db.models import (
    Campaign,
    CampaignContinuationAuthority,
    CampaignExecutionAttempt,
    CampaignGoal,
)
from guardian.protocol_tokens import (
    CAMPAIGN_EXECUTION_ATTEMPT_STATUSES,
    CAMPAIGN_GOAL_STATUSES,
    CAMPAIGN_STATUSES,
)


class CampaignRunnerStoreError(RuntimeError):
    """Base error for Campaign Runner store operations."""


class CampaignRunnerValidationError(CampaignRunnerStoreError):
    """Raised when Campaign Runner payload validation fails."""

    def __init__(self, message: str, *, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class CampaignRunnerNotFound(CampaignRunnerStoreError):
    """Raised when a requested Campaign Runner entity is not found."""

    def __init__(self, entity: str, identifier: str) -> None:
        super().__init__(f"{entity} not found: {identifier}")
        self.entity = entity
        self.identifier = identifier


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def _coerce_optional_text(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value or None


def _coerce_optional_positive_int(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _coerce_mapping(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _normalize_required_text(raw: Any, field: str, *, max_length: int) -> str:
    if not isinstance(raw, str):
        raise CampaignRunnerValidationError(
            f"invalid required field: {field}",
            reason_code="invalid_continuation_authority_text",
        )
    value = raw.strip()
    if not value or len(value) > max_length:
        raise CampaignRunnerValidationError(
            f"invalid required field: {field}",
            reason_code="invalid_continuation_authority_text",
        )
    return value


def _normalize_authority_scope(raw: Any, field: str) -> list[str]:
    if not isinstance(raw, (list, tuple)) or not raw or len(raw) > 256:
        raise CampaignRunnerValidationError(
            f"invalid authority scope: {field}",
            reason_code="invalid_continuation_authority_scope",
        )
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip() or len(item) > 512:
            raise CampaignRunnerValidationError(
                f"invalid authority scope: {field}",
                reason_code="invalid_continuation_authority_scope",
            )
        value = item.strip()
        if value in values:
            raise CampaignRunnerValidationError(
                f"duplicate authority scope value: {field}",
                reason_code="duplicate_continuation_authority_scope",
            )
        values.append(value)
    return values


def _normalize_authority_json_object(raw: Any, field: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CampaignRunnerValidationError(
            f"invalid authority object: {field}",
            reason_code="invalid_continuation_authority_json",
        )
    try:
        serialized = json.dumps(raw, allow_nan=False)
        normalized = json.loads(serialized)
    except (TypeError, ValueError) as exc:
        raise CampaignRunnerValidationError(
            f"invalid authority object: {field}",
            reason_code="invalid_continuation_authority_json",
        ) from exc
    if normalized != raw or len(serialized) > 32_768:
        raise CampaignRunnerValidationError(
            f"invalid authority object: {field}",
            reason_code="invalid_continuation_authority_json",
        )
    return normalized


def _normalize_authority_timestamp(
    raw: datetime | None,
    field: str,
    *,
    optional: bool = False,
) -> datetime | None:
    if raw is None and optional:
        return None
    if (
        not isinstance(raw, datetime)
        or raw.tzinfo is None
        or raw.utcoffset() is None
    ):
        raise CampaignRunnerValidationError(
            f"invalid authority timestamp: {field}",
            reason_code="invalid_continuation_authority_timestamp",
        )
    return raw.astimezone(UTC)


def _normalize_attempt_status(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    return value or "failed"


def _goal_row_to_dict(row: CampaignGoal) -> dict[str, Any]:
    return {
        "goal_id": row.goal_id,
        "title": row.title,
        "summary": row.summary,
        "status": row.status,
        "source_thread_id": row.source_thread_id,
        "source_message_id": row.source_message_id,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _campaign_row_to_dict(row: Campaign) -> dict[str, Any]:
    return {
        "campaign_id": row.campaign_id,
        "goal_id": row.goal_id,
        "title": row.title,
        "summary": row.summary,
        "status": row.status,
        "source_thread_id": row.source_thread_id,
        "source_message_id": row.source_message_id,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _attempt_row_to_dict(row: CampaignExecutionAttempt) -> dict[str, Any]:
    return {
        "attempt_record_id": row.attempt_record_id,
        "campaign_id": row.campaign_id,
        "goal_id": row.goal_id,
        "work_order_id": row.work_order_id,
        "run_id": row.run_id,
        "attempt_id": row.attempt_id,
        "coding_task_id": row.coding_task_id,
        "adapter_kind": row.adapter_kind,
        "runtime_target": row.runtime_target,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": (
            row.completed_at.isoformat() if row.completed_at else None
        ),
        "failed_at": row.failed_at.isoformat() if row.failed_at else None,
        "error_code": row.error_code,
        "error_message": row.error_message,
        "validation_summary": dict(row.validation_summary or {}),
        "commit_hash": row.commit_hash,
        "delivery_ok": row.delivery_ok,
        "delivered_message_id": row.delivered_message_id,
        "delivery_reason": row.delivery_reason,
        "source_thread_id": row.source_thread_id,
        "source_message_id": row.source_message_id,
        "evidence_json": dict(row.evidence_json or {}),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _continuation_authority_row_to_dict(
    row: CampaignContinuationAuthority,
) -> dict[str, Any]:
    return {
        "authority_id": row.authority_id,
        "campaign_id": row.campaign_id,
        "revision": row.revision,
        "is_latest": row.is_latest,
        "approval_event_id": row.approval_event_id,
        "approved_by_actor_id": row.approved_by_actor_id,
        "approved_at": row.approved_at.isoformat(),
        "allowed_task_classes": list(row.allowed_task_classes or []),
        "allowed_execution_lanes": list(row.allowed_execution_lanes or []),
        "repository_scope": list(row.repository_scope or []),
        "workspace_scope": list(row.workspace_scope or []),
        "validation_classes": list(row.validation_classes or []),
        "proof_classes": list(row.proof_classes or []),
        "spend_posture": row.spend_posture,
        "spend_limits": dict(row.spend_limits or {}),
        "retry_permitted": row.retry_permitted,
        "retry_ceiling": row.retry_ceiling,
        "downstream_dispatch_permitted": row.downstream_dispatch_permitted,
        "stop_reasons": list(row.stop_reasons or []),
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "superseded_at": (
            row.superseded_at.isoformat() if row.superseded_at else None
        ),
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "revoked_by_actor_id": row.revoked_by_actor_id,
        "revocation_reason": row.revocation_reason,
        "created_at": row.created_at.isoformat(),
    }


@dataclass
class CampaignRunnerStore:
    """Postgres-backed store for Campaign Runner MVP entities."""

    db: Any

    def create_goal(
        self,
        *,
        title: str,
        summary: str | None = None,
        status: str = "active",
        source_thread_id: str | None = None,
        source_message_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_title = str(title or "").strip()
        if not normalized_title:
            raise CampaignRunnerValidationError(
                "missing required field: title",
                reason_code="missing_goal_title",
            )
        normalized_status = str(status or "").strip().lower()
        if normalized_status not in CAMPAIGN_GOAL_STATUSES:
            raise CampaignRunnerValidationError(
                f"invalid campaign goal status: {normalized_status}",
                reason_code="invalid_campaign_goal_status",
            )

        now = _utc_now()
        with self.db.get_session() as session:
            row = CampaignGoal(
                goal_id=_new_id("goal"),
                title=normalized_title,
                summary=_coerce_optional_text(summary),
                status=normalized_status,
                source_thread_id=_coerce_optional_text(source_thread_id),
                source_message_id=_coerce_optional_text(source_message_id),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _goal_row_to_dict(row)

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        with self.db.get_session() as session:
            row = session.query(CampaignGoal).filter_by(goal_id=goal_id).first()
            return _goal_row_to_dict(row) if row is not None else None

    def create_campaign(
        self,
        *,
        goal_id: str,
        title: str,
        summary: str | None = None,
        status: str = "active",
        campaign_id: str | None = None,
        source_thread_id: str | None = None,
        source_message_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_goal_id = str(goal_id or "").strip()
        normalized_title = str(title or "").strip()
        normalized_status = str(status or "").strip().lower()
        if not normalized_goal_id:
            raise CampaignRunnerValidationError(
                "missing required field: goal_id",
                reason_code="missing_campaign_goal_id",
            )
        if not normalized_title:
            raise CampaignRunnerValidationError(
                "missing required field: title",
                reason_code="missing_campaign_title",
            )
        if normalized_status not in CAMPAIGN_STATUSES:
            raise CampaignRunnerValidationError(
                f"invalid campaign status: {normalized_status}",
                reason_code="invalid_campaign_status",
            )

        now = _utc_now()
        with self.db.get_session() as session:
            goal = (
                session.query(CampaignGoal)
                .filter_by(goal_id=normalized_goal_id)
                .first()
            )
            if goal is None:
                raise CampaignRunnerNotFound("goal", normalized_goal_id)

            row = Campaign(
                campaign_id=_coerce_optional_text(campaign_id)
                or _new_id("campaign"),
                goal_id=normalized_goal_id,
                title=normalized_title,
                summary=_coerce_optional_text(summary),
                status=normalized_status,
                source_thread_id=_coerce_optional_text(source_thread_id),
                source_message_id=_coerce_optional_text(source_message_id),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _campaign_row_to_dict(row)

    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        with self.db.get_session() as session:
            row = (
                session.query(Campaign)
                .filter_by(campaign_id=campaign_id)
                .first()
            )
            return _campaign_row_to_dict(row) if row is not None else None

    def record_human_approved_continuation_authority(
        self,
        *,
        campaign_id: str,
        approval_event_id: str,
        approved_by_actor_id: str,
        approved_at: datetime,
        allowed_task_classes: list[str],
        allowed_execution_lanes: list[str],
        repository_scope: list[str],
        workspace_scope: list[str],
        validation_classes: list[str],
        proof_classes: list[str],
        spend_posture: str,
        spend_limits: dict[str, Any],
        retry_permitted: bool,
        retry_ceiling: int,
        downstream_dispatch_permitted: bool,
        stop_reasons: list[str],
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Persist an authenticated human approval envelope; never dispatch work.

        Callers must obtain ``approval_event_id`` and actor identity from the
        Guardian-authenticated human approval boundary. This store method is
        intentionally not exposed as an HTTP endpoint.
        """
        normalized_campaign_id = _normalize_required_text(
            campaign_id, "campaign_id", max_length=128
        )
        normalized_approval_event_id = _normalize_required_text(
            approval_event_id, "approval_event_id", max_length=128
        )
        normalized_actor_id = _normalize_required_text(
            approved_by_actor_id, "approved_by_actor_id", max_length=255
        )
        normalized_approved_at = _normalize_authority_timestamp(
            approved_at, "approved_at"
        )
        normalized_expires_at = _normalize_authority_timestamp(
            expires_at, "expires_at", optional=True
        )
        now = _utc_now()
        if normalized_approved_at is None or normalized_approved_at > now:
            raise CampaignRunnerValidationError(
                "approval timestamp must not be in the future",
                reason_code="invalid_continuation_authority_timestamp",
            )
        normalized_task_classes = _normalize_authority_scope(
            allowed_task_classes, "allowed_task_classes"
        )
        normalized_execution_lanes = _normalize_authority_scope(
            allowed_execution_lanes, "allowed_execution_lanes"
        )
        normalized_repository_scope = _normalize_authority_scope(
            repository_scope, "repository_scope"
        )
        normalized_workspace_scope = _normalize_authority_scope(
            workspace_scope, "workspace_scope"
        )
        normalized_validation_classes = _normalize_authority_scope(
            validation_classes, "validation_classes"
        )
        normalized_proof_classes = _normalize_authority_scope(
            proof_classes, "proof_classes"
        )
        normalized_spend_posture = _normalize_required_text(
            spend_posture, "spend_posture", max_length=64
        )
        normalized_spend_limits = _normalize_authority_json_object(
            spend_limits, "spend_limits"
        )
        normalized_stop_reasons = _normalize_authority_scope(
            stop_reasons, "stop_reasons"
        )
        if type(retry_permitted) is not bool or type(
            downstream_dispatch_permitted
        ) is not bool:
            raise CampaignRunnerValidationError(
                "authority permission fields must be booleans",
                reason_code="invalid_continuation_authority_permission",
            )
        if type(retry_ceiling) is not int or retry_ceiling < 0:
            raise CampaignRunnerValidationError(
                "retry_ceiling must be a non-negative integer",
                reason_code="invalid_continuation_authority_retry_ceiling",
            )
        if retry_permitted != (retry_ceiling > 0):
            raise CampaignRunnerValidationError(
                "retry permission and retry ceiling must agree",
                reason_code="invalid_continuation_authority_retry_ceiling",
            )

        expected_envelope = {
            "campaign_id": normalized_campaign_id,
            "approval_event_id": normalized_approval_event_id,
            "approved_by_actor_id": normalized_actor_id,
            "approved_at": normalized_approved_at,
            "allowed_task_classes": normalized_task_classes,
            "allowed_execution_lanes": normalized_execution_lanes,
            "repository_scope": normalized_repository_scope,
            "workspace_scope": normalized_workspace_scope,
            "validation_classes": normalized_validation_classes,
            "proof_classes": normalized_proof_classes,
            "spend_posture": normalized_spend_posture,
            "spend_limits": normalized_spend_limits,
            "retry_permitted": retry_permitted,
            "retry_ceiling": retry_ceiling,
            "downstream_dispatch_permitted": downstream_dispatch_permitted,
            "stop_reasons": normalized_stop_reasons,
            "expires_at": normalized_expires_at,
        }

        with self.db.get_session() as session:
            campaign = (
                session.query(Campaign)
                .filter_by(campaign_id=normalized_campaign_id)
                .with_for_update()
                .first()
            )
            if campaign is None:
                raise CampaignRunnerNotFound("campaign", normalized_campaign_id)

            existing_approval = (
                session.query(CampaignContinuationAuthority)
                .filter_by(approval_event_id=normalized_approval_event_id)
                .first()
            )
            if existing_approval is not None:
                if all(
                    getattr(existing_approval, key) == value
                    for key, value in expected_envelope.items()
                ):
                    return _continuation_authority_row_to_dict(existing_approval)
                raise CampaignRunnerValidationError(
                    "approval event is already bound to a different envelope",
                    reason_code="continuation_authority_approval_event_conflict",
                )

            if normalized_expires_at is not None and normalized_expires_at <= now:
                raise CampaignRunnerValidationError(
                    "authority expiry must be in the future",
                    reason_code="expired_continuation_authority",
                )

            current = (
                session.query(CampaignContinuationAuthority)
                .filter_by(campaign_id=normalized_campaign_id, is_latest=True)
                .with_for_update()
                .first()
            )
            if current is not None:
                is_unexpired = (
                    current.expires_at is None or current.expires_at > now
                )
                if current.revoked_at is None and is_unexpired:
                    raise CampaignRunnerValidationError(
                        "Campaign already has an unexpired, unrevoked "
                        "continuation authority",
                        reason_code="continuation_authority_already_active",
                    )
                current.is_latest = False
                if current.revoked_at is None:
                    current.superseded_at = now
                session.flush()

            current_revision = (
                session.query(func.max(CampaignContinuationAuthority.revision))
                .filter_by(campaign_id=normalized_campaign_id)
                .scalar()
                or 0
            )
            row = CampaignContinuationAuthority(
                authority_id=_new_id("continuation"),
                campaign_id=normalized_campaign_id,
                revision=current_revision + 1,
                is_latest=True,
                **expected_envelope,
                created_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _continuation_authority_row_to_dict(row)

    def get_continuation_authority(
        self, authority_id: str
    ) -> dict[str, Any] | None:
        normalized_authority_id = _coerce_optional_text(authority_id)
        if not normalized_authority_id:
            return None
        with self.db.get_session() as session:
            row = (
                session.query(CampaignContinuationAuthority)
                .filter_by(authority_id=normalized_authority_id)
                .first()
            )
            return (
                _continuation_authority_row_to_dict(row)
                if row is not None
                else None
            )

    def list_continuation_authorities_for_campaign(
        self,
        campaign_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        normalized_campaign_id = _coerce_optional_text(campaign_id)
        if not normalized_campaign_id:
            return []
        bounded_limit = max(1, min(int(limit or 100), 500))
        with self.db.get_session() as session:
            rows = (
                session.query(CampaignContinuationAuthority)
                .filter_by(campaign_id=normalized_campaign_id)
                .order_by(CampaignContinuationAuthority.revision.desc())
                .limit(bounded_limit)
                .all()
            )
            return [_continuation_authority_row_to_dict(row) for row in rows]

    def revoke_continuation_authority(
        self,
        authority_id: str,
        *,
        revoked_by_actor_id: str,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> dict[str, Any]:
        normalized_authority_id = _normalize_required_text(
            authority_id, "authority_id", max_length=64
        )
        normalized_actor_id = _normalize_required_text(
            revoked_by_actor_id, "revoked_by_actor_id", max_length=255
        )
        normalized_reason = _normalize_required_text(
            reason, "reason", max_length=4000
        )
        normalized_revoked_at = _normalize_authority_timestamp(
            revoked_at or _utc_now(), "revoked_at"
        )
        if normalized_revoked_at is None or normalized_revoked_at > _utc_now():
            raise CampaignRunnerValidationError(
                "revocation timestamp must not be in the future",
                reason_code="invalid_continuation_authority_timestamp",
            )

        with self.db.get_session() as session:
            authority = (
                session.query(CampaignContinuationAuthority)
                .filter_by(authority_id=normalized_authority_id)
                .first()
            )
            if authority is None:
                raise CampaignRunnerNotFound(
                    "continuation_authority", normalized_authority_id
                )
            session.query(Campaign).filter_by(
                campaign_id=authority.campaign_id
            ).with_for_update().first()
            row = (
                session.query(CampaignContinuationAuthority)
                .filter_by(authority_id=normalized_authority_id)
                .with_for_update()
                .first()
            )
            if row is None:
                raise CampaignRunnerNotFound(
                    "continuation_authority", normalized_authority_id
                )
            if row.revoked_at is not None:
                return _continuation_authority_row_to_dict(row)
            if normalized_revoked_at < row.approved_at:
                raise CampaignRunnerValidationError(
                    "revocation timestamp precedes approval",
                    reason_code="invalid_continuation_authority_timestamp",
                )

            row.revoked_at = normalized_revoked_at
            row.revoked_by_actor_id = normalized_actor_id
            row.revocation_reason = normalized_reason
            session.commit()
            session.refresh(row)
            return _continuation_authority_row_to_dict(row)

    def record_execution_attempt(
        self,
        *,
        run_id: str,
        attempt_id: str,
        status: str,
        coding_task_id: str | None = None,
        campaign_id: str | None = None,
        goal_id: str | None = None,
        work_order_id: str | None = None,
        adapter_kind: str | None = None,
        runtime_target: str | None = None,
        started_at: datetime | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        validation_summary: dict[str, Any] | None = None,
        commit_hash: str | None = None,
        delivery_ok: bool | None = None,
        delivered_message_id: int | None = None,
        delivery_reason: str | None = None,
        source_thread_id: int | None = None,
        source_message_id: int | None = None,
        evidence_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_run_id = str(run_id or "").strip()
        normalized_attempt_id = str(attempt_id or "").strip()
        normalized_status = _normalize_attempt_status(status)

        if not normalized_run_id:
            raise CampaignRunnerValidationError(
                "missing required field: run_id",
                reason_code="missing_attempt_run_id",
            )
        if not normalized_attempt_id:
            raise CampaignRunnerValidationError(
                "missing required field: attempt_id",
                reason_code="missing_attempt_id",
            )
        if normalized_status not in CAMPAIGN_EXECUTION_ATTEMPT_STATUSES:
            raise CampaignRunnerValidationError(
                f"invalid attempt status: {normalized_status}",
                reason_code="invalid_attempt_status",
            )

        now = _utc_now()
        normalized_campaign_id = _coerce_optional_text(campaign_id)
        normalized_goal_id = _coerce_optional_text(goal_id)
        normalized_work_order_id = _coerce_optional_text(work_order_id)
        normalized_started_at = started_at or now

        with self.db.get_session() as session:
            row = (
                session.query(CampaignExecutionAttempt)
                .filter_by(
                    run_id=normalized_run_id,
                    attempt_id=normalized_attempt_id,
                )
                .first()
            )
            if row is None:
                row = CampaignExecutionAttempt(
                    attempt_record_id=_new_id("attemptrec"),
                    run_id=normalized_run_id,
                    attempt_id=normalized_attempt_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

            row.campaign_id = normalized_campaign_id
            row.goal_id = normalized_goal_id
            row.work_order_id = normalized_work_order_id
            row.coding_task_id = _coerce_optional_text(coding_task_id)
            row.adapter_kind = _coerce_optional_text(adapter_kind)
            row.runtime_target = _coerce_optional_text(runtime_target)
            row.status = normalized_status
            row.started_at = row.started_at or normalized_started_at
            row.error_code = _coerce_optional_text(error_code)
            row.error_message = _coerce_optional_text(error_message)
            row.validation_summary = _coerce_mapping(validation_summary)
            row.commit_hash = _coerce_optional_text(commit_hash)
            row.delivery_ok = delivery_ok
            row.delivered_message_id = _coerce_optional_positive_int(
                delivered_message_id
            )
            row.delivery_reason = _coerce_optional_text(delivery_reason)
            row.source_thread_id = _coerce_optional_positive_int(
                source_thread_id
            )
            row.source_message_id = _coerce_optional_positive_int(
                source_message_id
            )
            row.evidence_json = _coerce_mapping(evidence_json)

            if normalized_status == "failed":
                row.failed_at = now
                row.completed_at = None
            elif normalized_status in {"succeeded", "cancelled"}:
                row.completed_at = now
                if normalized_status != "cancelled":
                    row.failed_at = None

            row.updated_at = now
            session.commit()
            session.refresh(row)
            return _attempt_row_to_dict(row)

    def list_attempts_for_campaign(
        self,
        campaign_id: str,
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(int(limit or 200), 500))
        with self.db.get_session() as session:
            rows = (
                session.query(CampaignExecutionAttempt)
                .filter(CampaignExecutionAttempt.campaign_id == campaign_id)
                .order_by(
                    CampaignExecutionAttempt.created_at.desc(),
                    CampaignExecutionAttempt.attempt_record_id.desc(),
                )
                .limit(bounded_limit)
                .all()
            )
            return [_attempt_row_to_dict(row) for row in rows]

    def latest_attempt_by_work_order(
        self, campaign_id: str
    ) -> dict[str, dict[str, Any]]:
        with self.db.get_session() as session:
            rows = (
                session.query(CampaignExecutionAttempt)
                .filter(CampaignExecutionAttempt.campaign_id == campaign_id)
                .order_by(
                    CampaignExecutionAttempt.work_order_id.asc(),
                    CampaignExecutionAttempt.created_at.desc(),
                    CampaignExecutionAttempt.attempt_record_id.desc(),
                )
                .all()
            )

            by_work_order: dict[str, dict[str, Any]] = {}
            for row in rows:
                work_order_id = _coerce_optional_text(row.work_order_id)
                if not work_order_id or work_order_id in by_work_order:
                    continue
                by_work_order[work_order_id] = _attempt_row_to_dict(row)
            return by_work_order


__all__ = [
    "CampaignRunnerNotFound",
    "CampaignRunnerStore",
    "CampaignRunnerStoreError",
    "CampaignRunnerValidationError",
]
