# Ordinary browser chat after native vector deadline repair — 2026-10-04

## Authority and source

Development Operator Level 0, PROOF_REQUIRED, PROOF. The active ordinary-chat
reliability Goal authorizes this single browser turn and read-only evidence.
ADR-087, Chat Runtime and Completion Pipeline contracts govern the existing
identity, provider, persistence and completion boundaries. No new ADR or release
claim. Private Task Spec preceded setup and submission.

Frozen clean isolated branch `codex/chat-postgres-terminal-deadline-20261003` at
`1d7d7128f2d9039877b848a3145969d46dc8053d`, the parent-owned snapshot/native
construction and search deadline repair. The retained supported-profile project
`codexify_chat_branch_proof_896387ad2` uses existing local models and Chroma.
All **1,138** Guardian/backend Python source files match checkout, retained
snapshot, backend and worker before and after this turn.

The preceding repair proof recorded an OOM-killed backend during overlapping
native reference and focused tests, then verified its recovery. This separate
Task starts from that healthy recovered runtime and runs no concurrent native
fixture or regression suite. Other projects, host/VM limits, runtime source,
configuration and service lifecycle were not changed. General release and
failure/recovery qualification remain **HOLD**.

## Single accepted turn and durable completion

Private evidence root:
`/private/tmp/codexify-chat-vector-bound-browser-1d7d7128f-20261004/`.
Task Spec, source hashes, heartbeat samples, inflight/completed/reloaded
SQL/API/receipt/Redis evidence, screenshots, lifecycle and cleanup manifests
are retained. One new chat was submitted through the normal UI composer with
explicit existing local provider/model:

`Reply with exactly CHAT_VECTOR_BOUND_SUCCESS_20261004 and no other text.`

| Identity | Observed value |
| --- | --- |
| Thread | `37` |
| Authored user message | `70` |
| Assistant message | `71` |
| Request | `req_041ae2f8de1c48989f1d969e933748fc` |
| Backend task | `6c4319e4-0c35-4441-bcfc-2086c5e5d109` |
| Turn | `ca6ae729-3621-49ff-9ba4-2197a6be6b86` |
| Duration | `51,057 ms` |

Exactly one accepted attempt and assistant message exist. The assistant contains
exactly `CHAT_VECTOR_BOUND_SUCCESS_20261004`. It was visible with the authored
prompt before and after intentional reload, and the final saved PNG was
independently inspected. Initial loading states were preserved separately.
No retry, resubmission or cancellation occurred.

PostgreSQL records `completed_message_id=71`; success leaves
`terminal_event_type=null` under the existing completion contract. The task
receipt is terminal `task.completed`, reason `durable_completion_recorded`.
The raw Redis stream has one completion terminal, with message 71, latest user
message 70, `persistence_outcome=persisted`, and matching request/task/turn.
Completion truth records accepted, attempted, executed and completed true;
fallback attempted false. Requested, attempted, resolved and final provider/model
are **`local` / `local-chat`**, selection source explicit, no fallback reason.
Assistant metadata agrees. UI displays Whoosh'd and Gemma 4 12B IT QAT 4-bit;
that label is an observation, not independent physical model attestation.

## Heartbeat and runtime preservation

The sampler retained **33** observations, including **31** active samples inside
the task-running interval. Each brackets the complete Redis state read and
retains task/attempt identity, event data and heartbeat publication time.
All sampled TTLs were positive and heartbeat ages at most ten seconds. No new
idle publication during running was observed. The final sample follows terminal
completion, with fresh idle heartbeat, queue zero and thread lock absent.
These are sampled observations, not proof of every instant between samples.

Backend and worker remained running without OOM or lifecycle change throughout
this Task. Backend start remains `2026-10-04T21:47:17.506339553Z`; worker start
remains `2026-10-04T21:34:16.858728583Z`; restart counts remain zero. Migration
is `d4c69e03a712`. Supported profile is valid `v1-local-core-web-mcp`, health
`ok`, chat health `healthy`. Prior thread 36 messages 68/69 retain exact content
and `extra_meta`. Evaluation queue moves **33 to 34** for this successful turn;
system queue remains **17**. Final chat queue zero, locks absent, idle TTL
positive. Independent final SQL readback matches reload evidence; no native
search child remains in the worker.

## Cleanup and validation

Eight tracked LFS manifests were hydrated only after all HEAD pointer OID/size
checks against existing installed workspace contents. Two absent owned
`node_modules` links reused existing dependencies. No installation occurred.
Exact pointer bytes were restored, each link target verified before removal,
and final absence checked. The isolated checkout was clean before this receipt.
Owned IAB tab **16** was closed and independently absent; all other tabs remain.
Known Vite handle **91250** terminated with actual exit **130**, port 5181 closed;
sampler handle **82970** exited zero. An initial cleanup artifact copied the
previous proof's Vite exit 1; it was retained and corrected to the actual result.
The first screenshot-save call lacked its filesystem binding after capturing
the inflight state; the already captured image/text were saved on the next call.
It did not trigger a second submission.

Independent `validate.py` and final durable readback passed. Source verifier,
local Markdown link checks, `python3 scripts/validate_docs.py` and
`git diff --check` passed before the scoped docs commit. No additional automated
runtime regression suite applies to this docs-only receipt. Vite reports inherited
Browserslist age and duplicate JSX `style` warnings; neither was changed.

This proves a fresh ordinary browser completion after the repair with durable
and visible truth aligned, while preserving the observed runtime. It does not
prove each retrieval branch was exercised, establish native active-forward
interruption in this turn, or attest live loaded-parent FAISS tensor capture.
Native private FAISS/Chroma parity and expiry are bounded separately by the
repair receipt, including its preserved OOM failure. Full current-main
integration and failure/retry/restart/shutdown qualification remain open;
the Goal stays active. No main edit, merge, push or deployment occurred.
