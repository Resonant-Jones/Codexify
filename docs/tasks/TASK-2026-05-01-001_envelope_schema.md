# TASK-2026-05-01-001: Define CodingTaskEnvelope Schema

## Task Metadata

- **Task ID**: TASK-2026-05-01-001
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: envelope_schema
- **Area**: backend
- **Risk**: LOW
- **Owner**: resonant_jones
- **Commit mode**: single-phase

## Objective

Define the `CodingTaskEnvelope` dataclass and related types per ADR-020 contract. This establishes the request path contract between Guardian and any coding-agent adapter.

## Scope

### In-scope
- `guardian/agents/coding_task.py` - New module for envelope schema
- Define all required fields per ADR-020
- Include validation and serialization helpers
- Type stubs for integration with existing queue system

### Out-of-scope
- Queue wiring (TASK-003)
- Result schema (TASK-004)
- Pi tool registration (TASK-002)
- Database migrations

## Allowed Files (STRICT)

- `guardian/agents/coding_task.py` (NEW)
- `guardian/agents/__init__.py` (update exports)
- `docs/tasks/TASK-2026-05-01-001_envelope_schema.md` (this file)
- `docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`

## Preconditions

```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

**EXPECTED**: No uncommitted changes

## Schema Definition

The `CodingTaskEnvelope` must include all required fields per ADR-020:

### Request Envelope

| Field | Type | Description |
|-------|------|-------------|
| `coding_task_id` | `str` | Guardian-owned task identity |
| `thread_id` | `str` | Source chat thread |
| `source_message_id` | `str` | User-authored message |
| `request_id` | `str` | Attempt/execution identity |
| `actor` | `str` | Resolved user or acting subject |
| `project_id` | `str \| None` | Optional project scope |
| `workspace_scope` | `str \| None` | Repository root or workspace path |
| `allowed_paths` | `list[str]` | Filesystem paths adapter may touch |
| `instructions` | `str` | Bounded coding instructions |
| `context_bundle_summary` | `str` | Guardian-owned context summary |
| `permission_policy` | `dict` | Capability and boundary policy |
| `adapter_kind` | `str` | Target adapter ("pi" or "codex_runner") |
| `profile` | `str \| None` | Profile name for execution config |

### Result Payload (for reference in TASK-004)

| Field | Type | Description |
|-------|------|-------------|
| `coding_task_id` | `str` | Links result to task |
| `request_id` | `str` | Links to specific attempt |
| `status` | `str` | "pending", "running", "success", "failed", "blocked" |
| `summary` | `str` | Human-readable result |
| `files_changed` | `list[str]` | Adapter-reported changes |
| `artifacts` | `list[dict]` | Generated outputs |
| `logs_summary` | `str` | Condensed execution trace |
| `error_code` | `str \| None` | Failure details |
| `adapter_session_ref` | `str \| None` | Handle for session lookup |

## Implementation Checklist

- [ ] Create `guardian/agents/coding_task.py`
- [ ] Define `CodingTaskEnvelope` dataclass with all required fields
- [ ] Add `CodingTaskStatus` enum
- [ ] Add `CodingTaskResult` dataclass (stub for TASK-004)
- [ ] Add `AdapterKind` enum ("pi", "codex_runner")
- [ ] Add `PermissionPolicy` dataclass
- [ ] Add `to_dict()` / `from_dict()` serialization helpers
- [ ] Add field validation (non-empty required fields)
- [ ] Update `guardian/agents/__init__.py` exports
- [ ] Write unit tests

## Execution Plan

```bash
cd <REPO_ROOT>

# 1. Verify preconditions
git status --porcelain -uall

# 2. Create the module
cat > guardian/agents/coding_task.py << 'EOF'
"""Coding task envelope schema per ADR-020."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AdapterKind(str, Enum):
    """Coding agent adapter types."""
    PI = "pi"
    CODEX_RUNNER = "codex_runner"


class CodingTaskStatus(str, Enum):
    """Coding task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class PermissionPolicy:
    """Guardian-issued permission and boundary policy."""
    allowed_paths: list[str] = field(default_factory=list)
    max_file_size_mb: int = 10
    allow_destructive: bool = False
    require_confirmation: list[str] = field(default_factory=list)
    timeout_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_paths": self.allowed_paths,
            "max_file_size_mb": self.max_file_size_mb,
            "allow_destructive": self.allow_destructive,
            "require_confirmation": self.require_confirmation,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionPolicy:
        return cls(
            allowed_paths=data.get("allowed_paths", []),
            max_file_size_mb=data.get("max_file_size_mb", 10),
            allow_destructive=data.get("allow_destructive", False),
            require_confirmation=data.get("require_confirmation", []),
            timeout_seconds=data.get("timeout_seconds", 300),
        )


