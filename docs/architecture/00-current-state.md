## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-10-30

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

`main` is in local-first Beta hardening with a separately gated Private Preview lane. It carries integrated read-state, migration-lineage, and operator-provenance work. The Private Preview lane has now been **redeployed on its pinned serving worktree** — the live Preview database migrated to Alembic head `3a91d7c4e8b2`, and recipient-local read state passed a 20-of-20 live two-account test evaluated at serving revision `5569f3f34`. The serving revision has since advanced to `c8e72ef86`, which changed no application source. The supported runtime has **not** been requalified beyond that one deployed surface, and the release gate remains `HOLD`.

## What changed recently

- Integrated recipient-local direct-message read state across the Inbox, launcher, and floating conversation surfaces, with monotonic watermarks and serialized concurrent cursor updates.
- Reconciled Saved Widget, automatic-collection consent, and read-cursor migrations into one Alembic head, then unified the Campaign Continuation Authority provenance branch with the Guardian coding-claim branch. The repository's single Alembic head is now `e2a7f3c1b9d4`, a graph-only merge revision that joins `b7e2c4a1d903` and `c8e42a91d307` and changes no schema. Those two heads existed because the campaign provenance revision was rooted at the pre-merge revision `3a91d7c4e8b2` rather than at the merge above it, so `alembic upgrade head` failed with "Multiple head revisions are present" and the focused migration suites could not build a schema.
- The unified head is a **repository graph correction only**. It has not been applied to the live Private Preview database, which remains at `3a91d7c4e8b2`; it is not new migration qualification evidence; it does not requalify the supported Compose runtime; and it is not a release claim. The release gate remains `HOLD`.
- Integrated the Guardian coding-worker ownership and claim-scoped heartbeat schema into `main`: three nullable `agent_runs` columns and three constraints behind a no-op Alembic merge revision. This is persistence only — it changes no worker execution, routing, or credential behaviour, and it is not a release claim.
- Added accepted ADR-105 operator-actor and human-approval provenance boundaries; this is governance evidence, not autonomous execution or release expansion.
- Qualified the committed migration chain on the supported `postgres:15` / PostgreSQL 15.19 path using an empty database and a restored, read-only copy of the Preview database; existing rows were preserved.
- Rehearsed the real image/migrator mechanism and recorded two traps: the backend entrypoint's `alembic` call is a swallowed no-op, and the migrator reads migrations from the baked image rather than the source mount.
- Reconciled local `main` with the stored remote-tracking tip; the Private Preview deployment and live read-state qualification then followed, and the serving revision has since advanced from `5569f3f34` to `c8e72ef86` without changing application source.
- Proved the unread badge in a real browser against the running Private Preview — Inbox and launcher badges render and agree with the API, and opening a conversation clears that reader's badge only — and recorded the account-scoped cleanup that removed the proof accounts without touching another account's durable read cursor.

## Current supported reality

- The named supported install path is local Docker Compose profile `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The Beta Supported envelope covers local inference, ordinary chat, durable threads/messages/tasks, supported document ingestion and retrieval, account ownership, migrations, and operator diagnostics; qualification is a separate gate.
- Mainline has bounded evidence for topology, health, browser chat, durable readback, retrieval provenance, queue/worker lifecycle, locks, cancellation, deadlines, and authorization; bounded evidence is not complete runtime qualification.
- The migration chain is qualified on the supported PostgreSQL version in disposable clean and restored-copy runs, and has since been applied to the **live** Private Preview database, which advanced `f0d7c4b2a198` → `3a91d7c4e8b2` with every pre-existing row preserved.
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
- Do not treat Saved Widget storage and ADR-102 acceptance as lifecycle support; promotion, listing, invocation, editing, deletion, export/restore, Library Widgets filtering, Web Audio, and canvas qualification remain open.
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
- Private Preview still lacks share-link expiry/revocation, cross-node messaging proof, and consent-enforcement coverage at a profile that mounts `iddb`; the unread badge is proven in Chrome 156 only, and Saved Widget lifecycle and complete browser qualification also remain open.

## This week’s priorities

1. Freeze the evaluated local `main` SHA and run the complete supported-Compose proof bundle.
2. Complete the frontend frozen-lockfile installation step of the approved deployment sequence; the image rebuild, migrator, and application restart steps have since been executed against the live Preview.
3. Resolve the explicit-model/delegated-adapter contradictions and execute the blocked Chronicle HTTP cases.
4. Reprove new-thread projection, browser/event coherence, restart recovery, ordinary chat, and scope isolation on one evaluated tip.
5. Close the highest-risk Preview and lifecycle gaps: share-link revocation, import-to-recall, export/restore, cross-browser verification of the now-proven unread badge, and Saved Widget operations.

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
