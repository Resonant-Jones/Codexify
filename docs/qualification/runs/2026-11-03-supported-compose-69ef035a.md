# Supported-Compose runtime — qualification at `69ef035a` — 2026-11-03

- Rubric: ../rubrics/supported-compose.md
- Rubric version: 2
- Verdict: PASS
- Date/time window: 2026-11-03
- Tester alias: automated-architecture-proof
- Tester role: architecture-impact qualification agent
- Prior familiarity: full
- Assistance level peak: 0
- Branch: `docs/qual-compose-02-qualification` (cut from the frozen revision `69ef035a4`)
- Commit: 69ef035a4320724b9a53279d2fabd6bac0c6e98f
- Runtime profile: v1-local-core-web-mcp
- Deployment/environment: local Docker Compose, macOS 27.2 arm64
- Device class: workstation
- Browser/client: Google Chrome 156.0.8078.80, real browser over the Chrome DevTools Protocol against the rendered WebUI
- Provider: local
- Model: local-chat

## Qualification metadata

```yaml qualification-metadata
qualification_id: supported-compose
rubric_version: 2
verdict: PASS
commit: 69ef035a4320724b9a53279d2fabd6bac0c6e98f
date: 2026-11-03
tester_alias: automated-architecture-proof
tester_kind: automated
assistance_level_peak: 0
evidence:
  - docs/architecture/proofs/supported-compose/2026-11-03-supported-compose-qualification-69ef035a.md
```

This run was executed against rubric version 1. Rubric version 2 (2026-11-04)
narrows the scope statement to name the source-matched launcher startup and
adds the launcher to the rubric's `surface_paths`. It changes no required
check, no blocking criterion, and no observation. The run was adjudicated
against rubric version 2 on 2026-11-04 and satisfies it exactly: the startup
command it exercised was
`scripts/whooshd_docker_smoke_up.sh full --detach --project
codexify_qual_20261103`, and the backend image reference it resolved was
`codexify-backend-runtime:src-69ef035a4320`.

## Scope

One exact supported-Compose qualification against the `v1-local-core-web-mcp`
local-only profile at the frozen revision
`69ef035a4320724b9a53279d2fabd6bac0c6e98f`. The run built the source-matched
backend image from an isolated clean worktree, launched the full supported
topology through the repaired canonical startup path
(`scripts/whooshd_docker_smoke_up.sh full --detach`), created only disposable
evaluation data, drove the real web UI in Google Chrome, inspected
PostgreSQL and the provider's own request ledger, ran the declared focused
verification surfaces, restarted only the qualification-owned application
services, and cleaned up only qualification-owned resources.

This run never stopped, restarted, pruned, or modified the Private Preview
lane. Its long-running services held a continuous 3-hour container uptime
across the whole run, and its `alembic_version` (`3a91d7c4e8b2`), backend
image (`sha256:22d9f5f1…e6e5c55`), and table count (138) were unchanged. The
before/after Preview snapshots — all 18 container IDs, images, states, 8
volumes, 1 network, image digest, Alembic head, and table count — compare
with no differences.

Cleanup was project-scoped and ownership-verified: the 16 containers, 8
volumes, and 1 network carrying `com.docker.compose.project=codexify_qual_20261103`
were removed with `docker compose … down --remove-orphans -v` (exit 0), and
zero residue remains under either the project label or the project name. The
source-matched image `codexify-backend-runtime:src-69ef035a4320` was
deliberately retained as the Gate A evidence artifact.

The frozen runtime revision did not move during the run. The working tree was
clean at every check.

**Scope of this verdict.** The PASS applies to the launcher-driven,
source-matched startup this run exercised
(`scripts/whooshd_docker_smoke_up.sh full --detach`, image
`codexify-backend-runtime:src-69ef035a4320` built from the evaluated
checkout). It does **not** qualify the stock `:latest` Compose startup at the
same revision: `backend/migrations` is a symlink to `../guardian/db/migrations`
and `docker-compose.yml`'s migrator bind-mounts only `./backend:/app/backend`,
so the symlink resolves into the baked image rather than into the checkout.
PR #982 hardened the qualification launcher; it did not change the stock
Compose configuration, and the stock-path migrator defect remains open in the
tree at this revision. The full mechanism is in the detailed proof, §5.1.

## Qualification matrix

