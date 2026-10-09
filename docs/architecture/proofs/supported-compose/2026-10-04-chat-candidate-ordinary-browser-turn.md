# Fresh repaired-candidate ordinary browser completion — 2026-10-04

## Authority, source and proof class

Development Operator Level 0, architecture-impact, PROOF_REQUIRED, EXECUTE →
PROOF. The active ordinary-chat reliability Goal authorizes one inert private
browser turn. ADR-087/038/003 and the original-deadline policy govern; no new ADR,
provider, deadline, queue or acceptance authority. Private Task Spec preceded
frontend preparation and the one send.

Clean repair `e80229f4514bea538acc36d064b579772923ea71`, branch
`codex/chat-postgres-terminal-deadline-20261003`. Backend/worker run the frozen
`bbf319376` runtime candidate against schema `f1a6d83b9024` from
[coherent source/schema proof](./2026-10-04-chat-candidate-source-schema.md).
Project `codexify_chat_branch_proof_896387ad2`, backend loopback 18889; no source,
schema or service refresh occurred in this Task.

Evidence root:
`/private/tmp/codexify-chat-candidate-browser-e80229f45-20261004/`.
Private frontend on loopback 5182 uses committed code, existing Node/dependencies
and hash/size-verified existing LFS payloads. Owned node_modules root and Vite
configuration/cache paths prevent shared package cache writes. The only later
private configuration edit adds Vite's owned cache directory. No installation,
model download, build of Docker images, or external provider dispatch occurred.
Native custody checks match all 1,140 backend/Guardian files and 686 unchanged
frontend source files; the private Vite configuration is recorded separately.

## One actual turn and durable agreement

The in-app browser opened a fresh `/chat` at the private frontend. It inspected
the offered local Gemma model, then submitted exactly one prompt:

```text
For this isolated runtime check, reply with exactly: CANDIDATE CHAT OK 20261004 E80229F45
```

No second send, synthetic assistant, injected terminal event, deadline shortening
or automatic replay was performed. The natural runtime produced exactly:
`CANDIDATE CHAT OK 20261004 E80229F45`.

| Identity | Observed value |
| --- | --- |
| Thread | 38 |
| Authored message | 72 |
| Assistant message | 73 |
| Request | `req_ba6d5a3ced7a423e962e593bdb90bce5` |
| Task | `10885ddc-47ae-4d04-90f8-bccc24b2fc35` |
| Turn | `ed355445-2ffd-43c2-8c44-33a4fec68c39` |
| Final provider/model | `local` / `local-chat` |

The exact original snapshot persisted before queue acknowledgement:
acceptance `2026-10-05T02:36:55.850818+00:00`, work end
`02:48:55.850818+00:00`, terminal end `02:49:55.850818+00:00`.
It retains the exact 720/60 envelope. Separate database acceptance confirmation
is `02:36:55.860304+00:00`; neither later confirmation nor receipt polling
reconstructs or slides the original deadline.

The worker reached AWAITING_MODEL and AWAITING_FIRST_TOKEN, then first output
at `02:38:56.501288+00:00`, completion at `02:39:00.757590+00:00`:
**124.906772 seconds** from original acceptance, inside the work window.
Raw Redis stream contains 58 events and exactly one terminal kind,
`task.completed`, bound to assistant 73 and the same request/task/thread/turn.
Assistant metadata preserves the exact authored message ID, requested/final
local provider and model, and `fallback_triggered=false`. The ordinary receipt
returns `terminal`, `task.completed`, `durable_completion_recorded` and link 73;
no cleanup token is exposed. PostgreSQL's successful attempt uses its atomic
assistant link; `terminal_event_type` remains NULL rather than duplicating a
failure/cancel field for completion.

The browser displayed the prompt and exact assistant reply, removed the
unconfirmed-outcome notice, and navigated to `/chat/38`. Reload first showed the
existing history-loading state, then returned to the same two-message transcript
without creating another request. The final screenshot and DOM/AX evidence are
retained as `reloaded-transcript.jpg`, `reloaded-ui.json` and tool observations.
No sidebar navigation or extra prompt was needed to make the answer appear.

## Observed limit: live request visibility

During execution, the sampled new-thread UI displayed “Response outcome
unconfirmed” and “Checking existing status without sending again,” while the
native worker had already reached AWAITING_FIRST_TOKEN. This is an observation
of incomplete transport visibility, not proof of provider failure or worker
loss. Live progress, chunk rendering and cancellation controls were not proven
by these samples. After completion the rendered inference-state attribute is
`idle`; canonical transcript completion is proven, not a continuously retained
active inference session. The Task's intended live generating/progress proof is
therefore incomplete. A focused new-thread request-ownership/progress inspection
is the next obligation; no cause is assumed or product repair hidden inside this
proof Task.

## Independent checks, documentation and remaining goal

`prepare-frontend.py`, `readback.py` and `validate.py` passed. Readback uses
ordinary authorized API receipts plus PostgreSQL and Redis observations; it
never manufactures completion. Validation independently checks exact identity,
original deadline unchanged, one terminal, assistant metadata, fallback absence,
reloaded UI, frozen source/schema/lifecycle and prior rows.

All 71 earlier messages and 37 earlier attempts retain their exact projections.
Only this natural private turn adds two messages and one attempt. Chat queue is
zero, locks absent, idle heartbeat with positive TTL. Evaluation queue changes
34 -> 35 through the normal completion follow-through; system queue stays 18.
Backend/worker IDs, start instants and restart counts remain those recorded in
the source/schema receipt. Main's concurrent state was inspected read-only and
not modified; there is no main integration or shared-memory write.

The owned Vite process remains verified live on exec session 30976 for the next
browser Task; tab 3 is marked for handoff at `/chat/38`. Existing warnings include
Babel's large dependency formatting note and duplicate `style` attributes in
SettingsPanelDock. They did not block this chat proof and were not repaired
outside scope. No automated product regression suite applies to the repository
docs-only diff; the native browser/API/SQL/Redis proof above is the validation
surface. `python3 scripts/validate_docs.py`, local receipt links and
`git diff --check` passed. Only this receipt changes; scoped commit is reported
in closeout, with no new ADR or release-anchor change.

This proves one successful repaired-candidate browser completion and durable
reload. It does not prove continuous live request projection, cancellation,
retry identity, provider failure/rejection, controlled deadline, lost-worker
orphan reconciliation/fencing, service restart, graceful shutdown, or current-main
release qualification. Unconfirmed admission and receipt-window exclusion remain
separate known limitations. Full Goal stays active; release HOLD.
