# Guardian Codex Runner Bridge Proof Chain Index

> Classification: canonical index
> Status: operator-facing proof-chain navigation surface
> Scope: index only — no new bridge authority

Last updated: 2026-07-09

Source anchors:
- All docs in docs/architecture/guardian-codex-runner-*.md
- docker-compose.codex-runner-bridge.yml
- guardian/codex_runner_bridge/
- docs/architecture/00-current-state.md
- docs/architecture/README.md

## 1. Purpose

This document is the single canonical proof-chain index for the Guardian Codex Runner command-bus bridge.

The bridge proof sequence now spans thirteen artifacts. This index makes the sequence easy for a future operator or agent to inspect without accidentally reclassifying preflight proof as execution authority, validation evidence as plan execution permission, or receipt availability as Codexify ingestion.

This index is a navigation and interpretation surface — it does not add any new bridge authority.

## 2. Status

Status: canonical index only.

This index does not:

- add a new bridge capability
- change runtime code
- change compose files
- widen release claims
- add UI support
- set production policy

This index does not add UI support. No UI panel is implied by this index.

## 3. Scope

This index covers all thirteen Guardian Codex Runner bridge proof-chain artifacts from the preflight bridge contract through the local-auth override contract.

It does not implement or approve any new bridge behavior.

## 4. Current Truth

What is true now:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- The Guardian Codex Runner bridge is internal and preflight-only.
- Both bridge preflight commands are live-proven through the command bus.
- All authority locks remain false across every proof.
- This index catalogs the proof chain without adding authority.

## 5. Proof Chain Summary

The bridge proof chain progressed through four phases:

1. **Contract & controlled proof**: Architecture contract defined the bridge boundary; controlled command-bus proof validated lifecycle wiring.
2. **Container visibility**: Opt-in read-only Docker mount made Codex Runner visible inside the backend container.
3. **Validate proof chain**: Multiple live validate attempts, each blocked or failed by a different seam, culminating in a PASS using module invocation.
4. **Orchestration proof chain**: Receipt prerequisite contract, receipt availability proofs, selected receipt, and the live orchestration preflight PASS.

The entire bridge is preflight-only. No execution, no Pi Loop, no source mutation, no ingestion occurred at any stage.

## 6. Canonical Artifact Table

| # | Artifact | Class | Status | What It Established | What It Did Not Establish |
|---|---|---|---|---|---|
| 1 | [`guardian-codex-runner-preflight-bridge-contract.md`](./guardian-codex-runner-preflight-bridge-contract.md) | Architecture contract | Governing | Bridge boundary: backend-owned, typed, JSON-only, preflight-only | UI, write flags, Pi Loop, execution, ingestion |
| 2 | [`guardian-codex-runner-command-bus-proof.md`](./guardian-codex-runner-command-bus-proof.md) | Controlled proof | PASS | Command-bus lifecycle wiring, boundary preservation | Live Codex Runner execution, UI, write flags |
| 3 | [`guardian-codex-runner-container-visibility-contract.md`](./guardian-codex-runner-container-visibility-contract.md) | Architecture contract | Opt-in seam | Read-only Docker mount at expected bridge path | Live validation, live orchestration, UI |
| 4 | [`guardian-codex-runner-command-bus-live-validate-proof.md`](./guardian-codex-runner-command-bus-live-validate-proof.md) | Live proof | BLOCKED | Route-availability block (backend unreachable) | Live validation, orchestration, UI |
| 5 | [`guardian-codex-runner-command-bus-live-validate-retry-proof.md`](./guardian-codex-runner-command-bus-live-validate-retry-proof.md) | Live proof | FAIL | Backend reachable, command-bus available; path invisibility block | Live validation, orchestration, UI |
| 6 | [`guardian-codex-runner-command-bus-live-validate-mounted-proof.md`](./guardian-codex-runner-command-bus-live-validate-mounted-proof.md) | Live proof | FAIL | Mount works (path visible); codexrun binary not on PATH | Live validation, orchestration, UI |
| 7 | Executable availability seam (`guardian/codex_runner_bridge/adapter.py`) | Adapter enhancement | Implemented | Binary/module invocation mode resolver; python -m codex_runner support | Live validation pass, orchestration, UI |
| 8 | [`guardian-codex-runner-command-bus-live-validate-module-proof.md`](./guardian-codex-runner-command-bus-live-validate-module-proof.md) | Live proof | PASS | First live validate PASS through module invocation | Orchestration, UI, write flags, ingestion |
| 9 | [`guardian-codex-runner-orchestration-receipt-prerequisite-contract.md`](./guardian-codex-runner-orchestration-receipt-prerequisite-contract.md) | Prerequisite contract | Governing | Receipt rules for future orchestration proof | Orchestration proof, receipt creation, ingestion |
| 10 | [`guardian-codex-runner-validation-receipt-availability-proof.md`](./guardian-codex-runner-validation-receipt-availability-proof.md) | Operator evidence | BLOCKED | No operator-selected receipt source configured | Orchestration, receipt trust, ingestion |
| 11 | [`guardian-codex-runner-selected-validation-receipt-proof.md`](./guardian-codex-runner-selected-validation-receipt-proof.md) | Operator evidence | SELECTED_AVAILABLE | Operator-selected receipt path verified visible and readable | Orchestration, receipt trust, ingestion |
| 12 | [`guardian-codex-runner-command-bus-live-orchestration-proof.md`](./guardian-codex-runner-command-bus-live-orchestration-proof.md) | Live proof | PASS | 12/12 preconditions met; 8/8 hashes verified; dry-run only | Pi Loop, plan execution, source mutation, ingestion |
| 13 | [`guardian-codex-runner-local-auth-override-contract.md`](./guardian-codex-runner-local-auth-override-contract.md) | Governance contract | Implemented | Local auth override for bridge proof profile; not production policy | Production auth, UI, release expansion |

