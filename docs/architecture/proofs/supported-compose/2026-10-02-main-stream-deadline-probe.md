# Current-main streaming deadline boundary

Date: 2026-10-02. Evaluated source:
`17546590c6b20dab994580fdfb1883207259c021` on `main`.
Authority: active ordinary-chat reliability Goal, Development Operator Level 0.
Lane: architecture-impact, PROOF_REQUIRED. Governing sources: current-state HOLD,
ADR-001/002/003/038/087, and the canonical chat runtime contract.

## Result

**Deadline enforcement failed in six controlled real-HTTP cases.** The shared
completion attempt returned successful provider terminal evidence after its
immutable accepted-task work deadline. Both future-deadline and legacy controls
returned valid success. No harness watchdog fired.

This is provider-attempt evidence, not durable assistant completion, a task
terminal event, or supported Compose qualification. It directly contradicts
ADR-087's in-flight, non-sliding provider bound at the evaluated source.

| Case | Connect/read policy, seconds | Elapsed, seconds | Work deadline overrun, seconds | Outcome |
| --- | --- | --- | --- | --- |
| Delayed response headers | 2 / 2 | 0.759 | 0.509 | Provider success, late output |
| Silent response body | 2 / 2 | 0.757 | 0.507 | Provider success, late output |
| Continuing tokenless frames | 2 / 2 | 0.800 | 0.550 | Provider success, late output |
| Early partial output, continuing frames | 2 / 2 | 0.818 | 0.568 | Provider success, late final output |
| Future deadline control | 2 / 2 | 0.804 | 0 | Provider success within budget |
| Legacy absent-envelope control | 2 / 2 | 0.812 | Not applicable | Provider success |
| Tokenless frames, shorter inactivity bound | 0.20 / 0.20 | 0.798 | 0.548 | Provider success, late output |
| Partial output, shorter inactivity bound | 0.20 / 0.20 | 0.812 | 0.562 | Provider success, late final output |

The six expiring cases had approximately 0.25 seconds of remaining work budget
at attempt entry. They all delivered final output after that boundary without
`CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`. Early partial output was observed before
expiry in the partial cases. All deadline snapshots remained unchanged.

## Causal seam and controlled surfaces

Invoke the current `_execute_completion_attempt` with an actual
`ChatCompletionTask` roundtripped through canonical queue serialization and
decoding. Construct the acceptance timestamp approximately 719.75 seconds in
the past; preserve the real 720-second work and 60-second terminal intervals.
No shorter acceptance contract or replacement budget is introduced.

The real `stream_local`, Requests session/socket transport, streaming parser,
terminal evidence validation, and cancellation monitor execute. An ephemeral
HTTP server bound to `127.0.0.1` returns OpenAI-compatible frames. Delayed-header
and quiet-body cases wait 0.75 seconds. Continuing cases flush complete padded
frames every 0.05 seconds for 0.75 seconds, then return final text and `[DONE]`.
Padding makes each full frame observable independently of Requests' read chunk
size. This is a finite fixture, not a claim of having observed an infinite hang.

Controlled seams are explicit: synthetic local Whoosh'd settings/model/key,
disabled supported-profile override, a single fixture base candidate, and an
assertion restricting every HTTP request to the fixture's exact loopback port.
The last two cases override only the runtime-policy helper's connect/read
values to 0.20 seconds, shorter than the remaining parent budget. They retain
the real Requests transport. No Requests response or parser is mocked.

Eight actual `/v1/chat/completions` requests occurred, one per case, with the
synthetic configured model and request/task/execution-attempt correlation
headers. The cancellation callback always returned false. No user cancellation
was used to simulate expiry, and no cancellation-monitor thread remained after
the server and requests were closed.

Source inspection independently shows that `_execute_completion_attempt` does
not pass accepted-task deadline authority to `stream_local`. The latter selects
connect/read-inactivity policy and uses `iter_lines()` without an absolute work
deadline. A checkpoint after `next(iterator)` cannot bound the blocked read;
lowering inactivity timeout alone cannot interrupt continuously arriving frames.
The current dequeue-only guard does not enforce this in-flight boundary.

## Validation and reproducibility

External evidence root:
`/private/tmp/codexify-main-stream-deadline-17546590c-20261002/`.
It contains the complete `probe.py`, `results.json`, and `probe.log`, plus the
earlier six-case results. Run from the repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python \
  /private/tmp/codexify-main-stream-deadline-17546590c-20261002/probe.py
python3 -m py_compile \
  /private/tmp/codexify-main-stream-deadline-17546590c-20261002/probe.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check \
  /private/tmp/codexify-main-stream-deadline-17546590c-20261002/probe.py
git diff --check
```

Probe: **exit 1**, with fixture controls PASS and six deadline violations. The
nonzero result reports failed runtime compliance, not failed fixture controls.
Each case had an eight-second harness watchdog; none fired. Compilation, scoped
Ruff, and diff check passed. Ruff emitted the existing configuration deprecation
warning. No automated runtime tests apply to the receipt-only repository change.

The first harness run incorrectly read `result.terminal_evidence` instead of
the actual `result.terminal` field. Its controls failed with AttributeError;
that run is retained as `initial-harness-error.log/json` and excluded from the
runtime verdicts. The corrected runs completed all fixture controls.

Imported source SHA-256 values were independently checked against Git HEAD:

```text
guardian/core/ai_router.py
bfd43540b35dc754eb5f661941c31f419b0731c278fa9affdf02333b3b94fec5
guardian/core/chat_completion_service.py
b5cb86cd2a8cc423134e95e4346321340c5604274c59cf2f6549c9d574cb27a3
```

## Consequences and remaining work

The next causally justified obligation is accepted-task deadline propagation
into an interruptible absolute bound covering local provider headers and body
streaming. It must preserve typed deadline failure, explicit cancellation,
terminal evidence, request correlation, and endpoint/model authority. It must
close the actual I/O operation rather than merely abandon a waiting observer
or classify expiry as user cancellation. Repair requires a separate Task Spec.

Context/retrieval, tool/fallback children, PostgreSQL/persistence, terminal
publication/rollback/cleanup, and graceful drain remain separate unqualified
obligations under ADR-087. Fresh current-source Compose/browser/PG failure and
recovery evidence is still required for the larger Goal.

No production source, service, live model, queue, database, credential, or
deployment changed. No push or merge occurred. No new ADR, runtime token,
release claim, or Axis KB addition is proposed. Release documentation remains
HOLD; this receipt is evidence of a concrete implementation gap.
