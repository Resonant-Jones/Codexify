from __future__ import annotations

from types import SimpleNamespace

from guardian.evals.groundedness import evaluate_groundedness
from guardian.evals.spine import build_trace_snapshot, build_verdict_record
from guardian.tasks.types import EvalTask
from guardian.workers import eval_worker


def _task() -> SimpleNamespace:
    return SimpleNamespace(
        task_id="task-123",
        request_id="req-123",
        thread_id=42,
        latest_turn_message_id=17,
        created_at="2026-04-22T12:00:00+00:00",
        provider="groq",
        model="moonshotai/kimi-k2-instruct-0905",
        requested_source_mode="project",
        selection_source="explicit",
    )


def test_groundedness_evaluator_supported_and_unsupported() -> None:
    supported = evaluate_groundedness(
        {
            "assistant_output_text": "The sky is blue.",
            "trace_json": {
                "messages": [{"role": "user", "content": "The sky is blue."}],
                "documents": [{"title": "note", "content": "The sky is blue."}],
            },
        }
    )
    unsupported = evaluate_groundedness(
        {
            "assistant_output_text": "The moon is made of cheese.",
            "trace_json": {
                "messages": [{"role": "user", "content": "The sky is blue."}],
                "documents": [{"title": "note", "content": "The sky is blue."}],
            },
        }
    )

    assert supported["label"] == "grounded"
    assert supported["score"] == 1.0
    assert unsupported["label"] == "ungrounded"
    assert unsupported["score"] == 0.0
    assert "Unsupported claim" in unsupported["reason"]


def test_build_trace_snapshot_preserves_attempt_linkage() -> None:
    task = _task()
    result = {
        "assistant_text": "The sky is blue.",
        "provider": "groq",
        "model": "moonshotai/kimi-k2-instruct-0905",
        "latest_turn_message_id": 17,
        "retrieval_query": "sky color",
        "retrieval_target": "thread",
        "retrieval_query_matches_latest_turn": True,
        "trace": {
            "widen_reason": "none",
            "project_id": 7,
            "retrieval_query": "sky color",
            "retrieval_target": "thread",
        },
        "payload_summary": {
            "source_mode": "project",
            "completion_truth": {"accepted": True},
            "attempted_provider": "groq",
            "attempted_model": "moonshotai/kimi-k2-instruct-0905",
        },
    }

    snapshot = build_trace_snapshot(
        task=task,
        result=result,
        assistant_message_id=99,
        worker_started_at="2026-04-22T12:01:00+00:00",
        completion_persisted_at="2026-04-22T12:02:00+00:00",
        thread_record={"project_id": 7},
    )

    assert snapshot["task_id"] == "task-123"
    assert snapshot["request_id"] == "req-123"
    assert snapshot["thread_id"] == 42
    assert snapshot["user_message_id"] == 17
    assert snapshot["assistant_message_id"] == 99
    assert snapshot["project_id"] == 7
    assert snapshot["provider"] == "groq"
    assert snapshot["model"] == "moonshotai/kimi-k2-instruct-0905"
    assert snapshot["source_mode"] == "project"
    assert snapshot["widen_reason"] == "none"
    assert (
        snapshot["timestamps_json"]["queued_at"] == "2026-04-22T12:00:00+00:00"
    )
    assert (
        snapshot["timestamps_json"]["worker_started_at"]
        == "2026-04-22T12:01:00+00:00"
    )
    assert (
        snapshot["timestamps_json"]["completion_persisted_at"]
        == "2026-04-22T12:02:00+00:00"
    )


def test_build_verdict_record_preserves_attempt_linkage() -> None:
    snapshot = {
        "trace_snapshot_id": "snapshot-1",
        "task_id": "task-123",
        "request_id": "req-123",
        "thread_id": 42,
        "user_message_id": 17,
        "assistant_message_id": 99,
    }
    eval_task = EvalTask.from_dict(
        {
            "task_id": "eval-run-1",
            "request_id": "eval-req-1",
            "thread_id": 42,
            "trace_snapshot_id": "snapshot-1",
            "evaluator_kind": "code",
            "evaluator_name": "groundedness_basic",
        }
    )
    verdict = {
        "evaluator_kind": "code",
        "evaluator_name": "groundedness_basic",
        "score": 1.0,
        "label": "grounded",
        "status": "succeeded",
        "reason": "supported",
        "structured_findings_json": {"unsupported_sentence_count": 0},
    }

    record = build_verdict_record(
        eval_task=eval_task,
        trace_snapshot=snapshot,
        verdict=verdict,
    )

    assert record["eval_run_id"] == "eval-run-1"
    assert record["trace_snapshot_id"] == "snapshot-1"
    assert record["request_id"] == "eval-req-1"
    assert record["task_id"] == "task-123"
    assert record["thread_id"] == 42
    assert record["user_message_id"] == 17
    assert record["assistant_message_id"] == 99
    assert record["evaluator_kind"] == "code"
    assert record["evaluator_name"] == "groundedness_basic"
    assert record["label"] == "grounded"
    assert record["score"] == 1.0


def test_eval_worker_failure_isolated(monkeypatch) -> None:
    task = EvalTask.from_dict(
        {
            "task_id": "eval-run-2",
            "request_id": "eval-req-2",
            "thread_id": 42,
            "trace_snapshot_id": "snapshot-2",
            "evaluator_kind": "code",
            "evaluator_name": "groundedness_basic",
        }
    )
    monkeypatch.setattr(eval_worker.dependencies, "chatlog_db", object())
    monkeypatch.setattr(
        eval_worker,
        "get_trace_snapshot_by_id",
        lambda *_args, **_kwargs: {
            "trace_snapshot_id": "snapshot-2",
            "task_id": "task-123",
            "request_id": "req-123",
            "thread_id": 42,
            "user_message_id": 17,
            "assistant_message_id": 99,
            "assistant_output_text": "The sky is blue.",
            "trace_json": {"messages": [{"content": "The sky is blue."}]},
        },
    )
    monkeypatch.setattr(
        eval_worker,
        "evaluate_groundedness",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("judge crashed")
        ),
    )

    assert eval_worker.process_eval_task(task) is None
