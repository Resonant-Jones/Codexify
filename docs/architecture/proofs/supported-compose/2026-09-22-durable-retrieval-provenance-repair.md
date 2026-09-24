# Durable retrieval provenance repair — 2026-09-22

## Result

**Bounded result: PASS. F5 CLOSED.**

The supported local Guardian path now persists the bounded identity of
document/chunk material that was actually retained for provider input. The
same `retrieval_provenance.contributing_items` object is stored on the durable
assistant message and emitted in the terminal `task.completed` payload.

This closes only the F5 retrieval-provenance gap. F4 remains closed by the
preceding shell repair. F7 remains open, so the overall supported-Compose
release posture remains `HOLD`.

## Environment

| Field | Evidence |
| --- | --- |
| Observation window | 2026-09-22, approximately 09:00–11:15 EDT |
| Branch / base commit | `main`; `ae6cc6b308e5fc7a4a28956d5a780e26eeef290b` |
| Upstream / divergence | `origin/main`; ahead 6, behind 0 |
| Initial worktree | One unrelated staged deletion: `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`; no unstaged or untracked paths |
| Supported topology | `docker-compose.yml` plus `docker-compose.whooshd-smoke.yml`; preserved PostgreSQL, Redis, Chroma, and other data volumes |
| Supported profile | `v1-local-core-web-mcp`, valid with no mismatches |
| Effective route | provider `local`; logical model `local-chat`; runtime Whoosh'd |
| Browser | Playwright CLI against the Compose frontend at `http://[::1]:5173/chat/10` |

The unrelated staged Dev Log deletion was not restored, unstaged, modified, or
included in this task's commit.

## Root cause and pre-repair evidence

The retained completion bundle already distinguished candidate material from
material actually injected into the provider prompt through `_prompt_meta`.
Stable ingestion metadata also already existed for semantic chunks, including
document id, vector/chunk id, chunk index/count, project scope, namespace, and
user scope.

Three projection gaps prevented that truth from becoming durable:

1. `_build_retrieval_provenance(...)` persisted aggregate source counts and a
   retrieval status, but did not project the contributing document/chunk
   identities from the retained bundle.
2. Whole uploaded project-document excerpts carried document identity and
   scope but dropped the stable ingestion index of the retained prefix. The
   excerpt is built from the beginning of the same parsed text chunked by the
   embedding worker, so its existing ingestion index is `0`.
3. The chat worker compatibility path kept retrieval truth nested in the
   completion payload/summary/trace but did not promote it into the existing
   result object consumed by assistant-message persistence and terminal event
   publication.

The preserved pre-repair live record demonstrates the gap: assistant message
`33` on thread `6` and terminal outbox row `78` had no durable
`retrieval_provenance`, even though the corresponding supported-path answer
used uploaded document `95b2cd45-b603-46a0-99ea-07fc4e855cdc`.

## Retained attribution path

For semantic retrieval, the authoritative attribution is the already-retained
semantic item and its ingestion metadata. Its item id is the stable
`chunk_id`; `metadata.doc_id` becomes `document_id`; existing chunk index/count,
project/thread scope, namespace, retrieval lane, filename, and score are
projected when present.

For a whole uploaded document retained through the project/thread document
bundle, the authoritative attribution is its existing document record. The
broker now carries `chunk_index: 0` for a non-empty uploaded prefix excerpt.
It does not invent a `chunk_id`. The vector store independently identifies the
same fixture as:

```text
collection: codexify_vault_supported
vector/chunk id: doc_1db8467369c249cdb5fbe5a23fe1b031
document id: c9670812-55a1-4f49-b8a3-58e7a80d38f6
chunk index/count: 0 / 1
namespace: project:1
user: local
```

Candidate-only, suppressed, global, and out-of-scope items are not promoted as
contributors. The completion projection only reads families marked as
injected by `_prompt_meta`; the live result contains only same-project records
from Project `1` and reports `global_documents: 0`.

## Repair

`guardian/context/broker.py` now preserves the existing stable first-chunk
index on non-empty uploaded-document prefix records.

`guardian/core/chat_completion_service.py` now:

- builds metadata-only `contributing_items` from semantic and document families
  that the existing prompt assembly marked as injected;
