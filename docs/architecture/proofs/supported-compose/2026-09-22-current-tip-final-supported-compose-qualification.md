# Current-tip final supported-Compose qualification

Date: 2026-09-22
Qualification lane: architecture-impact, verification only
Final verdict: **HOLD**
Evaluated revision: `5da79431fa059b7da80688380550cf29d4854b18`
Branch: `main`
Upstream at evaluation: `origin/main` at
`6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2`
Divergence at evaluation: ahead 9 / behind 0
Supported profile: `v1-local-core-web-mcp`
Provider / logical model: `local` / `local-chat`

## Qualification answer

The repaired tip passed the supported topology, migration, health, real-browser
cold and warm turns, terminal browser convergence, durable conversation,
reload/re-entry, document ingestion, embedding, project retrieval, durable
document/chunk provenance, queue/worker lifecycle, turn-lock, F1-F7 governing
static, and canonical live-receipt surfaces.

The qualification nevertheless remains **HOLD** because the bounded
fail-closed lane found one current prerequisite defect. An authenticated
completion request explicitly selected unavailable local model
`missing-local-model-A7K9`. The accepted task did not reject that exact target.
It executed `local-chat`, persisted assistant message `61`, and emitted
`task.completed`. Durable selection metadata states that the requested model
was overridden by configured `local-chat`, while execution metadata says
`fallback_triggered=false`. This is not cloud fallback, but it is an exact-model
substitution and a false successful result for a request that the accepted
fail-closed contract requires to reject.

No repair was attempted. Once that contradiction was durable, the task's stop
gate prohibited further runtime mutation. The planned application-service
restart and post-restart ordinary chat were therefore not run.

## Orientation receipt

- Role: Axis-capable Codex implementation agent.
- Interaction mode: `ORIENT` -> `EXECUTE` -> `PROOF`.
- Repository root: `/Volumes/Dev_SSD/Codexify-main`.
- Current-truth authority used: `docs/architecture/00-current-state.md`, then
  governing ADRs/contracts, then task criteria, then current code and tests.
- Architecture authority: ADR-069, ADR-041, ADR-042, ADR-074, ADR-087, the
  canonical live-proof receipt contract, and the chat/runtime contracts named
  by the task.
- Scope: one exact current-tip supported-Compose qualification. The only
  authorized repository mutation was this proof file.
- Pre-existing state preserved: staged deletion of
  `docs/DEV_LOG/2026-09-22/Dev Log - 2026-09-22.md`.

## Scope and evidence boundaries

This run rebuilt and observed the supported Compose project, created only
disposable evaluation data, drove the real web UI with headed Playwright,
inspected PostgreSQL and Redis read-only, ran the declared static gates, and
collected the existing canonical live-proof receipt. It did not change source,
tests, runtime configuration, `.env`, ADRs, release truth, Whoosh'd mapping, or
volumes. It never ran `docker compose down`, `down -v`, or a volume-removal
command. It did not push.

The frozen runtime revision remained
`5da79431fa059b7da80688380550cf29d4854b18` through all live evaluation and
static validation. The proof commit created after evaluation is evidence
packaging, not the evaluated runtime revision.

## Repository and host identity

| Surface | Observed value |
| --- | --- |
| Host | `VaultNode.local`, macOS 27.2, arm64 |
| Branch | `main` tracking `origin/main` |
| Evaluated HEAD | `5da79431fa059b7da80688380550cf29d4854b18` |
| Upstream | `6aa2d137eb3afc7d3d150f6533ce6ade36adf4e2` |
| Ahead / behind | 9 / 0 |
| Initial unrelated state | staged deletion of the 2026-09-22 Dev Log only |
| Docker | client 29.8.0; engine 29.8.0; Docker Desktop 4.92.0 (240144) |
| Compose | v5.5.1; context `desktop-linux` |
| Node / pnpm / Vitest | v25.9.0 / 9.12.1 / 4.1.11 |
| Python / pytest | 3.12.13 / 8.4.2 |

