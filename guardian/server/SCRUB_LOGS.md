Guardian Log Scrubbing

The Guardian backend includes a log‑scrubbing system to prevent sensitive file paths (OAuth tokens, private keys, credential files) from appearing in console or file logs.

How it works
 • All logs pass through ScrubFormatter (in guardian/server/app.py).
 • Sensitive basenames are detected via patterns (e.g., token.json, client_secret*.json,*.pem) and replaced with:  (hidden).
 • Scrubbing covers both console and rotating file logs.
 • It’s toggleable via env vars and accepts extra patterns at runtime.

Environment variables

Variable Default Description
GUARDIAN_SCRUB_LOGS 1 Toggle scrubbing (1/true/yes/on = enabled, 0/false/no/off = disabled).
GUARDIAN_SCRUB_EXTRA_EXTS (empty) Extra file extensions to scrub (comma‑sep, case‑insensitive), e.g. bak,tmp,log.
GUARDIAN_SCRUB_EXTRA_NAMES (empty) Exact basenames to scrub (comma‑sep, case‑sensitive), e.g. mysecret.txt,hidden.key.
GUARDIAN_LOG_FILE (unset) If set, logs also write to this path with rotation.
GUARDIAN_LOG_LEVEL INFO Logging level (DEBUG, INFO, WARNING, ERROR).

Built‑in patterns
 • client_secret*.json
 • credentials.json
 • token, token.json, token.pickle, token.any
 • Private keys:*.pem, *.p12,*.pfx

Quick test (one‑liner)

python - <<'PY'
import logging
from guardian.server.app import ScrubFormatter

tests = [
  "/very/secret/path/token.json",
  r"C:\Users\me\Downloads\token.pickle",
  "/x/y/client_secret_oauth.json",
  "/keys/my.pem",
  "/weird.dir/name/credentials.json",
]

h = logging.StreamHandler()
h.setFormatter(ScrubFormatter('%(message)s'))
lg = logging.getLogger('scrub-test'); lg.setLevel(logging.INFO); lg.addHandler(h)
lg.info(" | ".join(tests))
PY

Expected output (scrubbing ON):

token.json (hidden) | token.pickle (hidden) | client_secret_oauth.json (hidden) | my.pem (hidden) | credentials.json (hidden)

Toggle scrubbing

# Disable (for troubleshooting)

export GUARDIAN_SCRUB_LOGS=0

# Enable (default)

export GUARDIAN_SCRUB_LOGS=1

Health check

The health endpoint reports scrubbing status:

curl -s <http://127.0.0.1:8888/healthz> | jq

Example:

{
  "ok": true,
  "codexify": {
    "auth_mode": "oauth_ready",
    "default_folder_set": true,
    "share_anyone_default": false,
    "scrub_logs": true
  }
}

Extend patterns without code

# Add more extensions

export GUARDIAN_SCRUB_EXTRA_EXTS="bak,tmp,log"

# Add specific filenames

export GUARDIAN_SCRUB_EXTRA_NAMES="notes.txt,unsafe.key"

Notes
 • Scrubbing never throws—logging continues even if a pattern fails.
 • Applies to both file and console logs.
 • The formatter collapses repeated  (hidden) markers to a single  (hidden).

⸻

Optional: Makefile helper target

If you want a quick test target, add this to your Makefile:

.PHONY: scrub-test
scrub-test:
 @python - <<'PY'
import logging
from guardian.server.app import ScrubFormatter
tests = [
  "/very/secret/path/token.json",
  r"C:\\Users\\me\\Downloads\\token.pickle",
  "/x/y/client_secret_oauth.json",
  "/keys/my.pem",
  "/weird.dir/name/credentials.json",
]
h = logging.StreamHandler()
h.setFormatter(ScrubFormatter('%(message)s'))
lg = logging.getLogger('scrub-test'); lg.setLevel(logging.INFO); lg.addHandler(h)
lg.info(" | ".join(tests))
PY

Run with:

make scrub-test
