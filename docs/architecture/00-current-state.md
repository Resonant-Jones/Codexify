## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-11-02

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The repository migration graph is again a single head, `a3115f64dda8`, and that single-head invariant carries regression coverage. The Private Preview lane was last redeployed on its pinned serving worktree at serving revision `c8e72ef86`, with the live Preview database at Alembic head `3a91d7c4e8b2`. The repository head sits **two schema-carrying revisions** past that live database — `b7e2c4a1d903` (campaign continuation authority provenance) and `d86f2a4b1c90` (coding-worker claim heartbeat on `agent_runs`) — both persistence-only, and neither applied to the live Preview database. The supported runtime has **not** been requalified beyond that one deployed surface, and the release gate remains `HOLD`.

## What changed recently

- Generated the qualification registry instead of asserting it. `scripts/qualification/generate_registry.py` projects rubrics and run receipts into `docs/qualification/registry.json`, its `--check` fails on drift, and `validate_registry.py` enforces that cited rubrics and receipts exist and that a `PASS` carries both a tested commit and evidence. A new `Qualification Contracts` workflow gates all of it in CI.
- Made qualification freshness independent of local git objects. A run is current only when its tested commit is an ancestor of the tip, tested with `git merge-base --is-ancestor`, which answers identically in every checkout. The recorded supported-Compose run tested `5da79431fa`, which is not in the tip's lineage, so the registry now reports `tested_commit_not_in_tip_lineage` instead of a false "surface paths changed" verdict.
- Bound the knowledge-graph corpus to a revision. Canonical source bytes are read from the git object database at each node's own `freshness.verified_commit` rather than from the working tree, and a `rebind` tool writes `content_hash` and `verified_commit` together so they cannot drift apart.
- Widened the Architecture Contracts workflow to trigger on `docs/knowledge-graph/**`, `schemas/knowledge/**`, and `scripts/knowledge_graph/**`, which were outside its filter — the omission that let the corpus drift unnoticed.
- Reunified the two Alembic heads left behind by the coding-claim and campaign-provenance merges, restoring `alembic upgrade head` on `main` at `a3115f64dda8`, with regression suites locking revision-ID uniqueness and mergepoint reachability.
- Integrated the Guardian coding-worker ownership and claim-scoped heartbeat schema and the campaign-continuation authority provenance schema into `main`. Both are persistence only — no worker execution, routing, or credential behaviour changed, and neither is a release claim.
- Authorised Saved Widget promotion and persisted canonical widget revisions on `main`, behind `CODEXIFY_ENABLE_SAVED_WIDGET_ROUTES`, with `saved_widgets` in the `enabled` route posture of the supported profile.
- Published the browser-rendered unread-badge proof against the running Private Preview at serving revision `c8e72ef86`, and the live read-state deployment proof recording 20 of 20 checks at `5569f3f34`.
- Forced the backend verification path in Guardian CI on any manual `workflow_dispatch`, so dispatching on a documentation-only commit can no longer report a successful no-op in place of execution.
- Exposed Library from the main navigation with a four-filter presentation surface, and admitted the share route for private-preview user-to-user messaging.
- Isolated the scheduled release audits onto a dedicated audit checkout pinned to the fetched `origin/main` tip, routed through one guarded publisher landing on that same tip.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- The release gate is `HOLD`, and the generated qualification registry reports `HOLD` for both surfaces it tracks: `supported-compose` and `onboarding-and-people`.
- The registry's `supported-compose` blocker is now precise: its recorded run tested commit `5da79431fa`, which is not an ancestor of the current tip, so the run cannot be shown to describe the code the tip contains. `onboarding-and-people` has no run receipt at all.
- The repository migration graph is a single head, `a3115f64dda8`, and the single-head invariant is covered by regression tests. A head-clean graph is a repository invariant, not a deployment qualification.
- The live Preview database is at `3a91d7c4e8b2`. The repository head is two schema-carrying revisions ahead of it, and the Preview lane has not been advanced to apply them.
- Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, deadlines, and authorization; bounded evidence is not complete runtime qualification.
- Saved Widget **promotion and revision storage** exist on `main`: `POST /saved-widgets`, widget fetch, revision list, and revision fetch are registered behind `CODEXIFY_ENABLE_SAVED_WIDGET_ROUTES`, `saved_widgets` is in the `enabled` route posture of the supported profile, canonical revision persistence is in the database, and route and store tests cover it. This is a promotion and revision-storage slice only, not a qualified widget lifecycle.
- Recipient-local read state is **deployed and live-qualified** on the Private Preview: a two-account live test passed 20 of 20 checks at serving revision `5569f3f34`, covering the unread projection, explicit read advancement, account isolation, watermark accuracy, idempotency, reload persistence, concurrent reads, and the absence of any sender-visible read receipt. The consent HTTP surface is quarantined by the Preview profile, so consent enforcement is proven at the storage layer rather than the endpoint.
- The current serving revision is `c8e72ef86`. The advance from `5569f3f34` changed only `.dockerignore`, `.gitignore`, and documentation, so no application source differs from the evaluated revision. Post-advance observation is limited to health (`200`), the live schema head (`3a91d7c4e8b2`), the Guardian mount source, and running-model identity; **the 20 checks were not re-run against `c8e72ef86`**.
- The unread badge is **browser-rendered and proven** on the Private Preview: in Chrome 156 against the running service at serving revision `c8e72ef86`, the Inbox rendered per-conversation badges reading `3` and `1`, the launcher total read `4` and agreed with the API, and opening a conversation advanced the reader's own cursor and cleared its badge while the neighbouring conversation stayed unread. The badge is proven in one browser only; Firefox, Safari, and the floating conversation window remain unverified.
- The Private Preview deployment sequence itself has been executed against the live Preview — runtime image rebuilt, migrator run, application containers recreated — so that prerequisite is discharged. It covers the Preview lane only and is not a supported-Compose qualification.
- The knowledge-graph corpus is revision-bound: canonical node hashes are validated against the bytes at each node's own declared `verified_commit`, and a governed document that changes now fails the corpus test unless the node already declares itself stale.
- Private Preview same-node messaging has live end-to-end evidence for approved synthetic accounts; this does not qualify share links, cross-node transport, or default Beta support.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Connectors, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, and autonomous coding-worker work are not default Beta support without current-main qualification.