The direct rendered-Compose SHA-256 was
`dad71e60ce9481db74eed5b25fd32571ba4c3dc519c641d1bd0af0fd3ce0eeed`.
The receipt collector's normalized effective-config hash was
`151aff39fdd379d3982ca8646467b9ca5944d9a6ab4eb37435210ecf25327653`.
They hash different canonical forms and are recorded separately.

## Supported topology and startup

The supported render used, in order:

```text
docker-compose.yml
docker-compose.whooshd-smoke.yml
```

`docker compose ... config --quiet` passed. Required-service projection for
`backend`, `worker-chat`, and `worker-document-embed` agreed on:

```text
CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp
LLM_PROVIDER=local
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_EGRESS_ALLOWLIST=
LOCAL_CHAT_MODEL=local-chat
LOCAL_LLM_MODEL=local-chat
DEFAULT_LOCAL_MODEL=local-chat
LLM_MODEL=local-chat
LOCAL_PROVIDER_VENDOR=whooshd
```

The catalog additionally reported runtime preset `whooshd-mlx`. Cloud-provider
credential projections were blank in the safe rendered inspection.

The exact-tip rebuild/recreate command was:

```text
docker compose -p codexify \
  -f docker-compose.yml \
  -f docker-compose.whooshd-smoke.yml \
  up -d --build --force-recreate \
  db redis neo4j graph-init migrator model-prep \
  backend worker-chat worker-document-embed frontend
```

It exited 0 without destroying volumes. `graph-init`, `migrator`, and
`model-prep` exited 0. PostgreSQL, Redis, Neo4j, and backend were healthy;
frontend and both workers were running. From first recreated container start
(`17:02:37.981Z`) to the last required worker start (`17:03:39.309Z`) was
61.328 seconds. From the pre-start evidence timestamp (`17:02:12Z`) to the last
required process start was 87.309 seconds, including build/pre-create work.

The live Alembic revision was `a8d4c2f6b1e9`. Required PostgreSQL tables,
including `chat_threads`, `chat_messages`, `uploaded_documents`,
`project_document_links`, `thread_documents`, and `events_outbox`, were present.

Startup logs contained existing SQLAlchemy relationship warnings, a Vite
duplicate-style warning, and one logging-format exception during the ChatGPT
import sweep. They did not prevent health, chat, ingestion, or persistence.
They are not used to dilute the fail-closed defect below.

## Health, provider, and inventory

At the consolidated probe:

- frontend at `http://[::1]:5173/` returned HTTP 200;
- `/ping` returned `Guardian awake!`;
- `/health` returned `status=ok`, supported profile valid, no mismatches,
  selected provider `local`, and `release_hold=false`;
- `/health/chat` returned `ok=true`, `status=healthy`, Redis reachable, fresh
  worker heartbeat, queue depth 0, provider `local`, model `local-chat`, strict
  model resolution, and the selected Whoosh'd endpoint;
- `/api/health/llm` returned `ok=true`, `status=online`, provider `local`, model
  `local-chat`, discovered inventory available, and supported profile valid;
- authenticated `/api/llm/catalog` exposed one enabled provider, `local`, shown
  as `Whoosh'd`, and one model, canonical `local-chat`, shown as
  `Gemma 4 12B IT QAT 4-bit`;
- Whoosh'd `/health` returned `ok=true`, `status=ready`, version `0.1.0rc3`,
  queue depth 0, and active jobs 0;
- Whoosh'd `/v1/models` advertised `local-chat`, owned by `whooshd`, with
  display name `Gemma 4 12B IT QAT 4-bit`, engine `mlx_vlm`, and authoritative
  registry resolution.

The physical display model is observational Whoosh'd metadata. The Codexify
supported route remains logical `local-chat`.

Port 5173 also had an unrelated IPv4-only host process. The Compose UI was
therefore addressed explicitly through Docker's IPv6 listener at
`http://[::1]:5173`. The unrelated process was not altered.

## Real-browser chat qualification

Headed Playwright opened the real supported frontend and established the
normal local API-key session without printing or persisting the key. The idle
shell showed `Ready`; provider and model controls showed `Whoosh'd` and
`Gemma 4 12B IT QAT 4-bit`.

