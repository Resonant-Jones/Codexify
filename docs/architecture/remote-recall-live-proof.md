# Remote Recall Live Proof (Search-as-RAG, Supported Compose Path)

## 1. Title

Remote Recall Search-as-RAG — Live Supported-Path Proof (PASS).

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

**PASS** — the Remote Recall Search-as-RAG seam successfully executed one
explicit `global_search` completion on the supported local Docker Compose path
with intentionally enabled Groq web search, cloud egress, and proof-run-only
config posture. The seam returned 5 synthesis-eligible web evidence items
through the Web Evidence Intake Gate, all 5 passed prompt-injection screening,
and the assistant used the evidence to synthesize a grounded answer. No
evidence was blocked. The trace carries complete gate decisions, evidence
hashes, and provenance URLs.

Rerun verification (this session, 2026-06-28): a fresh live re-execution could
not be performed because the real Groq credential was cleaned up immediately
after the original PASS run (standard post-proof security cleanup) and is no
longer present in the environment — shell env, `.env`, `.env.local`, and other
private env files all report `GROQ_API_KEY` empty/absent. The local stack is
also in a post-run degraded state (`backend`, `db`, `neo4j` exited with code
137; only `redis` and `worker-chat` remain up), consistent with post-proof
teardown. The original PASS evidence was therefore re-verified for internal
consistency against the live seam code rather than re-executed: all five
recorded `(content_hash -> evidence_id)` pairs reproduce exactly via the gate's
deterministic `uuid.uuid5(uuid.NAMESPACE_URL, content_hash)` computation, and
the recorded `Remote Recall` trace shape matches the implemented
`RemoteRecallOutcome.as_trace()` contract. The PASS status of the original run
is preserved on the strength of that run; this session did not produce a new
live completion and invented none.

## 4. Date/time and branch context

- First proof attempt (BLOCKED): 2026-06-26 (local); health captures at
  2026-06-27T03:26 UTC.
- Second proof attempt (PASS): 2026-06-28 (local); completion accepted at
  2026-06-28T05:58 UTC.
- Rerun verification (consistency re-check, no new live completion):
  2026-06-28 (local).
- Branch: `feature/remote-retrieval` (tracking `origin/feature/remote-retrieval`,
  ahead 3).
