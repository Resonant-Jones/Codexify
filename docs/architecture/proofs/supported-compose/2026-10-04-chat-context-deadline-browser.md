# Ordinary browser chat after context deadline propagation — 2026-10-04

## Scope and authority

Development Operator Level 0, `PROOF_REQUIRED`, PROOF. This is one fresh
ordinary turn on the retained supported Compose profile after the context
repair, followed by browser reload and independent durable/runtime readback.
Chat Runtime Contract, Completion Pipeline and ADR-001/002/003/038/069/087
govern acceptance, identity, provider authority, terminal truth and evidence
limits. The proof aligns with those contracts; no ADR or runtime token changes.

Evaluated clean branch `codex/chat-postgres-terminal-deadline-20261003` at
`f0cfdcce95677468958120f27ce4806f17faccee`. The preceding
[context propagation receipt](./2026-10-04-chat-context-deadline-propagation.md)
proves the fatal exception seams; this receipt adds the fresh successful
browser path. No production source changes, merge, push or deployment occurred.
Current-main release truth remains HOLD and differs from this repair branch.

The atomic Task Spec was saved before frontend hydration and submission in
`/private/tmp/codexify-chat-context-deadline-browser-f0cfdcce9-20261004/`.
Its reused heading/context names the preceding heartbeat proof, while its
frozen revision, prompt, receipt path and final scope explicitly identify this
context-repair proof. It was retained unchanged rather than rewritten later.

## Source, topology and preconditions

Project `codexify_chat_branch_proof_896387ad2`, backend at loopback port 18889,
with its existing backend, worker-chat, Redis and PostgreSQL containers. All
**1,136** tracked Guardian/backend Python files matched checkout, retained
source snapshot and both application containers before submission and again
in independent final readback. Migration stayed `d4c69e03a712`.

Health was `ok`; the admitted `v1-local-core-web-mcp` profile was valid with
no mismatches. Chat queue was empty, turn locks absent, heartbeat idle with
positive TTL. Evaluation/system queue baselines were **31/12**. This Task
performed no runtime refresh or container restart.

Eight existing tracked frontend LFS manifests were hydrated from the original
checkout only after every pointer SHA-256 and size matched. Two absent owned
node_modules links reused existing installed dependencies. No package install
occurred. One fresh Vite process served this exact frontend on loopback port
5181; one owned background IAB tab was used.

## One accepted turn and coherent completion

Submitted once through the normal new-chat UI:

`Reply with exactly CHAT_CONTEXT_DEADLINE_SUCCESS_20261004 and no other text.`

| Identity | Observed value |
| --- | --- |
| Thread | 35 |
| Authored message | 66 |
| Assistant message | 67 |
| Request | `req_efc71da8ea7f48dcaceb235d847f0df3` |
| Task | `a789ce8f-0a65-479b-9168-bc807dc8479d` |
| Turn | `70f5ee02-a35a-48e1-bd95-e610366f14e1` |
| Accepted at | `2026-10-04T17:25:57.797366+00:00` |
| Terminal duration | 35,424 ms |

The in-flight receipt was honestly nonterminal with no assistant/completion
link. Later SQL, canonical message API, durable task receipt, raw Redis event
and assistant metadata agreed: exactly one attempt, one authored message,
one assistant, `completed_message_id=67`, one `task.completed` terminal and
`persistence_outcome=persisted`. The SQL successful attempt's nullable
`terminal_event_type` remained null; the durable receipt reported completion
from its assistant link, matching the existing success schema.

Requested, attempted, resolved and final provider/model were `local` /
`local-chat`, selection explicit. Completion truth was accepted, attempted,
executed and completed true; fallback_attempted false. Physical model display
metadata is observation only, not independent proof of physical inference.

The UI rendered the authored prompt and exact assistant marker before reload.
Immediate reload showed an honest loading-history state; it then loaded the
same pair without another submission. Full accessibility and PNG snapshots
before reload, immediately after reload and after history restoration are
retained. The final saved screenshot was independently inspected.

## Worker and preserved state

The sampler recorded **24** task-bound aggregates: **23 active** during the
running interval, then idle after terminal completion with the turn lock
absent. Every heartbeat had positive TTL and age at most ten seconds. No new
idle publication during observed running was found. Each whole Redis-state
read now has separate start/end timestamps; this brackets but does not isolate
the precise GET instant. Sampling and one-second publisher timestamps cannot
prove every subsecond transition.

Final independent readback: chat queue zero, no locks, idle heartbeat age
1.944 seconds, TTL 43. Evaluation queue **31→32** from the new authored-message
side effect; system queue remained **12**. These queues were retained.
Prior thread 34's messages 64/65 and metadata were byte-equivalent to the
preflight JSON readback; prior thread 33 retained message IDs 62/63. All new
application records and events remain in the retained proof stack.

## Validation and cleanup

- `python3 /private/tmp/codexify-chat-context-deadline-browser-f0cfdcce9-20261004/validate.py` — passed: SQL/API/receipt/event/meta identities, exact content, provider truth, UI/reload, heartbeat, source/migration/profile, preservation and cleanup.
- Independent final readback — passed: all 1,136 runtime hashes, fresh idle state, prior records and exact source revision.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

No new automated repository runtime suite applies to this docs-only proof.
The actual browser and native readbacks supply its runtime evidence.

Owned tab 9 closed and independently absent; user tab 1 remained. Sampler
handle 99661 exited 0. Vite handle 21126 was stopped once and exited **1**;
independent socket check proved port 5181 closed. All eight hydrated files
were verified against owned hashes, then restored to exact HEAD pointer bytes;
two links were verified against exact targets and removed. Repair checkout
was clean before this receipt. Vite emitted inherited Browserslist-age and
duplicate JSX style warnings; no unrelated edits were made for them.

## Limits and next obligation

This proves one ordinary successful branch-local browser turn after the
context deadline repair, including persistence, terminal propagation and
reload coherence. It does not prove production native vector deadline bounds,
terminal-reserve exhaustion, commit/remote-ack ambiguity, active-worker-loss
recovery, graceful drain, complete Compose restart or current-main integration.
The Goal stays active and full supported qualification stays HOLD. Next is
bounded production integration of the already-proven native vector child
mechanism, after verifying its authoritative context and resource lifecycle.