The disposable live object set was:

| Object | Identity |
| --- | --- |
| Project | `1` (`General`) |
| Evaluated thread | `11` |
| Cold task | `712c5441-609d-42eb-bb40-d980a8a8e567` |
| Warm task | `11302bc7-6690-47a2-9f00-db6188956710` |
| Upload-turn task | `189b6c0f-e49e-43e5-8af3-8af7556a622f` |
| Retrieval task | `8599e6e8-61dd-46dd-ae68-1890fc85cfe4` |
| Uploaded document | `aa57d818-45f7-49ae-b83e-f60381483adb` |
| Fail-closed probe thread | `12` |
| Fail-closed probe task | `a1333dcc-8f16-4f52-a18c-e0da54c037b2` |

### Cold and warm turns

| Turn | Browser input contract | Durable result | Task duration | Terminal browser evidence |
| --- | --- | --- | ---: | --- |
| Cold | exact `COLD_OK_A7K9` reply | message 53, provider `local`, model `local-chat`, exact content | 73,070 ms | one exact assistant token; shell `Ready`; zero `Queued` labels |
| Warm | derive the prior reply's last four characters and prepend `WARM_OK_` | message 55, exact `WARM_OK_A7K9` | 22,511 ms | one exact assistant token; shell `Ready`; zero `Queued` labels |

Cold task timing was queued `17:12:25.889529Z`, first token
`17:13:35.381360Z`, completed `17:13:37.552044Z`. The browser submission was
`17:12:25.026Z` and terminal confirmation was captured at `17:13:48.219Z`.
Warm task timing was queued `17:15:37.722892Z`, first token
`17:15:58.602662Z`, and completed `17:15:59.951260Z`.

Post-completion reload preserved exactly one cold result and exactly one warm
result. The shell remained `Ready` and exposed no `Queued` projection. The run
navigated to Dashboard and re-entered thread 11 through its actual thread
button; both assistant results again reconstructed exactly once.

The only initial console errors were two favicon 404s. During longer local
inference the UI emitted its expected 15-second slow-path warning. Neither
altered terminal projection or persisted truth. After later navigation the
browser reported zero console errors.

## Document ingestion, retrieval, and durable provenance

The browser attached and submitted
`codexify-final-qualification-20260922-a7k9.txt`. Its unique body marker was
`CODEXIFY_FINAL_DOC_A7K9`; its synthetic fact was ceremonial routing color
`VIOLET-4731`.

PostgreSQL recorded:

| Field | Value |
| --- | --- |
| Document ID | `aa57d818-45f7-49ae-b83e-f60381483adb` |
| Project / thread | 1 / 11 |
| MIME / size | `text/plain` / 180 bytes |
| Created | `2026-09-22T17:20:28.805847Z` |
| Embedding start | `2026-09-22T17:20:29.045271Z` |
| Embedding complete | `2026-09-22T17:20:30.272039Z` |
| Embedding status | `ready` with no error |
| Project link | enabled uploaded-document link, row 5 |

The real Documents surface showed the exact filename and `Ready` before the
retrieval request. Back in thread 11 with retrieval source `Project`, the
browser asked for the marked document's ceremonial routing color and received
exactly `VIOLET-4731`. The retrieval task completed in 29,017 ms and persisted
assistant message 59.

Message 59 `extra_meta.retrieval_provenance` named the target document ID and
filename, `chunk_index=0`, `source_type=uploaded`, project 1, thread 11, and the
eligible `thread_docs` and `project_docs` lanes. The terminal
`task.completed` outbox row 135 persisted the same target and chunk identity.
A machine comparison of the complete message provenance object and complete
terminal outbox provenance object returned `exact_equal=true`.

## Queue, worker, lock, and event coherence

The chat queue began and ended at depth 0 with a fresh worker heartbeat. Each
evaluated request had one task ID, one attempt ID, one assistant message, and
one terminal `task.completed` row. No retry or duplicate terminal assistant
write was observed.

Redis directly exposed `turn_lock:11` while requests were active:

