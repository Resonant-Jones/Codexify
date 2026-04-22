"""Durable post-completion eval snapshot and verdict helpers."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Json

from guardian.queue.redis_queue import enqueue
from guardian.tasks.types import EvalTask

logger = logging.getLogger(__name__)

EVAL_QUEUE_NAME = "codexify:queue:eval"
TRACE_SNAPSHOT_VERSION = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_int(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _coerce_text(raw: Any) -> str:
    return str(raw or "").strip()


def _coerce_mapping(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _coerce_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _coerce_json_safe(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_coerce_json_safe(item) for item in value]
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            return str(value)
    return str(value)


def _select_trace(result: dict[str, Any]) -> dict[str, Any]:
    trace = result.get("trace")
    return dict(trace) if isinstance(trace, dict) else {}


def _select_payload_summary(result: dict[str, Any]) -> dict[str, Any]:
    payload_summary = result.get("payload_summary")
    return dict(payload_summary) if isinstance(payload_summary, dict) else {}


def _select_retrieval_summary(
    *,
    result: dict[str, Any],
    trace: dict[str, Any],
    payload_summary: dict[str, Any],
) -> dict[str, Any]:
    retrieval_provenance = result.get("retrieval_provenance")
    if not isinstance(retrieval_provenance, dict):
        retrieval_provenance = payload_summary.get("retrieval_provenance")
    summary: dict[str, Any] = {
        "retrieval_provenance": _coerce_json_safe(retrieval_provenance),
        "retrieval_query": _coerce_json_safe(
            result.get("retrieval_query") or trace.get("retrieval_query")
        ),
        "retrieval_target": _coerce_json_safe(
            result.get("retrieval_target") or trace.get("retrieval_target")
        ),
        "retrieval_query_matches_latest_turn": _coerce_json_safe(
            result.get("retrieval_query_matches_latest_turn")
        ),
        "completion_truth": _coerce_json_safe(
            payload_summary.get("completion_truth")
        ),
    }
    return {key: value for key, value in summary.items() if value is not None}


def build_trace_snapshot(
    *,
    task: Any,
    result: dict[str, Any],
    assistant_message_id: int,
    worker_started_at: str,
    completion_persisted_at: str,
    thread_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = _select_trace(result)
    payload_summary = _select_payload_summary(result)
    task_id = _coerce_text(getattr(task, "task_id", ""))
    request_id = _coerce_text(getattr(task, "request_id", "")) or task_id
    thread_id = _coerce_int(getattr(task, "thread_id", None))
    latest_turn_message_id = _coerce_int(
        result.get("latest_turn_message_id")
        or trace.get("latest_turn_message_id")
        or getattr(task, "latest_turn_message_id", None)
    )
    project_id = _coerce_int(
        (thread_record or {}).get("project_id")
        if isinstance(thread_record, dict)
        else None
    )
    if project_id is None and isinstance(trace, dict):
        project_id = _coerce_int(trace.get("project_id"))

    snapshot = {
        "trace_snapshot_id": str(uuid.uuid4()),
        "task_id": task_id,
        "request_id": request_id,
        "thread_id": thread_id,
        "user_message_id": latest_turn_message_id,
        "assistant_message_id": _coerce_int(assistant_message_id),
        "project_id": project_id,
        "provider": _coerce_text(
            result.get("provider") or getattr(task, "provider", "")
        ),
        "model": _coerce_text(
            result.get("model") or getattr(task, "model", "")
        ),
        "source_mode": _coerce_text(
            payload_summary.get("source_mode")
            or payload_summary.get("normalized_source_mode")
            or getattr(task, "requested_source_mode", "")
        )
        or None,
        "widen_reason": _coerce_text(
            trace.get("widen_reason")
            or payload_summary.get("widen_reason")
            or trace.get("depth_downgrade_reason")
        )
        or None,
        "retrieval_summary_json": _select_retrieval_summary(
            result=result, trace=trace, payload_summary=payload_summary
        ),
        "assistant_output_text": _coerce_text(
            result.get("assistant_text")
            or result.get("assistant_output_text")
            or ""
        ),
        "trace_json": _coerce_json_safe(trace),
        "payload_summary_json": _coerce_json_safe(payload_summary),
        "timestamps_json": {
            "queued_at": _coerce_text(getattr(task, "created_at", "")),
            "worker_started_at": worker_started_at,
            "completion_persisted_at": completion_persisted_at,
        },
        "metadata_json": {
            "selection_source": _coerce_text(
                result.get("selection_source")
                or getattr(task, "selection_source", "")
            )
            or None,
            "attempted_provider": _coerce_text(
                result.get("attempted_provider")
                or payload_summary.get("attempted_provider")
            )
            or None,
            "attempted_model": _coerce_text(
                result.get("attempted_model")
                or payload_summary.get("attempted_model")
            )
            or None,
            "final_provider": _coerce_text(
                result.get("final_provider") or result.get("provider")
            )
            or None,
            "final_model": _coerce_text(
                result.get("final_model") or result.get("model")
            )
            or None,
            "completion_truth": _coerce_json_safe(
                payload_summary.get("completion_truth")
            ),
            "trace_version": TRACE_SNAPSHOT_VERSION,
        },
        "created_at": _utc_now_iso(),
    }
    return snapshot


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "keys"):
        return dict(row)
    return {}


def _json_payload(value: Any) -> Json:
    return Json(_coerce_json_safe(value))


def _connect(chatlog_db: Any):
    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        raise RuntimeError("chatlog_db does not expose a Postgres connection")
    return connect()


def persist_trace_snapshot(
    chatlog_db: Any,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise TypeError("snapshot must be a dict")

    query = """
        INSERT INTO eval_trace_snapshots (
            trace_snapshot_id,
            task_id,
            request_id,
            thread_id,
            user_message_id,
            assistant_message_id,
            project_id,
            provider,
            model,
            source_mode,
            widen_reason,
            retrieval_summary,
            assistant_output_text,
            trace,
            payload_summary,
            timestamps,
            metadata,
            created_at
        )
        VALUES (
            %(trace_snapshot_id)s,
            %(task_id)s,
            %(request_id)s,
            %(thread_id)s,
            %(user_message_id)s,
            %(assistant_message_id)s,
            %(project_id)s,
            %(provider)s,
            %(model)s,
            %(source_mode)s,
            %(widen_reason)s,
            %(retrieval_summary_json)s,
            %(assistant_output_text)s,
            %(trace_json)s,
            %(payload_summary_json)s,
            %(timestamps_json)s,
            %(metadata_json)s,
            %(created_at)s
        )
        ON CONFLICT (task_id) DO UPDATE SET
            request_id = EXCLUDED.request_id,
            thread_id = EXCLUDED.thread_id,
            user_message_id = EXCLUDED.user_message_id,
            assistant_message_id = EXCLUDED.assistant_message_id,
            project_id = EXCLUDED.project_id,
            provider = EXCLUDED.provider,
            model = EXCLUDED.model,
            source_mode = EXCLUDED.source_mode,
            widen_reason = EXCLUDED.widen_reason,
            retrieval_summary = EXCLUDED.retrieval_summary,
            assistant_output_text = EXCLUDED.assistant_output_text,
            trace = EXCLUDED.trace,
            payload_summary = EXCLUDED.payload_summary,
            timestamps = EXCLUDED.timestamps,
            metadata = EXCLUDED.metadata
        RETURNING *
    """
    with _connect(chatlog_db) as conn:
        with conn.cursor() as cur:
            payload = dict(snapshot)
            payload["retrieval_summary_json"] = _json_payload(
                payload.get("retrieval_summary_json")
            )
            payload["trace_json"] = _json_payload(payload.get("trace_json"))
            payload["payload_summary_json"] = _json_payload(
                payload.get("payload_summary_json")
            )
            payload["timestamps_json"] = _json_payload(
                payload.get("timestamps_json")
            )
            payload["metadata_json"] = _json_payload(
                payload.get("metadata_json")
            )
            cur.execute(query, payload)
            row = cur.fetchone()
    persisted = _row_to_dict(row)
    if not persisted:
        raise RuntimeError("failed to persist eval trace snapshot")
    return persisted


def build_eval_task(
    trace_snapshot: dict[str, Any],
    *,
    evaluator_name: str = "groundedness_basic",
    evaluator_kind: str = "code",
) -> EvalTask:
    trace_snapshot_id = _coerce_text(trace_snapshot.get("trace_snapshot_id"))
    request_id = _coerce_text(trace_snapshot.get("request_id"))
    thread_id = _coerce_int(trace_snapshot.get("thread_id")) or 0
    return EvalTask(
        trace_snapshot_id=trace_snapshot_id,
        thread_id=thread_id,
        evaluator_name=evaluator_name,
        evaluator_kind=evaluator_kind,
        request_id=request_id,
        origin="chat_completion_eval",
    )


def enqueue_post_completion_eval(
    chatlog_db: Any,
    trace_snapshot: dict[str, Any],
    *,
    evaluator_name: str = "groundedness_basic",
    evaluator_kind: str = "code",
) -> EvalTask | None:
    if not isinstance(trace_snapshot, dict):
        return None
    task = build_eval_task(
        trace_snapshot,
        evaluator_name=evaluator_name,
        evaluator_kind=evaluator_kind,
    )
    try:
        enqueue(task, EVAL_QUEUE_NAME)
    except Exception:
        logger.warning(
            "[eval] enqueue failed trace_snapshot_id=%s task_id=%s",
            trace_snapshot.get("trace_snapshot_id"),
            task.task_id,
            exc_info=True,
        )
    return task


def schedule_post_completion_eval(
    chatlog_db: Any,
    *,
    task: Any,
    result: dict[str, Any],
    assistant_message_id: int,
    worker_started_at: str,
    completion_persisted_at: str,
    thread_record: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        snapshot = build_trace_snapshot(
            task=task,
            result=result,
            assistant_message_id=assistant_message_id,
            worker_started_at=worker_started_at,
            completion_persisted_at=completion_persisted_at,
            thread_record=thread_record,
        )
        persisted = persist_trace_snapshot(chatlog_db, snapshot)
    except Exception:
        logger.warning(
            "[eval] trace snapshot persistence failed thread_id=%s task_id=%s",
            getattr(task, "thread_id", None),
            getattr(task, "task_id", None),
            exc_info=True,
        )
        return None

    enqueue_post_completion_eval(chatlog_db, persisted)
    return persisted


def _fetch_row(
    chatlog_db: Any, query: str, params: tuple[Any, ...]
) -> dict[str, Any] | None:
    with _connect(chatlog_db) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
    return _row_to_dict(row) or None


def _fetch_all_rows(
    chatlog_db: Any, query: str, params: tuple[Any, ...]
) -> list[dict[str, Any]]:
    with _connect(chatlog_db) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall() or []
    return [_row_to_dict(row) for row in rows]


def get_latest_trace_snapshot_for_thread(
    chatlog_db: Any,
    *,
    thread_id: int,
) -> dict[str, Any] | None:
    query = """
        SELECT *
        FROM eval_trace_snapshots
        WHERE thread_id = %s
        ORDER BY created_at DESC, trace_snapshot_id DESC
        LIMIT 1
    """
    return _fetch_row(chatlog_db, query, (thread_id,))


def get_trace_snapshot_by_id(
    chatlog_db: Any,
    *,
    trace_snapshot_id: str,
) -> dict[str, Any] | None:
    query = """
        SELECT *
        FROM eval_trace_snapshots
        WHERE trace_snapshot_id = %s
        LIMIT 1
    """
    return _fetch_row(chatlog_db, query, (trace_snapshot_id,))


def persist_eval_verdicts(
    chatlog_db: Any,
    verdicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    persisted: list[dict[str, Any]] = []
    if not verdicts:
        return persisted

    query = """
        INSERT INTO eval_verdicts (
            eval_run_id,
            trace_snapshot_id,
            request_id,
            task_id,
            thread_id,
            user_message_id,
            assistant_message_id,
            evaluator_kind,
            evaluator_name,
            score,
            label,
            status,
            reason,
            structured_findings,
            created_at
        )
        VALUES (
            %(eval_run_id)s,
            %(trace_snapshot_id)s,
            %(request_id)s,
            %(task_id)s,
            %(thread_id)s,
            %(user_message_id)s,
            %(assistant_message_id)s,
            %(evaluator_kind)s,
            %(evaluator_name)s,
            %(score)s,
            %(label)s,
            %(status)s,
            %(reason)s,
            %(structured_findings_json)s,
            %(created_at)s
        )
        ON CONFLICT (eval_run_id, evaluator_name) DO UPDATE SET
            trace_snapshot_id = EXCLUDED.trace_snapshot_id,
            request_id = EXCLUDED.request_id,
            task_id = EXCLUDED.task_id,
            thread_id = EXCLUDED.thread_id,
            user_message_id = EXCLUDED.user_message_id,
            assistant_message_id = EXCLUDED.assistant_message_id,
            evaluator_kind = EXCLUDED.evaluator_kind,
            score = EXCLUDED.score,
            label = EXCLUDED.label,
            status = EXCLUDED.status,
            reason = EXCLUDED.reason,
            structured_findings = EXCLUDED.structured_findings
        RETURNING *
    """
    with _connect(chatlog_db) as conn:
        with conn.cursor() as cur:
            for verdict in verdicts:
                payload = dict(verdict)
                payload.setdefault(
                    "created_at",
                    _utc_now_iso(),
                )
                payload["structured_findings_json"] = _json_payload(
                    payload.get("structured_findings_json")
                )
                cur.execute(query, payload)
                row = cur.fetchone()
                persisted_row = _row_to_dict(row)
                if persisted_row:
                    persisted.append(persisted_row)
    return persisted


def get_eval_verdicts_for_snapshot(
    chatlog_db: Any,
    *,
    trace_snapshot_id: str,
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM eval_verdicts
        WHERE trace_snapshot_id = %s
        ORDER BY created_at ASC, id ASC
    """
    return _fetch_all_rows(chatlog_db, query, (trace_snapshot_id,))


