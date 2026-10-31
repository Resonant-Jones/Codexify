## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-31

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. The repository migration graph is again a single head, `a3115f64dda8`, and that single-head invariant now carries regression coverage. The Private Preview lane was last redeployed on its pinned serving worktree at serving revision `c8e72ef86`, with the live Preview database at Alembic head `3a91d7c4e8b2`; the repository head has moved past that only through graph-only merge revisions, so no schema change is outstanding. The supported runtime has **not** been requalified beyond that one deployed surface, and the release gate remains `HOLD`.

## What changed recently

- Reunified the two Alembic heads that PR #958 and PR #959 left behind. The coding-worker claim branch `c8e42a91d307` and the campaign-provenance branch `b7e2c4a1d903` now join under the no-op mergepoint `a3115f64dda8`, restoring `alembic upgrade head` on `main`.
- Added two migration regression suites that lock the single-head invariant: revision-ID uniqueness with mergepoint reachability across every branch of the graph, and the campaign-provenance/coding-claim mergepoint specifically.
- Clarified the Saved Widget promotion credential contract on the route itself: in the local single-user deployment the static Guardian API key is accepted and resolves to that deployment's own local user identity; in the remote and private-preview lanes an authenticated account session is required and a static API key is refused. This is a contract clarification, not a behaviour change, and promotion remains account-action attribution rather than attestation of a physical human's presence.
- Forced the backend verification path in Guardian CI on any manual `workflow_dispatch`, so dispatching on a documentation-only commit can no longer report a successful no-op in place of execution.
- Isolated the scheduled release audits onto a dedicated audit checkout pinned to the fetched `origin/main` tip, and routed their current-state output through one guarded publisher that lands on that same tip. This changes how release truth is maintained; it does not change the release posture.
- Integrated recipient-local direct-message read state across the Inbox, launcher, and floating conversation surfaces, with monotonic watermarks and serialized concurrent cursor updates.
- Reconciled the Saved Widget, automatic-collection consent, and read-cursor migrations into one Alembic head.
- Integrated the Guardian coding-worker ownership and claim-scoped heartbeat schema and the campaign-continuation authority provenance schema into `main`. Both are persistence only — no worker execution, routing, or credential behaviour changed, and neither is a release claim.
- Added accepted ADR-105 operator-actor and human-approval provenance boundaries; governance evidence, not autonomous execution or release expansion.
- Qualified the committed migration chain on the supported `postgres:15` / PostgreSQL 15.19 path using an empty database and a restored, read-only copy of the Preview database; existing rows were preserved.
- Rehearsed the real image/migrator mechanism and recorded two traps: the backend entrypoint's `alembic` call is a swallowed no-op, and the migrator reads migrations from the baked image rather than the source mount.
- Proved the unread badge in a real browser against the running Private Preview — Inbox and launcher badges render and agree with the API, and opening a conversation clears that reader's badge only — and recorded the account-scoped cleanup that removed the proof accounts without touching another account's durable read cursor.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, deadlines, and authorization; bounded evidence is not complete runtime qualification.
- The repository migration graph is a single head, `a3115f64dda8`, and the single-head invariant is now covered by regression tests. A head-clean graph is a repository invariant, not a deployment qualification.
- The migration chain is qualified on the supported PostgreSQL version in disposable clean and restored-copy runs, and has since been applied to the **live** Private Preview database, which advanced `f0d7c4b2a198` → `3a91d7c4e8b2` with every pre-existing row preserved. The live Preview database has **not** been advanced past `3a91d7c4e8b2`.
- Saved Widget **promotion and revision storage** exist on `main`: `POST /saved-widgets`, widget fetch, and revision list and fetch are registered behind `CODEXIFY_ENABLE_SAVED_WIDGET_ROUTES`, `saved_widgets` is in the `enabled` route posture of the supported profile, canonical revision persistence is in the database, and route and store tests cover it. This is a promotion and revision-storage slice only, not a qualified widget lifecycle.
- Recipient-local read state is **deployed and live-qualified** on the Private Preview: a two-account live test passed 20 of 20 checks at serving revision `5569f3f34`, covering the unread projection, explicit read advancement, account isolation, watermark accuracy, idempotency, reload persistence, concurrent reads, and the absence of any sender-visible read receipt. The consent HTTP surface is quarantined by the Preview profile, so consent enforcement is proven at the storage layer rather than the endpoint.
- The current serving revision is `c8e72ef86`. The advance from `5569f3f34` changed only `.dockerignore`, `.gitignore`, and documentation, so no application source differs from the evaluated revision. The backend's `/app/guardian` bind mount is the serving worktree's own `guardian/` tree, and the container's `guardian/db/models.py` hashes identically to the worktree copy. Post-advance observation is limited to health (`200`), the live schema head (`3a91d7c4e8b2`), the Guardian mount source, and running-model identity; **the 20 checks were not re-run against `c8e72ef86`**.
- The Private Preview deployment sequence itself has been executed against the live Preview — runtime image rebuilt, migrator run, application containers recreated — so that prerequisite is discharged. It covers the Preview lane only and is not a supported-Compose qualification.
- The unread badge is **browser-rendered and proven** on the Private Preview: in Chrome 156 against the running service at serving revision `c8e72ef86`, the Inbox rendered per-conversation badges reading `3` and `1`, the launcher total read `4` and agreed with the API, and opening a conversation advanced the reader's own cursor and cleared its badge while the neighbouring conversation stayed unread. The API and the database confirmed the same result, and the sender observed no read state. The badge is proven in one browser only; Firefox, Safari, and the floating conversation window remain unverified.
- Private Preview same-node messaging has live end-to-end evidence for approved synthetic accounts; this does not qualify share links, cross-node transport, or default Beta support.
- `local` is the provider/policy class; `whooshd` is runtime identity; `local-chat` is the logical route; physical model display metadata is observation only.
- Connectors, activation, browser host/import, Watchdog, hosted sandbox, Atlas, Pi, federation, and autonomous coding-worker work are not default Beta support without current-main qualification.