- 30 consecutive half-second samples during the cold turn;
- 20 during the warm turn;
- 16 during the upload turn; and
- 20 during the retrieval turn.

The key was absent after each terminal state. The same thread immediately
accepted the next request, and no `turn_lock:*` key remained after retrieval.

For retrieval task `8599e6e8-61dd-46dd-ae68-1890fc85cfe4`, the authenticated
task stream preserved the monotonic sequence:

```text
task.created
QUEUED                     2026-09-22T17:23:53.608201Z
task.running
AWAITING_MODEL             2026-09-22T17:23:54.854604Z
AWAITING_FIRST_TOKEN       2026-09-22T17:23:54.880433Z
STREAMING                  2026-09-22T17:24:20.324674Z
COMPLETED                  2026-09-22T17:24:21.791348Z
task.completed
```

Run ID was `5edcc2b5bf5a4cf4871d7a297d086034`, attempt ID was
`attempt_49335557b3c5491c88b41f98cfd94264`, persisted assistant message was 59,
and outbox terminal row was 135. The browser projected the same terminal truth
as `Ready` with exact answer content and no active/queued label.

## First prerequisite defect: exact-model fail-closed substitution

The strongest accepted safe fail-closed surface was the same authenticated
completion API used by the browser. A disposable thread received user message
60, then the completion request specified:

```json
{
  "provider": "local",
  "model": "missing-local-model-A7K9",
  "source_mode": "project",
  "reasoning_mode": "no_think"
}
```

The route returned HTTP 200 with `acceptance_status=accepted` and task
`a1333dcc-8f16-4f52-a18c-e0da54c037b2`. It then progressed through queued,
awaiting-model, awaiting-first-token, streaming, and completed rather than
failing. The terminal evidence is internally explicit:

| Durable field | Value |
| --- | --- |
| Requested / attempted model | `missing-local-model-A7K9` |
| Resolution message | requested model was overridden by configured `local-chat` from `LOCAL_CHAT_MODEL` |
| Resolved / final model | `local-chat` |
| Attempted / final provider | `local` / `local` |
| Fallback flag | `false` |
| Completion truth | accepted, attempted, executed, completed all `true` |
| Persisted assistant | message 61 |
| Terminal evidence | `task.completed`, outbox row 140, duration 36,447 ms |

The system stayed local-only and made no cloud fallback. That does not satisfy
the required behavior: the unavailable exact target was not rejected, and a
false assistant success persisted. ADR-074 requires explicit exact selection
to fail closed on inventory disagreement and prohibits silent substitution.
The durable resolution message makes the substitution diagnosable after the
fact, but neither the accepted task nor the user-facing terminal result failed
closed.

The focused contract check also exposed a current static mismatch:

```text
.venv/bin/python -m pytest -p no:cacheprovider -v \
  guardian/tests/workers/test_chat_worker_provider_resolution.py::test_explicit_model_unavailable_fails_instead_of_fallback \
  tests/core/test_ai_router.py::test_strict_explicit_provider_model_preserves_exact_model_and_token_bound
```

Result: 1 passed / 1 failed. The strict router test passed. The explicit-model
worker test did raise `LLMConfigError`, but with `Provider blocked by egress
policy` rather than its required `Requested model 'missing-model' is not
available` failure, so the contract assertion failed. The governing F7
ten-file suite remains green; this focused failure is evidence on the newly
discovered fail-closed seam, not a reason to rewrite the F7 accounting.

Per the task stop conditions, no further runtime mutation was allowed after
this contradiction. Service restart/recovery and the required post-restart
ordinary chat are `BLOCKED`, not inferred and not claimed.

## Governing static and structural validation

| Gate | Result |
| --- | --- |
| Reconciled ten-file backend supported-path suite | **PASS** — 157 passed, 0 failed, 8 warnings, 23.58 s |
| Focused exact-model fail-closed contracts | **FAIL** — 1 passed, 1 failed as detailed above |
| Guardian lifecycle timing + turn-lock, ordinary config | **PASS** — 2 files, 11/11 tests, 2.68 s; no OOM or hang |
| Neighboring supported frontend group | **PASS** — 7 files, 83/83 tests, 3.21 s |
| Documentation validation | **PASS** — required architecture docs, README links, and source headings |
| `git diff --check` and cached diff check before proof | **PASS** |

