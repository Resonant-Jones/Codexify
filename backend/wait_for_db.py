# Ensure wait_for_db.py exists (use repo copy from /app/backend if present)
RUN /bin/sh -lc "if [ -f /app/wait_for_db.py ]; then \
      echo 'wait_for_db.py present'; \
    elif [ -f /app/backend/wait_for_db.py ]; then \
      cp /app/backend/wait_for_db.py /app/wait_for_db.py && chmod +x /app/wait_for_db.py; \
    else \
      printf '%s\n' '#!/usr/bin/env python3' \
                    'import os, time, sys' \
                    'try:' '    import psycopg2' 'except Exception:' '    pass' '' \
                    \"dsn = os.environ.get('DATABASE_URL')\" \
                    \"if not dsn:\" \"    print('DATABASE_URL not set', file=sys.stderr)\" \"    sys.exit(1)\" '' \
                    'for i in range(90):' '    try:' \
                    \"        import psycopg2\" \
                    \"        psycopg2.connect(dsn).close()\" \
                    \"        print('Postgres is up')\" \
                    '        break' '    except Exception as e:' \
                    \"        print('Waiting for Postgres...', e, file=sys.stderr)\" \
                    '        time.sleep(2)' \
                    \"else:\" \"    raise SystemExit('Postgres did not become available')\" \
       > /app/wait_for_db.py && chmod +x /app/wait_for_db.py; \
    fi"