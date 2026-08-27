## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-08-27

## Interpretation rule

This file is authoritative for:

- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Checked-out `main` is in local-first Beta hardening. It contains merged control-plane work and bounded proof artifacts, but no fresh supported-Compose closure at the audited tip. Release readiness remains on hold pending one coherent, current-main runtime proof bundle.

## What changed recently

- Requalified one bounded Guardian/Pi provider-backed invocation through the canonical rail; the CE-L0 gate passed, but the surface remains Internal / proof-only.
- Merged the Campaign live Executor record contract with schema and validation coverage; this is code/test evidence, not live Campaign Engine or release proof.
- Recorded a Google Drive OAuth attempt with real consent and callback reachability; Google's authorization-code exchange was rejected, so the connection did not reach `connected`.
- Restored tester backend health observation, but strict backend lifecycle qualification remained blocked by a separate restart/other failure.
- Retained the previously classified Chroma compatibility failure and Docker image-retention evidence gap; neither has a current supported-path closure.

## Current supported reality

- The supported install path is local Docker Compose using `v1-local-core-web-mcp` with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- The intended Beta Supported boundary remains local inference, ordinary chat, durable threads/messages/tasks, upload → embed → readback, workspace-local retrieval, identity/ownership, migrations, and operator diagnostics; this is support doctrine, not current-tip qualification.
- Postgres remains canonical application authority; Chroma is derived retrieval state and cannot be treated as durable source-of-truth.
- Settings read surfaces, the read-only Connections catalog, and bounded account-export imports retain their existing contracts; Google Drive OAuth, search, and Docs readback remain unqualified.
- Watchdog, Pi diagnostics, Campaign proof tooling, and tester-stack receipts are Internal or proof-only surfaces. Their presence does not prove supported release behavior.

## Not yet true / do not assume

- Do not assume current-tip Compose startup, health, model inventory, terminal chat, persistence/readback, retrieval, queue/worker, locks, or recovery are green together.
- Do not treat the CE-L0 PASS or Campaign Executor contract as Campaign Engine live execution or Beta support.
- Do not treat Google consent or callback reachability as a connected Google Drive credential; no successful token exchange, persisted credential, search, or Docs readback is proven.
- Do not assume Watchdog has model execution, review publication, GitHub mutation, fallback, or automatic retry.
- Do not assume the lost qualified image's deletion cause or retention behavior is known, or that feature branches, local work, or origin-only commits are shipped reality.

## Active blockers

- Fresh supported-Compose closure has not been rerun at the audited current tip after configuration alignment.
- One supported-profile proof bundle is still missing for health, chat, durable readback, retrieval, queue/worker execution, locks, terminal events, migrations, and recovery.
- Fresh-state Chroma startup/retrieval qualification remains blocked after the classified compatibility failure; no authorized repair or restore is proven.
- Google Drive OAuth is blocked at Google's authorization-code exchange; the connection remains `error` rather than `connected`.
- Disposable Docker archive-retention qualification remains blocked by unavailable `desktop-linux` authority, and the deletion actor/mechanism remains unproven.
- Checked-out `main` is 2 commits ahead and 16 behind `origin/main`; this audit is bounded to HEAD `4e1e1a7ca` and must not mix the two histories as one release baseline.

## This week’s priorities

1. Establish one canonical mainline baseline before the next release decision.
2. Rerun supported-Compose closure from that exact baseline.
3. Capture health, chat, persistence/readback, retrieval, queue/worker, locks, events, migration, and recovery proof together.
4. Requalify Chroma and Docker retention only through explicitly authorized fresh proof paths.
5. Repair the named Google OAuth exchange and bind any Watchdog provider/model policy before rerunning qualification.

## Release definition right now

- [x] Supported local Compose path, local-only defaults, and Beta boundary are defined on `main`.
- [x] Internal, bounded/conditional, qualification-pending, and Out-of-Beta surfaces remain separated from Beta Supported.
- [ ] One coherent current-main run proves healthy startup, health, model inventory, terminal chat, persistence/readback, and retrieval.
- [ ] Queue, worker, lock, migration, configuration, event, and recovery behavior is green on the supported install path.
- [ ] Qualification-pending lanes have named current-main proof receipts; until then, they remain quarantined.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
