#!/usr/bin/env python3
"""
Compatibility shim for the Guardian CLI.

This wrapper forwards all commands to the canonical Typer app defined in
`guardian/guardian_main.py`. Kept to preserve existing docs and scripts that
invoke `guardian/guardian-main.py`.

We also ensure the repository root (one directory above this file) is on
`sys.path` so that `import guardian...` resolves to the local package in the
repo rather than an installed package named `guardian` in site-packages.
"""

import sys
from pathlib import Path

# Put repository root (one level up from this file) at the front of sys.path.
# When Python runs a script directly, sys.path[0] becomes the directory
# containing that script; that can cause imports like `import guardian` to
# resolve against site-packages instead of this repo. Forcing the repo root
# first avoids that shadowing.
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Now import the canonical Typer app and delegate execution.
from guardian.guardian_main import app as app


if __name__ == "__main__":
    # Run the Typer app when executed directly
    app()
