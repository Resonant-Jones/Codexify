"""Persistence helpers for agent orchestration entities."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from guardian.agents.events import build_coding_result_lineage_payload
from guardian.db.models import (
    AgentConfidenceReport,
    AgentDeployment,
    AgentEscalation,
    AgentEvent,
    AgentRun,
    AgentRunArtifact,
    AgentRunAttempt,
    AgentRunStep,
    ChatMessage,
    ChatThread,
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


def _coerce_positive_int(value: Any) -> int | None:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return None
    return coerced if coerced > 0 else None


def _normalize_coding_result_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    return value or "error"


def _should_persist_coding_result_message(status: str) -> bool:
    return _normalize_coding_result_status(status) in {
        "ok",
        "success",
        "succeeded",
        "completed",
        "partial",
        "partial_success",
        "partial-success",
    }


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
        self._mem_coding_results: list[dict[str, Any]] = []

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
                    "spec_json": dict(row.spec_json or {}),
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
                    "spec_json": dict(row.spec_json or {}),
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

    def store_coding_result(
        self,
        *,
        run_id: str,
        coding_task_id: str,
        attempt_id: str,
        result_json: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "run_id": run_id,
            "coding_task_id": coding_task_id,
            "attempt_id": attempt_id,
            "result_json": dict(result_json or {}),
        }
        if self._has_db():
            self.add_artifact(
                run_id=run_id,
                step_index=None,
                artifact_type="coding_result",
                content_json=payload,
            )
            return payload
        self._mem_coding_results.append(payload)
        return payload

    def list_coding_results(
        self, *, run_id: str | None = None
    ) -> list[dict[str, Any]]:
        if self._has_db():
            with self.db.get_session() as session:
                run_filter = None
                if run_id is not None:
                    run_row = (
                        session.query(AgentRun).filter_by(run_id=run_id).first()
                    )
                    if run_row is None:
                        return []
                    run_filter = run_row.id
                query = session.query(AgentRunArtifact).filter_by(
                    artifact_type="coding_result"
                )
                if run_filter is not None:
                    query = query.filter_by(run_id=run_filter)
                rows = query.order_by(AgentRunArtifact.created_at.asc()).all()
                return [
                    {
                        "run_id": row.run_id,
                        "run_step_id": row.run_step_id,
                        "artifact_type": row.artifact_type,
                        "content_json": dict(row.content_json or {}),
                    }
                    for row in rows
                ]
        if run_id is None:
            return list(self._mem_coding_results)
        return [
            row
            for row in self._mem_coding_results
            if row.get("run_id") == run_id
        ]

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

    def store_coding_result(
        self,
        *,
        run_id: str,
        coding_task_id: str,
        attempt_id: str,
        request_id: str | None = None,
        thread_id: int | None,
        source_message_id: int | None,
        result_status: str,
        result_summary: str,
        adapter_kind: str | None = None,
        adapter_session_ref: str | None = None,
        files_changed: list[str] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        errors: list[str] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        validation_results: Any | None = None,
        validation_attempt_count: Any | None = None,
        validation_attempts: Any | None = None,
        validation_stop_reason: Any | None = None,
        final_validation_status: Any | None = None,
        final_fail_signature: Any | None = None,
        best_validation_result: Any | None = None,
        max_validation_attempts: Any | None = None,
    ) -> dict[str, Any]:
        """Store coding result and inject into source thread.

        Per ADR-020: results must return through Guardian before user-visible output.
        """
        normalized_status = _normalize_coding_result_status(result_status)
        persist_message = _should_persist_coding_result_message(
            normalized_status
        )
        normalized_files_changed = [
            str(item).strip()
            for item in (files_changed or [])
            if str(item).strip()
        ]
        artifact_rows = [
            dict(artifact)
            if isinstance(artifact, dict)
            else {"value": str(artifact)}
            for artifact in (artifacts or [])
        ]
        if not normalized_files_changed:
            normalized_files_changed = [
                artifact.get("path", artifact.get("name", ""))
                for artifact in artifact_rows
                if isinstance(artifact, dict) and artifact.get("path")
            ]
        run = self.get_run(run_id)
        deployment = None
        if run and run.get("deployment_id"):
            deployment = self.get_deployment(str(run["deployment_id"]))

        deployment_spec: dict[str, Any] = {}
        if isinstance(deployment, dict):
            deployment_spec = dict(deployment.get("spec_json") or {})
        adapter_kind = (
            str(
                adapter_kind or deployment_spec.get("adapter_kind") or ""
            ).strip()
            or None
        )
        expected_thread_id = (
            _coerce_positive_int(
                deployment_spec.get("source_thread_id")
                or deployment_spec.get("thread_id")
            )
            or thread_id
        )
        expected_source_message_id = _coerce_positive_int(
            deployment_spec.get("source_message_id") or source_message_id
        )
        expected_user_id = (
            str(deployment_spec.get("user_id") or "").strip() or None
        )
        expected_project_id = _coerce_positive_int(
            deployment_spec.get("project_id")
        )

        commit_hash = None
        validation_results = None
        validation_attempt_count = None
        validation_attempts = None
        validation_stop_reason = None
        final_validation_status = None
        final_fail_signature = None
        best_validation_result = None
        max_validation_attempts = None
        for artifact in artifact_rows:
            if commit_hash is None:
                candidate = artifact.get("commit_hash") or artifact.get(
                    "git_commit"
                )
                if isinstance(candidate, str) and candidate.strip():
                    commit_hash = candidate.strip()
            if (
                validation_results is None
                and artifact.get("validation_results") is not None
            ):
                validation_results = artifact.get("validation_results")
            if (
                validation_attempt_count is None
                and artifact.get("validation_attempt_count") is not None
            ):
                validation_attempt_count = artifact.get(
                    "validation_attempt_count"
                )
            if (
                validation_attempts is None
                and artifact.get("validation_attempts") is not None
            ):
                validation_attempts = artifact.get("validation_attempts")
            if (
                validation_stop_reason is None
                and artifact.get("validation_stop_reason") is not None
            ):
                validation_stop_reason = artifact.get("validation_stop_reason")
            if (
                final_validation_status is None
                and artifact.get("final_validation_status") is not None
            ):
                final_validation_status = artifact.get(
                    "final_validation_status"
                )
            if (
                final_fail_signature is None
                and artifact.get("final_fail_signature") is not None
            ):
                final_fail_signature = artifact.get("final_fail_signature")
            if (
                best_validation_result is None
                and artifact.get("best_validation_result") is not None
            ):
                best_validation_result = artifact.get("best_validation_result")
            if (
                max_validation_attempts is None
                and artifact.get("max_validation_attempts") is not None
            ):
                max_validation_attempts = artifact.get(
                    "max_validation_attempts"
                )

            result_payload = {
                "run_id": run_id,
                "coding_task_id": coding_task_id,
                "attempt_id": attempt_id,
                "request_id": request_id,
                "thread_id": expected_thread_id,
                "source_message_id": expected_source_message_id,
                "adapter_kind": adapter_kind,
                "user_id": expected_user_id,
                "project_id": expected_project_id,
                "status": normalized_status,
                "coding_result_status": normalized_status,
                "summary": result_summary,
                "files_changed": normalized_files_changed,
                "artifacts": artifact_rows,
                "errors": errors or [],
                "error_code": error_code,
                "error_message": error_message,
                "commit_hash": commit_hash,
                "validation_results": validation_results,
                "validation_result": validation_results,
                "validation_attempt_count": validation_attempt_count,
                "validation_attempts": validation_attempts,
                "validation_stop_reason": validation_stop_reason,
                "final_validation_status": final_validation_status,
                "final_fail_signature": final_fail_signature,
                "best_validation_result": best_validation_result,
                "max_validation_attempts": max_validation_attempts,
                "adapter_session_ref": adapter_session_ref,
                "result_captured_by_guardian": True,
            }

        result_payload = {
            "run_id": run_id,
            "coding_task_id": coding_task_id,
            "attempt_id": attempt_id,
            "request_id": request_id,
            "thread_id": expected_thread_id,
            "source_message_id": expected_source_message_id,
            "adapter_kind": adapter_kind,
            "user_id": expected_user_id,
            "project_id": expected_project_id,
            "status": normalized_status,
            "coding_result_status": normalized_status,
            "summary": result_summary,
            "files_changed": normalized_files_changed,
            "artifacts": artifact_rows,
            "errors": errors or [],
            "error_code": error_code,
            "error_message": error_message,
            "commit_hash": commit_hash,
            "validation_results": validation_results,
            "validation_result": validation_results,
            "validation_attempt_count": validation_attempt_count,
            "validation_attempts": validation_attempts,
            "validation_stop_reason": validation_stop_reason,
            "final_validation_status": final_validation_status,
            "final_fail_signature": final_fail_signature,
            "best_validation_result": best_validation_result,
            "max_validation_attempts": max_validation_attempts,
            "adapter_session_ref": adapter_session_ref,
            "result_captured_by_guardian": True,
        }

        message_id = None
        delivery_reason = None
        delivery_ok = False
        if (
            persist_message
            and expected_thread_id is not None
            and self._has_db()
        ):
            (
                message_id,
                delivery_reason,
            ) = self._inject_coding_result_into_thread(
                thread_id=expected_thread_id,
                run_id=run_id,
                coding_task_id=coding_task_id,
                attempt_id=attempt_id,
                request_id=request_id,
                source_message_id=expected_source_message_id,
                expected_user_id=expected_user_id,
                expected_project_id=expected_project_id,
                adapter_kind=adapter_kind,
                status=normalized_status,
                summary=result_summary,
                files_changed=normalized_files_changed,
                artifacts=artifact_rows,
                errors=errors or [],
                commit_hash=commit_hash,
                validation_results=validation_results,
                validation_attempt_count=validation_attempt_count,
                validation_attempts=validation_attempts,
                validation_stop_reason=validation_stop_reason,
                final_validation_status=final_validation_status,
                final_fail_signature=final_fail_signature,
                best_validation_result=best_validation_result,
                max_validation_attempts=max_validation_attempts,
                adapter_session_ref=adapter_session_ref,
                error_code=error_code,
                error_message=error_message,
            )
            delivery_ok = message_id is not None
        elif expected_thread_id is None:
            delivery_reason = "missing_source_thread"
        elif not persist_message:
            delivery_reason = "result_status_not_persisted_as_assistant_message"
        else:
            delivery_reason = "delivery_database_unavailable"

        final_status = (
            "succeeded" if persist_message and delivery_ok else "failed"
        )
        self.update_run_status(
            run_id=run_id,
            status=final_status,
            error=error_message
            or delivery_reason
            or (errors[0] if errors else None),
        )

        artifact_payload = dict(result_payload)
        artifact_payload["message_id"] = message_id
        artifact_payload["delivery_ok"] = delivery_ok
        artifact_payload["delivery_reason"] = delivery_reason
        if self._has_db():
            existing_artifact = None
            for row in self.list_artifacts(
                run_id=run_id, artifact_type="coding_result"
            ):
                content = row.get("content_json")
                if not isinstance(content, dict):
                    continue
                if (
                    content.get("coding_task_id") == coding_task_id
                    and content.get("attempt_id") == attempt_id
                ):
                    existing_artifact = row
                    break
            if existing_artifact is None:
                self.add_artifact(
                    run_id=run_id,
                    step_index=None,
                    artifact_type="coding_result",
                    content_json=artifact_payload,
                )

        return {
            "ok": True,
            "run_id": run_id,
            "status": normalized_status,
            "message_id": message_id,
            "delivery_ok": delivery_ok,
            "delivery_reason": delivery_reason,
            "files_changed": normalized_files_changed,
            "artifacts_count": len(artifact_rows),
            "commit_hash": commit_hash,
            "validation_results": validation_results,
            "validation_attempt_count": validation_attempt_count,
            "validation_attempts": validation_attempts,
            "best_validation_result": best_validation_result,
            "max_validation_attempts": max_validation_attempts,
            "result_payload": result_payload,
        }

    def _inject_coding_result_into_thread(
        self,
        *,
        thread_id: int,
        run_id: str,
        coding_task_id: str,
        attempt_id: str,
        request_id: str | None,
        source_message_id: int | None,
        expected_user_id: str | None,
        expected_project_id: int | None,
        adapter_kind: str | None,
        status: str,
        summary: str,
        files_changed: list[str],
        artifacts: list[dict[str, Any]],
        errors: list[str],
        commit_hash: str | None = None,
        validation_results: Any | None = None,
        validation_attempt_count: Any | None = None,
        validation_attempts: Any | None = None,
        validation_stop_reason: Any | None = None,
        final_validation_status: Any | None = None,
        final_fail_signature: Any | None = None,
        best_validation_result: Any | None = None,
        max_validation_attempts: Any | None = None,
        adapter_session_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> tuple[int | None, str | None]:
        if not self._has_db():
            return None, "delivery_database_unavailable"

        with self.db.get_session() as session:
            existing = None
            for candidate in (
                session.query(ChatMessage)
                .filter_by(thread_id=thread_id, kind="coding_result")
                .order_by(ChatMessage.id.asc())
                .all()
            ):
                if (
                    isinstance(candidate.extra_meta, dict)
                    and str(candidate.extra_meta.get("run_id") or "") == run_id
                ):
                    existing = candidate
                    break
            if existing:
                return existing.id, None

            thread = session.query(ChatThread).filter_by(id=thread_id).first()
            if thread is None:
                return None, "source_thread_missing"
            if expected_user_id and str(thread.user_id) != expected_user_id:
                return None, "source_thread_scope_mismatch"
            if expected_project_id is not None and (
                thread.project_id is None
                or int(thread.project_id) != int(expected_project_id)
            ):
                return None, "source_project_scope_mismatch"
            if source_message_id is not None:
                source_message = (
                    session.query(ChatMessage)
                    .filter_by(id=int(source_message_id))
                    .first()
                )
                if source_message is None or int(
                    source_message.thread_id
                ) != int(thread_id):
                    return None, "source_message_missing"

            extra_meta = build_coding_result_lineage_payload(
                run_id=run_id,
                queue_task_id=None,
                coding_task_id=coding_task_id,
                attempt_id=attempt_id,
                request_id=request_id,
                source_thread_id=thread_id,
                source_message_id=source_message_id,
                adapter_kind=adapter_kind,
            )
            extra_meta.update(
                {
                    "type": "coding_result",
                    "user_id": expected_user_id,
                    "project_id": expected_project_id,
                    "status": status,
                    "coding_result_status": status,
                    "files_changed": list(files_changed),
                    "artifacts": list(artifacts),
                    "adapter_session_ref": adapter_session_ref,
                    "result_captured_by_guardian": True,
                    "error_code": error_code,
                    "error_message": error_message,
                }
            )
            if commit_hash:
                extra_meta["commit_hash"] = commit_hash
            if validation_results is not None:
                extra_meta["validation_results"] = validation_results
                extra_meta["validation_result"] = validation_results
            if validation_attempt_count is not None:
                extra_meta[
                    "validation_attempt_count"
                ] = validation_attempt_count
            if validation_attempts is not None:
                extra_meta["validation_attempts"] = validation_attempts
            if validation_stop_reason is not None:
                extra_meta["validation_stop_reason"] = validation_stop_reason
            if final_validation_status is not None:
                extra_meta["final_validation_status"] = final_validation_status
            if final_fail_signature is not None:
                extra_meta["final_fail_signature"] = final_fail_signature
            if best_validation_result is not None:
                extra_meta["best_validation_result"] = best_validation_result
            if max_validation_attempts is not None:
                extra_meta["max_validation_attempts"] = max_validation_attempts

            content_parts = [f"## Coding Task Result\n\n"]
            content_parts.append(f"**Status**: {status.upper()}\n\n")
            content_parts.append(f"**Summary**: {summary}\n\n")

            if commit_hash:
                content_parts.append(f"**Commit Hash**: `{commit_hash}`\n\n")

            if files_changed:
                content_parts.append("**Files Changed**:\n")
                for f in files_changed:
                    content_parts.append(f"- `{f}`\n")
                content_parts.append("\n")

            if validation_results is not None:
                content_parts.append("**Validation Results**:\n")
                content_parts.append(
                    f"```json\n{json.dumps(validation_results, indent=2, sort_keys=True)}\n```\n\n"
                )
            if validation_attempt_count is not None:
                content_parts.append(
                    f"**Validation Attempt Count**: {validation_attempt_count}\n\n"
                )
            if max_validation_attempts is not None:
                content_parts.append(
                    f"**Max Validation Attempts**: {max_validation_attempts}\n\n"
                )
            if validation_stop_reason is not None:
                content_parts.append(
                    f"**Validation Stop Reason**: `{validation_stop_reason}`\n\n"
                )
            if final_validation_status is not None:
                content_parts.append(
                    f"**Final Validation Status**: `{final_validation_status}`\n\n"
                )
            if final_fail_signature is not None:
                content_parts.append(
                    f"**Final Fail Signature**: `{final_fail_signature}`\n\n"
                )

            if artifacts:
                content_parts.append("**Artifacts**:\n")
                for a in artifacts:
                    name = a.get(
                        "name", a.get("path", a.get("value", "unnamed"))
                    )
                    content_parts.append(f"- {name}\n")
                content_parts.append("\n")

            if errors:
                content_parts.append("**This task requires attention.**\n")
                content_parts.append("Please review the errors above.\n")

            message = ChatMessage(
                thread_id=thread_id,
                user_id=thread.user_id,
                role="assistant",
                content="".join(content_parts),
                kind="coding_result",
                extra_meta=extra_meta,
            )
            session.add(message)
            session.commit()
            return message.id, None


store = AgentStore()


__all__ = ["AgentStore", "deterministic_worktree_id", "store"]
