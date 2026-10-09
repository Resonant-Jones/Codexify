# Loaded native-parent snapshot proof on host CPU — 2026-10-04

## Authority, scope and runtime distinction

Development Operator Level 0, PROOF_REQUIRED, PROOF. Direct human authorization
requires parent-only mutable FAISS, coherent read-only snapshot per bounded
search, preparation within the same accepted deadline, no child additions or
persistence, and fail-closed expiry. ADR-087 governs immutable 720/60 envelopes.
One private Task Spec preceded execution; no production edit or new ADR.

Frozen clean isolated branch `codex/chat-postgres-terminal-deadline-20261003` at
`94db56ca1`, containing repair `1d7d7128f` and the fresh ordinary browser receipt.
The actual-worker native proof held a deferred parent model; the browser does
not independently prove the loaded native-parent snapshot case. This experiment
exercises that case using the existing host Python **3.12.13**, Torch **2.9.0**,
Sentence Transformers **5.2.0**, and FAISS **1.12.0**. Native library versions
match the retained worker; platform and interpreter differ.

The real local model is the same cached directory that backs the worker's
`/models/bge-large-en-v1.5` mount. The parent fixture explicitly loads CPU to
match the worker device; it uses a real `SentenceTransformer`, not fake model or
native calls. Its loader override selects CPU only for that private parent.
Fresh search subprocesses use unchanged production child code and the captured
binding. Offline/local-files-only policy and disabled mock fallback apply.
No download, install, device configuration or model-file change occurred.

This is **macOS CPU mechanism evidence**, not Linux/Docker qualification. It
avoids additional native processes in the Docker VM after the prior overlap
OOM; it does not change VM limits, stop another project, or turn host evidence
into supported-Compose evidence.

## Loaded parent and native result proof

Evidence root:
`/private/tmp/codexify-chat-live-native-parent-94db56ca1-20261004/`.
Task Spec, fixture, driver, stdout/stderr journals, model manifests, process
result, runtime custody and independent validator are retained.

The private parent loads and warms the real native model, embeds inert texts
through production `embed_and_index`, and owns the actual native FAISS index,
text and metadata arrays. Unscoped production search produces reference results.
Accepted production search then forks its owned serializer under the mutation
mutex. The serializer hashes the live parent tensor state and sends its coherent
index/array snapshot through the ephemeral pipe. A fresh child re-loads and
verifies that exact tensor digest, restores and queries the snapshot, and exits.
The parent's loaded model is retained throughout; it is not a deferred handle.

Every full query uses one immutable valid 720/60 envelope aged to 45 seconds
remaining work. Lock, live tensor digest, native index/array serialization,
transfer, child imports/model load, encoding, lookup and return all consume that
original work window. No warmup or preparation is excluded from accepted search.
Parent initialization/reference computation precede the accepted-search fixture.

| Operation | Elapsed seconds | Result |
| --- | --- | --- |
| Warm native parent's first snapshot | 4.921783 | original reference parity |
| Next snapshot after acknowledged parent addition | 4.551556 | updated reference parity |
| Negative account | 5.460194 | no hits |
| Snapshot search with 0.250 s remaining | 0.259323 | canonical deadline, killed/reaped |

Text, keys and metadata match exactly; scores match within `1e-6`. The parent
retains two native index/text/metadata entries and its `SentenceTransformer`.
Expired search returns no result and never falls back to unbounded search.
Elapsed observations include cleanup; they do not establish the exact kernel
stop instant or that forward computation had begun in the short expiry case.

The native parent process **43550**, search children
**43584/43608/43628/43685**, and serializers
**43583/43607/43627/43684** were independently checked absent after reaping.
The whole owned process group is absent. Driver and independent validator exited
zero; no observation ceiling extension, retry or failed native run occurred.

## Preservation, warnings and limits

Model manifests before/after include all regular files under the cached model
directory, with exact lengths and SHA-256 hashes; they match. Runtime source
verification matches all **1,138** Guardian/backend Python files across checkout,
retained snapshot and both application containers. Existing runtime stays
healthy and idle, chat queue zero, locks absent, heartbeat TTL positive,
evaluation/system queues **34/17** unchanged. Thread 37 messages **70/71** retain
exact contents and `extra_meta`. Backend and worker start times/restart counts
remain unchanged; no service/source/configuration/application mutation occurred.
Main stays at `016352131`, with its unrelated staged dev-log deletion preserved.

Python reports its multithreaded-fork deprecation warning; tokenizers reports
that it disables forked parallelism after parent warmup. These warnings are
retained. The tested warmed CPU state succeeds and owned expiry fails closed;
this does not establish safety or parity for every inherited lock/thread state,
GPU/MPS/CUDA model, arbitrary corpus size, Linux loaded-parent concurrency, or
concurrent mutation outside the embedder's canonical methods. No warning was
suppressed or parent threading policy changed to obtain a pass.

## Validation and next obligation

Private driver and independent validator passed; native source and model
manifests, process-group cleanup and retained-runtime custody passed. Local
Markdown link checks, `python3 scripts/validate_docs.py` and `git diff --check`
passed before this scoped docs commit. No additional automated runtime suite
applies to this docs-only receipt. Scoped commit is reported in closeout.

This closes the previously missing host CPU loaded-parent mechanism proof.
It complements actual-worker deferred-native FAISS/Chroma parity and expiry,
and the fresh ordinary browser/durable-readback success after the repair. It
does not close full current-main or supported-Compose failure/recovery gates.
Active-worker-loss orphan authority, terminal reserve/acknowledgement ambiguity,
and complete retry/restart/shutdown qualification remain open. Goal stays
active, qualification **HOLD**; no push, merge, deployment or release promotion.
