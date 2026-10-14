"""Durable persistence helpers for Campaign Runner MVP control-plane state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from guardian.agents.campaign_continuation_authority import (
    CampaignContinuationAuthorityEnvelope,
)
from guardian.db.models import (
    Campaign,
    CampaignContinuationAuthorityRecord,
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


def _same_optional_timestamp(
    left: datetime | None, right: datetime | None
) -> bool:
    if left is None or right is None:
        return left is right
    if left.tzinfo is None:
        left = left.replace(tzinfo=UTC)
    if right.tzinfo is None:
        right = right.replace(tzinfo=UTC)
    return left.astimezone(UTC) == right.astimezone(UTC)


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
    row: CampaignContinuationAuthorityRecord,
    *,
    campaign_status: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = now or _utc_now()
    expires_at = row.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    expired = expires_at is not None and expires_at <= checked_at
    revoked = row.revoked_at is not None
    terminal_campaign = campaign_status in {"completed", "archived"}
    return {
        "authority_id": row.authority_id,
        "campaign_id": row.campaign_id,
        "envelope": dict(row.envelope_json or {}),
        "approved_by_actor_id": row.approved_by_actor_id,
        "approved_at": row.approved_at.isoformat(),
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "revoked_by_actor_id": row.revoked_by_actor_id,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "revocation_reason": row.revocation_reason,
        "configured": True,
        "revoked": revoked,
        "expired": expired,
        "campaign_terminal": terminal_campaign,
        "currently_valid": not (revoked or expired or terminal_campaign),
        "automatic_retry_execution_enabled": False,
        "automatic_downstream_dispatch_enabled": False,
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

    def approve_continuation_authority(
        self,
        *,
        campaign_id: str,
        envelope: dict[str, Any],
        approved_by_actor_id: str,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        normalized_campaign_id = str(campaign_id or "").strip()
        normalized_actor_id = str(approved_by_actor_id or "").strip()
        if not normalized_campaign_id:
            raise CampaignRunnerValidationError(
                "missing required field: campaign_id",
                reason_code="missing_continuation_authority_campaign_id",
            )
        if not normalized_actor_id:
            raise CampaignRunnerValidationError(
                "missing authenticated approver identity",
                reason_code="missing_continuation_authority_actor",
            )
        try:
            validated_envelope = CampaignContinuationAuthorityEnvelope.model_validate(
                envelope
            )
        except ValidationError as exc:
            raise CampaignRunnerValidationError(
                "invalid Campaign Continuation Authority envelope",
                reason_code="invalid_continuation_authority_envelope",
            ) from exc

        now = _utc_now()
        normalized_expiry = expires_at
        if normalized_expiry is not None:
            if (
                normalized_expiry.tzinfo is None
                or normalized_expiry.utcoffset() is None
            ):
                raise CampaignRunnerValidationError(
                    "expires_at must include a timezone",
                    reason_code="invalid_continuation_authority_expiry",
                )
            normalized_expiry = normalized_expiry.astimezone(UTC)
            if normalized_expiry <= now:
                raise CampaignRunnerValidationError(
                    "expires_at must be in the future",
                    reason_code="invalid_continuation_authority_expiry",
                )

        normalized_envelope = validated_envelope.model_dump(mode="json")
        with self.db.get_session() as session:
            campaign = (
                session.query(Campaign)
                .filter_by(campaign_id=normalized_campaign_id)
                .with_for_update()
                .first()
            )
            if campaign is None:
                raise CampaignRunnerNotFound("campaign", normalized_campaign_id)
            if campaign.status in {"completed", "archived"}:
                raise CampaignRunnerValidationError(
                    "continuation authority cannot be approved for a terminal Campaign",
                    reason_code="terminal_campaign_continuation_authority",
                )

            existing = (
                session.query(CampaignContinuationAuthorityRecord)
                .filter_by(campaign_id=normalized_campaign_id)
                .filter(CampaignContinuationAuthorityRecord.revoked_at.is_(None))
                .first()
            )
            if existing is not None:
                if (
                    existing.envelope_json == normalized_envelope
                    and existing.approved_by_actor_id == normalized_actor_id
                    and _same_optional_timestamp(
                        existing.expires_at, normalized_expiry
                    )
                ):
                    return _continuation_authority_row_to_dict(
                        existing, campaign_status=campaign.status, now=now
                    )
                raise CampaignRunnerValidationError(
                    "an unrevoked continuation authority already exists; "
                    "revoke it before replacement",
                    reason_code="continuation_authority_already_exists",
                )

            row = CampaignContinuationAuthorityRecord(
                authority_id=_new_id("cauth"),
                campaign_id=normalized_campaign_id,
                envelope_json=normalized_envelope,
                approved_by_actor_id=normalized_actor_id,
                approved_at=now,
                expires_at=normalized_expiry,
                created_at=now,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                existing = (
                    session.query(CampaignContinuationAuthorityRecord)
                    .filter_by(campaign_id=normalized_campaign_id)
                    .filter(
                        CampaignContinuationAuthorityRecord.revoked_at.is_(None)
                    )
                    .first()
                )
                if (
                    existing is not None
                    and existing.envelope_json == normalized_envelope
                    and existing.approved_by_actor_id == normalized_actor_id
                    and _same_optional_timestamp(
                        existing.expires_at, normalized_expiry
                    )
                ):
                    return _continuation_authority_row_to_dict(
                        existing, campaign_status=campaign.status, now=now
                    )
                raise CampaignRunnerValidationError(
                    "an unrevoked continuation authority already exists; "
                    "revoke it before replacement",
                    reason_code="continuation_authority_already_exists",
                ) from exc
            session.refresh(row)
            return _continuation_authority_row_to_dict(
                row, campaign_status=campaign.status, now=now
            )

    def list_continuation_authorities(
        self, campaign_id: str
    ) -> list[dict[str, Any]]:
        normalized_campaign_id = str(campaign_id or "").strip()
        with self.db.get_session() as session:
            campaign = (
                session.query(Campaign)
                .filter_by(campaign_id=normalized_campaign_id)
                .first()
            )
            if campaign is None:
                raise CampaignRunnerNotFound("campaign", normalized_campaign_id)
            rows = (
                session.query(CampaignContinuationAuthorityRecord)
                .filter_by(campaign_id=normalized_campaign_id)
                .order_by(
                    CampaignContinuationAuthorityRecord.approved_at.desc(),
                    CampaignContinuationAuthorityRecord.authority_id.desc(),
                )
                .all()
            )
            now = _utc_now()
            return [
                _continuation_authority_row_to_dict(
                    row, campaign_status=campaign.status, now=now
                )
                for row in rows
            ]

    def revoke_continuation_authority(
        self,
        *,
        campaign_id: str,
        authority_id: str,
        revoked_by_actor_id: str,
        reason: str,
    ) -> dict[str, Any]:
        normalized_campaign_id = str(campaign_id or "").strip()
        normalized_authority_id = str(authority_id or "").strip()
        normalized_actor_id = str(revoked_by_actor_id or "").strip()
        normalized_reason = str(reason or "").strip()
        if not normalized_actor_id or not normalized_reason:
            raise CampaignRunnerValidationError(
                "revocation requires an authenticated actor and reason",
                reason_code="invalid_continuation_authority_revocation",
            )

        with self.db.get_session() as session:
            campaign = (
                session.query(Campaign)
                .filter_by(campaign_id=normalized_campaign_id)
                .first()
            )
            if campaign is None:
                raise CampaignRunnerNotFound("campaign", normalized_campaign_id)
            row = (
                session.query(CampaignContinuationAuthorityRecord)
                .filter_by(
                    campaign_id=normalized_campaign_id,
                    authority_id=normalized_authority_id,
                )
                .with_for_update()
                .first()
            )
            if row is None:
                raise CampaignRunnerNotFound(
                    "continuation authority", normalized_authority_id
                )
            if row.revoked_at is None:
                now = _utc_now()
                row.revoked_by_actor_id = normalized_actor_id
                row.revoked_at = now
                row.revocation_reason = normalized_reason
                session.commit()
                session.refresh(row)
            return _continuation_authority_row_to_dict(
                row, campaign_status=campaign.status
            )

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
