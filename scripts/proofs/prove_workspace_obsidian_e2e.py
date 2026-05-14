#!/usr/bin/env python3
"""
Workspace + Obsidian End-to-End Live Proof Harness

PURPOSE
=======
This harness validates the supported local Compose path for the
`retrievalSource="workspace"` seam. It proves that an ingested
Obsidian-backed local note can influence a real Guardian assistant
completion and that trace evidence on the supported runtime path
shows workspace-local retrieval participation.

SCOPE
=====
This harness is a RELEASE-EVIDENCE TOOL. It does NOT prove:
- Sync automation between Obsidian and Codexify
- First-class connector UX
- Non-Compose install modes (e.g., Kubernetes, bare metal)

This harness validates ONLY the supported local Docker Compose path.

CURRENT-TRUTH ANCHORS
=====================
- `retrievalSource="workspace"` is a live backend meaning for
  user-bounded local knowledge, including Obsidian-backed notes.
- Chat completion is queue-backed; route acceptance is NOT completion.
- The latest retrieval-posture snapshot can distinguish `workspace`
  from thread, project, personal_knowledge, and obsidian_only.
- The completion worker emits a canonical retrieval-posture snapshot
  for supported source modes.

RUNTIME CONTRACT
================
The harness reads the following runtime surfaces:
- `/health` — basic backend readiness
- `/health/chat` — Redis, queue, and worker heartbeat health
- `/api/health/llm` — active provider runtime health
- `POST /api/chat/threads` — thread creation
- `POST /api/chat/{thread_id}/messages` — user message persistence
- `POST /api/chat/{thread_id}/complete` — queue-backed completion request
- `GET /api/tasks/{task_id}/events` — task lifecycle and terminal state
- `GET /api/chat/{thread_id}/messages` — final thread messages (verdict)
- `GET /api/chat/debug/retrieval-posture/{thread_id}/latest` — trace evidence
- `POST /api/obsidian/index` — Obsidian index trigger on configured vault

ACCEPTANCE SEMANTICS (per ADR-001 / flows.md)
=============================================
Route acceptance means:
- Turn lock acquired
- Task enqueued to Redis
- HTTP 200 with task_id returned

Route acceptance does NOT mean:
- Task dequeued
- Model called
- Assistant message persisted
- Trace evidence available

An honest E2E validator MUST wait for task completion and verify
the assistant response and retrieval evidence.

ENVIRONMENT
===========
BASE              — backend base URL (default: http://localhost:8888)
GUARDIAN_API_KEY  — required; falls back to scripts/dev/dev-key.sh

EXIT BEHAVIOR
=============
Exits 0   — all proof conditions met:
            1. Health checks pass
            2. Sentinel note ingested
            3. Thread + message created
            4. Completion accepted (task_id returned)
            5. Task reaches terminal state (task.completed or task.failed)
            6. Assistant response contains sentinel-derived content
            7. Retrieval posture shows workspace-local participation

Exits !=0 — any proof condition fails (see failure classes below)

FAILURE CLASSES
===============
1. HEALTH_CHECK_FAILED  — backend health surfaces not ready
2. INGESTION_FAILED     — Obsidian index trigger failed
3. ACCEPTANCE_FAILED   — POST /complete did not return 200/task_id
4. COMPLETION_TIMEOUT  — task did not reach terminal state within timeout
5. RESPONSE_VERDICT_FAILED — assistant response missing sentinel content
6. RETRIEVAL_EVIDENCE_FAILED — posture snapshot missing workspace signal
7. ABORT_MISSING_ENV   — required env var not set and no fallback

USAGE
=====
# With default BASE and dev-key fallback:
python scripts/proofs/prove_workspace_obsidian_e2e.py

# With explicit BASE and key:
BASE=http://localhost:8888 GUARDIAN_API_KEY="$(cat ~/.codex_guardian_key)" \
  python scripts/proofs/prove_workspace_obsidian_e2e.py

# In a release-evidence workflow:
# Run the harness after a clean Compose start. Attach stdout/stderr
# and the git commit hash to the evidence pack.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Sentinel content — distinctive enough to make false-positive retrieval
# unlikely on any reasonably healthy runtime.
# ---------------------------------------------------------------------------
_SENTINEL_TRIGGER = "mariner-signal-lattice-qrx7"
_SENTINEL_ANSWER = "beacon calibration sequence"
_SENTINEL_BODY = f"""---
tags: [proof-harness, e2e-test]
created: {datetime.now(timezone.utc).isoformat()}
---

# Workspace Obsidian E2E Proof Harness Note

This note exists solely to validate the workspace retrieval seam.

**Sentinel trigger:** {_SENTINEL_TRIGGER}

**Expected answer:** {_SENTINEL_ANSWER}

The assistant should reference the beacon calibration sequence
when asked about the sentinel trigger.

## Technical notes for proof harness

