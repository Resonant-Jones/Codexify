"""Persistence helpers for agent orchestration entities."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from guardian.db.models import (
    AgentConfidenceReport,
    AgentDeployment,
    AgentEscalation,
    AgentEvent,
    AgentRun,
    AgentRunArtifact,
    AgentRunAttempt,
    AgentRunStep,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_external_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def deterministic_worktree_id(
    *, deployment_id: str, run_id: str, step_index: int
) -> str:
    seed = f"{deployment_id}:{run_id}:{step_index}".encode()
    digest = hashlib.sha256(seed).hexdigest()
    return digest[:24]


@dataclass
class AgentStore:
    """Durable store with SQLAlchemy-backed persistence and in-memory fallback."""

    db: Any | None = None

    def __post_init__(self) -> None:
        self._mem_deployments: dict[str, dict[str, Any]] = {}
        self._mem_runs: dict[str, dict[str, Any]] = {}
        self._mem_steps: dict[tuple[str, int], dict[str, Any]] = {}
        self._mem_attempts: list[dict[str, Any]] = []
        self._mem_artifacts: list[dict[str, Any]] = []
        self._mem_confidence: list[dict[str, Any]] = []
        self._mem_escalations: list[dict[str, Any]] = []

    def configure_db(self, db: Any | None) -> None:
        self.db = db

    def _has_db(self) -> bool:
        return bool(self.db is not None and hasattr(self.db, "get_session"))

    def create_deployment(
        self,
        *,
        flow_id: str,
        thread_id: int | None,
        spec_json: dict[str, Any],
        spec_hash: str,
        trust_state: str = "supervised",
    ) -> dict[str, Any]:
        deployment_id = _new_external_id("dep")
        now = _utc_now()
        if self._has_db():
            with self.db.get_session() as session:
                row = AgentDeployment(
                    deployment_id=deployment_id,
                    flow_id=flow_id,
                    thread_id=thread_id,
                    spec_json=spec_json or {},
                    spec_hash=spec_hash,
                    trust_state=trust_state,
                    unlocked_for_unsupervised=(trust_state == "unlocked"),
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.commit()
                return {
                    "deployment_id": row.deployment_id,
                    "flow_id": row.flow_id,
                    "thread_id": row.thread_id,
                    "trust_state": row.trust_state,
                    "status": row.status,
                    "spec_hash": row.spec_hash,
                }

        data = {
            "deployment_id": deployment_id,
            "flow_id": flow_id,
            "thread_id": thread_id,
            "spec_json": dict(spec_json or {}),
            "spec_hash": spec_hash,
            "trust_state": trust_state,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._mem_deployments[deployment_id] = data
        return data

    def get_deployment(self, deployment_id: str) -> dict[str, Any] | None:
        if self._has_db():
            with self.db.get_session() as session:
                row = (
                    session.query(AgentDeployment)
                    .filter_by(deployment_id=deployment_id)
                    .first()
                )
                if row is None:
                    return None
                return {
                    "deployment_id": row.deployment_id,
                    "flow_id": row.flow_id,
                    "thread_id": row.thread_id,
                    "trust_state": row.trust_state,
                    "status": row.status,
                    "spec_hash": row.spec_hash,
                }
        return self._mem_deployments.get(deployment_id)

    def create_run(
        self,
        *,
        deployment_id: str,
        thread_id: int | None,
        runtime_target: str = "container",
        rollback_mode: str = "auto",
        status: str = "running",
        worktree_id: str | None = None,
        worktree_path: str | None = None,
    ) -> dict[str, Any]:
        run_id = _new_external_id("run")
        now = _utc_now()
        if self._has_db():
            with self.db.get_session() as session:
                dep_row = (
                    session.query(AgentDeployment)
                    .filter_by(deployment_id=deployment_id)
                    .first()
                )
                if dep_row is None:
                    raise ValueError(f"Unknown deployment_id '{deployment_id}'")
                row = AgentRun(
                    run_id=run_id,
                    deployment_id=dep_row.id,
                    thread_id=thread_id,
                    status=status,
                    runtime_target=runtime_target,
                    rollback_mode=rollback_mode,
                    worktree_id=worktree_id,
                    worktree_path=worktree_path,
                    started_at=now if status == "running" else None,
                    created_at=now,
                )
                session.add(row)
                session.commit()
                return {
                    "run_id": row.run_id,
                    "deployment_id": deployment_id,
                    "thread_id": row.thread_id,
                    "status": row.status,
                    "runtime_target": row.runtime_target,
                    "worktree_id": row.worktree_id,
                    "worktree_path": row.worktree_path,
                }

        data = {
            "run_id": run_id,
            "deployment_id": deployment_id,
            "thread_id": thread_id,
            "status": status,
            "runtime_target": runtime_target,
            "rollback_mode": rollback_mode,
            "worktree_id": worktree_id,
            "worktree_path": worktree_path,
            "created_at": now.isoformat(),
            "started_at": now.isoformat() if status == "running" else None,
        }
        self._mem_runs[run_id] = data
        return data

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        if self._has_db():
            with self.db.get_session() as session:
                row = session.query(AgentRun).filter_by(run_id=run_id).first()
                if row is None:
                    return None
                dep = (
                    session.query(AgentDeployment)
                    .filter_by(id=row.deployment_id)
                    .first()
                )
                return {
                    "run_id": row.run_id,
                    "deployment_id": dep.deployment_id if dep else None,
                    "thread_id": row.thread_id,
                    "status": row.status,
                    "runtime_target": row.runtime_target,
                    "rollback_applied": bool(row.rollback_applied),
                    "rollback_reason": row.rollback_reason,
                    "worktree_id": row.worktree_id,
                    "worktree_path": row.worktree_path,
                }
        return self._mem_runs.get(run_id)

    def list_runs_for_thread(self, thread_id: int) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                rows = (
                    session.query(AgentRun)
                    .filter_by(thread_id=thread_id)
                    .order_by(AgentRun.created_at.desc())
                    .all()
                )
                return [
                    {
                        "run_id": row.run_id,
                        "thread_id": row.thread_id,
                        "status": row.status,
                        "runtime_target": row.runtime_target,
                        "worktree_id": row.worktree_id,
                        "worktree_path": row.worktree_path,
                    }
                    for row in rows
                ]
        items = [
            value
            for value in self._mem_runs.values()
            if value.get("thread_id") == thread_id
        ]
        return sorted(
            items,
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )

    def update_run_status(
        self,
        *,
        run_id: str,
        status: str,
        error: str | None = None,
        rollback_applied: bool | None = None,
        rollback_reason: str | None = None,
    ) -> None:
        now = _utc_now()
        if self._has_db():
            with self.db.get_session() as session:
                row = session.query(AgentRun).filter_by(run_id=run_id).first()
                if row is None:
                    return
                row.status = status
                if error is not None:
                    row.error = error
                if rollback_applied is not None:
                    row.rollback_applied = rollback_applied
                if rollback_reason is not None:
                    row.rollback_reason = rollback_reason
                if status in {"failed", "succeeded", "canceled", "escalated"}:
                    row.ended_at = now
                session.commit()
                return

        item = self._mem_runs.get(run_id)
        if item is None:
            return
        item["status"] = status
        if error is not None:
            item["error"] = error
        if rollback_applied is not None:
            item["rollback_applied"] = rollback_applied
        if rollback_reason is not None:
            item["rollback_reason"] = rollback_reason
        if status in {"failed", "succeeded", "canceled", "escalated"}:
            item["ended_at"] = now.isoformat()

    def create_step(
        self,
        *,
        run_id: str,
        step_index: int,
        step_id: str,
        primitive: str,
        is_mutating: bool,
    ) -> dict[str, Any]:
        now = _utc_now()
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    raise ValueError(f"Unknown run_id '{run_id}'")
                row = AgentRunStep(
                    run_id=run_row.id,
                    step_index=step_index,
                    step_id=step_id,
                    primitive=primitive,
                    is_mutating=is_mutating,
                    status="running",
                    started_at=now,
                )
                session.add(row)
                session.commit()
                return {
                    "run_id": run_id,
                    "step_index": row.step_index,
                    "step_id": row.step_id,
                    "status": row.status,
                }

        data = {
            "run_id": run_id,
            "step_index": step_index,
            "step_id": step_id,
            "primitive": primitive,
            "is_mutating": is_mutating,
            "status": "running",
            "started_at": now.isoformat(),
        }
        self._mem_steps[(run_id, step_index)] = data
        return data

    def update_step_status(
        self,
        *,
        run_id: str,
        step_index: int,
        status: str,
        schema_valid: bool | None = None,
        spec_alignment_ok: bool | None = None,
        tests_passed: bool | None = None,
    ) -> None:
        now = _utc_now()
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return
                row = (
                    session.query(AgentRunStep)
                    .filter_by(run_id=run_row.id, step_index=step_index)
                    .first()
                )
                if row is None:
                    return
                row.status = status
                if schema_valid is not None:
                    row.schema_valid = schema_valid
                if spec_alignment_ok is not None:
                    row.spec_alignment_ok = spec_alignment_ok
                if tests_passed is not None:
                    row.tests_passed = tests_passed
                if status in {"succeeded", "failed", "escalated", "canceled"}:
                    row.ended_at = now
                session.commit()
                return

        item = self._mem_steps.get((run_id, step_index))
        if item is None:
            return
        item["status"] = status
        if schema_valid is not None:
            item["schema_valid"] = schema_valid
        if spec_alignment_ok is not None:
            item["spec_alignment_ok"] = spec_alignment_ok
        if tests_passed is not None:
            item["tests_passed"] = tests_passed
        if status in {"succeeded", "failed", "escalated", "canceled"}:
            item["ended_at"] = now.isoformat()

    def add_attempt(
        self,
        *,
        run_id: str,
        step_index: int,
        attempt_index: int,
        status: str,
        fail_count: int,
        fail_signature: str,
        diff_added: int,
        diff_deleted: int,
        error_category: str,
        progress_made: bool,
        stderr_excerpt: str | None = None,
    ) -> dict[str, Any]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    raise ValueError(f"Unknown run_id '{run_id}'")
                step_row = (
                    session.query(AgentRunStep)
                    .filter_by(run_id=run_row.id, step_index=step_index)
                    .first()
                )
                if step_row is None:
                    raise ValueError(
                        f"Unknown step run_id='{run_id}' step_index={step_index}"
                    )
                row = AgentRunAttempt(
                    run_step_id=step_row.id,
                    attempt_index=attempt_index,
                    status=status,
                    fail_count=fail_count,
                    fail_signature=fail_signature,
                    diff_added=diff_added,
                    diff_deleted=diff_deleted,
                    error_category=error_category,
                    progress_made=progress_made,
                    stderr_excerpt=stderr_excerpt,
                    ended_at=_utc_now(),
                )
                session.add(row)
                session.commit()
                return {
                    "run_id": run_id,
                    "step_index": step_index,
                    "attempt_index": attempt_index,
                    "status": status,
                    "id": row.id,
                }

        item = {
            "run_id": run_id,
            "step_index": step_index,
            "attempt_index": attempt_index,
            "status": status,
            "fail_count": fail_count,
            "fail_signature": fail_signature,
            "diff_added": diff_added,
            "diff_deleted": diff_deleted,
            "error_category": error_category,
            "progress_made": progress_made,
            "stderr_excerpt": stderr_excerpt,
        }
        self._mem_attempts.append(item)
        return item

    def add_artifact(
        self,
        *,
        run_id: str,
        step_index: int | None,
        artifact_type: str,
        content_json: dict[str, Any],
    ) -> None:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return
                step_row = None
                if step_index is not None:
                    step_row = (
                        session.query(AgentRunStep)
                        .filter_by(run_id=run_row.id, step_index=step_index)
                        .first()
                    )
                row = AgentRunArtifact(
                    run_id=run_row.id,
                    run_step_id=step_row.id if step_row else None,
                    artifact_type=artifact_type,
                    content_json=dict(content_json or {}),
                )
                session.add(row)
                session.commit()
                return
        self._mem_artifacts.append(
            {
                "run_id": run_id,
                "step_index": step_index,
                "artifact_type": artifact_type,
                "content_json": dict(content_json or {}),
            }
        )

    def add_confidence_report(
        self,
        *,
        run_id: str,
        step_index: int | None,
        scope: str,
        confidence: float,
        decision: str,
        factors: dict[str, Any],
        model_self_confidence: float | None = None,
    ) -> None:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return
                step_row = None
                if step_index is not None:
                    step_row = (
                        session.query(AgentRunStep)
                        .filter_by(run_id=run_row.id, step_index=step_index)
                        .first()
                    )
                row = AgentConfidenceReport(
                    run_id=run_row.id,
                    run_step_id=step_row.id if step_row else None,
                    step_index=step_index,
                    scope=scope,
                    confidence=confidence,
                    decision=decision,
                    factors_json=dict(factors or {}),
                    model_self_confidence=model_self_confidence,
                )
                session.add(row)
                session.commit()
                return
        self._mem_confidence.append(
            {
                "run_id": run_id,
                "step_index": step_index,
                "scope": scope,
                "confidence": confidence,
                "decision": decision,
                "factors": dict(factors or {}),
                "model_self_confidence": model_self_confidence,
            }
        )

    def add_escalation(
        self,
        *,
        run_id: str,
        step_index: int | None,
        severity: str,
        reason_code: str,
        reason: str,
        preserved_worktree: bool,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    raise ValueError(f"Unknown run_id '{run_id}'")
                step_row = None
                if step_index is not None:
                    step_row = (
                        session.query(AgentRunStep)
                        .filter_by(run_id=run_row.id, step_index=step_index)
                        .first()
                    )
                row = AgentEscalation(
                    run_id=run_row.id,
                    run_step_id=step_row.id if step_row else None,
                    step_index=step_index,
                    severity=severity,
                    reason_code=reason_code,
                    reason=reason,
                    status="open",
                    preserved_worktree=preserved_worktree,
                    payload_json=dict(payload or {}),
                )
                session.add(row)
                session.commit()
                return {
                    "id": row.id,
                    "run_id": run_id,
                    "step_index": step_index,
                    "severity": severity,
                    "reason_code": reason_code,
                    "reason": reason,
                    "status": row.status,
                    "preserved_worktree": bool(row.preserved_worktree),
                }
        entry = {
            "id": len(self._mem_escalations) + 1,
            "run_id": run_id,
            "step_index": step_index,
            "severity": severity,
            "reason_code": reason_code,
            "reason": reason,
            "status": "open",
            "preserved_worktree": preserved_worktree,
            "payload": dict(payload or {}),
        }
        self._mem_escalations.append(entry)
        return entry

    def list_attempts(
        self,
        *,
        run_id: str,
        step_index: int | None = None,
    ) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return []
                query = (
                    session.query(AgentRunAttempt)
                    .join(
                        AgentRunStep,
                        AgentRunAttempt.run_step_id == AgentRunStep.id,
                    )
                    .filter(AgentRunStep.run_id == run_row.id)
                )
                if step_index is not None:
                    query = query.filter(AgentRunStep.step_index == step_index)
                rows = query.order_by(
                    AgentRunStep.step_index.asc(),
                    AgentRunAttempt.attempt_index.asc(),
                ).all()
                return [
                    {
                        "step_index": row_step.step_index,
                        "attempt_index": row_attempt.attempt_index,
                        "status": row_attempt.status,
                        "fail_count": row_attempt.fail_count,
                        "fail_signature": row_attempt.fail_signature,
                        "diff_added": row_attempt.diff_added,
                        "diff_deleted": row_attempt.diff_deleted,
                        "error_category": row_attempt.error_category,
                        "progress_made": bool(row_attempt.progress_made),
                    }
                    for (row_attempt, row_step) in (
                        (
                            attempt,
                            session.query(AgentRunStep)
                            .filter_by(id=attempt.run_step_id)
                            .first(),
                        )
                        for attempt in rows
                    )
                    if row_step is not None
                ]

        rows = [item for item in self._mem_attempts if item["run_id"] == run_id]
        if step_index is not None:
            rows = [row for row in rows if row["step_index"] == step_index]
        return sorted(rows, key=lambda row: int(row.get("attempt_index") or 0))

    def list_artifacts(
        self,
        *,
        run_id: str,
        step_index: int | None = None,
        artifact_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return []
                query = session.query(AgentRunArtifact).filter_by(
                    run_id=run_row.id
                )
                if artifact_type is not None:
                    query = query.filter_by(artifact_type=artifact_type)
                rows = query.order_by(AgentRunArtifact.created_at.asc()).all()
                out: list[dict[str, Any]] = []
                for row in rows:
                    resolved_step_index = None
                    if row.run_step_id is not None:
                        step_row = (
                            session.query(AgentRunStep)
                            .filter_by(id=row.run_step_id)
                            .first()
                        )
                        resolved_step_index = (
                            step_row.step_index if step_row else None
                        )
                    if (
                        step_index is not None
                        and resolved_step_index != step_index
                    ):
                        continue
                    out.append(
                        {
                            "step_index": resolved_step_index,
                            "artifact_type": row.artifact_type,
                            "content_json": dict(row.content_json or {}),
                        }
                    )
                return out

        rows = [
            item for item in self._mem_artifacts if item["run_id"] == run_id
        ]
        if step_index is not None:
            rows = [row for row in rows if row["step_index"] == step_index]
        if artifact_type is not None:
            rows = [
                row for row in rows if row["artifact_type"] == artifact_type
            ]
        return rows

    def list_confidence_reports(
        self,
        *,
        run_id: str,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return []
                query = session.query(AgentConfidenceReport).filter_by(
                    run_id=run_row.id
                )
                if scope is not None:
                    query = query.filter_by(scope=scope)
                rows = query.order_by(
                    AgentConfidenceReport.created_at.asc()
                ).all()
                return [
                    {
                        "step_index": row.step_index,
                        "scope": row.scope,
                        "confidence": row.confidence,
                        "decision": row.decision,
                        "factors": dict(row.factors_json or {}),
                        "model_self_confidence": row.model_self_confidence,
                    }
                    for row in rows
                ]

        rows = [
            item for item in self._mem_confidence if item["run_id"] == run_id
        ]
        if scope is not None:
            rows = [row for row in rows if row["scope"] == scope]
        return rows

    def list_escalations(self, *, run_id: str) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return []
                rows = (
                    session.query(AgentEscalation)
                    .filter_by(run_id=run_row.id)
                    .order_by(AgentEscalation.created_at.asc())
                    .all()
                )
                return [
                    {
                        "step_index": row.step_index,
                        "severity": row.severity,
                        "reason_code": row.reason_code,
                        "reason": row.reason,
                        "status": row.status,
                        "preserved_worktree": bool(row.preserved_worktree),
                    }
                    for row in rows
                ]
        return [
            row for row in self._mem_escalations if row.get("run_id") == run_id
        ]

    def list_events(self, *, run_id: str) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                run_row = (
                    session.query(AgentRun).filter_by(run_id=run_id).first()
                )
                if run_row is None:
                    return []
                rows = (
                    session.query(AgentEvent)
                    .filter_by(run_id=run_row.id)
                    .order_by(AgentEvent.created_at.asc())
                    .all()
                )
                return [
                    {
                        "event_type": row.event_type,
                        "payload": dict(row.payload_json or {}),
                    }
                    for row in rows
                ]
        return []


store = AgentStore()


__all__ = ["AgentStore", "deterministic_worktree_id", "store"]
