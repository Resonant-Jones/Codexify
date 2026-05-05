#!/usr/bin/env python3
"""Release-evidence harness for the supported local Compose path.

This script proves that an Obsidian-backed local note, indexed through the
supported Obsidian control plane, can influence a real Guardian completion on
the supported local Compose path. It does not widen the release promise to
packaged desktop, webUI-only, or other install modes.
"""

from __future__ import annotations

import json
import os
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
    "completion",
    "retrieval_evidence",
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
    token = f"workspace-seal-mariner-signal-lattice-{phrase_suffix}"
    note_title = f"Workspace Proof Sentinel {token[-8:]}"
    note_filename = "workspace-proof-sentinel.md"
    question = (
        "From my workspace notes, what is the exact workspace proof phrase? "
        "Reply with only the phrase."
    )
    note_text = (
        "---\n"
        f"title: {note_title}\n"
        "tags:\n"
        "  - obsidian\n"
        "  - workspace\n"
        "  - proof\n"
        "---\n"
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
    terminal_event_type: str | None,
    assistant_text: str | None,
    retrieval_status: str | None,
    obsidian_semantic_hits: int,
    retrieval_source_mode: str | None,
    retrieval_posture: dict[str, Any] | None,
    token: str,
) -> dict[str, dict[str, Any]]:
    """Classify the proof into the operator-facing verdict categories."""

    acceptance_ok = str(acceptance_status or "").strip() in ACCEPTED_STATUSES
    completion_ok = terminal_event_type == "task.completed"
    assistant_ok = bool(assistant_text and token in assistant_text)
    retrieval_ok = (
        str(retrieval_source_mode or "").strip() == WORKSPACE_SOURCE_MODE
        and str(retrieval_status or "").strip() == WORKSPACE_RETRIEVAL_STATUS
        and obsidian_semantic_hits > 0
    )
    if retrieval_posture:
        retrieval_ok = retrieval_ok and (
            retrieval_posture.get("source_mode") == WORKSPACE_SOURCE_MODE
            and retrieval_posture.get("boundary_label") == "same_user_only"
            and retrieval_posture.get("widen_reason") == "explicit_workspace"
        )

    verdicts: dict[str, dict[str, Any]] = {
        "acceptance": {
            "status": acceptance_status or "missing",
            "passed": acceptance_ok,
        },
        "completion": {
            "status": terminal_event_type or "missing",
            "passed": completion_ok,
        },
        "retrieval_evidence": {
            "status": retrieval_status or "missing",
            "passed": retrieval_ok,
            "source_mode": retrieval_source_mode,
            "obsidian_semantic_hits": obsidian_semantic_hits,
            "retrieval_posture": retrieval_posture,
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


def _health_retrieval_probe(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    token: str,
) -> dict[str, Any] | None:
    try:
        probe = _request_json(
            session,
            "GET",
            f"{base_url}/api/health/retrieval",
            headers=headers,
            params={"q": token, "k": 10},
            timeout=30.0,
        )
    except (ProofFailure, requests.Timeout):
        return None
    matches = probe.get("search", {}).get("matches")
    if not isinstance(matches, list) or not matches:
        return None
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
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    retrieval_posture: dict[str, Any] | None = None
    retrieval_provenance: dict[str, Any] | None = None
    trace: dict[str, Any] | None = None

    if isinstance(task_completed_payload, dict):
        retrieval_posture = task_completed_payload.get("retrieval_posture")
        if not isinstance(retrieval_posture, dict):
            payload_summary = task_completed_payload.get("payload_summary")
            if isinstance(payload_summary, dict):
                maybe_posture = payload_summary.get("retrieval_posture")
                if isinstance(maybe_posture, dict):
                    retrieval_posture = maybe_posture
        retrieval_provenance = task_completed_payload.get(
            "retrieval_provenance"
        )
        if not isinstance(retrieval_provenance, dict):
            payload_summary = task_completed_payload.get("payload_summary")
            if isinstance(payload_summary, dict):
                maybe_provenance = payload_summary.get("retrieval_provenance")
                if isinstance(maybe_provenance, dict):
                    retrieval_provenance = maybe_provenance
        trace = task_completed_payload.get("trace")
        if not isinstance(trace, dict):
            trace = None

    if retrieval_posture is None:
        try:
            posture_response = _request_json(
                session,
                "GET",
                f"{base_url}/api/chat/debug/retrieval-posture/{thread_id}/latest",
                headers=headers,
                timeout=10.0,
            )
            maybe_posture = posture_response.get("retrieval_posture")
            if isinstance(maybe_posture, dict):
                retrieval_posture = maybe_posture
        except ProofFailure:
            pass

    if retrieval_provenance is None or trace is None:
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
                maybe_provenance = trace_response.get("retrieval_provenance")
                if isinstance(maybe_provenance, dict):
                    retrieval_provenance = maybe_provenance
                payload_summary = trace_response.get("payload_summary")
                if isinstance(payload_summary, dict):
                    maybe_payload_provenance = payload_summary.get(
                        "retrieval_provenance"
                    )
                    if isinstance(maybe_payload_provenance, dict):
                        retrieval_provenance = maybe_payload_provenance
        except ProofFailure:
            pass
    return retrieval_posture, retrieval_provenance, trace


def _format_summary(
    *,
    base_url: str,
    thread_id: int,
    task_id: str,
    assistant_text: str,
    task_completed_payload: dict[str, Any] | None,
    verdicts: dict[str, dict[str, Any]],
    retrieval_posture: dict[str, Any] | None,
    retrieval_provenance: dict[str, Any] | None,
) -> str:
    acceptance = verdicts["acceptance"]
    completion = verdicts["completion"]
    retrieval = verdicts["retrieval_evidence"]
    assistant_match = verdicts["assistant_match"]
    final_verdict = verdicts["final_verdict"]
    obsidian_hits = retrieval.get("obsidian_semantic_hits", 0)
    provenance_status = (
        retrieval_provenance.get("retrieval_status")
        if isinstance(retrieval_provenance, dict)
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
    provenance_summary = ""
    if isinstance(task_completed_payload, dict):
        payload_summary = task_completed_payload.get("payload_summary")
        if isinstance(payload_summary, dict):
            provenance_summary = json.dumps(
                payload_summary.get("retrieval_provenance"), sort_keys=True
            )
    return "\n".join(
        [
            f"ACCEPTANCE: {acceptance['status']} | passed={str(acceptance['passed']).lower()} | task_id={task_id} | thread_id={thread_id} | source_mode={WORKSPACE_SOURCE_MODE}",
            f"COMPLETION: {completion['status']} | passed={str(completion['passed']).lower()} | assistant_match={str(assistant_match['passed']).lower()} | assistant_message={assistant_text!r}",
            f"RETRIEVAL: {retrieval.get('status') or provenance_status or 'missing'} | passed={str(retrieval['passed']).lower()} | obsidian_semantic_hits={obsidian_hits} | posture_source_mode={posture_source_mode} | widen_reason={posture_reason}",
            f"TRACE: {provenance_summary or json.dumps(retrieval_provenance, sort_keys=True) if retrieval_provenance else 'missing'}",
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
    try:
        _copy_workspace_vault_to_container(
            scratch_root, CONTAINER_PROOF_ROOT / scratch_root.name
        )
        _check_runtime_health(session, base_url, headers)
        previous_obsidian_config = _configure_obsidian_vault(
            session, base_url, headers, container_vault_root
        )
        _index_obsidian_vault(session, base_url, headers)
        _health_retrieval_probe(session, base_url, headers, sentinel.token)

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

        payload_summary = task_completed_payload.get("payload_summary")
        if not isinstance(payload_summary, dict):
            _fail(
                "task.completed did not include a payload_summary with retrieval evidence"
            )
        retrieval_provenance = payload_summary.get("retrieval_provenance")
        if not isinstance(retrieval_provenance, dict):
            retrieval_provenance = None
        (
            retrieval_posture,
            debug_provenance,
            trace,
        ) = _latest_retrieval_artifacts(
            session,
            base_url,
            headers,
            thread_id,
            task_completed_payload,
        )
        if retrieval_provenance is None:
            retrieval_provenance = debug_provenance
        if retrieval_provenance is None:
            _fail(
                "Could not obtain retrieval provenance from task events or debug trace "
                f"(thread_id={thread_id}, task_id={task_id}, "
                f"task_completed_keys={sorted(task_completed_payload.keys())})"
            )
        if retrieval_posture is None:
            _fail(
                "Could not obtain retrieval posture evidence from the live path "
                f"(thread_id={thread_id}, task_id={task_id}, "
                f"task_completed_keys={sorted(task_completed_payload.keys())})"
            )
        if sentinel.token not in assistant_text:
            _fail(
                "Assistant response did not contain the workspace sentinel token: "
                f"{assistant_text!r} (thread_id={thread_id}, task_id={task_id}, "
                f"retrieval_provenance={retrieval_provenance!r}, "
                f"retrieval_posture={retrieval_posture!r})"
            )
        if (
            retrieval_provenance.get("retrieval_status")
            != WORKSPACE_RETRIEVAL_STATUS
        ):
            _fail(
                "Workspace retrieval did not participate in the live completion: "
                f"{retrieval_provenance!r}"
            )
        source_hit_counts = retrieval_provenance.get("source_hit_counts")
        obsidian_semantic_hits = 0
        if isinstance(source_hit_counts, dict):
            obsidian_semantic_hits = int(
                source_hit_counts.get("obsidian_semantic") or 0
            )
        verdicts = classify_proof_verdicts(
            acceptance_status=str(
                completion_payload.get("acceptance_status") or ""
            ).strip(),
            terminal_event_type=terminal_event_type,
            assistant_text=assistant_text,
            retrieval_status=str(
                retrieval_provenance.get("retrieval_status") or ""
            ).strip(),
            obsidian_semantic_hits=obsidian_semantic_hits,
            retrieval_source_mode=str(
                retrieval_posture.get("source_mode") or ""
            ).strip(),
            retrieval_posture=retrieval_posture,
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
            retrieval_provenance=retrieval_provenance,
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
