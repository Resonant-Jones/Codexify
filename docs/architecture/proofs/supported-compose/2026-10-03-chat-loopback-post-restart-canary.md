# Ordinary browser chat after loopback deadline integration

Date: 2026-10-03. Classification: `PROOF_REQUIRED`. Evaluated source:
`065fb06e7fca5a1669b15cb27b5a812bb23f465c`. Full qualification remains `HOLD`.

## Atomic Task Spec

On retained project `codexify_chat_branch_proof_896387ad2`, confirm empty chat
queue/no turn locks/fresh idle heartbeat; refresh only the three stale Python
files; restart only backend and idle chat worker; verify source identity; then
prove one ordinary browser turn and reload with independent terminal-event,
transcript, durable-attempt, and receipt readback. Preserve databases, other
services, and queue contents. Record this receipt without application edits,
migration, image rebuild, release promotion, or publication.

This change belongs in this proof receipt. Architecture-impact proof aligned
with ADR-087 and the Chat Runtime Contract, authorized by the active reliability
Goal under the Codex Development Operator protocol. P1; owner Codex; proof
review. Acceptance is exact identity/content/provider agreement and cleanup,
not request acceptance alone. Validation is live source/health/browser/readback
assertions plus `git diff --check`; no new automated runtime tests apply to this
documentation-only task. Stage this file alone and commit with subject
`docs(proof): record chat after loopback deadline integration`.

## Runtime and preconditions

Chat queue depth was zero, turn-lock scan empty, and chat heartbeat idle with
40 seconds remaining. Eval/system depths were 21/2. Health was `ok`, with
valid `v1-local-core-web-mcp`, selected provider `local`, and cloud-capable
configuration absent.

The task-owned source snapshot at
`/private/tmp/codexify-chat-branch-proof-896387ad2-20261003/source` received only:
- `guardian/command_bus/invoke.py`
- `guardian/command_bus/loopback_http_adapter.py`
- `guardian/core/chat_completion_service.py`

Only `codexify_chat_branch_proof_896387ad2-worker-chat-1` and
`codexify_chat_branch_proof_896387ad2-backend-1` were restarted. Postgres, Redis,
Neo4j, volumes, and other queues were retained. Post-restart health was `ok`
on the same valid local-only profile. All 1,134 compared tracked Python files
under `guardian`/`backend` matched this checkout both in the source snapshot
and independently inside each restarted container. This proves Python-source
identity, not image/dependency/hydrated-resource/configuration equivalence.

A fresh Vite process served this checkout at `http://localhost:5181`, proxying
to isolated backend `http://127.0.0.1:18889`. The existing isolated development
credential was reused only in process environment. No credential was created,
printed, stored in the receipt, or staged. Account-session qualification is
outside this canary.

## Observed turn

The browser sent `Reply with exactly this marker:
CHAT_AFTER_LOOPBACK_DEADLINE_20261003` once through the ordinary composer.
It rendered the authored message while waiting for generation, then showed
Completed and the exact assistant marker. Reload showed transient history
loading/backend checking, then settled into the same two-message transcript
without a retry, second send, or duplicate assistant.

| Surface | Independent evidence |
| --- | --- |
| Thread / authored / assistant | `25` / `46` / `47` |
| Request | `req_21df935f0ccd425c9e90c2f8addca15f` |
| Task | `dee91c65-6375-43a1-94a7-604a3a3aa0a9` |
| Turn | `d658aa82-a6fb-4485-837c-58a5647a0db7` |
| Redis | Exactly one terminal event, `task.completed`, linked to assistant `47` |
| Postgres | Same request/task/thread/turn, completed-message binding `47` |
| Receipt | `terminal`, `task.completed`, `durable_completion_recorded`, message `47` |
| Transcript API | One authored and one assistant; exact marker content |
| Model truth | Event/assistant metadata `local` / `local-chat`; no fallback |
| Browser model label | Gemma 4 12B IT QAT 4-bit, matching advertised alias display metadata |
| Completion truth | accepted/attempted/executed/completed true, fallback attempted false |
| Tool path | `tool_turn_used=false`; plain assistant answer |
| Final runtime | Chat queue zero, no turn locks, idle heartbeat with TTL 44 |

Identity, content, single-terminal, provider/model, completion-truth, source,
and cleanup assertions passed. Final eval/system depths were 22/3; no proof
command cleared or consumed them. Their change is an observation rather than
proof that unrelated work completed.

Evidence root: `/private/tmp/codexify-chat-loopback-runtime-065fb06e7-20261003/`.
Preconditions, health before/after, snapshot/container hashes, raw task events,
API messages/receipts, independent SQL readback, final runtime state, and
settled reload screenshot are retained. The temporary Vite process and browser
tab were closed after capture; retained proof containers remain running.
Vite reported stale Browserslist data and an existing duplicate JSX `style`
attribute in `SettingsPanelDock.tsx`; neither was repaired in this proof scope.
The intentional interrupt of the temporary frontend returned exit 130.

## Whole-path re-evaluation and limits

This verifies one ordinary browser completion on integrated Python source after
backend/idle-worker restart. The local provider generated the actual reply,
and UI/event/Postgres/receipt evidence agreed. It does not exercise a tool turn
or deadline exhaustion; those client bounds have the separate real-socket
fixture evidence in `2026-10-03-chat-loopback-accepted-deadline.md`.

Full-stack/Redis/Postgres restart, the Compose start wrapper, graceful shutdown
during generation, server-side command quiescence, context/retrieval and
database/terminal envelope enforcement, failure/cancellation/retry on this
evaluated tip, and full supported-path qualification remain unproven. Existing
active-worker-loss and partial-output execution-field decisions remain open;
the intermittent cancellation test failure remains unlocalized.

Documentation follow-through is this receipt; no ADR/current-state claim was
changed. No source edit, push, main merge, deployment, or memory update occurred
in this proof task. The broader Goal remains active.
