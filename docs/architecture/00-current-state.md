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

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The release gate is `HOLD` and did not move in the last audit window. The repository migration graph is a single Alembic head, `d91e4fa6702b` — verified at this tip by resolving all 133 revision files — and the single-head invariant carries regression coverage. The stock supported path still fails Gate B: `docker-compose.yml`'s migrator bind-mounts only `./backend:/app/backend` while `backend/migrations` is a symlink to `../guardian/db/migrations`, so the symlink resolves into the baked image and a stock-launched stack serves the application against a schema behind it. `docker-compose.runtime.yml`'s migrator declares no volumes at all. The live Preview database remains at `3a91d7c4e8b2`, four schema-carrying revisions behind the head (`b7e2c4a1d903`, `d86f2a4b1c90`, `e42c7d0b9135`, `d91e4fa6702b`), plus two graph-only mergepoints (`a3115f64dda8`, `c8e42a91d307`). The supported runtime has been qualified on one frozen revision, not at this tip and not on the stock path.

## What changed recently

- **PR #982 hardened the qualification launcher, not the supported path.** `scripts/whooshd_docker_smoke_up.sh` gained an isolated source-matched startup, a `verify_migration_outcome` step that confirms a migration only when the migrator container is unambiguously identified, has exited zero, and the project's own database reports exactly one `alembic_version` row equal to the expected head, plus refusal of any `codexify_private_preview*` Compose project. `tests/test_whooshd_smoke_env_contract.py` grew by roughly 800 lines.
- **PR #984 landed governed account-scoped history recall and chat message origin custody.** New: `guardian/core/account_history_recall.py`, a read-only `GET /api/chat/projects/{project_id}/history/search` route, a model-facing `op::history.search` tool advertised only with a request-scoped grant, and a shared write-side custody rule in `guardian/core/db.py` protecting the reserved `extra_meta.message_origin` member.
- **PR #986 landed durable coding-worker claim persistence** in `guardian/agents/store.py`: acceptance, heartbeat, and terminal transitions are owner-bound conditional updates.
- **PR #987 rebound the `adr-index` knowledge-graph node** to `74fd8f489` and recomputed its content hash. Its freshness state is still `stale`; the corpus was not reverified.
- **PR #989 recorded a qualification capacity preflight**: 30 GiB free, BuildKit cache 0 B across 0 records, 0 B reclaimed, Private Preview unchanged at 18 containers with backend image `sha256:22d9f5f1…e6e5c55`. It does not start QUAL-COMPOSE-02 and qualifies nothing.
- Added the 2026-11-03 daily dev log.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- A supported-Compose qualification exists **inside the tip's lineage**: frozen revision `41ff615293ec`, confirmed an ancestor of this tip, executed 2026-11-02 in an isolated Compose project with no cloud credential present in any qualification container. It is a dated receipt against one frozen revision, not a qualification of this tip and not a qualification of the stock path.
- That receipt's dispositions are exact: Gate A (supported configuration/provider contract) **PASS**, Gate B (startup and migrations) **FAIL** on the stock path, Gate C (explicit-model rejection) **PASS** with provider-side corroboration — a durable terminal failure of the attempt, no model substituted, and no provider-ledger entry for the rejected turn — Gate D (ordinary chat and durable state) **PASS**, Gate E (retrieval and provenance) **PASS** with a recorded durability caveat, Gate F (browser and event coherence) **PASS**, Gate G (restart recovery) **PASS**, Gate H **PASS** for every selector that could execute with **3 selectors INCOMPLETE** for a missing optional `trio` dependency — `trio` is still declared in no requirements file or `pyproject.toml`.
- The stock migrator defect is **still open in the tree at this tip**: `docker-compose.yml` mounts only `./backend:/app/backend` and its own comment records that migration files come from the baked image; `docker-compose.runtime.yml`'s migrator has no volumes. PR #982 changed the qualification launcher only.
- The repository migration graph is a single head, `d91e4fa6702b`. A head-clean graph is a repository invariant, not a deployment qualification. The live Preview database is at `3a91d7c4e8b2`, with the four schema-carrying revisions and two graph-only mergepoints above it unapplied there; the Preview lane has not been advanced.
- The qualification registry still reports `HOLD` for both tracked surfaces, `supported-compose` and `onboarding-and-people`. Its `supported-compose` entry still projects the September run at `5da79431fa`, confirmed not an ancestor of this tip; the November receipt is a proof artifact and does not carry the run-receipt metadata the registry projects, so the registry's own verdict did not move. `onboarding-and-people` still has no run receipt at all.
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

