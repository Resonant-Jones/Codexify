from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ToolRisk(str, Enum):
    SAFE_READONLY = "safe_readonly"
    SENSITIVE = "sensitive"
    DISALLOWED = "disallowed"


@dataclass(frozen=True)
class ToolPolicy:
    tool: str
    risk: ToolRisk
    description: str

    @property
    def requires_consent(self) -> bool:
        return self.risk in {ToolRisk.SENSITIVE, ToolRisk.DISALLOWED}


@dataclass(frozen=True)
class ToolIntent:
    tool: str
    args: dict[str, Any]
    reason: str | None = None
    # Stable ID assigned by Guardian for consent/workflow tracking
    intent_id: str = ""


class ToolIntentParseError(Exception):
    """Raised when model output does not match the tool-intent schema."""


_FENCED_BLOCK_RE = re.compile(
    r"^\s*```(?:json)?\s*\r?\n(?P<body>.*?)(?:\r?\n)?```\s*$",
    re.DOTALL | re.IGNORECASE,
)

MAX_TOOL_INTENTS_PER_MESSAGE = 20
MAX_TOOL_INTENT_REASON_CHARS = 4096
MAX_TOOL_INTENT_ARGS_JSON_BYTES = 65536  # 64 KiB

REDACTED_VALUE = "[REDACTED]"

_REDACT_KEYS_EXACT = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "auth",
    "bearer",
    "secret",
    "client_secret",
    "password",
    "passphrase",
}

_REDACT_KEYS_CONTAINS = {
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
}


DEFAULT_TOOL_POLICIES: dict[str, ToolPolicy] = {
    "fs.search": ToolPolicy(
        tool="fs.search",
        risk=ToolRisk.SAFE_READONLY,
        description=(
            "Search for file paths/metadata using globs and simple text "
            "queries."
        ),
    ),
    "fs.read_file": ToolPolicy(
        tool="fs.read_file",
        risk=ToolRisk.SENSITIVE,
        description=(
            "Read file contents; may expose secrets or sensitive user data."
        ),
    ),
    "secrets.get": ToolPolicy(
        tool="secrets.get",
        risk=ToolRisk.SENSITIVE,
        description=(
            "Fetch a secret from a secret store / password manager "
            "integration."
        ),
    ),
}


def classify_tool_intent(intent: ToolIntent) -> ToolPolicy:
    """Classify a tool intent according to explicit policy (fail closed)."""
    return DEFAULT_TOOL_POLICIES.get(
        intent.tool,
        ToolPolicy(
            tool=intent.tool,
            risk=ToolRisk.SENSITIVE,
            description="Unknown tool; consent required by default.",
        ),
    )


def _should_redact_key(key: str) -> bool:
    k = (key or "").strip().lower()
    if not k:
        return False
    if k in _REDACT_KEYS_EXACT:
        return True
    return any(sub in k for sub in _REDACT_KEYS_CONTAINS)


def redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if _should_redact_key(str(k)):
                out[k] = REDACTED_VALUE
            else:
                out[k] = redact_json(v)
        return out
    if isinstance(value, list):
        return [redact_json(v) for v in value]
    # Scalars unchanged
    return value


def redact_tool_intent_dict(intent: dict[str, Any]) -> dict[str, Any]:
    # Shallow copy; v1 redacts args only.
    out = dict(intent)
    if isinstance(out.get("args"), (dict, list)):
        out["args"] = redact_json(out["args"])
    return out


def _validate_obj(obj: Any) -> ToolIntent:
    if not isinstance(obj, dict):
        raise ToolIntentParseError("Tool intent must be a JSON object.")

    required = {"id", "tool", "args", "reason"}
    missing = required - set(obj.keys())
    if missing:
        raise ToolIntentParseError(f"missing_keys:{','.join(sorted(missing))}")

    intent_id = obj["id"]
    tool = obj["tool"]
    args = obj["args"]
    reason = obj["reason"]

    if not isinstance(intent_id, str):
        raise ToolIntentParseError("Invalid 'id' (expected UUID string).")
    try:
        uuid.UUID(intent_id)
    except ValueError as exc:
        raise ToolIntentParseError(
            "Invalid 'id' (expected UUID string)."
        ) from exc
    if not isinstance(tool, str) or not tool.strip():
        raise ToolIntentParseError(
            "Missing or invalid 'tool' (expected non-empty string)."
        )
    if not isinstance(args, dict):
        raise ToolIntentParseError(
            "Missing or invalid 'args' (expected object)."
        )
    args_bytes = len(
        json.dumps(args, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    if args_bytes > MAX_TOOL_INTENT_ARGS_JSON_BYTES:
        raise ToolIntentParseError("tool_intents_args_too_large")
    if not isinstance(reason, str):
        raise ToolIntentParseError("Invalid 'reason' (expected string).")
    if len(reason) > MAX_TOOL_INTENT_REASON_CHARS:
        raise ToolIntentParseError("tool_intents_reason_too_long")

    # Ignore extra keys for forward compatibility.
    return ToolIntent(
        tool=tool,
        args=args,
        reason=reason,
        intent_id=intent_id,
    )


def _unwrap_json_maybe_fenced(text: str) -> str:
    """
    Accept either:
      - pure JSON text
      - a single fenced block containing JSON (```json ...``` or ``` ... ```)
    Reject if JSON is mixed with prose outside the fenced block.
    """
    s = (text or "").strip()
    if not s:
        raise ToolIntentParseError("empty_tool_intents")

    if s[0] in "{[":
        return s

    m = _FENCED_BLOCK_RE.match(s)
    if m:
        return m.group("body").strip()

    # Not pure JSON and not a single fenced JSON block
    raise ToolIntentParseError("tool_intents_not_json")


def parse_tool_intents(text: str) -> list[ToolIntent]:
    """Parse tool intents from model output JSON object or array."""
    try:
        raw = _unwrap_json_maybe_fenced(text)
        payload = json.loads(raw)
    except ToolIntentParseError:
        raise
    except Exception as exc:  # pragma: no cover - branch covered via raises
        raise ToolIntentParseError(
            f"Invalid JSON for tool intent: {exc}"
        ) from exc

    intents: list[ToolIntent] = []
    if isinstance(payload, dict):
        intents.append(_validate_obj(payload))
    elif isinstance(payload, list):
        if not payload:
            raise ToolIntentParseError("Tool intent array must not be empty.")
        for item in payload:
            intents.append(_validate_obj(item))
    else:
        raise ToolIntentParseError(
            "Tool intents must be a JSON object or array of objects."
        )

    if len(intents) > MAX_TOOL_INTENTS_PER_MESSAGE:
        raise ToolIntentParseError("tool_intents_too_many")

    return intents
