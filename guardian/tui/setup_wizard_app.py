from __future__ import annotations

from pathlib import Path
from typing import Mapping

from guardian.ops.setup_wizard import write_env_file


def write_wizard_env(
    *, repo_root: Path, selections: Mapping[str, str], env_name: str = ".env"
) -> Path:
    """
    Write the setup-wizard .env file using repo-root template seeding.

    The caller provides wizard selections (cloud toggle, keys, connector
    toggles/tokens, etc.) and those values overlay template defaults.
    """
    root = Path(repo_root)
    env_path = root / env_name
    overrides = {k: str(v) for k, v in selections.items()}
    return write_env_file(env_path, overrides, repo_root=root)
