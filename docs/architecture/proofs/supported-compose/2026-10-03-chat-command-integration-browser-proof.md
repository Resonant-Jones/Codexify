# Browser chat after command failure integration

Date: 2026-10-03. Evaluated source: `b67469c9a4fcc60787c440a14c824eb47c16764b`.
Classification: `PROOF_REQUIRED`; architecture-impact proof. Qualification
remains `HOLD`.

## Atomic Task Spec

Verify the retained isolated Compose project is idle with an empty chat queue,
no turn locks, and a fresh heartbeat. Refresh only the stale shared chat service
in the task-owned source snapshot, restart only backend and idle worker, and
verify source identity. Serve the evaluated frontend through fresh Vite. Send
one ordinary browser turn and one bounded prompt proposing an unadvertised
read-only action through the real local model. Compare browser state with raw
events, PostgreSQL messages/attempts, and API messages/receipts. Preserve all
databases, other queues, accepted identities, and provider authority. Record
model noncompliance as a proof limit. Close temporary frontend/browser.

This change belongs in this receipt alone. P1; owner Codex; proof review.
Authority is the active reliability Goal under the Codex Development Operator
protocol, Chat Runtime Contract, Agent Tool Loop Contract, Provider Tool Turn
Boundary Contract, and ADR-087. No new ADR or authority is created. Validation
is live source/health/browser/readback/cleanup assertions and `git diff --check`;
no new automated runtime tests apply to this documentation-only task. Commit
this file only with subject `docs(proof): record browser chat after command failure integration`.

## Runtime and source

Project: `codexify_chat_branch_proof_896387ad2`; backend `127.0.0.1:18889`;
fresh frontend `localhost:5181`. Before mutation: chat queue zero, no locks,
worker heartbeat idle with TTL 44, health `ok`; eval/system queues 22/3.

Only `guardian/core/chat_completion_service.py` was copied into the retained
task-owned source snapshot. Only the existing backend and chat-worker containers
were restarted. Postgres/Redis/Neo4j and their volumes were retained. Two early
health observations reset while backend health was `starting`; the same process
then returned `ok`, with valid local-only `v1-local-core-web-mcp`. No extra
restart was issued. The first preflight used an incorrect `/api/health` URL;
the verified route is `/health`.

All 1,134 compared tracked Python files under guardian/backend matched the
checkout, source snapshot, and both containers independently. This proves
Python-source identity, not whole-image/configuration/dependency equivalence.
Postgres remained at migration head `d4c69e03a712`. Existing isolated API
credentials were reused only in process environment; no credential was printed,
staged, or added to this receipt. This is not account-session qualification.

## Observed outcomes

| Surface | Exact-marker ordinary reply | Requested action proposal |
| --- | --- | --- |
| Thread / authored / assistant | 26 / 48 / 49 | 27 / 50 / 51 |
| Request | `req_3e68d9992a034b24b91dedee2f79927c` | `req_a7541b4bf642455986024602656c8578` |
| Task | `83155d5b-7f6a-4a1f-8fa2-705c1f7a9745` | `0fcfc187-ef0a-47ba-af54-7f5ae011c54b` |
| Turn | `eff0720b-cf34-45b4-9e72-c0060849a0ff` | `05b6c32f-e2db-4ca1-b2df-9f4fb473f01a` |
| Runtime outcome | Exactly one `task.completed` | Exactly one `task.completed` |
| Provider / model | `local` / `local-chat` | `local` / `local-chat` |
| Tools | Automatic, zero advertised/dispatched | Automatic, zero advertised/dispatched |
| Loop | `idle` / `plain_answer` | `idle` / `plain_answer` |

The first browser prompt produced exactly `CHAT_COMMAND_TRUTH_SUCCESS_20261003`.
Its authored message and reply rendered, then survived reload. The second
prompt asked for an exact JSON tool decision proposing `op::health_health_get`.
The actual model instead returned: “I cannot fulfill this request. I am unable
to provide the specific JSON object or command structure you've requested.”
That is a plain assistant reply. The UI displayed Completed and the same text,
and reload retained it. It did not exercise the authority rejection or returned
command failure guard. No synthetic response, task permission, or event was
injected, and no additional prompt was sent to force the failure.

For both cases, independent SQL message/attempt readback, API transcript and
durable receipt, and raw Redis event identities agree. Each has one authored
and one assistant message, exactly one terminal event, the exact assistant
binding, and matching request/task/turn. Completion truth is accepted,
attempted, executed, and completed true; fallback attempted false. Assertions
passed. Final chat queue zero, no locks, heartbeat idle TTL 44; eval/system
queues 24/4. No proof command cleared or consumed unrelated queues.

Evidence root: `/private/tmp/codexify-chat-command-runtime-b67469c9a-20261003/`.
It retains preconditions/health, source/container hashes, migration head,
events, API and SQL messages/attempts/receipts, validated readback, and browser
screenshots before/after reload. Early files named `blocked-*` record the
attempted negative canary; its actual outcome is the plain-answer completion
documented above and in `authority-proposal-*`, not a blocked command.

The browser tab closed; Vite was intentionally interrupted (exit 130), and port
5181 was verified closed. Retained proof containers remain running. Existing
Browserslist and SettingsPanelDock duplicate-style warnings were not repaired.

## Whole-path re-evaluation

This is fresh branch-local ordinary completion evidence after loading the
returned-command repair and frontend presentation repair. It proves UI/event/
durable agreement for an exact marker and a model refusal. It does not prove
actual failed/blocked command execution/presentation: those retain focused
test evidence in their separate receipts. The zero-tool supported-profile
canary must not be widened into tool qualification.

Other tool-loop failure classifications, finite context/database/terminal
deadline enforcement, server-side command quiescence, full Compose
restart/shutdown, active-worker-loss recovery authority, and important failure/
retry evidence on the resulting tip remain open. This receipt is documentation
follow-through; no current-state promotion, main merge, push, deployment, or
memory update occurred. The Goal remains active.
