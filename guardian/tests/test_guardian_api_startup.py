import asyncio
import threading
import time

import pytest

import guardian.guardian_api as guardian_api

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_chatgpt_import_sweep_is_scheduled_in_background(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def slow_sweep() -> None:
        started.set()
        release.wait(timeout=1)

    monkeypatch.setattr(
        guardian_api, "_run_chatgpt_import_startup_sweep", slow_sweep
    )

    start = time.perf_counter()
    task = guardian_api._schedule_chatgpt_import_startup_sweep(guardian_api.app)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.05
    assert not task.done()

    await asyncio.wait_for(asyncio.to_thread(started.wait, 1), timeout=1)
    assert started.is_set()

    release.set()
    await asyncio.wait_for(task, timeout=1)

    startup_tasks = getattr(
        guardian_api.app.state, "startup_background_tasks", set()
    )
    assert task not in startup_tasks