| Criterion | Result | Observation | Evidence |
| --- | --- | --- | --- |
| Supported topology and startup | PASS | `docker compose config --quiet` exited 0 for `docker-compose.yml` + `docker-compose.whooshd-smoke.yml`. All 16 blessed Whoosh'd contract assertions passed against the resolved configuration. Every required service for the profile — `frontend`, `backend`, `db`, `redis`, `worker-chat`, `worker-document-embed`, `migrator` — was present; the required ones were healthy. The launcher's Step 7 additionally asserted that the migrator, backend, and worker-chat all run the source-matched image `codexify-backend-runtime:src-69ef035a4320`. | Detailed proof, "Supported topology and startup" |
| Health and inventory | PASS | `/health` → 200 with `v1-local-core-web-mcp` valid and no mismatches; `/health/chat` → 200, `ok: true`, worker heartbeat fresh, queue progressing; `/api/health/llm` → 200, provider `local`, model `local-chat`, runtime authorized and available. Model inventory was observed at the runtime: the host Whoosh'd advertised exactly one model, `local-chat`. | Detailed proof, "Health and inventory" |
| Ordinary chat and durable readback | PASS | Thread 1 created through the ordinary route; a user message was accepted (`acceptance_status: accepted`); the completion reached `state: terminal`, `event_type: task.completed`, `reason: durable_completion_recorded`, `completed_message_id: 2`. Both the user and assistant messages are persisted and readable. The durable attempt row binds `request_id`, `backend_task_id`, `turn_id`, and `completed_message_id`, and the provider's own ledger carries the matching entry (`upstream_request_id req_59e0a7779a214ada8cbe240eb151f3d6`, model `local-chat`, status completed). | Detailed proof, "Ordinary chat and durable state" |
| Document ingestion and retrieval | PASS | A synthetic document uploaded, reached `embedding_status: ready` in 35 s with no error, and the retrieval probe returned the document's unique passphrase verbatim in the assistant reply. Provenance identifies the retrieved document and chunk (`document_id 6e7675ed-98d2-4c9a-b269-c1ec6eb40998`, `chunk_index 0`, lanes `thread_docs` and `project_docs`). A second thread saw zero documents, so scope isolation held. **Limitation:** the `rag-trace` HTTP operator surface returns empty `documents`/`graph` and `retrieval_provenance: null` while the durable trace record holds the attribution. | Detailed proof, "Document retrieval and provenance" |
| Explicit model authority | PASS | An authenticated completion explicitly requesting the unavailable local model `qual-nonexistent-model-69ef035a` failed durably: `state: terminal`, `event_type: task.failed`, `reason: durable_terminal_outcome_recorded`, `completed_message_id: null`. The exact requested model identity was preserved (`requested_model` = `model` = `qual-nonexistent-model-69ef035a`, `configured_source: requested_model`, `selection_source: explicit`), no substitute model executed, `fallback_reason: null`, and no assistant message was persisted — thread 2 holds one row, role `user`. Provider-side non-execution was established from the provider's own ledger: **0** entries for the rejected `request_id` and **0** entries anywhere with that model. The only provider contact was the model inventory read. | Detailed proof, "Explicit model authority" |
| Browser projection | PASS | Real Google Chrome 156 rendered the thread, the event stream delivered through the frontend's own proxy (`live-events-hub` connected; event cursor 16 → 20), the successful completion rendered as "browser-gate-f" attributed to Guardian, the failed attempt rendered as "1 earlier response task failed.", the terminal state reconciled with no lingering in-progress state, and a full page reload preserved the projected state. | Detailed proof, "Browser projection" |
| Restart recovery | PASS | Only `backend`, `worker-chat`, and `worker-document-embed` were restarted; every other container kept its uptime and the Private Preview was untouched. Services returned healthy, thread 4 and its messages survived, the four durable attempt rows were byte-identical before and after, no attempt shared a `turn_id` or a `completed_message_id`, ordinary chat worked again on the restarted path, and the document's embedding and retrieval posture remained accessible. | Detailed proof, "Restart recovery" |
| Baseline verification surfaces | PASS | Nine focused groups executed with **zero skips** after two environment-gated proofs were re-run: queue/worker lifecycle, cancellation and deadline behaviour, turn locks, account authorization, provider/model authority, migration contract, retrieval provenance, durable state integrity, and supported configuration. | Detailed proof, "Baseline verification surfaces" |

## Metrics

```yaml
task_completed: yes
assistance_level: 0
wrong_turns: 0
self_recovered: 2
time_to_first_success_seconds: 246.4
repeat_task_confidence_1_to_5: 4
```

`time_to_first_success_seconds` is measured from stack creation
(2026-11-04T00:08:46Z) to the acceptance of the first successful completion
(2026-11-04T00:12:52.404Z). `self_recovered: 2` counts the two
qualification-environment corrections recorded in the detailed proof — a
symlinked `./models` bind source, and a mismatch between the operator's
`.env` lane and the supported profile's provider contract — both corrected
before the evaluated run.

## Observed behavior

The repaired tip passed the supported topology, the migration boundary, the
health surfaces, ordinary chat with durable readback, document ingestion and
retrieval with document/chunk provenance, explicit model authority, real
browser projection with event delivery, restart recovery, and the nine
focused verification surfaces.

