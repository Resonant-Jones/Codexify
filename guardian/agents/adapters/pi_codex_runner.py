"""Pi-powered Codex Runner adapter implementing AgentAdapter protocol."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from guardian.agents.adapters.base import (
    AgentAdapter,
    AgentExecutionIdentity,
    AgentExecutionRequest,
    AgentRunEnvelope,
)
from guardian.pi.tokens import (
    PI_AUTHORIZED_FAILURE_CLASSES,
    PiAuthorizedFailureClass,
)


def _get_pi_wrapper_path() -> Path:
    """Get absolute path to Pi agent wrapper."""
    # Go up: pi_codex_runner.py -> adapters -> agents -> guardian -> repo_root
    repo_root = Path(__file__).parent.parent.parent.parent
    return repo_root / "codex_runner" / "src" / "agent-wrapper.js"


class PiCodexRunnerAdapter:
    """Adapter that invokes Codex Runner through the Pi agent wrapper.

    Implements AgentAdapter protocol for Guardian orchestration.
    Uses the Pi SDK wrapper to execute tasks via the configured model.
    `pi_codex_runner` is a legacy-compatible adapter name and does not mean
    direct Codex CLI execution.
    """

    name = "pi_codex_runner"

    def execute(self, request: AgentExecutionRequest) -> AgentRunEnvelope:
        """Execute a coding task through Pi agent wrapper.

        Args:
            request: AgentExecutionRequest with prompt and execution context

        Returns:
            AgentRunEnvelope with execution results
        """
        wrapper_path = _get_pi_wrapper_path()

        # Build execution environment
        env = os.environ.copy()

        # Set model and thinking from environment or defaults
        env["PI_MODEL"] = env.get("PI_MODEL", "claude-sonnet-4-20250514")
        env["PI_THINKING"] = env.get("PI_THINKING", "medium")

        # Build the command
        cmd = ["node", str(wrapper_path), "task", request.prompt]

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
        except FileNotFoundError as exc:
            return AgentRunEnvelope(
                status="error",
                summary="Pi agent wrapper not found (Node.js or wrapper.js missing)",
                artifacts=[],
                next_actions=[],
                errors=["pi_wrapper_not_found", str(exc)],
                metrics={},
            )

    def execute_authorized(
        self,
        request: AgentExecutionRequest,
        identity: AgentExecutionIdentity,
        *,
        read_only: bool,
    ) -> AgentRunEnvelope:
        """Execute exactly one Guardian-authorized Pi task.

        This opt-in path never falls back to the legacy provider/model defaults.
        Its local subprocess environment is the only configuration surface it
        changes; global process environment remains untouched.
        """
        if not all(
            (
                identity.provider_id,
                identity.model_id,
                identity.harness_id,
                identity.harness_version,
            )
        ):
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi identity is incomplete",
                errors=[],
                failure_classification=PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value,
                failure_stage="authorization",
            )

        wrapper_path = _get_pi_wrapper_path()
        env = os.environ.copy()
        env.update(
            {
                "PI_PROVIDER": identity.provider_id,
                "PI_MODEL": identity.model_id,
                "PI_GUARDIAN_AUTHORIZED": "1",
                "PI_GUARDIAN_HARNESS_ID": identity.harness_id,
                "PI_GUARDIAN_HARNESS_VERSION": identity.harness_version,
                "PI_DISABLE_TOOLS": "1" if read_only else "0",
            }
        )
        cmd = ["node", str(wrapper_path), "guardian-authorized-task", request.prompt]

        try:
            result = subprocess.run(
                cmd,
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            return self._parse_result(
                result,
                require_runtime_identity=True,
                require_tool_telemetry=True,
            )
        except subprocess.TimeoutExpired:
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi execution timed out",
                failure_classification=PiAuthorizedFailureClass.ADAPTER_TIMEOUT.value,
                failure_stage="adapter_execution",
                metrics={"timeout_seconds": request.timeout_seconds},
            )
        except FileNotFoundError:
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi wrapper is unavailable",
                failure_classification=PiAuthorizedFailureClass.WRAPPER_UNAVAILABLE.value,
                failure_stage="wrapper_launch",
            )

    def preflight_authorized(
        self,
        request: AgentExecutionRequest,
        identity: AgentExecutionIdentity,
    ) -> AgentRunEnvelope:
        """Run the authorized Pi setup/readiness path without a model prompt.

        Readiness does NOT require tool telemetry (it is non-inference and
        does not create a session).
        """
        if not all(
            (
                identity.provider_id,
                identity.model_id,
                identity.harness_id,
                identity.harness_version,
            )
        ):
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi identity is incomplete",
                failure_classification=PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value,
                failure_stage="authorization",
            )

        wrapper_path = _get_pi_wrapper_path()
        env = os.environ.copy()
        env.update(
            {
                "PI_PROVIDER": identity.provider_id,
                "PI_MODEL": identity.model_id,
                "PI_GUARDIAN_AUTHORIZED": "1",
                "PI_GUARDIAN_HARNESS_ID": identity.harness_id,
                "PI_GUARDIAN_HARNESS_VERSION": identity.harness_version,
                "PI_DISABLE_TOOLS": "1",
            }
        )
        cmd = ["node", str(wrapper_path), "guardian-authorized-readiness"]

        try:
            result = subprocess.run(
                cmd,
                cwd=request.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            return self._parse_result(result, require_runtime_identity=True)
        except subprocess.TimeoutExpired:
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi preflight timed out",
                failure_classification=PiAuthorizedFailureClass.ADAPTER_TIMEOUT.value,
                failure_stage="preflight",
            )
        except FileNotFoundError:
            return AgentRunEnvelope(
                status="error",
                summary="Guardian-authorized Pi wrapper is unavailable",
                failure_classification=PiAuthorizedFailureClass.WRAPPER_UNAVAILABLE.value,
                failure_stage="wrapper_launch",
            )

    def _parse_result(
        self,
        result: subprocess.CompletedProcess[str],
        *,
        require_runtime_identity: bool = False,
        require_tool_telemetry: bool = False,
    ) -> AgentRunEnvelope:
        """Parse subprocess result into AgentRunEnvelope.

        `require_tool_telemetry=True` is used by live authorized task
        execution.  A successful live authorized task must carry valid
        bounded tool telemetry.  Readiness uses `require_tool_telemetry=False`.
        """
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            failure_class = (
                _classify_authorized_failure(stderr)
                if require_runtime_identity
                else None
            )
            return AgentRunEnvelope(
                status="error",
                summary=(
                    "Guardian-authorized Pi operation failed"
                    if require_runtime_identity
                    else "Pi agent execution failed"
                ),
                artifacts=[] if require_runtime_identity else [],
                next_actions=[] if require_runtime_identity else [],
                errors=[] if require_runtime_identity else [
                    stderr or f"exit_code={result.returncode}"
                ],
                metrics={"returncode": result.returncode},
                failure_classification=failure_class,
                failure_stage=(
                    _failure_stage_for_class(failure_class)
                    if failure_class
                    else None
                ),
                return_code=result.returncode,
            )

        if stdout:
            try:
                data = json.loads(stdout)
                runtime_identity = data.get("actual_runtime_identity")
                if data.get("failure_class") in PI_AUTHORIZED_FAILURE_CLASSES:
                    # On failure paths we still surface whatever telemetry
                    # the wrapper emitted (defense-in-depth visibility).
                    telemetry = _parse_tool_telemetry(data.get("tool_telemetry"))
                    return AgentRunEnvelope(
                        status="error",
                        summary="Guardian-authorized Pi operation failed",
                        failure_classification=data["failure_class"],
                        failure_stage=_bounded_text(data.get("failure_stage")),
                        runtime_identity_established=isinstance(
                            runtime_identity, dict
                        ),
                        session_initialized=_bounded_bool(
                            data.get("session_initialized")
                        ),
                        provider_request_started=_bounded_bool(
                            data.get("provider_request_started")
                        ),
                        oauth_available=_bounded_bool(data.get("oauth_available")),
                        effective_tool_names=telemetry[0],
                        write_tool_available=telemetry[1],
                        tool_execution_start_count=telemetry[2],
                        tool_execution_end_count=telemetry[3],
                        executed_tool_names=telemetry[4],
                        assistant_tool_call_count=telemetry[5],
                        assistant_message_count=telemetry[6],
                        assistant_content_block_types=telemetry[7],
                        assistant_message_event_types=telemetry[8],
                        assistant_tool_call_event_count=telemetry[9],
                    )
                if require_runtime_identity and not isinstance(runtime_identity, dict):
                    return AgentRunEnvelope(
                        status="error",
                        summary="Pi wrapper omitted runtime identity attestation",
                        failure_classification=PiAuthorizedFailureClass.ACTUAL_IDENTITY_MISSING.value,
                        failure_stage="identity_attestation",
                    )
                runtime_identity_established = isinstance(runtime_identity, dict) and all(
                    _bounded_text(runtime_identity.get(field))
                    for field in (
                        "actual_provider_id",
                        "actual_model_id",
                        "actual_harness_id",
                        "actual_harness_version",
                    )
                )
                telemetry = _parse_tool_telemetry(data.get("tool_telemetry"))
                # Live authorized task must carry valid tool telemetry.
                if require_tool_telemetry and not _is_valid_tool_telemetry(telemetry):
                    return AgentRunEnvelope(
                        status="error",
                        summary="Pi wrapper omitted or returned invalid tool telemetry",
                        failure_classification=PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value,
                        failure_stage="wrapper_protocol",
                        runtime_identity_established=runtime_identity_established,
                        actual_provider_id=(
                            runtime_identity.get("actual_provider_id")
                            if isinstance(runtime_identity, dict)
                            else None
                        ),
                        actual_model_id=(
                            runtime_identity.get("actual_model_id")
                            if isinstance(runtime_identity, dict)
                            else None
                        ),
                        actual_harness_id=(
                            runtime_identity.get("actual_harness_id")
                            if isinstance(runtime_identity, dict)
                            else None
                        ),
                        actual_harness_version=(
                            runtime_identity.get("actual_harness_version")
                            if isinstance(runtime_identity, dict)
                            else None
                        ),
                        session_initialized=_bounded_bool(
                            data.get("session_initialized")
                        ),
                        provider_request_started=_bounded_bool(
                            data.get("provider_request_started")
                        ),
                        oauth_available=_bounded_bool(data.get("oauth_available")),
                        effective_tool_names=telemetry[0],
                        write_tool_available=telemetry[1],
                        tool_execution_start_count=telemetry[2],
                        tool_execution_end_count=telemetry[3],
                        executed_tool_names=telemetry[4],
                        assistant_tool_call_count=telemetry[5],
                        assistant_message_count=telemetry[6],
                        assistant_content_block_types=telemetry[7],
                        assistant_message_event_types=telemetry[8],
                        assistant_tool_call_event_count=telemetry[9],
                    )
                return AgentRunEnvelope(
                    status=data.get("status", "ok"),
                    summary=data.get(
                        "summary", data.get("text", "Task completed")
                    ),
                    artifacts=data.get("artifacts", []),
                    next_actions=data.get("next_actions", []),
                    errors=data.get("errors", []),
                    metrics=data.get("metrics", {}),
                    actual_provider_id=(
                        runtime_identity.get("actual_provider_id")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    actual_model_id=(
                        runtime_identity.get("actual_model_id")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    actual_harness_id=(
                        runtime_identity.get("actual_harness_id")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    actual_harness_version=(
                        runtime_identity.get("actual_harness_version")
                        if isinstance(runtime_identity, dict)
                        else None
                    ),
                    runtime_identity_established=runtime_identity_established,
                    session_initialized=_bounded_bool(data.get("session_initialized")),
                    provider_request_started=_bounded_bool(
                        data.get("provider_request_started")
                    ),
                    oauth_available=_bounded_bool(data.get("oauth_available")),
                    effective_tool_names=telemetry[0],
                    write_tool_available=telemetry[1],
                    tool_execution_start_count=telemetry[2],
                    tool_execution_end_count=telemetry[3],
                    executed_tool_names=telemetry[4],
                    assistant_tool_call_count=telemetry[5],
                    assistant_message_count=telemetry[6],
                    assistant_content_block_types=telemetry[7],
                    assistant_message_event_types=telemetry[8],
                    assistant_tool_call_event_count=telemetry[9],
                )
            except json.JSONDecodeError:
                if require_runtime_identity:
                    return AgentRunEnvelope(
                        status="error",
                        summary="Pi wrapper returned a non-attested result",
                        failure_classification=PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value,
                        failure_stage="wrapper_protocol",
                    )
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
            summary=(
                "Pi wrapper omitted runtime identity attestation"
                if require_runtime_identity
                else "Task completed with no output"
            ),
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
            failure_classification=(
                PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value
                if require_runtime_identity
                else None
            ),
            failure_stage="wrapper_protocol" if require_runtime_identity else None,
        )


def _parse_tool_telemetry(raw: Any) -> tuple:
    """Parse bounded tool + assistant-response telemetry from the wrapper.

    Returns a 10-tuple. Missing fields yield ``None``. Empty lists/tuples are
    valid (read-only sessions, sessions where the assistant emitted no
    tool-call lifecycle events, etc.).

    Position contract (do not reorder without updating all call sites):

        0. effective_tool_names: tuple[str, ...] | None
        1. write_tool_available: bool | None
        2. tool_execution_start_count: int | None
        3. tool_execution_end_count: int | None
        4. executed_tool_names: tuple[str, ...] | None
        5. assistant_tool_call_count: int | None
        6. assistant_message_count: int | None
        7. assistant_content_block_types: tuple[str, ...] | None
        8. assistant_message_event_types: tuple[str, ...] | None
        9. assistant_tool_call_event_count: int | None
    """
    if not isinstance(raw, dict):
        return (None,) * 10
    names = raw.get("effective_tool_names")
    names_out: tuple[str, ...] | None = None
    if isinstance(names, list):
        cleaned = [n for n in names if isinstance(n, str) and len(n) > 0]
        names_out = tuple(cleaned)  # always tuple; empty tuple when none present
    executed = raw.get("executed_tool_names")
    executed_out: tuple[str, ...] | None = None
    if isinstance(executed, list):
        cleaned = [n for n in executed if isinstance(n, str) and len(n) > 0]
        executed_out = tuple(cleaned)  # always tuple; empty tuple when none present
    write_avail = raw.get("write_tool_available")
    write_avail_out = write_avail if isinstance(write_avail, bool) else None
    start_count = raw.get("tool_execution_start_count")
    start_out = start_count if isinstance(start_count, int) and start_count >= 0 else None
    end_count = raw.get("tool_execution_end_count")
    end_out = end_count if isinstance(end_count, int) and end_count >= 0 else None
    asst_count = raw.get("assistant_tool_call_count")
    asst_out = asst_count if isinstance(asst_count, int) and asst_count >= 0 else None

    # Bounded assistant-response telemetry.  Each field is validated for
    # shape and non-content only — no text/reasoning/args/IDs are read.
    # Non-string list members in `assistant_content_block_types` or
    # `assistant_message_event_types` cause the field to surface as None
    # (i.e. fail closed) per spec §9.
    msg_count = raw.get("assistant_message_count")
    msg_count_out = msg_count if isinstance(msg_count, int) and msg_count >= 0 else None
    block_types = raw.get("assistant_content_block_types")
    block_types_out: tuple[str, ...] | None = None
    if isinstance(block_types, list):
        if not all(isinstance(b, str) and len(b) > 0 for b in block_types):
            block_types_out = None
        else:
            # Preserve first-occurrence order; deduplicate.
            seen: set[str] = set()
            deduped: list[str] = []
            for b in block_types:
                if b not in seen:
                    seen.add(b)
                    deduped.append(b)
            block_types_out = tuple(deduped)
    event_types = raw.get("assistant_message_event_types")
    event_types_out: tuple[str, ...] | None = None
    if isinstance(event_types, list):
        if not all(isinstance(e, str) and len(e) > 0 for e in event_types):
            event_types_out = None
        else:
            seen = set()
            deduped = []
            for e in event_types:
                if e not in seen:
                    seen.add(e)
                    deduped.append(e)
            event_types_out = tuple(deduped)
    tool_call_event_count = raw.get("assistant_tool_call_event_count")
    tool_call_event_out = (
        tool_call_event_count
        if isinstance(tool_call_event_count, int) and tool_call_event_count >= 0
        else None
    )

    return (
        names_out,
        write_avail_out,
        start_out,
        end_out,
        executed_out,
        asst_out,
        msg_count_out,
        block_types_out,
        event_types_out,
        tool_call_event_out,
    )


def _is_valid_tool_telemetry(
    telemetry: tuple,
) -> bool:
    """Live authorized task requires complete, well-formed telemetry.

    An empty ``effective_tool_names`` is valid (e.g. read-only sessions with
    ``PI_DISABLE_TOOLS=1``).  ``None`` means the wrapper omitted the field.

    Both existing 6 fields AND the new 4 assistant-response fields must be
    well-formed on a successful live authorized task.
    """
    if len(telemetry) != 10:
        return False
    (
        names_out,
        write_avail_out,
        start_out,
        end_out,
        executed_out,
        asst_out,
        msg_count_out,
        block_types_out,
        event_types_out,
        tool_call_event_out,
    ) = telemetry
    if names_out is None or not isinstance(names_out, tuple):
        return False
    # An empty tuple/list is valid (read-only, or disabled tools).
    if not isinstance(write_avail_out, bool):
        return False
    if not isinstance(start_out, int) or start_out < 0:
        return False
    if not isinstance(end_out, int) or end_out < 0:
        return False
    if executed_out is None or not isinstance(executed_out, tuple):
        return False
    if not isinstance(asst_out, int) or asst_out < 0:
        return False
    # Assistant-response field validation.
    if not isinstance(msg_count_out, int) or msg_count_out < 0:
        return False
    if not isinstance(block_types_out, tuple):
        return False
    if not isinstance(event_types_out, tuple):
        return False
    if not isinstance(tool_call_event_out, int) or tool_call_event_out < 0:
        return False
    return True


def _bounded_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text[:120] if text else None


def _bounded_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _classify_authorized_failure(stderr: str) -> str:
    text = str(stderr or "").lower()
    if "cannot find package" in text or "cannot find module" in text:
        return PiAuthorizedFailureClass.RUNTIME_MODULE_UNAVAILABLE.value
    if "guardian_authorized_identity_missing" in text or "identity does not match" in text:
        return PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value
    if "model not found" in text:
        return PiAuthorizedFailureClass.MODEL_UNRESOLVED.value
    if "provider not found" in text or "unknown provider" in text:
        return PiAuthorizedFailureClass.PROVIDER_UNRESOLVED.value
    if any(token in text for token in ("no api key", "no credentials", "auth", "oauth")):
        return PiAuthorizedFailureClass.OAUTH_AUTH_UNAVAILABLE.value
    if any(token in text for token in ("econn", "fetch failed", "network", "socket")):
        return PiAuthorizedFailureClass.PROVIDER_TRANSPORT_FAILED.value
    if any(token in text for token in ("401", "403", "429", "provider request", "response")):
        return PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value
    return PiAuthorizedFailureClass.UNKNOWN_ADAPTER_FAILURE.value


def _failure_stage_for_class(failure_class: str | None) -> str:
    return {
        PiAuthorizedFailureClass.RUNTIME_MODULE_UNAVAILABLE.value: "runtime_load",
        PiAuthorizedFailureClass.AUTHORIZED_IDENTITY_REJECTED.value: "authorization",
        PiAuthorizedFailureClass.PROVIDER_UNRESOLVED.value: "provider_resolution",
        PiAuthorizedFailureClass.MODEL_UNRESOLVED.value: "model_resolution",
        PiAuthorizedFailureClass.OAUTH_AUTH_UNAVAILABLE.value: "oauth_readiness",
        PiAuthorizedFailureClass.PROVIDER_TRANSPORT_FAILED.value: "provider_transport",
        PiAuthorizedFailureClass.PROVIDER_REQUEST_FAILED.value: "provider_request",
        PiAuthorizedFailureClass.WRAPPER_PROTOCOL_FAILED.value: "wrapper_protocol",
    }.get(failure_class, "adapter_execution")
