# Beta Release Sentinel — 2026-11-06

## Repo status
- Branch: `main`
- Head: `e66beb5021188ddaa3a5d6afad86094a995f5325`
- Worktree clean: `True`
- Worktree appears clean.

## Current beta promise
- Local-first beta hardening.
- Supported path: local Docker Compose.
- Supported beta posture: local-only.
- Primary operator truth surfaces: `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`.

## Release gates
- [checked] Supported install path, Beta boundary, provider identity, and local-only policy are defined on `main`. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] Bounded chat, cancellation, durable readback, retrieval, authorization, and migration-chain evidence exists at evaluated mainline tips. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] Release-readiness claims are machine-checkable: the qualification registry is generated and drift-gated, and the knowledge-graph corpus is bound to a revision. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] A supported-Compose qualification exists inside the tip's lineage, on the source-matched launcher startup, covering explicit-model rejection with provider-side non-execution evidence, ordinary chat with durable state, retrieval with attribution, browser/event coherence, and restart recovery. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] A migration is judged by the database's own `alembic_version`, not by a container's exit code, and the stock migrator refuses to run against a migration source that does not describe this checkout. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] The **stock** supported Compose path applies the source head's migrations — proven on the stock path by direct `alembic_version` readback, including refusal of a stale image, a same-head image with different content, and a same-head source with a different migration environment. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] A stock-path qualification run passes health, inventory, chat, durable readback, retrieval, browser projection, event delivery, and restart recovery, under a `supported-compose-stock` rubric with its own run receipt and registry entry. **Closed at `844b35599ed6`** by the stock-path run (`docs/qualification/runs/2026-11-05-supported-compose-stock-844b35599ed6.md`, verdict `PASS`): the source-head migration contract passed with the live `alembic_version` read directly out of PostgreSQL equal to the checkout's single head `a7d4c9e2f1b3` with exactly one row; document ingestion and retrieval passed after the collection-dimension defect was repaired; browser projection was exercised in a real browser, with the terminal state converging in the UI and a reload preserving it. The earlier run at `456da46b8` remains in the repository as a `FAIL` receipt, so the defect and its repair stay on the record. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Each tracked qualification surface carries its own dated run receipt inside the tip's lineage and is not `stale` against it; a receipt for one surface does not qualify another, and a proof artifact the registry cannot read does not qualify it either. **Partially satisfied at `844b35599ed6`:** `supported-compose-stock` now carries its own dated receipt at the tip's lineage with verdict `PASS` and projects `freshness: current`. `supported-compose` (the source-matched path) is still `stale` against this tip, and `onboarding-and-people` still has no receipt at all. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] The live Preview database is advanced past `3a91d7c4e8b2` and the five unapplied schema revisions land. **Closed at `dece01821`**: the live database moved `3a91d7c4e8b2` → `a7d4c9e2f1b3`, applying five schema-carrying revisions (`b7e2c4a1d903`, `d86f2a4b1c90`, `e42c7d0b9135`, `d91e4fa6702b`, `a7d4c9e2f1b3`) and two graph-only mergepoints (`a3115f64dda8`, `c8e42a91d307`); every pre-existing row is preserved (138 → 140 public tables, 113547 chat messages and 5144 threads unchanged) and the live `alembic_version` was read directly out of PostgreSQL as `a7d4c9e2f1b3` with exactly one row. The recovery path was proven rather than assumed — the pre-migration `pg_dump` was restored into a disposable database and compared row-for-row with the live database it was dumped from — and the image's baked migration source was proven byte-identical to the served checkout by a SHA-256 manifest computed inside the image. Receipt: `docs/architecture/proofs/runtime/2026-11-06-private-preview-schema-advance-and-read-state-proof.md`. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] A document left in `embedding_status = 'processing'` by a worker kill is recovered or terminally failed. **Closed at `456da46b8`**: a bounded age-based sweeper inside the existing `worker-document-embed` terminally fails abandoned documents with a recorded reason, using a compare-and-set on the claim timestamp so a live worker's document is never stolen. Re-embedding is not provably idempotent, so the outcome is terminal failure rather than a silent double-index. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] Per-message origin classification excludes imported, unknown, and conflicting messages before excerpts reach the model. **Closed at `456da46b8`**: `guardian/core/message_origin_classification.py` classifies each candidate message at read time, the recall reader excludes imported/unknown/conflicting messages before excerpts reach the model, and the coverage receipt carries content-free per-message exclusion counts separate from thread-level counts. No schema change, no migration, no backfill; ADR-016's write-side custody boundary is unchanged. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof. **Partially satisfied at `456da46b8`**: the contract no longer fails before provider execution — the binding's authored effort now resolves against the lane's compatible set before the worker forwards it, an unauthorized or lane-incompatible effort still fails closed, and a caller-supplied task field still cannot set it. The **live proof** is still missing: no delegated execution was exercised on a supported path in this window. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline. **Partially satisfied at `dece01821`**: the Preview lane now carries current live evidence — the schema advance, the twenty recipient-local read-state checks re-run against the running service, and a restored reconciler cycle — but the **release metadata still points at a pre-evaluated revision**: the newest beta release sentinel artifact records a May head, so the metadata half of this criterion is not yet met. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Platform readiness audit execution — scripts/audit_platform_readiness.py (Audit script executed and returned JSON summary.)

## Evidence summary
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

## Changelog draft
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

## Blockers
- Each tracked qualification surface carries its own dated run receipt inside the tip's lineage and is not `stale` against it; a receipt for one surface does not qualify another, and a proof artifact the registry cannot read does not qualify it either. **Partially satisfied at `844b35599ed6`:** `supported-compose-stock` now carries its own dated receipt at the tip's lineage with verdict `PASS` and projects `freshness: current`. `supported-compose` (the source-matched path) is still `stale` against this tip, and `onboarding-and-people` still has no receipt at all.
- Queue/worker, deadline, graceful-stop, lock, migration deployment, browser, import-recall, and scope-isolation gates are green on one evaluated tip.
- Delegated execution has a passing worker-to-adapter `reasoning_effort` contract and live proof. **Partially satisfied at `456da46b8`**: the contract no longer fails before provider execution — the binding's authored effort now resolves against the lane's compatible set before the worker forwards it, an unauthorized or lane-incompatible effort still fails closed, and a caller-supplied task field still cannot set it. The **live proof** is still missing: no delegated execution was exercised on a supported path in this window.
- Claimed Preview or public-ingress paths have current live evidence, and release metadata points to the evaluated mainline. **Partially satisfied at `dece01821`**: the Preview lane now carries current live evidence — the schema advance, the twenty recipient-local read-state checks re-run against the running service, and a restored reconciler cycle — but the **release metadata still points at a pre-evaluated revision**: the newest beta release sentinel artifact records a May head, so the metadata half of this criterion is not yet met.

## Warnings
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

## Not promised / excluded surfaces
- cloud-provider beta support
- public multi-user deployment
- federation durability
- graph-write release expansion
- unsupported provider paths

## Recommended next actions
- Re-run sentinel after runtime changes on current tip.
- Keep supported-profile contract and health/catalog surfaces aligned.
- Treat this artifact as evidence, not release approval.

## Machine-readable JSON artifact path
- `docs/audits/generated/2026-11-06-beta-sentinel.json`
