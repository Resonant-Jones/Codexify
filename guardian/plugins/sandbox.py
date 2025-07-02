"""Simple plugin sandbox using subprocesses."""

import subprocess
from pathlib import Path
from typing import List
import sys


def run_plugin(path: Path, args: List[str]) -> subprocess.CompletedProcess:
    """Execute a plugin in a subprocess.

    Parameters
    ----------
    path: Path
        Path to the plugin entry point.
    args: List[str]
        Arguments to pass to the plugin.
    """
    command = [sys.executable, str(path)] + args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Plugin failed: {result.stderr}")
    return result
