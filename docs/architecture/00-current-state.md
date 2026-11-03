## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-11-03

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The repository migration graph is a single Alembic head, `d91e4fa6702b`, and the single-head invariant carries regression coverage. A supported-Compose qualification was executed on 2026-11-02 against frozen revision `41ff615293ec`, which **is** an ancestor of this tip: seven of eight gates passed, and **Gate B (startup and migrations) FAILED on the stock supported path**. That failure is a product defect in the supported path, not a harness artifact: the stock migrator applies the baked image's Alembic head `3a91d7c4e8b2` instead of the frozen source head, so a stock-launched stack serves the application against a schema behind it. The live Preview database remains at `3a91d7c4e8b2`, and the repository head is now **four schema-carrying revisions** ahead of it: `b7e2c4a1d903`, `d86f2a4b1c90`, `e42c7d0b9135`, and `d91e4fa6702b`. The supported runtime has been qualified on one frozen revision, not at the tip and not on the stock path. The release gate remains `HOLD`.

## What changed recently

- Ran the first supported-Compose qualification whose tested revision sits inside the tip's lineage. It froze `41ff615293ec`, ran in an isolated Compose project (`codexify_qual`), and left the Private Preview untouched. Seven of eight gates passed; Gate B failed.
- Found and isolated a supported-path defect: the migrator bind-mounts only `./backend`, while `backend/migrations` is a symlink to `../guardian/db/migrations`, so the symlink resolves into the baked image. The stock migrator therefore stops at `3a91d7c4e8b2`. Adding the guardian mount as a diagnostic proves the frozen revisions apply cleanly — isolating the cause to the mount, not the migrations. `docker-compose.runtime.yml`'s migrator declares no volumes at all and is worse.
- Proved explicit-model rejection for the first time with provider-side evidence: an absent model fails as a durable terminal `task.failed` carrying `local_model_unavailable`, with `attempted: false`, `executed: false`, `fallback_attempted: false`, no provider-ledger entry for the rejected turn, and no assistant message persisted.
- Qualified browser and event coherence in real Chrome 156 against the supported frontend, and qualified restart recovery: durable counts and content fingerprints matched across a restart of `backend`, `worker-chat`, and `worker-document-embed`, and a new chat completed afterwards.
- Recorded two real durability and diagnostics gaps against passing gates: a killed `worker-document-embed` left a document permanently in `embedding_status = 'processing'` with no observed recovery, and the rag-trace and retrieval-posture operator surfaces reported empty even on a successful retrieval.
- Advanced the migration graph: `d91e4fa6702b` (observe-only, account-owned inference attempt metering) landed on 2026-11-01 via PR #974, making the head four schema-carrying revisions ahead of the live Preview database rather than two.
- Added the 2026-11-02 daily dev log.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- A supported-Compose qualification exists **inside the tip's lineage** for the first time: frozen revision `41ff615293ec`, executed 2026-11-02, in an isolated Compose project with no cloud credential present in any qualification container. It is a dated receipt against one frozen revision, not a qualification of this tip and not a qualification of the stock path.
- That receipt's dispositions are exact: Gate A (supported configuration/provider contract) **PASS**, Gate B (startup and migrations) **FAIL**, Gate C (explicit-model rejection) **PASS**, Gate D (ordinary chat and durable state) **PASS**, Gate E (retrieval and provenance) **PASS** with a recorded durability caveat, Gate F (browser and event coherence) **PASS**, Gate G (restart recovery) **PASS**, Gate H (other baseline gates) **PASS** for every selector that could execute with **3 selectors INCOMPLETE** for a missing optional `trio` dependency.
- Gate B's failure is a supported-path product defect: on the stock path the migrator applies the baked image's Alembic head `3a91d7c4e8b2` instead of the frozen source head, because `backend/migrations` is a symlink to `../guardian/db/migrations` and the migrator mounts only `./backend:/app/backend`. A Docker bind mount does not carry a symlink target across the mount boundary. `docker-compose.runtime.yml`'s migrator has no volumes at all. The diagnostic comparison run proves the frozen revisions apply cleanly once the migrator can see the source tree.
- The repository migration graph is a single head, `d91e4fa6702b`, and the single-head invariant is covered by regression tests. A head-clean graph is a repository invariant, not a deployment qualification.
- The live Preview database is at `3a91d7c4e8b2`. The repository head is **four** schema-carrying revisions ahead of it — `b7e2c4a1d903` (campaign continuation authority provenance), `d86f2a4b1c90` (coding-run claim heartbeat), `e42c7d0b9135` (coding-worker ownership), and `d91e4fa6702b` (inference usage metering) — and the Preview lane has not been advanced to apply them.
- The qualification registry still reports `HOLD` for both tracked surfaces, `supported-compose` and `onboarding-and-people`. Its `supported-compose` entry still projects the September run at `5da79431fa`, which is not an ancestor of this tip; the November receipt is a proof artifact and does not carry the run-receipt metadata the registry projects, so the registry's own verdict did not move.
- Explicit-model rejection is now proven at the frozen revision with provider-side corroboration: the rejection is a durable terminal failure of the attempt, not a synchronous HTTP refusal, no model was substituted, and the provider's own ledger contains no request for the rejected turn.
- Ordinary chat, durable persistence and readback, retrieval with source attribution, browser-driven event coherence, and restart recovery are all proven at the frozen revision. Retrieval carries a recorded durability caveat, and the operator retrieval surfaces are not trustworthy as evidence.
- Saved Widget **promotion and revision storage** exist on `main`: `POST /saved-widgets`, widget fetch, revision list, and revision fetch are registered behind `CODEXIFY_ENABLE_SAVED_WIDGET_ROUTES`, `saved_widgets` is in the `enabled` route posture of the supported profile, canonical revision persistence is in the database, and route and store tests cover it. This is a promotion and revision-storage slice only, not a qualified widget lifecycle.
- Recipient-local read state is **deployed and live-qualified** on the Private Preview: a two-account live test passed 20 of 20 checks at serving revision `5569f3f34`, and the advance to the current serving revision `c8e72ef86` changed only `.dockerignore`, `.gitignore`, and documentation, so no application source differs from the evaluated revision. The 20 checks were not re-run against `c8e72ef86`.
- The unread badge is **browser-rendered and proven** on the Private Preview: in Chrome 156 against the running service at serving revision `c8e72ef86`, the Inbox rendered per-conversation badges reading `3` and `1`, the launcher total read `4` and agreed with the API, and opening a conversation advanced the reader's own cursor and cleared its badge while the neighbouring conversation stayed unread. The badge is proven in one browser only.
- `direct_messages` is mounted `internal_only` on the supported profile. Share links remain bearer credentials: `expires_in_days` is optional on creation and no revocation endpoint exists.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Connectors, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, and autonomous coding-worker work are not default Beta support without current-main qualification.

