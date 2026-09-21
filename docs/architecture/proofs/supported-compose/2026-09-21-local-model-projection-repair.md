# Supported local model projection repair proof — 2026-09-21

## Bounded verdict

**Result: `PASS`**

The supported Whoosh'd-backed Compose path now owns the logical
`local-chat` route instead of inheriting the ambient physical model
`qwen3.8-27b-4bit`. Backend, chat worker, and document-embed worker project
one `v1-local-core-web-mcp`, local-only, cloud-disabled posture. Live health,
catalog, browser, queue/worker, terminal, API, and PostgreSQL evidence agree.

Two real browser turns completed in one disposable thread. The second answer
required context from the first. Both assistant rows are durable. Every
execution record names provider `local`, logical model `local-chat`, successful
terminal truth, and `fallback_attempted=false`.

This proof closes the bounded F1/F2 prerequisite from the preceding evaluation.
It does **not** change the preceding whole-evaluation `HOLD`, qualify the full
release, or update `docs/architecture/00-current-state.md`. The complete
current-tip supported-Compose evaluation must be rerun.

## Authority and scope

- Lane: Architecture-Impact; modes: `EXECUTE`, then `PROOF`.
- Governing decisions: ADR-069 and ADR-074, with current release truth from
  `docs/architecture/00-current-state.md`.
- State authority: PostgreSQL remained canonical durable application truth;
  Redis/task state was used only as runtime evidence.
- Provider/runtime separation: `local` is the provider/policy identity;
  `whooshd` / `Whoosh'd` is the runtime identity; `local-chat` is the logical
  route; the live physical display target was
  `Gemma 4 12B IT QAT 4-bit`.
- No runtime source, frontend, persistence, migration, retrieval, event, or
  architecture-contract implementation was changed.
- No volume was destroyed and `.env` was not modified.

## Repository and machine identity

| Field | Evidence |
|---|---|
| Evaluation window | 2026-09-21, approximately 12:30–13:16 EDT |
| Machine | `VaultNode.local`; Darwin arm64 |
| Repository | `/Volumes/Dev_SSD/Codexify-main` |
| Branch before repair | `main` |
| Commit before repair | `4cb262e64ffb44c6e2620242d9910068f1b87cd3` |
| Upstream | `origin/main` |
| Ahead / behind | ahead 21, behind 0 |
| Pre-existing dirty state | staged deletion of `docs/DEV_LOG/2026-09-21/Dev Log - 2026-09-21.md` |
| Preservation result | deletion remained staged, unmodified, and excluded from this task's commit |
| Supported profile | `v1-local-core-web-mcp` |
| Compose topology | `docker-compose.yml` plus `docker-compose.whooshd-smoke.yml` |

Before mutation there were no other staged, unstaged, or untracked paths. The
repair created only the authorized test and proof and modified only the
authorized Whoosh'd overlay.

## Configuration contradiction and repair

The repository `.env` was inspected without printing secrets. Its relevant
pre-existing values were:

```text
CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web
LLM_PROVIDER=deepseek
ALLOW_CLOUD_PROVIDERS=true
CODEXIFY_LOCAL_ONLY_MODE=false
CODEXIFY_EGRESS_ALLOWLIST=deepseek
LOCAL_CHAT_MODEL=qwen3.8-27b-4bit
```

The pre-repair supported render used command-scoped supported-profile flags but
did not pass `LOCAL_CHAT_MODEL`. Hash:
`6bf8325529914073c12d70b7fed9afac0fbe6c97ba006e8101f62ec3f2557327`.

| Service | Profile | Provider | Local only | Cloud allowed | Egress | Chat route |
|---|---|---:|---:|---:|---|---|
| backend | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | `qwen3.8-27b-4bit` |
| worker-chat | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | `qwen3.8-27b-4bit` |
| worker-document-embed | `v1-friends-family-web` | `local` | `false` | `true` | `deepseek` | `qwen3.8-27b-4bit` |

The repair makes the supported overlay authoritative for its own logical route:

- backend and worker-chat receive literal `local-chat` across the four model
  aliases used by the supported path;
- worker-document-embed receives the same supported-profile/provider/model
  overlay;
- all three required services receive local-only true, cloud false, empty
  egress, and blank cloud credential fields, preventing unrelated ambient
  `.env` values from creating a contradictory supported runtime;
