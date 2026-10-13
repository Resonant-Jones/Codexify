# Native vector child stop prerequisite — 2026-10-04

## Scope and authority

Development Operator Level 0, `PROOF_REQUIRED`, PROOF mode. This Task completes
the native process-ownership observation left incomplete in
`2026-10-04-chat-owned-vector-child-proof.md`. It does not implement the repair
for `2026-10-04-chat-vector-child-deadline-gap.md`.

Governing sources: ADR-087 (immutable 720/60 envelope, child bounds and terminal
cleanup), ADR-001/002/003/038/069, and the Chat Runtime Contract. This is aligned
proof work, with no new ADR, subsystem, daemon, queue, execution authority or
release claim. Full qualification remains **HOLD**.

The clean repair branch began at `27283a8e016ffdef5a234ea3a7c9512d3dbd122c`.
Production source/configuration, migrations and main were unchanged. Main's
unrelated staged Dev Log deletion remained untouched. No operator restart,
merge, push or deployment was issued.

## Corrected fixture and custody

Fresh evidence root:
`/private/tmp/codexify-chat-vector-child-native-stop-27283a8e0-20261004/`.

The Task Spec preceded execution. Exact probe, driver, validator, stdout/stderr,
process/result, native phase journals, source matrix, container lifecycle,
health, queue and independent-validation artifacts are retained. The previous
failed proof artifacts remain unchanged in their original root.

The supervisor does not import Torch or hold an embedding model. A native
reference query runs in a separate process that exits before the next child
starts. Only one additional native child exists at a time. This removes the
previous fixture's simultaneous private parent/child model allocation.

Readiness uses raw `select`/`os.read` with one absolute 45-second ceiling. It does
not mix a buffered text reader with descriptor readiness. No waiting ceiling
was increased and no failed case was automatically retried.

The probe executes through `docker exec -i` in the retained supported worker of
`codexify_chat_branch_proof_896387ad2`; it creates no container fixture files.
Children select the configured cached `LOCAL_EMBED_MODEL`, require a real
SentenceTransformer, prohibit downloads and use `get_collection` on the
existing Chroma collection. No fallback or new collection is used.

Each query calls the unchanged production `VectorStore.search`, embedder search,
encoding and native Chroma query. The positive query uses the canonical owner
of thread 34 and namespace `thread:34`; the negative uses a non-account proof
identity. Raw account IDs and retrieved content are not reported. No vector
add/delete, provider generation, message, application request or attempt occurs.

## Native observations

| Operation | Total elapsed seconds | Outcome | Exit / state after reap |
| --- | --- | --- | --- |
| Native reference outside accepted scope | 10.744418 | one positive hit | 0 / absent |
| Full child, 45 s remaining work | 6.459319 | positive result matched reference | 0 / absent |
| Negative account, 45 s remaining work | 3.787199 | zero hits | 0 / absent |
| Startup, 0.25 s remaining work | 0.252900 | timeout, kill and reap | -9 / absent |
| Native encoding, 0.020 s remaining work | 0.045739 | timeout, kill and reap | -9 / absent |

Positive keys, text, metadata and count matched the native reference exactly;
scores matched within relative/absolute tolerance `1e-6`. Both full scoped
children completed inside their existing work window, covering imports, model
initialization, collection open, encoding, query and process return. Their
remaining work time at return was approximately 38.541/41.213 seconds.

The startup-expiry child was physically killed and reaped. For the separate
native-encoding case, the diagnostic child initialized and warmed the model
before the short accepted fixture window. A forward pre-hook on the first real
Torch Linear module recorded `native_linear_started` during the subsequent
actual query. The computation proceeded normally with no imposed latency or
mocked native operation. The parent timeout then killed/reaped the process;
no query result or search completion was returned and the PID was absent.

The 0.045739-second observation includes process termination and reaping after
the 0.020-second work window. Cleanup uses the original terminal reserve; no
new work budget is minted or refreshed. This is not a claim about the exact
kernel instant at which every native thread stopped. Startup/warmup are excluded
from that narrow encoding case, and are covered separately by the full-child
and startup-expiry observations above.

## Independent verification and retained state

The native probe/driver exited **0** and the independent validator exited **0**.
There were no fixture failures or retries in this Task. The validator confirmed
all five observations, meaningful positive parity, negative account isolation,
physical process absence and retained runtime state.

All **1,136** tracked Guardian/backend Python files matched checkout, retained
snapshot, backend container and worker container before and independently after
execution. Chroma still held **31** entries. Thread 34 still held messages
**64/65** and the prior successful assistant marker.

Chat queue remained zero, turn locks empty, heartbeat fresh idle with positive
TTL, evaluation/system queues **31/11**, general health `ok` and chat health
`healthy`. No unrelated queue was cleared or dequeued. The final worker process
inventory contained only the application Python process.

Worker restart count remained **1**, with the identical start timestamp
`2026-10-04T16:37:00.254120509Z` before, after and at independent validation.
No new interruption occurred. The prior unexpected restart's cause remains
unknown; this successful run does not diagnose or erase that historical failure.

Validation commands:

- `python3 /private/tmp/codexify-chat-vector-child-native-stop-27283a8e0-20261004/driver.py` — passed.
- `python3 /private/tmp/codexify-chat-vector-child-native-stop-27283a8e0-20261004/validate.py` — passed.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

No automated application regression suite applies to this docs-only receipt.
The proof class is controlled native child-runtime evidence, not full chat,
browser, restart, shutdown, provider or release qualification.

## Next obligation

Compile the production repair separately. It must retain configured model and
store authority, account/namespace filters and actual retrieval capability;
cover child launch, I/O, initialization, native work and cleanup with the
original envelope; reject retrieval after work expiry; and propagate deadline
failure through context assembly without replacing it with optional-context
success. Other configured stores and initialization paths need explicit review.

This receipt proves the tested local Chroma child mechanism, not its integration
into accepted tasks. The existing native vector deadline gap remains open until
that repair and the real supported chat path are requalified. The Goal stays
active and qualification remains HOLD.
