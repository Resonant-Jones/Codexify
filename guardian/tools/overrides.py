# guardian/tools/overrides.py
from __future__ import annotations

from typing import Any

# Keyed by command_id (best) or tool_id.
# Values are partial ToolSpec field patches applied by ToolRegistry.
TOOL_OVERRIDES_BY_COMMAND_ID: dict[str, dict[str, Any]] = {}
TOOL_OVERRIDES_BY_TOOL_ID: dict[str, dict[str, Any]] = {}
