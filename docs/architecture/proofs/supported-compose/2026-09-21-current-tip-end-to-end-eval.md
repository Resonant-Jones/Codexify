# Current-tip supported-Compose end-to-end evaluation — 2026-09-21

## Verdict

**Overall result: `HOLD`**

The current-tip stack started far enough to prove PostgreSQL, Redis, migrations, the frontend, the chat worker, the document worker, Whoosh'd discovery, browser session establishment, document ingestion, queue claim, worker execution, fail-closed provider behavior, and durable user-message/document readback. It did not qualify the supported path.

The first prerequisite failure is a supported-runtime configuration contradiction:

- Whoosh'd advertised the logical model `local-chat`, with display/runtime metadata for `Gemma 4 12B IT QAT 4-bit`.
- The required backend and chat worker retained `LOCAL_CHAT_MODEL=qwen3.8-27b-4bit`.
- Strict resolution overrode each browser request for `local-chat` with that configured exact model.
- Whoosh'd returned `404 model_not_found`; no token or assistant message was produced.
- `/health/chat` was `unhealthy`, `/api/health/llm` was `down`, and the canonical health receipt retained `release_hold=true`.

No defect was repaired. No source, configuration, migration, frontend, backend, or Compose file was changed. No volume was destroyed. No cloud fallback occurred.

## Orientation receipt

- Axis interaction mode: `EXECUTE` followed by `PROOF`.
- Architecture-impact lane; verification-only.
- Governing sources read before mutation: `docs/axis-node/README.md`, the invocation and character directives, `docs/architecture/00-current-state.md`, `docs/architecture/README.md`, the canonical ADR index, ADR-069, ADR-041, ADR-042, the canonical live-proof receipt contract, `config-and-ops.md`, `flows.md`, `data-and-storage.md`, agent protocol operations, and the two Ops issue/compiler contracts.
- Current-state authority remained `docs/architecture/00-current-state.md`; no release claim was widened.

## Environment and repository identity

| Field | Observed value |
|---|---|
| Evaluation date/window | 2026-09-21, approximately 10:39–11:31 EDT |
| Machine | `vaultnode.local`; requested machine id `vaultnode`; role `canonical_evidence_host` |
| Audit authority | `PROVISIONAL`; repository was not eligible for a trusted canonical receipt because of upstream mismatch and a dirty worktree |
| Repository | `/Volumes/Dev_SSD/Codexify-main` |
| Branch | `main` |
| Evaluated commit | `72f588e669c725aa27d599e6c81b255ed35ac388` |
| Upstream | `origin/main` at `4a09140b98858630088265912528698166b0cec6` |
| Ahead / behind | ahead 20, behind 0 |
| Pre-existing worktree state | staged deletion of `docs/DEV_LOG/2026-09-21/Dev Log - 2026-09-21.md`; preserved and excluded from this task's commit |
| Docker | Docker Desktop 4.91.0; Engine 29.8.0; Compose 5.5.1; context `desktop-linux` |
| Supported profile under test | `v1-local-core-web-mcp` |
| Compose files | `docker-compose.yml` plus checked-in `docker-compose.whooshd-smoke.yml` |
| Compose project | `codexify` |
| Effective-config hash | `c1f0a94de63f10c03a70b5a289a83c642e8d01cbc72190efd5944e69b6e51c45` |
| Migration head | `a8d4c2f6b1e9` |
| Canonical live receipt | `live-proof-receipt-sha256-24628304d16895846bbd259840fb3a1c7d04dcca3548fbc332d24889438785c6`; outcome `FAIL` |

### Effective configuration

The repository `.env` was not modified. Its relevant pre-existing values selected `v1-friends-family-web`, `LLM_PROVIDER=deepseek`, cloud providers enabled, local-only mode disabled, and `LOCAL_CHAT_MODEL=qwen3.8-27b-4bit`. Command-scoped supported-profile variables and the checked-in Whoosh'd smoke overlay were used to evaluate the supported path without rewriting that file.

The resulting required-service projection was not coherent:

| Service | Profile | Provider | Local only | Cloud allowed | Egress allowlist | Local model |
|---|---|---|---|---|---|---|
| backend | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | `qwen3.8-27b-4bit` |
| worker-chat | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | `qwen3.8-27b-4bit` |
| worker-document-embed | `v1-friends-family-web` | `local` | `false` | `true` | `deepseek` | `qwen3.8-27b-4bit` |

The backend's supported-profile object nevertheless reported `valid=true` and no mismatches, while also reporting `cloud_capable_configuration_present=true` and `release_hold=true`. That projection does not cover the required document worker's divergent environment.

## Startup observations

An initial command-scoped env-file attempt omitted the existing Neo4j password handoff, causing `graph-init` to exit 1 before the backend could start. This was an evaluation-harness configuration error, not product evidence. It was preserved in the command ledger and not classified as a Codexify defect.

The second startup used the repository's checked-in Whoosh'd overlay. It completed image build/recreation and produced:

- PostgreSQL healthy; Redis healthy; Neo4j healthy.
- `migrator` exit 0 and live Alembic head `a8d4c2f6b1e9`.
- `model-prep` exit 0 and `graph-init` exit 0.
- backend healthy, `/ping` 200, and frontend `/` 200.
- chat worker heartbeat fresh; document worker running and later embedding the evaluation document.
- frontend and workers have no Compose healthcheck, so HTTP behavior, worker heartbeat, task execution, and document embedding were used instead of process existence alone.

Startup diagnostics included a SQLAlchemy overlapping-relationship warning, skipped built-in help ingest, failed assignment of the General system role, and a logging-format `TypeError` in the ChatGPT import sweep. None was repaired.

## Evaluation matrix

Every required surface has exactly one evaluation result.

