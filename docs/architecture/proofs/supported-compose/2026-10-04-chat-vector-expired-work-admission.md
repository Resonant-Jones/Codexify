# Native vector expired-work admission repair — 2026-10-04

## Change and authority

Development Operator Level 0, `AUTHORIZED_IMPLEMENTATION`, EXECUTE/PROOF.
ADR-087 forbids new retrieval work after the immutable accepted work deadline;
its terminal reserve cannot fund replacement work. Chat Runtime Contract,
Completion Pipeline and ADR-001/002/003/038/069 preserve identity, acceptance,
provider and evidence boundaries. This repair aligns with those contracts;
no new ADR, runtime token, queue, model/store selection or persistence policy.

The preceding [native initialization proof](./2026-10-04-chat-vector-initialization-deadline-gap.md)
showed real VectorStore construction starting after expiry and returning a
SentenceTransformer. This atomic prerequisite now rejects that admission:

- `guardian/core/chat_postgres_deadline.py` exposes a work-admission check over
  the worker's existing anchored scope. It reads the original `work_end`,
  regardless of database terminal mode, and creates no replacement budget.
- `guardian/vector/store.py` checks before construction, directly before native
  embedder creation, and before search and each legacy search fallback. Both
  Chroma and FAISS retain their current model, contents and account/namespace
  behavior for admitted or unscoped operations.
- `guardian/core/chat_completion_service.py` checks before fresh workspace
  embedder construction and rethrows the exact canonical expiry exception
  rather than treating it as optional reconstruction failure.
- `tests/vector/test_vector_accepted_work_admission.py` verifies those boundaries,
  invalid snapshots, terminal-reserve exclusion, scope restoration, unchanged
  ordinary results/filter authority and unchanged non-deadline optional errors.

Started from clean `3fa5b9b70b3de01b05c4f54667972db1f9c1db2f` on
`codex/chat-postgres-terminal-deadline-20261003`. Main and its unrelated staged
Dev Log deletion were untouched. No merge, push or deployment occurred.

## Regression evidence

Fresh private evidence root:
`/private/tmp/codexify-chat-vector-expired-admission-3fa5b9b70-20261004/`.
The Task Spec preceded tests and production edits. Source-before copies,
baseline/final logs/XML, lint comparison, runtime refresh/source matrix,
native probe/result, cleanup and independent readback are retained.

Initial host baseline: **11 checks, eight failures, three passes**, zero
errors/skips. The first repair passed **51** focused checks. Three additional
regressions cover actual expiry between legacy signature calls and expiry
between runtime resolution and native initialization. Final result: **54 host
passes**, zero failures/errors/skips. Actual worker old-source baseline with
all new regressions: **14 checks, 11 failures, three passes**, zero errors/skips.
After the scoped refresh: **54 actual worker passes**, zero failures/errors/skips
in 5.917 seconds.

Host command from repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest tests/vector/test_vector_accepted_work_admission.py tests/vector/test_vector_store_resolution.py guardian/tests/test_vector_store_namespace.py tests/core/test_context_deadline_propagation.py tests/core/test_chat_completion_service_source_mode_fallback.py -q
```

The same five test files plus three exact helpers were copied to the owned
worker fixture and run against actual worker source. The timing regressions
use short real sleeps to cross the admission boundary; they do not claim to
prove physical interruption of a native operation. The native reproof below
uses no mocked clock, latency or native operation.

## Actual worker reproof

At chat queue zero, no locks and fresh idle heartbeat, exactly the three changed
runtime files were copied into the retained snapshot. Backend and worker were
restarted once. All **1,136** tracked Guardian/backend Python files matched the
checkout, snapshot and both containers before and after refresh and again at
independent final validation. Migration stayed `d4c69e03a712`.

A private actual-worker probe repeated the prior constructor case with a valid
720/60 envelope aged 0.05 seconds past work expiry. An observation wrapper on
`Embedder._init_embedding_model` delegates to the real function if entered;
it recorded **zero entries**. `VectorStore()` raised the canonical
`CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` in **0.000069416 seconds**. Remaining work
at entry was **−0.050063 seconds**. The original envelope was unchanged.
Completion truth remained accepted true, attempted/fallback_attempted/executed/
completed false. No model, query, provider or application turn was created.

Chroma count was **32 before and after**. Thread 35 messages **66/67**, content
and metadata matched preflight readback. Evaluation queue stayed **32**;
system queue changed **12→13** from backend startup warmup and was retained.
Chat queue stayed zero, locks absent, general/chat health `ok`/`healthy`.
Independent final heartbeat was idle, age 5.269 seconds, TTL 40.

Native probe handle **30763 exited 0**. Its container PID 56 was independently
absent after reaping. Worker lifecycle was unchanged during the probe. Eight
copied test/helper files were hash-verified before removing the exact owned
folder `/tmp/codexify-vector-admission-19083f7b`; independent absence passed.
No native fixture files, frontend links or browser resources remain.

## Other validation

- Runtime setup/baseline, final and source verification — passed; baseline
  pytest failure is expected regression evidence and retained explicitly.
- Native reproof and independent final readback — passed.
- Ruff baseline/current comparison — **15 inherited shared-service findings,
  zero new findings**. The vector, deadline and new test files have no findings.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

Only task-scoped runtime/test/receipt files are staged. Broader inherited lint
was left outside this task. Documentation follow-through is this receipt;
release/current-state claims are not promoted.

## Remaining requirement

This closes zero-new-vector-work admission after expiry, including workspace
construction and legacy fallback calls. It does **not** physically interrupt
native initialization/encoding/store work admitted before expiry. The original
[native search gap](./2026-10-04-chat-vector-child-deadline-gap.md) therefore
remains a required production repair, not a completed gate. FAISS state has
not been serialized or reconstructed by this change; preserving it remains
mandatory for an eventual owned-child boundary.

The preceding successful browser turn evaluated the earlier source. Fresh
browser/end-to-end re-evaluation is still required after this repair, followed
by physical native-bound integration and its narrow/full-path proofs. Active
worker loss, commit/ack ambiguity, terminal exhaustion, restart and graceful
shutdown remain separately unqualified. Goal active; full qualification HOLD.
