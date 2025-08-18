Codex Task: Verify Log Scrubbing & Server Logging

Objective

Enable log scrubbing, (re)start the Guardian API with file logging, and confirm that sensitive paths in log lines are masked with “(hidden)”.

Environment
 • Project root: guardian-backend_v2
 • Shell: zsh/bash
 • Assumes guardian-api is installed/available.

Do this
 1. Export env vars
 2. Start server on 8888 (if busy, retry on 8889)
 3. Tail last 50 lines of the log and watch for new entries
 4. Confirm scrubbed output appears (token/client_secret/etc. show “(hidden)”)

Commands to run

# 1) Enable scrubbing + file logging

export SCRUB_LOGS=1
export GUARDIAN_LOG_FILE="$PWD/guardian.log"

# 2) Start API on 8888; if the address is in use, retry on 8889

guardian-api --reload --port 8888 || guardian-api --reload --port 8889 &

# 3) Tail and watch logs (new terminal or after the server is backgrounded)

tail -n 50 -f guardian.log

What to look for (acceptance criteria)
 • You see the rotating file message:
 • File logging enabled → /…/guardian.log (max 5 MB, backups 3)
 • Any lines that previously contained credential‑like paths now show masked basenames:
 • Examples that should appear masked:
 • token.json (hidden)
 • client_secret_oauth.json (hidden)
 • token.pickle (hidden)
 • credentials.json (hidden)
 • *.pem (hidden)
 • Sample expected pattern (not exact text):
 • Drive auth: using OAuth token at token.json (hidden) (client at …/client_secret_oauth.json (hidden))

If something fails
 • Address already in use: you should see ERROR: [Errno 48] Address already in use. The fallback command above retries on 8889. If both fail, pick another port (--port 8890).
 • No log file: ensure GUARDIAN_LOG_FILE is set and the directory is writable.
 • Scrubbing not applied: confirm SCRUB_LOGS=1 is exported in the same shell that launches guardian-api.

Deliverables
 • Paste the last 10 lines of guardian.log that show:
 1. The “File logging enabled” line
 2. At least one line where a credential‑like basename is masked with (hidden)

⸻