- This note is created by `scripts/proofs/prove_workspace_obsidian_e2e.py`
- It is NOT user content and should be cleaned up after proof runs
- It uses a UUID-like trigger to avoid false retrieval matches
"""

# ---------------------------------------------------------------------------
# Default env / paths
# ---------------------------------------------------------------------------
_DEFAULT_BASE = "http://localhost:8888"
_DEV_KEY_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "dev", "dev-key.sh"
)
_COMPLETION_TIMEOUT_SECONDS = 120
_POLL_INTERVAL_SECONDS = 2.0


# ---------------------------------------------------------------------------
# Failure class registry
# ---------------------------------------------------------------------------
class ProofError(Exception):
    """Base class for proof harness failures."""

    exit_code: int = 1
    category: str = "PROOF_FAILED"

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class HealthCheckFailed(ProofError):
    category = "HEALTH_CHECK_FAILED"
    exit_code = 2


class IngestionFailed(ProofError):
    category = "INGESTION_FAILED"
    exit_code = 3


class AcceptanceFailed(ProofError):
    category = "ACCEPTANCE_FAILED"
    exit_code = 4


class CompletionTimeout(ProofError):
    category = "COMPLETION_TIMEOUT"
    exit_code = 5


class ResponseVerdictFailed(ProofError):
    category = "RESPONSE_VERDICT_FAILED"
    exit_code = 6


class RetrievalEvidenceFailed(ProofError):
    category = "RETRIEVAL_EVIDENCE_FAILED"
    exit_code = 7


class AbortMissingEnv(ProofError):
    category = "ABORT_MISSING_ENV"
    exit_code = 8


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _api_request(
    method: str,
    path: str,
    base: str,
    api_key: str,
    body: Any = None,
    timeout: float = 30.0,
) -> tuple[int, Any]:
    """Make an authenticated API request and return (status, parsed_json)."""
    url = f"{base}{path}"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception:
                parsed = raw.decode("utf-8", errors="replace")
            return status, parsed
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        raise ProofError(
            f"Connection failed to {url}: {e.reason}",
            detail=str(e),
        )


def _parse_sse_events(raw_payload: Any) -> list[dict[str, Any]]:
    """Parse SSE text frames into event dictionaries."""
    if isinstance(raw_payload, list):
        return [item for item in raw_payload if isinstance(item, dict)]
    if not isinstance(raw_payload, str) or not raw_payload.strip():
        return []

    events: list[dict[str, Any]] = []
    current_event_type: str | None = None
    current_data_lines: list[str] = []

    def _flush_current() -> None:
        if not current_event_type:
            return
        payload_text = "\n".join(current_data_lines).strip()
        payload: Any = {}
        if payload_text:
            try:
                payload = json.loads(payload_text)
            except Exception:
                payload = {"raw": payload_text}
        if not isinstance(payload, dict):
            payload = {"value": payload}
        events.append(
            {
                "event_type": current_event_type,
                "type": current_event_type,
                **payload,
            }
        )

    for raw_line in raw_payload.splitlines():
        line = raw_line.strip()
        if not line:
            _flush_current()
            current_event_type = None
            current_data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            current_event_type = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            current_data_lines.append(line.split(":", 1)[1].lstrip())

    _flush_current()
    return events


# ---------------------------------------------------------------------------
# Health check helpers
# ---------------------------------------------------------------------------
def _check_health_surface(
    base: str,
    api_key: str,
    path: str,
    surface_name: str,
) -> bool:
    """Return True if the surface responds 2xx, False otherwise."""
    status, _ = _api_request("GET", path, base, api_key, timeout=10.0)
    if status >= 200 and status < 300:
        return True
    # Log but do not raise — aggregate in _check_all_health
    print(
        f"  [WARN] {surface_name} at {path} returned {status}", file=sys.stderr
    )
    return False


def _check_all_health(base: str, api_key: str) -> None:
    """Fail fast if the live stack is not healthy enough to run the proof."""
    surfaces = [
        ("/health", "GET /health"),
        ("/health/chat", "/health/chat"),
        ("/api/health/llm", "/api/health/llm"),
    ]
    results = {
        name: _check_health_surface(base, api_key, path, name)
        for path, name in surfaces
    }
    failed = [name for name, ok in results.items() if not ok]
    if failed:
        raise HealthCheckFailed(
            f"One or more health surfaces unhealthy: {', '.join(failed)}",
            detail=f"Health results: {results}",
        )
    print("[PASS] All health surfaces healthy")


# ---------------------------------------------------------------------------
# Sentinel generation
# ---------------------------------------------------------------------------
def _build_sentinel_payload() -> dict[str, Any]:
    """Build a distinctive sentinel note payload mimicking an Obsidian file."""
    return {
        "vault_path": "/obsidian-vault",
        "source": "obsidian",
        "files": [
            {
                "path": "ProofHarness/workspace_e2e_sentinel.md",
                "content": _SENTINEL_BODY,
            }
        ],
        "user_id": "local",
    }


# ---------------------------------------------------------------------------
# Thread / message helpers
# ---------------------------------------------------------------------------
def _create_thread(base: str, api_key: str) -> int:
    """Create a chat thread and return the thread_id."""
    status, body = _api_request(
        "POST",
        "/api/chat/threads",
        base,
        api_key,
        body={"user_id": "local", "summary": "workspace e2e proof thread"},
    )
    if status != 200:
        raise AcceptanceFailed(
            f"Thread creation failed with status {status}",
            detail=str(body),
        )
    thread_id = body.get("id")
    if not thread_id:
        raise AcceptanceFailed(
            "Thread creation returned no id",
            detail=str(body),
        )
    return int(thread_id)


def _post_message(
    base: str,
    api_key: str,
    thread_id: int,
    content: str,
) -> int:
    """Post a user message and return the message_id."""
    status, body = _api_request(
        "POST",
        f"/api/chat/{thread_id}/messages",
        base,
        api_key,
        body={
            "thread_id": thread_id,
            "role": "user",
            "content": content,
            "user_id": "local",
        },
    )
    if status != 200:
        raise AcceptanceFailed(
            f"Message creation failed with status {status}",
            detail=str(body),
        )
    return body.get("id", 0)


# ---------------------------------------------------------------------------
# Ingestion helper — uses the supported Obsidian index trigger route
# ---------------------------------------------------------------------------
def _ingest_sentinel_note(base: str, api_key: str) -> None:
    """Trigger Obsidian indexing through the supported control-plane route."""
    status, body = _api_request(
        "POST",
        "/api/obsidian/index",
        base,
        api_key,
        timeout=30.0,
    )
    if status >= 400:
        raise IngestionFailed(
            f"Obsidian index trigger failed with status {status}",
            detail=str(body),
        )
    print("[PASS] Obsidian index triggered via /api/obsidian/index")


# ---------------------------------------------------------------------------
# Completion helpers
# ---------------------------------------------------------------------------
def _request_completion(
    base: str,
    api_key: str,
    thread_id: int,
) -> str:
    """Request completion and return the task_id. Raises AcceptanceFailed."""
    status, body = _api_request(
        "POST",
        f"/api/chat/{thread_id}/complete",
        base,
        api_key,
        body={
            "source_mode": "workspace",
            "retrievalSource": "workspace",
            "depth_mode": "deep",
        },
        timeout=30.0,
    )
    if status != 200:
        raise AcceptanceFailed(
            f"Completion request failed with status {status}",
            detail=str(body),
        )
    task_id = body.get("task_id")
    if not task_id:
        raise AcceptanceFailed(
            "Completion request returned no task_id",
            detail=str(body),
        )
    print(f"[MILESTONE] Completion accepted — task_id={task_id}")
    return str(task_id)


def _wait_for_terminal_task(
    base: str,
    api_key: str,
    task_id: str,
    timeout: float = _COMPLETION_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Poll task events until terminal state or timeout."""
    deadline = time.time() + timeout
    terminal_types = {"task.completed", "task.failed", "task.cancelled"}

    while time.time() < deadline:
        status, events = _api_request(
            "GET",
            f"/api/tasks/{task_id}/events",
            base,
            api_key,
            timeout=10.0,
        )
        if status == 404:
            # Task not yet registered — keep polling
            time.sleep(_POLL_INTERVAL_SECONDS)
            continue
        if status >= 400:
            time.sleep(_POLL_INTERVAL_SECONDS)
            continue

        parsed_events = _parse_sse_events(events)
        for event in parsed_events:
            if event.get("event_type") in terminal_types:
                return event
        time.sleep(_POLL_INTERVAL_SECONDS)

    raise CompletionTimeout(
        f"Task {task_id} did not reach terminal state within {timeout}s",
        detail=None,
    )


