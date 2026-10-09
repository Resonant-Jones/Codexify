# Ordinary browser completion after the PostgreSQL DNS deadline repair

Date: 2026-10-03. Evaluated source: `fddebb50e`.
Classification: `PROOF_REQUIRED`; architecture-impact, P1; owner: Codex.
Fresh ordinary completion/reload passed; full supported qualification remains HOLD.

## Atomic Task Spec and authority

Re-evaluate ordinary chat after the DNS repair: serve the current frontend,
submit exactly one local-model browser turn, compare visible completion with
independent SQL, message API, durable receipt and raw terminal event, then reload
and confirm the same transcript. Remove only owned temporary frontend/browser
setup. This change belongs in this receipt; allowlist: this receipt only.
Commit subject: `docs(proof): record browser chat after DNS deadline repair`.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, ADR-087 and current-state release gate. Direct bounded
operator proof; no new architecture, Campaign progression, runtime policy change,
main merge, push, deployment or release promotion.

## Evaluated source and runtime

Retained project `codexify_chat_branch_proof_896387ad2`, backend
`127.0.0.1:18889`, PostgreSQL `127.0.0.1:55433`, fresh temporary Vite frontend
`localhost:5181`. Before the turn: empty chat queue, no turn locks, idle worker
with positive heartbeat TTL, health ok, valid `v1-local-core-web-mcp` profile,
selected provider local and cloud-capable configuration absent. Independent SQL
read migration head `d4c69e03a712`.

The preceding repair had refreshed exactly its helper and restarted only idle
backend/chat worker; this task did not restart them again. All **1,135 tracked
Guardian/backend Python files** matched checkout, mounted source and both
containers. Both drivers are psycopg **3.3.6**. The
[DNS repair receipt](./2026-10-03-chat-postgres-dns-deadline.md) separately records
73 host and 47 container checks, including owned resolver termination/reaping,
DNS/native-poll budget sharing and healthy actual hostname/SQL controls.

Eight necessary frontend LFS manifests were temporarily hydrated only after
their exact pointer SHA-256 matched existing checkout bytes. Two owned symlinks
reused installed dependencies; no installation occurred. This evaluates core
chat, not full assets, a production build or installation qualification.

## Turn and terminal agreement

The browser submitted exactly once:
`Reply with exactly CHAT_POSTGRES_DNS_SUCCESS_20261003 and no other text.`
The new thread displayed the authored prompt and exactly
`CHAT_POSTGRES_DNS_SUCCESS_20261003`. After a full reload, the initial loading
state resolved to the same authored/assistant pair without another submission
or user action. Before/after screenshots and full accessibility snapshots were
saved; the final screenshot was independently inspected.

| Binding | Observed value |
| --- | --- |
| Thread | `31` |
| Authored message | `58` |
| Assistant message | `59` |
| Request | `req_0941483fdfa04bf7a7d080f226923ca2` |
| Backend task | `bfdbb3cb-eb85-46c5-aa22-c6487032bbdf` |
| Turn | `66cd5194-1dc3-4f04-b380-6c07d754d30d` |

SQL found one attempt linked to assistant `59`, without a failure/cancellation
terminal type, and exactly two messages. API IDs, roles and contents matched
SQL. The durable receipt was terminal `task.completed`, reason
`durable_completion_recorded`, with identical bindings. Raw Redis contained
exactly one completion terminal and no failure/cancellation terminal. Its
persistence outcome was `persisted`; accepted, attempted, executed and completed
were true, fallback attempted false. Assistant metadata agreed with event and
attempt identities and final provider/model.

Requested, attempted, resolved and final values were consistently `local` /
`local-chat`, with explicit selection and no fallback. Worker-reported duration:
**23,176 ms**. This proves one successful ordinary integration turn after the
DNS repair, not a controlled performance comparison, nonempty retrieval/tool
path, real DNS outage or every failure/recovery case.

## Validation, cleanup and limits

Private runner `preflight`, `verify`, `readback 31 progress/reload` and independent
assertions passed for unique completion, identity, SQL/API/event/receipt agreement,
provider/model truth, source hashes, migration, health and reload visibility.
No new automated runtime suite applies to this documentation-only task;
`git diff --check` passed. The repair's targeted suites remain separate proof.

Final chat queue was empty, turn locks absent, worker idle with positive heartbeat
TTL. Independent process scans found no DNS resolver child remaining in backend
or worker. Evaluation queue grew 27 to 28; system queue remained 8. This task did
not consume/delete queue contents. The owned browser tab was closed, known Vite
session interrupted to terminal exit 130 and port closure verified. All eight
manifests were restored to exact HEAD pointer bytes and only the two owned
dependency symlinks removed. The checkout was clean before adding this receipt.
Existing Browserslist-age and SettingsPanelDock duplicate-style warnings remain
outside this proof. The runner used a fresh evidence root, preserving prior
proof artifacts.

Evidence:
`/private/tmp/codexify-chat-postgres-dns-browser-fddebb50e-20261003/`
contains runner, source matrices, health/runtime snapshots, SQL/API/task readbacks,
independent validated results, screenshots/full accessibility text, and frontend
setup/cleanup receipts. Credentials remained private runner environment and were
not printed or committed. This receipt is documentation follow-through; ADR
impact is alignment only, with no current-state promotion or memory update.

The Goal remains active. Redis/outbox/context bounds, exhausted durable terminal
reserves, remote commit ambiguity and active-worker drain/loss recovery remain
unfinished. Accepted service-file configuration is deliberately rejected until
its hidden resolution can be bounded; this ordinary direct-host proof does not
qualify it. Successful completion after idle restart does not establish full
supported-Compose qualification or current-main release readiness.
