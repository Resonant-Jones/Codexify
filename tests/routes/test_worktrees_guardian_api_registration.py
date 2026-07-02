"""Static checks for Guardian worktree route registration boundaries."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_worktree_routes_are_explicitly_opt_in() -> None:
    """The operator worktree router must stay dormant unless its flag is true."""
    source = (ROOT / "guardian" / "guardian_api.py").read_text()
    module = ast.parse(source)

    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "_include_router"):
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        label = keywords.get("label")
        if isinstance(label, ast.Constant) and label.value == "worktrees":
            default_enabled = keywords.get("default_enabled")
            assert isinstance(default_enabled, ast.Constant)
            assert default_enabled.value is False
            return

    raise AssertionError("worktrees _include_router registration not found")
