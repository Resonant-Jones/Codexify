#syntax=docker/dockerfile:1

# === Build stage: Install dependencies and prepare application ===
FROM dhi.io/python:3.11.14-debian13-dev AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /tmp

# Copy requirements and install dependencies
COPY requirements.txt requirements/ backend/requirements.txt* ./

RUN python - <<'PY'
import os, sys, subprocess
candidates = [
    "./backend/requirements.txt",
    "./requirements.txt",
    "./all.txt",
]
req_file = None
for p in candidates:
    if os.path.exists(p):
        req_file = p
        break

if not req_file:
    sys.exit(1)

subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])
subprocess.check_call(['pip', 'install', '-r', req_file])
PY

# Pre-stage scripts and configs for later copy
RUN mkdir -p /app_staging/backend && \
    python - <<'PY'
from pathlib import Path
import stat

# Create wait_for_db script
dst = Path("/app_staging/wait_for_db.py")
dst.write_text("""#!/usr/bin/env python3
import os, time, sys
try:
    import psycopg2
except Exception:
    print('psycopg2 unavailable; skipping active DB wait', file=sys.stderr)
    sys.exit(0)
dsn = os.environ.get('DATABASE_URL')
if not dsn:
    print('DATABASE_URL not set; skipping DB wait', file=sys.stderr)
    sys.exit(0)
for i in range(90):
    try:
        psycopg2.connect(dsn).close()
        print('Postgres is up')
        break
    except Exception as e:
        print('Waiting for Postgres...', e, file=sys.stderr)
        time.sleep(2)
""", encoding="utf-8")
dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

# Create runtime entrypoint script (no shell required in final image)
ep = Path("/app_staging/entrypoint.py")
ep.write_text("""#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def _ensure_symlink():
    # Provide /app/codexify alias for code that imports via `codexify.*`
    target = Path('/app/codexify')
    if target.exists():
        return
    try:
        target.symlink_to('/app/guardian')
    except Exception:
        # If symlinks are unsupported in the runtime, fall back to no-op.
        pass

def _run(cmd, *, check=False):
    try:
        return subprocess.run(cmd, check=check)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127)


def main() -> None:
    _ensure_symlink()

    # Best-effort DB wait
    _run([sys.executable, '/app/wait_for_db.py'])

    # Best-effort migrations
    alembic_cfg = '/app/backend/alembic.ini'
    if os.path.isfile(alembic_cfg):
        _run(['alembic', '-c', alembic_cfg, 'upgrade', 'head'])

    # Exec uvicorn as PID 1
    port = os.environ.get('PORT', '8888')
    argv = [
        sys.executable,
        '-m',
        'uvicorn',
        'codexify.guardian_api:app',
        '--host',
        '0.0.0.0',
        '--port',
        str(port),
    ]
    os.execv(sys.executable, argv)


if __name__ == '__main__':
    main()
""", encoding="utf-8")
ep.chmod(ep.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
PY

# === Optional TTS deps stage: install pinned TTS runtime dependencies ===
FROM builder AS builder-tts

COPY backend/requirements-tts.txt /tmp/backend/requirements-tts.txt
RUN python -m pip install -r /tmp/backend/requirements-tts.txt

# === Final stage: Create minimal runtime image ===
 # NOTE: The non-"-dev" runtime image is intentionally hardened/minimal and does not ship with apt.
 # We use the "-dev" variant here because this stage needs to install ffmpeg via apt-get.
FROM dhi.io/python:3.11.14-debian13-dev AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PORT=8888

WORKDIR /app


# Voice normalization/transcoding dependency (also includes ffprobe).
# ffmpeg pulls packages (e.g., x11-common) whose postinst calls update-rc.d.
# Ensure update-rc.d is present via init-system-helpers.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg init-system-helpers && \
    rm -rf /var/lib/apt/lists/*

# qwen-tts pulls python-sox, which shells out through /bin/sh during import.
# Keep a POSIX shell available in the runtime image for compatibility.

# Copy Python site-packages from builder (minimal and secure)
COPY --from=builder /opt/python/lib/python3.11/site-packages /opt/python/lib/python3.11/site-packages

# Copy application code
COPY guardian /app/guardian
COPY backend /app/backend
COPY plugins /app/plugins
COPY scripts /app/scripts

# Copy pre-staged runtime scripts
COPY --from=builder /app_staging/wait_for_db.py /app/wait_for_db.py
COPY --from=builder /app_staging/entrypoint.py /app/entrypoint.py

# Create symlink alias at runtime (in ENTRYPOINT since no shell in runtime image for RUN)
EXPOSE 8888

ENTRYPOINT ["python", "/app/entrypoint.py"]

# === TTS runtime stage: backend runtime + pinned TTS deps ===
FROM runtime AS tts-runtime

# Copy the site-packages tree with pinned TTS dependency graph.
COPY --from=builder-tts /opt/python/lib/python3.11/site-packages /opt/python/lib/python3.11/site-packages