@dataclass
class CodingTaskEnvelope:
    """Guardian-mediated coding task envelope per ADR-020."""
    coding_task_id: str
    thread_id: str
    source_message_id: str
    request_id: str
    actor: str
    instructions: str
    adapter_kind: AdapterKind
    # Optional fields
    project_id: str | None = None
    workspace_scope: str | None = None
    allowed_paths: list[str] = field(default_factory=list)
    context_bundle_summary: str = ""
    permission_policy: PermissionPolicy = field(default_factory=PermissionPolicy)
    profile: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate required fields. Returns list of error messages."""
        errors = []
        if not self.coding_task_id:
            errors.append("coding_task_id is required")
        if not self.thread_id:
            errors.append("thread_id is required")
        if not self.source_message_id:
            errors.append("source_message_id is required")
        if not self.request_id:
            errors.append("request_id is required")
        if not self.actor:
            errors.append("actor is required")
        if not self.instructions:
            errors.append("instructions is required")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "coding_task_id": self.coding_task_id,
            "thread_id": self.thread_id,
            "source_message_id": self.source_message_id,
            "request_id": self.request_id,
            "actor": self.actor,
            "project_id": self.project_id,
            "workspace_scope": self.workspace_scope,
            "allowed_paths": self.allowed_paths,
            "context_bundle_summary": self.context_bundle_summary,
            "permission_policy": self.permission_policy.to_dict(),
            "adapter_kind": self.adapter_kind.value,
            "profile": self.profile,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodingTaskEnvelope:
        policy_data = data.get("permission_policy", {})
        return cls(
            coding_task_id=data["coding_task_id"],
            thread_id=data["thread_id"],
            source_message_id=data["source_message_id"],
            request_id=data["request_id"],
            actor=data["actor"],
            instructions=data["instructions"],
            adapter_kind=AdapterKind(data.get("adapter_kind", "pi")),
            project_id=data.get("project_id"),
            workspace_scope=data.get("workspace_scope"),
            allowed_paths=data.get("allowed_paths", []),
            context_bundle_summary=data.get("context_bundle_summary", ""),
            permission_policy=PermissionPolicy.from_dict(policy_data),
            profile=data.get("profile"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CodingTaskResult:
    """Coding task result payload per ADR-020."""
    coding_task_id: str
    request_id: str
    status: CodingTaskStatus
    summary: str
    files_changed: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    logs_summary: str = ""
    error_code: str | None = None
    error_message: str | None = None
    adapter_session_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "coding_task_id": self.coding_task_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "summary": self.summary,
            "files_changed": self.files_changed,
            "artifacts": self.artifacts,
            "logs_summary": self.logs_summary,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "adapter_session_ref": self.adapter_session_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodingTaskResult:
        return cls(
            coding_task_id=data["coding_task_id"],
            request_id=data["request_id"],
            status=CodingTaskStatus(data["status"]),
            summary=data.get("summary", ""),
            files_changed=data.get("files_changed", []),
            artifacts=data.get("artifacts", []),
            logs_summary=data.get("logs_summary", ""),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            adapter_session_ref=data.get("adapter_session_ref"),
        )
EOF

# 3. Update __init__.py
cat >> guardian/agents/__init__.py << 'EOF'

from guardian.agents.coding_task import (
    AdapterKind,
    CodingTaskEnvelope,
    CodingTaskResult,
    CodingTaskStatus,
    PermissionPolicy,
)

__all__ = [
    "AdapterKind",
    "CodingTaskEnvelope",
    "CodingTaskResult",
    "CodingTaskStatus",
    "PermissionPolicy",
]
EOF

# 4. Run import check
python -c "from guardian.agents.coding_task import CodingTaskEnvelope, CodingTaskResult, AdapterKind; print('ok')"

# 5. Verify no additional changes
git status --porcelain -uall
```

**EXPECTED OUTPUT**: 
- `ok` printed on import check
- Only `guardian/agents/coding_task.py` and `guardian/agents/__init__.py` modified

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/agents/coding_task.py guardian/agents/__init__.py
git status --porcelain -uall
```

## Commit Message (EXACT)

```
TASK-2026-05-01-001: Define CodingTaskEnvelope schema

Per ADR-020 contract, define the Guardian-mediated coding task
envelope with required fields for request identity, lineage,
and permission policy.

- Add CodingTaskEnvelope dataclass
- Add CodingTaskResult dataclass  
- Add PermissionPolicy dataclass
- Add AdapterKind and CodingTaskStatus enums
- Add serialization helpers (to_dict/from_dict)
- Add field validation
```

## Success Criteria

1. Import check passes: `python -c "from guardian.agents.coding_task import ..."`
2. All required ADR-020 fields present in `CodingTaskEnvelope`
3. `validate()` returns errors for missing required fields
4. Serialization round-trips correctly: `from_dict(to_dict())`
5. Only specified files modified