- base Compose still transports `${LOCAL_CHAT_MODEL}` into backend and
  worker-chat, so accepted explicit exact-target behavior outside this
  supported overlay remains available and fail-closed.

No Gemma, Qwen, or other physical model was encoded as the supported default.

## Post-repair effective configuration

The exact post-repair render again omitted a command-line `LOCAL_CHAT_MODEL`.
Hash:
`dad71e60ce9481db74eed5b25fd32571ba4c3dc519c641d1bd0af0fd3ce0eeed`.

| Service | Profile | Provider | Local only | Cloud allowed | Egress | Four chat aliases | Cloud keys |
|---|---|---:|---:|---:|---|---|---|
| backend | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | all `local-chat` | all blank |
| worker-chat | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | all `local-chat` | all blank |
| worker-document-embed | `v1-local-core-web-mcp` | `local` | `true` | `false` | empty | all `local-chat` | all blank |

The same values were independently read from each recreated container. Required
runtime state was: PostgreSQL healthy, Redis healthy, migrator exit 0, backend
healthy, frontend running and serving the application, chat worker running with
a fresh heartbeat, and document-embed worker running. Volumes were preserved.

## Live inventory, health, and catalog agreement

| Surface | Result | Evidence |
|---|---|---|
| Whoosh'd `/health` | `PASS` | `ok=true`, `status=ready`, version `0.1.0rc3`, queue depth 0, active jobs 0 |
| Whoosh'd `/v1/models` | `PASS` | one advertised id `local-chat`, owned by `whooshd`; display `Gemma 4 12B IT QAT 4-bit`; engine `mlx_vlm`; resolution source `authoritative_registry` |
| Guardian `/health` | `PASS` | profile valid, no mismatches, selected provider `local`, cloud-capable configuration false, `release_hold=false` |
| Guardian `/health/chat` | `PASS` | `ok=true`, `status=healthy`, Redis ok, worker fresh, queue progressing/empty, configured model `local-chat`, strict source `LOCAL_CHAT_MODEL`, inventory contains `local-chat` |
| Guardian `/api/health/llm` | `PASS` | `status=online`, provider `local`, model `local-chat`, selected endpoint `host.docker.internal:8000`, profile valid, `release_hold=false` |
| Guardian `/api/llm/catalog` | `PASS` | provider id `local`; runtime id `whooshd`; runtime/display label `Whoosh'd`; logical model id `local-chat`; physical display label `Gemma 4 12B IT QAT 4-bit` |

Before the first turn, Whoosh'd reported `active_model=null` and inventory
provenance `model_lifecycle=unloaded`. These are observations, not an SLO or a
claim about residency after the request.

## Real browser proof

Playwright CLI drove headed Chrome against `http://127.0.0.1:5173`. The actual
Guardian surface rendered the runtime selector as provider `Whoosh'd`, model
`Gemma 4 12B IT QAT 4-bit`, while backend requests remained the logical
`local-chat` route. Artifacts were kept outside the repository under
`/private/tmp/codexify-local-model-projection-playwright-20260921/`.

The browser created project `1`, disposable thread `2`, submitted both turns,
rendered both assistant results, and reconstructed all four ordered messages
after a browser reload. The post-reload console contained no warnings or errors.
Browser request enumeration showed only the local application origin
`http://127.0.0.1:5173`; no cloud inference host appeared.

### Turn A — initial/cold path

| Field | Value |
|---|---|
| Prompt marker | `CODEXIFY_MODEL_PROJECTION_20260921_COLD_K7M4` |
| User / assistant messages | `4` / `5` |
| Task | `7a537e95-f7fe-41b2-8c4d-655cb4119861` |
| Run / turn | `26de14df4f3e4bf8ac05446c2e199b9e` / `c7a28dda-931a-400f-a3fa-35de5720d571` |
| Attempt / request | `attempt_34a615e0184f455ea0fa6ba93e0a9d72` / `req_4e7675e2ee92486cbe509bb18fdf9a6c` |
| Provider / logical model | `local` / `local-chat` |
| Browser output | exact marker rendered |
| Terminal state | one `task.completed`; status `success`; finish reason `stop` |
| Fallback | `false` |

