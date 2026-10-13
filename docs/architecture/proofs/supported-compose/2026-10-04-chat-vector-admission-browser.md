# Ordinary browser chat after vector admission repair — 2026-10-04

## Authority and evaluated source

Development Operator Level 0, `PROOF_REQUIRED`, PROOF. This is one fresh
ordinary successful turn and reload on the retained supported-profile stack
after [expired vector work admission repair](./2026-10-04-chat-vector-expired-work-admission.md).
Chat Runtime Contract, Completion Pipeline and ADR-001/002/003/038/069/087 govern
identity, acceptance, provider authority and evidence limits. No new ADR or
runtime semantics. Full qualification remains HOLD.

Clean evaluated branch `codex/chat-postgres-terminal-deadline-20261003` at
`69090e7f5e7cc40fa12eac57ce8703345e015e70`. Runtime project
`codexify_chat_branch_proof_896387ad2`, backend loopback port 18889.
All **1,136** tracked Guardian/backend Python files matched checkout, retained
snapshot and both application containers before and independently after the
proof. Migration remained `d4c69e03a712`; `v1-local-core-web-mcp` was valid with
no mismatches. Health `ok`/`healthy`, chat queue zero, locks absent, idle heartbeat
and positive TTL. Evaluation/system baselines **32/13**.

Preflight and submission were separated by a continuation interval; retained
precondition timestamps are not presented as exact submission-time observations.
The worker's start timestamp and restart count remained unchanged from the
repair's native proof through independent final validation: start
`2026-10-04T17:47:30.036259801Z`, restart count zero. Task-bound sampling began
with actual running evidence and active heartbeat. No runtime refresh/restart
was issued in this Task.

## One turn, matching durable and visible outcomes

Fresh evidence root:
`/private/tmp/codexify-chat-vector-admission-browser-69090e7f5-20261004/`.
The Task Spec preceded frontend hydration and submission. One fresh Vite process
served the checkout frontend on loopback port 5181. Eight tracked LFS manifests
were hydrated from the original checkout only after all pointer SHA-256/size
checks passed. Two absent owned node_modules links reused installed dependencies;
no package installation occurred. One owned background IAB tab was used.

Submitted exactly once through normal new-chat UI:

`Reply with exactly CHAT_VECTOR_ADMISSION_SUCCESS_20261004 and no other text.`

| Identity | Value |
| --- | --- |
| Thread | 36 |
| Authored message | 68 |
| Assistant message | 69 |
| Request | `req_4105492be10346f8837ccf87f538f776` |
| Task | `40767685-738d-4dd2-8ace-8b4926ce1a34` |
| Turn | `52d60160-334c-4fef-8d7a-7eb5ff39c59d` |
| Durable accepted-at update | `2026-10-04T20:24:01.563378+00:00` |
| Running event | `2026-10-04T20:24:00.335553+00:00` |
| Completed event | `2026-10-04T20:24:46.373180+00:00` |
| Reported duration | 46,060 ms |

Exactly one attempt and one authored/assistant pair persisted. SQL, canonical
message API, durable receipt, raw Redis terminal event and assistant metadata
agreed on all identities. SQL `completed_message_id=69`; the successful attempt's
nullable `terminal_event_type` remained null. Its receipt reports completion
from the durable assistant binding. One `task.completed` event records
`persistence_outcome=persisted` and matching authored/assistant IDs.

Requested/attempted/resolved/final selection was explicit `local` / `local-chat`.
Completion truth accepted, attempted, executed and completed true;
fallback_attempted false. UI physical-model display is observation only.

The initial browser API-delay banner recovered before submission. During the
nonterminal task, UI showed the prompt and “Response outcome unconfirmed,”
explicitly checking existing status without sending again. The durable receipt
was then nonterminal and provider chunks were arriving. That banner cleared
when the assistant appeared. Prompt and exact reply were visible before reload.
Immediate reload showed loading history; it subsequently displayed the same
pair without another submission. All distinct AX/PNG observations are retained;
the final screenshot was independently inspected.

The first sampler read saw the already-bound durable attempt with null
`accepted_at`. Running preceded the later durable accepted-at update and
`task.created` breadcrumb. This is the established enqueue-before-best-effort
publication order; no new attempt or deadline was inferred from those updates.

## Worker, preservation and cleanup

**29** task-bound aggregate samples: **28 active** in the running interval, one
idle after completion with lock absent. All TTLs positive and observed ages at
most ten seconds. No new idle publication during observed running was found.
Each Redis-state read has separate start/end timestamps; these bracket rather
than isolate the exact heartbeat GET. No subsecond-transition guarantee.

Prior thread 35 messages **66/67**, content and metadata matched preflight
readback. Evaluation queue **32→33** from this authored turn's side effect;
system queue stayed **13**. All app records and queues were retained. Independent
final state: chat queue zero, no locks, idle heartbeat age 4.808 seconds, TTL 41.

Owned tab **11** closed and independently absent; user tab 1 remained. Sampler
handle **94038 exited 0**. Vite handle **94130** was stopped once and exited **1**;
independent socket check confirmed port 5181 closed. All eight owned hydrated
files were hash-checked and restored to exact HEAD pointer bytes; both links
were target-checked and removed. Repair checkout was clean before this receipt.
Inherited Browserslist-age and duplicate JSX style warnings were retained;
unrelated source was not changed to address them.

## Validation and limits

- `python3 /private/tmp/codexify-chat-vector-admission-browser-69090e7f5-20261004/validate.py` — passed: identities/content, SQL/API/receipt/event/meta coherence, model truth, UI/reload, heartbeat, source/profile/migration, preservation and cleanup.
- Independent final source/runtime readback — passed: all 1,136 hashes and worker lifecycle consistency.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

No new repository automated runtime suite applies to this docs-only proof.
Main and its unrelated staged Dev Log deletion were untouched. No merge, push
or deployment occurred. ADR impact aligned; documentation follow-through is
this receipt, with release/current-state promotion deferred.

This proves a successful branch-local ordinary browser turn after the admission
repair and its durable/event/reload coherence. It does not physically interrupt
native work admitted before expiry or qualify active-worker loss, terminal
exhaustion, commit/ack ambiguity, complete restart/shutdown or current-main
integration. The next required production obligation is the owned native child
boundary, preserving initialization, configured model/store and live retrieval
state. Goal active; full supported qualification HOLD.
