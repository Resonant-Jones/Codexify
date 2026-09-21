# Current-tip supported-Compose end-to-end rerun — 2026-09-21

## Result

**Overall result: HOLD.**  The originally selected checkout was changed by an
external rebase during the run, so this is not a complete qualification of the
post-rebase current tip.  Before that identity change, the running supported
stack demonstrated a concrete supported-path defect: the browser continued to
announce `Queued` after terminal task completion, durable readback, reload, and
a safe restart.  That contradicts the terminal-event/UI-truth invariant.

The exact runtime revision evaluated before the identity boundary was
`da55b055e8c34a1400416f5416e00864168496f0` (`main`, then 22 commits ahead of
`origin/main`, dirty only for a pre-existing staged deletion of the daily log).
At 2026-09-21 14:03:18 EDT the checkout was rebased externally to
`6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2`, clean and equal to `origin/main`.
The backend image remained the image built before that rebase.  Per the task
stop condition, all evidence collected after that point is explicitly
non-qualifying for the original runtime revision and no claim is made that the
new tip was evaluated.

## Environment and authority

| Field | Evidence |
|---|---|
| Observation window | 2026-09-21 13:53–14:13 EDT (17:53–18:13 UTC) |
| Machine | `vaultnode.local`; `Darwin 27.2.0 arm64`; machine id/role `vaultnode` / `canonical_evidence_host` |
| Selected revision | `da55b055e8c34a1400416f5416e00864168496f0` before the mid-run rebase |
| Final checkout | `6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2`, reached by `rebase (finish)` at 14:03:18 EDT |
| Supported profile | `v1-local-core-web-mcp`; `LLM_PROVIDER=local`; `CODEXIFY_LOCAL_ONLY_MODE=true`; `ALLOW_CLOUD_PROVIDERS=false`; empty egress allowlist; `LOCAL_CHAT_MODEL=local-chat` in the effective containers |
| Runtime identity | Provider/policy `local`; runtime `whooshd` / Whoosh'd; physical inventory target `local-chat`, displayed as Gemma 4 12B IT QAT 4-bit |
| Durable authority | PostgreSQL (`alembic_version` `a8d4c2f6b1e9`); Redis used only for queue/event/lock operations |
| Canonical receipt | `live-proof-receipt-sha256-677c42e437b26b1a1f406a9d9b015977805bc8aaa623bd3ecbc1e056b9b7db76`: execution probes PASS, authority `PROVISIONAL` for `commit_upstream_mismatch` and `dirty_worktree` |

## Evaluation matrix

