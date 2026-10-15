# FAISS state ownership at the native deadline frontier — 2026-10-04

## Task, authority and scope

Development Operator Level 0, PROOF followed by REPORT. One atomic private
Task Spec preceded the experiment. Evaluated clean repair branch
`codex/chat-postgres-terminal-deadline-20261003` at
`dacaa30aece379b7fd4d8b1d6e966f6c75e7a9af`. Main was independently observed at
`0163521312ef767c0884654e70094ae7b44a5eec` with its existing staged dev-log
deletion preserved.

The chat reliability Goal authorizes investigation and repairs entailed by
accepted architecture, and requires stopping at unresolved semantic decisions.
[Development Operator Goal](../../../Ops/codex-development-operator-goal.md)
requires an Authority Frontier Report when ownership or a new state model is
undetermined. [ADR-087](../../adr/087-accepted-chat-task-execution-deadline.md)
requires immutable 720-second work and 60-second terminal budgets, physical
child bounds, and no new retrieval in the terminal reserve. The
[Chat Runtime Contract](../../chat-runtime-contract.md) and
[Completion Pipeline](../../completion_pipeline.md) retain request, attempt,
message, provider and persistence authority. Main's `00-current-state.md`
continues to report full supported-Compose qualification HOLD.

No application source, accepted contract, ADR, current-state claim, application
record or service configuration changed in this Task. Only this receipt and
private evidence were created. No merge, push, deployment or service restart.

## Fresh source and state evidence

Private evidence root:
`/private/tmp/codexify-chat-faiss-authority-frontier-dacaa30ae-20261004/`.
It contains `task-spec.md`, `probe.py`, `result.json`, `stderr.log`, and an
independent read-only runtime check and its source/health evidence.

Current `LocalSemanticEmbedder` owns `_index`, `_index_dim`, `_texts` and
`_metadatas` in one instance. FAISS additions update native index, texts and
metadata separately; search encodes, searches that index, then filters and
materializes from those arrays. Current `VectorStore` can reuse a matching
shared embedder. Neither implementation contains coherent snapshot transfer,
addition replay or replacement recovery. A copied constructor cannot recreate
the existing FAISS contents. Runtime configuration admits both Chroma and
FAISS; Compose defaults to Chroma, while the supported profile does not
explicitly exclude FAISS. The current ADR index and contracts contain no
accepted FAISS child ownership/transfer/recovery policy. ADR-089 currently
governs bounded Project document recall, not this policy.

The private host experiment used **real FAISS 1.12.0** with the repository's
existing explicitly selected **mock embedding backend**. It performed no
production vector writes, model downloads or latency injection. It proves
instance state ownership only, not SentenceTransformer execution, accepted
deadline enforcement or supported-Compose retrieval conformance.

| Observation | Index / texts / metadata |
| --- | --- |
| Parent after first acknowledged addition | 1 / 1 / 1 |
| Fork at creation | 1 / 1 / 1 |
| Parent after second acknowledged addition | 2 / 2 / 2 |
| Same fork after parent addition | 1 / 1 / 1 |
| Fresh independent replacement instance | 0 / 0 / 0 |

The parent searched the second acknowledged text successfully, with its account
and namespace metadata and score `1.0000001192092896`. A different account
returned no result. All assertions passed. Fork and replacement exited zero;
the parent joined the fork and `subprocess.run` reaped the replacement.
Independent `ps -p 22019,22020` returned no rows (exit 1). An initial sandboxed
process inspection was denied; the permitted read-only inspection succeeded in
establishing absence. The experiment driver itself exited zero.

Independent retained-stack verification matched all **1,136** tracked
Guardian/backend Python files across checkout, snapshot and both application
containers. Health was `ok`; chat queue zero; turn locks absent; heartbeat
idle, TTL 44; evaluation/system queues 33/13. These observations establish
source custody and idle health, not an additional successful user turn.

## Completed work and exact limits

The branch already contains the following relevant completed slices:

