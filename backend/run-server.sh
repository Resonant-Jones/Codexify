# Ensure run-server.sh exists (use repo copy from /app/backend if present)
RUN /bin/sh -lc "if [ -f /app/run-server.sh ]; then \
      echo 'run-server.sh present'; \
    elif [ -f /app/backend/run-server.sh ]; then \
      cp /app/backend/run-server.sh /app/run-server.sh && chmod +x /app/run-server.sh; \
    else \
      printf '%s\n' \
        '#!/usr/bin/env bash' \
        'set -euo pipefail' \
        'export PYTHONPATH=${PYTHONPATH:-/app}' \
        '# wait for DB (best-effort)' \
        'python /app/wait_for_db.py || true' \
        '# run migrations (best-effort)' \
        'if command -v alembic >/dev/null 2>&1; then' \
        '  alembic -c /app/backend/alembic.ini upgrade head || true' \
        'fi' \
        '# run uvicorn app' \
        'exec uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8000' \
        > /app/run-server.sh && chmod +x /app/run-server.sh; \
    fi"
