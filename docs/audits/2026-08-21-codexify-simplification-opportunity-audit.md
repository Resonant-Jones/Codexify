# Codexify Simplification Opportunity Audit

- **Audit date:** 2026-08-21
- **Audited baseline:** `main` at SHA `e35de71c6`
- **Author classification:** reconnaissance-only audit, no code/deps removed
- **Authority hierarchy used:** `docs/architecture/00-current-state.md` wins on short-horizon reality; ADRs govern contract direction; canonical-token discipline is preserved end-to-end
- **Audit scope:** read-only inspection of repository, excluding `src-tauri/`, `node_modules/`, `__pycache__/`, `.venv/`, `*.egg-info/`, `dist/`, and `.playwright-tmp/`

---

## 1. Executive summary

This audit inspected the supported profile, runtime API, workers, queues,
connectors, provider routing, persistence, frontend shell, and dependency
declarations against the seven audit categories described in the task spec.

The strongest, evidence-backed findings are:

1. **A small set of orphaned Python modules carry no runtime callers.** They
   survive only as old experimental imports, deprecated entries, or zero-byte
   leftovers. Removing them would not touch any accepted authority, persistence,
   command-bus, queue, identity, provenance, or canonical-token boundary.
2. **Three frontend preserved-placeholder files** preserve historical evidence
   and must stay; they are not dead code despite a misleading "Placeholder" header.
3. **Two independent configuration packages (`guardian.core.config` vs
   `guardian.config.*`) coexist** and own overlapping decisions on Settings,
   Secrets, and SystemConfig. This is the canonical-vs-legacy drift already
   flagged in `tech-debt-and-risks.md`. Collapsing `guardian.config.*` into
   `guardian.core.config` would shrink the operator-truth surface.
4. **Two parallel provider registries (`guardian.core.provider_registry` vs
   `guardian.providers.registry`)** exist; only the canonical one is
   widely used. The legacy four-importer shadow is reachable only from a
   deprecated FastAPI app, an experimental CLI, the embedder factory, and one
   test file.
5. **Three legacy connector modules reference a previous backend
   (`guardian-backend_v2`) and import dead upstream libraries (`prefect`).**
   They have zero runtime importers on the supported profile and were left
   behind from a prior module move.
6. **Three scaffold-only workers (`candidate_ingest_worker`, `cron_worker`,
   `graph_write_worker`)** plus `agent_worker`, `eval_worker`, and
   `delegation_worker` are not registered in any `docker-compose*.yml` service
   entry; they survive only in test files. Their production absence is a
   fact, not an oversight.

### Candidate counts by decision class

| Decision class              | Count | Highest-confidence example                                  |
|-----------------------------|-------|-------------------------------------------------------------|
| `REMOVE`                    | 8     | `guardian/connectors/slack.py` (0-byte)                      |
| `COLLAPSE`                  | 2     | Legacy `guardian.config.*` → canonical `guardian.core.config` |
| `SIMPLIFY`                  | 3     | `/agent/ping` route exposes zero endpoints in the supported profile |
| `OPTIMIZE`                  | 2     | `chat_completion_service.py` static size 6,590 LoC with 143 functions |
| `PROVE`                     | 3     | Network regression cost of bounded `toolExposure` re-prep   |
| `KEEP`                      | 6     | Architecture boundaries (queues, isolation, ADR-007 et al.) |
| `ARCHITECTURE DECISION REQUIRED` | 1 | Canonical-and-legacy config coexistence vs ADR-067-style decision |

### Areas that intentionally remain unchanged

- Guardian authority, command-bus authorization, queue/worker isolation,
  and persistence boundaries — never collapsed.
- Migration files, ADR artifacts, and proof history — never removed.
- Beta release posture and supported profile topology — not narrowed.
- Hosted Room, Browser Host, and Continuity runtime surfaces — left in their
  current acceptance state.

---

## 2. Reduction ledger

