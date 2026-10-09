# Ordinary browser completion after the PostgreSQL connection polling repair

Date: 2026-10-03. Evaluated source: `3231fc57b`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
Fresh ordinary completion/reload passed; full supported qualification remains HOLD.

## Atomic Task Spec and authority

Re-evaluate the complete ordinary user path after the native connection repair:
serve the current frontend, submit one local-model browser turn, compare visible
completion with independent SQL, message API, durable task receipt and raw task
event, then reload and verify the same transcript. Remove only owned temporary
frontend/browser setup. This change belongs in this proof receipt; allowlist:
this receipt only. Commit subject:
`docs(proof): record browser chat after connection deadline repair`.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, ADR-087 and current-state release gate. Direct bounded
operator proof; no Campaign Engine progression, implementation change, new ADR,
main merge, push, deployment, runtime policy change or release promotion.

## Source and runtime custody

Retained project `codexify_chat_branch_proof_896387ad2`, backend
`127.0.0.1:18889`, PostgreSQL `127.0.0.1:55433`, fresh temporary Vite frontend
`localhost:5181`. Before the turn, chat queue was empty, turn locks absent and
worker idle with positive heartbeat TTL. Health was ok, supported profile
`v1-local-core-web-mcp` valid, selected provider local and cloud-capable
configuration absent. Independent SQL read migration head `d4c69e03a712`.

The preceding repair had refreshed exactly its helper and restarted only idle
backend/chat worker. This task did not restart them again. All **1,135 tracked
Guardian/backend Python files** matched checkout, mounted source and both
containers. Both use psycopg **3.3.6**. The
[repair receipt](./2026-10-03-chat-postgres-connect-deadline.md) separately records
52 host and 26 container tests, including actual deadline failures.

Eight required frontend LFS manifests were temporarily hydrated after verifying
their exact pointer SHA-256 against existing checkout bytes. Two owned symlinks
reused existing installed dependencies; no dependency installation occurred.
This evaluates ordinary chat, not complete assets or a production frontend build.

## Browser, persistence and terminal agreement

The browser submitted exactly once:
`Reply with exactly CHAT_POSTGRES_CONNECT_SUCCESS_20261003 and no other text.`
The new thread initially showed its loading state, then displayed the durable
authored message and exactly `CHAT_POSTGRES_CONNECT_SUCCESS_20261003`. After a
full reload, loading resolved to the same authored/assistant pair without another
submission or user action. Both screenshots and full accessibility snapshots
were saved; the final screenshot was inspected independently.

| Binding | Observed value |
| --- | --- |
| Thread | `30` |
| Authored message | `56` |
| Assistant message | `57` |
| Request | `req_f02d84a2b8fe4dc99b83b6ed21b1ed50` |
| Backend task | `1abce5db-e52f-4727-9a2d-51734e27d0e0` |
| Turn | `556c72e0-13f4-4324-9496-05da597caa06` |

SQL found one accepted attempt linked to assistant `57`, without a failure or
cancellation terminal type, and exactly two messages. Message API IDs, roles and
contents matched SQL. The durable receipt was terminal `task.completed`, reason
`durable_completion_recorded`, with matching request/task/thread/turn/message
bindings. Raw Redis contained exactly one completion terminal and no failure or
cancellation terminal. Its persistence outcome was `persisted`; accepted,
attempted, executed and completed were true; fallback attempted was false.

Requested, attempted, resolved and final provider/model were consistently
`local` / `local-chat`, selected explicitly without fallback. Assistant metadata
agreed with the event and persisted attempt. Observed duration: **21,144 ms**.
This real provider turn proves ordinary integration after the connection repair.
It does not prove nonempty retrieval, tools or every failure/recovery case.

## Validation and cleanup

Private runner `preflight`, `verify`, `readback 30 progress/reload`, and independent
assertions passed for unique completion, identity, SQL/API/event/receipt agreement,
provider/model truth, migration, health, runtime source and reload visibility.
No new automated runtime tests apply to this documentation-only task;
`git diff --check` passed. The repair's narrow tests remain separate evidence.

Final chat queue was empty, turn locks absent, worker idle with positive heartbeat
TTL. Evaluation queue grew from 26 to 27; system queue remained 7. No queue
consumption or deletion was performed by this task. The owned browser tab was
closed, the known Vite session interrupted to terminal exit 130 and port closure
verified. All eight manifests were restored to exact HEAD pointer bytes and
only the two owned dependency symlinks removed. The checkout was clean before
adding this receipt. Existing Browserslist-age and duplicate-style warnings in
SettingsPanelDock were observed without widening into frontend repair.

Evidence:
`/private/tmp/codexify-chat-postgres-connect-browser-3231fc57b-20261003/`
contains runner, source matrices, runtime/health snapshots, SQL/API/task readbacks,
independent validated results, screenshots/full accessibility text, and frontend
setup/cleanup receipts. Credentials stayed in private runner environment and
were not printed or committed. This receipt is documentation follow-through;
ADR impact is alignment only. No current-state promotion or memory update.

The Goal remains active. DNS resolution still precedes the bounded native
connection generator and needs proof/repair. Redis/outbox/context bounds,
exhausted terminal reserves, remote commit ambiguity and active-worker drain/loss
recovery remain unfinished. Ordinary success after an idle restart does not
qualify those gates or establish current-main release readiness.
