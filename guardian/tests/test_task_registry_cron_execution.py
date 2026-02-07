from __future__ import annotations

from guardian.tasks.types import (
    CronExecutionTask,
    TASK_TYPE_REGISTRY,
    task_from_dict,
)


def test_registry_contains_cron_execution_task() -> None:
    assert TASK_TYPE_REGISTRY["cron.execute"] is CronExecutionTask


def test_task_from_dict_resolves_cron_execution_task() -> None:
    task = task_from_dict(
        {
            "type": "cron.execute",
            "cron_run_id": 7,
            "cron_job_id": 3,
            "job_type": "noop",
            "payload": {"k": "v"},
            "origin": "scheduler",
        }
    )

    assert isinstance(task, CronExecutionTask)
    assert task.cron_run_id == 7
    assert task.cron_job_id == 3
    assert task.job_type == "noop"
    assert task.payload == {"k": "v"}
    assert task.origin == "scheduler"
