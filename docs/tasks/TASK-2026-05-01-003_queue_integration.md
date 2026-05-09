# TASK-2026-05-01-003: Implement Delegation Queue Integration

## Task Metadata

- **Task ID**: TASK-2026-05-01-003
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: queue_integration
- **Area**: backend
- **Risk**: MED
- **Owner**: resonant_jones
- **Commit mode**: single-phase
- **Prerequisite**: TASK-2026-05-01-002

## Objective

Wire the Pi/Codes Runner adapter into the existing Guardian queue infrastructure. Tasks are queue-backed and should use the existing Redis queue pattern with SSE task events.

## Scope

### In-scope
- Define `CodingDelegationTask` for the queue
- Create delegation route in `guardian/routes/agent_orchestration.py`
- Create worker in `guardian/workers/coding_worker.py`
- Wire task events via existing SSE pattern
- Handle lifecycle: `pending` → `running` → `success`/`failed`

### Out-of-scope
- Result ingestion (TASK-004)
- Frontend UI changes
- Database migrations (can add to existing models)

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
class CodingDelegationTask(BaseTask):
    """Queue task for coding agent delegation."""
    task_type: str = "coding_delegation"
    coding_task_id: str
    envelope_json: str  # Serialized CodingTaskEnvelope
    adapter_kind: str
```

### 2. Route Handler

```python
# guardian/routes/agent_orchestration.py
@router.post("/coding/delegation")
async def delegate_coding_task(
    envelope: CodingTaskEnvelope,
    current_user: User = Depends(get_current_user),
):
    # Validate envelope
    errors = envelope.validate()
    if errors:
        raise HTTPException(400, "\n".join(errors))
    
    # Create task
    task = CodingDelegationTask(
        coding_task_id=envelope.coding_task_id,
        envelope_json=json.dumps(envelope.to_dict()),
        adapter_kind=envelope.adapter_kind.value,
    )
    
    # Enqueue
    queue = get_queue()
    await queue.enqueue(task)
    
    # Publish task.created event
    await publish_task_event(
        task_id=task.id,
        event_type="task.created",
        data={"coding_task_id": envelope.coding_task_id},
    )
    
    return {
        "task_id": task.id,
        "coding_task_id": envelope.coding_task_id,
        "status": "accepted",
    }
```

### 3. Worker

```python
# guardian/workers/coding_worker.py
async def process_delegation(task: CodingDelegationTask):
    envelope = CodingTaskEnvelope.from_dict(json.loads(task.envelope_json))
    
    # Publish running
    await publish_task_event(task.id, "task.running", {})
    
    # Execute via appropriate adapter
    if task.adapter_kind == "codex_runner":
        adapter = PiCodexRunnerAdapter()
        result = adapter.execute_task(envelope)
    else:
        raise ValueError(f"Unknown adapter: {task.adapter_kind}")
    
    # Store result
    await store_coding_result(result)
    
    # Publish terminal event
    await publish_task_event(
        task.id, 
        "task.completed" if result.status == CodingTaskStatus.SUCCESS else "task.failed",
        result.to_dict()
    )
    
    return result
```

## Task Event Format

```json
{
  "type": "coding_task_event",
  "task_id": "uuid",
  "event": "task.running | task.completed | task.failed",
  "coding_task_id": "string",
  "request_id": "string",
  "status": "string",
  "summary": "string",
  "timestamp": "ISO-8601"
}
```

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/queue/tasks.py guardian/routes/agent_orchestration.py guardian/workers/coding_worker.py
git status --porcelain -uall
```

## Commit Message (EXACT)

```
TASK-2026-05-01-003: Implement delegation queue integration

Wire coding delegation into Guardian queue infrastructure.
- Add CodingDelegationTask to queue task types
- Create POST /coding/delegation route
- Add coding worker with Pi adapter invocation
- Wire task events via SSE pattern
- Implement lifecycle: pending → running → terminal
```

## Success Criteria

1. Route accepts `CodingTaskEnvelope` and returns `task_id`
2. Task appears in queue and worker processes it
3. Task events published via SSE pattern
4. Lifecycle state transitions observable