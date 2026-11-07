# Beta Changelog

Evidence-led beta readiness changes only.

## 2026-11-06

### Evidence
- Merge pull request #1010 from Resonant-Jones/docs/preview-schema-advance-criterion-20261106
- docs(current-state): close the Preview schema-advance release criterion
- Merge pull request #1009 from Resonant-Jones/docs/preview-reconciler-recovery-20261106
- docs(current-state): record the Private Preview reconciler recovery
- Merge pull request #1008 from Resonant-Jones/docs/preview-schema-advance-receipt-20261106
- docs(current-state): record the live Preview schema advance and read-state requalification
- Merge pull request #1007 from Resonant-Jones/feat/auto-20261105-c8c1dc20
- docs(current-state): let the registry carry the changed-path count
- docs(current-state): correct the eight claims that landing #1007 falsifies
- Merge mainline into feat/auto-20261105-c8c1dc20 and reconcile the release truth
- docs: refresh weekly current-state override
- docs(qualification): qualify the stock Compose startup with a PASS verdict
- Merge remote-tracking branch 'origin/main' into feat/auto-20261105-c8c1dc20
- fix(rag): derive the embedding dimension from the configured model
- docs: add 2026-05-02 daily dev log

### Blockers
- Each tracked qualification surface carries its own dated run receipt inside the tip's lineage and is not `stale` against it; a receipt for one surface does not qualify another, and a proof artifact the registry cannot read does not qualify it either. **Partially satisfied at `844b35599ed6`:** `supported-compose-stock` now carries its own dated receipt at the tip's lineage with verdict `PASS` and projects `freshness: current`. `supported-compose` (the source-matched path) is still `stale` against this tip, and `onboarding-and-people` still has no receipt at all.
- Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof. **Partially satisfied at `456da46b8`**: the contract no longer fails before provider execution — the binding's authored effort now resolves against the lane's compatible set before the worker forwards it, an unauthorized or lane-incompatible effort still fails closed, and a caller-supplied task field still cannot set it. The **live proof** is still missing: no delegated execution was exercised on a supported path in this window.
- Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline. **Partially satisfied at `dece01821`**: the Preview lane now carries current live evidence — the schema advance, the twenty recipient-local read-state checks re-run against the running service, and a restored reconciler cycle — but the **release metadata still points at a pre-evaluated revision**: the newest beta release sentinel artifact records a May head, so the metadata half of this criterion is not yet met.

### Warnings
- Core Loop Integrity: Chat route exposes async completion enqueue path
- Core Loop Integrity: Architecture docs still flag chat-loop dependency coupling
- Primitive Stability: Repo-local docs warn about contract drift in tool primitives
- Extension Boundary: Architecture docs describe command bus, cron, and coding-agent seams
- Extension Boundary: Legacy /tools compatibility route status
- Observability: Observability docs leave some logging guarantees unverified
- Durability & Recovery: Roadmap docs warn that sync delivery is not yet durable
- Durability & Recovery: Risk register warns about Redis persistence or replay gaps
- Alternate Surface Readiness: Repo-local docs still describe shell-level coupling
- Federation Readiness: Roadmap docs warn that sync subscriptions are process-local
- Federation Readiness: Risk register warns that federation remains security- and config-sensitive
- Governance Readiness: Ownership authority is still informal in the scanned docs

## 2026-06-12

### Merged PRs
- #423 - [guardian-work-brief](https://github.com/Resonant-Jones/Codexify/pull/423)
- #422 - [add-campaign-intent-packet-seam](https://github.com/Resonant-Jones/Codexify/pull/422)
- #421 - [enable-whooshd](https://github.com/Resonant-Jones/Codexify/pull/421)
- #420 - [add-campaign-intent-packet-seam](https://github.com/Resonant-Jones/Codexify/pull/420)
- #419 - [add-gemma-profile-registry](https://github.com/Resonant-Jones/Codexify/pull/419)
- #418 - [launch-codexify](https://github.com/Resonant-Jones/Codexify/pull/418)
- #417 - [add-campaign-intent-packet-seam](https://github.com/Resonant-Jones/Codexify/pull/417)
- #416 - [github-mention-define-docs-to-issue-compiler-protocol](https://github.com/Resonant-Jones/Codexify/pull/416)
- #415 - [github-mention-define-codexify-issue-template-contract](https://github.com/Resonant-Jones/Codexify/pull/415)
- #414 - [github-mention-classify-local-worktree-drift-before-new-imp](https://github.com/Resonant-Jones/Codexify/pull/414)
- #413 - [add-campaign-intent-packet-seam](https://github.com/Resonant-Jones/Codexify/pull/413)

## 2026-05-15

### Evidence
- No new commit subjects discovered for this sentinel window.

### Blockers
- Coding results return through Guardian into the source thread without duplicate delivery.
- Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- No internal-only or quarantined surface is part of the release claim.

### Warnings
- Core Loop Integrity: Architecture docs still flag chat-loop dependency coupling
- Primitive Stability: Repo-local docs warn about contract drift in tool primitives
- Extension Boundary: Architecture docs describe command bus, cron, and coding-agent seams
- Extension Boundary: Legacy /tools compatibility route status
- Observability: Observability docs leave some logging guarantees unverified
- Durability & Recovery: Roadmap docs warn that sync delivery is not yet durable
- Durability & Recovery: Risk register warns about Redis persistence or replay gaps
- Alternate Surface Readiness: Repo-local docs still describe shell-level coupling
- Federation Readiness: Roadmap docs warn that sync subscriptions are process-local
- Federation Readiness: Risk register warns that federation remains security- and config-sensitive
- Governance Readiness: Ownership authority is still informal in the scanned docs

## 2026-05-15

### Evidence
- No new commit subjects discovered for this sentinel window.

### Blockers
- Coding results return through Guardian into the source thread without duplicate delivery.
- Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- No internal-only or quarantined surface is part of the release claim.

### Warnings
- Core Loop Integrity: Architecture docs still flag chat-loop dependency coupling
- Primitive Stability: Repo-local docs warn about contract drift in tool primitives
- Extension Boundary: Architecture docs describe command bus, cron, and coding-agent seams
- Extension Boundary: Legacy /tools compatibility route status
- Observability: Observability docs leave some logging guarantees unverified
- Durability & Recovery: Roadmap docs warn that sync delivery is not yet durable
- Durability & Recovery: Risk register warns about Redis persistence or replay gaps
- Alternate Surface Readiness: Repo-local docs still describe shell-level coupling
- Federation Readiness: Roadmap docs warn that sync subscriptions are process-local
- Federation Readiness: Risk register warns that federation remains security- and config-sensitive
- Governance Readiness: Ownership authority is still informal in the scanned docs

## 2026-05-15

### Evidence
- No new commit subjects discovered for this sentinel window.

### Blockers
- None.

### Warnings
- Core Loop Integrity: Architecture docs still flag chat-loop dependency coupling
- Primitive Stability: Repo-local docs warn about contract drift in tool primitives
- Extension Boundary: Architecture docs describe command bus, cron, and coding-agent seams
- Extension Boundary: Legacy /tools compatibility route status
- Observability: Observability docs leave some logging guarantees unverified
- Durability & Recovery: Roadmap docs warn that sync delivery is not yet durable
- Durability & Recovery: Risk register warns about Redis persistence or replay gaps
- Alternate Surface Readiness: Repo-local docs still describe shell-level coupling
- Federation Readiness: Roadmap docs warn that sync subscriptions are process-local
- Federation Readiness: Risk register warns that federation remains security- and config-sensitive
- Governance Readiness: Ownership authority is still informal in the scanned docs