| Surface | Result | Evidence | Command / tool / surface | Identifier | Notes |
|---|---|---|---|---|---|
| repository/current-tip identity | `PASS` | Exact local branch, HEAD, upstream, ahead/behind, and pre-existing staged deletion recorded | Git porcelain v2, `rev-parse`, `rev-list` | commit `72f588e...` | Canonical receipt remains provisional; this is exact local-current-tip evidence, not a release receipt |
| supported profile/config | `FAIL` | Backend/chat worker use local-only profile, but exact model is not advertised and required document worker retains friends/family plus cloud-capable settings | Compose render; selected container env; `/health` | config hash `c1f0a94d...` | No configuration was changed to force a pass |
| Compose startup/readiness | `FAIL` | Required containers reached their process/readiness checks, but supported chat health was unhealthy and release hold stayed active | `docker compose up`, `ps`, HTTP probes | project `codexify` | A stack that cannot execute supported chat is not application-ready |
| migrations | `PASS` | Migrator exited 0 and database reports the expected single Alembic revision | container state; read-only PostgreSQL query | `a8d4c2f6b1e9` | Migration exit and live DB revision agree |
| Whoosh'd connectivity | `PASS` | Guardian reached `http://host.docker.internal:8000/v1`; host `/health` was ready with queue depth 0 | backend health; host HTTP probe | Whoosh'd `0.1.0rc3` | Runtime was reachable before and after restart |
| live model inventory | `PASS` | `/v1/models` returned one live item, `local-chat`, owned by Whoosh'd | host HTTP probe; backend model resolution | `local-chat` | Inventory display name was `Gemma 4 12B IT QAT 4-bit`; lifecycle was unloaded |
| provider/runtime identity | `FAIL` | Provider remained `local`, but UI selected logical `local-chat` while the execution layer overrode it with unavailable `qwen3.8-27b-4bit` | health JSON, Playwright, task terminal event | provider `local`; requested `local-chat`; configured `qwen3.8-27b-4bit` | Provider identity stayed distinct from runtime identity, but the resolution contract did not yield an executable target |
| browser authentication/session | `PASS` | Real Vite application loaded with local API-key session, health/events connected, and authenticated APIs returned 200 | Playwright headed Chrome | user `local` | Default supported profile is local single-user authentication; no login form is expected |
| Guardian/chat UI | `FAIL` | Navigation, sidebar, composer, selectors, and submission worked, but the first terminal failure remained visually `Queued` until the 300-second hard timeout | Playwright | thread `1` | Later failures rendered `Failed`; ordinary successful chat was unusable |
| cold chat | `FAIL` | User message persisted; task progressed to provider request, then Whoosh'd returned `model_not_found`; no output token | browser, task SSE, worker log | task `28ff6b62-dd04-4d15-b0bd-2ecb977adcb4`; run `7186a003...`; attempt `attempt_5480...` | Total accepted-to-terminal time about 6.51 s; no TTFT |
| warm continuation | `FAIL` | Follow-up was accepted in the same thread and failed independently at the same strict model boundary | browser, task SSE, worker log | task `50863bbe-e0aa-4c04-b05b-ccaf818efacc`; run `3dbb0561...`; attempt `attempt_de8e...` | Terminal failure after about 0.79 s; no contextual answer |
| durable user-message persistence | `PASS` | Three user messages existed in PostgreSQL `chat_messages` with ordered ids/timestamps and were returned by the API | read-only PostgreSQL; chat messages API | project `1`; thread `1`; messages `1`, `2`, `3`; owner `local` | PostgreSQL remained canonical durable application truth |
| durable assistant-message persistence | `FAIL` | Zero assistant messages existed because all three inference tasks failed before output | PostgreSQL; messages API; task events | no assistant message id | No false success or placeholder assistant message was persisted |
| reload/re-entry | `PASS` | Reload and direct re-entry reconstructed the persisted user transcript; ordering remained correct | Playwright reload/direct route | `/chat/1` | The expected assistant transcript could not exist; that failure is recorded separately |
| document upload/readback | `PASS` | Browser upload progressed from Pending to Ready after reload; worker embedded one chunk; PostgreSQL stored marker/fact, project, owner, and ready status | Playwright Documents UI; worker log; PostgreSQL | document `edb46f7d-2ead-4783-bf6c-b192971b06f9` | Filename `codexify-eval-20260921-7f3c.md`; project `1`; owner `local` |
| workspace retrieval | `FAIL` | Context broker observed one project document, but inference failed before any fact-bearing answer could be produced | Playwright chat; worker log | task `2133aa4d-00b3-4ee7-bef2-2c85d847cfd6`; run `ffd0ff37...` | Expected answer was synthetic orchard number `7319`; no assistant output |
| retrieval scoping/provenance | `INSUFFICIENT PROOF` | Persisted trace says retrieval executed, project-document hits 1, global hits 0, boundary `same_user_same_project`, and global fallback false; the same trace also says `retrieval_status=no_candidates` with an empty document provenance list | read-only `chat_threads.metadata` query; debug trace endpoint | project/thread `1` | Scope enforcement is evidenced, but document-level provenance is internally incomplete and no completion can corroborate usage |
| queue progression | `PASS` | Each request was accepted, enqueued, claimed, ran, and reached a single failed terminal state; queue depth returned to 0 | task SSE; Redis; PostgreSQL outbox | three task ids above | No abandoned queue item, retry, or duplicate execution observed |
| worker execution | `PASS` | Chat worker logged one run and one failure per task; document worker embedded one chunk | worker logs; durable outbox counts | runs `7186...`, `3dbb...`, `ffd0...` | Provider execution itself did not complete |
| lock release | `INSUFFICIENT PROOF` | `EXISTS turn_lock:1` was 0 after terminal failure and the next same-thread request was accepted; acquisition was not directly captured | Redis; subsequent browser request | thread `1` | No stale held lock observed, but the normal path did not expose sufficient acquisition evidence |
| terminal events | `FAIL` | PostgreSQL outbox contains exactly one `task.running` and one `task.failed` for each task; browser rendered the second/third failures, but missed the first terminal failure for 300 seconds | task SSE; outbox query; browser console/UI | first task `28ff6b62...` | Backend/domain terminal truth and first browser-visible completion state disagreed |
| restart persistence | `BLOCKED` | Safe restart preserved/reconstructed all three user messages and the ready document; assistant persistence could not be evaluated because no assistant message was ever produced | Compose restart; Playwright; PostgreSQL | thread `1`; document `edb46f7d...` | PostgreSQL, Redis, and volumes were not restarted or destroyed |
| bounded negative path | `PASS` | Failure was explicit `local_model_unavailable/model_not_found`, fallback was false, no assistant message was created, queue/lock cleared, and a later ordinary request was independently accepted | terminal event; Redis; browser; PostgreSQL | first and second tasks | The baseline defect itself exercised the accepted fail-closed path; it was not manufactured destructively |
| provider-health/degraded-state truth | `PASS` | Classification **C**: runtime discovery is reachable, but the narrower configured chat target is non-executable; UI says provider available with failing checks | `/health/chat`, `/api/health/llm`, UI technical details | `chat_unhealthy`; `local_model_resolution_error` | The warning is materially accurate; the separate model picker/execution mismatch fails provider/runtime identity |
| fatal browser console/runtime errors | `PASS` | No fatal application exception. Initial browser session logged only favicon 404s plus the consequential 300-second completion timeout warning; fresh post-restart page logged no warnings/errors | Playwright console | headed Chrome session `codexify-eval` | Browser network hosts were exclusively `http://127.0.0.1:5173` |

