from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


class _StopProbe(BaseException):
    pass


class _Samples(list):
    def __init__(self):
        super().__init__()
        self.changed = threading.Condition()

    def append(self, status):
        with self.changed:
            super().append(status)
            self.changed.notify_all()

    def wait_status(self, status):
        with self.changed:
            assert self.changed.wait_for(lambda: self and self[-1] == status, timeout=2)

    def wait_count(self, status, count):
        with self.changed:
            assert self.changed.wait_for(lambda: self.count(status) >= count, timeout=2)


def _task():
    accepted = datetime.now(timezone.utc)
    return ChatCompletionTask(
        user_id="inert-heartbeat-proof",
        thread_id=909001,
        accepted_at=accepted.isoformat(),
        work_deadline_at=(accepted + timedelta(seconds=720)).isoformat(),
        terminal_deadline_at=(accepted + timedelta(seconds=780)).isoformat(),
    )


def _install(monkeypatch, worker):
    samples = _Samples()
    futures = []

    class ObservedExecutor(ThreadPoolExecutor):
        def submit(self, fn, *args, **kwargs):
            future = super().submit(fn, *args, **kwargs)
            futures.append(future)
            return future

    monkeypatch.setattr(chat_worker, "_initialize_worker", lambda: None)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda _: False)
    monkeypatch.setattr(chat_worker, "_run_chat_task", worker)
    monkeypatch.setattr(chat_worker, "ThreadPoolExecutor", ObservedExecutor)
    monkeypatch.setattr(
        chat_worker, "_publish_worker_heartbeat", lambda status="idle": samples.append(status)
    )
    return samples, futures


def _run():
    with pytest.raises(_StopProbe):
        chat_worker.run_forever()