Two boundaries that earlier runs left open are green **on the exercised
path**. The migration boundary that QUAL-COMPOSE-01 failed is green on the
launcher path, verified by direct database readback rather than an exit code.
The fail-closed model-authority boundary that the September run failed is
green too: an explicitly requested unavailable local model was rejected
**before provider execution** — the request's `request_id` has no entry in the
provider's own ledger, no substitute model ran, and no assistant message was
persisted.

Neither of those two statements extends to the stock `:latest` Compose path,
which this run did not exercise. See the scope note above.

## Proven

- The supported Compose topology starts and reaches healthy state on the
  evaluated tip through the repaired canonical startup path, with the exact
  local-only provider contract and no cloud credential in any qualification
  container.
- The baked image, the source tree, and the live database all agree on the
  single Alembic head `d91e4fa6702b`, read directly from PostgreSQL with
  exactly one `alembic_version` row.
- Ordinary chat completes, persists, binds to a durable attempt row, and
  converges in a real browser.
- An explicitly requested unavailable model fails durably before provider
  execution, preserves the exact requested identity, persists no assistant
  message, and leaves no provider ledger entry.
- Document ingestion, embedding, and retrieval with document/chunk provenance
  work on the evaluated tip, with scope isolation holding.
- Durable state survives a restart of the qualification-owned application
  services, with no duplicate completion and no shared attempt identity.
- The nine focused verification surfaces execute with zero skips.

## Failed

None. No rubric blocking criterion occurred.

## Unproven

- Any boundary outside the supported local-only profile. The Private Preview
  lane, cloud providers, federation, connectors, hosted sandbox, Atlas, Pi,
  and the autonomous coding worker remain unqualified by this run and keep
  their own authority.
- The `rag-trace` and `evals` operator surfaces as *operator-facing* views.
  The per-message provenance they draw from is present and correct, but the
  `rag-trace` HTTP response does not expose the attribution that the durable
  trace record holds.
- Any Trio-gated selector. Trio is not installed in this environment, so
  Trio-only selectors elsewhere are INPROVEN, not PASS. No selector in the
  nine groups executed here is Trio-gated.
- `worker-coding` on the source-matched image. It started from the pre-baked
  `codexify-worker-coding-runtime:latest` and is outside this rubric.
- The **stock `:latest` Compose startup** at this revision. This run qualified
  the launcher-driven, source-matched path only. The stock path's migrator
  cannot reach the source tree's migrations, so it is unqualified here and
  remains the open blocker recorded in `docs/architecture/00-current-state.md`.

## Human friction

Not applicable. This was an automated architecture-impact qualification run
with no human tester in the loop.

## Positive signals

- The migration boundary that QUAL-COMPOSE-01 failed is green on the
  launcher path, verified by a direct database readback rather than an exit
  code. The stock path's copy of that boundary is still open.
- The fail-closed model-authority boundary that the September run failed is
  green, corroborated from the provider's own ledger.
- Restart recovery, which the September run left UNPROVEN, is now exercised
  with before/after durable identities and a post-restart completion.
- All nine focused verification surfaces executed with zero skips.

## Highest-priority follow-up

Give the `rag-trace` operator surface its document attribution back. The
durable trace record identifies the retrieved document and chunk; the HTTP
surface returns `documents: []` and `retrieval_provenance: null`. An operator
inspecting `rag-trace` today cannot see what the system actually retrieved.

Secondary: the `events_outbox` retention lifecycle. All ten rows remained
`pending` while the live SSE stream served the same events — but that is the
implemented behaviour, not a delivery failure. The SSE path keeps outbox rows
intact so concurrent clients can resume independently, and the read path
filters only on event id, never on `status`. The narrower questions are
whether the schema-only `status` column should be given meaning or dropped,
and whether retention should be bounded — the `stream_events` docstring still
claims a deletion that the code no longer performs. Deleting rows to make the
table "drain" would break the resume behaviour the implementation preserves.

## Evidence

- Commit: `69ef035a4320724b9a53279d2fabd6bac0c6e98f`
- Detailed proof: `docs/architecture/proofs/supported-compose/2026-11-03-supported-compose-qualification-69ef035a.md`
- Image: `codexify-backend-runtime:src-69ef035a4320`, digest `sha256:0ecc261727e61eeaad44c48d0c434479a92a8fdb378af82c6f4cb22c9dde1f65`
- Related automated tests: the nine focused verification surfaces recorded in
  the detailed proof, plus `tests/qualification/` (38 passed) and the DLG
  validator (`result: pass`, 0 errors, 6 pre-existing warnings) — exact
  commands and results in the detailed proof, §20
- Other: provider request ledger (`GET http://127.0.0.1:8000/runtime/requests`)
  and direct PostgreSQL readbacks were collected during the run

## Freshness

```text
current
```

At the time of the run this receipt described its evaluated commit. The
registry recomputes freshness against the current tip; see
`docs/architecture/00-current-state.md` for release authority.
