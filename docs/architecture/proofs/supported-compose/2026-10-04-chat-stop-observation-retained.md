# Retain observation while ordinary chat Stop is pending

Level 0 bounded repair and native proof, starting at `01b4e27fedf7ecc1bc458aad8b10b75caabf1df3`. Governing ADR-003/038/087 remain unchanged. Release HOLD and the full Goal remain open.

## Change

AppShell previously called `SessionSpine.cancelActiveCompletion` as soon as the cancel POST was dispatched. That optimistic terminal transition restored the draft, unlocked the composer and replaced GuardianChat before worker confirmation. The request interceptor now leaves Stop to the existing inference hook, which keeps its task stream and pending Stop state until accepted terminal evidence resolves the request. Existing session submitting/streaming exclusion stays in force; no second cancellation state machine or new terminal authority was added.

Files changed: AppShell source, its request-interceptor regression, asynchronous terminal assertions in GuardianChat's turn-lock lifecycle tests, and this receipt. The regression failed before repair because dispatching Stop invoked terminal cancellation; it passes afterward. The lifecycle tests now await their unchanged expected terminal UI phase instead of assuming an unlocked render proves that phase has committed. Expected completion/cancellation/failure, stream-close and request-count assertions remain intact.

## Fresh native Stop proof

The source-verified browser created thread 45 and authored message 85. A natural Stop click left the same chat subtree visible with “Stopping…,” disabled Stop and disabled Send. It did not restore the submitted draft or claim terminal cancellation. The pending DOM was saved at `2026-10-05T03:27:37.218546+00:00`; the raw cancellation event was published later at `2026-10-05T03:27:50.585320+00:00`. A `task.running` event precedes cancellation in that task's stream.

| Field | Value |
| --- | --- |
| Request | `req_5c4ecbb62f4a41ffa0fd790117036cd6` |
| Task | `0122e908-bdfb-4682-b4be-bd9ce8c2dbb8` |
| Thread / turn | `45` / `dfdadc2e-1096-4315-bca6-9cdf59d00ba0` |
| Authored / assistant | `85` / none |
| Original snapshot acceptance | `2026-10-05T03:27:36.335513+00:00` |
| Work / terminal deadlines | `2026-10-05T03:39:36.335513+00:00` / `2026-10-05T03:40:36.335513+00:00` |
| Cancellation terminal timestamp | `2026-10-05T03:27:50.585272+00:00` |

PostgreSQL terminal kind, one raw `task.cancelled` event, and the bounded durable receipt agree on the exact identity. No assistant or completion link persisted. The receipt matches the stored original 720/60-second deadline envelope. Cancellation terminalized 14.249759 seconds after its original snapshot acceptance. The UI then showed Cancelled, the canonical stopped notice survived reload, the matching lock disappeared and the worker returned idle.

An earlier request on thread 44 completed before the Stop locator could click; no cancellation was issued for that request. Its authored/assistant messages 83/84 and exact response `STOP OBSERVATION OK 20261004 01B4E27FE` were preserved and verified. It is ordinary completion evidence, not a cancellation-race proof or replay.

## Validation and custody

Private evidence: `/private/tmp/codexify-chat-stop-observation-01b4e27fe-20261004/`, containing the Task Spec, pre-repair failing regression, all suite logs, source checks, both request readbacks, DOM/screenshots and assertion driver.

- `.../.venv/bin/python .../run-regression.py`: expected failure before repair at the premature terminal-call assertion.
- `.../.venv/bin/python .../run-frontend.py`: final run passed 225 tests across five suites. Coverage includes AppShell dispatch, pending Stop, rejected Stop POST, authoritative completion/cancellation/failure during cancellation, SessionSpine identity filtering and turn-lock lifecycle. The private config explicitly includes `state/session` tests omitted by default include patterns.
- Earlier full runs exposed asynchronous assertion failures in receipt completion/cancellation and owned global command failure; the receipt cases passed alone. Logs are retained. Awaiting the exact expected terminal render repaired test observation; no expected outcomes were weakened and no command/tool implementation changed.
- `.../.venv/bin/python .../readback.py` and `.../.venv/bin/python .../validate.py`: passed identity, outcome, deadline-envelope, prior-record, source, schema, lifecycle, queue and lock checks.
- `git diff --check`: passed. Full frontend lint was not rerun; the previously recorded missing-plugin limitation remains outside scope.

Only the verified owned frontend proof-server process was refreshed to serve the tested private copy. HTTP inspection confirmed the optimistic parser/call absent and the served AppShell source map exactly matching the candidate source. Validation matched 685 frontend files and all 1,140 backend/worker source hashes. Backend/worker IDs/start times/restart counts and schema `f1a6d83b9024` remained unchanged. All 82 prior messages and 43 attempts were preserved; the two fresh requests added exactly three messages/two attempts. Afterward chat queue and turn locks were empty, the worker was idle, system queue remained 18, and evaluation queue advanced naturally 39 to 40.

No install, download, backend/worker restart, source refresh, schema mutation, shortened deadline, synthetic outcome, data deletion, queue cleanup, retry, protected-main mutation, push, merge or deployment occurred. Parent-only FAISS mutation and bounded read-only search snapshots remain intact. Release documentation is explicitly deferred. Native failed-Stop/completion-wins races, explicit retry and the remaining model/provider failure, orphan fencing/recovery, restart and shutdown gates still need fresh evidence before the Goal can close.
