# Accepted vector initialization deadline gap — 2026-10-04

## Scope and authority

Development Operator Level 0, `PROOF_REQUIRED`, PROOF. This is a controlled
native initialization observation, not a production repair or chat turn.
ADR-087 forbids starting retrieval child work after accepted work expiry and
reserves the remaining 60 seconds for terminalization. ADR-001/002/003/038/069,
Chat Runtime Contract and Completion Pipeline preserve acceptance, identity,
provider and release boundaries. No new ADR or runtime token is introduced.

The clean evaluated branch was
`codex/chat-postgres-terminal-deadline-20261003` at
`3799de4cef2f6288901148adc315757b20c25607`. Main and its staged Dev Log deletion
were untouched. No production source/configuration edit, container restart,
refresh, merge, push or deployment occurred. Full qualification remains HOLD.

Fresh evidence root:
`/private/tmp/codexify-chat-vector-initialization-gap-3799de4ce-20261004/`.
Task Spec preceded execution. Exact probe/driver/validator, stdout/stderr,
result, process, source matrix, health, queue, worker lifecycle and retained
message readbacks are preserved there.

## Why this changes the repair scope

The preceding [native vector child stop proof](./2026-10-04-chat-vector-native-child-stop.md)
proved bounded initialized Chroma reads and one full child lifecycle. It did
not integrate those bounds into production or inventory every constructor
reachable before search. Current code adds these obligations:

| Surface | Current code-path evidence | Repair requirement |
| --- | --- | --- |
| Worker service startup | `_initialize_worker` calls `dependencies.init_services` before task handling | Keep startup distinct from accepted task work; preserve shared runtime binding |
| New VectorStore | Constructor resolves runtime, reuses matching shared embedder or initializes one synchronously | Admission and initialization must inherit accepted work bounds when reached inside a task |
| Workspace completion | `_workspace_completion_vector_store` constructs VectorStore and explicitly reconstructs `backend.rag.embedder.Embedder` | Bounding search alone leaves fresh model/store initialization outside enforcement |
| Workspace reconstruction errors | Fresh-embedder broad catch keeps the previous store | Canonical expiry must propagate, rather than become optional reconstruction fallback |
| Existing local model binding | Embedder records model name, configured backend, store/path/collection | Child must inherit effective binding; current environment cannot silently replace an already-selected model |
| Local initialization recovery | `_recover_local_model_once` can attempt download and reload on cache miss | All reachable attempts need the same deadline; this proof does not exercise cache miss or authorize new egress |
| FAISS | `_index`, `_texts`, `_metadatas` are live in-memory instance state | A fresh child cannot reconstruct an empty index and claim equivalent retrieval; snapshot/native ownership requires explicit proof |

These are code-path findings, not proof that every ordinary turn uses workspace
scope or FAISS. The supported project exercised here is local Chroma. The
previous browser turn selected Project retrieval and completed successfully.
No parent-thread abandonment or silent empty-result substitution satisfies
the native stop or retrieval capability requirements.

## Native result

One private process on the actual retained worker imported production
`guardian.vector.store.VectorStore`. Its private shared store was absent, so
construction necessarily initialized a real model. It verified the configured
existing Chroma collection first, then entered canonical PostgreSQL and Redis
accepted scopes with a valid immutable 720/60 envelope aged **0.05 seconds past
work expiry**. No clocks, native work or latency were mocked.

`VectorStore()` returned a **SentenceTransformer** in **0.161010 seconds**.
Remaining work was **−0.050043 seconds** at entry and **−0.211301 seconds** at
return. The canonical deadline exception was not raised. Model name matched
configured `LOCAL_EMBED_MODEL`; runtime store/path/collection matched canonical
resolution. No search, provider, application message/request/attempt or vector
add/delete was invoked.

The PostgreSQL scope correctly classified its remaining interval as terminal.
That is database cleanup permission, not permission for new native retrieval
initialization. The vector constructor did not consult the expired work limit.
The original accepted/work/terminal timestamps remained unchanged.

Imports and existing-collection preflight occurred outside the narrow measured
accepted window. This proves initialization admission after expiry, not a
worst-case model-load duration or interrupted native constructor. The 45-second
observation ceiling was not application enforcement; the measured constructor
returned well inside it. The native process was observed through the same live
handle until actual exit, with no retry or timeout-triggered restart.

## Independent validation and preserved state

Native driver/process handle **53035 exited 0**. Container-owned probe PID 513
was independently absent after reaping. Validator handle **57569 exited 0**.
Worker restart count and start timestamp matched before, after and independently;
no new worker interruption occurred.

All **1,136** tracked Guardian/backend Python files matched checkout, retained
snapshot, backend and worker before and independently after the probe. Migration
remained `d4c69e03a712`. Existing Chroma count was **32 before and after**, confirmed
again by an independent native collection read. This is the current count, not
the older proof's 31-entry observation.

Thread 35 messages **66/67**, content and metadata matched their preflight JSON
readback. Chat queue stayed zero; locks were absent; evaluation/system queues
stayed **32/12**. Independent final heartbeat was idle, age 2.107 seconds and
TTL 44. General/chat health were `ok`/`healthy`; the admitted
`v1-local-core-web-mcp` profile was valid with no mismatches. No queue was cleared.
The probe created no container fixture files, links or browser/Vite resources.

Validation:

- `python3 /private/tmp/codexify-chat-vector-initialization-gap-3799de4ce-20261004/driver.py` — passed, recording the violation rather than declaring conformance.
- `python3 /private/tmp/codexify-chat-vector-initialization-gap-3799de4ce-20261004/validate.py` — passed: measured violation, immutable envelope, native process absence, source identity and retained runtime state.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

No new automated repository runtime suite applies to this docs-only proof.
Validation success means the observation is verified; deadline conformance is
still false on this native initialization path.

## Next obligation and limits

The production repair must reject new initialization/search after work expiry,
physically bound initialization and native reads inside the original envelope,
retain effective model/store and account/namespace authority, preserve live
FAISS contents where applicable, and propagate canonical deadline failure
through workspace construction and context assembly. A search-only wrapper
would leave the newly proved constructor gap reachable. Expiry-admission checks
alone would still leave native work started before expiry unbounded.

This Task proves the narrow constructor gap and resolves the next repair's
entry-point inventory. It does not implement the child boundary, prove native
stop during constructor execution, or qualify full browser/failure/recovery,
current-main integration, restart or graceful shutdown. Goal active; HOLD.