The 83-test neighboring command covered provider catalog/select, Guardian shell
terminal projection, Guardian sidebar stability, `useChat`,
`useInferenceRequestState`, `useTaskEvents`, and the combined runtime-health
test surface. The only recurring output was the known Node
`--localstorage-file` warning.

## Canonical live-proof receipt

The read-only collector observed the already-running `codexify` serving
project with both Compose files. It produced:

| Field | Value |
| --- | --- |
| Receipt ID | `live-proof-receipt-sha256-f23645791848f3d9125b34daba8a429e7fcb30a1e27d74b67ca7fede79dba902` |
| Collector result | `pass` |
| Execution outcome | `PASS` |
| Schema validation | `pass`; zero issues |
| Authority status | `PROVISIONAL` |
| Reason codes | `commit_upstream_mismatch`, `dirty_worktree` |
| Evaluated repository commit | `5da79431fa059b7da80688380550cf29d4854b18` |
| Migration head | `a8d4c2f6b1e9` |
| Collection interval | `17:36:03.279918Z` to `17:36:04.781358Z` |

Receipt trust is separate from the runtime verdict. Its health-oriented
execution `PASS` accurately records the observed supported topology; it does
not exercise or override the exact-model fail-closed failure. It remains
provisional because the evaluated commit is ahead of upstream and the
pre-existing staged deletion makes the worktree dirty.

## Evaluation matrix

Runtime rows use `PASS`, `FAIL`, `INSUFFICIENT PROOF`, or `BLOCKED`. The receipt
row additionally preserves its native authority status.

| Evaluation row | Status | Evidence |
| --- | --- | --- |
| repository identity | **PASS** | Frozen `main` at `5da79431...`; upstream `6aa2d137...`; ahead 9 / behind 0; unchanged through live/static evaluation |
| supported profile/config | **PASS** | Two-file render valid; required services agree on supported local-only/cloud-disabled `local-chat` posture |
| startup/readiness | **PASS** | Exact-tip rebuild/recreate exited 0; init jobs 0; required services running/healthy without volume destruction |
| migrations | **PASS** | Live Alembic `a8d4c2f6b1e9`; required tables present |
| backend health | **PASS** | `/ping` and `/health` healthy; profile valid; no mismatches |
| chat health | **PASS** | `/health/chat` healthy; Redis reachable; worker fresh; queue depth 0 |
| LLM health | **PASS** | `/api/health/llm` online for `local` / `local-chat` |
| Whoosh'd health | **PASS** | `0.1.0rc3`, ready, zero queued/active jobs |
| Whoosh'd inventory | **PASS** | Advertised `local-chat`; authoritative registry; Gemma display metadata |
| catalog/provider identity | **PASS** | Authenticated catalog: `Whoosh'd`, `local`, `local-chat`, `whooshd-mlx` |
| browser auth/session | **PASS** | Real supported UI loaded through normal local API-key session; protected requests 200 |
| idle provider projection | **PASS** | Shell showed `Ready`; provider/model identity separate from request lifecycle |
| cold chat | **PASS** | Exact `COLD_OK_A7K9`; local/local-chat; durable 73,070 ms terminal |
| warm contextual | **PASS** | Derived `WARM_OK_A7K9`; durable 22,511 ms terminal |
| terminal browser convergence | **PASS** | One exact assistant result per turn; `Ready`; no stale `Queued` |
| durable conversation | **PASS** | Messages 52-59 persisted in thread 11 with task/request/attempt correlation |
| reload/re-entry | **PASS** | Reload plus Dashboard thread re-entry reconstructed cold/warm exactly once |
| document upload | **PASS** | Browser-submitted specimen persisted as `aa57d818...` in project 1/thread 11 |
| embedding readiness | **PASS** | `ready`, no error; completed in 1.227 s; Documents UI showed Ready |
| workspace/project retrieval | **PASS** | Project source returned exact unique fact `VIOLET-4731` |
| doc/chunk provenance | **PASS** | Target document ID/name plus chunk 0 persisted for thread/project document lanes |
| provenance persistence agreement | **PASS** | Full assistant and terminal-outbox provenance objects machine-compared equal |
| queue progression | **PASS** | Queue accepted and progressed each task; depth returned to 0 |
| worker execution | **PASS** | Single run/attempt/message/terminal per evaluated successful task; no unexplained retry |
| lock acquisition | **PASS** | `turn_lock:11` directly sampled during four active requests |
| lock release | **PASS** | Lock absent after terminal; same thread accepted subsequent turns |
| lifecycle/event coherence | **PASS** | Monotonic queued -> awaiting model -> awaiting first token -> streaming -> completed; browser and persistence agreed |
| bounded fail-closed | **FAIL** | Unavailable exact model was overridden by `local-chat`; false assistant success and `task.completed` persisted |
| restart recovery | **BLOCKED** | Stop gate prohibited further runtime mutation after the fail-closed contradiction |
| post-restart ordinary chat | **BLOCKED** | Restart was not authorized after the stop gate; no claim made |
| backend suite | **PASS** | Governing declared bundle 157/157 |
| Guardian lifecycle | **PASS** | 11/11 together under ordinary Vitest config; no OOM/hang |
| neighboring frontend | **PASS** | 83/83 across seven supported-path files |
| docs validation | **PASS** | Architecture/link/source-heading validator and diff checks passed |
| canonical receipt | **PASS / PROVISIONAL** | Execution and schema pass; provisional for upstream mismatch and dirty worktree |

