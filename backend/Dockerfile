FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for typical Python builds (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps (support multiple repo layouts)
# Copy potential requirement sources into the image
COPY backend /app/backend
COPY requirements /app/requirements
COPY requirements.txt /app/requirements.txt

# Choose the first existing requirements file and install
RUN python - <<'PY'
import os, sys, subprocess
candidates = [
    "/app/backend/requirements.txt",        # monorepo backend specific
    "/app/requirements.txt",                # root requirements
    "/app/requirements/all.txt",            # compiled lock
]
for p in candidates:
    if os.path.exists(p):
        sys.stderr.write(f"[deps] Using {p}\n")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])
        subprocess.check_call(['pip', 'install', '-r', p])
        break
else:
    sys.stderr.write("[deps] No requirements file found in candidates.\n")
    sys.exit(1)
PY

# Make both import paths available inside the container:
# - Keep the original package name `guardian`
# - Provide `codexify` as an alias so `uvicorn codexify.guardian_api:app` works
COPY guardian /app/guardian
RUN ln -s /app/guardian /app/codexify

# Ensure alembic.ini exists in /app/backend (or write a tiny default) and normalize newlines
RUN python - <<'PY'
from pathlib import Path
p = Path("/app/backend/alembic.ini")
if not p.exists():
    p.write_text("[alembic]\nscript_location = backend/migrations\n", encoding="utf-8")
raw = p.read_bytes()
if raw.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
    raw = raw[3:]
raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
p.write_bytes(raw)
PY

# Create / normalize the DB wait script (always synthesize)
RUN python - <<'PY'
from pathlib import Path
import stat

dst = Path("/app/wait_for_db.py")
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
        print('Postgres is up'); break
    except Exception as e:
        print('Waiting for Postgres...', e, file=sys.stderr)
        time.sleep(2)
""", encoding="utf-8")
raw = dst.read_bytes()
if raw.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
    raw = raw[3:]
raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
dst.write_bytes(raw)
dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
PY

# Create / normalize the launcher script (always synthesize a clean script in the image)
RUN python - <<'PY'
from pathlib import Path
import stat

dst = Path("/app/run-server.sh")
dst.write_text("""#!/bin/sh
set -eu
export PYTHONPATH=${PYTHONPATH:-/app}
PORT=${PORT:-8000}

# best-effort DB wait
python /app/wait_for_db.py || true

# best-effort migrations (honor script_location in alembic.ini)
if command -v alembic >/dev/null 2>&1 && [ -f /app/backend/alembic.ini ]; then
  alembic -c /app/backend/alembic.ini upgrade head || true
else
  echo "[migrate] Skipping Alembic (no alembic.ini)"
fi

# launch API
exec uvicorn codexify.guardian_api:app --host 0.0.0.0 --port "${PORT}"
""", encoding="utf-8")
raw = dst.read_bytes()
if raw.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
    raw = raw[3:]
raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
dst.write_bytes(raw)
dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
PY

ENV PYTHONPATH=/app
EXPOSE 8000
ENTRYPOINT ["/app/run-server.sh"]
