"""Read-only tool-turn observability read-model helper.

Normalizes existing durable evidence from chat_messages.extra_meta,
command_runs, and receipt linkage into a safe operator-facing read model.

Pure function — no DB, no HTTP, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ToolTurnObservabilityReadModel:
    message_id: str | None = None
    request_id: str | None = None
    tool_turn_id: str | None = None
    tool_turn_state: str | None = None
    loop_stop_reason: str | None = None
    command_run_id: str | None = None
    command_id: str | None = None
    command_status: str | None = None
    command_result_summary: str | None = None
    command_error_summary: str | None = None
    command_blocked_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    receipt_ids: tuple[str, ...] = ()
    latest_receipt_id: str | None = None
    evidence_durability: str = "unknown"
    redaction_summary: Mapping[str, Any] = field(default_factory=lambda: {
        "raw_args_rendered": False,
        "secrets_rendered": False,
        "prompts_rendered": False,
        "unredacted_payload_rendered": False,
        "local_surrogate_ids_rendered": False,
    })


_RESULT_SUMMARY_MAX_LENGTH = 240
_ERROR_TEXT_MAX_LENGTH = 500

_SAFE_RESULT_KEYS = ("summary", "result_summary", "message", "status")

_SECRET_MARKERS = (
    "secret", "password", "token", "api_key", "credential",
    "system_prompt", "hidden_prompt", "raw_args",
)


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return str(value).strip() or None


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _contains_secrets(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def _extract_canonical_field(
    meta: Mapping[str, Any] | None,
    camel: str,
    snake: str,
) -> str | None:
    if meta is None:
        return None
    camel_val = meta.get(camel)
    if camel_val is not None and str(camel_val).strip():
        return str(camel_val).strip()
    snake_val = meta.get(snake)
    if snake_val is not None and str(snake_val).strip():
        return str(snake_val).strip()
    return None


def _summarize_result(result_json: Any) -> str | None:
    if result_json is None:
        return None
    if isinstance(result_json, str):
        trimmed = result_json.strip()
        if not trimmed:
            return None
        if len(trimmed) <= _RESULT_SUMMARY_MAX_LENGTH and not _contains_secrets(trimmed):
            return trimmed
        return "Result stored; open CommandRun readback for safe details."
    if isinstance(result_json, Mapping):
        body = result_json.get("body")
        if isinstance(body, Mapping):
            for key in _SAFE_RESULT_KEYS:
                val = body.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()[:240]
            return "Result stored; open CommandRun readback for safe details."
        if isinstance(body, str) and body.strip():
            trimmed = body.strip()
            if len(trimmed) <= _RESULT_SUMMARY_MAX_LENGTH and not _contains_secrets(trimmed):
                return trimmed
        return "Result stored; open CommandRun readback for safe details."
    return "Result stored; open CommandRun readback for safe details."


def _summarize_error(error_text: Any) -> str | None:
    if error_text is None:
        return None
    if not isinstance(error_text, str):
        return None
    trimmed = error_text.strip()
    if not trimmed:
        return None
    if len(trimmed) <= _ERROR_TEXT_MAX_LENGTH and not _contains_secrets(trimmed):
        return trimmed
    return "Command failed; details redacted."


def _read_command_run(
    command_run: Any,
) -> dict[str, Any]:
    """Read command_run fields from either a mapping or an ORM-like object."""
    result: dict[str, Any] = {}
    if isinstance(command_run, Mapping):
        result["run_id"] = _safe_str(command_run.get("run_id"))
        result["command_id"] = _safe_str(command_run.get("command_id"))
        result["status"] = _safe_str(command_run.get("status"))
        result["result_json"] = command_run.get("result_json")
        result["error_text"] = _safe_str(command_run.get("error_text"))
        result["created_at"] = _safe_str(command_run.get("created_at"))
        result["updated_at"] = _safe_str(command_run.get("updated_at") or command_run.get("ended_at"))
    else:
        result["run_id"] = _safe_str(getattr(command_run, "run_id", None))
        result["command_id"] = _safe_str(getattr(command_run, "command_id", None))
        result["status"] = _safe_str(getattr(command_run, "status", None))
        result["result_json"] = getattr(command_run, "result_json", None)
        result["error_text"] = _safe_str(getattr(command_run, "error_text", None))
        result["created_at"] = _safe_str(getattr(command_run, "created_at", None))
        result["updated_at"] = _safe_str(
            getattr(command_run, "updated_at", None) or getattr(command_run, "ended_at", None)
        )
    return result


def build_tool_turn_observability_read_model(
    *,
    assistant_extra_meta: Mapping[str, Any] | None,
    command_run: Any | Mapping[str, Any] | None = None,
    receipt_ids: Sequence[str] | None = None,
    latest_receipt_id: str | None = None,
) -> ToolTurnObservabilityReadModel:
    """Build a safe operator-facing tool-turn observability read model.

    Args:
        assistant_extra_meta: The `extra_meta` dict from a chat message.
        command_run: A CommandRun record (mapping or ORM object).
        receipt_ids: Linked receipt IDs.
        latest_receipt_id: The latest receipt ID from a work order.

    Returns:
        A read-only ToolTurnObservabilityReadModel.
    """
    # ── Extract canonical fields from extra_meta ──────────────────
    message_id = _extract_canonical_field(assistant_extra_meta, "messageId", "message_id")
    request_id = _extract_canonical_field(assistant_extra_meta, "requestId", "request_id")
    tool_turn_id = _extract_canonical_field(assistant_extra_meta, "toolTurnId", "tool_turn_id")
    tool_turn_state = _extract_canonical_field(assistant_extra_meta, "toolTurnState", "tool_turn_state")
    loop_stop_reason = _extract_canonical_field(assistant_extra_meta, "loopStopReason", "loop_stop_reason")
    meta_command_run_id = _extract_canonical_field(assistant_extra_meta, "commandRunId", "command_run_id")

    # ── Enrich from CommandRun ────────────────────────────────────
    cr_data = _read_command_run(command_run) if command_run is not None else {}
    command_id = cr_data.get("command_id")
    command_status = cr_data.get("status")
    command_result_summary = _summarize_result(cr_data.get("result_json"))
    command_error_summary = _summarize_error(cr_data.get("error_text"))
    run_created_at = cr_data.get("created_at")
    run_updated_at = cr_data.get("updated_at")

    # commandRunId: prefer extra_meta value, fall back to CommandRun run_id
    resolved_command_run_id = meta_command_run_id or cr_data.get("run_id")

    # ── Blocked reason ────────────────────────────────────────────
    command_blocked_reason: str | None = None
    if command_status == "blocked":
        command_blocked_reason = "Command execution was blocked by policy or validation."

    # ── Receipt evidence ──────────────────────────────────────────
    resolved_receipt_ids = tuple(receipt_ids) if receipt_ids else ()
    resolved_latest_receipt_id = _safe_str(latest_receipt_id)

    # ── Evidence durability ───────────────────────────────────────
    has_meta = assistant_extra_meta is not None and bool(assistant_extra_meta)
    has_cr = bool(cr_data)
    has_receipts = bool(resolved_receipt_ids) or resolved_latest_receipt_id is not None

    if has_receipts and (has_meta or has_cr):
        durability = "receipt_enriched"
    elif has_meta or has_cr:
        durability = "durable"
    else:
        durability = "unknown"

    return ToolTurnObservabilityReadModel(
        message_id=message_id,
        request_id=request_id,
        tool_turn_id=tool_turn_id,
        tool_turn_state=tool_turn_state,
        loop_stop_reason=loop_stop_reason,
        command_run_id=resolved_command_run_id,
        command_id=command_id,
        command_status=command_status,
        command_result_summary=command_result_summary,
        command_error_summary=command_error_summary,
        command_blocked_reason=command_blocked_reason,
        created_at=run_created_at,
        updated_at=run_updated_at,
        receipt_ids=resolved_receipt_ids,
        latest_receipt_id=resolved_latest_receipt_id,
        evidence_durability=durability,
    )