## F1-F7 disposition

| Finding | Final integrated disposition | Current-tip evidence |
| --- | --- | --- |
| F1 — supported local model projection | **CLOSED** | Supported route and all four aliases are `local-chat`; Whoosh'd owns physical mapping |
| F2 — required-service profile projection | **CLOSED** | Backend and both workers agree on profile, local-only, cloud-disabled, no-egress posture |
| F3 — successful chat / assistant persistence | **DOWNSTREAM RESOLVED** | Cold/warm/upload/retrieval assistant messages persisted with exact terminal correlation |
| F4 — browser terminal-task projection | **CLOSED** | Real browser returned to `Ready`, removed active lifecycle state, and never retained stale `Queued` |
| F5 — durable retrieval provenance | **CLOSED** | Exact target document/chunk persisted identically on assistant and terminal task evidence |
| F6 — turn-lock acquisition/release | **CLOSED** | Lock observed during execution, absent after terminal, same-thread continuation worked |
| F7 — governing static/lifecycle reliability | **CLOSED for its declared bundle** | Backend 157/157, lifecycle 11/11, neighboring frontend 83/83; no OOM/hang |

F1-F7 closure does not convert this run to `GO`: the final qualification has an
additional required fail-closed row, and that row failed.

## Command and action ledger

Secret values were obtained only through the repository's local helper and
were never printed or persisted.

