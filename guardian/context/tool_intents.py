from __future__ import annotations

import json
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

    def with_id(self, intent_id: str) -> ToolIntent:
        return ToolIntent(
            tool=self.tool,
            args=self.args,
            reason=self.reason,
            intent_id=intent_id,
        )


class ToolIntentParseError(Exception):
    """Raised when model output does not match the tool-intent schema."""


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


def _validate_obj(obj: Any) -> ToolIntent:
    if not isinstance(obj, dict):
        raise ToolIntentParseError("Tool intent must be a JSON object.")

    if obj.get("type") != "tool_intent":
        raise ToolIntentParseError(
            "Missing or invalid 'type' (expected 'tool_intent')."
        )

    tool = obj.get("tool")
    args = obj.get("args")
    reason = obj.get("reason")

    if not isinstance(tool, str) or not tool.strip():
        raise ToolIntentParseError(
            "Missing or invalid 'tool' (expected non-empty string)."
        )
    if not isinstance(args, dict):
        raise ToolIntentParseError(
            "Missing or invalid 'args' (expected object)."
        )
    if reason is not None and not isinstance(reason, str):
        raise ToolIntentParseError("Invalid 'reason' (expected string).")

    return ToolIntent(tool=tool, args=args, reason=reason)


def parse_tool_intents(text: str) -> list[ToolIntent]:
    """Parse tool intents from model output JSON object or array."""
    try:
        payload = json.loads(text)
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

    return [intent.with_id(str(uuid.uuid4())) for intent in intents]