## Not yet true / do not assume

- **Do not read the new qualification as a supported-path qualification.** Gates C through H were executed against a source-mounted comparison stack, not the stock supported path, precisely so the application source and schema were both at the frozen revision. The stock supported path still fails Gate B. Nothing here says a stock-launched stack is correct.
- **Do not read the qualification as a qualification of this tip.** It froze `41ff615293ec`; this tip is a descendant. It is dated evidence about one frozen revision, and a green receipt is not a rolling claim.
- Do not read the qualification as lifting the release gate. Its own conclusion is `HOLD`, and the registry still reports `HOLD` for both tracked surfaces.
- Do not read a green CI run as runtime qualification. The registry, the corpus validator, and the contract suites are documentation-integrity gates; they prove a claim is checkable, not that the runtime behaves.
- Do not read a `PASS` gate as a clean gate. Gate E passes with a recorded durability caveat, Gate H carries 3 INCOMPLETE selectors, and the receipt deliberately records two harness artifacts so they are not mistaken for product behaviour.
- Do not infer that a document that survives a worker kill recovers. A killed `worker-document-embed` left a document permanently in `embedding_status = 'processing'` with no observed recovery or terminal-failure marking. The retrieval layer correctly withheld it, which is correct behaviour over an unrecovered document, not a working path.
- Do not use the rag-trace or retrieval-posture surfaces to verify retrieval. They reported empty on both a failing and a successful retrieval. Only per-message `retrieval_provenance` carries the truth.
- Do not infer exact unavailable-model rejection from the September receipt — that gap is now closed by the November receipt at the frozen revision. But do not infer it either for the stock path or at this tip; the same migrator defect means the frozen schema is not what a stock stack serves.
- Do not read the single-head migration graph as a new qualification of the live Preview database; that database is still at `3a91d7c4e8b2`, and it is now four schema-carrying revisions behind the repository head.
- Do not read a corrected `supported-compose` lineage as qualifying `onboarding-and-people`; that surface still has no run receipt, and the two verdicts are independent.
- Do not treat the registry's projected September run as the newest supported-Compose evidence. It is the newest the registry can see; the November receipt is newer and is not projected.
- Do not read Saved Widget promotion and revision storage as widget lifecycle support. Library Widgets collection listing and filtering, invocation, conversational revision and editing, deletion, export and restore, Web Audio, and canvas qualification are all still open, and none of the slice has browser proof.
- Do not read the delegated worker canary as successful provider execution; the `reasoning_effort` contract still fails before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not read the serving-revision advance as a re-run of the live read-state qualification: source equivalence is an observation about code, not a fresh execution of the 20 checks, and a healthy Private Preview is not a supported-Compose qualification.
- Do not read a revision-bound corpus as a re-review. Rebinding is mechanical; the `current-state` node remains explicitly `stale`, so it is not current release proof.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality.

