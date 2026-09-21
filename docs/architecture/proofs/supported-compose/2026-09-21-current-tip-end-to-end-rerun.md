# Current-tip supported-Compose end-to-end rerun — 2026-09-21

## Result

**Overall result: HOLD.** The repaired current tip executes the supported local
chat and document path, but two essential supported invariants do not close:

1. the browser continues to expose `Queued` after the durable task is
   terminal-successful, the assistant row is persisted, and the same transcript
   is reconstructed after reload and restart; and
2. the retrieval turn returns the synthetic document fact under project scope,
   but no persisted terminal or assistant evidence identifies the contributing
   document or chunk.

The exact evaluated commit is
`1fbf2f043117a252bfafe52720725cfc29281e92` on `main`. Its parent is
`6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2` (`Align supported local model
projection`). The historical repair SHA named by the task,
`da55b055e8c34a1400416f5416e00864168496f0`, is not an ancestor after the
repository's prior rebase; `git patch-id --stable` gives both repair commits the
same patch id, `19db61a609f49663e7f232692add47eea2062eed`. The supported repair was
therefore present in rebased form and was independently re-proved live rather
than inferred from history.

## Environment

| Field | Evidence |
|---|---|
| Observation window | 2026-09-21 14:36–17:16 EDT (18:36–21:16 UTC) |
| Machine | `VaultNode.local`; `Darwin 27.2.0 arm64` |
| Branch / HEAD | `main`; `1fbf2f043117a252bfafe52720725cfc29281e92` |
| Upstream / divergence | `origin/main` at `6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2`; ahead 1, behind 0 |
| Initial worktree | Clean: no staged, unstaged, or untracked paths. The task-described staged Dev Log deletion was not present and was not created or restored. |
| Supported topology | `docker-compose.yml` plus `docker-compose.whooshd-smoke.yml`; profile `v1-local-core-web-mcp` |
| Command-scoped posture | `LLM_PROVIDER=local`; `CODEXIFY_LOCAL_ONLY_MODE=true`; `ALLOW_CLOUD_PROVIDERS=false`; empty egress allowlist; no `LOCAL_CHAT_MODEL` override |
| Effective required-service model route | Backend, `worker-chat`, and `worker-document-embed` each projected `LOCAL_CHAT_MODEL=local-chat` together with the supported local-only posture |
| Direct rendered-config hash | `dad71e60ce9481db74eed5b25fd32571ba4c3dc519c641d1bd0af0fd3ce0eeed` |
| Migration head | PostgreSQL `alembic_version=a8d4c2f6b1e9` |
| Durable / operational authority | PostgreSQL remained durable application truth; Redis was used only for queue, heartbeat, event, and lock observation |
| Canonical live-proof receipt | `live-proof-receipt-sha256-bef1ef239470abdf6b4425a819223b886cb570a2c07ee26f89a4b786e9a29d87`; execution outcome `PASS`, schema valid, authority `PROVISIONAL` only for `commit_upstream_mismatch`; collector runtime hash `151aff39fdd379d3982ca8646467b9ca5944d9a6ab4eb37435210ecf25327653` |

The receipt collector's static runtime hash and the direct fully rendered Compose
hash use different normalization surfaces; both are recorded without treating
them as interchangeable.

## Effective runtime and readiness

The supported stack was recreated with `up -d --build --force-recreate` for
PostgreSQL, Redis, Neo4j, graph init, migrator, model prep, backend, both required
workers, and frontend. Persistent volumes were preserved; `down -v` was never
used. Containers began creation at 18:36:04 UTC. Backend table/migration
verification began at 18:36:50, and Vite reported ready at 18:37:15, an
approximately 71-second creation-to-frontend-ready interval. The first fully
instrumented browser request began at 18:44 UTC; no SLO is inferred.

