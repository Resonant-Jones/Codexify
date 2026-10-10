# Browser Stop: durable cancellation passes, immediate shell truth fails

Level 0 proof-only task at clean candidate `8ae0e9ece9f641a9e55a6c9fde3c3712cf32b84c`, with the coherent backend/worker snapshot `bbf319376` and schema `f1a6d83b9024`. Governing ADR-003/038/087 and accepted deadline/orphan authority remain unchanged. Release stays HOLD.

## Result

A fresh browser Send created thread 43 and authored message 82. The repaired new-thread panel displayed Working and Stop. Read-only runtime evidence confirmed that the worker was active, the accepted attempt had no assistant or terminal kind, and the matching turn lock existed. One natural Stop click produced exactly one durable `task.cancelled`, no assistant, and matching lock cleanup. The canonical stopped notice survived reload.

The immediate shell projection failed: after Stop, the shell replaced the chat subtree, restored the submitted draft and enabled Send without showing Stopping. The saved DOM timestamp was `2026-10-05T03:11:45.916115+00:00`; the raw cancellation event was published at `2026-10-05T03:11:50.355087+00:00`. These wall-clock observations establish that Send was enabled before terminal-event publication; they do not independently timestamp the PostgreSQL commit.

Source inspection identifies the premature transition: the AppShell POST request interceptor calls `SessionSpine.cancelActiveCompletion` before the cancel POST resolves. That method immediately sets `canceled` and restores the draft. The AppShell subscription then advances `guardianSurfaceEpoch`, replacing GuardianChat and its task observer. SessionSpine also ignores later matching live events after `canceled`, so the completion-versus-cancellation race cannot be inferred from this optimistic state. This run ultimately cancelled successfully; it does not prove the competing-completion race.

The next bounded repair must keep a Stop request nonterminal, retain the observer/composer exclusion while cancellation is unresolved, and permit durable completion to win when appropriate. The existing `canceling` status is present but unused by this request path. No new cancellation authority or terminal token is proposed here. Explicit retry was not issued because the Task Spec required stopping at a visibility defect; retry remains a required later proof.

## Exact identity and deadline

| Field | Value |
| --- | --- |
| Request | `req_ad29ab1a28864a79bb9bd75749d21e5e` |
| Task | `12ef5284-952a-4799-8e13-f52bc15a60d7` |
| Thread / turn | `43` / `26899987-dbe9-479e-9cad-1cc087c77749` |
| Authored / assistant | `82` / none |
| Original snapshot acceptance | `2026-10-05T03:11:20.331681+00:00` |
| Work deadline | `2026-10-05T03:23:20.331681+00:00` |
| Terminal deadline | `2026-10-05T03:24:20.331681+00:00` |
| Cancellation terminal timestamp | `2026-10-05T03:11:50.354939+00:00` |

The durable attempt changed only `terminal_event_type` to `task.cancelled`. Its original deadline snapshot remained exact and unchanged. The raw event and bounded receipt agreed on the request/task/thread/turn; the receipt used `durable_terminal_outcome_recorded`. No assistant completion link or terminal orphan outcome appeared. Cancellation terminalized 30.023258 seconds after original snapshot acceptance, within its original work deadline.

## Validation and custody

Private evidence: `/private/tmp/codexify-chat-cancel-proof-8ae0e9ece-20261004/`, including the Task Spec, preconditions, accepted attempt, active-worker checkpoint, before/after Stop DOM, screenshots, raw events, durable messages/receipt and validation output. Browser actions used CUA; API/PostgreSQL/Redis readback was read-only. The already-live owned Vite server was polled and its served repair markers verified; it was not restarted or refreshed.

`.../.venv/bin/python .../readback.py` and `.../.venv/bin/python .../validate.py` passed the evidence assertions. They preserved all 81 prior messages and 42 prior attempts, accounted for exactly one authored message and one cancelled attempt, verified exactly one cancellation terminal event/no assistant, matched all 1,140 backend/worker source hashes, and rechecked unchanged schema and backend/worker IDs/start times/restart counts. The worker ended idle, chat queue and turn locks were empty, and evaluation/system queues remained 39/18. `git diff --check` is the scoped document validation; no automated runtime test applies to this documentation-only change.

Only this receipt changes in the repository. No product repair, ADR change, release-current-state update, retry, replay, shortened deadline, provider/model change, data deletion, runtime restart, protected-main mutation, push, merge or deployment occurred. Parent-only FAISS mutation and per-search bounded read-only snapshots remain unchanged. Goal active: the optimistic shell cancellation path must be repaired, then cancellation/retry and the remaining failure/orphan/restart/shutdown surfaces must receive fresh qualification.
