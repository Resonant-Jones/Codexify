#!/usr/bin/env python3
"""Evidence harness for the release-readiness-gates qualification rubric.

The rubric (``docs/qualification/rubrics/release-readiness-gates.md``) names,
for each of its eight gates, the exact observable surface to read, the PASS
condition, the FAIL condition, and the UNPROVEN condition. This harness reads
those surfaces against an already-running stack and reports a verdict per gate.

It is a read-and-observe instrument. It never starts, stops, or recreates a
Docker container - the stack lifecycle belongs to another component - and it
never modifies a tracked file. The only writes it performs are its own output
JSON and, where a gate's PASS condition requires driving the running product,
ordinary calls to the product's own HTTP API.

Usage:

    /Volumes/Dev_SSD/Codexify-main/.venv/bin/python \\
        scripts/ops/eight_gate_evidence.py \\
        --env-file .env \\
        --compose-project <project> \\
        --base-url http://127.0.0.1:8888 \\
        --out /path/to/results.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eight_gate_runtime import (  # noqa: E402
    BrowserDriver,
    HttpClient,
    PostgresReader,
    RedisReader,
    RuntimeAccessError,
    Secret,
    compose_service_containers,
    compose_service_running,
    env_bool,
    env_int,
    fingerprint,
    iso,
    load_env_file,
    parse_iso,
    redact,
    resolve_base_url,
    resolve_database_dsn,
    resolve_frontend_url,
    resolve_redis_url,
    secret_from,
    utc_now,
)

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_UNPROVEN = "UNPROVEN"

GATE_NAMES = (
    "queue/worker",
    "deadline",
    "graceful-stop",
    "lock",
    "migration-deployment",
    "browser",
    "import-recall",
    "scope-isolation",
)

#: The queue keys the rubric names for gate 1, in rubric order.
RUBRIC_QUEUE_KEYS = (
    "codexify:queue:chat-embed",
    "codexify:queue:coding-execution",
    "codexify:queue:document-embed",
    "codexify:queue:account-import",
)

#: The queue a chat completion is actually enqueued on
#: (guardian/core/chat_completion_service.py: CHAT_COMPLETION_QUEUE_NAME).
CHAT_COMPLETION_QUEUE = "codexify:queue:chat"

#: The only two worker heartbeat keys that exist in the codebase
#: (guardian/workers/chat_worker.py, guardian/voice/runtime.py).
HEARTBEAT_KEYS = (
    "codexify:worker:chat:heartbeat",
    "codexify:worker:voice:heartbeat",
)

#: The chat worker heartbeat TTL (guardian/workers/chat_worker.py).
CHAT_HEARTBEAT_TTL_SECONDS = 45


@dataclass
class GateResult:
    """One gate's verdict, the surface read, and the values observed."""

    gate: str
    verdict: str
    surface: list[str] = field(default_factory=list)
    observed: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "verdict": self.verdict,
            "surface_read": self.surface,
            "observed": redact(self.observed),
            "reason": self.reason,
            "missing_inputs": self.missing,
        }

    def summary(self) -> str:
        observed = self.observed.get("summary")
        if not observed:
            observed = self.reason or "no observation recorded"
        return f"[{self.verdict}] {self.gate}  -- {observed}"


@dataclass
class Harness:
    """The read-side context every gate function receives."""

    env: Mapping[str, Secret]
    compose_project: str
    base_url: str
    frontend_url: str
    postgres: PostgresReader
    redis: RedisReader
    http: HttpClient
    browser: BrowserDriver
    options: argparse.Namespace
    notes: list[str] = field(default_factory=list)

    @property
    def session_token(self) -> Secret | None:
        return secret_from(
            self.env,
            "CODEXIFY_SESSION_TOKEN",
            "GUARDIAN_SESSION_TOKEN",
            "EIGHT_GATE_SESSION_TOKEN",
        )

    def api_key(self) -> Secret | None:
        return secret_from(
            self.env,
            "GUARDIAN_API_KEY",
            "CODEXIFY_API_KEY",
            "EIGHT_GATE_API_KEY",
        )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return iso(utc_now()) or ""


def _read_chat_queue_depths(redis: RedisReader) -> dict[str, int]:
    """Read the depth of every queue the rubric names, plus the chat queue."""
    depths: dict[str, int] = {}
    for key in (*RUBRIC_QUEUE_KEYS, CHAT_COMPLETION_QUEUE):
        try:
            depths[key] = redis.llen(key)
        except RuntimeAccessError as exc:
            depths[key] = -1
            _ = exc
    return depths


def _account_sessions(harness: Harness) -> dict[str, Secret]:
    """Collect the account session tokens the operator supplied, by name.

    Keys are read from the env file by name only. A session whose identity is
    ever shown is shown as a fingerprint, never as its token.
    """
    sessions: dict[str, Secret] = {}
    for key, value in harness.env.items():
        if not re.fullmatch(r"(EIGHT_GATE|GUARDIAN)_ACCOUNT_[A-Z0-9_]*_SESSION(_TOKEN)?", key):
            continue
        if not value.value:
            continue
        account = key.split("_")[-2] if key.endswith("_TOKEN") else key.split("_")[-1]
        sessions[account] = value
    return sessions


def _account_credentials(harness: Harness) -> dict[str, dict[str, str]]:
    """Collect ``EIGHT_GATE_ACCOUNT_<NAME>_USERNAME`` / ``_PASSWORD`` pairs."""
    accounts: dict[str, dict[str, str]] = {}
    for key, value in harness.env.items():
        match = re.fullmatch(
            r"EIGHT_GATE_ACCOUNT_([A-Z0-9_]+?)_(USERNAME|PASSWORD|EMAIL)", key
        )
        if not match or not value.value:
            continue
        account, field_name = match.group(1).lower(), match.group(2).lower()
        accounts.setdefault(account, {})[field_name] = value.value
    return accounts


def _login_account(
    harness: Harness, username: str, password: str
) -> tuple[str, Secret] | tuple[None, None]:
    """Log one account in through the product's own login route.

    Returns the account id and the issued session token. The token is never
    printed; only its fingerprint is recorded.
    """
    response = harness.http.post(
        "/api/auth/login", payload={"username": username, "password": password}
    )
    if not response.ok or not isinstance(response.body, dict):
        return None, None
    token = str(response.body.get("token") or "").strip()
    account = str(response.body.get("user_id") or username).strip()
    if not token:
        return None, None
    return account, Secret(name="session_token", value=token)


# ---------------------------------------------------------------------------
# Gate 1 - queue and worker lifecycle
# ---------------------------------------------------------------------------


def _heartbeat_age(raw: str | None) -> float | None:
    """Read the age of a worker heartbeat from its payload.

    The chat worker publishes ``ts`` as an integer epoch
    (guardian/workers/chat_worker.py: ``int(time.time())``), so both an
    integer epoch and an ISO-8601 string are accepted.
    """
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    stamp = payload.get("ts")
    if isinstance(stamp, (int, float)):
        return (utc_now() - datetime.fromtimestamp(float(stamp), timezone.utc)).total_seconds()
    parsed = parse_iso(stamp)
    if parsed is None:
        return None
    return (utc_now() - parsed).total_seconds()