PostgreSQL, Redis, Neo4j, and backend became healthy; init/migration/model-prep
services exited successfully; both workers reported startup and fresh heartbeat
evidence. Startup also emitted non-blocking warnings: an SQLAlchemy relationship
overlap warning, skipped built-in help ingestion, failed General system-role
assignment, and a logging-format `TypeError` during the ChatGPT import sweep.
They were preserved as observations and were not repaired.

Live probes agreed after startup and again after restart:

- `/health`: `status=ok`, supported profile valid, no mismatches,
  `selected_provider=local`, cloud-capable configuration absent, and no release
  hold;
- `/health/chat`: healthy, Redis reachable, chat worker fresh, queue depth zero,
  provider `local`, strict model source `LOCAL_CHAT_MODEL`, model `local-chat`;
- `/api/health/llm`: online, provider `local`, logical model `local-chat`, Whoosh'd
  endpoint selected, no release hold;
- `/api/llm/catalog`: stable provider id `local`, runtime id `whooshd`, runtime
  preset `whooshd-mlx`, logical/canonical model id `local-chat`;
- Whoosh'd `/health`: ready, version `0.1.0rc3`, queue depth zero, no active job;
- Whoosh'd `/v1/models`: `local-chat`, owned by `whooshd`, engine `mlx_vlm`,
  format `mlx`, authoritative-registry resolution, managed-sidecar execution,
  display metadata `Gemma 4 12B IT QAT 4-bit`.

The physical display metadata is observational Whoosh'd inventory, not a
Codexify supported-profile default or architecture token.

## Runtime matrix

| Surface | Result | Evidence / interpretation |
|---|---|---|
| repository/current-tip identity | PASS | HEAD remained `1fbf2f043…` from initial capture through proof edit; repair content is the patch-equivalent rebased parent `6aa2d137…`. |
| supported profile/config | PASS | Render and three required-container environments agree on local-only posture and logical `local-chat`; no manual model override. |
| Compose startup/readiness | PASS | Genuine rebuild/recreate completed without volume destruction; required services and init jobs reached their expected states. |
| migrations | PASS | Migrator exited 0 and PostgreSQL independently reported `a8d4c2f6b1e9`. |
| Whoosh'd connectivity | PASS | Backend inventory/health and direct Whoosh'd health/inventory agreed. |
| live model inventory | PASS | Whoosh'd advertised executable `local-chat` with physical display metadata observed separately. |
| provider/runtime identity | PASS | Provider `local`, logical model `local-chat`, runtime `whooshd`; persisted turns show no fallback and no cloud-capable configuration. |
| browser authentication/session | PASS | Real headed Chrome loaded the local authenticated session before and after restart. |
| Guardian/chat UI | FAIL | Transcript and composer worked, but the accessible top-level status remained `Queued` after every inspected success, reload, and restart. |
| cold chat | PASS | Exact requested marker rendered, terminalized, and persisted under thread 4. |
| warm continuation | PASS | Same-thread request correctly returned the history-dependent suffix `T1FB`; the output omitted the requested `WARM_CONTEXT_` prefix but proved the preceding marker was available. |
| durable user-message persistence | PASS | PostgreSQL preserved evaluated user messages 18, 20, 32, and 34 with ownership, order, and timestamps. |
| durable assistant-message persistence | PASS | Assistant messages 19, 21, 33, and 35 persisted exactly once with local provider/model correlation. |
| browser reload/re-entry | PASS | Reload reconstructed evaluated cold/warm turns before later concurrent user activity; retrieval and post-restart transcripts also reconstructed. |
| document upload/readback | PASS | Real Documents UI uploaded document `95b2cd45-b603-46a0-99ea-07fc4e855cdc`; PostgreSQL shows project 1, user `local`, status `ready`; UI showed Ready after reload. |
| workspace retrieval | PASS | Real Project-source turn returned exact synthetic value `HELIOTROPE-7429`. |
| retrieval provenance/scoping | FAIL | Terminal trace proves project source and three eligible project documents with no global fallback, but `trace.documents=[]` and persisted `retrieval_provenance=null`; the contributing document/chunk is not attributable. |
| queue progression | PASS | Cold, warm, retrieval, and post-restart tasks each had one running event, one assistant message event, and one completed terminal event; Redis queues returned to zero. |
| worker execution | PASS | Chat worker claimed/executed all correlated turns; document worker logged one-chunk embedding and durable ready status. |
| lock acquisition/release | PASS | Redis exposed `turn_lock` ownership during cold, warm, retrieval, and post-restart execution; each lock cleared after terminal completion and the next same-thread turn proceeded. |
| terminal events | FAIL | Durable outbox terminal truth and rendered assistant output are successful, while browser status remains `Queued`. |
| bounded negative path | BLOCKED | The supported browser selector exposed only live `local-chat`; no accepted UI control admitted an unavailable exact target. No configuration, request interception, or transport fault was injected. |
| restart persistence | PASS | Narrow application-service restart preserved chat rows, document ready state, retrieval state, and browser reconstruction; a new ordinary local turn succeeded. |
| provider-health/degraded-state truth | PASS | Classification **A**: backend/provider healthy and the former provider-degraded warning absent. The separate stale `Queued` request-status defect remains captured under Guardian/terminal events. |
| fatal browser/runtime errors | PASS | No fatal browser exception was observed. Favicon 404s, one slow-path warning, and transient restart connection noise were non-fatal; ordinary use recovered. |
| backend static validation | FAIL | Focused governing suite remained 151 passed / 5 failed; failures are stale documentation/test expectations, not a new live-runtime contradiction. |
| frontend static validation | FAIL | Four smaller files passed 32/32; lifecycle-timing OOMed near 4 GiB and turn-lock-lifecycle made no progress for one minute and was terminated. |