Persisted timing gives queued-to-first-token `12.880 s` and queued-to-complete
`16.573 s`. The browser displayed the exact assistant output. The first
Playwright wait predicate expected the marker twice in the live DOM, but the
optimistic user row was not retained in that pre-reload DOM; the wait was
cancelled after backend completion and the assistant result was verified by
snapshot, API, database, and reload. No false timing is inferred from that
harness predicate.

### Turn B — warm contextual continuation

The second prompt asked for the four-character suffix from Turn A without
supplying the answer. The model returned exactly `WARM_CONTEXT_K7M4`, proving
same-thread conversational continuity.

| Field | Value |
|---|---|
| User / assistant messages | `6` / `7` |
| Task | `53171d1f-c173-4228-82e9-f2a38fa05884` |
| Run / turn | `fa5a29832af449399a8376c355e04245` / `4aa5241c-0463-4a31-baed-9b2294f2dc54` |
| Attempt / request | `attempt_f7605aff58a24e309a7698abecef6884` / `req_2b875054154247d7a300a6dc2e3d6624` |
| Provider / logical model | `local` / `local-chat` |
| Browser output | `WARM_CONTEXT_K7M4` |
| Terminal state | one `task.completed`; status `success`; finish reason `stop` |
| Fallback | `false` |

Persisted timing gives queued-to-first-token `13.329 s` and queued-to-complete
`14.964 s`. Playwright observed the fully verifiable assistant text after
`14.867 s`. These are observations, not performance targets. Reliable
generation throughput was not exposed and is recorded as unavailable.

## Independent durable and terminal readback

Read-only API and PostgreSQL inspection agreed:

- thread `2` belongs to user `local` and project `1`;
- ordered message rows are user `4`, assistant `5`, user `6`, assistant `7`;
- both assistant rows contain the exact browser-visible text;
- each assistant row records its task, request, and attempt correlation;
- both record attempted and final provider `local`, attempted and final model
  `local-chat`, `completed=true`, and `fallback_attempted=false`;
- each task has exactly one `task.running`, one `message.created`, and one
  `task.completed` outbox row;
- there is no duplicate assistant row, duplicate terminal event, failed event,
  or contradictory terminal state for either request.

The completed event records `explicit_provider_terminal_observed=true`,
`visible_output_emitted=true`, and `transport_ended_cleanly=true`. Catalog and
endpoint resolution prove that the local provider's selected runtime was the
live Whoosh'd endpoint. Per-request persisted physical-model provenance is not
separately exposed; the live inventory is the physical mapping authority.

## Cloud non-use

Cloud non-use is supported by mutually agreeing evidence:

- all supported runtime cloud-provider flags were false and egress allowlists
  were empty;
- OpenAI, Groq, DeepSeek, Alibaba, and MiniMax credential fields were blank in
  all three required containers;
- `/health` reported `cloud_capable_configuration_present=false`;
- both assistant rows and terminal events record provider `local`, model
  `local-chat`, and `fallback_attempted=false`;
- browser requests were local-origin only;
- bounded backend/worker log search after submission found no cloud host or
  provider invocation.

## Regression and validation results

| Command / surface | Exit / result | Notes |
|---|---:|---|
| `git status --porcelain=v2 --branch` | 0 | exact branch/dirty state captured before and after; pre-existing staged deletion preserved |
| pre-repair supported Compose render without `LOCAL_CHAT_MODEL` | 0 | proved ambient Qwen leak and worker profile contradiction; hash `6bf83255...` |
| `.venv/bin/python -m pytest -v tests/architecture/test_supported_compose_local_model_projection.py` | 0 | 4 passed; rerun after final edit also 4 passed |
| `.venv/bin/python -m pytest -v tests/core/test_config_coherence.py` without scoped profile flags | 1 | 15 passed, 1 failed because ambient `.env` selects the unrelated friends/family/DeepSeek profile; preserved as environment evidence |
| same config-coherence test with the supported command-scoped flags and no `LOCAL_CHAT_MODEL` | 0 | 16 passed |
| strict local resolution spot checks in `tests/core/test_ai_router.py` | 0 | 2 passed; exact local selection and blank-target fail-closed behavior remain intact |
| post-repair supported Compose render without `LOCAL_CHAT_MODEL` | 0 | three required services coherent; hash `dad71e60...` |
| first sandboxed `docker compose ... up -d --build ...` | harness failure | Buildx metadata access was denied by the sandbox before runtime mutation |
| approved Compose recreation, volumes preserved | 0 | required images/services recreated; later cloud-key overlay recreation tool output was truncated, but new container creation times, final runtime env, healthy state, and live requests independently prove completion |
| initial combined HTTP probe using wrong port assumptions | harness failure | `8000` was Whoosh'd, not Guardian; `8100` was closed; corrected probes used Guardian `8888` and Whoosh'd `8000` |
| corrected `/health`, `/health/chat`, `/api/health/llm`, catalog, and Whoosh'd probes | 0 | all required surfaces healthy and mutually consistent |
| selected container environment inspection | 0 | three required services match the post-repair render; credential values reduced to blank/present state only |
| first Playwright Chrome launch in sandbox | harness failure | macOS Crashpad bootstrap was denied before browser use |
| approved headed Playwright launch and browser workflow | 0 | real UI cold and warm turns, reload, screenshots, console, and request inventory completed |
| read-only message API and PostgreSQL correlation queries | 0 | durable rows, ownership, ordering, provenance, and exact terminal counts confirmed |
| backend/worker cloud-provider log search | 0 | no matching cloud invocation found |
| `.venv/bin/python scripts/validate_docs.py` | 0 | docs validation passed |
| `git diff --check` | 0 | passed before proof creation and rerun at closeout |