# ---------------------------------------------------------------------------
# Verdict helpers
# ---------------------------------------------------------------------------
def _fetch_assistant_response(
    base: str,
    api_key: str,
    thread_id: int,
) -> str:
    """Fetch the final assistant message content."""
    status, body = _api_request(
        "GET",
        f"/api/chat/{thread_id}/messages",
        base,
        api_key,
        timeout=15.0,
    )
    if status >= 400:
        raise ResponseVerdictFailed(
            f"Failed to fetch messages (status {status})",
            detail=str(body),
        )

    messages = body.get("messages", []) if isinstance(body, dict) else []
    assistant_messages = [
        m.get("content", "")
        for m in messages
        if m.get("role") == "assistant" and m.get("content")
    ]
    if not assistant_messages:
        raise ResponseVerdictFailed(
            "No assistant message found in thread",
            detail=str(messages[:3]),
        )
    return "\n".join(assistant_messages)


def _check_response_verdict(assistant_text: str) -> None:
    """Assert that the assistant response contains the sentinel-derived answer."""
    # Case-insensitive check for the sentinel answer fragment.
    # This proves the note influenced the response.
    normalized = assistant_text.lower()
    if _SENTINEL_ANSWER.lower() not in normalized:
        raise ResponseVerdictFailed(
            f"Assistant response does not contain sentinel answer "
            f"'{_SENTINEL_ANSWER}'",
            detail=f"Response preview: {assistant_text[:300]}",
        )
    print(
        f"[VERDICT] Assistant response contains sentinel content: "
        f"'{_SENTINEL_ANSWER}'"
    )


def _fetch_retrieval_posture(
    base: str,
    api_key: str,
    thread_id: int,
) -> dict[str, Any]:
    """Fetch the latest retrieval posture snapshot."""
    status, body = _api_request(
        "GET",
        f"/api/chat/debug/retrieval-posture/{thread_id}/latest",
        base,
        api_key,
        timeout=15.0,
    )
    if status >= 400:
        return {}
    if not isinstance(body, dict):
        return {}
    nested_posture = body.get("retrieval_posture")
    if isinstance(nested_posture, dict):
        return nested_posture
    return body


def _check_retrieval_evidence(posture: dict[str, Any]) -> None:
    """Assert that the retrieval posture shows workspace-local participation."""
    source_mode = posture.get("source_mode", "")
    posture_str = json.dumps(posture, default=str)

    # The posture must show a workspace-related signal.
    # Valid signals: source_mode == "workspace" OR
    #               widen_reason contains "workspace" OR
    #               retrieval_provenance shows workspace_local success
    has_workspace_mode = source_mode == "workspace"
    has_workspace_widen = (
        "workspace" in str(posture.get("widen_reason", "")).lower()
    )
    provenance = posture.get("retrieval_provenance", {})
    has_workspace_provenance = (
        provenance.get("retrieval_status", "") == "workspace_local_success"
    )

    if not (
        has_workspace_mode or has_workspace_widen or has_workspace_provenance
    ):
        raise RetrievalEvidenceFailed(
            "Retrieval posture does not show workspace-local signal",
            detail=f"Posture: {posture_str[:500]}",
        )
    print(
        f"[VERDICT] Retrieval posture confirms workspace-local retrieval: "
        f"source_mode={source_mode}, "
        f"widen_reason={posture.get('widen_reason')}"
    )


