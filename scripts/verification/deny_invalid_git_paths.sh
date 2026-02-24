#!/usr/bin/env bash
# Fail if git tracks pathnames that are unsafe/invalid for this repo policy.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 - <<'PY'
from __future__ import annotations

import subprocess
import sys


def splitz(data: bytes) -> list[bytes]:
    if not data:
        return []
    parts = data.split(b"\0")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return parts


raw = subprocess.check_output(["git", "ls-files", "-z"])
paths = splitz(raw)
bad: list[bytes] = []

for path in paths:
    if path.endswith(b":") or b"\r" in path or b"\t" in path:
        bad.append(path)

if bad:
    print("FAIL: invalid tracked git path(s) detected:")
    for entry in bad:
        print(f"  - {entry.decode('utf-8', 'backslashreplace')}")
    sys.exit(1)

print(f"PASS: {len(paths)} tracked paths validated; no invalid names found.")
PY