## Not yet true / do not assume

- Do not call the supported path release-ready or treat migration qualification as deployment.
- Do not read a green CI run as runtime qualification. The registry, the corpus validator, and the contract suites are documentation-integrity gates; they prove a claim is checkable, not that the runtime behaves.
- Do not read a `HOLD` registry entry as the whole release verdict, and do not read a `PASS` as lifting the gate: the supported-Compose rubric cannot receive PASS while the browser, restart-recovery, or provenance boundaries are unexercised, and a PASS does not by itself lift the release gate.
- Do not infer a fresh integrated-tip Compose run, restart recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegated worker canary as successful provider execution; the `reasoning_effort` contract still fails before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat merged suites, focused database tests, or deployment rehearsal as live runtime qualification.
- Do not treat the serving-revision advance as a re-run of the live read-state qualification: source equivalence is an observation about code, not a fresh execution of the 20 checks, and a healthy Private Preview is not a supported-Compose qualification.
- Do not read the revision-bound corpus as a re-review. Rebinding is mechanical; the `current-state` node remains explicitly `stale`, so it is not current release proof.
- Do not read Saved Widget promotion and revision storage as widget lifecycle support. Library Widgets collection listing and filtering, invocation, conversational revision and editing, deletion, export and restore, Web Audio, and canvas qualification are all still open, and none of the slice has browser proof.
- Do not read the single-head migration graph as a new qualification of the live Preview database; that database is still at `3a91d7c4e8b2`, and it is two schema-carrying revisions behind the repository head.
- Share links remain bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality. The request-bound history-recall authorization, the Documents and Gallery surface retirement, and the OpenConnector v1.9.4 integration plan are feature-ref only; none of them is `main` behaviour, and the recall change is the largest unreviewed change in that set.

## Active blockers

- No supported-Compose qualification exists inside the tip's lineage. The recorded run tested `5da79431fa`, which is not an ancestor of the tip, so the registry reports `tested_commit_not_in_tip_lineage` and stays `HOLD`.
- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- The live Preview database has not been advanced past `3a91d7c4e8b2`; two persistence-only schema revisions on `main` are unapplied there.
- Frontend frozen-lockfile installation on the supported path remains unrehearsed.
- Cross-browser qualification of the generative-UI containment repair is missing; Chrome 156 is the only reported browser result and Playwright cannot launch on the reported host.
- The UMS/Chronicle lane retains an inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still needs execution against the corrected baseline.
- The explicit-model rejection and delegated worker-to-adapter contract remain unresolved before provider execution claims.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open.
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`; the unread badge is proven in Chrome 156 only.
- The Saved Widget lifecycle is incomplete beyond promotion and revision storage: no Library Widgets collection listing, invocation, conversational editing, deletion, or export and restore path, and no browser proof.

## This week’s priorities

1. Run the supported-Compose qualification on a commit inside the tip's lineage and record it as a dated run receipt, so the registry stops reporting HOLD for a lineage reason.
2. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
3. Complete the frontend frozen-lockfile installation step of the approved deployment sequence; the image rebuild, migrator, and application restart steps have since been executed against the live Preview.
4. Advance the live Preview database to the repository head and re-pin the serving revision, then re-run the 20 read-state checks against that revision.
5. Resolve the explicit-model and delegated-adapter contradictions and execute the blocked Chronicle HTTP cases.
6. Reprove new-thread projection, browser/event coherence, restart recovery, ordinary chat, and scope isolation on one evaluated tip.
7. Close the highest-risk Preview and lifecycle gaps: share-link revocation, import-to-recall, export and restore, cross-browser verification of the now-proven unread badge, and the Saved Widget lifecycle beyond promotion.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists at evaluated mainline tips.
- [x] Release-readiness claims are machine-checkable: the qualification registry is generated and drift-gated, and the knowledge-graph corpus is bound to a revision.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof.
- [ ] Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline.

## How to read the rest of the KB

- `docs/qualification/` is the generated index of qualification evidence, verdicts, and freshness. It normalizes evidence and does not replace architecture proofs or this file.
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
