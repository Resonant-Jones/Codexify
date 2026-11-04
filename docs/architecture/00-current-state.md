## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-11-04

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The release gate remains `HOLD` and did not move in the last audit window. The repository migration graph is a single Alembic head, `d91e4fa6702b` — verified at this tip by resolving all 133 revision files — and the single-head invariant carries regression coverage. The stock Compose startup still fails Gate B: `docker-compose.yml`'s migrator bind-mounts only `./backend:/app/backend` while `backend/migrations` is a symlink to `../guardian/db/migrations`, so the symlink resolves into the baked image and a stock-launched stack serves the application against a schema behind it. `docker-compose.runtime.yml`'s migrator declares no volumes at all. The live Preview database remains at `3a91d7c4e8b2`, four schema-carrying revisions behind the head (`b7e2c4a1d903`, `d86f2a4b1c90`, `e42c7d0b9135`, `d91e4fa6702b`), plus two graph-only mergepoints (`a3115f64dda8`, `c8e42a91d307`). The supported runtime has been qualified on one frozen revision, not at this tip and not on the stock Compose startup. That qualification covers the **source-matched launcher startup** only — `scripts/whooshd_docker_smoke_up.sh full --detach` builds the backend image from the evaluated checkout, so the migrator reaches the source head. The stock Compose startup of the same profile remains unqualified, and the two startups are not interchangeable.

## What changed recently

