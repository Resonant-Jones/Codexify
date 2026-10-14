# Accepted vector construction and snapshot search deadline — 2026-10-04

## Authority and evaluated change

Development Operator Level 0, AUTHORIZED_IMPLEMENTATION, EXECUTE then PROOF.
The human authorized the parent FAISS instance as sole mutable authority,
a coherent read-only snapshot per bounded search, preparation within that same
accepted deadline, no child additions or persistence, and deadline failure
without an unbounded fallback. The private Task Spec preceded implementation.
ADR-087 and the Chat Runtime/Completion Pipeline govern the existing 720-second
work window and 60-second terminal reserve, identity and model boundaries.
This implements that policy; no new ADR or release claim.

Frozen repair branch `codex/chat-postgres-terminal-deadline-20261003` at
`19f8d2436251ef22de6c86e6979dd91e030a1416`. Main remains at
`0163521312ef767c0884654e70094ae7b44a5eec`, preserving its unrelated staged
`docs/DEV_LOG/2026-10-04/Dev Log - 2026-10-04.md` deletion.

## Implementation and ownership

`LocalSemanticEmbedder` routes accepted construction and search through owned
native child processes. Unscoped startup and indexing retain parent authority.
Accepted construction initializes and verifies the actual selected model inside
its bounded child and leaves a deferred parent handle. Later unscoped parent
indexing materializes that exact binding. Accepted native indexing fails closed.
Canonical startup still owns Chroma collection creation; a bounded child opens
an existing collection only.

All FAISS index, text and metadata additions/resets share a parent mutex with
snapshot capture. Capture forks a read-only serializer while holding that mutex;
subsequent additions remain in the parent. The serializer transfers the captured
index and arrays directly to a fresh search process through an ephemeral pipe.
The parent does not copy or serialize the corpus. The search child restores and
queries that view, returns scoped results, and exits; it has no addition or
vector persistence protocol. The next search captures subsequent acknowledged
parent additions.

The child preserves the actual backend, model, device, prompt settings,
sequence length, truncation, normalization and account/namespace filtering.
Because the retained model directory is writable, native tensor weights are
attested inside the owned serializer or initialization child. Re-loading a model
with different weights fails closed rather than silently changing authority.
A deferred unscoped parent load preserves the parent's fallback environment.
Unsupported live model classes fail closed.

Lock acquisition, snapshot preparation/transfer, process startup, model load,
encoding, lookup and result return consume the original accepted work end.
Neither phase receives a fresh relative deadline. Expiry raises the canonical
`AcceptedChatTaskDeadlineExceeded`; child termination/reaping uses the original
terminal reserve. No background search thread or unbounded fallback is left
running. Existing workspace and context exception propagation needs no change.

Changed files: `backend/rag/embedder.py`,
`guardian/core/chat_postgres_deadline.py`,
`guardian/vector/accepted_deadline.py`,
`guardian/vector/accepted_child.py`,
`tests/vector/test_vector_physical_deadline.py`, and this receipt.

## Focused validation and preserved failures

Private evidence root:
`/private/tmp/codexify-chat-vector-physical-bound-19f8d2436-20261004/`.
Task Spec, initial failures, exact copied test manifests, JUnit, native fixture,
source matrices and lifecycle/data readbacks are retained there.

Final host and actual retained-worker executions each passed **37 tests**, with
zero failures, errors or skips. Command surface:

```text
python -m pytest tests/vector/test_vector_physical_deadline.py tests/vector/test_vector_accepted_work_admission.py tests/vector/test_vector_store_resolution.py tests/core/test_context_deadline_propagation.py -q --junitxml=<private evidence XML>
```

Host uses the existing repository virtual environment; worker uses its installed
Python and copied, hash-verified tests with an owned private pytest directory.
The nine new tests cover actual child reaping, admission before native startup,
accepted/unscoped parent addition authority, concurrent coherent snapshot and
next-search visibility, account/namespace negatives, original envelope retention,
lock expiry, constructor/search expiry, Chroma parity, failed-fork descriptor
closure, and changed native tensor rejection without environment mutation.

Initial baseline selection exposed an inherited FAISS regression fixture that
omits the required `user_id`; the exact frozen backend reproduces that failure.
It was not changed. An initial worker fixture put three independent searches
inside one artificially aged 30-second envelope; its final control correctly
expired. Independent controls now receive separate immutable fixture envelopes.
No production deadline was extended. Initial source and failure outputs remain.

Final helper/core/test Ruff checks, targeted `compileall` and `git diff --check`
passed. The backend's existing unused `hashlib` lint finding is outside scope.
Worker emits inherited FAISS SWIG deprecation warnings.

## Runtime custody and qualification boundary