Read-only orientation, governing-document, source, log, schema, and diff
inspections also exited 0 unless the harness-only cases above say otherwise.
The non-executable `scripts/dev/dev-key.sh` helper was invoked safely through
`bash`; no key was printed or stored.

## Focused regression contract

`tests/architecture/test_supported_compose_local_model_projection.py` locks the
architecture contract rather than YAML formatting or a physical model:

- supported backend and chat worker own `local-chat`;
- backend, chat worker, and document-embed worker share the local-only supported
  posture and blank cloud credentials;
- the obsolete Qwen id and any physical model authority are absent from the
  supported projection/profile;
- base Compose retains explicit `${LOCAL_CHAT_MODEL}` transport for accepted
  custom/operator exact-target semantics.

## Deferred evidence and boundaries

- The preceding F4 initial terminal-event/browser timing seam was not repaired.
  During this successful proof, a visible `Queued` label remained at the upper
  left after terminal success and reload even though the transcript, `Ready` /
  `Completed` projection during the turn, API, outbox, and PostgreSQL agreed.
  The composer remained usable and the warm continuation succeeded. This is
  preserved as deferred F4/UI projection evidence, not expanded here.
- F5 retrieval provenance, F6 lock-acquisition observability, and F7 large
  frontend Vitest behavior were not reopened.
- Workspace retrieval, restart qualification, account activation, Private
  Preview, ADR-087 graceful shutdown, and Tester bind-readiness were not run.
- The old general Whoosh'd smoke contract test was not part of this task's
  authorized validation surface; the new architecture regression is the
  governing test for the repaired supported projection. No unauthorized test
  file was edited.
- No release/current-state claim is changed by this bounded pass.

## Files changed

- `docker-compose.whooshd-smoke.yml`
- `tests/architecture/test_supported_compose_local_model_projection.py`
- `docs/architecture/proofs/supported-compose/2026-09-21-local-model-projection-repair.md`

`docker-compose.yml` and
`config/supported_profiles/v1-local-core-web-mcp.yaml` were inspected and did
not require changes. The unrelated staged Dev Log deletion remains outside the
task commit.

## ADR and invariant check

- ADR impact: aligned with existing ADR-069/ADR-074; no ADR change.
- PostgreSQL remains durable truth; Redis did not become domain truth.
- `local`, `whooshd`, `local-chat`, and the physical model remain distinct.
- Supported local-only/cloud-disabled/fail-closed invariants remain enforced.
- Exact custom/operator model semantics were not removed or weakened.
- No cloud fallback, unauthorized scope expansion, volume destruction, or
  release-claim widening occurred.

## Documentation follow-through and next action

F1/F2 now have bounded successful current-tip evidence. This justifies a later
human-approved rerun of the complete current-tip supported-Compose evaluation;
it does not yet justify a current-state or release-readiness update.

**Next atomic action:** rerun the full current-tip supported-Compose end-to-end
evaluation from the repaired revision, including the still-open terminal-event,
retrieval-provenance, lock-observability, restart, and governing-static-proof
surfaces.
