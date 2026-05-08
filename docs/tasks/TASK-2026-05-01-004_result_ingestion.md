# TASK-2026-05-01-004: Implement Result Ingestion and Thread Injection

## Task Metadata

- **Task ID**: TASK-2026-05-01-004
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: result_ingestion
- **Area**: backend
- **Risk**: MED
- **Owner**: resonant_jones
- **Commit mode**: single-phase
- **Prerequisite**: TASK-2026-05-01-003

## Objective

Implement the result ingestion path per ADR-020: results must return through Guardian before any user-visible output. Inject summaries into the source thread as assistant messages.

## Scope

### In-scope
- Result storage in Postgres (coding_task_results table)
- Thread injection: create assistant message in source thread
- Idempotency: prevent duplicate result injection
- Lineage preservation: maintain source_thread_id, source_message_id
- Error handling: blocked/failed results with proper escalation

### Out-of-scope
- Frontend UI display of results
- Real-time SSE streaming of results (handled by TASK-003)
- Approval workflow UI

## Preconditions

```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

**EXPECTED**: No uncommitted changes (TASK-003 committed)

## Implementation

### 1. Database Model

```python
# guardian/db/models.py

class CodingTaskResultModel(Base):
    __tablename__ = "coding_task_results"
    
    id = Column(String, primary_key=True)
    coding_task_id = Column(String, nullable=False, index=True)
    request_id = Column(String, nullable=False)
    thread_id = Column(String, nullable=False, index=True)
    source_message_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    files_changed = Column(JSON, default=list)
    artifacts = Column(JSON, default=list)
    logs_summary = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    adapter_session_ref = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2. Result Storage Service

```python
# guardian/agents/result_store.py

async def store_coding_result(
    result: CodingTaskResult,
    thread_id: str,
    source_message_id: str,
) -> str:
    """Store coding result and inject into thread.
    
    Returns result_id if successful.
    Raises if duplicate or lineage violation.
    """
    # Check idempotency
    existing = db.query(CodingTaskResultModel).filter(
        CodingTaskResultModel.coding_task_id == result.coding_task_id,
        CodingTaskResultModel.request_id == result.request_id,
    ).first()
    
    if existing:
        return existing.id
    
    # Validate lineage
    if not thread_id or not source_message_id:
        raise ValueError("Lineage violation: thread_id and source_message_id required")
    
    # Store result
    result_row = CodingTaskResultModel(
        id=generate_id(),
        coding_task_id=result.coding_task_id,
        request_id=result.request_id,
        thread_id=thread_id,
        source_message_id=source_message_id,
        status=result.status.value,
        summary=result.summary,
        files_changed=result.files_changed,
        artifacts=result.artifacts,
        logs_summary=result.logs_summary,
        error_code=result.error_code,
        error_message=result.error_message,
        adapter_session_ref=result.adapter_session_ref,
    )
    db.add(result_row)
    db.commit()
    
    # Inject into thread
    await inject_result_into_thread(result_row)
    
    return result_row.id


async def inject_result_into_thread(result_row: CodingTaskResultModel):
    """Create assistant message in source thread with result summary."""
    # Check if message already exists (idempotency)
    existing = db.query(ChatMessage).filter(
        ChatMessage.thread_id == result_row.thread_id,
        ChatMessage.metadata["coding_task_id"] == result_row.coding_task_id,
    ).first()
    
    if existing:
        return existing.id
    
    # Build summary message
    content_parts = [f"## Coding Task Result\n\n"]
    content_parts.append(f"**Status**: {result_row.status}\n\n")
    content_parts.append(f"**Summary**: {result_row.summary}\n\n")
    
    if result_row.files_changed:
        content_parts.append(f"**Files Changed**:\n")
        for f in result_row.files_changed:
            content_parts.append(f"- `{f}`\n")
        content_parts.append("\n")
    
    if result_row.artifacts:
        content_parts.append(f"**Artifacts**:\n")
        for a in result_row.artifacts:
            content_parts.append(f"- {a.get('name', 'unnamed')}\n")
        content_parts.append("\n")
    
    if result_row.error_code:
        content_parts.append(f"**Error**: {result_row.error_code}\n")
        if result_row.error_message:
            content_parts.append(f"```\n{result_row.error_message}\n```\n")
    
    # Create assistant message
    message = ChatMessage(
        thread_id=result_row.thread_id,
        role="assistant",
        content="".join(content_parts),
        metadata={
            "coding_task_id": result_row.coding_task_id,
            "request_id": result_row.request_id,
            "source_message_id": result_row.source_message_id,
            "type": "coding_result",
        },
    )
    db.add(message)
    db.commit()
    
    return message.id
```

### 3. Integration with Worker

In `guardian/workers/coding_worker.py`, after execution:

```python
# Store result with proper lineage
result_id = await store_coding_result(
    result=result,
    thread_id=envelope.thread_id,
    source_message_id=envelope.source_message_id,
)
```

## Success Criteria

1. Result stored in `coding_task_results` table
2. Assistant message created in source thread
3. Idempotency: rerunning doesn't create duplicates
4. Lineage preserved: `source_thread_id`, `source_message_id` in both tables
5. Error results handled gracefully with escalation message

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/db/models.py guardian/agents/result_store.py guardian/workers/coding_worker.py
```

## Commit Message (EXACT)

```
TASK-2026-05-01-004: Implement result ingestion and thread injection

Per ADR-020, results must return through Guardian before user-visible
output. Inject coding results into source thread as assistant messages.

- Add CodingTaskResultModel to database
- Add result_store service with idempotency
- Add thread injection with proper lineage
- Handle error/blocked states with escalation
```

## Expected Outcome

After completing all four tasks, the full delegation pipeline is operational:

```
Guardian (request) → Queue → Worker → Pi + Codex Runner
                                    ↓
                    Result ← Guardian (ingestion) ← Thread injection
```