## 7. What Is Proven

The following bridge capabilities are live-proven through the command bus:

- `internal::guardian.codex_runner.validate_plan_pack` — validates a Plan Pack structurally through the bridge adapter and Codex Runner.
- `internal::guardian.codex_runner.orchestrate_dry_run_preflight` — performs dry-run orchestration preflight through the bridge adapter, using an operator-selected validation receipt.

Both commands are proven through module invocation (`python -m codex_runner`) against the mounted Codex Runner source checkout. Both pass with all authority locks false and the exact four-line bridge boundary label returned.

The orchestration proof was dry-run preflight only — no execution occurred (`execution_performed: false`). No receipt was written. No orchestration log was written. No orchestration receipt was written.

## 8. What Is Not Proven

The following are NOT proven by any bridge proof-chain artifact:

- Pi Loop invocation
- plan execution
- source mutation
- patch application
- provider execution
- Codexify ingestion
- write flags
- receipt writing
- orchestration log writing
- orchestration receipt writing
- UI support
- remote deployment
- production auth policy
- Execution Ledger writes
- WorkOrder mutation

## 9. Authority Boundary

Across all thirteen artifacts, these authority locks remain `false`:

```yaml
authority:
  guardian_operational: false
  plan_execution_allowed: false
  pi_loop_invocation_allowed: false
  codexify_ingestion_allowed: false
  durable_mutation_allowed: false
  provider_execution_allowed: false
  patch_application_allowed: false
  dispatch_allowed: false
  merge_allowed: false
```

No proof artifact widened authority. No proof artifact enabled write flags. No proof artifact authorized execution. The bridge remains preflight-only.

## 10. Runtime Config Seams

Three opt-in runtime seams support the bridge proof chain:

| Seam | File | Purpose |
|---|---|---|
| Read-only Codex Runner mount | `docker-compose.codex-runner-bridge.yml` | Makes host Codex Runner visible inside backend container |
| Module invocation | `docker-compose.codex-runner-bridge.yml` | Enables `python -m codex_runner` without global binary |
| Local auth override | `docker-compose.codex-runner-bridge.yml` | Forces local API-key auth when `.env` has remote defaults |

All three seams are opt-in (never applied by default). None modify `docker-compose.yml`. None are production auth policy. None are release support expansion.

## 11. Receipt Interpretation

The validation receipt used in the orchestration proof is evidence only:

- It declares itself as `evidence_not_authority: true`.
- All nine authority locks in the receipt are `false`.
- It was never ingested into Codexify.
- It was never trusted as approval.
- It was used only as a required argument to `orchestrate_dry_run_preflight`.
- Its hash matches prove file continuity, not correctness.

Receipt availability is not execution authority. Receipt existence is not dispatch authority. Receipt hash match is not plan correctness.

## 12. Operator Reading Order

For operators and agents inspecting the bridge proof chain, the recommended reading order is:

1. [`guardian-codex-runner-preflight-bridge-contract.md`](./guardian-codex-runner-preflight-bridge-contract.md) — understand the bridge boundary
2. [`guardian-codex-runner-container-visibility-contract.md`](./guardian-codex-runner-container-visibility-contract.md) — understand the Docker mount seam
3. [`guardian-codex-runner-command-bus-proof.md`](./guardian-codex-runner-command-bus-proof.md) — understand the controlled proof baseline
4. [`guardian-codex-runner-command-bus-live-validate-module-proof.md`](./guardian-codex-runner-command-bus-live-validate-module-proof.md) — see the first live validate PASS
5. [`guardian-codex-runner-orchestration-receipt-prerequisite-contract.md`](./guardian-codex-runner-orchestration-receipt-prerequisite-contract.md) — understand receipt rules
6. [`guardian-codex-runner-selected-validation-receipt-proof.md`](./guardian-codex-runner-selected-validation-receipt-proof.md) — see which receipt was selected
7. [`guardian-codex-runner-command-bus-live-orchestration-proof.md`](./guardian-codex-runner-command-bus-live-orchestration-proof.md) — see the live orchestration PASS
8. [`guardian-codex-runner-local-auth-override-contract.md`](./guardian-codex-runner-local-auth-override-contract.md) — understand the local auth seam

The blocked and failed validate proofs (artifacts 4–6) are supplementary evidence showing which seams blocked progression. They are not required reading for understanding the bridge's current capabilities.

## 13. Future Allowed Slices

Future slices beyond this proof chain remain deferred. Any post-orchestration work would require separate contracts. The following are explicitly deferred and not authorized by any artifact in this chain:

- Codexify ingestion of bridge evidence
- Execution Ledger writes
- WorkOrder mutation
- Plan execution (requires Chris-approved Pi Loop contract)
- Source mutation
- Patch application
- UI integration
- Provider execution through the bridge

## 14. Forbidden Interpretations

Do not interpret this index as meaning:

- the bridge is a general execution surface
- orchestration preflight pass = plan execution authority
- codexrun validate pass = Pi Loop authorization
- receipt availability = receipt trust
- receipt hash match = plan correctness
- command-bus run/event records = Codexify ingestion
- local auth override = production auth policy
- this index = UI support
- this index = release support expansion
- this index = new bridge capability
- live prove = shipped UI
- preflight pass = execution authorization

## 15. Bottom Line

The Guardian Codex Runner command-bus bridge proof chain spans thirteen artifacts: one architecture contract, three runtime seam contracts, one controlled proof, six live proofs (three blocked/failed, three passed), and two governance contracts.

Five artifacts reached a positive proof status: preflight contract (governing), controlled proof (PASS), module validate proof (PASS), selected receipt proof (SELECTED_AVAILABLE), and live orchestration proof (PASS).

Both bridge preflight commands are live-proven through the command bus. All authority locks remain false. No execution occurred. No Pi Loop was invoked. No source was mutated. No evidence was ingested.

The bridge is preflight-only. The index is navigation-only. Neither widens release claims.

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 16. Relationship to Guardian Evidence Reduction

This bridge proof-chain index is an evidence source candidate for future [`GuardianEvidencePacket`](./guardian-evidence-packet-reducer-contract.md) production. The index itself is not a GuardianEvidencePacket. The index does not authorize ingestion, execution, UI, Pi Loop invocation, or source mutation.

A future reducer implementation producing packets from bridge proof chain evidence must preserve the bridge boundary label and all false authority locks in every produced packet. See the evidence packet reducer contract for the schema family and reduction depth policies.
