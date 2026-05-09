# TASK-2026-05-01-003: Connect Delegation to Queue/Worker System

## Task Metadata

- **Task ID**: TASK-2026-05-01-003
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: queue_wiring
- **Area**: backend
- **Risk**: MED
- **Owner**: resonant_jones
- **Commit mode**: single-phase
- **Prerequisite**: TASK-2026-05-01-002

## Objective

Connect the coding task execution to the existing queue/worker infrastructure so tasks are processed asynchronously. Tasks should be queue-backed with SSE visibility.

## Existing Infrastructure Context

```python
# guardian/queue/tasks.py
class BaseTask:
    task_type: str

# guardian/workers/chat_worker.py
async def process_chat_task(task: ChatCompletionTask):
    # Pattern for async worker

# guardian/queue/task_events.py
def publish_task_event(task_id, event_type, payload):
    # SSE event publishing
```

## Scope

### In-scope
- Define `CodingExecutionTask` for queue
- Create `guardian/workers/coding_worker.py` 
- Wire task events via existing pattern
- Handle lifecycle: pending → running → completed/failed

### Out-of-scope
- New database tables (reuse existing models)
- Frontend UI changes

## Preconditions

```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

**EXPECTED**: No uncommitted changes (TASK-002 committed)

## Implementation

### 1. Task Definition

```python
# guardian/queue/tasks.py
@dataclass
class CodingExecutionTask(BaseTask):
    """Queue task for coding execution via PiCodexRunnerAdapter."""
    task_type: str = "coding_execution"
    run_id: str
    deployment_id: str
    prompt: str
    cwd: str | None
    timeout_seconds: int = 300
```

### 2. Worker Implementation

```python
# guardian/workers/coding_worker.py
"""Worker for async coding task execution."""

from __future__ import annotations

from typing import Any

from guardian.agents.adapters import ADAPTERS, AgentExecutionRequest
from guardian.agents.store import AgentStore, store
from guardian.queue import task_events
from guardian.queue.tasks import CodingExecutionTask
from guardian.workers.base import Worker


class CodingWorker(Worker):
    """Processes coding execution tasks from queue."""
    
    name = "coding"
    queue_name = "coding_execution"
    
    def __init__(self, store: AgentStore | None = None):
        self.store = store or AgentStore()
    
    async def process(self, task: CodingExecutionTask) -> None:
        # Publish running
        task_events.publish_task_event(
            task.run_id,
            "task.running",
            {"status": "running"},
        )
        
        # Get adapter
        adapter = ADAPTERS.get("pi_codex_runner")
        if not adapter:
            await self._fail(task.run_id, "Adapter not configured")
            return
        
        # Execute
        request = AgentExecutionRequest(
            prompt=task.prompt,
            cwd=task.cwd,
            timeout_seconds=task.timeout_seconds,
        )
        result = adapter.execute(request)
        
        # Store result
        self.store.create_result(
            run_id=task.run_id,
            status=result.status,
            summary=result.summary,
            artifacts=result.artifacts,
            errors=result.errors,
        )
        
        # Publish terminal event
        event_type = "task.completed" if result.status == "ok" else "task.failed"
        task_events.publish_task_event(
            task.run_id,
            event_type,
            result.model_dump(),
        )
    
    async def _fail(self, run_id: str, error: str) -> None:
        task_events.publish_task_event(
            run_id,
            "task.failed",
            {"error": error},
        )
        self.store.update_run_status(run_id, status="failed")
```

### 3. Enqueue from Route

```python
# In agent_orchestration.py, modify execute_coding_task
from guardian.queue import enqueue_task

# After creating run, enqueue for async processing
task = CodingExecutionTask(
    run_id=run["run_id"],
    deployment_id=deployment["deployment_id"],
    prompt=envelope.instructions,
    cwd=envelope.repo_root,
    timeout_seconds=envelope.permission_policy.max_runtime_seconds,
)
enqueue_task(task)

# Return immediately - client polls for events
return {
    "ok": True,
    "run_id": run["run_id"],
    "status": "queued",
}
```

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/queue/tasks.py guardian/workers/coding_worker.py guardian/routes/agent_orchestration.py
```

## Commit Message (EXACT)

```
TASK-2026-05-01-003: Connect delegation to queue/worker system

Wire coding tasks into existing queue infrastructure.
- Add CodingExecutionTask to queue task types
- Create CodingWorker for async processing
- Emit task events via existing SSE pattern
- Reuse AgentStore for result persistence
```

## Success Criteria

1. Task appears in queue after `POST /coding/execute`
2. Worker processes task asynchronously
3. Task events visible via SSE
4. Lifecycle observable: queued → running → completed/failed