## Not yet true / do not assume

- Do not call the supported path release-ready or treat migration qualification as deployment.
- Do not infer a fresh integrated-tip Compose run, restart recovery, browser/event/provenance coherence, ordinary chat after restart, or a complete natural import-to-recall path.
- Do not infer exact unavailable-model rejection; the recorded complete Compose proof accepted work with model substitution and no assistant fallback flag.
- Do not treat the delegated worker canary as successful provider execution; the `reasoning_effort` contract still fails before provider execution, and worker egress was observed despite `allow_network=false`.
- Do not treat merged suites, focused database tests, or deployment rehearsal as live runtime qualification.
- Do not treat the serving-revision advance as a re-run of the live read-state qualification: source equivalence is an observation about code, not a fresh execution of the 20 checks, and a healthy Private Preview is not a supported-Compose qualification.
- Do not read Saved Widget promotion and revision storage as widget lifecycle support. Library Widgets collection listing and filtering, invocation, conversational revision and editing, deletion, export and restore, Web Audio, and canvas qualification are all still open, and none of the slice has browser proof.
- Do not read the single-head migration graph as a new qualification of the live Preview database; that database is still at `3a91d7c4e8b2`.
- Share links remain bearer credentials; links without `expires_in_days` do not expire and no revocation endpoint exists.
- Branch-only, origin-only, uncommitted, and local-only work is not shipped `main` reality. Capabilities without current-main qualification are not default Beta support.
- The current-state knowledge-graph node parses but has stale freshness metadata; it is not current release proof.

## Active blockers

- A fresh current-tip supported-Compose qualification is missing, including model rejection, browser/event/provenance coherence, restart recovery, and ordinary chat after restart.
- Frontend frozen-lockfile installation on the supported path remains unrehearsed.
- Cross-browser qualification of the generative-UI containment repair is missing; Chrome 156 is the only reported browser result and Playwright cannot launch on the reported host.
- The UMS/Chronicle lane retains an inherited stale migration-head assertion, and blocked Chronicle HTTP coverage still needs execution against the corrected baseline.
- The explicit-model rejection and delegated worker-to-adapter contract remain unresolved before provider execution claims.
- New-thread projection, natural import-to-recall, scope isolation, export/restore/retention, and complete conversation-lifecycle proof remain open.
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`; the unread badge is proven in Chrome 156 only.
- The Saved Widget lifecycle is incomplete beyond promotion and revision storage: no Library Widgets collection listing, invocation, conversational editing, deletion, or export and restore path, and no browser proof.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Complete the frontend frozen-lockfile installation step of the approved deployment sequence; the image rebuild, migrator, and application restart steps have since been executed against the live Preview.
3. Resolve the explicit-model and delegated-adapter contradictions and execute the blocked Chronicle HTTP cases.
4. Reprove new-thread projection, browser/event coherence, restart recovery, ordinary chat, and scope isolation on one evaluated tip.
5. Close the highest-risk Preview and lifecycle gaps: share-link revocation, import-to-recall, export and restore, cross-browser verification of the now-proven unread badge, and the Saved Widget lifecycle beyond promotion.

## Release definition right now

- [x] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`.
- [x] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists at evaluated mainline tips.
- [ ] A fresh current-tip Compose run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery.
- [ ] An unavailable explicit model fails before provider execution and cannot be silently substituted.
- [ ] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- [ ] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof.
- [ ] Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
