# TASK-2026-05-01-001: Create PiCodexRunnerAdapter

## Task Metadata

- **Task ID**: TASK-2026-05-01-001
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: pi_adapter
- **Area**: backend
- **Risk**: MED
- **Owner**: resonant_jones
- **Commit mode**: single-phase

## Objective

Create a `PiCodexRunnerAdapter` that implements the existing `AgentAdapter` protocol from `guardian/agents/adapters/base.py`. This adapter will invoke the Codex Runner via the Pi agent wrapper, bridging the existing codebase with our new Pi integration.

## Existing Code Context

```python
# guardian/agents/adapters/base.py
class AgentAdapter(Protocol):
    name: str
    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope: ...

class AgentExecutionRequest:
    prompt: str
    cwd: str | None = None
    timeout_seconds: int = 120

class AgentRunEnvelope:
    status: str
    summary: str
    artifacts: list[dict]
    next_actions: list[str]
    errors: list[str]
```

## Scope

### In-scope
- Create `guardian/agents/adapters/pi_codex_runner.py` implementing `AgentAdapter`
- Use existing `codex_runner/src/agent-wrapper.js` via Node.js subprocess
- Map profile selection from envelope or env vars
- Handle workspace scope and timeout

### Out-of-scope
- Queue wiring (TASK-003)
- SSE event handling
- Database persistence

## Preconditions

```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

**EXPECTED**: No uncommitted changes

## Implementation

```python
# guardian/agents/adapters/pi_codex_runner.py
"""Pi-powered Codex Runner adapter implementing AgentAdapter protocol."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from guardian.agents.adapters.base import (
    AgentAdapter,
    AgentExecutionRequest,
    AgentRunEnvelope,
)

# Path to the Pi agent wrapper
PI_WRAPPER = Path(__file__).parent.parent.parent.parent / "codex_runner" / "src" / "agent-wrapper.js"


class PiCodexRunnerAdapter:
    """Adapter that invokes Codex Runner through the Pi agent wrapper.
    
    Implements AgentAdapter protocol for Guardian orchestration.
    """

    name = "pi_codex_runner"

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        """Execute a coding task through Pi agent wrapper.
        
        Args:
            request: AgentExecutionRequest with prompt and execution context
            
        Returns:
            AgentRunEnvelope with execution results
        """
        # Build execution environment
        env = os.environ.copy()
        
        # Set model and thinking from environment or defaults
        env["PI_MODEL"] = env.get("PI_MODEL", "claude-sonnet-4-20250514")
        env["PI_THINKING"] = env.get("PI_THINKING", "medium")
        
        # Build the command
        cmd = ["node", str(PI_WRAPPER), "task", request.prompt]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            
            return self._parse_result(result, request.prompt)
            
        except subprocess.TimeoutExpired:
            return AgentRunEnvelope(
                status="error",
                summary=f"Execution timed out after {request.timeout_seconds}s",
                artifacts=[],
                next_actions=[],
                errors=["timeout_expired"],
                metrics={"timeout_seconds": request.timeout_seconds},
            )
        except FileNotFoundError:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent wrapper not found (Node.js or wrapper.js missing)",
                artifacts=[],
                next_actions=[],
                errors=["pi_wrapper_not_found"],
                metrics={},
            )

    def _parse_result(
        self, result: subprocess.CompletedProcess, prompt: str
    ) -> AgentRunEnvelope:
        """Parse subprocess result into AgentRunEnvelope."""
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        
        if result.returncode != 0:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent execution failed",
                artifacts=[],
                next_actions=[],
                errors=[stderr or f"exit_code={result.returncode}"],
                metrics={"returncode": result.returncode},
            )
        
        # Try to parse JSON output
        if stdout:
            try:
                data = json.loads(stdout)
                return AgentRunEnvelope(
                    status=data.get("status", "ok"),
                    summary=data.get("summary", data.get("text", "Task completed")),
                    artifacts=data.get("artifacts", []),
                    next_actions=data.get("next_actions", []),
                    errors=data.get("errors", []),
                    metrics=data.get("metrics", {}),
                )
            except json.JSONDecodeError:
                # Non-JSON output - wrap as text summary
                return AgentRunEnvelope(
                    status="ok",
                    summary=stdout[:500] if stdout else "Task completed",
                    artifacts=[],
                    next_actions=[],
                    errors=[],
                    metrics={},
                )
        
        return AgentRunEnvelope(
            status="ok",
            summary="Task completed with no output",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )


# Register in adapters __init__.py
ADAPTERS["pi_codex_runner"] = PiCodexRunnerAdapter()
```

## Execution Plan

```bash
cd <REPO_ROOT>

# 1. Verify preconditions
git status --porcelain -uall

# 2. Create the adapter
cat > guardian/agents/adapters/pi_codex_runner.py << 'EOF'
"""Pi-powered Codex Runner adapter implementing AgentAdapter protocol."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from guardian.agents.adapters.base import (
    AgentAdapter,
    AgentExecutionRequest,
    AgentRunEnvelope,
)