## Request correlation

| Turn | Thread | User msg | Task | Run | Request | Attempt | Assistant msg | Terminal event |
|---|---:|---:|---|---|---|---|---:|---:|
| cold | 4 | 18 | `18d1b7c0-f2bd-4d6e-8734-52331bab9017` | `9809d4d2fed94b088ab49945e5c7a252` | `req_9b619d15f0094b94a219906d734662ce` | `attempt_07127f889d93412eb02ccfaae2e7b35e` | 19 | 48 |
| warm | 4 | 20 | `da2eb497-a2bf-4258-bd4d-4d4ad587a30a` | `7ec379ccba7b4a4ab306cccfc6c285a2` | `req_5aa7f53a5a6d49fb9fd934372ba7f91a` | `attempt_9dc2064fc12b4f41b4208b3ff0c95ee4` | 21 | 52 |
| retrieval | 6 | 32 | `8885699e-9677-4a99-898d-a596d9073e48` | `558fd22278bb4197b68b5de1c3cab325` | `req_54a6fe2c200a4e738fe5d811ada9f115` | `attempt_affc804d2c9d44cbb6d9c154412e6b29` | 33 | 78 |
| post-restart | 6 | 34 | `a9d8a391-8b07-49c9-94b3-0f3dcdf7ce18` | `8076c174a2874b7294de9fd4037f3754` | `req_13252be3b7f6476daeaf4708b25c2ccc` | `attempt_cec7a541787f47abb83b8afee292eea3` | 35 | 82 |

All four assistant rows report attempted/final provider `local`, attempted/final
logical model `local-chat`, successful completion truth, and
`fallback_attempted=false`. The durable terminal traces explicitly report clean
provider termination and persisted output.

During an operator pause, the same live browser/thread 4 received unrelated user
messages 28 and 30 and assistant messages 29 and 31. They occurred two hours
after the bounded cold/warm evidence. The original message/task/event IDs above
were unchanged. Retrieval was therefore performed in fresh thread 6 to avoid
conflating that concurrent activity with the evaluation slice.

## Durable readback

Read-only PostgreSQL inspection established:

- threads 4 and 6 are project 1 / owner `local`;
- evaluated user and assistant rows are ordered by durable ids/timestamps;
- each correlated task has exactly one evaluated assistant row and exactly one
  `task.completed` outbox event;
- assistant metadata preserves request/task/attempt correlation, strict logical
  route selection, local provider truth, and no fallback;
- uploaded document `95b2cd45-b603-46a0-99ea-07fc4e855cdc` is owned by `local`,
  scoped to project 1, embedded as one chunk, and durably `ready`;
- no evaluated task showed persisted output without terminal success or terminal
  success without persisted output.

Redis inspection was used only for live queue/heartbeat/lock evidence. Chat and
document queue lengths returned to zero, and no evaluated `turn_lock` survived a
terminal state.

## Timing observations

| Measure | Observation |
|---|---:|
| startup creation to frontend ready | approximately 71 s (18:36:04–18:37:15 UTC) |
| cold TTFT | 27.567 s |
| cold total | 31.930 s |
| warm TTFT | 26.410 s |
| warm total | 28.394 s |
| retrieval TTFT | 20.175 s |
| retrieval total | 22.247 s |
| narrow restart recovery | 34 s (21:08:12–21:08:46 UTC) |
| post-restart total | 29.391 s |

TTFT is the durable terminal trace interval from `queued_at` to
`first_token_at`; total is the recorded task duration. These observations do not
establish or evaluate a performance SLO.

## Previous Finding Disposition

| Finding | Disposition | Rerun evidence |
|---|---|---|
| F1 — supported local model resolution non-executable | CLOSED | `local-chat` was independently advertised, selected, executed, and persisted across cold, warm, retrieval, and post-restart turns. |
| F2 — required-service profile projection inconsistent | CLOSED | Backend and both required workers independently projected the coherent supported local-only environment and `local-chat`. |
| F3 — successful-chat/persistence downstream failure | DOWNSTREAM RESOLVED | Browser output, terminal success, PostgreSQL persistence, reload, and restart readback all succeeded. |
| F4 — terminal failure/browser event-delivery disagreement | PERSISTS | Even successful terminal events leave the browser's accessible top-level state at `Queued`; the unavailable-model negative path was blocked by the supported selector. |
| F5 — incomplete document-level retrieval provenance | PERSISTS | Correct project-scoped answer, but no contributing document/chunk identity in terminal or persisted assistant provenance. |
| F6 — incomplete lock-acquisition proof | CLOSED | Direct Redis acquisition/owner/lease samples and post-terminal release were captured repeatedly. |
| F7 — static validation failures/OOM behavior | PERSISTS | Backend remains 151/5; lifecycle-timing still OOMs and turn-lock-lifecycle still hangs; smaller suites remain green. |

## Failure ledger

### 1. Terminal event/browser status contradiction — current first prerequisite

- **Observed:** browser output renders and PostgreSQL/outbox prove successful
  terminal completion, but the accessible top-level status remains `Queued`
  after cold, warm, retrieval, post-restart completion, reload, and re-entry.
- **Expected:** running/terminal browser state agrees with canonical task/event
  truth and clears generating/pending state promptly.
- **Governing invariant:** API success is not browser proof; browser/event/durable
  terminal truth must be coherent.
- **Evidence:** outbox events 48, 52, 78, and 82; corresponding durable assistant
  rows; headed-browser snapshots and screenshots before/after reload/restart.
- **Reproduction status:** deterministic across every inspected successful turn.
- **Suspected subsystem:** Guardian task-status / SessionSpine event projection.
- **Recommended next atomic task:** repair and narrowly qualify terminal task
  state projection so terminal success and failure clear the browser's queued /
  generating state without changing queue, event, or persistence authority.

### 2. Retrieval attribution missing

- **Observed:** the answer is exactly correct and the terminal trace records
  project mode, `same_user_same_project`, three eligible project documents, and
  no global fallback; however `trace.documents=[]` and persisted
  `retrieval_provenance=null`.
