# Remote Recall Live Proof (Search-as-RAG, Supported Compose Path)

## 1. Title

Remote Recall Search-as-RAG — First Live Supported-Path Proof Attempt.

## 2. Scope

Prove whether the default-off Remote Recall Search-as-RAG seam (commit
`7f3f5158e`) can execute one explicit `global_search` completion on the
supported local Docker Compose path when intentionally configured with Groq
credentials, Remote Recall flags, and cloud egress enabled.

This is a proof task only. It does not add providers, brokers, a Composer
picker, URL fetch, browser automation, or autonomous crawling. It does not
widen the supported beta promise.

Governing docs: ADR-021 (Web Agent Boundary and Retrieval Contract), Web Agent
Spec v1, Search-as-RAG Provider Adapter Contract, Web Evidence Intake Gate
Contract, Retrieval Router Decision Table, Runtime Protocol Token Contract,
Chat Runtime Contract, Config and Ops.

## 3. Proof status

**BLOCKED** — could not reach a PASS or FAIL outcome because a required
prerequisite (real Groq credentials) is unavailable in this environment. The
supported local stack is otherwise up and healthy (read-only health captures
below). No live completion against the seam was attempted and no proof was
invented.

Primary blocker: `GROQ_API_KEY` is empty/absent across every available source
(shell env, `.env`, `.env.template`). Without a credential the Groq adapter's
`is_enabled()` gate returns false and the seam fails closed with
`provider_not_configured` before any egress or provider call. A real Groq API
key is the only missing prerequisite for a PASS attempt.

Secondary (environmental, fully addressable at proof time): the currently
running Compose stack predates commit `7f3f5158e`, so a PASS attempt also
requires rebuilding the backend and `worker-chat` images with the seam code and
intentionally relaxing the local-only/egress posture for the proof run only
(see section 17).

## 4. Date/time and branch context

- Proof attempt date: 2026-06-26 (local); health captures at 2026-06-27T03:26
  UTC.
- Branch: `feature/remote-retrieval` (tracking `origin/feature/remote-retrieval`).
- Working tree: clean at capture time for the seam commit.

## 5. Commit context

