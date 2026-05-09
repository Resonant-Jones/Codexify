# TASK-2026-05-01-002: Wire Adapter into Agent Orchestration Routes

## Task Metadata

- **Task ID**: TASK-2026-05-01-002
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: route_wiring
- **Area**: backend
- **Risk**: MED
- **Owner**: resonant_jones
- **Commit mode**: single-phase
- **Prerequisite**: TASK-2026-05-01-001

## Objective

Wire the `PiCodexRunnerAdapter` into the existing `agent_orchestration.py` routes. The existing deployment/run pattern should be extended to support `pi_codex_runner` as a runtime target.

## Existing Code Context

```python
# guardian/routes/agent_orchestration.py
@router.post("/deployments/{deployment_id}/runs")
async def start_run(deployment_id: str, body: AgentRunStartRequest) -> dict:
    # Creates run via AgentStore
    # Emits task events via AgentEventPublisher
    
@router.get("/runs/{run_id}/events")  
async def stream_run_events(run_id: str) -> StreamingResponse:
    # SSE event stream from task_events
```

## Scope

### In-scope
- Add `pi_codex_runner` to `ALLOWED_RUNTIME_TARGETS`
- Create route for coding task execution via Pi adapter
- Integrate with existing event publishing
- Map `CodingAgentTaskEnvelope` to `AgentExecutionRequest`

### Out-of-scope
- Database migrations (reuse existing AgentRun model)
- Worker implementation (reuse existing patterns)

## Preconditions

```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

**EXPECTED**: No uncommitted changes (TASK-001 committed)

## Implementation

### 1. Extend Runtime Targets

```python
# Add to agent_orchestration.py
ALLOWED_RUNTIME_TARGETS = {"container", "terminal", "pi_codex_runner"}
```

### 2. Add Coding Task Route

```python
from guardian.agents.coding_agent_contracts import (
    CodingAgentTaskEnvelope,
    CodingAgentResult,
)
from guardian.agents.adapters import ADAPTERS, AgentExecutionRequest

@router.post("/coding/execute")
async def execute_coding_task(
    envelope: CodingAgentTaskEnvelope,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute a coding task via PiCodexRunnerAdapter.
    
    Returns immediately with run_id. Poll /runs/{run_id}/events for progress.
    """
    # Create deployment
    deployment = _store.create_deployment(
        flow_id=f"coding_{envelope.coding_task_id}",
        thread_id=int(envelope.thread_id) if envelope.thread_id else None,
        spec_json=envelope.model_dump(),
        spec_hash=hashlib.sha256(
            json.dumps(envelope.model_dump(), sort_keys=True).encode()
        ).hexdigest()[:16],
        trust_state="supervised",
    )
    
    # Create run
    run = _store.create_run(
        deployment_id=deployment["deployment_id"],
        thread_id=deployment.get("thread_id"),
        runtime_target="pi_codex_runner",
        rollback_mode="auto",
        status="pending",
    )
    
    # Emit created event
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="created",
        payload={
            "coding_task_id": envelope.coding_task_id,
            "attempt_id": envelope.attempt_id,
        },
    )
    
    return {
        "ok": True,
        "run_id": run["run_id"],
        "deployment_id": deployment["deployment_id"],
        "coding_task_id": envelope.coding_task_id,
    }
```

### 3. Update Existing Start Run Logic

In `start_run`, handle `pi_codex_runner` runtime target by executing immediately:

```python
if runtime_target == "pi_codex_runner":
    # Get adapter
    adapter = ADAPTERS.get("pi_codex_runner")
    if not adapter:
        raise HTTPException(500, "pi_codex_runner adapter not configured")
    
    # Build request from deployment spec
    spec = deployment.get("spec_json", {})
    request = AgentExecutionRequest(
        prompt=spec.get("instructions", ""),
        cwd=spec.get("repo_root"),
        timeout_seconds=spec.get("permission_policy", {}).get("max_runtime_seconds", 300),
    )
    
    # Execute
    result = adapter.execute(request)
    
    # Store result
    _store.create_result(
        run_id=run["run_id"],
        status=result.status,
        summary=result.summary,
        artifacts=result.artifacts,
        errors=result.errors,
    )
    
    # Emit terminal event
    _event_publisher.emit(
        run_id=run["run_id"],
        event_type="completed" if result.status == "ok" else "failed",
        payload=result.model_dump(),
    )
```

## Execution Plan

```bash
cd <REPO_ROOT>

# 1. Verify preconditions
git status --porcelain -uall

# 2. Add route and wiring to agent_orchestration.py
# (Manual edit following the patterns above)

# 3. Run import check
python -c "
from guardian.agents.adapters import ADAPTERS
from guardian.agents.coding_agent_contracts import CodingAgentTaskEnvelope
print('ok')
"

# 4. Verify changes
git status --porcelain -uall
```

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/routes/agent_orchestration.py
git status --porcelain -uall
```

## Commit Message (EXACT)

```
TASK-2026-05-01-002: Wire adapter into agent orchestration routes

Connect PiCodexRunnerAdapter to existing Guardian routes.
- Add pi_codex_runner to ALLOWED_RUNTIME_TARGETS
- Add POST /coding/execute route for direct execution
- Emit task events via existing publisher
- Reuse AgentStore for deployment/run tracking
```

## Success Criteria

1. `POST /api/agents/coding/execute` accepts `CodingAgentTaskEnvelope`
2. Returns `run_id` immediately for SSE polling
3. Task events visible via `/api/agents/runs/{run_id}/events`
4. Adapter executes and result is stored