- **PR #982 hardened the qualification launcher, not the stock Compose startup.** The launcher is itself a supported startup path; the stock Compose startup was untouched. `scripts/whooshd_docker_smoke_up.sh` gained an isolated source-matched startup, a `verify_migration_outcome` step that confirms a migration only when the migrator container is unambiguously identified, has exited zero, and the project's own database reports exactly one `alembic_version` row equal to the expected head, plus refusal of any `codexify_private_preview*` Compose project. `tests/test_whooshd_smoke_env_contract.py` grew by roughly 800 lines.
- **PR #984 landed governed account-scoped history recall and chat message origin custody.** New: `guardian/core/account_history_recall.py`, a read-only `GET /api/chat/projects/{project_id}/history/search` route, a model-facing `op::history.search` tool advertised only with a request-scoped grant, and a shared write-side custody rule in `guardian/core/db.py` protecting the reserved `extra_meta.message_origin` member.
- **PR #986 landed durable coding-worker claim persistence** in `guardian/agents/store.py`: acceptance, heartbeat, and terminal transitions are owner-bound conditional updates.
- **PR #987 rebound the `adr-index` knowledge-graph node** to `74fd8f489` and recomputed its content hash. Its freshness state is still `stale`; the corpus was not reverified.
- **PR #989 recorded a qualification capacity preflight**: 30 GiB free, BuildKit cache 0 B across 0 records, 0 B reclaimed, Private Preview unchanged at 18 containers with backend image `sha256:22d9f5f1…e6e5c55`. It does not start QUAL-COMPOSE-02 and qualifies nothing.
- **A supported-Compose qualification now covers the source-matched launcher startup**, at frozen revision `69ef035a4320724b9a53279d2fabd6bac0c6e98f`, executed 2026-11-03 with no cloud credential in any of the 16 qualification containers. All seven rubric checks pass; Gate B is green on that startup by direct `alembic_version` readback (`d91e4fa6702b`, one row, 139 public tables, migrator exit 0), and the run covers real browser, provider-ledger, persistence, retrieval, and restart evidence. The qualification surface's scope statement was narrowed to name the launcher startup, and the launcher joined the rubric's `surface_paths` because it is part of the qualified path. **The stock Compose startup is not covered and stays open.**
- Added the 2026-11-03 daily dev log.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`. **The startup path is part of that supported path, and the two available startups are not interchangeable.** The *stock* Compose startup (`docker compose up` against the pre-baked `codexify-backend-runtime:latest`) resolves the migrator's migrations into the baked image; it is **unqualified and defective**. The *source-matched launcher startup* (`scripts/whooshd_docker_smoke_up.sh full --detach`) builds the backend image from the evaluated checkout, and it is the startup the `supported-compose` qualification surface covers.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- A supported-Compose qualification exists **inside the tip's lineage**: frozen revision `41ff615293ec`, confirmed an ancestor of this tip, executed 2026-11-02 in an isolated Compose project with no cloud credential present in any qualification container. It is a dated receipt against one frozen revision, not a qualification of this tip and not a qualification of the stock path.
- That receipt's dispositions are exact: Gate A (supported configuration/provider contract) **PASS**, Gate B (startup and migrations) **FAIL** on the stock path, Gate C (explicit-model rejection) **PASS** with provider-side corroboration — a durable terminal failure of the attempt, no model substituted, and no provider-ledger entry for the rejected turn — Gate D (ordinary chat and durable state) **PASS**, Gate E (retrieval and provenance) **PASS** with a recorded durability caveat, Gate F (browser and event coherence) **PASS**, Gate G (restart recovery) **PASS**, Gate H **PASS** for every selector that could execute with **3 selectors INCOMPLETE** for a missing optional `trio` dependency — `trio` is still declared in no requirements file or `pyproject.toml`.
- A **second** supported-Compose qualification exists, at frozen revision `69ef035a4320724b9a53279d2fabd6bac0c6e98f`, executed 2026-11-03, on the **source-matched launcher startup**. All seven rubric checks pass: Gate A **PASS** with zero cloud credentials in any qualification container, Gate B **PASS** on that startup by direct database readback, Gate C **PASS** with provider-side non-execution evidence, Gate D **PASS**, Gate E **PASS** with a recorded operator-surface limitation, Gate F **PASS** in real Chrome, Gate G **PASS**, Gate H **PASS** with zero skips. It is a dated receipt against one frozen revision and one startup path — **not** a qualification of this tip and **not** a qualification of the stock Compose startup.
- The stock migrator defect is **still open in the tree at this tip**: `docker-compose.yml` mounts only `./backend:/app/backend` and its own comment records that migration files come from the baked image; `docker-compose.runtime.yml`'s migrator has no volumes. PR #982 changed the qualification launcher only, not the stock Compose startup.
- The repository migration graph is a single head, `d91e4fa6702b`. A head-clean graph is a repository invariant, not a deployment qualification. The live Preview database is at `3a91d7c4e8b2`, with the four schema-carrying revisions and two graph-only mergepoints above it unapplied there; the Preview lane has not been advanced.
- The qualification registry's `supported-compose` entry now projects the 2026-11-03 run at `69ef035a4320724b9a53279d2fabd6bac0c6e98f`, which is an ancestor of this tip, with `freshness: current`. **Its scope statement names the source-matched launcher startup**, so the projection states which startup the `PASS` covers instead of leaving a reader to infer it from the title. `onboarding-and-people` still has no run receipt at all and remains `HOLD` on absent evidence; a supported-Compose run does not qualify that surface.
- **Account-scoped history recall is implemented on `main` and mounted.** `GET /api/chat/projects/{project_id}/history/search` resolves the account from authenticated authority only. It is reachable on the supported profile because route posture is per-router and `api_chat` is in that profile's `enabled` posture. The model-facing `op::history.search` tool is advertised only when a request-scoped `HistoryRecallGrant` is present. Coverage is code and test level only.
- **Message-origin custody is write-side only.** The reserved `extra_meta.message_origin` member cannot be forged by a client: the trust decision is the `NativeOriginAssertion` type, only backend creation paths construct one, and restore refuses archives carrying an untrusted native-origin claim. **The reader-side per-message origin classifier is not implemented.** The recall reader scopes at *thread* level through `ChatThread.origin_system`, and its message query selects no per-message origin column, so canonical ChatGPT import metadata inside a native thread still reaches the model. The governing contract records this as finding #3, "partially addressed" and still open.
- **Coding-worker claim persistence is implemented.** In `guardian/agents/store.py`, acceptance requires a live PostgreSQL session and matching canonical lineage, and heartbeat and terminal transitions are conditional on recorded ownership. The receipt's disposition is "GO for independent reconciliation of this persistence slice; Release: HOLD" — disposable-PostgreSQL persistence proof, not successful coding-worker execution.
- Ordinary chat, durable persistence and readback, retrieval with source attribution, browser-driven event coherence, and restart recovery are all proven at the frozen revision. Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, deadlines, and authorization; bounded evidence is not complete runtime qualification. Retrieval carries a recorded durability caveat, and the operator retrieval surfaces are not trustworthy as evidence.
- Saved Widget **promotion and revision storage** exist on `main`: `POST /saved-widgets`, widget fetch, revision list, and revision fetch are registered behind `CODEXIFY_ENABLE_SAVED_WIDGET_ROUTES`, `saved_widgets` is in the `enabled` route posture of the supported profile, canonical revision persistence is in the database, and route and store tests cover it. This is a promotion and revision-storage slice only, not a qualified widget lifecycle.
- Recipient-local read state is **deployed and live-qualified** on the Private Preview: a two-account live test passed 20 of 20 checks at serving revision `5569f3f34`, and the advance to serving revision `c8e72ef86` changed only `.dockerignore`, `.gitignore`, and documentation — re-verified at this tip, no application source differs between the two. The 20 checks were not re-run against `c8e72ef86`.
- The unread badge is **browser-rendered and proven** on the Private Preview: in Chrome 156 against the running service at serving revision `c8e72ef86`, the Inbox rendered per-conversation badges reading `3` and `1`, the launcher total read `4` and agreed with the API, and opening a conversation advanced the reader's own cursor and cleared its badge while the neighbouring conversation stayed unread. The badge is proven in one browser only.
- `direct_messages` is mounted `internal_only` on the supported profile. Share links remain bearer credentials: `expires_in_days` is optional on creation and no revocation endpoint exists.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Connectors, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, and autonomous coding-worker work are not default Beta support without current-main qualification.

## Not yet true / do not assume

- Capabilities without current-main qualification are not default Beta support.
- **Do not read PR #982 as a stock-Compose-startup fix.** It changed the qualification launcher, which is a supported startup path in its own right. The stock migrator still mounts only `./backend` and still resolves migrations from the baked image; the stock Compose startup is not repaired by it.
- **Do not read PR #989 as a qualification.** It is a host-capacity measurement. It states that it does not start QUAL-COMPOSE-02, authorizes no qualification run, and qualifies no surface.
- **Do not read the `supported-compose` registry `PASS` as qualifying the stock Compose startup.** That surface's scope names the source-matched launcher startup. The stock startup of the same profile resolves migrations into the baked image and is the open blocker below; the two paths are not interchangeable.
- **Do not read the history-recall slice as per-message origin enforcement.** Write-side custody is implemented; reader-side per-message classification, exclusion, and coverage reporting are not. Thread-level scoping is not message-level proof.
- **Do not read the history-recall route's presence as qualification.** It is implemented, mounted, and test-covered; no runtime receipt exists for it, and the model-facing tool only appears with a request-scoped grant.
- **Do not read PR #986 as successful coding-worker execution.** The receipt is persistence proof scoped to a disposable PostgreSQL database, disposition GO for independent reconciliation with Release HOLD.
- **Do not read the 2026-11-02 comparison-stack qualification as a stock-Compose-startup qualification.** Its Gates C through H were executed against a source-mounted comparison stack, not the stock Compose startup, precisely so the application source and schema were both at the frozen revision. The stock Compose startup still fails Gate B.
- **Do not read either supported-Compose qualification as a qualification of this tip.** One froze `41ff615293ec` and the other `69ef035a4320724b9a53279d2fabd6bac0c6e98f`; this tip is a descendant of both. They are dated evidence about one frozen revision each, and a green receipt is not a rolling claim.
- Do not read the supported-Compose qualification as lifting the release gate. Its verdict is `PASS` for the named launcher scope only, the registry still reports `HOLD` for `onboarding-and-people`, and the release gate remains `HOLD`.
- Do not read a green CI run as runtime qualification. The registry, the corpus validator, and the contract suites are documentation-integrity gates; they prove a claim is checkable, not that the runtime behaves.
- Do not read a `PASS` gate as a clean gate. Gate E passes with a recorded durability caveat, Gate H carries 3 INCOMPLETE selectors, and the receipt deliberately records two harness artifacts so they are not mistaken for product behaviour.
- Do not infer that a document that survives a worker kill recovers. A killed `worker-document-embed` left a document permanently in `embedding_status = 'processing'` with no observed recovery or terminal-failure marking, and no sweeper for stuck `processing` documents exists in the tree. The retrieval layer correctly withheld it, which is correct behaviour over an unrecovered document, not a working path.
- Do not use the rag-trace or retrieval-posture surfaces to verify retrieval. They reported empty on both a failing and a successful retrieval, and PR #984 did not change those surfaces. Only per-message `retrieval_provenance` carries the truth.
- Do not read the single-head migration graph as a new qualification of the live Preview database; that database is still at `3a91d7c4e8b2`.
- Do not read a corrected `supported-compose` lineage as qualifying `onboarding-and-people`; that surface still has no run receipt, and the two verdicts are independent.
- Do not treat any supported-Compose receipt — the September run, the 2026-11-02 comparison stack, or the 2026-11-03 launcher run — as a qualification of the stock Compose startup. All three were executed off the stock Compose startup; that startup's Gate B is the open blocker below.
- Do not read Saved Widget promotion and revision storage as widget lifecycle support. Library Widgets collection listing and filtering, invocation, conversational revision and editing, deletion, export and restore, Web Audio, and canvas qualification are all still open, and none of the slice has browser proof.
- Do not read the delegated worker canary as successful provider execution; the `reasoning_effort` contract still fails before provider execution, worker egress was observed despite `allow_network=false`, and no production caller of `reasoning_effort` exists in `guardian/`.
- Do not read the serving-revision advance as a re-run of the live read-state qualification: source equivalence is an observation about code, not a fresh execution of the 20 checks, and a healthy Private Preview is not a supported-Compose qualification.
- Do not read the `adr-index` rebinding as a corpus re-review. Its freshness state remains `stale`, and the `current-state` node is still `stale`.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality.

## Active blockers

- **The stock supported Compose migrator cannot reach the source tree's migrations.** A stock-launched stack runs a schema behind its own application source. Cause remains isolated to the migrator's bind mount; no remediation has landed, and the receipt does not propose one. The 2026-11-03 qualification does not close it: that run covered the source-matched launcher startup, and the stock Compose startup's migrator is unchanged in the tree.
- `onboarding-and-people` has no qualification run receipt at all, so the registry reports `HOLD` for it on absent evidence rather than on a lineage or staleness cause. A supported-Compose run does not qualify this surface.
- The current-tip supported-Compose qualification is missing. The 2026-11-03 run froze `69ef035a4320724b9a53279d2fabd6bac0c6e98f`, and this tip is a descendant of it. A qualification is commit-bound, so no supported-Compose qualification describes the current tip.
- The stock Compose startup has no supported-Compose qualification of its own. Gate B must be re-run and pass on that startup after the migrator's migration source is settled. The `supported-compose` rubric now scopes to the source-matched launcher startup, and the stock Compose startup gets **its own qualification identity** — `supported-compose-stock` — so the two execution contracts carry independent verdicts instead of one ambiguous PASS/HOLD value. That rubric is not written yet; it belongs with the stock startup's own bounded remediation and proof sequence, not with the launcher qualification.
- The live Preview database has not been advanced past `3a91d7c4e8b2`; four schema-carrying revisions and two mergepoints on `main` are unapplied there.
- **Reader-side per-message origin classification is not implemented.** Imported, unknown, and conflicting messages are not excluded before excerpts reach the model, and no content-free per-message coverage receipts are produced. The governing contract carries this as an open finding.
- A killed `worker-document-embed` leaves the affected document permanently in `embedding_status = 'processing'` with no observed recovery path.
- The rag-trace and retrieval-posture operator surfaces report empty even when retrieval demonstrably succeeded.
- Three `[trio]`-parametrised retrieval selectors cannot execute because the optional `trio` dependency is absent; they are INCOMPLETE, not passes.
- Frontend frozen-lockfile installation on the supported install path remains unrehearsed.
- Cross-browser qualification is missing on both the generative-UI containment repair and the unread badge; Chrome 156 is the only reported browser result.
- The UMS/Chronicle lane retains an inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still needs execution against the corrected baseline.
- The delegated worker-to-adapter `reasoning_effort` contract still fails before provider execution, and worker egress was observed despite `allow_network=false`. Explicit-model rejection is proven only at the frozen revision — not on the stock path and not at this tip.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open.
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`.
- The Saved Widget lifecycle is incomplete beyond promotion and revision storage: no Library Widgets collection listing, invocation, conversational editing, deletion, or export and restore path, and no browser proof.