## Active blockers

- **The stock supported Compose migrator cannot reach the source tree's migrations.** A stock-launched stack runs a schema behind its own application source. Cause isolated to the migrator's bind mount; no remediation has landed, and the fix is not proposed by the receipt.
- **The qualification registry has not absorbed the November receipt.** Its `supported-compose` projection still cites the September run at `5da79431fa`, which is not an ancestor of the tip, so the registry reports `tested_commit_not_in_tip_lineage` and stays `HOLD` even though a lineage-valid receipt now exists.
- `onboarding-and-people` has no qualification run receipt at all, so the registry reports `HOLD` for it on absent evidence rather than on a lineage or staleness cause. A supported-Compose run does not qualify this surface.
- A stock-path supported-Compose qualification is missing. Gate B must be re-run and pass after the migrator's migration source is settled; the current receipt explicitly names this as the next proof needed.
- The live Preview database has not been advanced past `3a91d7c4e8b2`; four persistence-only schema revisions on `main` are unapplied there.
- A killed `worker-document-embed` leaves the affected document permanently in `embedding_status = 'processing'` with no observed recovery path.
- The rag-trace and retrieval-posture operator surfaces report empty even when retrieval demonstrably succeeded.
- Three `[trio]`-parametrised retrieval selectors cannot execute because the optional `trio` dependency is absent; they are INCOMPLETE, not passes.
- Frontend frozen-lockfile installation on the supported path remains unrehearsed.
- Cross-browser qualification is missing on both the generative-UI containment repair and the unread badge; Chrome 156 is the only reported browser result.
- The UMS/Chronicle lane retains an inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still needs execution against the corrected baseline.
- The explicit-model rejection and delegated worker-to-adapter contract remain unresolved before provider execution claims.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open.
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`.
- The Saved Widget lifecycle is incomplete beyond promotion and revision storage: no Library Widgets collection listing, invocation, conversational editing, deletion, or export and restore path, and no browser proof.

## This week’s priorities

1. Fix the supported-path migrator so the migrator can reach the source tree's migrations, then re-run **Gate B on the stock path** and publish a receipt whose `alembic_version` equals the frozen source head. This is the one defect that blocks the supported path from being self-consistent.
2. Add a qualification run receipt for the November run so the registry projects a lineage-valid `supported-compose` verdict instead of the stale September entry. Registry drift-gating is only meaningful once the newest evidence is machine-readable to it.
3. Advance the live Preview database through the approved migration and deployment sequence with a verified recovery path, re-pin the serving revision, and re-run the 20 read-state checks against that revision.
4. Advance the live Preview database past `3a91d7c4e8b2` so the four unapplied schema revisions land, and re-verify the Preview against the advanced schema.
5. Characterise the document-embed failure path under a kill injected at a controlled point, so `processing` documents are either recovered or terminally failed.
6. Populate the rag-trace and retrieval-posture surfaces, or mark them as non-evidence, so operator-facing retrieval diagnostics can be qualified rather than only per-message provenance.
7. Run a first qualification for `onboarding-and-people`, which still has no run receipt; a supported-Compose run does not qualify that second surface.
8. Complete the frontend frozen-lockfile installation step of the approved deployment sequence.
9. Resolve the explicit-model and delegated-adapter contradictions, execute the blocked Chronicle HTTP cases, and close the remaining Preview and lifecycle gaps: share-link revocation, import-to-recall, export and restore, cross-browser verification, and the Saved Widget lifecycle beyond promotion.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists at evaluated mainline tips.
- [x] Release-readiness claims are machine-checkable: the qualification registry is generated and drift-gated, and the knowledge-graph corpus is bound to a revision.
- [x] A supported-Compose qualification exists inside the tip's lineage, covering explicit-model rejection with provider-side non-execution evidence, ordinary chat with durable state, retrieval with attribution, browser/event coherence, and restart recovery.
- [ ] The **stock** supported Compose path applies the source head's migrations; a stock-path run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] Each tracked qualification surface carries its own dated run receipt inside the tip's lineage; a receipt for one surface does not qualify another, and a proof artifact that the registry cannot read does not qualify it either.
- [ ] The live Preview database is advanced past `3a91d7c4e8b2` and the four unapplied schema revisions land.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] A document left in `embedding_status = 'processing'` by a worker kill is recovered or terminally failed.
- [ ] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof.
- [ ] Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline.

## How to read the rest of the KB

- `docs/qualification/` is the generated index of qualification evidence, verdicts, and freshness. It normalizes evidence and does not replace architecture proofs or this file.
- `docs/architecture/proofs/runtime/` holds the dated runtime receipts, including the supported-Compose qualification at `41ff615293ec`.
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