- **Expected:** evidence identifies the contributing uploaded document/chunk or
  an equivalent attributable durable provenance record.
- **Governing invariant:** answer correctness alone is not retrieval provenance
  proof.
- **Evidence:** document id `95b2cd45-b603-46a0-99ea-07fc4e855cdc`, message 33,
  terminal event 78, assistant metadata and terminal trace.
- **Reproduction status:** reproduced.
- **Suspected subsystem:** project-document retrieval provenance capture and
  terminal/persistence projection.
- **Recommended next atomic task:** deferred until the first prerequisite above
  is closed; no retrieval implementation change is authorized here.

### 3. Required bounded negative browser path unavailable

- **Observed:** the live browser model menu exposes only the executable Whoosh'd
  `local-chat` catalog entry.
- **Expected:** an accepted, non-destructive supported UI path for an unavailable
  exact local target, or a separately authorized failure harness.
- **Governing invariant:** fail-closed semantics must not be weakened or
  manufactured by altering supported configuration.
- **Evidence:** real selector snapshot with one model entry.
- **Reproduction status:** blocked rather than falsified.
- **Suspected subsystem:** proof-surface limitation, not an established runtime
  defect.
- **Recommended next atomic task:** deferred; no config, network, or request-body
  injection was used.

### 4. Static lifecycle/release-contract validation remains open

- **Observed:** four backend assertions retain stale current-state structure
  expectations; one startup fixture retains the old physical model; the two
  large Guardian lifecycle files still OOM/hang.
- **Expected:** focused governing checks complete cleanly against current logical
  model and documentation truth.
- **Governing invariant:** static validation is surface-specific and cannot
  override live runtime evidence.
- **Evidence:** command ledger below.
- **Reproduction status:** reproduced.
- **Suspected subsystem:** stale test expectations plus frontend test-runner /
  lifecycle fixture memory behavior.
- **Recommended next atomic task:** deferred; tests/configuration were not edited
  in this verification-only task.

## Commands and validation

Commands are grouped by proof surface. No secret values or environment dumps
were printed.