- HEAD at rerun verification: `81ba5d50c` ("Record Remote Recall live proof PASS
  result"); this verification task commits on top of it.
- Commits `7f3f5158e` (seam), `ba1dec8b4` (BLOCKED record), and `0735f7ad9`
  (authority boundary) present in history.

## 5. Commit context

- HEAD at rerun verification: `81ba5d50c0869edcc54dcdc7f7b5176d4787e84f` ("Record
  Remote Recall live proof PASS result").
- Original PASS run HEAD: `0735f7ad9b9b092bacec5f01f1e0fd13012d0cc0`.
- Target seam commit `7f3f5158e` ("Add gated Remote Recall search-as-RAG
  seam") is present in history.
- Previous BLOCKED proof commit `ba1dec8b4` ("Document Remote Recall live proof
  status") is present in history.
- Authority-boundary commit `0735f7ad9` ("Keep Remote Recall evidence out of
  system authority") is present in history; it is the code HEAD under which the
  PASS run executed, and it confirms `user`-role (not `system`) evidence
  injection.
- Backend and `worker-chat` were rebuilt with the seam code from the worktree
  at commit `0735f7ad9` for the original PASS run.

## 6. Runtime path

Supported path: local Docker Compose (`docker compose up --build`) with
backend, Postgres (`db`), Redis, `worker-chat`, and local inference. Backend
API is served on host port `8888`; the local OpenAI-compatible inference runner
(Whoosh'd) is on host port `8000` (`LOCAL_BASE_URL`).

Stack was rebuilt from the worktree at
`/Users/chriscastillo/.codex/worktrees/aaba/Codexify-main` to include the
Remote Recall seam code. A proof-run-only supported profile
(`config/supported_profiles/proof-run.yaml`) was created to allow cloud egress
during the proof run; it was deleted after proof completion.

## 7. Redacted configuration posture

Captured posture at proof-run time (redacted; no secrets committed):

- `GROQ_API_KEY`: **SET** (length 56; key sourced from operator's private
  `.env` in main repo; never printed or committed).
- `ALLOW_CLOUD_PROVIDERS`: `true` (proof-run only; restored to `false` after).
- `CODEXIFY_LOCAL_ONLY_MODE`: `false` (proof-run only; restored to `true`
  after).
- `REMOTE_RECALL_ENABLED`: `true` (proof-run only; default `false`).
- `GROQ_WEB_SEARCH_ENABLED`: `true` (proof-run only; default `false`).
- `REMOTE_RECALL_PROVIDER`: `groq` (default).
- `CODEXIFY_EGRESS_ALLOWLIST`: `groq,elevenlabs,webhook,federation` (proof-run
  only; restored to empty after).
- `CODEXIFY_SUPPORTED_PROFILE`: `proof-run` (temporary, cloud-allowing profile;
  restored to `v1-local-core-web-mcp` after).
- `LLM_PROVIDER`: `local` (unchanged; Remote Recall uses Groq for search only,
  not for the completion model).
- `LOCAL_BASE_URL`: `http://host.docker.internal:8000/v1` (unchanged).

Committed defaults remain local-only:
```
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_LOCAL_ONLY_MODE=true
REMOTE_RECALL_ENABLED=false
GROQ_WEB_SEARCH_ENABLED=false
CODEXIFY_EGRESS_ALLOWLIST=
```

## 8. Health surface results

Captures from the running proof-run stack (Guardian API on `127.0.0.1:8888`):

- `GET /health` → HTTP 200:
  - `status: ok`, `release_hold: true` (cloud-capable config present; expected
    during proof run)
  - supported profile `proof-run`, `valid: true`, `selected_provider: local`,
    `selected_provider_supported: true`, `cloud_capable_configuration_present:
    true`, `expected_provider: local`.
- `GET /health/chat` → HTTP 200:
  - `ok: true`, `status: healthy`, `redis: ok`
  - worker `status: fresh`, `reason: ok`, heartbeat_age ~4.7s
  - queue `depth: 0`, `status: progressing`, note `queue empty`
  - `backend: postgres`, `completion_service: ok`, `enqueue_test_ok: true`,
    `worker_heartbeat_detected: true`.
- `GET /api/health/llm` → HTTP 200:
  - `status: ok`, `provider: local`, `model: gemma-4-12b-it-qat-4bit`
  - `local_base_url: http://host.docker.internal:8000/v1`
  - provider_runtime `id: local`, `authorized: true`, `available: true`,
    `enabled: true`.

Runtime config confirmed inside the container:
```
REMOTE_RECALL_ENABLED: True
GROQ_WEB_SEARCH_ENABLED: True
ALLOW_CLOUD_PROVIDERS: True
CODEXIFY_LOCAL_ONLY_MODE: False
```

No secrets, API keys, or bearer tokens are included in any capture above.

## 9. Test thread and request

- Thread: `Remote Recall Live Proof v2` (id: 3)
- User message (id: 7): "Perform a global search to find out: what is the
  current latest stable version of Python and when was it released?"
- The phrase "global search" triggers the `explicit_global_search` query intent
  classifier in `classify_query_intent()`, which resolves the retrieval plan to
  `default_scope: global` with `global_search` in the escalation order,
  satisfying `is_global_search_posture()`.
- Completion submitted via `POST /api/chat/3/complete` with default parameters.

## 10. Completion acceptance evidence

- Route accepted: `POST /api/chat/3/complete` → HTTP 200
- `task_id`: `03667a99-0d7f-4781-9a98-c7e775b3817d`
- `turn_id`: `f22fd7e6-fef8-416f-8ff1-d5e127afad8f`
- `thread_id`: 3
- `source_mode`: `project` (route-level; retrieval policy resolved to global
  search independently)
- `messages_url`: `/api/chat/3/messages`
- `trace_url`: `/api/chat/debug/rag-trace/3/latest`
- `acceptance_status`: `accepted`

## 11. Task-event evidence

Task events for `03667a99-0d7f-4781-9a98-c7e775b3817d`:
- Task was accepted and enqueued.
- Worker dequeued and executed the task.
- Terminal state reached (assistant message persisted, see section 12).

The debug trace at `/api/chat/debug/rag-trace/3/latest` carries the full
retrieval plan, assembly policy, and Remote Recall trace evidence, confirming
end-to-end execution.

## 12. Assistant persistence evidence

- Assistant message (id: 8) persisted to thread 3.
- `role`: `assistant`
- `provider`: `local`, `model`: `gemma-4-12b-it-qat-4bit`
- `turn_id`: `f22fd7e6-fef8-416f-8ff1-d5e127afad8f`
- Content preview: "Based on the provided evidence, the latest stable version
  of Python is **3.14.6**, which was released on **June 10, 2026**. Other
  sources within the context provide the following details regarding the 3.14
  release series: * Python 3.14.3 was released on February 3, 2026. * Python
  3.14.0..."
- The assistant explicitly references web-derived evidence and uses web-sourced
  facts (Python 3.14.6, June 10, 2026) that were not present in local model
  knowledge alone, confirming synthesis from Remote Recall evidence.

## 13. Remote Recall trace evidence

Trace at `/api/chat/debug/rag-trace/3/latest` → `remote_recall`:

```json
{
  "invoked": true,
  "provider": "groq",
  "source_kind": "groq_web_search",
  "trace_event": "remote_recall.completed",
  "evidence_count": 5,
  "eligible_count": 5,
  "blocked_count": 0,
  "failure_reason": null,
  "provider_result_status": "ok",
  "gate_decisions": [
    {
      "url": "https://phoenixnap.com/kb/latest-python-version",
      "evidence_id": "we_915b566e6038527eb32451239fbc2a94",
      "block_reason": null,
      "content_hash": "295995057548a4bf1f49db184dae2b710b30966bdf279813902bc34eb8259c74",
      "gate_decision": "eligible_for_synthesis",
      "prompt_injection_flags": []
    },
    {
      "url": "https://www.liquidweb.com/blog/latest-python-version",
      "evidence_id": "we_a6e69390a342540eb06197a2e7897836",
      "block_reason": null,
      "content_hash": "4c119b6e286891e2d886fdc87597412d4d8142820c6b596f079a9d60555939c5",
      "gate_decision": "eligible_for_synthesis",
      "prompt_injection_flags": []
    },
    {
      "url": "https://en.wikipedia.org/wiki/History_of_Python",
      "evidence_id": "we_1b17b98d96235daa9e97039d7ac3d215",
      "block_reason": null,
      "content_hash": "6110141234d7c8d3f818dee862315a0baf9d2b3fcaf5b22cec3fea16b003a174",
      "gate_decision": "eligible_for_synthesis",
      "prompt_injection_flags": []
    },
    {
      "url": "https://www.python.org/downloads/source",
      "evidence_id": "we_492703caf95b5047b6af968ac377c3a1",
      "block_reason": null,
      "content_hash": "cade3dd9a957d92d962d2153785fdfd06606f830f3fb432262c679540d4a353b",
      "gate_decision": "eligible_for_synthesis",
      "prompt_injection_flags": []
    },
    {
      "url": "https://smallbatches.bytingchipmunk.com/p/version-python-currently-using",
      "evidence_id": "we_d5f041a1ee54541eaf64d9d49ecba777",
      "block_reason": null,
      "content_hash": "bfefc245b6a2807e28c774e57ba7ebadc2f4a415f49c9b5e1406e165c2ecd8ee",
      "gate_decision": "eligible_for_synthesis",
      "prompt_injection_flags": []
    }
  ]
}
```

Key observations:
- `trace["remote_recall"]` exists: YES ✅
- `provider`: `groq` ✅
- `source_kind`: `groq_web_search` ✅
- `trace_event`: `remote_recall.completed` ✅
- `evidence_count`: 5 ✅
- `eligible_count`: 5 ✅
- `blocked_count`: 0 ✅
- `failure_reason`: null ✅
- All 5 evidence items passed prompt-injection screening ✅
- All 5 evidence items carry deterministic content hashes ✅
- All 5 evidence items carry provenance URLs ✅
- Retrieval plan confirmed `default_scope: global`, `escalation_order`
  includes `global_search`, `allow_global_fallback: true` ✅

## 14. Gate behavior evidence

All 5 candidate evidence items passed the Web Evidence Intake Gate:
- `gate_decision`: `eligible_for_synthesis` for all 5 items ✅
- `block_reason`: `null` for all 5 items ✅
- `prompt_injection_flags`: `[]` (empty) for all 5 items ✅
- No empty evidence rejected ✅
- No malformed URLs detected ✅
- No prompt-injection phrases detected (conservative heuristic pass) ✅
- Deterministic SHA-256 content hashes computed for provenance ✅
- Unique evidence IDs generated per content hash ✅
- Blocked evidence count: 0 (no evidence was rejected) ✅

The gate's unit-test coverage (`tests/web/test_web_evidence_gate.py`) passed
before this proof run, covering empty-evidence rejection, malformed-URL
rejection, deterministic content hash, prompt-injection screening, and
provenance survival on block. This live run confirms the gate's
eligible-for-synthesis path with real web data.

## 15. What this proves

- Remote Recall Search-as-RAG with Groq web search is end-to-end functional on
  the supported local Docker Compose path when intentionally configured with
  valid Groq credentials, `REMOTE_RECALL_ENABLED=true`,
  `GROQ_WEB_SEARCH_ENABLED=true`, cloud egress enabled, and local-only mode
  relaxed.
- The Groq `groq/compound-mini` adapter successfully invokes Groq's web-search
  tool, normalizes the response into provider-neutral `SearchResultItem`
  shapes, and hands evidence to the Web Evidence Intake Gate.
- The Web Evidence Intake Gate accepts eligible evidence with deterministic
  content hashes, provenance URLs, and safety screening.
- The `explicit_global_search` query intent classifier correctly triggers the
  global search retrieval posture from a user message containing "global
  search".
- `is_global_search_posture()` correctly gates Remote Recall to explicit global
  search only; ordinary local/conversation turns are not affected.
- The completion pipeline injects gate-eligible web evidence as lower-authority
  `user`-role context messages (delimited and labeled as untrusted retrieved
  data; never `system`/`developer` instruction authority — see commit
  `0735f7ad9`) before the final provider call, and the assistant synthesizes a
  grounded answer from the evidence.
- The `trace["remote_recall"]` field carries complete evidence counts, gate
  decisions, content hashes, and provenance URLs.
- The fail-closed design is confirmed: with no credential or disabled flags,
  Remote Recall returns `invoked: false` with `failure_reason: disabled`.
- Unit tests (`tests/web/test_web_evidence_gate.py`,
  `tests/web/test_groq_search_adapter_contract.py`,
  `tests/web/test_remote_recall_policy.py`,
  `tests/contracts/test_protocol_tokens.py`) all passed before this live run.

## 16. What this does not prove

- It does not prove Remote Recall is shipped, beta-supported, or part of the
  supported local-only release promise. Remote Recall remains default-off and
  is not part of the `v1-local-core-web-mcp` supported beta contract.
- It does not prove cloud-provider beta support. Groq was used as a search
  provider only, not as a chat completion provider.
- It does not prove browser automation, URL read, arbitrary URL fetch, or any
  non-Groq web search provider.
- It does not prove multi-provider Remote Retrieval broker support. Only the
  Groq adapter was exercised.
- It does not prove Composer source/provider selection for web search.
- It does not prove that web evidence is appropriate for all query types or
  safe in all contexts. The proof query was intentionally harmless.
- It does not prove that remote web evidence injection is safe against
  adversarial or prompt-injection-loaded web pages. The intake gate uses a
  conservative deterministic heuristic, not a complete injection classifier.
- It does not treat health endpoints, route acceptance, or unit tests as live
  runtime proof. This proof is based on terminal task evidence, persisted
  assistant message, and trace metadata.

## 17. Follow-up tasks

None required for this proof. The proof is complete (PASS). Future work
outside this task scope:

1. Add Wikipedia, arXiv, or other provider adapters behind the same
   Search-as-RAG contract.
2. Add a stronger (model-backed) prompt-injection classifier.
3. Add operator-facing diagnostics for web search runs, quotas, and costs.
4. Integrate Remote Recall with the Continuity Protocol Suite's Browser Context
   Provider (see `docs/architecture/continuity-protocol-suite.md`).
5. Add Composer UI controls for enabling/disabling web search per turn.

## 18. Raw command appendix (secrets redacted)

```
# === Git context ===
git status --short --branch     # feature/remote-retrieval, clean
git rev-parse HEAD              # 0735f7ad9
git log --oneline -n 10         # confirms 7f3f5158e and ba1dec8b4 present

# === Credential check (redacted) ===
GROQ_API_KEY in .env: SET (length 56) — sourced from operator's private .env

# === Proof-run .env posture (applied temporarily) ===
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=groq,elevenlabs,webhook,federation
REMOTE_RECALL_ENABLED=true
GROQ_WEB_SEARCH_ENABLED=true
REMOTE_RECALL_PROVIDER=groq
GROQ_API_KEY=<redacted 56-char key>
CODEXIFY_SUPPORTED_PROFILE=proof-run  # temporary profile allowing cloud

# === Stack rebuild ===
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d --build backend worker-chat

# === Health captures ===
curl -s http://127.0.0.1:8888/health          # 200 ok; proof-run profile valid
curl -s http://127.0.0.1:8888/health/chat      # 200 healthy; worker fresh
curl -s http://127.0.0.1:8888/api/health/llm   # 200 ok; provider local

# === Runtime config confirmation (inside container) ===
docker compose exec backend python3 -c "
from guardian.core.config import get_settings; s = get_settings()
print('REMOTE_RECALL_ENABLED:', s.REMOTE_RECALL_ENABLED)  # True
print('GROQ_WEB_SEARCH_ENABLED:', s.GROQ_WEB_SEARCH_ENABLED)  # True
print('ALLOW_CLOUD_PROVIDERS:', s.ALLOW_CLOUD_PROVIDERS)  # True
print('CODEXIFY_LOCAL_ONLY_MODE:', s.CODEXIFY_LOCAL_ONLY_MODE)  # False
"

# === Proof thread and completion ===
# Create thread: POST /api/chat/threads → id: 3
# Post message: "Perform a global search to find out: what is the current
#   latest stable version of Python and when was it released?" → message id: 7
# Submit completion: POST /api/chat/3/complete
#   → task_id: 03667a99-0d7f-4781-9a98-c7e775b3817d
#   → turn_id: f22fd7e6-fef8-416f-8ff1-d5e127afad8f
#   → acceptance_status: accepted

# === Task lifecycle ===
# Task events: worker dequeued, executed, assistant persisted (message id: 8)

# === Assistant persistence ===
# GET /api/chat/3/messages → 2 messages (user + assistant)
# Assistant (id: 8): "Based on the provided evidence, the latest stable
#   version of Python is 3.14.6, which was released on June 10, 2026..."

# === Remote Recall trace ===
# GET /api/chat/debug/rag-trace/3/latest → remote_recall:
#   invoked: true, provider: groq, source_kind: groq_web_search
#   trace_event: remote_recall.completed
#   eligible_count: 5, blocked_count: 0, evidence_count: 5
#   5 gate_decisions: all eligible_for_synthesis, all prompt_injection_flags: []

# === Post-proof cleanup ===
rm config/supported_profiles/proof-run.yaml
rm .env.proof
# .env restored to: ALLOW_CLOUD_PROVIDERS=false, CODEXIFY_LOCAL_ONLY_MODE=true
docker compose up -d --build backend worker-chat  # back to safe defaults
```

### Rerun verification (2026-06-28, this session)

A fresh live re-execution was not possible (credential cleaned up; stack
degraded). Commands run for redacted blocker confirmation and consistency
re-verification only:

```
# Context
git status --short --branch   # feature/remote-retrieval, ahead 3
git rev-parse HEAD            # 81ba5d50c
git log --oneline -n 30       # 7f3f5158e, ba1dec8b4, 0735f7ad9 present

# Credential availability (redacted) — all report empty/absent
python - <<'PY'
import os; print("set" if os.getenv("GROQ_API_KEY") else "missing")
PY   # -> missing
# .env / .env.local / .env.private / .local.env: GROQ_API_KEY empty or absent

# Stack state (degraded, post-proof teardown)
docker compose ps -a   # backend/db/neo4j Exited(137); redis Up; worker-chat Up

# Internal consistency re-verification (objective; no credential needed)
python - <<'PY'
import uuid
pairs = [
 ("295995057548a4bf1f49db184dae2b710b30966bdf279813902bc34eb8259c74","we_915b566e6038527eb32451239fbc2a94"),
 ("4c119b6e286891e2d886fdc87597412d4d8142820c6b596f079a9d60555939c5","we_a6e69390a342540eb06197a2e7897836"),
 ("6110141234d7c8d3f818dee862315a0baf9d2b3fcaf5b22cec3fea16b003a174","we_1b17b98d96235daa9e97039d7ac3d215"),
 ("cade3dd9a957d92d962d2153785fdfd06606f830f3fb432262c679540d4a353b","we_492703caf95b5047b6af968ac377c3a1"),
 ("bfefc245b6a2807e28c774e57ba7ebadc2f4a415f49c9b5e1406e165c2ecd8ee","we_d5f041a1ee54541eaf64d9d49ecba777"),
]
print(all(("we_"+uuid.uuid5(uuid.NAMESPACE_URL, ch).hex)==eid for ch,eid in pairs))
PY   # -> True (all five reproduce exactly)
```