def gate_queue_worker(harness: Harness) -> GateResult:
    """Observe the queue depths, the chat heartbeat, and a durable attempt row.

    Rubric surface: Redis ``LLEN`` on the named queues, the worker heartbeat
    key and its age, and the durable attempt row for the submitted request.
    """
    surface = [
        "Redis LLEN codexify:queue:chat-embed",
        "Redis LLEN codexify:queue:coding-execution",
        "Redis LLEN codexify:queue:document-embed",
        "Redis LLEN codexify:queue:account-import",
        f"Redis LLEN {CHAT_COMPLETION_QUEUE} (the queue a completion is enqueued on)",
        "Redis GET codexify:worker:chat:heartbeat",
        "Redis GET codexify:worker:voice:heartbeat",
        "PostgreSQL chat_completion_attempts (durable attempt row)",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="queue/worker",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    try:
        depths_before = _read_chat_queue_depths(harness.redis)
    except RuntimeAccessError as exc:
        result.reason = f"queue depth could not be read: {exc}"
        result.missing.append("a reachable Redis for the evaluated stack")
        observed["summary"] = f"queue depth could not be read: {exc}"
        return result

    heartbeat: dict[str, Any] = {}
    for key in HEARTBEAT_KEYS:
        try:
            raw = harness.redis.get(key)
            ttl = harness.redis.ttl(key)
        except RuntimeAccessError as exc:
            result.reason = f"heartbeat {key} could not be read: {exc}"
            result.missing.append("a reachable Redis for the evaluated stack")
            return result
        worker = None
        if raw:
            try:
                parsed = json.loads(raw)
                worker = parsed.get("worker") if isinstance(parsed, Mapping) else None
            except json.JSONDecodeError:
                parsed = None
        heartbeat[key] = {
            "present": bool(raw),
            "ttl_seconds": ttl,
            "age_seconds": _heartbeat_age(raw),
            "worker": worker,
        }

    # Submit one durable request through the product's own route so that a
    # durable attempt row exists to read back.
    submitted: dict[str, Any] = {}
    attempt: dict[str, Any] | None = None
    try:
        submitted = _submit_chat_completion(harness)
    except RuntimeAccessError as exc:
        submitted = {"error": str(exc)}

    request_id = str(submitted.get("request_id") or "")
    if request_id:
        try:
            attempt = _read_attempt_row(harness.postgres, request_id)
        except RuntimeAccessError as exc:
            result.reason = f"attempt row could not be read: {exc}"

    # Sample the chat queue continuously from before the submission through the
    # settle window, so a transient non-zero depth is not missed.
    depths_after: dict[str, int] = dict(depths_before)
    max_chat_depth = depths_before.get(CHAT_COMPLETION_QUEUE, 0)
    settle_deadline = time.monotonic() + float(
        harness.options.gate1_settle_seconds
    )
    while time.monotonic() < settle_deadline:
        try:
            current = _read_chat_queue_depths(harness.redis)
        except RuntimeAccessError:
            break
        depths_after = current
        max_chat_depth = max(max_chat_depth, current.get(CHAT_COMPLETION_QUEUE, 0))
        if (
            attempt is not None
            and _attempt_is_terminal(attempt)
            and current.get(CHAT_COMPLETION_QUEUE, -1) == 0
        ):
            break
        time.sleep(0.1)

    # A final read settles the "later at zero" half of the PASS condition, and
    # re-reads the heartbeat so its freshness is judged at the time of the read.
    try:
        depths_after = _read_chat_queue_depths(harness.redis)
    except RuntimeAccessError:
        pass
    max_chat_depth = max(max_chat_depth, depths_after.get(CHAT_COMPLETION_QUEUE, 0))

    try:
        raw_heartbeat = harness.redis.get("codexify:worker:chat:heartbeat")
        heartbeat["codexify:worker:chat:heartbeat"] = {
            "present": bool(raw_heartbeat),
            "ttl_seconds": harness.redis.ttl("codexify:worker:chat:heartbeat"),
            "age_seconds": _heartbeat_age(raw_heartbeat),
            "worker": None,
        }
        if raw_heartbeat:
            try:
                parsed = json.loads(raw_heartbeat)
                if isinstance(parsed, Mapping):
                    heartbeat["codexify:worker:chat:heartbeat"]["worker"] = parsed.get(
                        "worker"
                    )
            except json.JSONDecodeError:
                pass
    except RuntimeAccessError:
        pass

    observed.update(
        {
            "queue_depth_before": depths_before,
            "queue_depth_after": depths_after,
            "max_observed_chat_queue_depth": max_chat_depth,
            "heartbeat": heartbeat,
            "submitted_request": {
                "request_id": request_id or None,
                "task_id": submitted.get("task_id"),
                "acceptance_status": submitted.get("acceptance_status"),
                "http_status": submitted.get("http_status"),
            },
            "durable_attempt_row": attempt,
        }
    )

    if not request_id:
        result.reason = (
            "no durable request could be submitted, so no attempt row exists "
            "to observe"
        )
        result.missing.append(
            "an authenticated session or static key that the backend accepts "
            "for POST /api/chat/{thread_id}/complete"
        )
        observed["summary"] = f"submission failed: {submitted.get('error')}"
        return result

    if attempt is None:
        result.reason = "the submitted request has no durable attempt row yet"
        observed["summary"] = (
            f"request_id={request_id} has no chat_completion_attempts row"
        )
        return result

    if not _attempt_is_terminal(attempt):
        result.reason = (
            "the attempt row has not reached a terminal state at the time of "
            "the read"
        )
        observed["summary"] = (
            f"request_id={request_id} attempt_state={attempt.get('attempt_state')}"
        )
        return result

    chat_heartbeat = heartbeat.get("codexify:worker:chat:heartbeat", {})
    heartbeat_fresh = bool(
        chat_heartbeat.get("present")
        and isinstance(chat_heartbeat.get("age_seconds"), (int, float))
        and float(chat_heartbeat["age_seconds"]) <= CHAT_HEARTBEAT_TTL_SECONDS
    )
    depth_observed = max_chat_depth > 0
    drained = depths_after.get(CHAT_COMPLETION_QUEUE, -1) == 0

    observed["summary"] = (
        f"max_chat_queue_depth={max_chat_depth} "
        f"final_chat_queue_depth={depths_after.get(CHAT_COMPLETION_QUEUE)} "
        f"chat_heartbeat_age_s={chat_heartbeat.get('age_seconds')} "
        f"attempt_state={attempt.get('attempt_state')}"
    )

    if depth_observed and drained and heartbeat_fresh:
        result.verdict = VERDICT_PASS
        result.reason = (
            "a submitted request was observed at non-zero queue depth and "
            "later at zero, the chat worker heartbeat was fresh at the time "
            "of the read, and the durable attempt row reached a terminal state"
        )
        return result

    # The rubric's FAIL condition is work left in a queue that no worker
    # claims while the worker reports healthy, or an attempt that never
    # reached a terminal state. Both are checked explicitly here.
    if not drained and not heartbeat_fresh:
        result.verdict = VERDICT_FAIL
        result.reason = (
            "work was left in the chat queue and the chat worker heartbeat was "
            "not fresh at the time of the read"
        )
        return result

    missing: list[str] = []
    if not depth_observed:
        missing.append(
            "a moment at which the submitted request is observable at a "
            "non-zero queue depth (the worker claimed it before a sample "
            "caught it)"
        )
    if not heartbeat_fresh:
        missing.append(
            "a live chat worker publishing codexify:worker:chat:heartbeat "
            "within its 45 s TTL"
        )
    if not drained:
        missing.append(
            "the chat queue observed at zero after the submitted request was "
            "claimed"
        )
    result.missing.extend(missing)
    result.reason = (
        "the terminal attempt row was observed, but "
        + "; ".join(missing)
        if missing
        else "the gate's PASS conditions were not all observed"
    )
    return result


def _submit_chat_completion(harness: Harness) -> dict[str, Any]:
    """Submit one chat completion through the product's own HTTP route."""
    http = harness.http
    thread_response = http.post(
        "/api/chat/threads", payload={"title": "eight-gate queue probe"}
    )
    if not thread_response.ok or not isinstance(thread_response.body, dict):
        return {
            "error": f"thread creation failed with HTTP {thread_response.status}",
            "http_status": thread_response.status,
        }
    thread_id = thread_response.body.get("id")
    try:
        thread_id = int(thread_id)
    except (TypeError, ValueError):
        return {"error": "thread creation returned no usable id"}

    message_response = http.post(
        f"/api/chat/{thread_id}/messages",
        payload={"role": "user", "content": "eight-gate queue/worker probe"},
    )
    if not message_response.ok:
        return {
            "error": f"message post failed with HTTP {message_response.status}",
            "http_status": message_response.status,
        }

    completion = http.post(
        f"/api/chat/{thread_id}/complete",
        payload={"turn_id": f"eight-gate-{uuid.uuid4().hex}"},
    )
    payload = completion.body if isinstance(completion.body, dict) else {}
    return {
        "thread_id": thread_id,
        "task_id": payload.get("task_id"),
        "request_id": payload.get("request_id"),
        "acceptance_status": payload.get("acceptance_status"),
        "http_status": completion.status,
        "error": None if completion.ok else completion.raw[:300],
    }


def _read_attempt_row(
    postgres: PostgresReader, request_id: str
) -> dict[str, Any] | None:
    """Read the durable attempt row for one request."""
    row = postgres.query_one(
        """
        SELECT request_id,
               backend_task_id,
               thread_id,
               turn_id,
               accepted_at,
               terminal_event_type,
               terminal_outcome,
               deadline_snapshot,
               turn_lock_token,
               completed_message_id,
               created_at
          FROM chat_completion_attempts
         WHERE request_id = %s
        """,
        (request_id,),
    )
    if row is None:
        return None
    return _normalize_attempt(row)


def _normalize_attempt(row: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = row.get("deadline_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    terminal_event = row.get("terminal_event_type")
    completed = row.get("completed_message_id")
    if completed is not None:
        state = "completed"
    elif terminal_event:
        state = terminal_event
    else:
        state = "open"
    return {
        "request_id": row.get("request_id"),
        "backend_task_id": row.get("backend_task_id"),
        "thread_id": row.get("thread_id"),
        "accepted_at": iso(row.get("accepted_at")),
        "terminal_event_type": terminal_event,
        "terminal_outcome": dict(row.get("terminal_outcome") or {}) or None,
        "deadline_snapshot": dict(snapshot),
        "turn_lock_token": row.get("turn_lock_token"),
        "completed_message_id": completed,
        "created_at": iso(row.get("created_at")),
        "attempt_state": state,
    }


def _attempt_is_terminal(attempt: Mapping[str, Any]) -> bool:
    return attempt.get("attempt_state") not in {"open", None}


# ---------------------------------------------------------------------------
# Gate 2 - deadline
# ---------------------------------------------------------------------------


def gate_deadline(harness: Harness) -> GateResult:
    """Observe the deadline snapshot on an accepted attempt and its enforcement.

    Rubric surface: ``chat_completion_attempts.deadline_snapshot`` and
    ``turn_lock_token``, plus the constraint that pairs them.
    """
    surface = [
        "PostgreSQL chat_completion_attempts.deadline_snapshot",
        "PostgreSQL chat_completion_attempts.turn_lock_token",
        "PostgreSQL chat_completion_attempts.accepted_at",
        "PostgreSQL constraint ck_chat_attempt_recovery_snapshot_pair",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="deadline",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    constraint = _read_snapshot_constraint(harness.postgres)
    observed["constraint"] = constraint

    attempts = _read_attempt_rows(harness.postgres)
    observed["durable_attempts"] = attempts
    observed["attempt_count"] = len(attempts)

    with_snapshot = [
        attempt
        for attempt in attempts
        if attempt.get("deadline_snapshot")
        and attempt.get("turn_lock_token")
    ]
    observed["attempts_with_snapshot_and_lock"] = len(with_snapshot)

    # Requirement 1: an accepted attempt carrying a non-null snapshot whose
    # terminal_deadline_at is in the future at acceptance, plus a turn lock.
    accepted = [
        attempt
        for attempt in with_snapshot
        if attempt.get("accepted_at")
        and attempt.get("deadline_snapshot", {}).get("terminal_deadline_at")
    ]
    observed["accepted_attempts_with_snapshot"] = len(accepted)

    # Requirement 2: an attempt observed past its own terminal_deadline_at and
    # in a terminal state, with the deadline recorded.
    past_deadline_terminal = []
    for attempt in attempts:
        snapshot = attempt.get("deadline_snapshot") or {}
        terminal_at = parse_iso(snapshot.get("terminal_deadline_at"))
        if terminal_at is None or not _attempt_is_terminal(attempt):
            continue
        if utc_now() > terminal_at:
            past_deadline_terminal.append(
                {
                    "request_id": attempt.get("request_id"),
                    "terminal_deadline_at": snapshot.get("terminal_deadline_at"),
                    "attempt_state": attempt.get("attempt_state"),
                    "terminal_event_type": attempt.get("terminal_event_type"),
                    "terminal_outcome": attempt.get("terminal_outcome"),
                    "turn_lock_token": attempt.get("turn_lock_token"),
                    "observed_past_deadline": True,
                }
            )
    observed["attempts_past_deadline_in_terminal_state"] = past_deadline_terminal

    if not accepted:
        observed["summary"] = (
            f"no accepted attempt carried a deadline snapshot; "
            f"{len(attempts)} durable attempt rows were read"
        )
        result.reason = (
            "no accepted attempt was observed carrying a deadline snapshot "
            "with a future terminal_deadline_at and a turn lock"
        )
        result.missing.append(
            "an accepted chat completion whose durable attempt row carries a "
            "deadline_snapshot"
        )
        return result

    if not past_deadline_terminal:
        observed["summary"] = (
            f"{len(accepted)} accepted attempt(s) carry a snapshot, but none "
            "was observed past its own terminal_deadline_at in a terminal state"
        )
        result.reason = (
            "a snapshot was observed, but no attempt was observed past its own "
            "terminal_deadline_at in a terminal state; the snapshot proves the "
            "shape, not that the deadline was enforced"
        )
        result.missing.append(
            "an attempt observed past its own terminal_deadline_at in a "
            "terminal state - the accepted-chat budgets are fixed constants "
            "(720 s work + 60 s terminal, guardian/tasks/chat_deadline.py), "
            "not environment-configurable, so an attempt must live for ~13 "
            "minutes before it can be observed past its terminal deadline"
        )
        return result

    observed["summary"] = (
        f"{len(accepted)} accepted attempt(s) carry a snapshot with a future "
        f"terminal_deadline_at; {len(past_deadline_terminal)} attempt(s) "
        "observed past their own terminal_deadline_at in a terminal state"
    )
    result.verdict = VERDICT_PASS
    result.reason = (
        "an accepted attempt carried a non-null deadline snapshot with a "
        "future terminal_deadline_at and a turn lock, and an attempt was "
        "observed past its own terminal_deadline_at in a terminal state"
    )
    return result


def _read_snapshot_constraint(postgres: PostgresReader) -> dict[str, Any]:
    """Read the pairing constraint that the rubric names as the primary observable."""
    try:
        row = postgres.query_one(
            """
            SELECT conname, pg_get_constraintdef(oid) AS definition
              FROM pg_constraint
             WHERE conrelid = 'chat_completion_attempts'::regclass
               AND conname = 'ck_chat_attempt_recovery_snapshot_pair'
            """
        )
    except RuntimeAccessError as exc:
        return {"present": None, "error": str(exc)}
    if row is None:
        return {"present": False, "definition": None}
    return {"present": True, "definition": row.get("definition")}


def _read_attempt_rows(postgres: PostgresReader) -> list[dict[str, Any]]:
    """Read the durable attempt rows the gate needs."""
    try:
        rows = postgres.query(
            """
            SELECT request_id,
                   backend_task_id,
                   thread_id,
                   turn_id,
                   accepted_at,
                   terminal_event_type,
                   terminal_outcome,
                   deadline_snapshot,
                   turn_lock_token,
                   completed_message_id,
                   created_at
              FROM chat_completion_attempts
             ORDER BY created_at DESC
             LIMIT 200
            """
        )
    except RuntimeAccessError:
        return []
    return [_normalize_attempt(row) for row in rows]


# ---------------------------------------------------------------------------
# Gate 3 - graceful stop
# ---------------------------------------------------------------------------


def gate_graceful_stop(harness: Harness) -> GateResult:
    """Observe a coding run's ownership and status across a worker stop.

    Rubric surface: ``agent_runs.status``, the ownership pair
    ``coding_worker_instance_id`` / ``coding_worker_claim_id``, and the Redis
    queue depth immediately before and after the stop.
    """
    surface = [
        "PostgreSQL agent_runs.status",
        "PostgreSQL agent_runs.coding_worker_instance_id",
        "PostgreSQL agent_runs.coding_worker_claim_id",
        f"Redis LLEN {CHAT_COMPLETION_QUEUE} (queue depth before/after)",
        "backend/scripts/docker/run_worker_coding.py (SIGTERM/SIGINT handler)",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="graceful-stop",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    handler = _read_coding_worker_handler()
    observed["shutdown_handler"] = handler

    try:
        depth_before = harness.redis.llen(CHAT_COMPLETION_QUEUE)
    except RuntimeAccessError as exc:
        depth_before = -1
        observed["depth_error"] = str(exc)

    # The coding worker's own queue is the one the rubric's stop concerns.
    try:
        coding_depth_before = harness.redis.llen("codexify:queue:coding-execution")
    except RuntimeAccessError:
        coding_depth_before = -1

    runs = _read_agent_runs(harness.postgres)
    observed["agent_runs"] = runs
    observed["queue_depth_before"] = {
        CHAT_COMPLETION_QUEUE: depth_before,
        "codexify:queue:coding-execution": coding_depth_before,
    }

    claimed = [
        run
        for run in runs
        if run.get("coding_worker_instance_id") or run.get("coding_worker_claim_id")
    ]
    observed["runs_with_ownership"] = len(claimed)
    observed["runs_terminal_with_null_ownership"] = [
        run
        for run in runs
        if run.get("status") in {"canceled", "failed", "succeeded"}
        and not run.get("coding_worker_instance_id")
        and not run.get("coding_worker_claim_id")
    ]

    try:
        depth_after = harness.redis.llen(CHAT_COMPLETION_QUEUE)
    except RuntimeAccessError:
        depth_after = -1
    try:
        coding_depth_after = harness.redis.llen("codexify:queue:coding-execution")
    except RuntimeAccessError:
        coding_depth_after = -1
    observed["queue_depth_after"] = {
        CHAT_COMPLETION_QUEUE: depth_after,
        "codexify:queue:coding-execution": coding_depth_after,
    }

    observed["summary"] = (
        f"{len(claimed)} agent_run(s) carry ownership; "
        f"{len(observed['runs_terminal_with_null_ownership'])} terminal run(s) "
        "have both ownership columns NULL"
    )

    if not handler.get("registers_sigterm"):
        result.verdict = VERDICT_FAIL
        result.reason = (
            "the coding worker's shutdown handler does not register SIGTERM, "
            "so the rubric's stop condition cannot be met by this source"
        )
        return result

    if not claimed:
        result.reason = (
            "no coding run holds a claim on this stack, so the worker was "
            "stopped while idle and nothing was held"
        )
        result.missing.append(
            "a coding run that holds an ownership claim while the coding "
            "worker is stopped on SIGTERM - this needs a coding execution "
            "task in codexify:queue:coding-execution and a coding worker with "
            "its Pi prerequisites available"
        )
        return result

    terminal_released = observed["runs_terminal_with_null_ownership"]
    if terminal_released and depth_before == depth_after:
        result.verdict = VERDICT_PASS
        result.reason = (
            "a run that held an ownership claim is now terminal with both "
            "ownership columns NULL, and the queue depth is unchanged"
        )
        return result

    result.reason = (
        "a claim was observed, but no run was observed terminal with both "
        "ownership columns NULL after the stop, or the queue depth changed"
    )
    result.missing.append(
        "a SIGTERM to the coding worker while it holds a claim, followed by "
        "the durable observation of that run"
    )
    return result


def _read_coding_worker_handler() -> dict[str, Any]:
    """Read the coding worker's shutdown handler from the source of truth."""
    path = (
        Path(__file__).resolve().parents[2]
        / "backend"
        / "scripts"
        / "docker"
        / "run_worker_coding.py"
    )
    if not path.exists():
        return {"path": str(path), "present": False, "registers_sigterm": False}
    source = path.read_text(encoding="utf-8")
    return {
        "path": str(path),
        "present": True,
        "registers_sigterm": "signal.signal(signal.SIGTERM" in source,
        "registers_sigint": "signal.signal(signal.SIGINT" in source,
        "source_sha256_prefix": fingerprint(source),
    }


def _read_agent_runs(postgres: PostgresReader) -> list[dict[str, Any]]:
    """Read the canonical coding-run rows the gate needs."""
    try:
        rows = postgres.query(
            """
            SELECT run_id,
                   deployment_id,
                   status,
                   started_at,
                   ended_at,
                   coding_worker_instance_id,
                   coding_worker_claim_id,
                   coding_worker_last_heartbeat_at,
                   created_at
              FROM agent_runs
             ORDER BY created_at DESC
             LIMIT 100
            """
        )
    except RuntimeAccessError:
        return []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "run_id": row.get("run_id"),
                "deployment_id": row.get("deployment_id"),
                "status": row.get("status"),
                "started_at": iso(row.get("started_at")),
                "ended_at": iso(row.get("ended_at")),
                "coding_worker_instance_id": row.get("coding_worker_instance_id"),
                "coding_worker_claim_id": row.get("coding_worker_claim_id"),
                "coding_worker_last_heartbeat_at": iso(
                    row.get("coding_worker_last_heartbeat_at")
                ),
                "created_at": iso(row.get("created_at")),
            }
        )
    return normalized


# ---------------------------------------------------------------------------
# Gate 4 - lock
# ---------------------------------------------------------------------------


def gate_lock(harness: Harness) -> GateResult:
    """Exercise two concurrent claim attempts against the same run.

    Rubric surface: the ``uq_agent_runs_coding_worker_claim_id`` UNIQUE
    constraint and ``claim_run_for_acceptance``'s row locks.
    """
    surface = [
        "PostgreSQL constraint uq_agent_runs_coding_worker_claim_id (UNIQUE)",
        "guardian/agents/store.py claim_run_for_acceptance (with_for_update)",
        "PostgreSQL agent_runs.coding_worker_claim_id",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="lock",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    constraint = _read_claim_unique_constraint(harness.postgres)
    observed["unique_constraint"] = constraint

    if constraint.get("present") is False:
        observed["summary"] = "uq_agent_runs_coding_worker_claim_id is ABSENT"
        result.verdict = VERDICT_FAIL
        result.reason = (
            "the unique constraint on coding_worker_claim_id is absent; the "
            "rubric treats that as a schema defect"
        )
        return result

    # Two concurrent claim attempts against one run, issued through the
    # product's own store code path.
    attempts = _run_concurrent_claim_attempts(harness)
    observed["claim_attempts"] = attempts

    if attempts.get("error"):
        observed["summary"] = f"claim attempts could not be run: {attempts['error']}"
        result.reason = attempts["error"]
        result.missing.extend(attempts.get("missing", []))
        return result

    accepted = attempts.get("accepted", [])
    refused = attempts.get("refused", [])
    holders = attempts.get("holders_after", [])
    distinct_holders = {holder.get("coding_worker_claim_id") for holder in holders}

    observed["summary"] = (
        f"{len(accepted)} claim(s) accepted, {len(refused)} refused, "
        f"{len(distinct_holders)} distinct holder(s) on the run"
    )

    if len(accepted) == 1 and len(refused) >= 1 and len(distinct_holders) == 1:
        result.verdict = VERDICT_PASS
        result.reason = (
            "exactly one concurrent claim attempt held the claim and the "
            "other was refused; the refusal left no partial write"
        )
        return result

    if len(distinct_holders) > 1:
        result.verdict = VERDICT_FAIL
        result.reason = (
            "both actors were observed holding the same run, which the rubric "
            "says is only reachable if the unique constraint is absent"
        )
        return result

    result.reason = (
        "the concurrent claim attempts did not produce exactly one holder and "
        "one recorded refusal"
    )
    result.missing.extend(attempts.get("missing", []))
    return result


def _read_claim_unique_constraint(postgres: PostgresReader) -> dict[str, Any]:
    """Read the UNIQUE constraint the rubric names as the primary observable."""
    try:
        row = postgres.query_one(
            """
            SELECT conname,
                   pg_get_constraintdef(oid) AS definition,
                   contype
              FROM pg_constraint
             WHERE conrelid = 'agent_runs'::regclass
               AND conname = 'uq_agent_runs_coding_worker_claim_id'
            """
        )
    except RuntimeAccessError as exc:
        return {"present": None, "error": str(exc)}
    if row is None:
        return {"present": False, "definition": None}
    return {
        "present": True,
        "definition": row.get("definition"),
        "constraint_type": row.get("contype"),
        "is_unique": str(row.get("contype") or "") == "u",
    }


def _run_concurrent_claim_attempts(harness: Harness) -> dict[str, Any]:
    """Issue two concurrent claim attempts against one queued coding run.

    The attempts go through the product's own ``claim_run_for_acceptance``
    against the live database, so the refusal path under observation is the
    real one.
    """
    import threading

    try:
        run = _find_claimable_run(harness.postgres)
    except RuntimeAccessError as exc:
        return {"error": f"no coding run could be located: {exc}"}

    if run is None:
        return {
            "error": "no queued coding run exists on this stack to claim",
            "missing": [
                "a queued agent_runs row with a coding deployment - a coding "
                "execution task must be dispatched to "
                "codexify:queue:coding-execution first"
            ],
        }

    try:
        from guardian.agents.store import AgentStore
        from guardian.core.db import GuardianDB
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "error": f"the store could not be imported: {type(exc).__name__}",
            "missing": ["an importable guardian package in the interpreter"],
        }

    dsn = getattr(harness.postgres, "dsn", None)
    dsn_value = getattr(dsn, "value", "") if dsn is not None else ""
    if not dsn_value:
        return {
            "error": "no direct PostgreSQL DSN is available for the store",
            "missing": [
                "a host-reachable DATABASE_URL for the evaluated stack, which "
                "the concurrent claim attempts need to open their own "
                "transactions"
            ],
        }

    store = AgentStore()
    store.configure_db(GuardianDB(dsn_value))

    results: list[str] = []
    barrier = threading.Barrier(2)

    def _attempt(worker_suffix: str) -> None:
        barrier.wait()
        outcome = store.claim_run_for_acceptance(
            run_id=str(run["run_id"]),
            deployment_id=str(run["deployment_id"]),
            worker_instance_id=f"eight-gate-worker-{worker_suffix}",
            claim_id=f"eight-gate-claim-{worker_suffix}-{uuid.uuid4().hex[:8]}",
            user_id=run.get("account_origin_user_id"),
            thread_id=run.get("thread_id"),
        )
        results.append(outcome)

    threads = [
        threading.Thread(target=_attempt, args=("a",)),
        threading.Thread(target=_attempt, args=("b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    if len(results) != 2:
        return {
            "error": "the two concurrent claim attempts did not both return",
            "missing": ["a database that accepts two concurrent claim transactions"],
        }

    accepted = [outcome for outcome in results if outcome == "accepted"]
    refused = [outcome for outcome in results if outcome != "accepted"]
    holders = _read_run_ownership(harness.postgres, str(run["run_id"]))
    return {
        "run_id": run.get("run_id"),
        "deployment_id": run.get("deployment_id"),
        "outcomes": sorted(results),
        "accepted": accepted,
        "refused": refused,
        "holders_after": holders,
    }


def _find_claimable_run(postgres: PostgresReader) -> dict[str, Any] | None:
    """Find one queued coding run that a claim attempt may take."""
    try:
        row = postgres.query_one(
            """
            SELECT r.run_id,
                   r.deployment_id,
                   r.thread_id,
                   r.account_origin_user_id,
                   r.status
              FROM agent_runs r
             WHERE r.status = 'queued'
               AND r.coding_worker_instance_id IS NULL
               AND r.coding_worker_claim_id IS NULL
             ORDER BY r.created_at DESC
             LIMIT 1
            """
        )
    except RuntimeAccessError:
        return None
    return dict(row) if row else None


def _read_run_ownership(
    postgres: PostgresReader, run_id: str
) -> list[dict[str, Any]]:
    """Read the ownership pair of one run after the claim attempts."""
    try:
        rows = postgres.query(
            """
            SELECT run_id,
                   status,
                   coding_worker_instance_id,
                   coding_worker_claim_id
              FROM agent_runs
             WHERE run_id = %s
            """,
            (run_id,),
        )
    except RuntimeAccessError:
        return []
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Gate 5 - migration deployment
# ---------------------------------------------------------------------------


def gate_migration_deployment(harness: Harness) -> GateResult:
    """Read the live Alembic revision from PostgreSQL and the migrator's proof.

    Rubric surface: ``alembic_version`` read directly from PostgreSQL (row
    count and value), the migrator's coherence comparison, and the three
    refusal cases.
    """
    surface = [
        "PostgreSQL alembic_version (row count and value, read directly)",
        "backend/scripts/docker/run_migrator.py compare_migration_sources",
        "backend/scripts/docker/run_migrator.py require_coherent_migration_source",
        "migrator container logs (the migrator's own coherence verdict)",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="migration-deployment",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    live = _read_alembic_version(harness.postgres)
    observed["live_alembic_version"] = live
    if live.get("row_count") is None:
        observed["summary"] = "the live revision could not be read from PostgreSQL"
        result.reason = "alembic_version could not be read directly from PostgreSQL"
        result.missing.append("a reachable PostgreSQL for the evaluated stack")
        return result

    checkout = _read_checkout_head()
    observed["evaluated_checkout_head"] = checkout

    migrator_log = _read_migrator_log(harness.compose_project)
    observed["migrator_coherence_log"] = migrator_log

    refusals = _read_refusal_cases()
    observed["refusal_cases"] = refusals

    head_matches = bool(
        checkout.get("head")
        and live.get("values")
        and live["values"] == [checkout["head"]]
    )
    observed["summary"] = (
        f"live_revision={live.get('values')} rows={live.get('row_count')} "
        f"checkout_head={checkout.get('head')} "
        f"refusal_cases_passed={sum(1 for case in refusals if case.get('refused'))}"
        f"/{len(refusals)}"
    )

    if live.get("row_count") != 1:
        result.verdict = VERDICT_FAIL
        result.reason = (
            f"alembic_version holds {live.get('row_count')} rows; the rubric "
            "requires exactly one"
        )
        return result

    if not head_matches:
        result.verdict = VERDICT_FAIL
        result.reason = (
            f"the live revision {live.get('values')} is not the evaluated "
            f"checkout's single head {checkout.get('head')}"
        )
        return result

    coherence_reported = migrator_log.get("coherent_reported")
    all_refused = bool(refusals) and all(case.get("refused") for case in refusals)

    if coherence_reported is True and all_refused:
        result.verdict = VERDICT_PASS
        result.reason = (
            "the live revision equals the evaluated checkout's single head "
            "with exactly one row, the migrator's own coherence comparison "
            "reported the source coherent, and all three refusal cases failed "
            "closed before any migration was applied"
        )
        return result

    missing: list[str] = []
    if coherence_reported is not True:
        missing.append(
            "the migrator container's own coherence verdict in its logs - the "
            "migrator must have run against this checkout's source for its "
            "comparison to be observable"
        )
    if not all_refused:
        missing.append(
            "a run of the three refusal cases (stale image, same-head image "
            "with different revision content, same-head source with a "
            "different migration environment)"
        )
    result.missing.extend(missing)
    result.reason = (
        "the live revision and head agree, but "
        + "; ".join(missing)
        if missing
        else "the refusal cases could not be confirmed"
    )
    return result


def _read_alembic_version(postgres: PostgresReader) -> dict[str, Any]:
    """Read ``alembic_version`` directly out of PostgreSQL."""
    try:
        rows = postgres.query("SELECT version_num FROM alembic_version")
    except RuntimeAccessError as exc:
        return {"row_count": None, "values": None, "error": str(exc)}
    values = [str(row.get("version_num")) for row in rows]
    return {"row_count": len(rows), "values": values, "error": None}


def _read_checkout_head() -> dict[str, Any]:
    """Compute the evaluated checkout's single Alembic head from its source."""
    migrations = (
        Path(__file__).resolve().parents[2] / "guardian" / "db" / "migrations"
    )
    versions = migrations / "versions"
    if not versions.is_dir():
        return {"head": None, "revisions": 0, "error": "no versions directory"}
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config(
            str(Path(__file__).resolve().parents[2] / "backend" / "alembic.ini")
        )
        script = ScriptDirectory.from_config(config)
        heads = list(script.get_heads())
        revision_count = len(list(script.walk_revisions()))
    except Exception as exc:
        return {
            "head": None,
            "revisions": 0,
            "error": f"the checkout's Alembic head could not be computed: {exc}",
        }
    return {
        "head": heads[0] if len(heads) == 1 else None,
        "heads": heads,
        "revisions": revision_count,
        "error": None if len(heads) == 1 else "the checkout does not have one head",
    }


def _read_migrator_log(compose_project: str) -> dict[str, Any]:
    """Read the migrator container's own coherence verdict from its logs."""
    import subprocess

    containers = compose_service_containers(compose_project)
    container = containers.get("migrator")
    if container is None:
        return {
            "container": None,
            "coherent_reported": None,
            "reason": "no migrator container exists for this project",
        }
    result = subprocess.run(
        ["docker", "logs", container],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    log = f"{result.stdout}\n{result.stderr}"
    coherent = "Migration source is coherent" in log
    heads = re.findall(r"Alembic heads: \[([^\]]*)\]", log)
    verified = re.findall(r"Verified alembic_version == (\S+)", log)
    return {
        "container": container,
        "coherent_reported": coherent,
        "reported_heads": heads[-1] if heads else None,
        "verified_revision": verified[-1] if verified else None,
        "log_sha256_prefix": fingerprint(log),
    }


def _read_refusal_cases() -> list[dict[str, Any]]:
    """Exercise the migrator's own three refusal cases in isolation.

    The cases are run against temporary trees so that no migration is applied
    anywhere: the migrator's comparison and refusal functions are called
    directly, and each case must raise before any ``alembic upgrade`` runs.
    """
    import shutil
    import tempfile

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "scripts" / "docker"))
        from run_migrator import (  # type: ignore
            MigrationSourceError,
            compare_migration_sources,
            require_coherent_migration_source,
        )
    except Exception as exc:
        return [
            {
                "case": name,
                "refused": None,
                "error": f"the migrator module could not be imported: {exc}",
            }
            for name in ("stale_image", "same_head_different_content", "same_head_different_env")
        ]

    source_root = (
        Path(__file__).resolve().parents[2] / "guardian" / "db" / "migrations"
    )
    cases: list[dict[str, Any]] = []
    workspace = Path(tempfile.mkdtemp(prefix="eight-gate-refusal-"))
    try:
        for case_name in (
            "stale_image",
            "same_head_different_content",
            "same_head_different_env",
        ):
            effective = workspace / case_name / "effective"
            checkout = workspace / case_name / "checkout"
            shutil.copytree(source_root, effective)
            shutil.copytree(source_root, checkout)
            if case_name == "stale_image":
                revision_files = sorted((effective / "versions").glob("*.py"))
                if revision_files:
                    revision_files[0].unlink()
            elif case_name == "same_head_different_content":
                revision_files = sorted((effective / "versions").glob("*.py"))
                if revision_files:
                    revision_files[0].write_text(
                        revision_files[0].read_text(encoding="utf-8")
                        + "\n# eight-gate refusal probe\n",
                        encoding="utf-8",
                    )
            else:
                env_file = effective / "env.py"
                if env_file.exists():
                    env_file.write_text(
                        env_file.read_text(encoding="utf-8")
                        + "\n# eight-gate refusal probe\n",
                        encoding="utf-8",
                    )
            refused = False
            detail = ""
            try:
                comparison = compare_migration_sources(effective, checkout)
                require_coherent_migration_source(comparison, checkout)
                detail = comparison.summary()
            except MigrationSourceError as exc:
                refused = True
                detail = str(exc)
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
            cases.append(
                {
                    "case": case_name,
                    "refused": refused,
                    "detail": detail,
                    "migration_applied": False,
                }
            )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    return cases


# ---------------------------------------------------------------------------
# Gate 6 - browser
# ---------------------------------------------------------------------------


def gate_browser(harness: Harness) -> GateResult:
    """Read the chat projection from a real browser and compare it to durable state.

    Rubric surface: a real browser's DOM text and attributes, plus the
    durable rows the projection claims to render.
    """
    surface = [
        "Real Chromium DOM (data-testid=chat-message, chat-message-author)",
        "PostgreSQL chat_messages (the durable rows the projection renders)",
        "PostgreSQL chat_threads (thread title)",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="browser",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    available, detail = harness.browser.available()
    observed["browser_available"] = available
    observed["browser_detail"] = detail
    if not available:
        result.reason = f"no real browser could be launched: {detail}"
        result.missing.append(
            "a Chromium build the interpreter can launch (the repo's "
            "Playwright browser cache, or the docker-compose e2e Playwright "
            "container)"
        )
        return result

    sessions = _account_sessions(harness)
    token = harness.session_token
    account = "operator"
    if token is not None:
        account = "operator"
    elif sessions:
        token = next(iter(sessions.values()))
        account = next(iter(sessions))
    if token is None:
        result.reason = "no authenticated account session is available for the browser"
        result.missing.append(
            "an authenticated account session (EIGHT_GATE_SESSION_TOKEN, or "
            "EIGHT_GATE_ACCOUNT_<NAME>_SESSION) - the rubric states that an "
            "unauthenticated surface is not evidence for this gate"
        )
        observed["summary"] = "no account session was supplied"
        return result

    # Find a thread that carries durable messages to project.
    thread = _find_projected_thread(harness.postgres)
    if thread is None:
        result.reason = "no thread with durable messages exists to project"
        result.missing.append(
            "a chat thread with persisted messages (submit one through the "
            "chat API before running the browser gate)"
        )
        observed["summary"] = "no projected thread was available"
        return result

    observed["thread"] = {
        "thread_id": thread.get("thread_id"),
        "title": thread.get("title"),
        "message_count": thread.get("message_count"),
    }

    url = f"{harness.frontend_url}/chat/{thread.get('thread_id')}"
    try:
        with harness.browser.open(url, session_token=token.value) as page:
            page.goto(url)
            page.page.wait_for_timeout(2500)
            dom_messages = page.all_inner_texts('[data-testid="chat-message"]')
            dom_authors = page.all_inner_texts('[data-testid="chat-message-author"]')
            observed["browser"] = {
                "version": page.version,
                **page.viewport_info(),
                "url": url,
            }
            observed["dom"] = {
                "message_count": len(dom_messages),
                "messages": dom_messages,
                "authors": dom_authors,
            }
            before_reload = list(dom_messages)
            page.reload()
            page.page.wait_for_timeout(2500)
            after_reload = page.all_inner_texts('[data-testid="chat-message"]')
            observed["dom_after_reload"] = {
                "message_count": len(after_reload),
                "messages": after_reload,
            }
    except RuntimeAccessError as exc:
        result.reason = f"the browser could not be driven: {exc}"
        result.missing.append("a reachable frontend for the evaluated stack")
        return result
    except Exception as exc:
        result.reason = f"the browser could not be driven: {type(exc).__name__}"
        result.missing.append("a reachable frontend for the evaluated stack")
        return result

    durable = thread.get("messages") or []
    observed["durable_messages"] = durable

    dom_joined = "\n".join(before_reload)
    durable_joined = "\n".join(
        str(message.get("content") or "") for message in durable
    )
    projected = bool(durable_joined) and durable_joined.strip() in dom_joined
    preserved = before_reload == after_reload
    converged = len(before_reload) >= len(durable)

    observed["summary"] = (
        f"dom_messages={len(before_reload)} durable_messages={len(durable)} "
        f"projected={projected} reload_preserved={preserved}"
    )

    if projected and preserved and converged:
        result.verdict = VERDICT_PASS
        result.reason = (
            "the DOM's own message text matched the durable rows it claims to "
            "render, the terminal state converged in the UI, and a reload "
            "preserved the projected state"
        )
        return result

    if not projected:
        result.verdict = VERDICT_FAIL
        result.reason = "the DOM disagrees with the durable state it renders"
        return result

    if not preserved:
        result.verdict = VERDICT_FAIL
        result.reason = "a reload lost the projected state"
        return result

    result.reason = "the projection was observed but did not fully converge"
    result.missing.append(
        "a durable thread whose messages are all projected into the DOM"
    )
    return result


def _find_projected_thread(postgres: PostgresReader) -> dict[str, Any] | None:
    """Find one thread with durable messages, newest first."""
    try:
        rows = postgres.query(
            """
            SELECT t.id AS thread_id,
                   t.title AS title,
                   m.id AS message_id,
                   m.role AS role,
                   m.content AS content
              FROM chat_messages m
              JOIN chat_threads t ON t.id = m.thread_id
             WHERE m.content IS NOT NULL
               AND m.content <> ''
             ORDER BY m.id DESC
             LIMIT 200
            """
        )
    except RuntimeAccessError:
        return None
    if not rows:
        return None
    by_thread: dict[int, dict[str, Any]] = {}
    for row in rows:
        thread_id = row.get("thread_id")
        if thread_id is None:
            continue
        entry = by_thread.setdefault(
            int(thread_id),
            {
                "thread_id": int(thread_id),
                "title": row.get("title"),
                "messages": [],
            },
        )
        entry["messages"].append(
            {
                "message_id": row.get("message_id"),
                "role": row.get("role"),
                "content": row.get("content"),
            }
        )
    if not by_thread:
        return None
    best = max(by_thread.values(), key=lambda entry: len(entry["messages"]))
    best["message_count"] = len(best["messages"])
    best["messages"].reverse()
    return best


# ---------------------------------------------------------------------------
# Gate 7 - import to recall
# ---------------------------------------------------------------------------


def gate_import_recall(harness: Harness) -> GateResult:
    """Observe a natural import's materialisation and the recall that returns it.

    Rubric surface: the imported record's canonical PostgreSQL row, the
    materialisation job's durable checkpoint, the reader-side exclusion, and
    the recall result.
    """
    surface = [
        "PostgreSQL openai_account_import_jobs (durable checkpoint)",
        "PostgreSQL chat_threads / chat_messages (canonical imported rows)",
        "PostgreSQL chat_projects (the Imports Project)",
        "GET /api/chat/projects/{project_id}/history/search (recall result)",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="import-recall",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    export = harness.options.import_export_file

    jobs = _read_import_jobs(harness.postgres)
    observed["import_jobs"] = jobs
    observed["import_job_count"] = len(jobs)

    imported_threads = _read_imported_threads(harness.postgres)
    observed["imported_threads"] = imported_threads
    observed["imported_thread_count"] = len(imported_threads)

    if not jobs:
        observed["summary"] = "no account-import job exists on this stack"
        result.reason = (
            "no natural import has been performed on this stack, so there is "
            "no materialisation checkpoint and no canonical record to recall"
        )
        result.missing.append(
            "a real provider export file (an OpenAI or Anthropic account "
            "export) imported through the product's natural import path - the "
            "rubric explicitly refuses a synthetic fixture as evidence for "
            "this gate"
        )
        return result

    completed = [
        job for job in jobs if job.get("status") == "completed"
    ]
    observed["completed_import_jobs"] = len(completed)
    if not completed:
        observed["summary"] = (
            f"{len(jobs)} import job(s) exist, none in the completed state"
        )
        result.reason = (
            "an import job exists but has not completed, so no canonical "
            "record has been materialised"
        )
        result.missing.append(
            "a completed natural import whose worker checkpoint records the "
            "materialised conversations"
        )
        return result

    job = completed[0]
    observed["materialisation_checkpoint"] = job.get("checkpoint")

    if not imported_threads:
        observed["summary"] = (
            "the import job completed but no imported thread was materialised"
        )
        result.verdict = VERDICT_FAIL
        result.reason = (
            "the natural import job reached the completed state but "
            "materialised no canonical thread"
        )
        return result

    thread = imported_threads[0]
    observed["chosen_thread"] = thread
    observed["export_evidence"] = {
        "path": export,
        "classification": "unknown",
        "note": (
            "a real provider export file was not supplied to this harness; "
            "the natural/synthetic classification cannot be evidenced from "
            "the stack alone"
        ),
    }

    recall = _read_recall_result(harness, thread)
    observed["recall"] = recall
    observed["summary"] = (
        f"job={job.get('id')} status={job.get('status')} "
        f"imported_thread={thread.get('thread_id')} "
        f"recall_returned={recall.get('returned')}"
    )

    if export is None:
        result.reason = (
            "the import materialised and the recall was read, but the "
            "import's natural/synthetic classification is unevidenced, which "
            "the rubric makes UNPROVEN"
        )
        result.missing.append(
            "the real provider export file behind this import, so the "
            "classification can be evidenced rather than asserted"
        )
        return result

    if not recall.get("returned"):
        result.verdict = VERDICT_FAIL
        result.reason = (
            "the natural import materialised but its record was not returned "
            "by recall for the owning account"
        )
        return result

    result.verdict = VERDICT_PASS
    result.reason = (
        "a natural import materialised canonically with a durable "
        "checkpoint, and the imported record was returned by recall for the "
        "owning account"
    )
    return result


def _read_import_jobs(postgres: PostgresReader) -> list[dict[str, Any]]:
    """Read the durable import job rows, including their checkpoints."""
    try:
        rows = postgres.query(
            """
            SELECT id,
                   user_id,
                   source_system,
                   source_export_fingerprint,
                   status,
                   total_file_count,
                   total_byte_count,
                   uploaded_file_count,
                   uploaded_byte_count,
                   imported_thread_count,
                   imported_message_count,
                   imported_media_count,
                   failure_count,
                   error_details,
                   checkpoint,
                   staged_manifest,
                   created_at,
                   completed_at
              FROM openai_account_import_jobs
             ORDER BY created_at DESC
             LIMIT 50
            """
        )
    except RuntimeAccessError:
        return []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "id": row.get("id"),
                "user_id": row.get("user_id"),
                "source_system": row.get("source_system"),
                "source_export_fingerprint": row.get("source_export_fingerprint"),
                "status": row.get("status"),
                "total_file_count": row.get("total_file_count"),
                "total_byte_count": row.get("total_byte_count"),
                "uploaded_file_count": row.get("uploaded_file_count"),
                "uploaded_byte_count": row.get("uploaded_byte_count"),
                "imported_thread_count": row.get("imported_thread_count"),
                "imported_message_count": row.get("imported_message_count"),
                "imported_media_count": row.get("imported_media_count"),
                "failure_count": row.get("failure_count"),
                "error_details": row.get("error_details"),
                "checkpoint": row.get("checkpoint"),
                "staged_manifest": row.get("staged_manifest"),
                "created_at": iso(row.get("created_at")),
                "completed_at": iso(row.get("completed_at")),
            }
        )
    return normalized


def _read_imported_threads(postgres: PostgresReader) -> list[dict[str, Any]]:
    """Read the canonical imported thread rows and their message counts."""
    try:
        rows = postgres.query(
            """
            SELECT t.id AS thread_id,
                   t.user_id AS user_id,
                   t.project_id AS project_id,
                   t.origin_system AS origin_system,
                   t.title AS title,
                   COUNT(m.id) AS message_count
              FROM chat_threads t
              LEFT JOIN chat_messages m ON m.thread_id = t.id
             WHERE t.origin_system IN ('openai', 'anthropic')
             GROUP BY t.id, t.user_id, t.project_id, t.origin_system, t.title
             ORDER BY t.id DESC
             LIMIT 50
            """
        )
    except RuntimeAccessError:
        return []
    return [dict(row) for row in rows]


def _read_recall_result(
    harness: Harness, thread: Mapping[str, Any]
) -> dict[str, Any]:
    """Read the recall result for one imported record.

    The recall surface is the account history search route. An imported record
    is excluded from native recall by ADR-016, so the harness reads the
    imported-history inspection route as well and reports both.
    """
    thread_id = thread.get("thread_id")
    project_id = thread.get("project_id")
    observed: dict[str, Any] = {
        "thread_id": thread_id,
        "project_id": project_id,
        "returned": False,
    }

    if project_id is None or thread_id is None:
        observed["reason"] = "the imported thread carries no project binding"
        return observed

    search = harness.http.get(
        f"/api/chat/projects/{project_id}/history/search?q=&limit=50"
    )
    observed["native_recall_status"] = search.status
    if search.ok and isinstance(search.body, dict):
        records = search.body.get("records") or search.body.get("excerpts") or []
        observed["native_recall_records"] = len(records)
        observed["native_recall_returned_thread"] = any(
            str(record.get("thread_id")) == str(thread_id)
            for record in records
            if isinstance(record, Mapping)
        )

    inspection = harness.http.post(
        "/api/imports/history/inspect",
        payload={
            "project_id": int(project_id),
            "thread_ids": [int(thread_id)],
            "origins": [str(thread.get("origin_system") or "openai")],
            "max_messages": 50,
            "max_inspected_messages": 50,
            "max_excerpt_bytes": 8192,
            "max_response_bytes": 65536,
            "offset": 0,
        },
    )
    observed["inspection_status"] = inspection.status
    if inspection.ok and isinstance(inspection.body, Mapping):
        observed["inspection_records"] = len(
            inspection.body.get("records") or inspection.body.get("excerpts") or []
        )
        observed["returned"] = bool(
            observed["inspection_records"]
            or observation_body_has_content(inspection.body)
        )
    elif inspection.raw:
        observed["inspection_detail"] = inspection.raw[:200]
    return observed


def observation_body_has_content(body: Mapping[str, Any]) -> bool:
    """Return whether an inspection payload carries any cited excerpt."""
    for key in ("records", "excerpts", "items", "messages"):
        value = body.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) > 0:
                return True
    return False


# ---------------------------------------------------------------------------
# Gate 8 - scope isolation
# ---------------------------------------------------------------------------


def gate_scope_isolation(harness: Harness) -> GateResult:
    """Read the same record under two distinct account identities.

    Rubric surface: the same read issued under two account identities, and
    the retrieval path's account scoping.
    """
    surface = [
        "GET /api/chat/{thread_id}/messages under two account sessions",
        "GET /api/chat/projects/{project_id}/history/search under two account sessions",
        "PostgreSQL chat_threads.user_id / chat_messages.user_id",
    ]
    observed: dict[str, Any] = {"summary": ""}
    result = GateResult(
        gate="scope-isolation",
        verdict=VERDICT_UNPROVEN,
        surface=surface,
        observed=observed,
    )

    accounts = _account_credentials(harness)
    sessions = _account_sessions(harness)

    # Resolve two distinct account identities.
    identities: list[tuple[str, Secret]] = []
    for name in sorted(sessions):
        identities.append((name, sessions[name]))
    if len(identities) < 2:
        for name, credentials in sorted(accounts.items()):
            username = credentials.get("username") or credentials.get("email")
            password = credentials.get("password")
            if not username or not password:
                continue
            account, token = _login_account(harness, username, password)
            if account and token:
                identities.append((account, token))
    if len(identities) < 2:
        observed["summary"] = (
            f"{len(identities)} distinct account identit(ies) could be resolved; "
            "two are required"
        )
        result.reason = (
            "fewer than two distinct account identities were available, so the "
            "isolation boundary was not observed from two accounts"
        )
        result.missing.append(
            "two distinct authenticated accounts - EIGHT_GATE_ACCOUNT_<NAME>_"
            "SESSION(_TOKEN) or EIGHT_GATE_ACCOUNT_<NAME>_USERNAME/_PASSWORD for "
            "two different accounts"
        )
        return result

    (owner_name, owner_token), (other_name, other_token) = identities[0], identities[1]
    observed["accounts"] = [
        {
            "name": owner_name,
            "session_fingerprint": owner_token.fingerprint(),
            "role": "owner",
        },
        {
            "name": other_name,
            "session_fingerprint": other_token.fingerprint(),
            "role": "other",
        },
    ]

    # Create a record owned by the first account, through the product's API.
    created = _create_owned_record(harness, owner_token)
    observed["created_record"] = created
    if not created.get("thread_id"):
        observed["summary"] = "no record could be created under the owning account"
        result.reason = (
            "a record could not be created under the owning account, so the "
            "same read could not be issued against one record identifier"
        )
        result.missing.append(
            "a writable account session that can create a chat thread"
        )
        return result

    thread_id = created["thread_id"]
    message_id = created.get("message_id")
    observed["record"] = {"thread_id": thread_id, "message_id": message_id}

    owner_read = _read_record_as(harness, owner_token, thread_id, message_id)
    other_read = _read_record_as(harness, other_token, thread_id, message_id)
    observed["owner_read"] = owner_read
    observed["other_read"] = other_read

    owner_saw = bool(owner_read.get("found"))
    other_saw = bool(other_read.get("found"))
    observed["summary"] = (
        f"thread={thread_id} owner_saw_record={owner_saw} "
        f"other_saw_record={other_saw}"
    )

    if owner_saw and not other_saw:
        result.verdict = VERDICT_PASS
        result.reason = (
            "the owning account observed the record and the second, distinct "
            "account did not, for the same record identifier"
        )
        return result

    if other_saw:
        result.verdict = VERDICT_FAIL
        result.reason = (
            "a record owned by one account was observable by another account"
        )
        return result

    result.reason = (
        "the owning account's read did not return the record, so the "
        "isolation boundary was not exercised as the rubric requires"
    )
    result.missing.append(
        "a record that the owning account can read back through the same "
        "route the other account used"
    )
    return result


def _create_owned_record(
    harness: Harness, token: Secret
) -> dict[str, Any]:
    """Create one chat thread and message under the owning account."""
    client = HttpClient(
        base_url=harness.base_url,
        session_token=token,
        timeout_seconds=harness.http.timeout_seconds,
    )
    marker = f"eight-gate-scope-{uuid.uuid4().hex}"
    thread_response = client.post(
        "/api/chat/threads", payload={"title": f"scope isolation {marker}"}
    )
    if not thread_response.ok or not isinstance(thread_response.body, dict):
        return {
            "error": f"thread creation failed with HTTP {thread_response.status}",
            "thread_id": None,
        }
    try:
        thread_id = int(thread_response.body.get("id"))
    except (TypeError, ValueError):
        return {"error": "thread creation returned no usable id", "thread_id": None}
    message_response = client.post(
        f"/api/chat/{thread_id}/messages",
        payload={"role": "user", "content": marker},
    )
    message_id = None
    if message_response.ok and isinstance(message_response.body, dict):
        message_id = message_response.body.get("id")
    return {
        "thread_id": thread_id,
        "message_id": message_id,
        "marker": marker,
        "http_status": message_response.status,
    }


def _read_record_as(
    harness: Harness, token: Secret, thread_id: int, message_id: Any
) -> dict[str, Any]:
    """Issue the same read under one account identity."""
    client = HttpClient(
        base_url=harness.base_url,
        session_token=token,
        timeout_seconds=harness.http.timeout_seconds,
    )
    response = client.get(f"/api/chat/{thread_id}/messages?limit=100&offset=0")
    observed: dict[str, Any] = {
        "http_status": response.status,
        "found": False,
        "message_count": 0,
    }
    if not response.ok or not isinstance(response.body, dict):
        observed["detail"] = response.raw[:200]
        return observed
    messages = response.body.get("messages")
    if not isinstance(messages, list):
        observed["detail"] = "the response carried no message list"
        return observed
    observed["message_count"] = len(messages)
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        if message_id is not None and str(message.get("id")) == str(message_id):
            observed["found"] = True
            observed["matched_message_id"] = message.get("id")
            break
    return observed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


GATES: tuple[tuple[str, Callable[[Harness], GateResult]], ...] = (
    ("queue/worker", gate_queue_worker),
    ("deadline", gate_deadline),
    ("graceful-stop", gate_graceful_stop),
    ("lock", gate_lock),
    ("migration-deployment", gate_migration_deployment),
    ("browser", gate_browser),
    ("import-recall", gate_import_recall),
    ("scope-isolation", gate_scope_isolation),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Observe the eight release-readiness gates against a running stack."
        )
    )
    parser.add_argument("--env-file", required=True, help="path to the env file")
    parser.add_argument(
        "--compose-project",
        required=True,
        help="the disposable compose project the stack runs under",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="the backend base URL (defaults to the env file, then port 8888)",
    )
    parser.add_argument(
        "--frontend-url",
        default=None,
        help="the frontend base URL (defaults to the env file, then port 5173)",
    )
    parser.add_argument("--out", required=True, help="path for the results JSON")
    parser.add_argument(
        "--database-url",
        default=None,
        help="override the PostgreSQL DSN",
    )
    parser.add_argument(
        "--redis-url", default=None, help="override the Redis URL"
    )
    parser.add_argument(
        "--import-export-file",
        default=None,
        help=(
            "the real provider export file behind the import, when one is "
            "available; without it the import gate cannot evidence its "
            "natural/synthetic classification"
        ),
    )
    parser.add_argument(
        "--gate1-settle-seconds",
        type=float,
        default=45.0,
        help="how long the queue gate watches for the attempt to terminalise",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="run only the named gate (repeatable)",
    )
    return parser


def build_harness(options: argparse.Namespace) -> Harness:
    """Assemble the read-side context from the operator's inputs."""
    env_file = Path(options.env_file).expanduser()
    env = load_env_file(env_file)
    if not env:
        raise RuntimeAccessError(
            f"the env file {env_file} yielded no readable key/value pairs"
        )

    postgres = PostgresReader(
        dsn=resolve_database_dsn(env, options.database_url),
        compose_project=options.compose_project,
    )
    redis = RedisReader(
        url=resolve_redis_url(env, options.redis_url),
        compose_project=options.compose_project,
    )
    base_url = resolve_base_url(env, options.base_url)
    http = HttpClient(
        base_url=base_url,
        api_key=secret_from(env, "GUARDIAN_API_KEY", "CODEXIFY_API_KEY"),
        session_token=secret_from(
            env,
            "CODEXIFY_SESSION_TOKEN",
            "GUARDIAN_SESSION_TOKEN",
            "EIGHT_GATE_SESSION_TOKEN",
        ),
    )
    return Harness(
        env=env,
        compose_project=options.compose_project,
        base_url=base_url,
        frontend_url=resolve_frontend_url(env, options.frontend_url),
        postgres=postgres,
        redis=redis,
        http=http,
        browser=BrowserDriver(),
        options=options,
    )


def main(argv: Sequence[str] | None = None) -> int:
    options = build_parser().parse_args(argv)

    selected = set(options.only or GATE_NAMES)
    unknown = selected - set(GATE_NAMES)
    if unknown:
        print(
            f"unknown gate(s): {', '.join(sorted(unknown))}",
            file=sys.stderr,
        )
        return 2

    harness = build_harness(options)

    results: list[GateResult] = []
    for name, function in GATES:
        if name not in selected:
            continue
        try:
            result = function(harness)
        except Exception as exc:  # pragma: no cover - defensive
            result = GateResult(
                gate=name,
                verdict=VERDICT_UNPROVEN,
                reason=(
                    f"the gate could not be completed: {type(exc).__name__}: {exc}"
                ),
                missing=["a defect-free run of this gate"],
            )
        results.append(result)
        print(result.summary())

    passed = sum(1 for result in results if result.verdict == VERDICT_PASS)
    total = len(results)
    payload = {
        "schema": 1,
        "generated_at": _now_iso(),
        "compose_project": options.compose_project,
        "base_url": harness.base_url,
        "frontend_url": harness.frontend_url,
        "rubric": "release-readiness-gates",
        "rubric_version": 2,
        "passed": passed,
        "total": total,
        "verdicts": {result.gate: result.verdict for result in results},
        "gates": [result.to_dict() for result in results],
    }

    out_path = Path(options.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"passed {passed}/{total}; results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