| Surface | Result | Evidence / surface | Relevant identifier / note |
|---|---|---|---|
| repository/current-tip identity | BLOCKED | Git identity before and after run; reflog | Revision changed from `da55b055…` to `6aa2d137…` during evaluation. |
| supported profile/config | PASS | Effective container env, `/health`, `/health/chat` | Profile valid with no mismatch; no cloud-capable configuration. |
| Compose startup/readiness | PASS | Supported `docker compose up -d --build` and `compose ps` | Backend/db/redis healthy; frontend and required workers running; supporting graph service healthy. |
| migrations | PASS | Migrator exit 0; PostgreSQL inspection | Alembic head `a8d4c2f6b1e9`. |
| Whoosh'd connectivity | PASS | `/health/chat`, Whoosh'd `/health` | Ready, managed-sidecar lifecycle, queue depth 0 when observed. |
| live model inventory | PASS | Whoosh'd `/v1/models`, `/api/llm/catalog` | Sole target `local-chat`, owned by `whooshd`; registry provenance authoritative. |
| provider/runtime identity | PASS | Catalog, health, persisted assistant metadata | Stable `local` distinct from Whoosh'd runtime and physical target; no fallback/cloud provenance. |
| browser authentication/session | PASS | Headed Chrome at `127.0.0.1:5173` | Authenticated local session loaded and remained usable. |
| Guardian/chat UI | FAIL | Playwright snapshots/screenshots | Transcript/composer work, but top-level status stayed `Queued` after completion and reload. |
| cold chat | PASS | Real browser turn, task events, PostgreSQL | Thread 3; user msg 8; task `4f4a5441-6783-40d1-aba8-bb56d8c35fd9`; assistant msg 9 returned exact marker. |
| warm continuation | PASS | Real browser turn, PostgreSQL, events | Task `790c69c8-3bec-43ba-b418-46f52a8c72f1`; assistant msg 11 returned `WARM_CONTEXT_M9P2`. |
| durable user-message persistence | PASS | Read-only PostgreSQL | Messages 8, 10, 12, 14, and 16 persisted under thread 3 / project 1 / user `local`. |
| durable assistant-message persistence | PASS | Read-only PostgreSQL | Messages 9, 11, 13, 15, and 17 persisted with task/request/attempt correlation and local provenance. |
| reload/re-entry | PASS | Browser reload and screenshot | Transcript reconstructed in correct order, including cold, warm, lock, retrieval, and later restart turn. |
| document upload/readback | PASS | Real Documents UI; `uploaded_documents` | Document `37606b8e-59f8-411e-bcca-4625268eba81`, project 1/thread 3/user local, `ready`; parsed durable text contains the synthetic marker/fact. |
| workspace retrieval | PASS | Real Project-source chat and terminal event | Task `6a996323-b419-47f2-a57a-aef64f3d5c26`; exact synthetic answer returned. |
| retrieval scoping/provenance | INSUFFICIENT PROOF | `task.completed` trace and RAG debug surface | Source mode `project`, boundary `same_user_same_project`, counts include thread document 1/project documents 2, but no document id/chunk citation is preserved. |
| queue progression | PASS | Outbox task sequences | Each inspected task has one `task.running`, one `message.created`, one `task.completed`; no duplicate terminal event observed. |
| worker execution | PASS | Fresh worker health; assistant metadata/events | `worker-chat` executed the local turns; document worker indexed the upload. |
| lock release | PASS | Redis sampled during real browser lock-witness turn | `turn_lock:3` acquired by task `306546bf-3d26-41d2-9054-df0d77e3d46b`, 840-second lease, then absent after assistant msg 13 terminalized. |
| terminal events | FAIL | Event outbox vs browser state | Back end emitted one terminal `task.completed` per task and UI rendered output, but browser continued to expose `Queued`. |
| restart persistence | PASS | Narrow `docker compose restart`; health; browser/db readback | Existing transcript/document survived; post-restart task `8b6d8b8d-39f5-43cd-bacb-26afbcf4b35a` produced durable assistant msg 17. A transient proxy `ECONNREFUSED`/HTTP 500 burst occurred while services restarted, then health and ordinary chat recovered. |
| bounded negative path | BLOCKED | Browser model selector | The supported UI exposed only live `local-chat`; no accepted UI control exists for an unavailable exact local target, and transport/config injection was intentionally not used. |
| provider-health/degraded-state truth | FAIL | `/health/llm`, `/health/chat`, catalog, browser | Runtime health remained healthy/ready and local execution succeeded. The browser's persistent `Queued` projection is stale/incorrect (**classification B**) rather than evidence of provider degradation. |
| fatal browser console/runtime errors | BLOCKED | Browser console during the checkout-change interval | A transient Vite reload error for a missing `ActivateAccountPage.tsx` occurred while the checkout changed; it cleared on reload. It cannot be attributed reliably to the pre-rebase runtime. |

## Controlled identifiers and timing observations

| Turn | Task / result | Observed total completion |
|---|---|---|
| Cold | `4f4a5441-6783-40d1-aba8-bb56d8c35fd9` → msg 9 | 25.6 s (17:55:43.869–17:56:09.485 UTC) |
| Warm | `790c69c8-3bec-43ba-b418-46f52a8c72f1` → msg 11 | 14.5 s (17:57:03.905–17:57:18.430 UTC) |
| Lock witness | `306546bf-3d26-41d2-9054-df0d77e3d46b` → msg 13 | active lock sampled 17:59:30–18:00:29 UTC; released after terminal completion |
| Retrieval | `6a996323-b419-47f2-a57a-aef64f3d5c26` → msg 15 | 30.0 s (18:04:44.296–18:05:14.282 UTC) |
| Post-restart | `8b6d8b8d-39f5-43cd-bacb-26afbcf4b35a` → msg 17 | roughly 18 s observed |