# Path to the Pi agent wrapper (relative to this file)
def _get_pi_wrapper_path() -> Path:
    # Go up: adapters -> agents -> guardian -> repo_root
    repo_root = Path(__file__).parent.parent.parent.parent
    return repo_root / "codex_runner" / "src" / "agent-wrapper.js"


class PiCodexRunnerAdapter:
    """Adapter that invokes Codex Runner through the Pi agent wrapper.
    
    Implements AgentAdapter protocol for Guardian orchestration.
    """

    name = "pi_codex_runner"

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        """Execute a coding task through Pi agent wrapper."""
        env = os.environ.copy()
        env["PI_MODEL"] = env.get("PI_MODEL", "claude-sonnet-4-20250514")
        env["PI_THINKING"] = env.get("PI_THINKING", "medium")
        
        cmd = ["node", str(_get_pi_wrapper_path()), "task", request.prompt]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            return self._parse_result(result)
            
        except subprocess.TimeoutExpired:
            return AgentRunEnvelope(
                status="error",
                summary=f"Execution timed out after {request.timeout_seconds}s",
                artifacts=[],
                next_actions=[],
                errors=["timeout_expired"],
                metrics={"timeout_seconds": request.timeout_seconds},
            )
        except FileNotFoundError:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent wrapper not found",
                artifacts=[],
                next_actions=[],
                errors=["pi_wrapper_not_found"],
                metrics={},
            )

    def _parse_result(self, result: subprocess.CompletedProcess) -> AgentRunEnvelope:
        """Parse subprocess result into AgentRunEnvelope."""
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        
        if result.returncode != 0:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent execution failed",
                artifacts=[],
                next_actions=[],
                errors=[stderr or f"exit_code={result.returncode}"],
                metrics={"returncode": result.returncode},
            )
        
        if stdout:
            try:
                data = json.loads(stdout)
                return AgentRunEnvelope(
                    status=data.get("status", "ok"),
                    summary=data.get("summary", data.get("text", "Task completed")),
                    artifacts=data.get("artifacts", []),
                    next_actions=data.get("next_actions", []),
                    errors=data.get("errors", []),
                    metrics=data.get("metrics", {}),
                )
            except json.JSONDecodeError:
                return AgentRunEnvelope(
                    status="ok",
                    summary=stdout[:500] if stdout else "Task completed",
                    artifacts=[],
                    next_actions=[],
                    errors=[],
                    metrics={},
                )
        
        return AgentRunEnvelope(
            status="ok",
            summary="Task completed with no output",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )
EOF

# 3. Update adapters __init__.py to register
cat >> guardian/agents/adapters/__init__.py << 'EOF'
from .pi_codex_runner import PiCodexRunnerAdapter

ADAPTERS["pi_codex_runner"] = PiCodexRunnerAdapter()

__all__ = [
    *_all__,
    "PiCodexRunnerAdapter",
]
EOF

# 4. Run import check
python -c "from guardian.agents.adapters import PiCodexRunnerAdapter, ADAPTERS; print('ok', ADAPTERS.keys())"

# 5. Verify changes
git status --porcelain -uall
```

**EXPECTED OUTPUT**: `ok dict_keys(...)` showing pi_codex_runner registered

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/agents/adapters/pi_codex_runner.py guardian/agents/adapters/__init__.py
git status --porcelain -uall
```

## Commit Message (EXACT)

```
TASK-2026-05-01-001: Create PiCodexRunnerAdapter

Implement AgentAdapter protocol for Pi-powered Codex Runner execution.
- Add PiCodexRunnerAdapter class implementing AgentAdapter
- Use existing codex_runner/src/agent-wrapper.js
- Handle timeout and error cases
- Register in ADAPTERS registry
```

## Success Criteria

1. `from guardian.agents.adapters import PiCodexRunnerAdapter, ADAPTERS` works
2. `ADAPTERS["pi_codex_runner"]` returns valid adapter instance
3. `adapter.execute(request)` accepts `AgentExecutionRequest` and returns `AgentRunEnvelope`
4. Timeout and FileNotFoundError cases return proper error envelopes
5. JSON output from wrapper parsed correctly into envelope