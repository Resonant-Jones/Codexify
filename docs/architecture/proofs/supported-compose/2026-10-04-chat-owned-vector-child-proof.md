# Owned vector child prerequisite — incomplete proof, 2026-10-04

## Task and authority

Development Operator Level 0, `PROOF_REQUIRED`, PROOF mode. This atomic
prerequisite investigates process ownership for the native vector deadline gap
proved in `2026-10-04-chat-vector-child-deadline-gap.md`. It does not implement
a repair or qualify a production mechanism.

ADR-087 requires every blocking child to inherit the immutable 720/60 envelope,
prevents new retrieval after work expiry, and reserves terminal time for bounded
cleanup. ADR-001/002/003/038/069 and the Chat Runtime Contract preserve identity,
model authority, persistence and release boundaries. No new ADR, runtime
subsystem, queue, daemon or authority is approved by this proof.

The Task began on clean repair commit
`79bc12324ce994d95de9dc6689fe018b0aaa77af`. Production source, configuration,
migrations and main were not changed. No operator restart, merge, push or
deployment was issued. Full supported qualification remains **HOLD**.

## Fixture and evidence

Evidence root:
`/private/tmp/codexify-chat-vector-owned-child-79bc12324-20261004/`.

The Task Spec preceded execution. Exact initial and diagnostic probe/driver
sources, stdout/stderr and process results are retained. Additional artifacts
record phase observations, container state, memory observation, the queried
Docker event result, source matrix and independent partial validation.

A private process in the retained supported worker loads its configured cached
real local SentenceTransformer and reads the existing Chroma collection. Its
control query uses the canonical owner of thread 34 and namespace `thread:34`.
Fresh owned children restore that model name and existing collection, then call
the unchanged production `VectorStore.search`/embedder encoding/query methods.
Offline flags prohibit downloads; no fallback or new collection is used.
The native query is `CHAT_INDEPENDENT_HEARTBEAT_SUCCESS_20261004`.

Only result parity digests/receipts are eligible for reporting; private account
IDs and retrieved content are not emitted in the transcript. No vector add or
delete, provider generation, message, application request or attempt is created.

The parent supervises complete children with one valid accepted envelope aged
to 45 seconds remaining work. Startup expiry uses 0.25 seconds remaining.
The separate native-encoding fixture loads a diagnostic child outside a 0.020
second work window, to isolate physical interruption of native encoding. That
last fixture's startup is explicitly excluded; its proof did not finish.

## Verified diagnostic observations

| Operation | Elapsed seconds | Result | Child state after reap |
| --- | --- | --- | --- |
| Positive scoped read | 6.033822 | returned inside work window | absent, exit 0 |
| Negative account scope | 4.678562 | returned inside work window | absent, exit 0 |
| Startup expiry | 0.252983 | killed at deadline | absent, exit -9 |

The positive result matched the native control's keys, text, metadata and result
count; scores were checked with relative/absolute tolerance `1e-6`. The control
had at least one hit. The negative account returned zero hits. Those assertions
completed before the logged startup-expiry operation. Phase journals establish
model initialization, collection open and completed search for both successful
children. The startup-expiry child emitted only its import-start phase; it did
not begin search.

These are native mechanical observations, not full chat, terminal/UI, restart,
shutdown or release proof. Production repair still needs its own tests and real
supported-path requalification.

## Failures and unexpected worker restart

The initial fixture exited **1** after its negative-scope child exceeded the
45-second window and returned the timeout disposition. The fixture then treated
that absent result as a successful response and raised `TypeError`. Its exact
source/stdout/stderr/process files remain under `initial-*`. No native phase
journal was available to locate that first timeout; its cause is unknown.

A diagnostic fixture retained the same 45-second bound and added native phase
journals. It verified the three operations above, then ended with **exit 137**
before producing the final native-encoding cancellation result. During that
run the worker container stopped at `2026-10-04T16:36:58.184305258Z` and resumed
at `2026-10-04T16:37:00.254120509Z`. Docker reports restart count **1**. The
backend, PostgreSQL and Redis did not restart in that interval.

The restart cause is **unknown**. Current worker state reports `OOMKilled=false`
and running/exit 0 after recovery. The queried historical Docker event window
returned no events. Neither fact establishes the cause of the previous exit;
exit 137 alone is not an OOM diagnosis. No operator restart command was issued.

The fixture holds its own parent model and an additional child model alongside
existing services. That adds native model memory and makes resource pressure a
hypothesis to investigate, not a proven cause. The later Docker memory
observation shows an approximately 7.75 GiB VM; worker/backend usage was about
549/521 MiB after recovery. These are post-event observations, not peak-memory
measurements.

The diagnostic pipe reader also mixes `select` with buffered text `readline`.
Code inspection identifies a possible buffered-readiness observation error to
fix before any further probe. It does not establish that this caused exit 137
or the worker restart. Model-heavy trials stopped after the interruption.

## Independent state validation

The independent partial validator verifies the three logged mechanical
observations while explicitly keeping `task_acceptance_met=false` and
`native_encode_cancellation_proven=false`. Its corrected run passed. The first
validator exited 1 because `docker top -eo comm` omitted the PID column Docker
requires; its original source and error receipt are retained. That was a
read-only inventory failure; no probe was rerun or cleanup mutation repeated.

After the interruption, all **1,136** tracked Guardian/backend Python files
still matched the repair checkout, retained snapshot and both containers.
The existing Chroma collection count remained **31**. Thread 34 still held
messages **64/65** and the prior successful assistant marker.

Chat queue remained zero, turn locks empty, heartbeat fresh idle with positive
TTL, evaluation/system queues **31/11**, general health `ok` and chat health
`healthy`. The final worker process inventory contained only the application
Python process; no private probe or child remained. This verifies retained
state after an idle-worker interruption; it proves no active-task recovery or
ordinary new chat after restart.

Validation:

- Initial native driver — **failed, exit 1**; first timeout cause unknown.
- Diagnostic native driver — **interrupted, exit 137**; worker restart cause unknown.
- `python3 /private/tmp/codexify-chat-vector-owned-child-79bc12324-20261004/validate-partial.py` — passed after inventory-fixture correction, validating partial evidence and retained state only.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

No automated application regression suite applies to this docs-only receipt.
The Task's full acceptance criteria were **not met**. Native encoding
interruption and a production vector-bound mechanism remain unqualified.

## Next obligation

Resolve the private fixture's extra model allocation and readiness-reader
limitations before further model-heavy qualification. Preserve the original
budget and account/model parity requirements. Investigate the unexplained
worker interruption without treating current health as proof of its cause.
Then independently prove native operation interruption and compile the bounded
production repair. The Goal remains active, with the original vector deadline
gap still open and full qualification HOLD.
