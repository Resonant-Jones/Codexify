# CHUNK_CAMPAIGN_2026_02_17 — Incident Response + Secret Broker Foundations

## Campaign Storage Layout (Required)

- **Campaign index (this file):**
  - `docs/Campaigns/CHUNK_CAMPAIGN_2026_02_17/CHUNK_CAMPAIGN_2026_02_17_CHUNKPAIGN.md`

- **Individual task files (one task per file):**
  - Directory: `docs/tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/`
  - Naming convention: `TASK-<CODE>-<NNN>__<slug>.md`
    - Examples:
      - `TASK-IR-000__incident-response-tooling.md`
      - `TASK-BROKER-000__secret-broker-env.md`
      - `TASK-CAP-001__capability-enforcement-vector.md`

### Execution rule
Codex should **create each TASK as its own markdown file** under `docs/tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/` and keep this document as the **index** that links to those task files.

---

Absolutely 😄🔐 — here’s a Chunk 0 + Chunk 2 campaign written in your Codexify Task Template, broken into atomic, testable, individually-committed tasks.

Codex should **create the individual task files** under `docs/tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/` (one task per file) and keep this document as the **campaign index**.

If a connector is not active, the task files should still be written as manual execution blocks, but they must be placed in the directory above.
(Each task names exact files/paths and includes commands + commit steps.)

⸻

CAMPAIGN — Incident Response + Secret Broker Foundations

## Task Index

- [TASK-IR-000 — Add repo-local “incident response” tooling + documentation](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-IR-000__incident-response-tooling.md)
- [TASK-IR-001 — Expand pre-commit secret detection (beyond private keys)](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-IR-001__precommit-secret-scanning.md)
- [TASK-IR-002 — Add “toxic secret paths” guardrails (ignore + denylist)](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-IR-002__forbidden-paths-guardrails.md)
- [TASK-IR-003 — Add a runtime startup “fail closed” guard for missing secret broker backing](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-IR-003__require-secret-store-flag.md)
- [TASK-BROKER-000 — Introduce Secret Broker interface + env-backed implementation](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-BROKER-000__secret-broker-env.md)
- [TASK-BROKER-001 — Add macOS Keychain broker (best-effort, optional dependency)](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-BROKER-001__secret-broker-keychain.md)
- [TASK-CAP-000 — Add capability grant model (TTL + scope + max_calls)](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-CAP-000__capability-grant-model.md)
- [TASK-CAP-001 — Enforce capability checks in one high-risk surface (vector write/read)](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-CAP-001__capability-enforcement-vector.md)
- [TASK-CAP-002 — Wire capability issuance for single-user local flows (minimal)](../../tasks/chunks/CHUNK_CAMPAIGN_2026_02_17/TASK-CAP-002__capability-issuance-endpoint.md)

---

TASK-IR-000 — Add repo-local “incident response” tooling + documentation

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Docs-only changes: run relevant checks if defined; otherwise note no automated tests apply.
 3. If checks succeed: stage with git add and commit.
 4. Output: summary, checks, commit hash.

🧩 Task Description
This change belongs in /docs/security/INCIDENT_RESPONSE.md and /scripts/security/ because it establishes the repeatable playbook and scripts for secret incident response (rotation + history rewrite + scanning).

Create these files:
 • docs/security/INCIDENT_RESPONSE.md
 • scripts/security/scan_secrets.sh
 • scripts/security/rewrite_history_remove_paths.sh

Contents requirements:
 • INCIDENT_RESPONSE.md must include:
 • How to identify compromised credentials (OAuth client secret, refresh tokens).
 • Rotation steps checklist.
 • Git history rewrite steps using git filter-repo (preferred) and post-rewrite force push instructions.
 • Post-incident verification checklist (grep, pre-commit, GitHub scanning).
 • scan_secrets.sh:
 • Runs git grep patterns for known risky strings (token.json, client_secret, refresh_token).
 • Optionally runs detect-secrets or gitleaks if installed (guarded with “if command exists”).
 • rewrite_history_remove_paths.sh:
 • Uses git filter-repo --path <…> --invert-paths for known secret paths, and explains that this is destructive.

Checks:
 • If you have a markdown lint/docs command, run it; otherwise:
 • Note: “Docs/scripts only — no automated tests apply.”

Git steps:

git add docs/security/INCIDENT_RESPONSE.md scripts/security/scan_secrets.sh scripts/security/rewrite_history_remove_paths.sh
git commit -m "Docs: add secret incident response playbook and tooling"

✅ Expected Output
 • Confirmation of files created.
 • Note about checks/tests.
 • Git commit hash.

⸻

TASK-IR-001 — Expand pre-commit secret detection (beyond private keys)

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Docs-only or config changes: run the relevant checks.
 3. If checks pass: stage and commit.
 4. Output: summary, checks, commit hash.

🧩 Task Description
This change belongs in /.pre-commit-config.yaml because secrets must be blocked before they enter commits (push protection is not enough).

Files in scope:
 • .pre-commit-config.yaml