Application start and token-first-byte timing were not measured with a reliable
instrumentation boundary; no performance conclusion or SLO is asserted.

## Failure ledger

1. **F1 — terminal state projection is stale (FAIL, deterministic in this run).**
   - Observed: `Queued` remained accessible after each terminal event, durable
     assistant persistence, reload, and restart, while the in-panel provider
     projection reported `Ready` / `Completed`.
   - Expected: browser-visible terminal state agrees with the canonical task
     terminal event and persisted assistant result.
   - Governing invariant: browser/UI success or display must not contradict
     durable/event truth; terminal-event delivery must agree with domain state.
   - Evidence: headed-browser snapshots `cold-terminal.png`,
     `reload-durable-thread.png`, and `post-restart-terminal.png`; outbox rows
     for each task list exactly one `task.completed`.
   - Suspected seam: Guardian task-status/session projection.

2. **F2 — retrieval identity provenance incomplete (INSUFFICIENT PROOF).**
   - Observed: terminal trace proves project-scope retrieval and source counts,
     but not the precise document/chunk selected; assistant metadata and latest
     RAG debug view have null provenance.
   - Expected: attributable retrieval-path evidence for the synthetic document.
   - Governing invariant: correct model text alone is not retrieval proof.
   - Suspected seam: retrieval provenance persistence/projection.

3. **F3 — bounded UI negative path unavailable (BLOCKED).**
   - Observed: the real selector offered only the live inventory model.
   - Expected: a supported UI path for a bounded fail-closed unavailable-target
     test, or an explicitly authorized alternative.
   - No configuration or transport injection was used.

4. **F4 — qualification identity invalidated mid-run (BLOCKED).**
   - Observed: external rebase changed the worktree/ref while the earlier image
     continued running.  Later static results therefore belong to neither a
     stable original checkout nor a rebuilt new-tip runtime.
   - Expected: frozen repository ref from identity capture through closeout.

## Commands and validation

| Command / surface | Exit / result |
|---|---|
| Supported Compose recreation with command-scoped profile flags | 0; required services ready |
| `make ... canonical-audit-live-proof-receipt ...` | 0; execution PASS, authority provisional as noted |
| `.venv/bin/python -m pytest -v tests/architecture/test_supported_compose_local_model_projection.py tests/core/test_config_coherence.py` | 1; one ambient-profile coherence failure |
| Same config-coherence suite with explicit supported local env and empty egress allowlist | 0; 16 passed |
| `.venv/bin/python scripts/validate_docs.py` | 0 |
| Focused supported-boundary/profile suite (149 tests) | 5 failed, 144 passed; run after the ref changed and thus non-qualifying for selected runtime |
| Focused frontend catalog/document/runtime-health tests | 0; 19 passed |
| Focused `GuardianChat.lifecycle-timing` and `GuardianChat.turn-lock-lifecycle` | no result after one minute; terminated and recorded as a bounded validation hang |
| Headed Playwright/Chrome | actual local browser exercise completed; artifacts kept outside repository under `/private/tmp/codexify-current-tip-rerun-playwright-20260921` |

## Follow-through

ADR impact: **aligned, no ADR change.**  No implementation, configuration,
architecture-contract, migration, or release-claim file was modified.  This
receipt does **not** justify a current-state/release update.  The single
highest-priority next atomic task is: **freeze an identified current-tip ref and
rebuild the supported stack from that same ref before rerunning the qualification**.
Only after that prerequisite is met should the confirmed terminal-status
projection defect be repaired and requalified.