- `69090e7f5`: reject vector construction/search admission after accepted work
  expiry, including between legacy fallback calls and workspace reconstruction.
  Host and actual-worker focused checks passed 54 each. This is admission only.
- `f0cfdcce9`: propagate canonical accepted deadline failure through optional
  context/retrieval boundaries. Host and actual-worker checks passed 101 each;
  a native PostgreSQL history stall escaped canonically without subsequent
  retrieval or provider execution.
- `0f03bab57`: controlled native Chroma/model child termination and reaping,
  positive/negative scoped result parity and startup interruption. This was a
  private mechanism proof, not production integration or FAISS recovery proof.
- `dacaa30ae`: one browser turn after admission repair persisted thread 36,
  authored message 68 and assistant 69, matching request/task/turn identities,
  durable completion, Redis event and visible transcript before/after reload.
  All 1,136 runtime files matched. No fallback; explicit local/local-chat.

See the adjacent [admission repair](./2026-10-04-chat-vector-expired-work-admission.md),
[context repair](./2026-10-04-chat-context-deadline-propagation.md),
[native child proof](./2026-10-04-chat-vector-native-child-stop.md), and
[browser proof](./2026-10-04-chat-vector-admission-browser.md) for full validation
and limitations. Earlier unavailable-model and queued-cancel/retry proofs remain
bounded branch evidence. The [active worker crash-loss proof](./2026-10-03-chat-active-worker-crash-loss.md)
still identifies a separate recovery frontier. None closes current-main full
restart/shutdown qualification.

## Authority Frontier Report

**Blocking question:** which policy owns and preserves acknowledged FAISS
index/text/metadata state when physically interruptible retrieval moves across
a process boundary?

Accepted sources already determine identity/scoping, canonical PostgreSQL
authority, immutable child budgets and fail-closed deadline behavior. They do
not determine a coherent snapshot point relative to concurrent additions,
transfer preparation bounds, or replacement state recovery. Killing a child
does not settle those questions. Reconstructing an empty store, keeping a stale
fork, or silently rebinding model/store configuration would not preserve the
required retrieval behavior.

Distinct options requiring human selection:

1. Retain the parent as sole owner of additions; authorize coherent read-only
   per-search snapshots, with preparation and transfer inside the original
   accepted work budget. A killed search child cannot discard parent state.
   This is the smallest proposed policy; coherence, native model binding and
   bounded preparation still require proof before implementation acceptance.
2. Authorize a persistent vector worker owning additions and searches, with
   explicit acknowledged-write replay and replacement recovery. This adds a
   larger state/coordination boundary and requires a separate architecture task.
3. Defer FAISS integration and keep full native deadline qualification HOLD.
   Chroma-only mechanism evidence cannot qualify the unchanged FAISS path.

A decision affects context assembly, embedding/model initialization, vector
add/search ownership, account/namespace result isolation, deadline cleanup and
worker memory use. No policy was accepted or implemented by this report. The
smallest unlocking decision is option 1's ownership and snapshot authorization;
it is a recommendation, not approval. The human question was presented with
these options. The Goal remains active pending that decision and broader gates.

## Validation and documentation follow-through

- Private `PYTHONPATH="$PWD" .../.venv/bin/python .../probe.py`: passed, exit 0;
  real FAISS ownership and account-negative assertions, both children reaped.
- Independent runtime `runtime-check.py verify`: passed, exit 0; 1,136 matches
  and retained health/queue observations above.
- `python3 scripts/validate_docs.py` and `git diff --check`: passed before
  committing this receipt. All local Markdown links in this receipt resolved.
- No automated application runtime suite applies to this docs-only change.
  Private state assertions are not full runtime qualification.

Documentation follow-through is this proof/frontier receipt. Current-state and
ADR changes are deferred to human selection and qualifying evidence. No new
ADR; no release claim change; no memory update. Scoped commit recorded in the
Task closeout. Main's unrelated staged deletion remains untouched.