Implement:
 • Add one of the following (choose the simplest that works in your repo):
 • Option A (recommended): gitleaks pre-commit hook
 • Option B: detect-secrets hook with a baseline file
 • Configure excludes so it doesn’t scan node_modules/, .venv/, .pnpm-store/, large generated folders.

Checks:

pre-commit run --all-files

Git steps:

git add .pre-commit-config.yaml
git commit -m "Security: strengthen pre-commit secret scanning"

✅ Expected Output
 • Hook added and passing.
 • Git commit hash.

⸻

TASK-IR-002 — Add “toxic secret paths” guardrails (ignore + denylist)

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Run relevant checks or note none apply.
 3. Stage and commit.
 4. Output: summary + commit hash.

🧩 Task Description
This change belongs in /.gitignore and /docs/security/ because you need both prevention (ignore) and policy (documented forbidden paths).

Files in scope:
 • .gitignore
 • docs/security/INCIDENT_RESPONSE.md (append a “Forbidden Paths” section)

Implement:
 • Add explicit ignore rules for:
 • guardian/secrets/
 • **/token.json
 • **/client_secret*.json
 • .env (already likely) + any OAuth credential downloads
 • In INCIDENT_RESPONSE.md, add a section:
 • “Never commit these paths; they must be treated as compromised if committed.”

Checks:
 • No automated tests apply (ignore/docs).

Git steps:

git add .gitignore docs/security/INCIDENT_RESPONSE.md
git commit -m "Security: formalize forbidden secret paths and ignore rules"

✅ Expected Output
 • Updated ignore rules + documented policy.
 • Git commit hash.

⸻

TASK-IR-003 — Add a runtime startup “fail closed” guard for missing secret broker backing

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Backend-only changes: run backend tests (pytest -v).
 3. Stage and commit.
 4. Output: summary, tests, commit hash.

🧩 Task Description
This change belongs in guardian/config.py (or the existing config module) because the system must not silently run insecure defaults when secrets storage is misconfigured.

Files in scope (choose the actual config module used today):
 • guardian/config.py (or wherever env parsing lives)
 • guardian/tests/test_config_security.py (new)

Implement:
 • Add env flag(s):
 • CODEXIFY_SECRET_STORE = env | keychain (default env for now)
 • CODEXIFY_REQUIRE_SECRET_STORE = true/false (default false)
 • If CODEXIFY_REQUIRE_SECRET_STORE=true and configured store is unavailable -> hard fail on startup with actionable error.

Tests:

pytest -v

Git steps:

git add guardian/config.py guardian/tests/test_config_security.py
git commit -m "Security: add fail-closed secret store requirement flag"

✅ Expected Output
 • New config flags + tests passing.
 • Git commit hash.

⸻

Chunk 2 — Secret Broker + Capability Grants (foundations)

TASK-BROKER-000 — Introduce Secret Broker interface + env-backed implementation

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Backend-only changes: run backend tests (pytest -v).
 3. Stage and commit.
 4. Output: summary, tests, commit hash.

🧩 Task Description
This change belongs in guardian/core/secret_broker.py because the broker is the single choke point for secrets access (agents never see long-lived raw tokens).

Files in scope:
 • guardian/core/secret_broker.py (new)
 • guardian/tests/test_secret_broker.py (new)

Implement:
 • Define interface:
 • get_secret(secret_id: str) -> str
 • set_secret(secret_id: str, value: str) -> None (optional for now)
 • is_available() -> bool
 • Implement EnvSecretBroker:
 • Maps secret_id → env var name convention (e.g. CODEXIFY_SECRET_<ID>)
 • Never logs values; redact in errors
 • Add minimal tests:
 • Missing secret raises controlled error
 • Returned secret matches env
 • Redaction behavior

Tests:

pytest -v

Git steps:

git add guardian/core/secret_broker.py guardian/tests/test_secret_broker.py
git commit -m "Core: add SecretBroker interface with env-backed implementation"

✅ Expected Output
 • Broker abstraction merged + tests passing.
 • Git commit hash.

⸻

TASK-BROKER-001 — Add macOS Keychain broker (best-effort, optional dependency)

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Backend-only changes: run backend tests (pytest -v).
 3. Stage and commit.
 4. Output: summary, tests, commit hash.

🧩 Task Description
This change belongs in guardian/core/secret_broker_keychain.py because OS-backed secure storage is the desired long-term store. Implement best-effort macOS Keychain support with a soft dependency so local dev doesn’t break.

Files in scope:
 • guardian/core/secret_broker_keychain.py (new)
 • guardian/tests/test_secret_broker_keychain.py (new, skip if keychain unavailable)
 • requirements/optional.txt (or the repo’s optional deps pattern) OR document optional install in README (pick your existing convention)

Implement:
 • KeychainSecretBroker using keyring (if installed):
 • Service name: codexify
 • Account: secret_id
 • If dependency missing:
 • is_available() returns false
 • get_secret() raises actionable error “install keyring”
 • Tests:
 • Skip on CI if keyring backend not available (use pytest skip markers)