- normalizes stable document/chunk identity and optional scope/ranking fields;
- deduplicates contributors and bounds the array at 64 entries;
- never copies text, excerpts, parsed content, or prompt content into the
  contributor projection; and
- makes `retrieval_executed`/absence truth coherent when at least one
  contributor exists.

`guardian/workers/chat_worker.py` now promotes the existing retrieval fields
from the completion result, sanitized payload summary, or trace into the
worker's existing result envelope. Existing assistant persistence and
`task.completed` publication then carry the same object.

The repaired authority boundary is:

```text
existing retrieval selection and retained prompt bundle
  -> bounded contributing document/chunk projection
  -> existing assistant extra_meta and task.completed payload
```

No new retrieval engine, ranking path, lifecycle channel, database table,
schema migration, event type, provider behavior, or content-retention surface
was introduced.

## Static validation

| Command | Result | Interpretation |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/core/test_retrieval_document_chunk_provenance.py tests/context/test_retrieval_trace_provenance.py tests/workers/test_chat_worker_lifecycle_events.py guardian/tests/workers/test_chat_worker_completion_semantics.py tests/core/test_chat_completion_service_source_mode_fallback.py` | PASS: 55 tests | Covers retained semantic chunks, uploaded prefix chunk index, non-injected/suppressed exclusion, durable assistant/event equality, and neighboring completion semantics. |
| `.venv/bin/python -m py_compile guardian/context/broker.py guardian/core/chat_completion_service.py guardian/workers/chat_worker.py` | PASS | Edited runtime modules compile. |
| `.venv/bin/ruff check tests/core/test_retrieval_document_chunk_provenance.py tests/context/test_retrieval_trace_provenance.py tests/workers/test_chat_worker_lifecycle_events.py` | PASS | New and edited focused tests are lint-clean. |
| `.venv/bin/ruff check guardian/context/broker.py guardian/core/chat_completion_service.py guardian/workers/chat_worker.py --output-format concise` | FAIL: 19 existing findings | Existing unused imports/locals, undefined-name ledger, and repeated dictionary keys remain F7. No finding points to the new provenance helpers or broker projection. |

The source-file Ruff baseline was not widened into this repair. In particular,
known `trace_fallback`, payload-summary, duplicate-key, and older unused-code
findings remain unchanged.

## Live supported-path proof

### Fixture and ingestion truth

The browser uploaded `codexify-provenance-0ce612a7.txt` to Project `1`
(`General`). The document contained marker `CODEXIFY_PROVENANCE_0CE612A7`, the
synthetic value `ONYX-6807`, and the independent fact that the value has no
meaning outside this qualification.

| Field | Evidence |
| --- | --- |
| Uploaded document | `c9670812-55a1-4f49-b8a3-58e7a80d38f6` |
| Owner / project | user `local`; Project `1` |
| Ingestion status | `ready` |
| Vector/chunk | `doc_1db8467369c249cdb5fbe5a23fe1b031`; index `0`, count `1` |
| Namespace | `project:1` |

No fixture content, excerpt, or snippet is persisted in
`contributing_items`; only bounded metadata is retained.

### Browser sequence

1. Thread `10` was opened on the supported frontend with retrieval source
   `Personal Knowledge`, provider Whoosh'd, and logical model `local-chat`.
2. The question asked whether the marked document said the synthetic value had
   meaning outside the qualification, requiring exactly `YES` or `NO`.
3. The active request showed the existing request lifecycle, including waiting
   for first token and working output.
4. Assistant message `51` rendered `NO`; the inner lifecycle reached
   `Completed`, and the composer returned to idle without a reload.
5. The browser was later reloaded after the backend and chat worker restart.
   The full thread reconstructed with `READY`, `ONYX-6807`, and `NO`; the
   composer remained idle. The current supported Compose frontend also showed
   the outer semantic provider status `Provider runtime: Ready`, not `Queued`.

A separate host Vite process was found listening on IPv4
`127.0.0.1:5173` and serving an older design worktree. It was not modified.
Final supported-path re-entry used the Compose listener on IPv6 `[::1]:5173`,
whose served module and semantic status matched current commit
`ae6cc6b308e5fc7a4a28956d5a780e26eeef290b`.

### Terminal and durable truth

| Field | Evidence |
| --- | --- |
| Thread / owner / project | thread `10`; user `local`; Project `1` |
| User message | `50` |
| Task | `2686187b-ee6c-4045-8598-5b9e73805b3b` |
| Provider / model / runtime | `local` / `local-chat` / Whoosh'd |
| Assistant message | `51`; exact durable answer `NO` |
| Redis task lifecycle | `QUEUED -> AWAITING_MODEL -> AWAITING_FIRST_TOKEN -> STREAMING -> COMPLETED -> task.completed` |
| Durable outbox | row `118`, topic `task.completed`, message `51`, same task and thread |
| Assistant retrieval truth | `retrieval_executed: true`; no absence reason |
| Target contributor | document `c9670812-55a1-4f49-b8a3-58e7a80d38f6`, chunk index `0`, Project `1`, lane `project_docs` |
| Equality check | assistant `extra_meta.retrieval_provenance` exactly equals outbox `payload.retrieval_provenance` |
| Scope check | four contributing records, all retained Project `1` document records; `global_documents: 0`; no foreign project/user attribution |

The terminal answer depended on the uploaded fixture: the queried fact was not
present in the thread before user message `50`. PostgreSQL independently proved
message ordering (`46` through `51`), thread ownership, assistant persistence,
and the durable terminal outbox record. Redis independently proved terminal
task execution but was not treated as durable application authority.

## Restart durability

Only `backend` and `worker-chat` were restarted after the decisive completion;
PostgreSQL, Redis, Chroma, and all volumes were preserved. After restart:

- `/health/chat` reported healthy, provider `local`, model `local-chat`, a
  fresh worker heartbeat, and queue depth `0`;
- assistant message `51` still read `NO` on thread `10` for user `local`;
- outbox row `118` still referenced the same task, thread, and message;
- the assistant and outbox provenance objects still compared equal;
- the target document/chunk pair remained present;
- Redis still ended at `COMPLETED` and `task.completed`;
- the uploaded document remained `ready` and its Chroma metadata still mapped
  the same document to vector id `doc_1db8467369c249cdb5fbe5a23fe1b031`,
  chunk index `0`, count `1`; and
- browser reload/re-entry reconstructed the transcript and idle composer.

The frontend process was also restarted to clear its Vite module cache before
the final current-checkout browser read. No service restart removed or rewrote
durable data.

## Finding disposition

| Finding | Disposition | Evidence |
| --- | --- | --- |
| F4 — outer terminal/request projection disagreement | **CLOSED — unchanged** | The current Compose frontend re-entry showed `Provider runtime: Ready`, and no frontend source was changed by this task. |
| F5 — incomplete document/chunk retrieval provenance | **CLOSED** | Focused regression coverage plus live assistant/outbox identity equality, exact target document/chunk attribution, scope exclusion, and restart readback. |
| F7 — static/lifecycle-test findings | **PERSISTS — unchanged** | The focused suites pass; the existing source Ruff ledger and known broad lifecycle-suite failures remain outside scope. |

## ADR impact and invariants

**ADR impact: aligned with ADR-069, ADR-087, and the existing completion,
retrieval, persistence, and runtime-protocol contracts; no ADR change.**

- Existing retrieval policy and ranking remain authoritative.
- Only material marked as retained/injected by existing prompt assembly becomes
  a contributor.
- Document/chunk identities remain scoped to existing project/thread/user
  authority; no global or foreign attribution is synthesized.
- Candidate-only and suppressed records do not become contributors.
- The persisted projection is bounded and metadata-only; no document text,
  chunk content, excerpt, or prompt payload is added.
- Assistant persistence and terminal event publication reuse the same existing
  provenance object and lifecycle.
- No new request state, event transport, database schema, provider selection,
  queue behavior, retrieval widening, or release promise was introduced.

## Documentation follow-through

This proof records the bounded F5 repair and live qualification.
`docs/architecture/00-current-state.md` remains unchanged as required. The
overall supported-Compose posture remains `HOLD` because F7 persists.

The next single prerequisite is F7: reconcile the remaining static and
lifecycle-test reliability findings. This proof does not authorize or begin
that work.
