# Ordinary browser completion after the ORM pool wait repair

Date: 2026-10-03. Evaluated source: `b79bf20cf99ab18d6d96623423f68bfb706cbc50`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
Fresh ordinary completion/reload passed; full supported qualification remains HOLD.

## Atomic Task Spec and authority

Re-evaluate ordinary chat after the pool repair: serve the current frontend,
submit one real local-model browser turn, compare visible completion with SQL,
message API, durable task receipt and raw task event, then reload and confirm the
same transcript. Remove only owned temporary frontend/browser setup. Allowlist:
this receipt. Commit subject: `docs(proof): record browser chat after pool deadline repair`.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, ADR-087 and current-state release gate. This is
direct bounded operator proof; no Campaign Engine progression or new architecture.
No source repair, runtime policy change, main merge, push, or release promotion.

## Evaluated source and runtime

Retained project `codexify_chat_branch_proof_896387ad2`, backend
`127.0.0.1:18889`, PostgreSQL `127.0.0.1:55433`, fresh temporary Vite frontend
`localhost:5181`. Empty chat queue, no turn locks, idle heartbeat with positive
TTL, and health ok were verified first. The preceding repair had loaded its two
changed files and restarted only the idle backend/chat worker. This task did not
restart them again. All **1,135 tracked Guardian/backend Python files** matched
checkout, mounted snapshot and both containers. Both use psycopg **3.3.6**.
Health reported supported profile `v1-local-core-web-mcp` valid; independent SQL
read back migration head `d4c69e03a712`.

Eight required frontend LFS manifests were temporarily hydrated only after their
exact pointer SHA-256 matched the existing checkout. Two owned symlinks reused
existing installed dependencies. No install occurred; this is core chat proof,
not complete assets, production-build, or dependency-install qualification.

## Turn and terminal agreement

The browser submitted once:
`Reply with exactly CHAT_POOL_ADMISSION_SUCCESS_20261003 and no other text.`
It displayed exactly `CHAT_POOL_ADMISSION_SUCCESS_20261003`, then showed the
same authored/assistant pair after a full reload. Reload initially showed loading
and a transient backend-delayed overlay; it recovered to the transcript without
another user action. Screenshots and the full final accessibility snapshot are
retained.

| Binding | Observed value |
| --- | --- |
| Thread | `29` |
| Authored message | `54` |
| Assistant message | `55` |
| Request | `req_990427c2db6646958991523160d6b1fa` |
| Backend task | `443e9c96-604f-4748-8b41-181014544ecb` |
| Turn | `a2cf393a-6742-4956-a8fe-22f6b0b23644` |

SQL found exactly one attempt linked to assistant `55`, without a failure or
cancellation terminal type, and exactly two messages in the thread. Message API
IDs/roles/contents matched SQL. The durable receipt was terminal
`task.completed`, reason `durable_completion_recorded`, with identical bindings.
Raw Redis contained one completion terminal and no failure/cancellation terminal
for this task. Its persistence outcome was persisted; accepted, attempted,
executed and completed were true; fallback attempted was false.

Requested, attempted, resolved and final provider/model were consistently
`local` / `local-chat`, with explicit selection and no fallback. Observed duration:
21,530 ms. This real provider turn is distinct from the pool contention tests.
It proves successful ordinary integration after the repair, not failure handling
for every dependency or nonempty retrieval/tool paths.

## Validation and cleanup

`proof.py preflight`, `verify`, `readback 29 progress/reload`, and independent
assertions passed for attempt/message/event/receipt identity, unique completion,
provider/model truth, migration, health, idle state and reload visibility.
No new automated runtime suite applies to this documentation-only task;
`git diff --check` passed. The preceding repair's 42 host and 16 container tests
remain its separate narrow proof.

Final chat queue was empty, turn locks absent, worker idle with positive heartbeat
TTL. Evaluation queue changed from 25 to 26; system queue remained 6. No queue
consumption/deletion occurred. The owned browser tab was closed, Vite interrupted
and port closure verified, all eight manifests restored to exact HEAD pointer
bytes, and only the two owned dependency symlinks unlinked. The checkout was
clean before adding this receipt. Existing Browserslist age and SettingsPanelDock
duplicate-style warnings were observed without widening into frontend repair.

Evidence:
`/private/tmp/codexify-chat-postgres-pool-browser-b79bf20cf-20261003/` contains
runner, source matrices, health/runtime snapshots, SQL/API/task readbacks,
validated results, screenshots/full reload accessibility text, frontend setup
and cleanup receipts. Existing credentials stayed private runner environment;
none were printed or committed. This receipt is documentation follow-through;
ADR impact is alignment only, with no current-state promotion or memory update.

The Goal remains active. DNS/native connection polling still escape the frozen
deadline; their repair is next. Redis/outbox/context bounds, exhausted durable
terminal reserves, remote commit ambiguity, and active-worker drain/loss recovery
remain open. Successful completion plus idle restart does not qualify those gates.
