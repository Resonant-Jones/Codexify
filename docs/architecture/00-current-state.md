## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-11-08

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

Every runtime or implementation claim below is stated against `origin/main` only. Work that exists on a branch, in a draft, or in an open pull request is recorded as intent, never as shipped reality. Explicitly approved governance decisions may be recorded locally before publication; their acceptance does not imply implementation, merge or release qualification.

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The release gate remains `HOLD`.

- The migration graph is a single Alembic head, `b3f8c2d1e907`, across 137 revision files — re-verified at this tip by Alembic's own revision map and by the repository's single-head regression test.
- **No tracked qualification surface is currently `current` against this tip.** The registry projects `supported-compose` (source-matched launcher) as `PASS` but `stale`, `supported-compose-stock` (stock Compose) as `PASS` but `stale`, and `onboarding-and-people` and `release-readiness-gates` as `HOLD` on absent evidence. The registry's blocker strings carry the exact path counts.
- The two startups are not interchangeable: the *stock* startup (`docker compose up` against the pre-baked image) and the *source-matched launcher* (`scripts/whooshd_docker_smoke_up.sh full --detach`) carry independent verdicts, each qualified only at its own frozen revision.
- The live Preview database tracks the **serving source's** head, not `main`'s -- the reconciler advances it to whatever the pinned serving checkout contains -- so its distance from the published head moves as `main` moves. It was last measured at `c4f7a9e2b810` (2026-11-07 receipt), one revision behind this tip's head; that position and its restore-equivalence are dated observations in the runtime receipt, and must be re-measured rather than carried forward. That is a live-surface receipt for one surface, not a release decision.
- Host capacity is no longer a constraint on paper (a 2026-11-05 measurement returned **GO**), but the host itself killed Docker Desktop under memory pressure on 2026-11-07. Two heavy Docker workloads must never run concurrently here.

## What changed recently

Since the 2026-11-07 audit (`e239d3987`), the meaningful shifts on `main` are:

- **CI now always runs the suite on the tip of `main`** (`7d7d71ba7`, #1049). A documentation-only push to `main` used to produce a green "Backend Tests" check whose pytest step never ran; the tip is now forced to execute, while a superseded revision still no-ops.
- **The CI run matrix is an enforced invariant, not a convention** (`f081e8e41`, #1050). `tests/architecture/test_ci_run_matrix_contract.py` executes the workflow's own step bodies instead of restating the matrix, and pins the ordering constraint that the tip-of-main rule must follow the superseded-revision skip. All 17 cases pass at this tip.
- **The eight-gate harness's self-test no longer passes at this tip.** `scripts/ops/eight_gate_evidence_selfcheck.py` reports **53 of 54** checks, failing exactly one: the migration gate's expectation that the evaluated checkout's head is `a7d4c9e2f1b3`, the head when the harness shipped. This tip's head is `b3f8c2d1e907`. The defect is in the self-test's expectation, not in the harness -- `eight_gate_evidence.py` computes the head from the checkout's own source and hard-codes no head. **The previous audit's "passes 54/54 on this tip's tree" was already false at its own tip**: the head advanced at `784810f8d` before that audit ran.
- The eight-gate evidence harness, its 54-check self-test, and rubric version 3 shipped earlier in the same window, and pausing the Private Preview became a documented precondition of the run (`7b0cbb3b1`). The integrated eight-gate run against one frozen tip still has not been executed: the harness report states no gate reached PASS, because no disposable stack was up.
- The stock Compose surface was qualified at `844b35599ed6` and then went stale; the earlier `FAIL` at `456da46b8` stays in the repository as the evidence of the collection-dimension defect and its repair.
- The `reasoning_effort` contract has a live proof whose evaluated source is a disposable worktree commit `64ef74756`, not reachable from `origin/main`; the mainline revision with the identical tree is `dc2f0f921`, so the proof is reviewable on main. Two facts stay open: no supported profile mounts the delegated routes, and the provider transport completed despite `allow_network=false`.
- The root README's Repo Structure section was corrected and bound to a validator (`54f4d5618`), and the registry was regenerated at the merged tip rather than hand-edited; `generate_registry.py --check` passes at this tip.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`. The startup path is part of that supported path, and the two available startups are not interchangeable.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics. Qualification is a separate gate.
- The repository migration graph is a single head, `b3f8c2d1e907`. A head-clean graph is a repository invariant, not a deployment qualification. The live Preview database tracks the serving source's head, with the image's baked migration source proven byte-identical to the served checkout by SHA-256 inside the image and the live `alembic_version` read directly out of PostgreSQL as one row.
- **Account-scoped history recall is implemented on `main` and mounted.** `GET /api/chat/projects/{project_id}/history/search` resolves the account from authenticated authority only, and it is reachable on the supported profile because route posture is per-router and `api_chat` is in that profile's `enabled` posture. The model-facing `op::history.search` tool is advertised only when a request-scoped grant is present. Coverage is code and test level only.
- **Native assertion write custody and reader classification exist; durable same-row custody is pending.** `guardian/core/message_origin_classification.py` classifies each candidate message at read time from its own persisted evidence, and the recall reader excludes imported, unknown and conflicting messages before excerpts reach the model. The coverage receipt carries content-free per-message exclusion counts separate from thread-level counters. No schema change, no migration, no backfill. **Accepted architecture is distinct:** the `native_origin_custody` column, migration, trusted creation-only writers, PostgreSQL immutability and custody-aware reader verification are unimplemented.
- **The coding-worker lane is merged code, not qualified execution.** Claim persistence is in `guardian/agents/store.py`; the pre-acceptance refusal is deployment-scoped and fenced. None of these merges lifts the gate.
- **The Music Producer surface is merged code behind a quarantining profile.** `music_projects` is not in the default profile's route posture; it is reachable only under `v1-music-producer`, which is not a qualified supported path. ADR-108 is proposed, not accepted. **The host owns the job's attribution**: it records which project a music job belongs to when the handle is minted, in its own `music_jobs` table, so the finished files are placed against the right project even when the service echoes nothing back.
- Saved Widget **promotion and revision storage** exist on `main` behind `CODEXIFY_ENABLE_SAVED_WIDGET_ROUTES`. This is a promotion and revision-storage slice only, not a qualified widget lifecycle.
- `direct_messages` is mounted `internal_only` on the supported profile. Share links remain bearer credentials: `expires_in_days` is optional on creation and no revocation endpoint exists.
- Recipient-local read state is deployed and live-qualified on the Private Preview: a two-account live test passed 20 of 20 checks, re-run against the merged mainline. The unread badge is browser-rendered and proven in Chrome 156 on one browser only.
- Ordinary chat, durable persistence and readback, retrieval with source attribution, browser-driven event coherence, and restart recovery are proven at frozen revisions. Bounded evidence is not complete runtime qualification; per-message `retrieval_provenance` remains the carrier of retrieval truth, and the operator retrieval surfaces are not trustworthy as evidence on their own.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Connectors, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, and autonomous coding-worker work are not default Beta support without current-main qualification.

## Not yet true / do not assume

- Capabilities without current-main qualification are not default Beta support.
- **Do not read any qualification surface as current.** `supported-compose` and `supported-compose-stock` are both `PASS` but both `stale`; `onboarding-and-people` and `release-readiness-gates` have no run receipt at all. Qualification is commit-bound, and a green receipt does not travel forward.
- **Do not read one qualified surface as a qualified release.** A receipt for one surface does not qualify another, and a proof artifact the registry cannot read does not qualify it either. The release gate remains `HOLD`.
- **Do not read the eight-gate rubric or its harness as a qualification.** The rubric fixes the judgement rules in advance — UNPROVEN is not PASS, and a gate not exercised at the run's own revision is UNPROVEN — and no integrated run against a frozen tip has been executed. The harness report states plainly that no gate reached PASS.
- **Do not read the harness self-test as passing.** It reports 53 of 54 at this tip: the harness is sound, but the self-test's own head expectation is pinned to a superseded revision. A green self-test is not a property that survives a migration landing.
- **Do not read the delegation proof as a supported-path proof or as network-egress evidence.** No supported profile mounts the delegated routes, the proof ran on a proof-only profile, and the provider transport completed despite `allow_network=false`. That transport is what the coding harness needs to serve the task; agent-controlled network access is a different authority domain (ADR-077) and remains untested.
- **Do not read the reader-side classifier as the accepted durable custody mechanism.** Classification and exclusion are implemented; the same-row `native_origin_custody` column, its guarded writers, PostgreSQL immutability and custody-aware reader verification are not. ADR-016's acceptance is architecture, not shipped custody.
- **Do not read the Music Producer surface as default Beta support**, do not read ADR-108 as accepted, and do not read the engine pin as implementing the Studio v1 plan.
- **Do not read the history-recall slice as per-message origin enforcement, or the route's presence as qualification.** Thread-level scoping is not message-level proof. The route is implemented, mounted, and test-covered, but no runtime receipt exists for it, and the model-facing tool only appears with a request-scoped grant. The recall contract's own findings table still records three open items — the PostgreSQL `get_session` mismatch, missing ordinary-chat advertisement forwarding, and 500-thread coverage truncation.
- **Do not read a green CI run, a `PASS` gate, or a host-capacity `GO` as runtime qualification.** They prove a claim is checkable, or that a precondition holds; they do not prove the runtime behaves. The tip of `main` now always executes the suite, which removes the false-green case where a check passed without running; it still proves only that the suite's own assertions hold. The same applies to the README validators.
- Do not infer that a document left in `processing` recovers. The age-based sweeper terminally fails abandoned documents; re-embedding is not provably idempotent, so the outcome is failure, not a silent double-index.
- Do not read the registry's blocker strings as optional detail. They carry the exact per-surface path counts that make a `stale` projection auditable, and this document deliberately does not copy those counts.
- Do not read the release metadata sentinel as describing this tip. `docs/audits/generated/2026-11-06-beta-sentinel.json` is a dated snapshot of the tree it was generated from.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality.

## Active blockers

- **No tracked qualification surface is `current` against this tip.** Both `PASS` surfaces are `stale` and both `HOLD` surfaces have no receipt. The re-qualification that would restore `current` for the stock surface is the outstanding release-lane work, and the supported-compose qualification against this tip is missing: a qualification is commit-bound, so no supported-compose qualification describes the current tip.
- `onboarding-and-people` has no qualification run receipt at all, so the registry reports `HOLD` on absent evidence. **It needs two distinct non-developer tester accounts; no agent-run can close it.**
- **The eight-gate integrated run has not been executed.** The rubric and harness exist; the run against one frozen tip, isolated from the Private Preview, is what remains.
- **The eight-gate self-test's head expectation is stale** (`a7d4c9e2f1b3` against this tip's `b3f8c2d1e907`). Until it is re-pinned, the self-test reports 53/54 and the harness's own self-description is not self-consistent.
- **The host killed Docker Desktop under memory pressure on 2026-11-07**, taking the Preview's containers and a concurrent proof with it. The pause precondition is now recorded, but a heavy run beside a live Preview on this host is the condition that killed the VM.
- The live Preview database has been advanced under a proven recovery path and re-proven by dumping the live database, restoring it into a disposable database, and comparing every public table row-for-row -- equivalent -- and the twenty read-state checks re-run and passing. This qualifies that one live surface and nothing else.
- Reader-side per-message origin classification is implemented; the accepted durable same-row custody mechanism still requires its schema, guarded writer/admission channel, reader integration and disposable PostgreSQL proof.
- Three `[trio]`-parametrised retrieval selectors cannot execute, so they are INCOMPLETE rather than passes. `trio` is pinned only in the unreferenced legacy `requirements/backend-old.txt` and `requirements/deprecated/requirements.txt`, and is absent from every active install input.
- Frontend frozen-lockfile installation on the supported install path remains unrehearsed, and cross-browser qualification is missing on both the generative-UI containment repair and the unread badge; Chrome 156 is the only reported browser result.
- The `events_outbox` retention lifecycle has no bounded decision. The schema-only `status` column carries no runtime semantics, nothing transitions it, the read path never filters on it, and no production caller deletes rows — while the SSE path deliberately retains them so concurrent clients can resume independently.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open. The Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`.
- The Saved Widget lifecycle is incomplete beyond promotion and revision storage: no Library Widgets collection listing, invocation, conversational editing, deletion, or export and restore path, and no browser proof.

## This week’s priorities

1. Re-pin the eight-gate self-test's expected migration head to the resolved head, so the harness's self-description is honest again and its 54 checks pass at the tip.
2. Re-run the stock Compose qualification at the current tip so `supported-compose-stock` is `current` rather than `stale`, and let the registry carry the path count.
3. Execute the eight-gate integrated run against one frozen tip, with the Private Preview paused first, and write the run receipt that `release-readiness-gates` still lacks.
4. Run the first qualification for `onboarding-and-people`. Two distinct non-developer accounts are required; no agent-run can close it.
5. Give the `events_outbox` retention lifecycle a bounded decision: give `status` meaning or drop it, and decide whether retention is bounded, without breaking SSE resume behaviour.
6. Complete the frontend frozen-lockfile installation step of the approved deployment sequence.
7. Separately authorize the accepted durable-custody extension — its migration, exclusive native writers and custody-aware reader verification — and do not reimplement the existing classifier.
8. Close the remaining Preview and lifecycle gaps: share-link revocation, import-to-recall, export and restore, cross-browser verification, and the Saved Widget lifecycle beyond promotion.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists at evaluated mainline tips.
- [x] Release-readiness claims are machine-checkable: the qualification registry is generated and drift-gated, and the knowledge-graph corpus is bound to a revision.
- [x] A supported-Compose qualification exists inside the tip's lineage, on the source-matched launcher startup, covering explicit-model rejection with provider-side non-execution evidence, ordinary chat with durable state, retrieval with attribution, browser/event coherence, and restart recovery.
- [x] A migration is judged by the database's own `alembic_version`, not by a container's exit code, and the stock migrator refuses to run against a migration source that does not describe this checkout.
- [x] The **stock** supported Compose path applies the source head's migrations — proven on the stock path by direct `alembic_version` readback, including refusal of a stale image, a same-head image with different content, and a same-head source with a different migration environment.
- [x] A stock-path qualification run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery, under a `supported-compose-stock` rubric with its own run receipt and registry entry. **Closed at `844b35599ed6`** by the stock-path run, verdict `PASS`. The earlier run at `456da46b8` remains in the repository as a `FAIL` receipt, so the defect and its repair stay on the record.
- [ ] Each tracked qualification surface carries its own dated run receipt inside the tip's lineage and is not `stale` against it. **Partially satisfied, and currently satisfied by no surface at all.** Both `PASS` surfaces are `stale`; both `HOLD` surfaces have no receipt at all.
- [x] The live Preview database is advanced past `3a91d7c4e8b2` and the five unapplied schema revisions land. **Closed at `dece01821`**: the live database moved to `a7d4c9e2f1b3`, every pre-existing row preserved, and the live `alembic_version` was read directly out of PostgreSQL as `a7d4c9e2f1b3` with exactly one row. The recovery path was proven rather than assumed.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip. **Rubric written and harness shipped; the harness's own self-test is currently 53/54 and the integrated run is outstanding.**
- [x] A document left in `embedding_status = 'processing'` by a worker kill is recovered or terminally failed. **Closed at `456da46b8`**: a bounded age-based sweeper terminally fails abandoned documents with a recorded reason.
- [x] Per-message origin classification excludes imported, unknown, and conflicting messages before excerpts reach the model. **Closed at `456da46b8`**. This closes the classification/exclusion criterion; it does not establish the accepted durable custody representation.
- [x] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof. **Closed**: the governed effort reached the adapter instead of the adapter's own default, in the proof at `docs/architecture/proofs/runtime/2026-11-06-guardian-delegation-reasoning-effort-live-proof.md` (evaluated source `dc2f0f921` on main). The run was **not** on a supported path, and the network-egress surface is still advisory.
- [x] Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline. **Closed at `e66beb502`**: the release metadata was regenerated at the evaluated mainline and records a clean tree with a platform-readiness audit of 42 pass / 12 warn / 0 fail. The artifact is a dated snapshot of the tree it was generated from.

## How to read the rest of the KB

- `docs/qualification/` is the generated index of qualification evidence, verdicts, and freshness. It normalizes evidence and does not replace architecture proofs or this file.
- `docs/architecture/proofs/runtime/` holds the dated runtime receipts; `docs/architecture/proofs/supported-compose/` holds the supported-Compose qualification receipts, including the stock-path run at `844b35599ed6`.
- `account-history-recall-contract.md` governs account-scoped history recall and message-origin custody, and states its own open findings.
- `adr/108-codexify-music-producer-authority-and-agentdaw-service-boundary.md` records the proposed Music Producer authority boundary; proposed is not accepted.
- `system-overview.md` explains structure, `flows.md` runtime behavior, `data-and-storage.md` persistence and invariants, and `config-and-ops.md` operator truth. None of them is release readiness.
- `roadmap-signals.md` is planning guidance, not live status, and `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
