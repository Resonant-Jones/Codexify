# Native FAISS snapshot parity and interruption — 2026-10-04

## Authority and evaluated source

Development Operator Level 0, PROOF_REQUIRED, PROOF. This atomic prerequisite
follows the human-authorized parent-owned read-only snapshot policy recorded in
[snapshot transfer proof](./2026-10-04-chat-faiss-readonly-snapshot-transfer.md).
The parent remains sole mutable authority; preparation consumes the same
accepted deadline; search children receive snapshots only, without additions,
persistence, parallel authority or unbounded fallback. ADR-087 and the Chat
Runtime/Completion Pipeline identity, model, account and namespace boundaries
govern this proof. No new ADR or release claim.

Clean evaluated branch `codex/chat-postgres-terminal-deadline-20261003` at
`b804bcbeb1003b639c271681610b172ad288e773`. Private Task Spec preceded execution.
Retained project `codexify_chat_branch_proof_896387ad2`, actual worker Python
and installed real FAISS 1.12.0. Existing supported-profile runtime still uses
Chroma; this is a private FAISS mechanism experiment in its worker environment,
not a profile switch or a real accepted application turn.

## Fixture, model binding and parent ownership

Evidence root:
`/private/tmp/codexify-chat-faiss-native-snapshot-b804bcbeb-20261004/`.
Task Spec, source, driver, native journals/results, stderr, source matrix,
before/after state and independent validator are retained. Container Python
receives the fixture through stdin; no container snapshot files were created.

The configured cached model was exactly `/models/bge-large-en-v1.5`, with
`SentenceTransformer` verified in each completed native child. The fresh child
uses the captured model name and `local` backend explicitly; it does not select
another model from current environment. Offline flags and disabled mock
fallback apply. No download or application vector mutation occurred.

A native reference process executes the production `LocalSemanticEmbedder`
initialization, embedding, FAISS indexing and search on inert private texts.
It returns the initial native index, a third native vector and reference query
results, then exits before snapshot searches begin. It is independent reference
indexing, not a bounded search worker receiving addition authority.

The supervisor holds the private native FAISS index, text/metadata arrays and
model binding, but never imports Torch or loads an embedding model. Its private
parent state has the production storage shape; it is not the application's live
shared `VectorStore` instance. A mutex protects native index/array mutations
and coherent fork capture. A serializer child reads its captured copy and
transfers ephemeral bytes through owned pipes, then exits and is reaped. Only
then does a fresh native search child initialize the exact captured model,
restore the snapshot and call production search. Search execution never calls
indexing/addition methods or persists vector state. Only one additional native
model process exists at a time.

## Native results

Each full search uses one valid immutable 720/60 envelope aged to 45 seconds
remaining work. Capture, serialization, pipe transfer, process imports, model
initialization, query encoding, native lookup, filtering and return all consume
that original work window. Successful scores match reference within `1e-6`;
text, keys and metadata match exactly.

| Operation | Elapsed seconds | Result |
| --- | --- | --- |
| Independent native reference | 19.991104 | initial and subsequent reference results |
| Snapshot captured before later parent addition | 4.472242 | two indexed entries, one scoped hit; original-reference parity |
| Next snapshot | 4.577494 | three indexed entries, two scoped hits; subsequent-reference parity |
| Negative account | 4.626697 | zero returned hits |
| Negative namespace | 4.289631 | zero returned hits |
| Startup, 0.250 s remaining work | 0.253087 | killed/reaped, exit -9; no query result |
| Native encoding, 0.020 s remaining work | 0.046172 | real native entry observed, killed/reaped, exit -9; no query result |

Positive and negative full searches returned with approximately 40.37–40.71
seconds remaining work. The parent acknowledged its third addition after the
first snapshot's capture. That snapshot excluded the later addition; the next
included it. The parent retained all three index/text/metadata entries through
the interruption cases, with exact inert text and metadata arrays unchanged.

The narrow encoding case prepares its snapshot, initializes and warms the
model before the separate short fixture window. A forward pre-hook on the first
real Torch Linear module records `native_linear_started` during the actual
query. Computation proceeds normally without injected latency. The parent then
kills/reaps the child when the original short work deadline expires. No
`search_done` or result was returned. This narrow case excludes preparation and
warmup; the full-search and startup cases cover those phases independently.

Cleanup uses the original terminal reserve. Acceptance/work/terminal fields
remain unchanged, with exact 720/60 intervals. Elapsed observations include
termination/reaping and do not claim a precise kernel stop instant. Serializer
and native child PIDs were independently checked absent inside the worker after
reaping; the driver and validator both exited zero.

## Initial fixture failure and independent custody

The first driver exited 1 during read-only preflight, before starting the native
fixture: it selected nonexistent `chat_messages.metadata`. The corrected query
uses canonical `extra_meta`. Initial driver/stdout and preconditions remain in
`initial-*`; corrected execution refreshed the complete preconditions and source
matrix. No service restart or speculative native retry followed an observation
timeout.

Independent validation matched all 1,136 tracked Guardian/backend Python files
across checkout, retained snapshot and both application containers. Application
Chroma count stayed **33**. Thread 36 retained exact messages **68/69**, including
contents and metadata. Chat queue zero, locks absent, fresh idle heartbeat with
positive TTL; evaluation/system queues **33/13** unchanged. General health `ok`,
chat health `healthy`.

Worker restart count remained **0**, with start timestamp
`2026-10-04T17:47:30.036259801Z` unchanged before, after and independently checked.
No runtime source/configuration, migration, application request, attempt,
message, vector, queue entry or service lifecycle was changed by this Task.
Main remained at `0163521312ef767c0884654e70094ae7b44a5eec`, preserving its staged
dev-log deletion.

## Validation, documentation and next obligation

Private `driver.py` and `validate.py` passed. Initial preflight failure is
preserved above. `python3 scripts/validate_docs.py`, local Markdown link checks
and `git diff --check` passed before the scoped documentation commit. No
application regression suite applies to this docs-only receipt; the native
experiment is its proof surface. Scoped commit is recorded in the Task closeout.

This completes native-model/result parity and controlled interruption for the
tested snapshot mechanism. Production search still runs synchronously; this
proof does not implement the authorized policy or close ordinary-chat deadline
qualification. Production coherent capture must cover every addition path and
use the same accepted budget for lock, preparation, transfer, model work and
result decoding. General corpus transfer/parent buffer allocation and native
initialization in accepted constructors remain implementation concerns. The
next atomic task is integration across accepted vector construction and search,
preserving both FAISS parent state and Chroma/model binding, followed by narrow
native proof and a fresh browser/durable-readback turn. Full current-main and
failure/retry/restart/shutdown qualification remains HOLD; the Goal stays active.
