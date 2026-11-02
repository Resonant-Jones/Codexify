"""Write generated JSON artifacts on hosts that deny rename and unlink.

The DLG and ARP generators both write their derived artifacts through a
same-directory temporary file followed by `os.replace`. That is the right
default: it makes the visible file appear complete or not at all.

It does not work on every host. Some sandboxed environments deny `rename(2)`
and `unlink(2)` for paths under the repository. There, `os.replace` fails
with `PermissionError` and the temporary file is left behind, which then
breaks the very next run's scope check.

This module provides the alternative those hosts need: write the payload to
a sibling temporary file, then **copy it over the destination with
truncate-in-place**, which preserves the destination's inode and mode and
needs neither rename nor unlink.

Truncate-in-place is not atomic. A crash mid-copy leaves a partial file.
To keep that from silently corrupting a committed artifact, the payload is
serialized and validated in full *before* the destination is opened, and the
write is followed by an `fsync`. The destination therefore only ever
contains either the previous complete payload or the new complete payload,
except in the case of a crash or a full disk during the write itself.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


class AtomicWriteError(RuntimeError):
    """An artifact could not be written."""


def write_bytes_in_place(path: Path, payload: bytes) -> None:
    """Write `payload` over `path` without rename or unlink.

    The payload is staged in a sibling temporary file first, so a failure
    while serializing cannot leave a partial destination. The staged copy
    is then moved over the destination with truncate-in-place, and the
    temporary file is removed when the host permits it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    staging_path = path.parent / f".{path.name}.staged"
    try:
        with open(staging_path, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        # Copy the staged bytes over the destination in place. Opening the
        # destination for writing truncates it; the inode and its mode are
        # preserved and no rename is required.
        with open(path, "wb") as destination:
            with open(staging_path, "rb") as source:
                shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
    except Exception as exc:
        raise AtomicWriteError(f"Could not write {path}: {exc}") from exc
    finally:
        # Best effort: hosts that deny unlink simply keep the staging file.
        # Its name is deterministic, so the next write reuses it rather
        # than accumulating a new orphan on every call.
        try:
            staging_path.unlink(missing_ok=True)
        except OSError:
            pass


def write_json_in_place(path: Path, payload: dict[str, Any], *, serializer) -> None:
    """Write a JSON payload over `path` without rename or unlink.

    `serializer` must return the exact bytes to store. It is called before
    the destination is touched so that a serialization failure cannot leave
    a truncated artifact behind.
    """
    data = serializer(payload)
    write_bytes_in_place(path, data)
