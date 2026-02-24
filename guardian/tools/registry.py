# guardian/tools/registry.py
from __future__ import annotations

from typing import Dict, List, Optional

from guardian.tools.derive import derive_tools_from_manifest
from guardian.tools.overrides import (
    POLICY_OVERRIDES_BY_COMMAND_ID,
    POLICY_OVERRIDES_BY_TOOL_ID,
)
from guardian.tools.spec import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools_by_id: dict[str, ToolSpec] = {}
        self._tools_by_command_id: dict[str, ToolSpec] = {}

    def load_from_command_manifest(self, manifest: dict) -> None:
        tools = derive_tools_from_manifest(manifest)
        for t in tools:
            # Apply overrides (command_id wins)
            if t.command_id in POLICY_OVERRIDES_BY_COMMAND_ID:
                t.policy = POLICY_OVERRIDES_BY_COMMAND_ID[t.command_id]
            if t.tool_id in POLICY_OVERRIDES_BY_TOOL_ID:
                t.policy = POLICY_OVERRIDES_BY_TOOL_ID[t.tool_id]

            self._tools_by_id[t.tool_id] = t
            self._tools_by_command_id[t.command_id] = t

    def list(self) -> list[ToolSpec]:
        return list(self._tools_by_id.values())

    def get(self, tool_id: str) -> ToolSpec | None:
        return self._tools_by_id.get(tool_id)

    def get_by_command_id(self, command_id: str) -> ToolSpec | None:
        return self._tools_by_command_id.get(command_id)