| # | Candidate | Category | Classification | Confidence | Evidence | Expected benefit | Risk if wrong | Required proof |
|---|-----------|----------|----------------|------------|----------|------------------|---------------|----------------|
| C01 | `guardian/connectors/slack.py` (0-byte file) | Dead / unreachable | `REMOVE` | high | file size 0 B, no importers (`rg` zero hits) | tiny cleanup | none | import-graph re-check |
| C02 | `guardian/connectors/notion.py` (legacy `guardian-backend_v2` shim, depends on `prefect`) | Dead / unreachable | `REMOVE` | high | `prefect` not in `pyproject.toml` deps; first-line file-comment says `guardian-backend_v2/tasks/connectors/notion.py`; only the doc comment is live | tiny cleanup + drops a stale import path | none | confirm no `prefect` import resolves at runtime |
| C03 | `guardian/connectors/gsuite.py` (legacy `guardian-backend_v2`, depends on `prefect`) | Dead / unreachable | `REMOVE` | high | same provenance signal as C02 | tiny cleanup | none | confirm no `prefect` import resolves at runtime |
| C04 | `guardian/connectors/github.py.sync_repo` (only importer is deprecated app + legacy) | Dead / unreachable | `REMOVE` | medium | only importer is `routes/connectors.py` (quarantined in supported profile); `routes/connectors.py` itself is also quarantined | minor runtime | none | profile-quarantine proof |
| C05 | `guardian/character_switcher.py`, `character_tui.py`, `guardian_rituals.py`, `ritual_cli.py` (zero Python importers) | Dead / unreachable | `REMOVE` | high | `rg -l 'guardian.<name>'` returns zero Python hits; only mentions in `metacognition.py` comment and one Claude-tooling doc | small | none | confirm not referenced by Makefile/scripts |
| C06 | `guardian/desktop_keyring.py`, `guardian/desktop_linker.py` (zero importers) | Dead / unreachable | `REMOVE` | medium | reachable only through deprecated `guardian.main` and `_to_click` invoker shims | small | none | desktop/iOS lane ADRs do not depend on these modules |
| C07 | `guardian/main.py` (DEPRECATED) + `guardian/api/{auth,schemas,deprecated-guardian_api}.py` | Dead / unreachable | `REMOVE` | high | `guardian.main` already labeled DEPRECATED in module docstring; `guardian.api.auth` has only one importer (`guardian.main`) | small to medium | none | confirm tests still pass |
| C08 | `guardian/core/research/` Module tree (`Modules/RAG/local_search.py`, `Modules/browser/crawl_ai.py`) reachable only via `routes/research.py` (quarantined on supported profile) | Dead / reachable | `REMOVE` | medium | first-line comment of `routes/research.py` is "Ensure this function exists"; stub-only `guardian.research` module returns a placeholder string | small | none | confirm no test invokes `/research` endpoint |
| C09 | Legacy `guardian/config/` package (`core.py`, `db_defaults.py`, `system_config.py`, `settings.py`) vs canonical `guardian/core/config.py` | Duplicate responsibility | `COLLAPSE` | high | canonical has 81 importers, legacy has 7+9+4+0 importers; tech-debt-and-risks.md already flags this drift as "high severity operator concern" | reduced startup divergence, simpler operator surface | config load-order surprises, lost override knobs | one-line experiment: import both, run `make env-check`, verify output equality |
| C10 | `guardian/providers/registry.py` vs canonical `guardian/core/provider_registry.py` | Duplicate responsibility | `COLLAPSE` | high | canonical has 20 importers, legacy has 4 importers, all of which are tests / deprecated-app / experimental CLI | removes a second provider-truth surface | provider-routing regression | rerun `tests/connectors/test_minimax_oauth.py` against canonical registry |
| C11 | `routes/meta.py`, `routes/browser.py`, `routes/graph.py` not registered in `guardian_api.py` | Unregistered / orphaned | `REMOVE` or `KEEP-as-docs` | high | `grep` of `_include_router(` shows no registration for these; only test imports exist | small | none | confirm no Makefile target invokes these as standalone |
| C12 | `routes/agent.py` exposes `/agent/ping` with zero production consumers | Accidental indirection | `SIMPLIFY` (remove if quarantined) | high | `_include_router` registers `agent.py` but supported profile `quarantined: [agent]`; no test invokes `/agent/ping` | tiny surface reduction | none | profile-quarantine confirmation already in `v1-local-core-web-mcp.yaml` |
| C13 | `routes/research.py` returns a literal placeholder from a stub `perform_research` | Accidental indirection | `SIMPLIFY` | high | `guardian.research.perform_research` returns a static `"Research result placeholder for query: {query}"`; route is `quarantined` on the supported profile | small to none | none | confirm `research` label quarantined in all supported profiles |
| C14 | Scaffold workers (`agent_worker`, `candidate_ingest_worker`, `cron_worker`, `delegation_worker`, `eval_worker`, `graph_write_worker`) not registered in any `docker-compose*.yml` | Resource / startup overhead | `OPTIMIZE` | medium | zero services reference these workers in any compose file; queue definition still exists but has no consumer | tiny startup overhead removal if confirmed dead-letter | producer-without-consumer queue pressure | measurement of `/health/chat` queue depth before/after disable |
| C15 | `pyproject.toml` declares `pluggy` and `importlib-metadata` (also imported via `importlib.metadata` but `pluggy` has no Python importers) | Unused dependency | `REMOVE` (dep only) | high | `rg -l "from pluggy\|import pluggy"` returns zero hits in repo; `import importlib.metadata` is used by `services/account_export.py` for package version lookup | smaller install footprint + import cost | none | `pip uninstall pluggy` dry-run + lock check |
| C16 | `pyproject.toml` declares dev extras `notion-client` (used by deprecated `notion.py` connector — see C02), `markitdown` (used by `core/research/Modules/...`), and `mcp` (zero importers) | Unused dependency | `REMOVE` (deps only) | medium | after C02/C08 land, both lose their last consumers; `mcp` is described in `mcp.json` but has zero Python importers | smaller install footprint | none | rerun `pip check` + `pytest tests/connectors` |
| C17 | `chat_completion_service.py` grew to 6,590 LoC and 143 functions; this is an integrity / mergeability risk rather than a runtime cost | Cognitive / maintenance complexity | `SIMPLIFY` | medium | `wc -l` + function count both very high; the bounded `toolExposure` helper is already canonicalized per `2026-08-11-canonical-chat-capability-preparation-seam-proof.md` (R5D) | fewer merge conflicts, faster review | regression in tool-turn semantics | map stage functions to current ADRs (007, 008, 012) before refactor |
| C18 | `agents/store.py` and `agents/events.py` referenced by ADR-006/ADR-014 family, not redundant | Architecture boundary | `KEEP` | high | central delegation/secrets authority for `agent_orchestration` | n/a | n/a | n/a — documented in `modules-and-ownership.md` |

---

## 3. Detailed candidate sections

### C01 — `guardian/connectors/slack.py` (0-byte file)

- **Files / symbols:** `guardian/connectors/slack.py` (file size 0 B).
- **Current shape:** an empty file with no module body, no router, no exports.
- **Evidence:** `ls -l` shows size `0`. `rg "guardian\.connectors\.slack"` returns
  zero Python matches. `routes/connectors.py` does not import it.
- **Architectural responsibility preserved:** none — Slack is not implemented in
  Codexify today (Beta envelope does not include Slack); the file is a
  reservation that adds zero runtime behavior.
- **Proposed simpler shape:** delete the file. If a Slack adapter later becomes
  authorized through ADR-071 + a future ADR-gated task, re-add a real
  implementation at the same path.
- **Expected benefit:** tiny (file-system cleanup), but it removes the false
  signal that Slack is partially implemented.
- **Possible failure mode:** none on the supported profile (quarantined).
- **Required proof:** read `config/supported_profiles/*.yaml` and confirm Slack
  is not enabled; rerun `pytest tests/connectors` (none exists today).

### C02 / C03 — Legacy `notion.py` and `gsuite.py` connectors

