#!/usr/bin/env bash
set -euo pipefail

echo "[boot] Starting backend entrypoint"
echo "[boot] DATABASE_URL=${DATABASE_URL:-<unset>}"

echo "[boot] Waiting for Postgres with psycopg2 probe..."
python - <<'PY'
import os, sys, time
import psycopg2

dsn = os.environ.get("DATABASE_URL")
if not dsn:
    print("ERROR: DATABASE_URL is not set", flush=True)
    sys.exit(1)

for i in range(90):
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        print("READY", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"waiting for postgres... ({type(e).__name__}: {e})", flush=True)
        time.sleep(2)

print("ERROR: Postgres never became ready", flush=True)
sys.exit(1)
PY

echo "[migrate] Running Alembic migrations"
alembic -c /app/backend/alembic.ini upgrade head || echo "[migrate] No migrations or already up to date"

echo "[run] Launching Uvicorn"
exec uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8000 --reload