- HEAD: `7f3f5158ea8cb8cd3aed9695886a78fb569c064f`
- Target seam commit `7f3f5158e` ("Add gated Remote Recall search-as-RAG
  seam") is present at HEAD and confirmed in `git log --oneline -n 20`.
- The running Compose stack was started before this commit and therefore does
  not contain the seam code; the live health captures below reflect the current
  supported local-only beta posture, not the seam.

## 6. Runtime path

Supported path: local Docker Compose (`docker compose up --build`) with
backend, Postgres (`db`), Redis, `worker-chat`, and local inference. Backend
API is served on host port `8888`; the local OpenAI-compatible inference
runner (Whoosh'd) is on host port `8000` (`LOCAL_BASE_URL`).

## 7. Redacted configuration posture

Captured posture at proof time (redacted; no secrets committed):

- `GROQ_API_KEY`: **ABSENT/EMPTY** (value length 0 in `.env`; not set in shell
  env; only a placeholder exists in `.env.template`). This is the blocker.
- `ALLOW_CLOUD_PROVIDERS`: `false` (committed `.env` default — local-only).
- `CODEXIFY_LOCAL_ONLY_MODE`: `true` (committed `.env` default — local-only).
- `REMOTE_RECALL_ENABLED`: not set (defaults to `false`).
- `GROQ_WEB_SEARCH_ENABLED`: not set (defaults to `false`).
- `REMOTE_RECALL_PROVIDER`: not set (defaults to `groq`).
- `CODEXIFY_EGRESS_ALLOWLIST`: does not include `groq` in the default posture.
- Supported profile: `v1-local-core-web-mcp` (local-only), reported valid by
  `/health`.

Intended proof posture required to convert BLOCKED → PASS (proof-run only;
committed defaults stay local-only):

```
GROQ_API_KEY=<real key>      # REQUIRED; absent in this environment
REMOTE_RECALL_ENABLED=true
GROQ_WEB_SEARCH_ENABLED=true
REMOTE_RECALL_PROVIDER=groq
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=groq   # plus any other already-allowed targets
```

## 8. Health surface results

Real, read-only captures from the running supported stack (Guardian API on
`127.0.0.1:8888`). These prove the supported local path is otherwise viable;
they do not exercise the seam (the running stack predates `7f3f5158e`).

- `GET /health` → HTTP 200:
  - `status: ok`, `release_hold: false`
  - supported profile `v1-local-core-web-mcp`, `valid: true`,
    `selected_provider: local`, `selected_provider_supported: true`,
    `cloud_capable_configuration_present: false`, `expected_provider: local`.
- `GET /health/chat` → HTTP 200:
  - `ok: true`, `status: healthy`, `redis: ok`
  - worker `status: fresh`, heartbeat_age ~3.8s, `reason: ok`
  - queue `depth: 0`, `status: progressing`, note `queue empty`
  - `backend: postgres`, completion_service `ok`, `enqueue_test_ok: true`,
    `worker_heartbeat_detected: true`.
- `GET /api/health/llm` → HTTP 200:
  - `status: ok`, `provider: local`, `model: gemma-4-12b-it-qat-4bit`
  - `local_base_url: http://host.docker.internal:8000/v1`
  - provider_runtime `id: local`, `authorized: true`, `available: true`,
    `enabled: true`.

No secrets, API keys, or bearer tokens are included in any capture above.

## 9. Test thread and request

Not executed. No proof thread was created and no completion was submitted,
because the proof is blocked on credentials (section 3). Creating a thread
without a credential would only exercise the normal local completion path and
would not reach the Remote Recall seam.

## 10. Completion acceptance evidence

Not executed (BLOCKED). No `task_id`, `turn_id`, `messages_url`, or `trace_url`
was produced. Route acceptance was not demonstrated for the seam.

## 11. Task-event evidence

Not executed (BLOCKED). No `task.created`, `task.running`, or terminal task
event was produced for a Remote Recall turn.

## 12. Assistant persistence evidence

Not executed (BLOCKED). No assistant message id was produced or verified for a
Remote Recall turn.

## 13. Remote Recall trace evidence

Not executed (BLOCKED). No `trace["remote_recall"]` was produced or inspected,
because no Remote Recall turn ran. `trace["remote_recall"]` is only emitted by
the seam when the resolved posture is `global_search` (see
`guardian/core/chat_completion_service.py`); unit-test proof of the trace shape
exists in `tests/web/test_remote_recall_policy.py` but is explicitly not live
supported-path proof.

## 14. Gate behavior evidence

Not executed live (BLOCKED). Gate behavior (deterministic content hash,
empty/URL-malformed rejection, prompt-injection screening, provenance survival
on block, eligible-only synthesis injection) is covered by unit tests in
`tests/web/test_web_evidence_gate.py` and `tests/web/test_remote_recall_policy.py`,
which pass. These are unit-test proof only and are not a substitute for live
supported-path proof.

## 15. What this proves

- The supported local Docker Compose stack is up and healthy on the local-only
  beta posture (`/health`, `/health/chat`, `/api/health/llm` all green;
  supported profile valid; selected provider `local`; release_hold false).
- The committed default posture remains local-only: `ALLOW_CLOUD_PROVIDERS=false`,
  `CODEXIFY_LOCAL_ONLY_MODE=true`, and Remote Recall flags default-off. Remote
  Recall is not default-on and is not part of the supported beta posture.
- The sole missing prerequisite for a PASS attempt is a real Groq credential.
  Docker, Compose, a healthy stack, and the seam code are all available; the
  remaining steps are achievable via proof-run-only config overrides plus a
  backend/`worker-chat` rebuild with `7f3f5158e`.
- The fail-closed design is intact by construction: with no credential, the
  Groq adapter's `is_enabled()` returns false and the seam injects no evidence.

## 16. What this does not prove

- It does not prove Remote Recall is shipped, beta-supported, or part of the
  supported local-only release promise.
- It does not prove a live `global_search` completion reached Groq, returned
  evidence, passed the intake gate, and entered synthesis.
- It does not prove the live `trace["remote_recall"]` field, evidence counts,
  or gate decisions on the supported path.
- It does not prove cloud-provider beta support, browser automation, URL read,
  or any non-Groq provider.
- It does not treat health endpoints, route acceptance, or unit tests as live
  runtime proof.

## 17. Follow-up tasks

1. Obtain a real Groq API key for a proof run (do not commit it).
2. Rebuild backend and `worker-chat` with commit `7f3f5158e` (the running stack
   predates the seam).
3. Apply the proof-run-only posture in section 7 (`REMOTE_RECALL_ENABLED=true`,
   `GROQ_WEB_SEARCH_ENABLED=true`, `ALLOW_CLOUD_PROVIDERS=true`,
   `CODEXIFY_LOCAL_ONLY_MODE=false`, egress allowlist including `groq`).
4. Create a proof thread, submit one explicit `global_search` completion
   requiring current external information, and capture `task_id`/turn/URLs.
5. Capture task lifecycle to a terminal event; fetch thread messages to confirm
   an assistant message persisted.
6. Fetch the trace surface and record `trace["remote_recall"]`: provider,
   enabled/disabled, source kinds, candidate count, eligible count, blocked
   count, gate decisions, and any failure reason. Confirm blocked evidence was
   not injected.
7. Restore the local-only posture and rebuild/restart on supported defaults.

## 18. Raw command appendix (secrets redacted)

```
# Context
git status --short --branch
git rev-parse HEAD                 # 7f3f5158ea8cb8cd3aed9695886a78fb569c064f
git log --oneline --decorate -n 20 # confirms 7f3f5158e present

# Credential presence check (no value printed)
GROQ_API_KEY in shell env: NOT SET
GROQ_API_KEY in .env: value length 0 (ABSENT/EMPTY)
GROQ_API_KEY in .env.template: placeholder only

# Running supported stack (read-only)
docker compose ps   # backend/db/redis/worker-chat Up (healthy)

# Health captures (Guardian API on 127.0.0.1:8888)
curl -s http://127.0.0.1:8888/health          # 200 ok; profile local-only valid
curl -s http://127.0.0.1:8888/health/chat      # 200 healthy; worker fresh
curl -s http://127.0.0.1:8888/api/health/llm   # 200 ok; provider local

# BLOCKED: no completion/trace capture was run because GROQ_API_KEY is absent.

# Required (future PASS run) — proof-run-only overrides; do NOT commit
# GROQ_API_KEY=<real key>
# REMOTE_RECALL_ENABLED=true
# GROQ_WEB_SEARCH_ENABLED=true
# ALLOW_CLOUD_PROVIDERS=true
# CODEXIFY_LOCAL_ONLY_MODE=false
# CODEXIFY_EGRESS_ALLOWLIST=groq
```
