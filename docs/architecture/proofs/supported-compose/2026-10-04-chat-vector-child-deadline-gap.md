# Native vector child deadline gap — 2026-10-04

## Task and authority

Development Operator Level 0, `PROOF_REQUIRED`, PROOF mode. The atomic Task
measures the existing vector search child inside production accepted-task
PostgreSQL and Redis scopes. Governing authority is ADR-087: immutable 720/60
work/terminal intervals, every blocking child bounded by its parent, and no new
retrieval after work expiry. ADR-001/002/003/038/069 and the Chat Runtime Contract
preserve acceptance, identity, terminal and release boundaries.

This is aligned proof work, with no new ADR or production repair. Full supported
qualification remains **HOLD**. The clean repair branch began at
`b48465ca41fe52800f507e49dcb89adcb39b732c`. Main and unrelated staged changes
were not touched. No runtime refresh, restart, merge, push or deployment occurred.

## Verified production path

The shared completion service calls `_assemble_context_bundle`, which awaits
`ContextBroker.assemble`. Normal non-shallow thread-first semantic retrieval
reaches `_search_with_widening` and `_search_semantic`.
`ContextBroker._search_semantic` calls synchronous `self.vector.search`.
MemoryOS retrieval also calls this vector seam.

`guardian/vector/store.py::VectorStore.search` forwards to
`backend/rag/embedder.py::LocalSemanticEmbedder.search`. The Chroma branch
calls `_embed_np` (native `SentenceTransformer.encode`) and then the persistent
collection's native `query`. Those production methods neither consume an
accepted work deadline nor interrupt native computation at it. The PostgreSQL
and Redis scopes constrain their own transports, not this child.

The retained worker selects local embeddings with a configured local model,
Chroma at its configured runtime path, and collection
`codexify_vault_supported`. The probe does not substitute a mock model or store.

## Fixture and evidence custody

Evidence root:
`/private/tmp/codexify-chat-vector-deadline-gap-b48465ca4-20261004/`.

The Task Spec preceded execution. Artifacts include exact `probe.py`,
`driver.py`, `validate.py`, stdout/stderr, process result, deadline/result rows,
pre/post health and runtime state, source matrix and independent validation.

The native probe executes in a private subprocess inside the actual retained
worker of Compose project `codexify_chat_branch_proof_896387ad2`, through
`docker exec -i`; no container fixture files were created. Model initialization
uses the configured cached local model outside the measured scopes. Offline
flags in that private process prohibit downloads; a real `SentenceTransformer`
is required. Initialization duration and its own deadline participation are
excluded and remain unqualified.

Adapter fixtures are constructed without their constructors, so they use
`get_collection` on the existing Chroma collection rather than invoking
`get_or_create_collection`. Their production search, encoding and query methods
remain unchanged. A unique non-account proof user and `thread:34` namespace
return zero results without exposing another account's data. No add, delete,
new collection, provider generation, application message, request or attempt
is performed.

The query is ordinary finite text:
`Find supporting notes about ordinary chat runtime reliability.`

Valid 720/60 envelopes are aged using real UTC time; scopes and measurements use
native clocks. There is no fake clock, mocked search, imposed latency or held
child. The same process makes two sequential reads.

## Native observations

| Observation | Work remaining at entry | Child elapsed | Finished after work deadline | Outcome |
| --- | --- | --- | --- | --- |
| Near work expiry | 0.004951 s | 6.382107 s | 6.377039 s | returned, zero hits |
| Work already expired | -0.050045 s | 1.094069 s | 1.144061 s | returned, zero hits |

Neither read raised `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`. The first native
read continued past work expiry. The second began after work expiry and still
executed the native retrieval child. Neither envelope reached terminal expiry;
this proof does not establish a terminal-overrun duration. These measurements
prove the missing vector-child enforcement at this seam, not a production
chat's false-success terminal outcome or a general query latency guarantee.

The PostgreSQL scope switches an already-expired work envelope into its terminal
phase for database cleanup. That is not permission to perform new retrieval;
ADR-087 reserves that interval for terminalization. The vector method does not
consult the work limit at all.

## Verification and preserved state

The driver/native process exited **0**. Independent validation exited **0** and
confirmed both observations, valid result classification, source identity and
retained application state. No fixture retry or production-code change was
needed.

Before and independently after execution, all **1,136** tracked Guardian/backend
Python files matched the repair checkout, retained snapshot, backend container
and worker container. The Chroma collection count was **31** before, after and
on a separate independent read. Both private subprocess handles were terminal
with exit 0; their model/client memory was released by process exit.

Chat queue remained zero, turn locks empty, heartbeat fresh idle with positive
TTL, general health `ok`, and evaluation/system queues **31/11**. Those queues
were preserved. Existing thread 34 still held exact messages **64/65** and the
prior successful assistant marker. No new chat turn was submitted.

Validation commands:

- `python3 /private/tmp/codexify-chat-vector-deadline-gap-b48465ca4-20261004/driver.py` — passed, recording the unenforced deadline observations.
- `python3 /private/tmp/codexify-chat-vector-deadline-gap-b48465ca4-20261004/validate.py` — passed.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

This is a docs-only receipt with native child-runtime evidence; no automated
application regression suite applies. It is not browser, full chat-turn,
restart, shutdown, provider or release qualification.

## Next authorized obligation

A separate repair Task must give this existing native vector read a real finite
child bound, reject new retrieval after work expiry, and retain account/namespace
filters, configured local model authority and actual retrieval capability.
Checking only after a synchronous call returns cannot meet ADR-087. An abandoned
thread with a timed outer wait cannot establish that native work stopped.

Native initialization, Chroma read, and any cleanup must be considered in that
repair; no new execution subsystem or product semantics are approved by this
receipt. Reprove the native seam and then the real supported chat path after
repair. The Goal remains active.
