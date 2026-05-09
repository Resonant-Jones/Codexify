# TASK-2026-05-01-002: Create Pi Tool Wrapper for Codex Runner

## Task Metadata

- **Task ID**: TASK-2026-05-01-002
- **Campaign ID**: CAMPAIGN-2026-05-01_001_PI_CODER_INTEGRATION
- **Slug**: pi_tool_wrapper
- **Area**: backend
- **Risk**: MED
- **Owner**: resonant_jones
- **Commit mode**: single-phase
- **Prerequisite**: TASK-2026-05-01-001

## Objective

Create a Node.js/Python bridge that registers Codex Runner as a tool that Pi can invoke. This establishes the execution substrate per ADR-020 where Pi is the execution engine and Codex Runner is a specialized tool.

## Scope

### In-scope
- Extend `codex_runner/src/agent-wrapper.js` to accept the `CodingTaskEnvelope` format
- Create a Python adapter that can invoke the Node.js wrapper with proper envelope handling
- Add profile selection based on `envelope.profile`
- Handle workspace scope and allowed paths

### Out-of-scope
- Queue wiring (TASK-003)
- SSE event handling
- Database persistence

## Preconditions

```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

**EXPECTED**: No uncommitted changes (TASK-001 committed)

## Implementation

```bash
cd <REPO_ROOT>

# 1. Verify preconditions
git status --porcelain -uall

# 2. Create Python adapter
cat > guardian/agents/pi_adapter.py << 'EOF'
"""Pi adapter for Codex Runner integration per ADR-020."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from guardian.agents.coding_task import CodingTaskEnvelope, CodingTaskResult, CodingTaskStatus


# Path to the Pi agent wrapper
PI_WRAPPER = Path(__file__).parent.parent.parent / "codex_runner" / "src" / "agent-wrapper.js"


@dataclass
class PiToolConfig:
    """Configuration for Pi tool execution."""
    wrapper_path: Path = PI_WRAPPER
    timeout_seconds: int = 300
    verbose: bool = False


class PiCodexRunnerAdapter:
    """Adapter that invokes Codex Runner through the Pi agent wrapper."""

    def __init__(self, config: PiToolConfig | None = None):
        self.config = config or PiToolConfig()

    def execute_task(self, envelope: CodingTaskEnvelope) -> CodingTaskResult:
        """Execute a coding task through Pi agent wrapper.
        
        Args:
            envelope: The Guardian-issued coding task envelope
            
        Returns:
            CodingTaskResult with execution outcome
            
        Raises:
            RuntimeError: If execution fails
        """
        # Build execution environment
        env = os.environ.copy()
        
        # Set model and thinking level from profile
        profile = self._load_profile(envelope.profile or "default")
        env["PI_MODEL"] = profile.get("model", "claude-sonnet-4-20250514")
        env["PI_THINKING"] = profile.get("thinking", "medium")
        
        if self.config.verbose:
            env["PI_VERBOSE"] = "1"
        
        # Build the prompt from envelope instructions
        prompt = self._build_prompt(envelope)
        
        # Set working directory to workspace scope
        cwd = envelope.workspace_scope or os.getcwd()
        
        # Execute via Node.js wrapper
        cmd = ["node", str(self.config.wrapper_path), "task", prompt]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
            
            # Parse result
            if result.returncode == 0:
                return self._parse_success(envelope, result.stdout)
            else:
                return self._parse_error(envelope, result.stderr or result.stdout)
                
        except subprocess.TimeoutExpired:
            return CodingTaskResult(
                coding_task_id=envelope.coding_task_id,
                request_id=envelope.request_id,
                status=CodingTaskStatus.FAILED,
                summary="Execution timed out",
                error_code="TIMEOUT",
                error_message=f"Task exceeded {self.config.timeout_seconds}s timeout",
            )
        except FileNotFoundError:
            return CodingTaskResult(
                coding_task_id=envelope.coding_task_id,
                request_id=envelope.request_id,
                status=CodingTaskStatus.BLOCKED,
                summary="Execution environment unavailable",
                error_code="ENV_NOT_FOUND",
                error_message="Node.js or Pi wrapper not found",
            )

    def _load_profile(self, profile_name: str) -> dict[str, Any]:
        """Load profile from Codex Runner profile system."""
        from codex_runner.src.profile import ProfileManager
        
        pm = ProfileManager().load()
        profile = pm.get(profile_name)
        
        if not profile:
            return {}
        
        return profile.to_dict()

    def _build_prompt(self, envelope: CodingTaskEnvelope) -> str:
        """Build execution prompt from envelope."""
        parts = [
            f"Instructions: {envelope.instructions}",
        ]
        
        if envelope.context_bundle_summary:
            parts.append(f"Context: {envelope.context_bundle_summary}")
        
        if envelope.allowed_paths:
            parts.append(f"Allowed paths: {', '.join(envelope.allowed_paths)}")
        
        if envelope.permission_policy.require_confirmation:
            parts.append(
                f"Requires confirmation: {', '.join(envelope.permission_policy.require_confirmation)}"
            )
        
        parts.append(
            "Report results as JSON with: summary, files_changed, artifacts"
        )
        
        return "\n\n".join(parts)

    def _parse_success(self, envelope: CodingTaskEnvelope, output: str) -> CodingTaskResult:
        """Parse successful execution output."""
        try:
            data = json.loads(output)
            return CodingTaskResult(
                coding_task_id=envelope.coding_task_id,
                request_id=envelope.request_id,
                status=CodingTaskStatus.SUCCESS,
                summary=data.get("summary", data.get("text", "Task completed")),
                files_changed=data.get("files_changed", []),
                artifacts=data.get("artifacts", []),
                logs_summary=data.get("logs_summary", ""),
            )
        except json.JSONDecodeError:
            # Non-JSON output - treat as text summary
            return CodingTaskResult(
                coding_task_id=envelope.coding_task_id,
                request_id=envelope.request_id,
                status=CodingTaskStatus.SUCCESS,
                summary=output.strip()[:500],
            )

    def _parse_error(self, envelope: CodingTaskEnvelope, error_output: str) -> CodingTaskResult:
        """Parse error from failed execution."""
        return CodingTaskResult(
            coding_task_id=envelope.coding_task_id,
            request_id=envelope.request_id,
            status=CodingTaskStatus.FAILED,
            summary="Task execution failed",
            error_code="EXECUTION_ERROR",
            error_message=error_output.strip()[:1000],
        )


def create_adapter() -> PiCodexRunnerAdapter:
    """Factory function to create the adapter."""
    return PiCodexRunnerAdapter()
EOF

# 3. Run import check
python -c "from guardian.agents.pi_adapter import PiCodexRunnerAdapter; print('ok')"

# 4. Verify changes
git status --porcelain -uall
```

**EXPECTED OUTPUT**: `ok` printed, only new files created

## Rollback

```bash
cd <REPO_ROOT>
git checkout -- guardian/agents/pi_adapter.py
git status --porcelain -uall
```

## Commit Message (EXACT)

```
TASK-2026-05-01-002: Create Pi tool wrapper for Codex Runner

Bridge between Guardian envelope and Pi agent wrapper for Codex Runner.
- Add PiCodexRunnerAdapter class
- Add execute_task method with envelope handling
- Add profile loading from Codex Runner profile system
- Add workspace scope and path handling
```

## Success Criteria

1. Import check passes
2. `execute_task()` accepts `CodingTaskEnvelope` and returns `CodingTaskResult`
3. Profile loading works with Codex Runner profile system
4. Error handling returns proper `CodingTaskResult` with `BLOCKED` or `FAILED` status