| Command / action | Exit / result | Interpretation |
|---|---:|---|
| `git status --porcelain=v2 --branch`; `git rev-parse HEAD`; `git rev-parse @{upstream}`; divergence and repeated identity checks | 0 | Stable exact evaluated tip and clean initial worktree; ahead 1 / behind 0. |
| repair ancestry, commit metadata, and stable patch-id comparison | ancestry 1; other commands 0 | Historical `da55b055…` is not post-rebase ancestry; `6aa2d137…` is patch-equivalent and is HEAD's parent. |
| supported `docker compose ... config --quiet` and full render/hash, with command-scoped profile flags and no `LOCAL_CHAT_MODEL` | 0 | Render valid; direct hash recorded. |
| supported `docker compose ... up -d --build --force-recreate` for required services and init jobs | 0 after approved Docker build access | Fresh supported recreation succeeded without destroying volumes. |
| selected `docker inspect`, Compose status/logs, required-container environment inspection | 0 | Required services ready; three required environments coherent; warnings bounded above. |
| host/backend/Whoosh'd health, inventory, catalog, and frontend probes | 0 | Provider/runtime/logical route and physical inventory agreed; no F1/F2 release hold. |
| canonical live-proof receipt collector with both Compose files | 0 | Execution `PASS`, schema valid, authority provisional only for upstream mismatch. |
| headed Playwright Chrome: cold, warm, reload, document upload, retrieval, model-menu inspection, restart re-entry, and post-restart turn | supported actions 0 | Real UI exercised; screenshots retained outside the repository under `/private/tmp/codexify-current-tip-rerun-playwright-20260921-tip1fb/`. The first session expired during an operator pause and was relaunched; durable evidence remained intact. |
| read-only PostgreSQL queries over threads, messages, documents, Alembic, and event outbox | 0 after correcting exploratory legacy table/database names | Canonical durable evidence and correlation recorded. |
| Redis queue, heartbeat, and `turn_lock` inspection during/after active turns | 0 | Acquisition/ownership/release and idle queues directly observed. |
| narrow `docker compose ... restart backend worker-chat worker-document-embed frontend` | 0 | No persistent service/volume restart; recovery in 34 s and post-restart chat succeeded. |
| `.venv/bin/python -m pytest -v tests/architecture/test_supported_compose_local_model_projection.py` | 0 | 4 passed. |
| `.venv/bin/python -m pytest -v tests/core/test_config_coherence.py` ambient | 1 | 15 passed / 1 failed because ambient `.env` selects the unrelated DeepSeek profile. |
| same config-coherence command under supported command-scoped flags, no model override | 0 | 16 passed. |
| focused backend release/profile/receipt/Compose/live/workspace contract suite | 1 | 151 passed / 5 failed / 8 warnings: four stale current-state assertions and one stale physical-model fixture. |
| individual `ProviderSelect.catalog`, `useTaskEvents`, `DocumentsView.interactions`, and `test/useRuntimeHealth` Vitest files | 0 | 5 + 4 + 7 + 16 = 32 passed. |
| individual `GuardianChat.lifecycle-timing` Vitest | 1 | Worker reached the approximately 4 GiB heap limit and OOMed after about 61 s. |
| individual `GuardianChat.turn-lock-lifecycle` Vitest | terminated after 60 s | No result/progress; bounded hang preserved without heap/config changes. |
| Pi DeepSeek delegation catalog/check/dry-run and two bounded inference attempts | checks/dry-run passed; inference wrapper failed closed before inference | Selected pair appeared in catalog but wrapper reported it unavailable; no context was sent and no delegated artifact was created. |
| `.venv/bin/python scripts/validate_docs.py` | 0 | Required architecture documents, README links, and source headings validated. |
| `git diff --check -- docs/architecture/proofs/supported-compose/2026-09-21-current-tip-end-to-end-rerun.md` | 0 | No whitespace errors in the sole authorized artifact. |

The focused backend command was:

```text
.venv/bin/python -m pytest -p no:cacheprovider -v tests/architecture/test_beta_release_boundary.py tests/core/test_supported_profile.py tests/core/test_supported_profile_auth_coherence.py tests/core/test_supported_profile_provider.py tests/core/test_supported_profile_quarantine.py tests/core/test_supported_profile_startup.py tests/audit/test_collect_canonical_live_proof_receipt.py tests/ops/test_source_compose_supported_profile_contract.py tests/proofs/test_supported_profile_live_proof_contract.py tests/proofs/test_workspace_obsidian_e2e_contract.py
```

## ADR impact and invariants

**ADR impact: aligned with ADR-069, ADR-041, ADR-042, and ADR-074; no ADR change.**
No provider, runtime, persistence, queue, lock, event, retrieval, profile, or
release doctrine was changed.

- PostgreSQL remained canonical durable application truth.
- Redis remained operational/ephemeral evidence, not competing domain truth.
- Provider identity remained `local`; logical supported route remained
  `local-chat`; Whoosh'd retained physical mapping ownership.
- No physical model name was promoted to Codexify supported-profile truth.
- Cloud fallback remained disabled and unneeded; all evaluated completions show
  `fallback_attempted=false`.
- Browser, API, catalog, queue, worker, persistence, retrieval, lock, and restart
  evidence were evaluated as distinct proof surfaces.
- Fail-closed behavior was not weakened and no defect was repaired.

## Documentation follow-through

This HOLD does **not** provide sufficient evidence for a current-state or
release-readiness update. `docs/architecture/00-current-state.md`, the original
failed evaluation, and the repair proof were not modified.

The single first-prerequisite next implementation task is the terminal
task-state/browser projection defect described in failure-ledger item 1. Do not
begin retrieval-provenance or static-test reconciliation until that atomic task
is separately authorized and bounded.