@pytest.mark.parametrize("failure", [False, True])
def test_activity_includes_held_terminal_cleanup(monkeypatch, failure):
    task = _task()
    entered, finish_work = threading.Event(), threading.Event()
    cleanup_entered, finish_cleanup = threading.Event(), threading.Event()
    calls = []

    def worker(owned):
        calls.append(owned.task_id)
        entered.set()
        assert finish_work.wait(3)
        cleanup_entered.set()
        assert finish_cleanup.wait(3)
        if failure:
            raise RuntimeError("inert lifecycle failure after cleanup")

    samples, futures = _install(monkeypatch, worker)
    count = 0

    def dequeue(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            return task.to_dict()
        if count == 2:
            assert entered.wait(2)
            return None
        if count == 3:
            samples.wait_status("active")
            finish_work.set()
            assert cleanup_entered.wait(2)
            return None
        if count == 4:
            samples.wait_status("active")
            finish_cleanup.set()
            if failure:
                with pytest.raises(RuntimeError, match="after cleanup"):
                    futures[0].result(timeout=2)
            else:
                futures[0].result(timeout=2)
            return None
        samples.wait_status("idle")
        raise _StopProbe()

    monkeypatch.setattr(chat_worker, "dequeue", dequeue)
    try:
        _run()
    finally:
        finish_work.set()
        finish_cleanup.set()
    assert calls == [task.task_id]
    assert samples[0] == samples[-1] == "idle"
    assert all(status == "active" for status in samples[1:-1])


@pytest.mark.parametrize("concurrency", [1, 2])
def test_activity_covers_queued_and_overlapping_lifecycles(monkeypatch, concurrency):
    tasks = [_task(), _task()]
    entered = [threading.Event(), threading.Event()]
    release = [threading.Event(), threading.Event()]
    calls = []

    def worker(owned):
        index = next(i for i, task in enumerate(tasks) if task.task_id == owned.task_id)
        calls.append(owned.task_id)
        entered[index].set()
        assert release[index].wait(3)

    samples, futures = _install(monkeypatch, worker)
    monkeypatch.setattr(chat_worker, "CONCURRENCY", concurrency)
    count = 0

    def dequeue(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            return tasks[0].to_dict()
        if count == 2:
            assert entered[0].wait(2)
            return tasks[1].to_dict()
        if count == 3:
            samples.wait_status("active")
            if concurrency == 1:
                assert not entered[1].is_set()
            release[0].set()
            futures[0].result(timeout=2)
            assert entered[1].wait(2)
            return None
        if count == 4:
            samples.wait_status("active")
            release[1].set()
            futures[1].result(timeout=2)
            return None
        samples.wait_status("idle")
        raise _StopProbe()

    monkeypatch.setattr(chat_worker, "dequeue", dequeue)
    try:
        _run()
    finally:
        for gate in release:
            gate.set()
    assert sorted(calls) == sorted(task.task_id for task in tasks)
    assert all(status == "active" for status in samples[1:-1])


def test_inline_cancellation_does_not_clear_other_owned_activity(monkeypatch):
    ordinary, cancelled = _task(), _task()
    entered, release, inline_done = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def worker(owned):
        calls.append(owned.task_id)
        if owned.task_id == cancelled.task_id:
            assert entered.is_set()
            samples.wait_status("active")
            inline_done.set()
        else:
            entered.set()
            assert release.wait(3)

    samples, futures = _install(monkeypatch, worker)
    monkeypatch.setattr(chat_worker, "CONCURRENCY", 1)
    monkeypatch.setattr(
        chat_worker, "is_cancelled", lambda task_id: task_id == cancelled.task_id
    )
    count = 0

    def dequeue(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            return ordinary.to_dict()
        if count == 2:
            assert entered.wait(2)
            return cancelled.to_dict()
        if count == 3:
            assert inline_done.is_set()
            assert len(futures) == 1
            samples.wait_status("active")
            release.set()
            futures[0].result(timeout=2)
            return None
        samples.wait_status("idle")
        raise _StopProbe()

    monkeypatch.setattr(chat_worker, "dequeue", dequeue)
    try:
        _run()
    finally:
        release.set()
    assert sorted(calls) == sorted([ordinary.task_id, cancelled.task_id])
    assert all(status == "active" for status in samples[1:-1])


@pytest.mark.parametrize("seam", ["pre_dispatch", "submission"])
def test_dispatch_error_propagates_without_work_or_activity_in_next_run(monkeypatch, seam):
    task = _task()
    calls = []
    samples, _ = _install(monkeypatch, lambda owned: calls.append(owned.task_id))
    monkeypatch.setattr(chat_worker, "dequeue", lambda *a, **k: task.to_dict())

    class BrokenExecutor:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, *args, **kwargs):
            raise RuntimeError("inert submission error")

    def broken_check(owned):
        raise RuntimeError("inert pre_dispatch error")

    with monkeypatch.context() as failing:
        if seam == "submission":
            failing.setattr(chat_worker, "ThreadPoolExecutor", BrokenExecutor)
        else:
            failing.setattr(chat_worker, "_chat_task_cancelled_before_dispatch", broken_check)
        with pytest.raises(RuntimeError, match=seam):
            chat_worker.run_forever()
    assert calls == []

    def stop_dequeue(*args, **kwargs):
        samples.wait_status("idle")
        raise _StopProbe()

    monkeypatch.setattr(chat_worker, "dequeue", stop_dequeue)
    _run()


@pytest.mark.parametrize("seam", ["inline", "cancellation_probe", "dequeue", "executor_drain"])
def test_periodic_publication_survives_held_dispatch_and_drain(monkeypatch, seam):
    task = _task()
    entered, release = threading.Event(), threading.Event()
    dispatcher_stopped = threading.Event()
    calls, outcomes = [], []
    previous_threads = set(threading.enumerate())

    def held():
        entered.set()
        assert release.wait(3)

    def worker(owned):
        calls.append(owned.task_id)
        if seam in {"inline", "executor_drain"}:
            held()

    samples, _ = _install(monkeypatch, worker)
    monkeypatch.setattr(chat_worker, "WORKER_HEARTBEAT_INTERVAL_SECONDS", .025)

    def cancelled(task_id):
        assert task_id == task.task_id
        if seam == "cancellation_probe":
            held()
        return seam in {"inline", "cancellation_probe"}

    monkeypatch.setattr(chat_worker, "is_cancelled", cancelled)
    dequeues = 0

    def dequeue(*args, **kwargs):
        nonlocal dequeues
        dequeues += 1
        if seam == "dequeue":
            held()
        elif dequeues == 1:
            return task.to_dict()
        dispatcher_stopped.set()
        raise _StopProbe()

    monkeypatch.setattr(chat_worker, "dequeue", dequeue)

    def run():
        try:
            chat_worker.run_forever()
        except _StopProbe:
            outcomes.append("controlled_stop")
        except BaseException as error:
            outcomes.append(error)

    runner = threading.Thread(target=run)
    runner.start()
    try:
        assert entered.wait(2)
        if seam == "executor_drain":
            assert dispatcher_stopped.wait(2)
        status = "idle" if seam == "dequeue" else "active"
        first_new_sample = len(samples)
        samples.wait_count(status, samples.count(status) + 3)
        assert runner.is_alive() and not release.is_set()
        assert all(value == status for value in samples[first_new_sample:])
    finally:
        release.set()
        runner.join(3)
    assert not runner.is_alive() and outcomes == ["controlled_stop"]
    assert calls == ([] if seam == "dequeue" else [task.task_id])
    assert not [
        thread for thread in threading.enumerate()
        if thread not in previous_threads and thread.name == "chat-worker-heartbeat"
    ]