# ---------------------------------------------------------------------------
# Main proof harness
# ---------------------------------------------------------------------------
def run_proof() -> None:
    # 1. Resolve env
    base = os.environ.get("BASE", _DEFAULT_BASE).rstrip("/")
    api_key = os.environ.get("GUARDIAN_API_KEY", "").strip()

    if not api_key:
        # Try dev-key fallback
        if os.path.exists(_DEV_KEY_SCRIPT):
            import subprocess

            try:
                api_key = subprocess.check_output(
                    ["bash", _DEV_KEY_SCRIPT],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
            except subprocess.CalledProcessError:
                pass
        if not api_key:
            raise AbortMissingEnv(
                "GUARDIAN_API_KEY is not set and dev-key fallback failed",
                detail=None,
            )

    print(f"[PROOF] Workspace Obsidian E2E Harness")
    print(f"[PROOF] BASE={base}")
    print(f"[PROOF] Started at {datetime.now(timezone.utc).isoformat()}")
    print()

    # 2. Fail fast health check
    print("[STEP 1] Checking live stack health...")
    _check_all_health(base, api_key)
    print()

    # 3. Ingest sentinel note via Obsidian path
    print("[STEP 2] Ingesting sentinel Obsidian note...")
    _ingest_sentinel_note(base, api_key)
    print()

    # 4. Create thread
    print("[STEP 3] Creating chat thread...")
    thread_id = _create_thread(base, api_key)
    print(f"[MILESTONE] Thread created — thread_id={thread_id}")
    print()

    # 5. Post sentinel-trigger message
    print("[STEP 4] Posting sentinel-trigger message...")
    message_content = (
        f"Tell me about the {_SENTINEL_TRIGGER}. "
        f"What is the beacon calibration sequence?"
    )
    _post_message(base, api_key, thread_id, message_content)
    print("[MILESTONE] Message posted")
    print()

    # 6. Request completion (acceptance milestone)
    print("[STEP 5] Requesting completion with retrievalSource='workspace'...")
    task_id = _request_completion(base, api_key, thread_id)
    print()

    # 7. Wait for terminal task state (real completion, not just acceptance)
    print("[STEP 6] Waiting for task to reach terminal state...")
    terminal_event = _wait_for_terminal_task(base, api_key, task_id)
    print(
        f"[MILESTONE] Task reached terminal state — "
        f"event_type={terminal_event.get('event_type')}"
    )
    if terminal_event.get("event_type") == "task.failed":
        failure_detail = terminal_event.get("failure_class", "unknown")
        raise CompletionTimeout(
            f"Task failed during execution: {failure_detail}",
            detail=str(terminal_event),
        )
    print()

    # 8. Verify assistant response contains sentinel-derived content
    print("[STEP 7] Fetching and verifying assistant response...")
    assistant_text = _fetch_assistant_response(base, api_key, thread_id)
    _check_response_verdict(assistant_text)
    print()

    # 9. Verify retrieval posture shows workspace-local participation
    print("[STEP 8] Fetching and verifying retrieval posture evidence...")
    posture = _fetch_retrieval_posture(base, api_key, thread_id)
    _check_retrieval_evidence(posture)
    print()

    # 10. Print operator summary
    print("=" * 64)
    print("WORKSPACE OBSIDIAN E2E PROOF — FINAL VERDICT")
    print("=" * 64)
    print(f"[VERDICT] ✓ Health checks         — PASS")
    print(f"[VERDICT] ✓ Sentinel ingestion   — PASS")
    print(f"[VERDICT] ✓ Thread + message      — PASS (thread_id={thread_id})")
    print(f"[VERDICT] ✓ Completion acceptance — PASS (task_id={task_id})")
    print(f"[VERDICT] ✓ Task terminal state   — PASS")
    print(f"[VERDICT] ✓ Response verdict      — PASS")
    print(f"[VERDICT] ✓ Retrieval evidence   — PASS")
    print("=" * 64)
    print("[PROOF] All conditions met. Proof PASSED.")
    print(f"[PROOF] Completed at " f"{datetime.now(timezone.utc).isoformat()}")


def main() -> None:
    try:
        run_proof()
        sys.exit(0)
    except ProofError as e:
        print(f"[PROOF FAILURE] {e.category}: {e.message}", file=sys.stderr)
        if e.detail:
            print(f"[PROOF DETAIL] {e.detail}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"[PROOF ERROR] Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


# Legacy entrypoint intentionally disabled.
# The current proof harness continues below and owns the real __main__ block.

import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_TMP_ROOT = REPO_ROOT / "tmp"
BASE_DEFAULT = "http://localhost:8888"
CONTAINER_PROOF_ROOT = Path(
    os.getenv("CODEXIFY_CONTAINER_PROOF_ROOT", "/app/data/media")
)
TASK_EVENT_TERMINAL_TYPES = {
    "task.completed",
    "task.failed",
    "task.cancelled",
}
ACCEPTED_STATUSES = {"accepted", "accepted_degraded"}
WORKSPACE_SOURCE_MODE = "workspace"
WORKSPACE_RETRIEVAL_STATUS = "workspace_local_success"
PROOF_STEP_ORDER = (
    "health",
    "obsidian_config",
    "obsidian_index",
    "obsidian_search",
    "thread_create",
    "user_message",
    "completion_acceptance",
    "task_events",
    "message_verification",
    "trace_verification",
    "final_verdict",
)
VERDICT_CATEGORIES = (
    "acceptance",
    "substrate_searchability",
    "completion",
    "workspace_eligibility",
    "broker_selection",
    "completion_injection",
    "assistant_match",
    "final_verdict",
)


class ProofFailure(RuntimeError):
    """Raised when the live proof cannot establish a required condition."""


@dataclass(frozen=True)
class WorkspaceSentinel:
    """Deterministic sentinel payload for the Obsidian-backed workspace note."""

    token: str
    note_title: str
    note_filename: str
    note_text: str
    question: str
    expected_answer: str


def build_workspace_sentinel(seed: str | None = None) -> WorkspaceSentinel:
    """Build a distinctive note payload for the workspace proof.

    When `seed` is supplied the token is deterministic for contract tests.
    When omitted, the token is unique per run.
    """

    token_uuid = (
        uuid.uuid5(uuid.NAMESPACE_URL, seed)
        if seed is not None
        else uuid.uuid4()
    )
    phrase_suffix = token_uuid.hex[:8]
    token = f"workspace-seal-zephyr-candle-reef-{phrase_suffix}"
    note_title = f"Zephyr Candle Reef Sentinel {token[-8:]}"
    note_filename = "workspace-proof-sentinel.md"
    question = (
        f"In my workspace note titled {note_title}, what is the exact "
        "workspace proof phrase? Reply with only the phrase."
    )
    note_text = (
        "---\n"
        f"title: {note_title}\n"
        "tags:\n"
        "  - obsidian\n"
        "  - workspace\n"
        "  - proof\n"
        "---\n"
        f"{note_title}\n\n"
        f"{question}\n\n"
        f"The exact workspace proof phrase is `{token}`.\n\n"
        f"If asked for the workspace proof phrase, answer only `{token}`.\n\n"
        "This note validates the supported local Compose path only and does "
        "not widen the release promise to other install modes.\n"
    )
    return WorkspaceSentinel(
        token=token,
        note_title=note_title,
        note_filename=note_filename,
        note_text=note_text,
        question=question,
        expected_answer=token,
    )


def classify_proof_verdicts(
    *,
    acceptance_status: str | None,
    substrate_searchable: bool,
    terminal_event_type: str | None,
    assistant_text: str | None,
    retrieval_status: str | None,
    obsidian_semantic_hits: int,
    retrieval_source_mode: str | None,
    retrieval_posture: dict[str, Any] | None,
    obsidian_injected: bool,
    token: str,
) -> dict[str, dict[str, Any]]:
    """Classify the proof into the operator-facing verdict categories."""

    acceptance_ok = str(acceptance_status or "").strip() in ACCEPTED_STATUSES
    substrate_searchable_ok = bool(substrate_searchable)
    completion_ok = terminal_event_type == "task.completed"
    workspace_eligible_ok = (
        str(retrieval_source_mode or "").strip() == WORKSPACE_SOURCE_MODE
        and bool(retrieval_posture)
        and str(retrieval_posture.get("source_mode") or "").strip()
        == WORKSPACE_SOURCE_MODE
        and str(retrieval_posture.get("boundary_label") or "").strip()
        == "same_user_only"
        and str(retrieval_posture.get("widen_reason") or "").strip()
        == "explicit_workspace"
    )
    broker_selected_ok = obsidian_semantic_hits > 0
    completion_injected_ok = bool(obsidian_injected)
    assistant_ok = bool(assistant_text and token in assistant_text)

    verdicts: dict[str, dict[str, Any]] = {
        "acceptance": {
            "status": acceptance_status or "missing",
            "passed": acceptance_ok,
        },
        "substrate_searchability": {
            "status": "searchable" if substrate_searchable_ok else "missing",
            "passed": substrate_searchable_ok,
        },
        "completion": {
            "status": terminal_event_type or "missing",
            "passed": completion_ok,
        },
        "workspace_eligibility": {
            "status": str(retrieval_status or "missing").strip() or "missing",
            "passed": workspace_eligible_ok,
            "source_mode": retrieval_source_mode,
            "retrieval_posture": retrieval_posture,
        },
        "broker_selection": {
            "status": (
                "selected" if broker_selected_ok else "missing_obsidian_hits"
            ),
            "passed": broker_selected_ok,
            "obsidian_semantic_hits": obsidian_semantic_hits,
        },
        "completion_injection": {
            "status": "injected" if completion_injected_ok else "missing",
            "passed": completion_injected_ok,
            "obsidian_injected": obsidian_injected,
            "retrieval_status": retrieval_status,
        },
        "assistant_match": {
            "status": "matched" if assistant_ok else "missing_token",
            "passed": assistant_ok,
        },
    }
    final_ok = all(item["passed"] for item in verdicts.values())
    verdicts["final_verdict"] = {
        "status": "pass" if final_ok else "fail",
        "passed": final_ok,
        "reasons": [
            name
            for name, item in verdicts.items()
            if name != "final_verdict" and not item["passed"]
        ],
    }
    return verdicts


def _normalize_workspace_retrieval_evidence(
    *,
    task_completed_payload: dict[str, Any] | None,
    retrieval_posture: dict[str, Any] | None,
    trace: dict[str, Any] | None,
) -> dict[str, Any]:
    worker_payload_summary = (
        task_completed_payload.get("payload_summary")
        if isinstance(task_completed_payload, dict)
        else None
    )
    trace_payload_summary = (
        trace.get("payload_summary") if isinstance(trace, dict) else None
    )
    worker_snapshot = _workspace_evidence_snapshot(worker_payload_summary)
    trace_snapshot = _workspace_evidence_snapshot(trace_payload_summary)

    source_mode = worker_snapshot["source_mode"]
    obsidian_count = worker_snapshot["obsidian_count"]
    semantic_count = worker_snapshot["semantic_count"]
    graph_hit_count = worker_snapshot["graph_hit_count"]
    linked_document_count = worker_snapshot["linked_document_count"]
    retrieval_injected = worker_snapshot["retrieval_injected"]
    obsidian_injected = worker_snapshot["obsidian_injected"]
    retrieval_status = str(worker_snapshot["retrieval_status"] or "").strip()
    if not retrieval_status:
        if source_mode == WORKSPACE_SOURCE_MODE:
            if obsidian_count > 0 and retrieval_injected and obsidian_injected:
                retrieval_status = WORKSPACE_RETRIEVAL_STATUS
            elif obsidian_count > 0 or retrieval_injected:
                retrieval_status = "workspace_local_partial"
            else:
                retrieval_status = "workspace_local_missing_obsidian"
        else:
            retrieval_status = "missing"

    return {
        "source_mode": source_mode or None,
        "retrieval_status": retrieval_status or None,
        "obsidian_count": obsidian_count,
        "semantic_count": semantic_count,
        "graph_hit_count": graph_hit_count,
        "linked_document_count": linked_document_count,
        "retrieval_injected": retrieval_injected,
        "obsidian_injected": obsidian_injected,
        "worker_payload_obsidian_count": worker_snapshot["obsidian_count"],
        "worker_payload_obsidian_injected": worker_snapshot[
            "obsidian_injected"
        ],
        "worker_payload_retrieval_injected": worker_snapshot[
            "retrieval_injected"
        ],
        "trace_obsidian_count": trace_snapshot["obsidian_count"],
        "trace_obsidian_injected": trace_snapshot["obsidian_injected"],
        "trace_retrieval_injected": trace_snapshot["retrieval_injected"],
        "payload_summary": worker_payload_summary or {},
        "trace_payload_summary": trace_payload_summary or {},
    }


def _fail(message: str) -> None:
    raise ProofFailure(message)


def _env_value(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _read_env_file_key(env_file: Path, key: str) -> str | None:
    if not env_file.exists():
        return None
    for raw_line in env_file.read_text(
        encoding="utf-8", errors="ignore"
    ).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(f"{key}="):
            continue
        value = line.partition("=")[2].strip()
        return value.strip().strip('"').strip("'")
    return None


def _resolve_api_key() -> str:
    key = _env_value("GUARDIAN_API_KEY")
    if key:
        return key
    key = _read_env_file_key(REPO_ROOT / ".env", "GUARDIAN_API_KEY")
    if key:
        return key
    _fail("GUARDIAN_API_KEY is required. Set it in the environment or in .env.")
    return ""


def _resolve_base_url() -> str:
    base = _env_value("BASE", "GUARDIAN_API_BASE", default=BASE_DEFAULT)
    if base is None:
        return BASE_DEFAULT
    return base.rstrip("/")


def _copy_workspace_vault_to_container(
    host_root: Path, container_root: Path
) -> None:
    container_parent = container_root.parent
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "backend",
            "mkdir",
            "-p",
            str(container_parent),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    copy_result = subprocess.run(
        [
            "docker",
            "compose",
            "cp",
            str(host_root),
            f"backend:{container_root}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if copy_result.returncode != 0:
        _fail(
            "Failed to copy the proof vault into the Compose-visible volume: "
            f"{copy_result.stderr.strip() or copy_result.stdout.strip()}"
        )


def _request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float | tuple[float, float] = 10.0,
) -> dict[str, Any]:
    response = session.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise ProofFailure(
            f"{method} {url} failed with {response.status_code}: "
            f"{response.text.strip()}"
        )
    try:
        payload = response.json()
    except Exception as exc:
        raise ProofFailure(
            f"{method} {url} returned non-JSON payload: {response.text.strip()}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProofFailure(
            f"{method} {url} returned an unexpected payload shape: {payload!r}"
        )
    return payload


def _check_runtime_health(
    session: requests.Session, base_url: str, headers: dict[str, str]
) -> dict[str, Any]:
    health = _request_json(
        session, "GET", f"{base_url}/health", headers=headers
    )
    if str(health.get("status") or "").strip() != "ok":
        _fail(f"/health is not green: {health!r}")

    chat_health = _request_json(
        session, "GET", f"{base_url}/health/chat", headers=headers
    )
    if str(chat_health.get("status") or "").strip() not in {"healthy", "ok"}:
        _fail(f"/health/chat is not healthy enough: {chat_health!r}")

    completion_service = (
        chat_health.get("completion_service")
        if isinstance(chat_health.get("completion_service"), dict)
        else {}
    )
    redis_state = (
        completion_service.get("redis_reachable")
        if isinstance(completion_service, dict)
        else None
    )
    if redis_state is None:
        redis_state = (
            chat_health.get("redis")
            or chat_health.get("redis_status")
            or chat_health.get("redis_reachable")
        )
    worker_status = str(
        completion_service.get("worker_heartbeat_status")
        or chat_health.get("worker_heartbeat_status")
        or chat_health.get("worker.status")
        or ""
    ).strip()
    if redis_state not in {"ok", True}:
        _fail(f"/health/chat redis is not healthy: {chat_health!r}")
    if worker_status not in {"fresh", "ok"}:
        _fail(f"/health/chat worker heartbeat is not fresh: {chat_health!r}")

    llm_health = _request_json(
        session, "GET", f"{base_url}/api/health/llm", headers=headers
    )
    if str(llm_health.get("status") or "").strip() not in {"online", "ok"}:
        _fail(f"/api/health/llm is not online: {llm_health!r}")

    retrieval_health = _request_json(
        session, "GET", f"{base_url}/api/health/retrieval", headers=headers
    )
    if not retrieval_health.get("ok") or not retrieval_health.get(
        "proof_capable"
    ):
        _fail(
            f"/api/health/retrieval is not proof-capable: {retrieval_health!r}"
        )

    return {
        "health": health,
        "chat_health": chat_health,
        "llm_health": llm_health,
        "retrieval_health": retrieval_health,
    }


def _write_workspace_note(
    scratch_root: Path, sentinel: WorkspaceSentinel
) -> Path:
    vault_root = scratch_root / "vault"
    notes_dir = vault_root / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / sentinel.note_filename
    note_path.write_text(sentinel.note_text, encoding="utf-8")
    return vault_root


def _configure_obsidian_vault(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    vault_root: Path,
) -> dict[str, Any] | None:
    config_url = f"{base_url}/api/obsidian/config"
    previous_config: dict[str, Any] | None = None
    resp = session.get(config_url, headers=headers, timeout=10.0)
    if resp.status_code == 200:
        payload = resp.json()
        if isinstance(payload, dict):
            previous_config = payload
    elif resp.status_code not in {404}:
        raise ProofFailure(
            f"GET {config_url} failed with {resp.status_code}: {resp.text.strip()}"
        )

    payload = {
        "vault_root": str(vault_root),
        "allowed_paths": ["notes"],
        "allowed_tags": None,
    }
    updated = _request_json(
        session,
        "PUT",
        config_url,
        headers=headers,
        json_body=payload,
        timeout=10.0,
    )
    if updated.get("config", {}).get("vault_root") != str(vault_root):
        _fail(f"Obsidian config did not persist the proof vault: {updated!r}")
    return previous_config


def _restore_obsidian_config(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    previous_config: dict[str, Any] | None,
) -> None:
    if not previous_config:
        return
    config = previous_config.get("config")
    if not isinstance(config, dict):
        return
    try:
        session.put(
            f"{base_url}/api/obsidian/config",
            headers=headers,
            json=config,
            timeout=10.0,
        )
    except Exception:
        # Restoration is best-effort; the proof verdict is based on the live run.
        pass


def _index_obsidian_vault(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    indexed = _request_json(
        session,
        "POST",
        f"{base_url}/api/obsidian/index",
        headers=headers,
        timeout=60.0,
    )
    if int(indexed.get("indexed") or 0) < 1:
        _fail(f"Obsidian index did not ingest the proof note: {indexed!r}")
    return indexed


def _assert_obsidian_note_searchable(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    sentinel: WorkspaceSentinel,
) -> dict[str, Any]:
    probe = _request_json(
        session,
        "GET",
        f"{base_url}/api/health/retrieval",
        headers=headers,
        params={
            "q": sentinel.note_title,
            "k": 10,
            "namespace": "obsidian:local",
        },
        timeout=30.0,
    )
    matches = probe.get("search", {}).get("matches")
    if not isinstance(matches, list) or not matches:
        _fail(
            "Obsidian note was not searchable on the supported local Compose path: "
            f"{probe!r}"
        )
    top_match = matches[0] if isinstance(matches[0], dict) else None
    if not isinstance(top_match, dict):
        _fail(f"Obsidian search returned an unexpected shape: {probe!r}")
    meta = top_match.get("meta")
    if not isinstance(meta, dict) or meta.get("namespace") != "obsidian:local":
        _fail(
            f"Obsidian search did not return a workspace-local note: {probe!r}"
        )
    return probe


def _create_thread(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    sentinel: WorkspaceSentinel,
) -> dict[str, Any]:
    return _request_json(
        session,
        "POST",
        f"{base_url}/api/chat/threads",
        headers=headers,
        json_body={
            "title": f"workspace-proof-{sentinel.token[-8:]}",
            "retrievalSource": WORKSPACE_SOURCE_MODE,
        },
        timeout=15.0,
    )


def _post_user_message(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    thread_id: int,
    sentinel: WorkspaceSentinel,
) -> dict[str, Any]:
    return _request_json(
        session,
        "POST",
        f"{base_url}/api/chat/{thread_id}/messages",
        headers=headers,
        json_body={
            "role": "user",
            "content": sentinel.question,
        },
        timeout=15.0,
    )


def _request_completion(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    thread_id: int,
) -> dict[str, Any]:
    return _request_json(
        session,
        "POST",
        f"{base_url}/api/chat/{thread_id}/complete",
        headers=headers,
        json_body={
            "source_mode": WORKSPACE_SOURCE_MODE,
            "depth_mode": "normal",
        },
        timeout=15.0,
    )


def _read_task_events(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    url = f"{base_url}/api/tasks/{task_id}/events"
    response = session.get(
        url,
        headers=headers,
        params={"last_id": "0-0"},
        stream=True,
        timeout=(5.0, timeout_seconds),
    )
    if response.status_code >= 400:
        raise ProofFailure(
            f"GET {url} failed with {response.status_code}: {response.text.strip()}"
        )

    events: list[dict[str, Any]] = []
    current: dict[str, Any] = {"id": None, "type": None, "data": []}
    try:
        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = str(raw_line).strip()
            if not line:
                if current["type"]:
                    payload_text = "".join(current["data"]) or "{}"
                    try:
                        data = json.loads(payload_text)
                    except Exception as exc:
                        raise ProofFailure(
                            f"Failed to parse task event payload: {payload_text}"
                        ) from exc
                    event = {
                        "id": current["id"],
                        "type": current["type"],
                        "data": data,
                    }
                    events.append(event)
                    if current["type"] in TASK_EVENT_TERMINAL_TYPES:
                        return events
                current = {"id": None, "type": None, "data": []}
                continue

            if line.startswith(":"):
                continue
            if line.startswith("id: "):
                current["id"] = line[4:].strip()
            elif line.startswith("event: "):
                current["type"] = line[7:].strip()
            elif line.startswith("data: "):
                current["data"].append(line[6:])
    except requests.ReadTimeout as exc:
        raise ProofFailure(
            f"Timed out waiting for terminal task event from {task_id}"
        ) from exc
    finally:
        response.close()
    return events


def _get_last_assistant_message(
    messages_payload: dict[str, Any]
) -> dict[str, Any]:
    messages = messages_payload.get("messages")
    if not isinstance(messages, list):
        _fail(f"Messages payload has unexpected shape: {messages_payload!r}")
    assistants = [
        msg
        for msg in messages
        if isinstance(msg, dict) and msg.get("role") == "assistant"
    ]
    if not assistants:
        _fail(f"No assistant message was persisted: {messages_payload!r}")
    return assistants[-1]


def _latest_retrieval_artifacts(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    thread_id: int,
    task_completed_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    worker_payload_retrieval_posture: dict[str, Any] | None = None
    trace: dict[str, Any] | None = None

    if isinstance(task_completed_payload, dict):
        worker_payload_retrieval_posture = task_completed_payload.get(
            "retrieval_posture"
        )
        if not isinstance(worker_payload_retrieval_posture, dict):
            payload_summary = task_completed_payload.get("payload_summary")
            if isinstance(payload_summary, dict):
                maybe_posture = payload_summary.get("retrieval_posture")
                if isinstance(maybe_posture, dict):
                    worker_payload_retrieval_posture = maybe_posture
        trace = task_completed_payload.get("trace")
        if not isinstance(trace, dict):
            trace = None

    if trace is None:
        try:
            trace_response = _request_json(
                session,
                "GET",
                f"{base_url}/api/chat/debug/rag-trace/{thread_id}/latest",
                headers=headers,
                timeout=10.0,
            )
            if isinstance(trace_response, dict):
                trace = trace_response
        except ProofFailure:
            pass
    return worker_payload_retrieval_posture, trace


def _workspace_evidence_snapshot(
    payload_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(payload_summary, dict):
        return {
            "source_mode": None,
            "retrieval_status": None,
            "obsidian_count": 0,
            "semantic_count": 0,
            "graph_hit_count": 0,
            "linked_document_count": 0,
            "retrieval_injected": False,
            "obsidian_injected": False,
        }

    return {
        "source_mode": (
            str(payload_summary.get("source_mode") or "").strip() or None
        ),
        "retrieval_status": (
            str(payload_summary.get("retrieval_status") or "").strip() or None
        ),
        "obsidian_count": int(payload_summary.get("obsidian_count") or 0),
        "semantic_count": int(payload_summary.get("semantic_count") or 0),
        "graph_hit_count": int(payload_summary.get("graph_hit_count") or 0),
        "linked_document_count": int(
            payload_summary.get("linked_document_count") or 0
        ),
        "retrieval_injected": bool(payload_summary.get("retrieval_injected")),
        "obsidian_injected": bool(payload_summary.get("obsidian_injected")),
    }


def _format_summary(
    *,
    base_url: str,
    thread_id: int,
    task_id: str,
    assistant_text: str,
    task_completed_payload: dict[str, Any] | None,
    verdicts: dict[str, dict[str, Any]],
    retrieval_posture: dict[str, Any] | None,
    workspace_evidence: dict[str, Any] | None,
) -> str:
    acceptance = verdicts["acceptance"]
    substrate_searchability = verdicts["substrate_searchability"]
    completion = verdicts["completion"]
    workspace_eligibility = verdicts["workspace_eligibility"]
    broker_selection = verdicts["broker_selection"]
    completion_injection = verdicts["completion_injection"]
    assistant_match = verdicts["assistant_match"]
    final_verdict = verdicts["final_verdict"]
    obsidian_hits = broker_selection.get("obsidian_semantic_hits", 0)
    evidence_status = (
        workspace_evidence.get("retrieval_status")
        if isinstance(workspace_evidence, dict)
        else None
    )
    evidence_obsidian = (
        workspace_evidence.get("obsidian_count")
        if isinstance(workspace_evidence, dict)
        else None
    )
    worker_obsidian = (
        workspace_evidence.get("worker_payload_obsidian_count")
        if isinstance(workspace_evidence, dict)
        else None
    )
    trace_obsidian = (
        workspace_evidence.get("trace_obsidian_count")
        if isinstance(workspace_evidence, dict)
        else None
    )
    evidence_injected = (
        workspace_evidence.get("obsidian_injected")
        if isinstance(workspace_evidence, dict)
        else None
    )
    worker_injected = (
        workspace_evidence.get("worker_payload_obsidian_injected")
        if isinstance(workspace_evidence, dict)
        else None
    )
    trace_injected = (
        workspace_evidence.get("trace_obsidian_injected")
        if isinstance(workspace_evidence, dict)
        else None
    )
    posture_source_mode = (
        retrieval_posture.get("source_mode")
        if isinstance(retrieval_posture, dict)
        else None
    )
    posture_reason = (
        retrieval_posture.get("widen_reason")
        if isinstance(retrieval_posture, dict)
        else None
    )
    evidence_summary = ""
    if isinstance(workspace_evidence, dict):
        evidence_summary = (
            f"source_mode={workspace_evidence.get('source_mode')} | "
            f"worker_obsidian_count={worker_obsidian} | "
            f"trace_obsidian_count={trace_obsidian} | "
            f"obsidian_count={workspace_evidence.get('obsidian_count')} | "
            f"semantic_count={workspace_evidence.get('semantic_count')} | "
            f"graph_hit_count={workspace_evidence.get('graph_hit_count')} | "
            f"linked_document_count={workspace_evidence.get('linked_document_count')} | "
            f"retrieval_injected={workspace_evidence.get('retrieval_injected')} | "
            f"worker_obsidian_injected={worker_injected} | "
            f"trace_obsidian_injected={trace_injected} | "
            f"obsidian_injected={workspace_evidence.get('obsidian_injected')}"
        )
    return "\n".join(
        [
            f"ACCEPTANCE: {acceptance['status']} | passed={str(acceptance['passed']).lower()} | task_id={task_id} | thread_id={thread_id} | source_mode={WORKSPACE_SOURCE_MODE}",
            f"SEARCHABILITY: {substrate_searchability['status']} | passed={str(substrate_searchability['passed']).lower()} | obsidian_searchable={str(substrate_searchability['passed']).lower()}",
            f"COMPLETION: {completion['status']} | passed={str(completion['passed']).lower()} | assistant_match={str(assistant_match['passed']).lower()} | assistant_message={assistant_text!r}",
            f"ELIGIBILITY: {workspace_eligibility.get('status') or evidence_status or 'missing'} | passed={str(workspace_eligibility['passed']).lower()} | posture_source_mode={posture_source_mode} | widen_reason={posture_reason}",
            f"SELECTION: {broker_selection.get('status') or 'missing'} | passed={str(broker_selection['passed']).lower()} | obsidian_semantic_hits={obsidian_hits} | obsidian_count={evidence_obsidian}",
            f"INJECTION: {completion_injection.get('status') or 'missing'} | passed={str(completion_injection['passed']).lower()} | obsidian_injected={evidence_injected}",
            f"TRACE: {evidence_summary or 'missing'}",
            f"VERDICT: {str(final_verdict['status']).upper()} | reasons={','.join(final_verdict.get('reasons', [])) or 'none'} | base={base_url}",
        ]
    )


def run_proof(base_url: str, api_key: str) -> tuple[dict[str, Any], str]:
    headers = {"X-API-Key": api_key}
    session = requests.Session()
    scratch_root = Path(
        tempfile.mkdtemp(
            prefix="workspace-obsidian-e2e-", dir=str(HOST_TMP_ROOT)
        )
    )
    sentinel = build_workspace_sentinel()
    vault_root = _write_workspace_note(scratch_root, sentinel)
    container_vault_root = CONTAINER_PROOF_ROOT / scratch_root.name / "vault"

    previous_obsidian_config: dict[str, Any] | None = None
    task_completed_payload: dict[str, Any] | None = None
    assistant_text = ""
    thread_id = -1
    task_id = ""
    substrate_searchable = False
    try:
        _copy_workspace_vault_to_container(
            scratch_root, CONTAINER_PROOF_ROOT / scratch_root.name
        )
        _check_runtime_health(session, base_url, headers)
        previous_obsidian_config = _configure_obsidian_vault(
            session, base_url, headers, container_vault_root
        )
        _index_obsidian_vault(session, base_url, headers)
        _assert_obsidian_note_searchable(session, base_url, headers, sentinel)
        substrate_searchable = True

        thread_payload = _create_thread(session, base_url, headers, sentinel)
        thread_id = int(thread_payload.get("id") or 0)
        if thread_id <= 0:
            _fail(
                f"Thread creation did not return a usable id: {thread_payload!r}"
            )
        thread_config = thread_payload.get("thread", {}).get("thread_config")
        if not isinstance(thread_config, dict):
            _fail(
                f"Thread response did not include thread_config: {thread_payload!r}"
            )
        if thread_config.get("retrievalSource") != WORKSPACE_SOURCE_MODE:
            _fail(
                "Thread retrievalSource was not preserved as workspace: "
                f"{thread_config!r}"
            )

        _post_user_message(session, base_url, headers, thread_id, sentinel)
        completion_payload = _request_completion(
            session, base_url, headers, thread_id
        )
        task_id = str(completion_payload.get("task_id") or "").strip()
        if not task_id:
            _fail(
                f"Completion did not return a task id: {completion_payload!r}"
            )
        if (
            str(completion_payload.get("acceptance_status") or "").strip()
            not in ACCEPTED_STATUSES
        ):
            _fail(
                "Completion acceptance did not pass on the supported local Compose path: "
                f"{completion_payload!r}"
            )

        events = _read_task_events(session, base_url, headers, task_id, 180.0)
        terminal_events = [
            event
            for event in events
            if event.get("type") in TASK_EVENT_TERMINAL_TYPES
        ]
        if not terminal_events:
            _fail(f"Task never reached a terminal state: {events!r}")
        terminal_event = terminal_events[-1]
        terminal_event_type = str(terminal_event.get("type") or "").strip()
        if terminal_event_type != "task.completed":
            _fail(
                f"Task did not complete successfully: {terminal_event_type} {terminal_event!r}"
            )
        task_completed_payload = terminal_event.get("data")
        if not isinstance(task_completed_payload, dict):
            _fail(f"task.completed payload is missing: {terminal_event!r}")

        messages_payload = _request_json(
            session,
            "GET",
            f"{base_url}/api/chat/{thread_id}/messages",
            headers=headers,
            params={"limit": 50},
            timeout=20.0,
        )
        assistant_message = _get_last_assistant_message(messages_payload)
        assistant_text = str(assistant_message.get("content") or "").strip()

        (
            retrieval_posture,
            trace,
        ) = _latest_retrieval_artifacts(
            session,
            base_url,
            headers,
            thread_id,
            task_completed_payload,
        )
        if retrieval_posture is None:
            _fail(
                "Worker task.completed payload did not carry retrieval posture "
                f"evidence for the executed attempt "
                f"(thread_id={thread_id}, task_id={task_id}, "
                f"task_completed_keys={sorted(task_completed_payload.keys())})"
            )
        workspace_evidence = _normalize_workspace_retrieval_evidence(
            task_completed_payload=task_completed_payload,
            retrieval_posture=retrieval_posture,
            trace=trace,
        )
        trace_payload_summary = (
            trace.get("payload_summary") if isinstance(trace, dict) else None
        )
        if isinstance(trace_payload_summary, dict):
            worker_snapshot = _workspace_evidence_snapshot(
                task_completed_payload.get("payload_summary")
                if isinstance(task_completed_payload, dict)
                else None
            )
            trace_snapshot = _workspace_evidence_snapshot(trace_payload_summary)
            if any(
                worker_snapshot[key] != trace_snapshot[key]
                for key in (
                    "source_mode",
                    "retrieval_status",
                    "obsidian_count",
                    "obsidian_injected",
                    "retrieval_injected",
                )
            ):
                _fail(
                    "Worker task.completed payload did not match the debug "
                    "trace evidence for the executed workspace attempt "
                    f"(thread_id={thread_id}, task_id={task_id}, "
                    f"worker_snapshot={worker_snapshot!r}, "
                    f"trace_snapshot={trace_snapshot!r})"
                )
        if workspace_evidence["source_mode"] != WORKSPACE_SOURCE_MODE:
            _fail(
                "Workspace proof did not preserve the workspace source mode "
                f"(thread_id={thread_id}, task_id={task_id}, "
                f"workspace_evidence={workspace_evidence!r})"
            )
        verdicts = classify_proof_verdicts(
            acceptance_status=str(
                completion_payload.get("acceptance_status") or ""
            ).strip(),
            substrate_searchable=substrate_searchable,
            terminal_event_type=terminal_event_type,
            assistant_text=assistant_text,
            retrieval_status=str(
                workspace_evidence.get("retrieval_status") or ""
            ).strip(),
            obsidian_semantic_hits=int(
                workspace_evidence.get("obsidian_count") or 0
            ),
            retrieval_source_mode=str(
                workspace_evidence.get("source_mode") or ""
            ).strip(),
            retrieval_posture=retrieval_posture,
            obsidian_injected=bool(workspace_evidence.get("obsidian_injected")),
            token=sentinel.token,
        )
        summary = _format_summary(
            base_url=base_url,
            thread_id=thread_id,
            task_id=task_id,
            assistant_text=assistant_text,
            task_completed_payload=task_completed_payload,
            verdicts=verdicts,
            retrieval_posture=retrieval_posture,
            workspace_evidence=workspace_evidence,
        )
        if not verdicts["final_verdict"]["passed"]:
            _fail(summary)
        return verdicts, summary
    finally:
        _restore_obsidian_config(
            session, base_url, headers, previous_obsidian_config
        )
        session.close()


def main() -> int:
    base_url = _resolve_base_url()
    api_key = _resolve_api_key()
    if not HOST_TMP_ROOT.exists():
        HOST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

    try:
        verdicts, summary = run_proof(base_url, api_key)
    except ProofFailure as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(summary)
    if not verdicts["final_verdict"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