- **Do not read PR #982 as a supported-path fix.** It changed the qualification launcher. The stock migrator still mounts only `./backend` and still resolves migrations from the baked image; the supported path is not repaired by it.
- **Do not read PR #989 as a qualification.** It is a host-capacity measurement. It states that it does not start QUAL-COMPOSE-02, authorizes no qualification run, and qualifies no surface.
- **Do not read the history-recall slice as per-message origin enforcement.** Write-side custody is implemented; reader-side per-message classification, exclusion, and coverage reporting are not. Thread-level scoping is not message-level proof.
- **Do not read the history-recall route's presence as qualification.** It is implemented, mounted, and test-covered; no runtime receipt exists for it, and the model-facing tool only appears with a request-scoped grant.
- **Do not read PR #986 as successful coding-worker execution.** The receipt is persistence proof scoped to a disposable PostgreSQL database, disposition GO for independent reconciliation with Release HOLD.
- **Do not read the qualification as a supported-path qualification.** Gates C through H were executed against a source-mounted comparison stack, not the stock supported path, precisely so the application source and schema were both at the frozen revision. The stock supported path still fails Gate B.
- **Do not read the qualification as a qualification of this tip.** It froze `41ff615293ec`; this tip is a descendant. It is dated evidence about one frozen revision, and a green receipt is not a rolling claim.
- Do not read the qualification as lifting the release gate. Its own conclusion is `HOLD`, and the registry still reports `HOLD` for both tracked surfaces.
- Do not read a green CI run as runtime qualification. The registry, the corpus validator, and the contract suites are documentation-integrity gates; they prove a claim is checkable, not that the runtime behaves.
- Do not read a `PASS` gate as a clean gate. Gate E passes with a recorded durability caveat, Gate H carries 3 INCOMPLETE selectors, and the receipt deliberately records two harness artifacts so they are not mistaken for product behaviour.
- Do not infer that a document that survives a worker kill recovers. A killed `worker-document-embed` left a document permanently in `embedding_status = 'processing'` with no observed recovery or terminal-failure marking, and no sweeper for stuck `processing` documents exists in the tree. The retrieval layer correctly withheld it, which is correct behaviour over an unrecovered document, not a working path.
- Do not use the rag-trace or retrieval-posture surfaces to verify retrieval. They reported empty on both a failing and a successful retrieval, and PR #984 did not change those surfaces. Only per-message `retrieval_provenance` carries the truth.
- Do not read the single-head migration graph as a new qualification of the live Preview database; that database is still at `3a91d7c4e8b2`.
- Do not read a corrected `supported-compose` lineage as qualifying `onboarding-and-people`; that surface still has no run receipt, and the two verdicts are independent.
- Do not treat the registry's projected September run as the newest supported-Compose evidence. It is the newest the registry can see; the November receipt is newer and is not projected.
- Do not read Saved Widget promotion and revision storage as widget lifecycle support. Library Widgets collection listing and filtering, invocation, conversational revision and editing, deletion, export and restore, Web Audio, and canvas qualification are all still open, and none of the slice has browser proof.
- Do not read the delegated worker canary as successful provider execution; the `reasoning_effort` contract still fails before provider execution, worker egress was observed despite `allow_network=false`, and no production caller of `reasoning_effort` exists in `guardian/`.
- Do not read the serving-revision advance as a re-run of the live read-state qualification: source equivalence is an observation about code, not a fresh execution of the 20 checks, and a healthy Private Preview is not a supported-Compose qualification.
- Do not read the `adr-index` rebinding as a corpus re-review. Its freshness state remains `stale`, and the `current-state` node is still `stale`.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality.

## Active blockers

- **The stock supported Compose migrator cannot reach the source tree's migrations.** A stock-launched stack runs a schema behind its own application source. Cause remains isolated to the migrator's bind mount; no remediation has landed, and the receipt does not propose one.
- **The qualification registry has not absorbed the November receipt.** Its `supported-compose` projection still cites the September run at `5da79431fa`, which is not an ancestor of the tip, so the registry reports `tested_commit_not_in_tip_lineage` and stays `HOLD` even though a lineage-valid receipt now exists.
- `onboarding-and-people` has no qualification run receipt at all, so the registry reports `HOLD` for it on absent evidence rather than on a lineage or staleness cause. A supported-Compose run does not qualify this surface.
- A stock-path supported-Compose qualification is missing. Gate B must be re-run and pass after the migrator's migration source is settled; the current receipt explicitly names this as the next proof needed. The instrument now exists to judge it, but the run has not happened.
- The live Preview database has not been advanced past `3a91d7c4e8b2`; four schema-carrying revisions and two mergepoints on `main` are unapplied there.
- **Reader-side per-message origin classification is not implemented.** Imported, unknown, and conflicting messages are not excluded before excerpts reach the model, and no content-free per-message coverage receipts are produced. The governing contract carries this as an open finding.
- A killed `worker-document-embed` leaves the affected document permanently in `embedding_status = 'processing'` with no observed recovery path.
- The rag-trace and retrieval-posture operator surfaces report empty even when retrieval demonstrably succeeded.
- Three `[trio]`-parametrised retrieval selectors cannot execute because the optional `trio` dependency is absent; they are INCOMPLETE, not passes.
- Frontend frozen-lockfile installation on the supported path remains unrehearsed.
- Cross-browser qualification is missing on both the generative-UI containment repair and the unread badge; Chrome 156 is the only reported browser result.
- The UMS/Chronicle lane retains an inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still needs execution against the corrected baseline.
- The delegated worker-to-adapter `reasoning_effort` contract still fails before provider execution, and worker egress was observed despite `allow_network=false`. Explicit-model rejection is proven only at the frozen revision — not on the stock path and not at this tip.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open.
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`.
- The Saved Widget lifecycle is incomplete beyond promotion and revision storage: no Library Widgets collection listing, invocation, conversational editing, deletion, or export and restore path, and no browser proof.

## This week’s priorities

1. Fix the supported-path migrator so the migrator can reach the source tree's migrations, then re-run **Gate B on the stock path** and publish a receipt whose `alembic_version` equals the source head. The launcher now judges that outcome from the database rather than the container's exit code, so this is the one defect that blocks the supported path from being self-consistent.
2. Add a qualification run receipt for the November run so the registry projects a lineage-valid `supported-compose` verdict instead of the stale September entry.
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
- [x] A supported-Compose qualification exists inside the tip's lineage, covering explicit-model rejection with provider-side non-execution evidence, ordinary chat with durable state, retrieval with attribution, browser/event coherence, and restart recovery.
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