## This week’s priorities

1. Fix the supported-path migrator so the migrator can reach the source tree's migrations, then re-run **Gate B on the stock path** and publish a receipt whose `alembic_version` equals the source head. The launcher now judges that outcome from the database rather than the container's exit code, so this is the one defect that blocks the supported path from being self-consistent. The stock Compose startup's own qualification surface, `supported-compose-stock`, is defined and its Gate B re-run in that sequence rather than under the launcher rubric: `supported-compose` is scoped to the source-matched launcher startup, so the two execution contracts carry independent verdicts.
2. Give the `events_outbox` retention lifecycle a bounded decision. The schema-only `status` column carries no runtime semantics and nothing transitions it, the read path never filters on it, and no production caller deletes rows — while the SSE path deliberately retains them so concurrent clients can resume independently. Decide whether `status` is given meaning or dropped, and whether retention is bounded, without breaking that resume behaviour.
3. Run the first qualification for `onboarding-and-people`, which still has no run receipt; a supported-Compose run does not qualify that second surface.
4. Advance the live Preview database through the approved migration and deployment sequence with a verified recovery path, re-pin the serving revision, and re-run the 20 read-state checks against that revision.
5. Implement the reader-side per-message origin classification and exclusion for the recall reader, and emit content-free per-message coverage receipts, so the open finding can close on evidence rather than intent.
6. Characterise the document-embed failure path under a kill injected at a controlled point, so `processing` documents are either recovered or terminally failed.
7. Populate the rag-trace and retrieval-posture surfaces, or mark them as non-evidence, so operator-facing retrieval diagnostics can be qualified rather than only per-message provenance.
8. Complete the frontend frozen-lockfile installation step of the approved deployment sequence.
9. Resolve the delegated-adapter `reasoning_effort` contract, execute the blocked Chronicle HTTP cases, and close the remaining Preview and lifecycle gaps: share-link revocation, import-to-recall, export and restore, cross-browser verification, and the Saved Widget lifecycle beyond promotion.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists at evaluated mainline tips.
- [x] Release-readiness claims are machine-checkable: the qualification registry is generated and drift-gated, and the knowledge-graph corpus is bound to a revision.
- [x] A supported-Compose qualification exists inside the tip's lineage, on the source-matched launcher startup, covering explicit-model rejection with provider-side non-execution evidence, ordinary chat with durable state, retrieval with attribution, browser/event coherence, and restart recovery.
- [x] A migration is judged by the database's own `alembic_version`, not by a container's exit code.
- [ ] The **stock** supported Compose path applies the source head's migrations; a stock-path run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] Each tracked qualification surface carries its own dated run receipt inside the tip's lineage; a receipt for one surface does not qualify another, and a proof artifact the registry cannot read does not qualify it either.
- [ ] The live Preview database is advanced past `3a91d7c4e8b2` and the four unapplied schema revisions land.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] A document left in `embedding_status = 'processing'` by a worker kill is recovered or terminally failed.
- [ ] Per-message origin classification excludes imported, unknown, and conflicting messages before excerpts reach the model.
- [ ] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof.
- [ ] Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline.

## How to read the rest of the KB

- `docs/qualification/` is the generated index of qualification evidence, verdicts, and freshness. It normalizes evidence and does not replace architecture proofs or this file.
- `docs/architecture/proofs/runtime/` holds the dated runtime receipts, including the supported-Compose qualification at `41ff615293ec` and the 2026-11-03 capacity preflight and coding-claim receipts.
- `account-history-recall-contract.md` is the governing contract for account-scoped history recall and message-origin custody, and it states its own open findings.
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
