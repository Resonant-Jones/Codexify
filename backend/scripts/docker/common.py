from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


def log(section: str, msg: str) -> None:
    print(f"[{section}] {msg}", flush=True)


def run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    log("docker", f"run: {' '.join(cmd)}")
    return subprocess.run(cmd, env=merged_env, check=check)


def execv(cmd: list[str], env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    exe = cmd[0]
    if not os.path.isabs(exe):
        resolved = shutil.which(exe)
        if resolved:
            exe = resolved
    log("docker", f"exec: {' '.join(cmd)}")
    os.execve(exe, cmd, merged_env)


def wait_for_tcp(
    host: str, port: int, timeout_s: float, sleep_s: float = 1.0
) -> None:
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=3):
                log("wait", f"TCP ready: {host}:{port}")
                return
        except OSError as exc:
            last_err = exc
            time.sleep(sleep_s)
    raise TimeoutError(
        f"TCP endpoint not ready after {timeout_s}s ({host}:{port}): {last_err}"
    )


def _parse_dsn_host_port(dsn: str) -> tuple[str, int]:
    parsed = urlparse(dsn)
    host = parsed.hostname or "db"
    port = parsed.port or 5432
    return host, port


def _connect_psycopg3(dsn: str) -> None:
    import psycopg  # type: ignore

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")


def _connect_psycopg2(dsn: str) -> None:
    import psycopg2  # type: ignore

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        conn.close()


def wait_for_postgres(dsn: str, timeout_s: float) -> None:
    connector = None
    try:
        import psycopg  # noqa: F401

        connector = _connect_psycopg3
    except Exception:
        try:
            import psycopg2  # noqa: F401

            connector = _connect_psycopg2
        except Exception:
            connector = None

    if connector is None:
        host, port = _parse_dsn_host_port(dsn)
        log("wait", "psycopg/psycopg2 unavailable, falling back to TCP wait")
        wait_for_tcp(host, port, timeout_s=timeout_s, sleep_s=1.0)
        return

    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            connector(dsn)
            log("wait", "Postgres is ready")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.0)
    raise TimeoutError(f"Postgres not ready after {timeout_s}s: {last_err}")


def dump_dir_tree(paths: list[str], max_depth: int = 4) -> None:
    for raw_path in paths:
        root = Path(raw_path)
        print(f"[diag] tree {root}")
        if not root.exists():
            print(f"[diag]   <missing>")
            continue
        _dump_one(root, depth=0, max_depth=max_depth)


def _dump_one(path: Path, depth: int, max_depth: int) -> None:
    indent = "  " * depth
    marker = "/" if path.is_dir() else ""
    print(f"[diag] {indent}{path.name}{marker}")

    if depth >= max_depth or not path.is_dir():
        return

    try:
        entries = sorted(path.iterdir(), key=lambda p: p.name)
    except Exception as exc:  # noqa: BLE001
        print(f"[diag] {indent}  <error listing: {exc}>")
        return

    if not entries:
        print(f"[diag] {indent}  <empty>")
        return

    for entry in entries:
        if entry.is_symlink():
            try:
                target = os.readlink(entry)
            except OSError as exc:
                target = f"<unreadable:{exc}>"
            print(f"[diag] {indent}  {entry.name}@ -> {target}")
            continue
        _dump_one(entry, depth + 1, max_depth)


def ensure_symlink(src: str, dst: str) -> None:
    src_path = Path(src)
    dst_path = Path(dst)

    if dst_path.is_symlink() and os.readlink(dst_path) == src:
        return

    if dst_path.exists() or dst_path.is_symlink():
        if dst_path.is_dir() and not dst_path.is_symlink():
            shutil.rmtree(dst_path)
        else:
            dst_path.unlink()

    dst_path.symlink_to(src_path)


def clear_python_caches(root: str) -> tuple[int, int]:
    root_path = Path(root)
    removed_dirs = 0
    removed_files = 0

    if not root_path.exists():
        return removed_dirs, removed_files

    pycache_dirs: Iterable[Path] = sorted(
        [p for p in root_path.rglob("__pycache__") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for d in pycache_dirs:
        shutil.rmtree(d, ignore_errors=True)
        removed_dirs += 1

    for pyc in root_path.rglob("*.pyc"):
        try:
            pyc.unlink()
            removed_files += 1
        except FileNotFoundError:
            continue

    return removed_dirs, removed_files
