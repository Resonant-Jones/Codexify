# guardian/tools/overrides.py
from __future__ import annotations

from typing import Dict

from guardian.tools.spec import ToolPolicy

# Keyed by command_id (best) or tool_id (ok).
POLICY_OVERRIDES_BY_COMMAND_ID: dict[str, ToolPolicy] = {
    # Example: lock down destructive ops
    # "op::documents_delete": ToolPolicy(visibility="admin", side_effects=True, require_identity=True, require_loopback=True)
}

# Optional: tool_id overrides if you prefer
POLICY_OVERRIDES_BY_TOOL_ID: dict[str, ToolPolicy] = {}