## Controlled request correlation

| Turn | User message | Request / task / run | Terminal truth |
|---|---|---|---|
| A — initial | message `1`; marker `CODEXIFY_EVAL_20260921_A_7F3C` | request `req_6ea11fe5c22748b58d842be8087fa20b`; task `28ff6b62-dd04-4d15-b0bd-2ecb977adcb4`; run `7186a00362194aeb8cc791c8b1f14cbb`; turn `a28d33b2-4157-4ff9-a984-ca8e5b77e5e5` | one `task.failed`; no output and no assistant row |
| B — continuation | message `2`; asks for the prior marker | request `req_cf31c47664154c7aa85b9636ddc9fb1e`; task `50863bbe-e0aa-4c04-b05b-ccaf818efacc`; run `3dbb05616df240a9a33aa9bf9d22de77`; turn `ecfa1ca7-d53f-49dd-abe3-6b97ccda76a9` | one `task.failed`; no output and no assistant row |
| Retrieval | message `3`; asks for the synthetic project fact | task `2133aa4d-00b3-4ee7-bef2-2c85d847cfd6`; run `ffd0ff37531b40919e50918463e95d90`; turn `3244a561-6a92-44c2-9d49-5b957336817f` | project-doc count 1, then one `task.failed`; no output |

The first two terminal events include `attempt_id` values. All terminal records report `provider=local`, `fallback_attempted=false`, `executed=false`, `completed=false`, and `visible_output_emitted=false`. Browser request enumeration and runtime log searches found no OpenAI, DeepSeek, or other cloud-inference request.

## Independent durable readback

Read-only PostgreSQL inspection after UI completion and again after restart established:

- `chat_threads.id=1`, `user_id=local`, `project_id=1`, `origin_system=codexify`.
- `thread_config` selected `providerId=local`, `modelId=local-chat`, and `retrievalSource=project`.
- `chat_messages` contained ordered user messages `1`, `2`, and `3` at 14:55:03, 15:08:30, and 15:21:07 UTC.
- no assistant message existed.
- `uploaded_documents` contained the disposable document as `ready`, owned by `local`, scoped to project `1`, with the exact marker and synthetic fact in `parsed_text`.
- `events_outbox` contained exactly one `task.running` and one `task.failed` for each evaluated task, with zero `task.completed` rows.

Redis was used only for queue, ephemeral task-event, heartbeat, and lock evidence. It was not treated as durable domain truth.

## Timing observations

These are observations, not SLOs.

