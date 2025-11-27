"""Codexify subpackage shim.

This package exists to host API server helpers under `guardian.codexify.api_server`.
It re-exports symbols from the sibling module `guardian/codexify.py` so that
imports like `from guardian.codexify import create_notion_database_from_records`
continue to work.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load the sibling module file guardian/codexify.py under a distinct module name
_mod_path = Path(__file__).resolve().parents[1] / "codexify.py"
_spec = importlib.util.spec_from_file_location(
    "guardian._codexify_module", str(_mod_path)
)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _mod
    _spec.loader.exec_module(_mod)
else:
    raise ImportError("Unable to load sibling module codexify.py")

# Re-export selected helpers used by the API server and exporters
create_notion_database_from_records = _mod.create_notion_database_from_records
flatten_notion_blocks = _mod.flatten_notion_blocks
markdown_to_notion_blocks = _mod.markdown_to_notion_blocks