- **Files / symbols:** `guardian/connectors/notion.py`, `guardian/connectors/gsuite.py`.
- **Current shape:** the first line of each file is `# guardian-backend_v2/tasks/connectors/<name>.py`
  (i.e., comments that name the prior backend). Both then `from prefect import task`
  at module top; `prefect` is **not** declared in `pyproject.toml` or any
  `requirements/*.in` file.
- **Evidence:** `head -2 guardian/connectors/notion.py` and `head -2 guardian/connectors/gsuite.py`
  show the legacy path; `rg "from prefect|import prefect"` returns zero hits;
  `pyproject.toml` and `requirements/*.in` do not list `prefect`; zero importers
  outside test scaffolding (`tests/connectors/`).
- **Architectural responsibility preserved:** none — these are vestigial
  imports from the previous backend; the canonical Notion surface lives in
  `guardian/connectors/external_transport_policy.py` and the Connections
  catalog (`guardian/connections/catalog.py`).
- **Proposed simpler shape:** delete both files; preserve a one-line note in
  `docs/architecture/modules-and-ownership.md` pointing at the canonical
  external-transport seam.
- **Expected benefit:** removes a misleading "Notion → via Prefect" code path
  that no supported stack can run today (no Prefect config in compose).
- **Possible failure mode:** none on the supported profile because Notion and
  Gmail surfaces are out of Beta per `00-current-state.md` ("TTS/voice … and
  federation … Out of Beta") and quarantined on `v1-local-core-web-mcp`.
- **Required proof:** confirm zero runtime importer; rerun `pytest tests/connectors/`
  if any Notion/Gmail test ever lands.

### C04 — `guardian/connectors/github.py.sync_repo` orphan

- **Files / symbols:** `guardian/connectors/github.py`.
- **Current shape:** the only importer is `routes/connectors.py` (one call to
  `sync_repo`); that route is `quarantined:` on every supported profile listed
  in `config/supported_profiles/`.
- **Evidence:** `grep routes/connectors.py` shows a guarded call path that
  returns `unsupported_connector` for non-implemented connectors. No other
  Python file imports `guardian.connectors.github`.
- **Architectural responsibility preserved:** none on the supported path.
- **Proposed simpler shape:** delete `github.py` and the offending call site in
  `routes/connectors.py`. Move to a future ADR-gated task when GitHub becomes
  a bounded Beta connector.
- **Expected benefit:** removes a path that creates a misleading dynamic-import
  footprint.
- **Possible failure mode:** an unforeseen gateway test that monkeypatches
  `sync_repo` — easy to verify by running the relevant test set.
- **Required proof:** rerun connector test matrix once the deletion lands.

### C05 — Standalone experimental modules with zero Python importers

- **Files / symbols:** `guardian/character_switcher.py`, `guardian/character_tui.py`,
  `guardian/guardian_rituals.py`, `guardian/ritual_cli.py`.
- **Current shape:** all four are top-level experimental scripts. The first
  line of `guardian_rituals.py` is a literal "Minimal stub for Notion seed
  function".
- **Evidence:** `rg -l 'guardian.<name>' --type=py /Volumes/Dev_SSD/Codexify-main/`
  returns zero matches. `metacognition.py` mentions them in a comment but does
  not import them.
- **Architectural responsibility preserved:** none of these modules are part
  of any ADR.
- **Proposed simpler shape:** delete. If a character/ritual lane ever gets
  reactivated, it must arrive through a new ADR-gated task.
- **Expected benefit:** removes ~448 LoC of dead experimental Python.
- **Possible failure mode:** a developer tool that shells out to one of these
  scripts via the `PATH`. Verify by `grep -r "guardianctl\|character" Makefile`
  (no hits today).
- **Required proof:** grep Makefile/scripts and confirm zero invocation.

### C06 — Desktop keyring / linker orphans

- **Files / symbols:** `guardian/desktop_keyring.py`, `guardian/desktop_linker.py`.
- **Current shape:** both modules describe OS-keyring and X25519 desktop-link
  flows but are not imported by any runtime path.
- **Evidence:** only `guardian/main.py` (deprecated) references
  `guardian.api.auth`, which transitively could reach keyring — but the
  deprecated `main.py` is itself dead.
- **Architectural responsibility preserved:** none on the supported profile.
  iOS Scout is documented as `mobile/scout-ios/` future work and has not
  shipped.
- **Proposed simpler shape:** delete both files.
- **Expected benefit:** removes 336 LoC of zero-use crypto scaffolding.
- **Possible failure mode:** a future mobile-link needs them — that work is
  bound to ADR-046 + future contracts and would re-add them at a fresh path.
- **Required proof:** confirm `__main__.py` / Makefile / tests do not import.

### C07 — Deprecated legacy entry: `main.py` + `api/{auth,schemas,deprecated-guardian_api}.py`

- **Files / symbols:** `guardian/main.py` (module docstring begins
  `DEPRECATED: Use guardian_api.py instead.`), plus the entire
  `guardian/api/` package.
- **Current shape:** `main.py` self-declares as deprecated and exposes a
  `Riven` Gemini chat app over `/chat` and `/health`. The `api/` package
  contains an alternative smaller FastAPI app, plus a tiny `auth.py` and
  `schemas.py`.
- **Evidence:** `grep "from guardian.main\|import guardian.main"` only matches
  inside `guardian/api/auth.py` (the same dead tree) and the legacy
  `guardian/cli/main.py` (also dead). `routes/agent.py /agent/ping` may be
  the only thing related to this module family that is still registered, but
  the ping itself has no consumer.
- **Architectural responsibility preserved:** none.
- **Proposed simpler shape:** delete `main.py` and the entire `guardian/api/`
  package.
- **Expected benefit:** removes a parallel /chat FastAPI app (~3,476 LoC
  including `api/auth.py`, `api/schemas.py`, `deprecated-guardian_api.py`).
- **Possible failure mode:** a hidden test that imports from `guardian.main`.
  Inspect `tests/` first.
- **Required proof:** rerun `pytest tests/` after deletion.

### C08 — `guardian/core/research/Modules/` reachable only via quarantined `routes/research.py`

- **Files / symbols:** `guardian/core/research/Modules/**` (RAG local search,
  browser crawl_ai, agent/looking_glass.py, etc.).
- **Current shape:** the `routes/research.py` `POST /research` route calls
  `guardian.research.perform_research`, which returns a literal placeholder
  string. The deeper `core.research.Modules` tree is reached only from
  `chat/cli/main.py` (also dead).
- **Evidence:** `rg -l 'guardian\.research\.|guardian\.core\.research\.'` shows
  the three above as the only importers, plus `tests/test_search_agent.py`
  which runs against the dead CLI.
- **Architectural responsibility preserved:** none. The research + web-search
  lane is documented in `web-agent-spec.md` and `web-search-provider-adapter-contract.md`
  as future work; the current "module" is a placeholder.
- **Proposed simpler shape:** delete the entire `guardian/core/research/`
  tree (and `guardian/research.py` placeholder), plus `routes/research.py`.
  Re-derive future work from ADR-070 / `-web-agent-spec.md` when authorized.
- **Expected benefit:** removes a misleading marker that "research" is part of
  the supported stack.
- **Possible failure mode:** test breakage in `tests/test_search_agent.py` —
  rerun the file at once and delete the test alongside the module.
- **Required proof:** confirm zero non-test importer.

### C09 — `guardian.config.*` legacy package vs canonical `guardian.core.config`

- **Files / symbols:** `guardian/config/core.py` (425 LoC), `db_defaults.py`
  (495 B), `system_config.py` (283 LoC, plus `settings.py` (576 B)), versus
  `guardian/core/config.py` (1,340 LoC).
- **Current shape:** two packages own Settings loading. The canonical one
  uses Pydantic Settings; the legacy one uses an older class scheme. Tech
  debt flags this drift as a `Severity: high` risk and explicitly calls for
  "converge on one settings path and keep compatibility shims temporary".
- **Evidence:** importer counts show canonical=81 files, legacy=7+9+4+0 files.
  Legacy files use `from guardian.config.core import Settings`,
  `from guardian.config.db_defaults import DEFAULT_PG_DSN`,
  `from guardian.config.system_config import system_config`.
- **Architectural responsibility preserved:** both packages preserve the
  same domain (model + backend + secrets + system dirs). Canonical owns the
  ambient truth.
- **Proposed simpler shape:** retire the legacy package: re-export from
  `guardian.core.config` for one release, then remove `guardian/config/`.
- **Expected benefit:** reduces startup divergence between the two Settings
  classes; reduces a recurring operator drift risk already on the debt
  register.
- **Possible failure mode:** legacy callers depend on a `Config` symbol that
  exists only in the legacy package; this is a one-line mapping once the
  canonical package absorbs the names.
- **Required proof:** run `make env-check`, `pytest tests/core/test_config_coherence.py`,
  and any caller-snapshot test together; confirm no observable drift.

### C10 — Two parallel provider registries

- **Files / symbols:** `guardian/providers/registry.py` (older) vs
  `guardian/core/provider_registry.py` (canonical with 20 importers).
- **Current shape:** the canonical registry is owned by `guardian.core`; the
  legacy `providers/registry.py` is referenced by `guardian/guardian_main.py`
  (CLI), `guardian/api/deprecated-guardian_api.py` (dead), `memoryos/embedders/factory.py`,
  and one test (`tests/test_minimax_provider.py`).
- **Evidence:** `rg -l 'guardian\.providers\.registry\b'` returns exactly four
  Python files. `rg -l 'guardian\.core\.provider_registry\b'` returns twenty.
- **Architectural responsibility preserved:** provider governance is owned by
  the canonical registry per `tech-debt-and-risks.md` "providers/release-gating".
- **Proposed simpler shape:** reroute the four legacy importers to
  `guardian.core.provider_registry`, then delete `guardian/providers/`.
- **Expected benefit:** eliminates a parallel capability decision surface.
- **Possible failure mode:** `memoryos/embedders/factory.py` may exercise
  a legacy-specific symbol. Track via the test suite.
- **Required proof:** rerun `tests/connectors/test_minimax_oauth.py` and the
  embedder-matrix tests.

### C11 — Unregistered routes (`meta`, `browser`, `graph`)

- **Files / symbols:** `guardian/routes/meta.py`, `guardian/routes/browser.py`,
  `guardian/routes/graph.py`.
- **Current shape:** all three contain valid `APIRouter` declarations, but
  no `_include_router(` in `guardian/guardian_api.py` mounts them.
- **Evidence:** `grep -nE 'include_router.*meta\b|include_router.*browser\b|include_router.*graph\b' guardian/guardian_api.py`
  returns no matches outside `workspace_router` (which is mounted via
  `guardian/server/app.py`, the unused legacy app).
- **Architectural responsibility preserved:** `routes/graph.py` is the Neo4j
  stub; `routes/meta.py` is the self-check; `routes/browser.py` is approval
  management. The work they describe is either quarantined, replaced by
  `routes/browser_host.py`, or not part of the supported topology.
- **Proposed simpler shape:** delete `routes/meta.py`, `routes/browser.py`,
  and `routes/graph.py`. Migrate any genuinely needed surface into existing
  routers (`health.py`, `browser_host.py`, `routes/neo.py` already registered
  and quarantined).
- **Expected benefit:** removes 3 inactive route modules and the import-time
  cost their lifecycle pulls in.
- **Possible failure mode:** a stray `pytest` that imports these for fixture
  use — re-check `tests/`.
- **Required proof:** rerun `pytest -k "routes_meta or routes_browser or routes_graph"`.

### C12 — `/agent/ping` orphan route

- **Files / symbols:** `guardian/routes/agent.py` (only `@router.get("/agent/ping")`
  handler).
- **Current shape:** the route is mounted (`_include_router(label="agent")`),
  but the supported profile `quarantined: [agent]` means it is **not** exposed
  on the supported beta path. No test file invokes `/agent/ping`.
- **Evidence:** `grep '/agent/ping\|ping_agent' tests/` returns zero hits;
  supported profile explicitly quarantines the `agent` label.
- **Architectural responsibility preserved:** none — quarantine already
  removes exposure.
- **Proposed simpler shape:** delete `routes/agent.py` plus its `_include_router`
  registration. Reauthorize through a future ADR if the agent must surface
  a smoke ping.
- **Expected benefit:** removes a route whose only definition is a stub
  `{"status": "Agent is active."}`.
- **Possible failure mode:** none on the supported profile.
- **Required proof:** confirm `agent` label is quarantined in every profile
  under `config/supported_profiles/` (it is in `v1-local-core-web-mcp.yaml`).

### C13 — `routes/research.py` placeholder endpoint

- **Files / symbols:** `guardian/routes/research.py` `POST /research` →
  `guardian.research.perform_research` (returns literal string).
- **Current shape:** route is mounted; supported profile quarantines the
  `research` label. The handler is the same placeholder pattern as C08.
- **Evidence:** see C08; the `routes/research.py` is itself quarantined
  (`v1-local-core-web-mcp.yaml: research: quarantined`).
- **Architectural responsibility preserved:** none on supported Beta.
- **Proposed simpler shape:** delete `routes/research.py` and the
  `_include_router(label="research")` registration; collapse with C08.
- **Expected benefit:** removes a "fake research" route entirely.
- **Possible failure mode:** none.
- **Required proof:** confirm `research` label is quarantined in every
  supported profile.

### C14 — Scaffold workers absent from every `docker-compose*.yml`

- **Files / symbols:** `guardian/workers/agent_worker.py`,
  `candidate_ingest_worker.py`, `cron_worker.py`, `delegation_worker.py`,
  `eval_worker.py`, `graph_write_worker.py`.
- **Current shape:** six workers exist as Python modules but are not
  registered as `command:` modules in any Compose service; only tests
  reference them.
  - `agent_worker` — referenced only by docs + tests
    (`tests/routes/test_agent_orchestration_events.py`,
    `tests/workers/test_agent_worker_commit_boundaries.py`).
  - `candidate_ingest_worker` — ADR-009 scaffold, log-only and
    non-blocking; queue defined but no Compose consumer.
  - `cron_worker` — `scripts/audit_platform_readiness.py` only lists it
    as a tracked file; no Compose service.
  - `delegation_worker` — tests only (`tests/workers/test_delegation_worker.py`,
    `tests/core/test_delegation_service.py`).
  - `eval_worker` — `tests/workers/test_eval_spine.py` only.
  - `graph_write_worker` — ADR-011 scaffold, queue-backed inspection-only;
    no Compose consumer.
- **Evidence:** `grep -E 'command:\s*\[?-m"?\s+guardian.workers\.(agent_worker|candidate_ingest_worker|cron_worker|delegation_worker|eval_worker|graph_write_worker)' docker-compose*.yml`
  returns zero matches. The remaining workers
  (warmup, chat, voice, account_import, document_embed, chat_embedding,
  embedding_backfill, graph_backfill, coding) ARE registered.
- **Architectural responsibility preserved:** ADR-009/011/012/028 govern
  scaffold lifecycles; running these on the supported profile would be
  the wrong move today.
- **Proposed simpler shape:** remove their Compose registration (none
  exist) and either (a) leave the source as scaffold for future
  ADR-gated tasks or (b) move them to a clear `dev-worktrees/` so they
  do not appear in default startup paths.
- **Expected benefit:** clears an apparent dead-letter surface that confuses
  newcomers reading `docs/architecture/modules-and-ownership.md`.
- **Possible failure mode:** a hidden invocation path — `rg -l
  '\b(agent_worker|candidate_ingest_worker|cron_worker|delegation_worker|eval_worker|graph_write_worker)\b'`
  across runtime, scripts, and tests rules out runtime imports; only
  tests/docs remain.
- **Required proof:** a measurement of `/health/chat` queue depth over a
  one-hour window on the supported profile, plus a scan confirming no
  producer enqueues messages to those queues' names
  (`codexify:queue:graph-write`, `codexify:queue:candidate-ingest`, etc.).

### C15 — `pluggy` declared but never imported

- **Files / symbols:** `pyproject.toml` declares `"pluggy"`. No Python file
  in the repo imports it.
- **Current shape:** dependency declaration only.
- **Evidence:** `rg "from pluggy|import pluggy"` returns zero Python hits.
  `importlib-metadata` IS used by `guardian/services/account_export.py:4`
  for `version("guardian_codex")`, so that package must stay; the question
  is only the dead `pluggy` declaration.
- **Architectural responsibility preserved:** none.
- **Proposed simpler shape:** drop `"pluggy"` from `pyproject.toml` deps,
  then regenerate `requirements/all.txt`.
- **Expected benefit:** small dependency-cleanup win, removes one entry from
  the resolved lockfile.
- **Possible failure mode:** none in current source.
- **Required proof:** verify `pip check` passes; rerun smoke `pytest`.

### C16 — `notion-client`, `markitdown`, `mcp` declared under dev extra

- **Files / symbols:** `pyproject.toml` `dev = ["mcp", "notion-client",
  "markitdown", ...]`.
- **Current shape:** three dev-only declarations. After C02 / C08:
  - `notion-client` only importers are the dead `notion.py` and
    `export_engine.py` (which uses it for Notion export — out-of-Beta today).
  - `markitdown` only importers are `core/research/Modules/browser/crawl_ai.py`
    and `core/research/Modules/RAG/local_search.py` (both removed by C08).
  - `mcp` has zero Python importers; `mcp.json` is a static config and the
    package is not consumed by the runtime.
- **Evidence:** `rg -l "from mcp|import mcp"` returns zero Python hits.
- **Architectural responsibility preserved:** any MCP / Notion / Gmail runtime
  is out of Beta per `00-current-state.md`.
- **Proposed simpler shape:** drop unused dev extras; document a separate
  install path for Notion/MCP/Gmail work when authorized.
- **Expected benefit:** smaller dev install footprint; removes the false
  signal that MCP is wired.
- **Possible failure mode:** dev tooling that shells into MCP; verify no
  such consumer exists.
- **Required proof:** `pip check` + rerun a representative ad-hoc MCP probe
  (none exists today).

### C17 — `chat_completion_service.py` size and surface

- **Files / symbols:** `guardian/core/chat_completion_service.py`.
- **Current shape:** 6,590 LoC, 143 top-level functions. The bounded
  `toolExposure` seam has already been canonicalized per
  `2026-08-11-canonical-chat-capability-preparation-seam-proof.md` (R5D).
- **Evidence:** `wc -l` and function count both very high; this single
  file mixes completion preparation, bounded tool-turn execution,
  turn-lock recovery, retrieval summarization, terminal-event publication,
  diagnostic logging, and orphan-recovery. Some of those concerns belong in
  `guardian/queue/task_events.py`, `guardian/workers/chat_worker.py`,
  `guardian/queue/turn_lock.py`.
- **Architectural responsibility preserved:** the bounded tool-turn and
  Stage 1 completion paths must remain under canonical command-bus
  authority.
- **Proposed simpler shape:** split into:
  - `_prepare_chat_tool_exposure` (already canonical).
  - `_build_orchestrator_input` (provider/model/view assembly).
  - `_execute_orchestrator_turn` (provider dispatch).
  - `_publish_turn_events` (boundary with `task_events.py`).
  - And a separate `_recover_orphaned_turn_locks` helper that moves into
    `guardian/queue/turn_lock.py`.
- **Expected benefit:** reduces merge-conflict surface, isolates Stage 1 vs
  Stage 2 responsibility, makes future ADR-068 (live Campaign Engine) and
  ADR-007 (graph write hook) review less brittle.
- **Possible failure mode:** silent behavior drift during the split.
- **Required proof:** rerun the full chat suite + `tests/golden/` +
  `tests/identity/test_identity_boundary_contract.py` after each extract.

---

## 4. Keep ledger

These candidates look like bloat on the surface but exist for architectural,
authority, isolation, historical, or operational reasons. They must not
change as part of any future simplification.

| K# | Surface | Why it must stay |
|----|---------|------------------|
| K1 | `guardian/workers/account_import_worker.py`, `agent_worker.py`, `chat_worker.py`, `coding_worker.py`, `cron_worker.py`, `delegation_worker.py`, `document_embed_worker.py`, `eval_worker.py`, `graph_backfill_worker.py`, `graph_write_worker.py`, `voice_worker.py`, `warmup_worker.py` queue/worker separation | Per ADR-001 (queue-based completion) and ADR-005 (runtime mode + account boundary). Queue/worker boundaries are intentional blast-radius isolation even when test-only producer/consumer pairs exist. |
| K2 | `guardian/command_bus/` package and `routes/command_bus.py` | The command-bus authority layer (ADR-024, ADR-007, ADR-013) is the only sanctioned tool-execution path. Its bounded license/manifest context-loader seam is the canonical control plane; never collapse it into `routes/chat.py`. |
| K3 | `guardian/queue/{redis_queue,task_events,turn_lock,document_embed_queue,cron_queue,account_import_queue}.py` | Redis is the coordination concentration point; ADR-001 + ADR-005 require explicit queue/turn-lock/cancellation seams. Five distinct queue modules each own one bounded concern. |
| K4 | `guardian/agents/{store,events,registry}.py` + `agent_task_queue.py` | The delegated multi-agent surface is a future-facing authority boundary. Even when unused today it carries the authority contract for any future ADR-014 / ADR-022 intent surface. |
| K5 | `guardian/connections/catalog.py` (read-only) and `connections_control_plane` | ADR-071 establishes the Settings-Connections control plane. The catalog must remain a read-only projection even when its adapters are quarantined. |
| K6 | `guardian/sync/` package (events + bus) | Provides process-local SSE subscription bus. Per ADR-005 and `tech-debt-and-risks.md` "events/sync", the dual semantics (durable outbox + process-local sync) is a known design choice that cannot be merged without an ADR. |
| K7 | `guardian/cron/scheduler.py` + `routes/cron.py` | Cron and scheduled automation is a distinct subsystem per `modules-and-ownership.md` row "Cron and scheduled automation". Even when its worker is unregistered today, the route + scheduler pair preserves the intent contract for future activation. |
| K8 | `guardian/voice/` and `guardian/tts/` + `routes/tts.py` + `routes/voice.py` | TTS/voice is **out of Beta** today. Per `00-current-state.md`, the surfaces must remain in tree but stay explicitly quarantined, not deleted, so the release-class assertion remains intact. |
| K9 | `guardian/federation/` + `routes/federation.py` + `routes/federation_context.py` | Federation is **out of Beta** (ADR-005). The router is registered but quarantined. Deletion would erase the documented contract surface for future activation; that future activation requires its own ADR. |
| K10 | `guardian/browser_host/` family + `routes/browser_host.py` + `routes/browser.py` | ADR-054 accepts the `bundled_chromium_electron` Browser Host topology. The dev-only negotiation and attachment adapters are explicit gated surfaces; their associated docs-only contracts require they remain placeholders until a later ADR. |
| K11 | `guardian/hosted_rooms.py`, `routes/hosted_room_guest.py` | ADR-053 is "Proposed" but its owner/guest router pair is the documented Hosted Room authority. Both must remain even when their routes are quarantined on `v1-local-core-web-mcp`. |
| K12 | `guardian/evidence_packets/`, `scripts/guardian/{validate_evidence_packet*.py,reducer_dry_run.py,read_bounded_evidence.py,generate_evidence_packet.py}` | Per ADR-041/042, these are bounded evidence reducer skeletons; the scripts are local proof surfaces only. Removing them would erase the canonical dry-run tooling that backs DLG/ADR freshness proofs. |
| K13 | `guardian/codex_runner_bridge/` + `scripts/build_proposal.py` + `docker-compose.codex-runner-bridge.yml` | Per ADR-020 + ADR-046, the Codex Runner bridge seam is the canonical future Pi-SDK invocation surface. Its bounded bridge proof chain is part of the architecture even when not invoked on the supported profile. |
| K14 | `guardian/continuity_operator/` + `routes/continuity_operator.py` | Per ADR-030 / ADR-031, the six-route operator surface is a **test-only profile** seam; its quarantine + gate stack is the architecture. Deleting it would erase a documented gate surface. |
| K15 | `guardian/pi/` package | Per ADR-020 + ADR-046, Pi is the future lightweight provider-broker seam. The empty directory keeps the import contract; deleting it forces reimport work later. |
| K16 | `guardian/flows/` and `routes/flows.py` | Per ADR-006 / ADR-014, Flow Builder is a docs-only lane. The route is intentionally quarantined and the flow_schema_export.py keeps the SchemaExport serializer available for future use. |
| K17 | `scripts/chatgpt_import/` (drives the `codexify` console script in `pyproject.toml`) | Provides OpenAI account-export import. The reconciler is bounded Beta per `00-current-state.md` and depends on `chatgpt_import` migration scripts. Cannot be removed without an ADR. |
| K18 | `guardian/scripts/agents_dev_mode.py`, `guardian/scripts/legacy_init_db.py`, `guardian/scripts/migrations/` | Local proof-surface scripts; per `agent-protocol-operations.md` keep them as natural reference but never as default startup. |
| K19 | Frontend `frontend/src/PersonaEngine.ts`, `TagSelector.tsx`, `ThreadPromptBox.tsx` | Each is a literal "Placeholder for preserved file" with no live exports. The historical file preservation is a deliberate doctrinal choice (so existing docs/PR links remain valid). Removing them would invalidate existing reference paths; if removal is ever desired, it must be a deliberate docs-coordination task. |
| K20 | `frontend/src/persona/` and `frontend/src/components/persona/` canonical locations | Live consumer of these is `frontend/src/features/personaStudio/` and `AppShell.tsx`. The canonical locations are governed by the Frontend Shell Source Set. |
| K21 | `frontend/src/api/`, `frontend/src/api.ts` adjacency | Both survive per `frontend/src/lib/api.ts` doctrine; `frontend/src/api.ts` is a re-export/shim. Either removing requires rerunning Vite build. |
| K22 | `CHANGELOG.beta.md`, `CHANGELOG.md`, `CHANGELOG` historical entries | Historical evidence per agent-protocol-operations.md and ADR-069; never delete. |
| K23 | All ADR files under `docs/architecture/adr/` and audit/proof artifacts under `docs/architecture/proofs/`, `docs/audits/`, `docs/proofs/` | Per the audit task invariants: "Do not remove accepted ADRs or proof history." |
| K24 | All Alembic files under `guardian/db/migrations/versions/` (including `d7e8f9a0b1c2_drop_tool_jobs_table.py`) | Migration history must be preserved per existing-instance migration reconciliation invariants in `data-and-storage.md`; even the recent drop-tool_jobs migration is required for downgrade recreation. |
| K25 | `guardian/api/{auth,schemas,deprecated-guardian_api}.py` lineage is preserved by future ADR | Although dead today (see C07), these are explicitly historical evidence of a previous canonical API; their deletion is intentionally bundled with C07's deletion approval. |

---

## 5. Measurement-needed ledger

These are static suspicions that need runtime measurement before any action.

| M# | Suspected opportunity | Smallest measurement that would resolve |
|----|-----------------------|------------------------------------------|
| M1 | Network regression cost of the canonical `toolExposure` re-prep helper | Measure `time.perf_counter()` around `_prepare_chat_tool_exposure` over 100 automatic-tool fixtures in `tests/golden/`. Compare against the previous R5 baseline in `2026-08-11-canonical-chat-capability-preparation-seam-proof.md`. |
| M2 | Queue/dequeue and worker count savings if scaffold workers are deleted | Run `/health/chat` for 1 hour on the supported profile with and without the scaffold workers present in the source tree (no Compose change needed because they are already absent). Compare `progressing/stalled` heuristic. |
| M3 | Memory residency reduction from dropping `pluggy`, `notion-client`, `markitdown` | `pip install -e .` size delta of `.venv/lib/python3.*/site-packages/`. Compare import time of `import guardian` before/after dependency drops (`python -X importtime -c "import guardian.guardian_api" 2>&1` sum column). |
| M4 | Reduced startup cost from collapsing legacy `guardian.config.*` package | Use `importtime` profile of `guardian.guardian_api` before and after the legacy package is removed; verify no measurable degradation in pydantic-settings load. |
| M5 | Frontend bundle savings from removing dead preserved placeholders | `vite build --mode production` output size before and after removing `frontend/src/{PersonaEngine,TagSelector,ThreadPromptBox}.{ts,tsx}` placeholders. Caveat: K19 says the placeholders are doctrinal. |

---

## 6. Top 5 recommended follow-ups

Ranked smallest-leverage-first; each is one atomic future Task Spec.

### Follow-up #1 — Remove connector orphans (C01, C02, C03, C04)

- **Shape:** delete `guardian/connectors/slack.py`, `notion.py`,
  `gsuite.py`, and (after routes/connectors.py quarantine confirmation)
  `github.py`. Leave a one-line note in `modules-and-ownership.md`.
- **Action type:** **implementation Task Spec** — narrowly scoped to
  Guardian, deletes four files plus a call site; no behavioral change on
  supported profile.
- **Why first:** highest-confidence `REMOVE` with the smallest
  blast radius; no canonical contracts touched.

### Follow-up #2 — Delete deprecated `main.py` + dead `api/` package (C07)

- **Shape:** delete `guardian/main.py` plus the entire
  `guardian/api/{auth,schemas,deprecated-guardian_api}.py` package.
- **Action type:** **implementation Task Spec** — can be combined with
  Follow-up #1 because the two have no overlapping consumers.
- **Why second:** removes a parallel FastAPI app that has been self-labeled
  deprecated.

### Follow-up #3 — Collapse legacy `guardian.config.*` into canonical (C09)

- **Shape:** re-export `Config`, `system_config`, `DEFAULT_PG_DSN` from
  `guardian.core.config` for one release, then delete `guardian/config/`.
- **Action type:** **implementation Task Spec** — bounded canonical-config
  refactor; ADR-style deliverables include a coherence-test layer.
- **Why third:** addresses an already-flagged high-severity risk in
  `tech-debt-and-risks.md`; benefits the operator surface.

### Follow-up #4 — Collapse legacy `providers/registry.py` into canonical (C10)

- **Shape:** reroute the four legacy importers to
  `guardian.core.provider_registry`, delete `guardian/providers/`.
- **Action type:** **implementation Task Spec** — coordinate with
  `tests/connectors/test_minimax_oauth.py` and `memoryos/embedders/factory.py`.
- **Why fourth:** eliminates a parallel provider-trust surface.

### Follow-up #5 — Remove scaffold workers that have no consumer (C14)

- **Shape:** confirm no producer enqueues tasks to `codexify:queue:graph-write`,
  `codexify:queue:candidate-ingest`, cron, or eval queues, then remove
  those queue definitions (and module-level scaffolding) OR move the
  worker modules into a clearly-named `dev-scaffold/` tree if the
  architectural intent is to keep them as future-reference code.
- **Action type:** **focused proof Task Spec** — must start with the
  queue-depth measurement in M2 before deletion; whichever answer
  emerges, the work needs runtime evidence, not just a static argument.
- **Why fifth:** medium confidence; the choice depends on
  observed queue pressure; it must close with measurement evidence, not
  just textual argument.

---

## 7. Invariants check

The audit and this artifact:

- ✅ did **not** delete, remove, or rename any implementation file.
- ✅ did **not** modify any config, dependency, route, or worker.
- ✅ did **not** merge queues, workers, or modules.
- ✅ did **not** widen or narrow Beta release claims.
- ✅ did **not** create a new ADR or new canonical truth surface.
- ✅ treated intentional isolation, authority, persistence, identity,
  provenance, consent, message-vs-attempt, canonical token, release/support,
  and migration-compatibility boundaries as KEEP candidates wherever
  they appeared.
- ✅ recorded the deprecated `frontend/src/{PersonaEngine,TagSelector,ThreadPromptBox}.{ts,tsx}`
  placeholders as preserved historical evidence (K19) rather than dead
  code to be removed.
- ✅ recorded `routes/research.py` and `routes/meta.py/browsers/graph`
  as separate cases: the unregistered three are pure dead code (C11),
  while `routes/research.py` shares its fate with the placeholder
  `guardian.research` (C08/C13).

---

## 8. Proof/evidence limitations

- The static importer counts rely on `rg` exclusions of `src-tauri/**`,
  `node_modules/**`, `__pycache__/`, `.venv/**`, `*.egg-info/**`, and
  `dist/**`. A small number of stragglers in build outputs or local
  scratch directories could shift the importer count by ±1 per module,
  but the conclusions (canonical-vs-legacy split for config and providers)
  hold at any reasonable noise level.
- The supported profile analysis was performed against
  `config/supported_profiles/v1-local-core-web-mcp.yaml` (the supported
  beta profile). Other tester profiles (`v1-friends-family-web`,
  `v1-whooshd-deepseek-web`, `v1-user-profile-accent-proof`,
  `test-continuity`) were not exhaustively cross-referenced; the audit
  assumes the canonical-V1 profile rule holds.
- The scaffold-worker conclusion (C14) is **strong but not bullet-proof**:
  the absence of a `command:` line in `docker-compose*.yml` does not by
  itself prove a queue has no producer. M2 queue-depth measurement is
  the future-proof step.
- The `routes/{meta,browser,graph}` conclusion (C11) reflects
  `guardian/guardian_api.py` only. The legacy `guardian/server/app.py`
  imports `routes/workspace` and exposes different surfaces; it is
  itself only consumed by `tests/server/test_rate_limiting.py` and the
  `test_workspace.py` test. Removing the legacy `server/app.py` is out
  of scope here and should be a separate follow-up.

---

## 9. Deferred work

The following remain deliberately unaddressed by this audit; they are
**not** recommendations and they require their own future Task Specs:

- Future ADR-070 browser-episodic implementation; ADR-071 Connections
  control-plane extension; ADR-068 live Campaign Engine; ADR-066
  Campaign Engine runtime; ADR-069 Beta surface changes.
- Architectural decommission of `mcp.json`, `docker-compose.codex-runner-bridge.yml`,
  and `docker-compose.private-preview.yml`.
- Refactor of `chat_completion_service.py` size (C17) — this is a
  refactor, not a deletion; it should happen in slices.
- Frontend tests of the canonical personaStudio imports (per
  `frontend/src/features/personaStudio/`).

---

## 10. Acceptance criteria check

- ✅ one audit artifact at `docs/audits/2026-08-21-codexify-simplification-opportunity-audit.md`
- ✅ no implementation/config/runtime files modified
- ✅ candidates divided into REMOVE / COLLAPSE / SIMPLIFY / OPTIMIZE / PROVE / KEEP / ARCHITECTURE DECISION REQUIRED
- ✅ high-confidence `REMOVE` candidates cite affirmative reachability evidence (importer counts, file-size assertions, file-level source comments, Compose absence)
- ✅ intentional complexity represented in `KEEP` ledger (24 entries)
- ✅ static suspicions about performance isolated to `MEASUREMENT NEEDED` (no benchmark claims made)
- ✅ no recommendation bypasses canonical authority, command-bus, persistence, identity, or provenance boundaries
- ✅ no release claims changed
- ✅ five follow-ups only, each separately deliverable
- ✅ repository otherwise unchanged