| Observation | Value |
|---|---|
| Supported-overlay startup | backend became healthy about 23 s after required service recreation began; first recorded simultaneous backend/frontend HTTP proof was within about 123 s, including frontend dependency preparation |
| Safe restart recovery | API and frontend both returned 200 on poll 10, about 18.5 s after restart command completion |
| Observable cold model state | Whoosh'd `/health` reported `active_model=null`; inventory provenance reported `model_lifecycle=unloaded` |
| Initial request | accepted-to-terminal failure about 6.51 s; worker-reported duration 6.32 s |
| Warm continuation | accepted-to-terminal failure about 0.79 s; worker-reported duration 0.779 s |
| Retrieval request | worker running-to-terminal failure about 0.64 s |
| Initial TTFT | unavailable: no token was emitted |
| Warm TTFT | unavailable: no token was emitted |
| Generation throughput | unavailable: no generation occurred |
| First browser terminal visibility | failed: browser stayed `Queued` until its 300,000 ms hard timeout despite backend failure at about 6.5 s |

## Failure ledger

### F1 — supported local model resolution is non-executable

- **Observed:** live inventory advertised only `local-chat`; effective backend/chat-worker configuration required exact `qwen3.8-27b-4bit`; strict resolution overrode the UI request and Whoosh'd returned `model_not_found`.
- **Expected:** the logical supported `local-chat` route resolves to an advertised, executable physical target while provider identity remains `local`.
- **Governing contract/invariant:** ADR-069 supported local profile; live inventory requirement; logical route is not physical-runtime proof; no silent cloud fallback.
- **Evidence:** `/health/chat`, `/api/health/llm`, Whoosh'd `/v1/models`, three terminal events, worker logs, canonical receipt.
- **Suspected subsystem:** canonical supported-profile/Compose environment projection into backend and chat worker.
- **Deterministic:** yes, reproduced by all three browser requests and health probes.
- **Recommended next atomic task:** reconcile the authoritative supported-Compose local model selection so backend and chat worker request the inventory-advertised logical target, then rerun the same proof without changing provider or fallback policy.

### F2 — required-service profile projection is internally inconsistent

- **Observed:** required document worker retained friends/family, local-only false, cloud true, and `deepseek` egress while backend/chat worker reported the supported local profile.
- **Expected:** every required Tier-0 service participating in the supported path reflects the same local-only/cloud-disabled profile contract.
- **Governing contract/invariant:** ADR-069 and supported-profile critical-service configuration.
- **Evidence:** selected environment values from the three running containers.
- **Suspected subsystem:** Compose overlay coverage/effective configuration projection.
- **Deterministic:** yes on the rendered and running configuration.
- **Recommended next atomic task:** defer as acceptance within F1's single supported-configuration reconciliation task; do not split implementation before that prerequisite is scoped.

### F3 — successful chat, assistant persistence, and restart assistant readback are blocked

- **Observed:** all requests failed before first output; no assistant row exists.
- **Expected:** cold and warm local completions, assistant persistence, contextual continuation, and post-restart reconstruction.
- **Governing contract/invariant:** accepted supported chat, PostgreSQL durable truth, and browser/API/persistence proof separation.
- **Evidence:** task terminal events, browser transcript, messages API, `chat_messages`.
- **Suspected subsystem:** downstream consequence of F1.
- **Deterministic:** yes.
- **Recommended next atomic task:** no independent repair task; rerun these acceptance surfaces after F1.

### F4 — first terminal failure was not delivered coherently to the browser

- **Observed:** backend terminal failure occurred about 6.5 s after acceptance, while the initial browser remained `Queued` until its 300-second hard timeout and temporarily rendered `No messages yet` before reload.
- **Expected:** the terminal failure event clears generating state and renders an explicit failure promptly.
- **Governing contract/invariant:** browser-visible completion must agree with backend/domain terminal truth.
- **Evidence:** task SSE, durable outbox, Playwright snapshots, console timeout warning.
- **Suspected subsystem:** initial-thread task-event subscription/reconstruction timing.
- **Deterministic:** not established; subsequent failures rendered `Failed` promptly.
- **Recommended next atomic task:** defer independent triage until F1 is repaired and this same first-thread path is reproduced; do not widen the immediate task beyond F1.

### F5 — document-level retrieval provenance is incomplete