| Command / action | Result |
| --- | --- |
| `git status --porcelain=v2 --branch --untracked-files=all`; HEAD/upstream/divergence probes | Exact evaluated identity recorded; only the pre-existing staged Dev Log deletion present |
| full required architecture/proof-chain reads | Completed before runtime action; historical proof was not substituted for current evidence |
| `docker compose -p codexify -f docker-compose.yml -f docker-compose.whooshd-smoke.yml config --quiet` plus safe render/hash | Exit 0; coherent supported render; direct hash recorded |
| host Whoosh'd `/health` and `/v1/models` preflight | Ready `0.1.0rc3`; `local-chat` advertised |
| exact-tip `docker compose ... up -d --build --force-recreate ...` | Exit 0; no destructive reset; init jobs exited 0 |
| Compose `ps -a`, selected `docker inspect`, startup/error log review | Required services ready; startup timestamps and bounded warnings recorded |
| frontend, backend, chat, LLM, catalog, and Whoosh'd HTTP probes | All supported readiness/identity probes passed |
| PostgreSQL Alembic/table queries | Head `a8d4c2f6b1e9`; required durable tables present |
| first headed Playwright open inside sandbox | Blocked by macOS crashpad permission; rerun with approved GUI access succeeded; not a product failure |
| Playwright cold send plus 30 Redis lock samples | Exact cold result passed; lock directly observed |
| Playwright warm send plus 20 Redis lock samples | Exact contextual result passed; same-thread continuation proved |
| Playwright reload, Dashboard navigation, and thread-button re-entry | Durable transcript reconstructed exactly once; `Ready`; zero `Queued` |
| temporary specimen creation under `/private/tmp` and Playwright attachment/send | Real upload passed; no repository artifact created |
| PostgreSQL document/project-link inspection and Documents UI readback | Document embedded `ready`, enabled, visible as Ready |
| Playwright project retrieval plus 20 Redis lock samples | Exact `VIOLET-4731` result passed |
| assistant/outbox provenance extraction and `jq` object equality | Exact equality `true`; target document/chunk identity present |
| authenticated retrieval task-event stream | Monotonic lifecycle through completed; identifiers/timestamps recorded |
| authenticated unavailable exact-model completion probe | HTTP 200 accepted, executed `local-chat`, persisted false success: qualification failure |
| post-defect `/health/chat` and Whoosh'd probes | Runtime still healthy/idle and local-only; this does not cure the failed request contract |
| narrow service restart and post-restart chat | Not run: `BLOCKED` by explicit stop gate after runtime contradiction |
| exact ten-file backend governing pytest command | 157 passed / 0 failed / 8 warnings |
| focused exact-model worker/router pytest command | 1 passed / 1 failed; failure detail preserved above |
| combined Guardian lifecycle/turn-lock Vitest command | 11/11 passed; no OOM/hang |
| seven-file neighboring Vitest command | 83/83 passed |
| `.venv/bin/python scripts/validate_docs.py` | Passed before proof drafting |
| `git diff --check`; `git diff --cached --check` | Passed before proof drafting |
| canonical live-proof collector with both Compose files | Execution PASS; schema pass; authority PROVISIONAL |
| initial oversized combined probe | Output was tool-truncated; every required probe was rerun in bounded blocks and only rerun evidence was used |
| exploratory PostgreSQL quoted-table and empty-JSON queries | Two quoting/syntax attempts failed; corrected read-only queries succeeded; no mutation occurred |
| Playwright-generated repository snapshots | Four untracked snapshots and one ignored console log were removed exactly; final repository scope returned to the pre-existing staged deletion plus this proof |

## ADR impact and documentation follow-through

No ADR or accepted contract changed. The observed live substitution contradicts
ADR-074's existing exact-model fail-closed authority; it does not justify
weakening or rewriting that doctrine.

`docs/architecture/00-current-state.md` and all release/publication surfaces
remain intentionally untouched. Because the verdict is `HOLD`, the first and
only prerequisite is an atomic repair of the accepted chat-completion
exact-model path so an unavailable explicitly requested local model terminates
as a bounded failure before provider execution or assistant persistence, with
consistent task/event and regression-test evidence. After that repair, rerun
this qualification from a newly frozen exact tip, including the restart and
post-restart rows.

## Known limitations and release accounting

- Restart persistence was previously proven historically but is not current-tip
  proof for this run; the required restart rows are `BLOCKED` here.
- The canonical receipt is provisional and is not release/canonical evidence.
- The supported stack and disposable evaluation records remain available for
  inspection; volumes were preserved.
- This proof does not widen Beta support, declare deployment/publication, or
  change private-preview and other release gates.
- Only merged local `main` runtime truth is described. This proof commit itself
  packages evidence and is not a claim that upstream or publication advanced.

## Final verdict

**HOLD** — exact current-tip supported Compose is coherent across the repaired
F1-F7 path, but the accepted exact-model request surface does not fail closed
for an unavailable local target. It substitutes `local-chat` and persists a
successful assistant result. That first prerequisite defect must be repaired
and the full frozen-tip qualification rerun before `GO` can be considered.
