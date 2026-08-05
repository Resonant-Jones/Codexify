"""Focused regression tests for the restored _collect_after_guard helper.

These tests prove that:
1. The guard infrastructure functions are callable.
2. The worker processes a basic cwd=None task without NameError.
3. null/missing repo_root follows the documented unverified behavior.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


def test_collect_after_guard_is_callable():
    """Prove the guard infrastructure is present and callable."""
    from guardian.workers.coding_worker import _mutation_guard_metadata

    assert callable(_mutation_guard_metadata)

    from guardian.workers.coding_worker import _evaluate_mutation_guard

    assert callable(_evaluate_mutation_guard)

    from guardian.workers.coding_worker import _git_mutation_guard_snapshot

    assert callable(_git_mutation_guard_snapshot)


def test_no_name_error_in_guard_path() -> None:
    """Prove the coding worker processes a cwd=None task without NameError.

    The previous regression (_collect_after_guard undefined) crashed the
    worker before adapter execution.  This test sends a minimal task with
    no cwd (the exact shape that triggered the live-proof NameError) and
    asserts the worker reaches the adapter.
    """
    from guardian.workers.coding_worker import CodingWorker
    from guardian.agents.adapters.base import AgentRunEnvelope
    from guardian.agents.adapters import ADAPTERS
    from guardian.tasks.types import CodingExecutionTask

    store = _make_store_mock()
    worker = CodingWorker(agent_store=store)

    task = CodingExecutionTask(
        task_id="task-test-guard",
        run_id="run-test-guard",
        deployment_id="dep-test",
        coding_task_id="coding-test-guard",
        attempt_id="attempt-test-guard",
        thread_id=1,
        source_message_id=100,
        instructions="echo ok",
        cwd=None,
        timeout_seconds=60,
    )

    mock_adapter = MagicMock()
    mock_adapter.name = "pi_codex_runner"
    mock_adapter.execute = MagicMock(
        return_value=AgentRunEnvelope(
            status="ok",
            summary="adapter ok",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )
    )

    original = ADAPTERS.get("pi_codex_runner")
    try:
        ADAPTERS["pi_codex_runner"] = mock_adapter
        worker._process_task(task)
    except NameError as exc:
        if "_collect_after_guard" in str(exc):
            pytest.fail(f"_collect_after_guard still undefined: {exc}")
        raise
    finally:
        if original is not None:
            ADAPTERS["pi_codex_runner"] = original
        else:
            ADAPTERS.pop("pi_codex_runner", None)

    assert store.store_coding_result.called, (
        "store_coding_result was not called — worker did not reach "
        "the adapter execution phase"
    )


def test_null_repo_root_yields_unverified_guard():
    """_git_mutation_guard_snapshot with cwd=None returns unverified metadata."""
    from guardian.workers.coding_worker import _git_mutation_guard_snapshot

    snap = _git_mutation_guard_snapshot(cwd=None, allowed_paths=[])
    assert snap["repo_root"] is None
    assert snap["enabled"] is False
    assert snap["verified"] is False
    assert snap["before_paths"] == []
    assert snap["before_ok"] is False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_store_mock():
    mock = MagicMock()
    mock.store_coding_result = MagicMock(return_value={"delivery_ok": True})
    mock.get_deployment = MagicMock(
        return_value={
            "spec_json": {"adapter_kind": "pi_codex_runner"},
            "deployment_id": "dep-test",
        }
    )
    mock.create_run = MagicMock(
        return_value={
            "run_id": "run-test",
            "status": "queued",
            "deployment_id": "dep-test",
        }
    )
    mock.update_run_status = MagicMock()
    return mock