- **Observed:** persisted trace proves project-scoped execution and one project-document hit, but also says `retrieval_status=no_candidates` with zero document provenance items; no model answer exists to corroborate use.
- **Expected:** attributable document/chunk provenance sufficient to prove the synthetic fact entered completion context.
- **Governing contract/invariant:** workspace-scoped retrieval must not be inferred from a lucky answer or aggregate count alone.
- **Evidence:** `chat_threads.metadata`, ContextBroker log, unavailable debug trace projection, failed retrieval task.
- **Suspected subsystem:** retrieval trace publication/provenance projection; completion remains blocked by F1.
- **Deterministic:** one observed request; not enough for a separate defect claim.
- **Recommended next atomic task:** rerun provenance after F1; only open a separate task if the contradiction persists with a successful completion.

### F6 — lock acquisition proof is incomplete

- **Observed:** no lock remained after terminal failure and later requests on the same thread were accepted, but acquisition was not directly exposed in captured events/logs.
- **Expected:** observable acquisition and release evidence with no stale held lock.
- **Governing contract/invariant:** per-thread lock must serialize turns and release at terminal state.
- **Evidence:** Redis `EXISTS turn_lock:1 = 0`, queue depth 0, subsequent accepted tasks.
- **Suspected subsystem:** proof visibility, not an established lock defect.
- **Deterministic:** post-terminal absence is deterministic; acquisition proof is missing.
- **Recommended next atomic task:** include bounded lock observation in the F1 rerun; no code change is justified by this evaluation.

### F7 — static release-boundary and frontend lifecycle validation did not close cleanly

- **Observed:** focused backend suite produced 151 passes and 5 failures; two large Guardian lifecycle Vitest files exhausted the 4 GiB Node heap or hung and were terminated. Smaller focused frontend files produced 32 passes.
- **Expected:** focused governing static checks complete cleanly.
- **Governing contract/invariant:** static validation is surface-specific proof and cannot override live failure.
- **Evidence:** validation command ledger below.
- **Suspected subsystem:** four current-state wording expectations plus supported-profile `release_hold` expectation; test-runner memory behavior for large frontend files.
- **Deterministic:** backend failures reproduced once; frontend large-file OOM reproduced in grouped and isolated lifecycle runs.
- **Recommended next atomic task:** do not mix these into the prerequisite runtime repair; preserve as follow-up evidence after F1.

## Command and validation ledger

Commands are shown without secret values. Local API keys were obtained transiently through the repository helper and never printed or persisted.