def get_latest_eval_diagnostics(
    chatlog_db: Any,
    *,
    thread_id: int,
) -> dict[str, Any] | None:
    snapshot = get_latest_trace_snapshot_for_thread(
        chatlog_db,
        thread_id=thread_id,
    )
    if not snapshot:
        return None
    verdicts = get_eval_verdicts_for_snapshot(
        chatlog_db,
        trace_snapshot_id=str(snapshot.get("trace_snapshot_id") or ""),
    )
    return {
        "thread_id": thread_id,
        "trace_snapshot": snapshot,
        "verdicts": verdicts,
    }


def build_verdict_record(
    *,
    eval_task: Any,
    trace_snapshot: dict[str, Any],
    verdict: dict[str, Any],
) -> dict[str, Any]:
    eval_run_id = _coerce_text(getattr(eval_task, "task_id", ""))
    request_id = _coerce_text(
        getattr(eval_task, "request_id", "") or trace_snapshot.get("request_id")
    ) or trace_snapshot.get("task_id")
    task_id = _coerce_text(trace_snapshot.get("task_id"))
    thread_id = _coerce_int(trace_snapshot.get("thread_id")) or _coerce_int(
        getattr(eval_task, "thread_id", None)
    )
    return {
        "eval_run_id": eval_run_id,
        "trace_snapshot_id": _coerce_text(
            trace_snapshot.get("trace_snapshot_id")
        ),
        "request_id": request_id,
        "task_id": task_id,
        "thread_id": thread_id,
        "user_message_id": _coerce_int(trace_snapshot.get("user_message_id")),
        "assistant_message_id": _coerce_int(
            trace_snapshot.get("assistant_message_id")
        ),
        "evaluator_kind": _coerce_text(verdict.get("evaluator_kind")),
        "evaluator_name": _coerce_text(verdict.get("evaluator_name")),
        "score": verdict.get("score"),
        "label": _coerce_text(verdict.get("label")),
        "status": _coerce_text(verdict.get("status")) or "succeeded",
        "reason": _coerce_text(verdict.get("reason")),
        "structured_findings_json": _coerce_json_safe(
            verdict.get("structured_findings_json")
        ),
        "created_at": _utc_now_iso(),
    }