The retained project is `codexify_chat_branch_proof_896387ad2`, using its existing
local model and Chroma supported-profile configuration. Three explicitly scoped
idle source refreshes copied only the four production files above, then two
helpers for tensor attestation, then one helper for parent environment
preservation. Each verified the previous source matrix, idle chat queue/locks,
service health and expected lifecycle before/after; no queue was cleared.
All **1,138** tracked plus new Guardian/backend Python files match checkout,
retained source and both application containers. System queue moved **13 to 16**
from the three startup events; evaluation queue remained **33**. Application
Chroma remains **33** entries and thread 36 retains exact messages **68/69**,
contents and `extra_meta`. The final worker start timestamp is
`2026-10-04T21:34:16.858728583Z`, restart count **0**.

Native mechanism and recovery validation are recorded below. This repair does not itself prove an ordinary browser
turn or full failure/retry/restart/shutdown behavior. A fresh browser turn and
durable readback is a separate next Task, including the live parent-model
capture path. Current-main integration and full qualification remain **HOLD**;
the ordinary-chat reliability Goal stays active. No main edit, push, merge,
deployment, model installation or download is authorized or performed.


## Native production-path proof and runtime custody failure

The actual retained worker ran the production boundary with installed FAISS
and cached `SentenceTransformer` model `/models/bge-large-en-v1.5`. An independent
reference process used inert private native vectors and existing application
Chroma reads; it exited before bounded production children began. The private
parent retained a real FAISS index and a deferred model binding, with three
index/text/metadata entries after its acknowledged addition. It did not own a
loaded native embedding model during this probe.

Each full operation uses a valid immutable 720/60 envelope aged to 45 seconds
remaining work. All preparation and native work consume that same work window.

| Operation | Elapsed seconds | Result |
| --- | --- | --- |
| Native FAISS construction | 15.085596 | deferred actual model binding, tensor digest verified |
| FAISS snapshot search | 5.368832 | original native reference parity |
| Next snapshot after parent addition | 6.131433 | updated native reference parity |
| FAISS negative account | 5.368943 | no hits |
| FAISS search with 0.250 s remaining | 0.253156 | canonical deadline, killed/reaped |
| Native constructor with 0.250 s remaining | 0.253733 | canonical deadline, killed/reaped |
| Native Chroma construction | 6.377163 | existing collection, deferred verified model |
| Native Chroma search | 6.333089 | original native reference parity |
| Chroma negative account | 7.344567 | no hits |

Scores matched within `1e-6`; keys, texts and metadata matched exactly. Native
child PIDs `424,435,452,469,486,490,494,513,544`, serializer PIDs
`434,451,468,485` and reference PID `390` were independently verified absent
inside the worker. The startup expiry cases prove bounded startup cleanup;
they do not establish that native forward computation had begun at expiry.
The preceding native snapshot receipt separately proves controlled active
encoding interruption. The live already-loaded parent-model digest capture
path still requires the ordinary application turn proof.

The first native reference was run concurrently with focused worker tests and
exceeded its 45-second fixture ceiling before reaching the production boundary.
It was killed/reaped; the failed source, stdout/stderr and process result remain
in `initial-*`. Running the same unchanged ceiling in isolation with phase
telemetry completed native reference indexing/search and the production checks.
No accepted deadline or reference ceiling was extended.

Independent custody validation nevertheless failed: Docker reported that the
backend was OOM-killed at `2026-10-04T21:43:00.698823545Z`, exit **137**, during
the earlier overlapping run. The isolated mechanism probe therefore ran with
that backend stopped. This is a material failed runtime-preservation check,
not a successful full-runtime qualification. Other running projects were
observed but not modified; no host/VM limit was changed.

After confirming chat queue zero, locks absent and fresh idle worker heartbeat,
the existing backend was started without changing source, configuration or
application records. Its new start timestamp is
`2026-10-04T21:47:17.506339553Z`; worker lifecycle remained unchanged. Independent
post-recovery validation passed: all 1,138 source files match in both running
containers, general health `ok`, chat health `healthy`, canonical migration
`d4c69e03a712`, application Chroma **33**, exact thread 36 messages preserved,
chat queue **0**, locks absent, positive idle heartbeat TTL, evaluation queue
**33**. System queue **17** includes the additional backend startup event.

The final eight copied test-source hashes were verified against their manifest.
Their exact owned directory `/tmp/codexify-vector-physical-bound-31f492d8` was
removed only after XML/log/source custody, then independently verified absent.
Native driver exit **1** is retained for the custody failure; the independent
mechanism/recovery validator exited **0**. No retry or application request was
submitted, no queue cleared, and no unrelated container was stopped. Fresh
ordinary-chat proof must account for the observed memory pressure; this receipt
makes no conformance or release claim for simultaneous native work under it.