Tests:

pytest -v

Git steps:

git add guardian/core/secret_broker_keychain.py guardian/tests/test_secret_broker_keychain.py
git commit -m "Core: add KeychainSecretBroker (optional) for OS-backed secrets"

✅ Expected Output
 • Optional keychain broker with safe fallbacks + tests passing/skipping appropriately.
 • Git commit hash.

⸻

TASK-CAP-000 — Add capability grant model (TTL + scope + max_calls)

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Backend-only changes: run backend tests (pytest -v).
 3. Stage and commit.
 4. Output: summary, tests, commit hash.

🧩 Task Description
This change belongs in guardian/core/capabilities.py because capability grants are the enforcement primitive: short-lived, scoped, deny-by-default.

Files in scope:
 • guardian/core/capabilities.py (new)
 • guardian/tests/test_capabilities.py (new)

Implement:
 • CapabilityGrant fields:
 • grant_id (uuid)
 • action (string enum-like)
 • resource (string, supports prefix matching)
 • expires_at (UTC timestamp)
 • max_calls (int)
 • calls_used (int)
 • Methods:
 • is_expired(now)
 • allows(action, resource, now)
 • consume_call() raises if exceeded

Tests:
 • Deny-by-default
 • Expiry
 • max_calls enforcement
 • Resource prefix matching (if included)

Tests:

pytest -v

Git steps:

git add guardian/core/capabilities.py guardian/tests/test_capabilities.py
git commit -m "Core: add capability grants with TTL and max_calls enforcement"

✅ Expected Output
 • Capability model added + tests passing.
 • Git commit hash.

⸻

TASK-CAP-001 — Enforce capability checks in one high-risk surface (vector write/read)

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Backend-only changes: run backend tests (pytest -v).
 3. Stage and commit.
 4. Output: summary, tests, commit hash.

🧩 Task Description
This change belongs in guardian/routes/codexify_router.py because /embed and /search are high-impact primitives; capability enforcement here prevents lateral movement even after auth.

Files in scope:
 • guardian/routes/codexify_router.py
 • guardian/tests/test_rate_limiting.py (or add new targeted tests)
 • guardian/tests/test_capability_enforcement_vector.py (new)

Implement:
 • Require a capability grant for:
 • action="vector:write" on /embed
 • action="vector:read" on /search
 • Resource can be namespace (e.g. resource="ns:<namespace_id>")
 • Deny requests lacking grant or with mismatched scope (403)

Tests:
 • Without capability -> 403
 • With valid capability -> success path
 • Expired capability -> 403

Tests:

pytest -v

Git steps:

git add guardian/routes/codexify_router.py guardian/tests/test_capability_enforcement_vector.py
git commit -m "Security: enforce capability grants on vector read/write endpoints"

✅ Expected Output
 • Capability enforcement in vector endpoints + tests passing.
 • Git commit hash.

⸻

TASK-CAP-002 — Wire capability issuance for single-user local flows (minimal)

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Backend-only changes: run backend tests (pytest -v).
 3. Stage and commit.
 4. Output: summary, tests, commit hash.

🧩 Task Description
This change belongs in guardian/guardian_api.py (or the existing auth/session module) because you need a minimal issuance mechanism to unblock the UI: server generates short-lived grants on behalf of the authenticated user.

Files in scope:
 • guardian/guardian_api.py (or the auth module you use today)
 • guardian/routes/iddb.py OR guardian/routes/admin.py (pick a safe existing authed route to host a “grant issuance” endpoint)
 • guardian/tests/test_capability_issuance.py (new)

Implement:
 • Add endpoint: POST /api/capabilities/issue
 • Requires auth
 • Accepts requested actions + namespace/resource
 • Returns signed/opaque grant token (or grant_id stored server-side)
 • Keep it minimal:
 • Store grants in-memory for now (dict) with TTL
 • Explicit TODO for persistent store later

Tests:
 • Unauthed -> 401
 • Authed -> returns grant
 • Grant can be used to call /embed or /search in tests

Tests:

pytest -v

Git steps:

git add guardian/guardian_api.py guardian/tests/test_capability_issuance.py
git commit -m "Security: add minimal capability issuance endpoint for local flows"

✅ Expected Output
 • Issuance endpoint + tests passing.
 • Git commit hash.

⸻

Quick “Campaign Run Order” ✅
 1. TASK-IR-000
 2. TASK-IR-001
 3. TASK-IR-002
 4. TASK-IR-003
 5. TASK-BROKER-000
 6. TASK-BROKER-001
 7. TASK-CAP-000
 8. TASK-CAP-001
 9. TASK-CAP-002

⸻

One important note (operational, not code) 🧨

Rotation/revoke + history rewrite still must happen outside the repo work. The tasks above support it, but don’t replace it.

⸻

If you want, I can also generate a Chunk 1 “localhost baseline” mini-campaign (bind-to-loopback + host/origin tests) next — but this set will get you the Secret Broker + capability spine fast. 😄