| Command / action | Exit | Result |
|---|---:|---|
| `git status --porcelain=v2 --branch`; `git rev-parse HEAD`; `git rev-parse @{upstream}`; `git rev-list --left-right --count origin/main...HEAD` | 0 | Exact repository identity recorded |
| `make PYTHON=.venv/bin/python canonical-audit-evidence-identity repo=. machine_id=vaultnode machine_role=canonical_evidence_host authority_basis=operator-approved-current-tip-eval assert_canonical_machine=1` | 1 | Correctly rejected trusted-canonical status: `commit_upstream_mismatch`, `dirty_worktree` |
| focused `pytest -v` over release boundary, supported-profile, canonical receipt, Compose contract, live-proof contract, and workspace proof contract files | 1 | 151 passed, 5 failed: four current-state classification assertions and one `release_hold` startup expectation |
| supported-profile `docker compose ... config --quiet` render | 0 | Render syntactically valid; selected env inspection exposed required-service drift |
| first `docker compose up -d --build ...` with temporary supported env file | 1 | Harness-only failure: missing Neo4j password handoff caused `graph-init` exit 1 |
| `docker compose -f docker-compose.yml -f docker-compose.whooshd-smoke.yml up -d --build db redis migrator backend worker-chat worker-document-embed frontend` with command-scoped supported flags | 0 | Required processes started; live chat health still failed |
| `docker compose ... ps --all --format json`; selected `docker inspect`; service logs | 0 | Required service and diagnostic evidence captured |
| host HTTP probes for backend, frontend, and Whoosh'd | 0 | Core/frontend/Whoosh'd reachable; chat/LLM projections unhealthy/down |
| read-only PostgreSQL queries for Alembic, threads, messages, documents, retrieval trace, and outbox | 0 after corrected table/column queries | Durable evidence recorded; exploratory queries against the legacy `messages` table and one quoted JSON query failed and were corrected without mutation |
| Redis queue/lock/event inspection | 0 | queue depth 0; `turn_lock:1` absent after terminal; task streams observed before expiry |
| Playwright CLI headed browser actions: open, resize, snapshots, screenshots, console, request inspection, chat submissions, document upload, reload/direct re-entry | 0 for supported commands | Real UI exercised. `network` was not a CLI command and was corrected to `requests`; one malformed `run-code` wait was discarded |
| `.venv/bin/python scripts/proofs/prove_workspace_obsidian_e2e.py --help` | 1 | Script has no help-only path; it executed preflight and stopped on unhealthy `/health/chat` before proof mutation |
| canonical live-proof receipt collector with both Compose files and serving project `codexify` | 1 | Schema validation passed; receipt outcome `FAIL` for upstream/dirty authority plus LLM/runtime/release hold |
| `docker compose ... restart backend worker-chat worker-document-embed frontend` | 0 | Safe restart; no volumes affected; API/frontend 200 after about 18.5 s |
| `pnpm test --run ...` from `frontend/src` | 1 | Invalid pnpm option; corrected to direct Vitest invocation |
| grouped focused `pnpm exec vitest run ...` | 130 | a worker exceeded the 4 GiB heap; remaining hung process was stopped |
| individual `ProviderSelect.catalog`, `useTaskEvents`, `DocumentsView.interactions`, and `test/useRuntimeHealth` Vitest files | 0 | 5 + 4 + 7 + 16 = 32 tests passed |
| isolated `GuardianChat.lifecycle-timing` | 1 | worker heap OOM; no trustworthy test result |
| isolated `GuardianChat.turn-lock-lifecycle` | 130 | no progress after the companion OOM; terminated rather than left running |
| `.venv/bin/python scripts/validate_docs.py` | 0 | Architecture document, README-link, and source-heading validation passed |
| `git diff --check -- docs/architecture/proofs/supported-compose/2026-09-21-current-tip-end-to-end-eval.md` | 0 | No whitespace errors |

Playwright produced three meaningful screenshots: initial degraded state, first-request hard-timeout state, and explicit later failure state. To honor the one-repository-file allowlist, session artifacts were retained outside the repository under `/private/tmp/codexify-current-tip-eval-playwright-20260921/` and were not staged.

## Invariants check

- PostgreSQL remained canonical durable application truth for thread, message, document, ownership, retrieval-trace, and durable outbox observations.
- Redis was not treated as competing durable domain truth.
- Browser visibility was checked separately from API, queue, worker, and PostgreSQL evidence.
- Provider identity remained `local`; Whoosh'd runtime metadata remained separately represented.
- The disposable document is attributable by filename, marker, owner `local`, and project `1`.
- Authentication, ownership, project, thread, and retrieval boundaries were not weakened.
- No fail-closed check was bypassed.
- No mock substituted for the live path.
- No cloud provider or browser network host was used.
- No runtime defect was repaired.
- No volume was destroyed and `docker compose down -v` was not used.

## ADR impact and documentation follow-through

This evaluation is aligned with ADR-069, ADR-041, ADR-042, and the existing provider, persistence, queue, identity, retrieval, and event contracts. It changes no ADR and makes no architecture decision.

This result would justify a later human-approved current-state update only to record the current-tip `HOLD`, the executable-model mismatch, and the bounded healthy sub-surfaces. It does **not** justify upgrading supported-runtime qualification or widening Beta claims. `docs/architecture/00-current-state.md` was intentionally not modified.

## Single highest-priority follow-up seam

The next atomic Task Spec should address only the authoritative supported-Compose local model/config projection: make the backend and chat worker resolve the same inventory-advertised logical local target under `v1-local-core-web-mcp`, without enabling cloud fallback or weakening strict resolution, and prove `/health/chat`, `/api/health/llm`, one cold turn, and one warm turn before reopening downstream retrieval/event questions.
