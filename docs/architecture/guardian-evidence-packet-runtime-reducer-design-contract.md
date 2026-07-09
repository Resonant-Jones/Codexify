# Guardian Evidence Packet Runtime Reducer Design Contract

> Classification: architecture contract
> Status: docs-only future reducer design — no runtime implementation
> Scope: bounded reduction of evidence into GuardianEvidencePacket-shaped output

## 1. Purpose

This contract defines the future boundary for a Guardian Evidence Packet runtime reducer. It specifies permitted inputs, output shape, reduction depth, bounded self-checks, authority locks, provenance, validation handoff, and human review handoff.

This is a design contract only. It does not implement runtime reducer behavior.

## 2. Status

The reducer described here is future design work. No runtime reducer, packet generator, reducer service, route, worker, UI, persistence, or execution path is implemented by this contract.

## 3. Scope

The future reducer may classify bounded evidence, preserve references, extract and qualify claims, record uncertainty, preserve forbidden interpretations, set false authority locks, select bounded next gates, produce a packet, and return a static validation result for review.

It may not broaden authority or turn evidence into durable Codexify truth.

## 4. Why This Exists

The existing schema, authoring guide, static validator contract, bridge fixture, and local validation-toolchain fixture establish a packet shape. A future implementation needs a separate design boundary so it does not overfit to one evidence source or silently turn summaries into execution authority.

## 5. Current Truth

What is true now:

- GuardianEvidencePacket is a schema, authoring, fixture, and local static-validation pattern.
- Two static fixtures exist: the bridge proof-chain fixture and the local validator toolchain fixture.
- The authoring template remains outside the fixture directory.
- Static validation checks shape and guardrails only; it does not prove claim truth.
- No runtime reducer or packet generator exists.

This contract does not widen the supported local-first beta release path.

Pure backend contract constants now exist at `guardian/evidence_packets/contracts.py`. They define schema versions, required fields, allowed values, false authority locks, and pure shape helpers. They are not a reducer implementation, packet generator, or runtime wiring; they do not call command bus, Codex Runner, live validation, orchestration, Pi Loop, provider execution, or source mutation. Future reducer implementation should import these constants rather than re-invent packet literals.

Future reducer implementation should use `guardian/evidence_packets/contracts.py` as the source for packet constants. Local validators already consume that package, keeping future reducer and current local validation aligned. Passing validation remains shape/guardrail evidence only, not truth or authority.

Pure reducer interface contracts now exist at `guardian/evidence_packets/reducer_contracts.py`. They define input classes, output classes, reducer lifecycle constants, frozen dataclasses, and pure helper functions. They do not implement reduction, generate packets, validate packets, or call command bus, Codex Runner, live validation, orchestration, Pi Loop, provider execution, or source mutation. Future reducer implementation should use these interfaces instead of inventing a parallel reducer shape.

A pure reducer dry-run skeleton now exists at `guardian/evidence_packets/reducer.py`. It accepts `ReducerInputBundle` and returns `ReducerResult`, stops after receive/classify/stop diagnostics, and returns `packet=None` and `validation_result=None`. It does not reduce evidence, generate packets, validate packets, call command bus, Codex Runner, live validation, orchestration, Pi Loop, provider execution, or source mutation. It is not runtime wiring.

A local reducer dry-run CLI now exists at `scripts/guardian/reducer_dry_run.py`. It wraps the pure dry-run skeleton and returns diagnostics JSON only, with `packet=null` and `validation_result=null`. It does not reduce evidence, generate packets, validate packets, read evidence source files, write files, call command bus, Codex Runner, live validation, orchestration, Pi Loop, provider execution, or source mutation. It is not runtime wiring.

```bash
python3 scripts/guardian/reducer_dry_run.py --json
python3 scripts/guardian/reducer_dry_run.py --json --review-depth high --input readme:static_docs:docs/architecture/README.md
```

## 6. Reducer Design Boundary

A future reducer is a pure, bounded evidence-reduction boundary. It receives an explicitly bounded input set and produces only a `GuardianEvidencePacket` plus an associated static validation result and diagnostic summary where separately requested.

The future reducer must preserve evidence refs, uncertainty, contradictions, forbidden interpretations, provenance, and limits. It must default every authority lock to `false` and must never promote evidence to authority.

## 7. Non-Goals

This contract does not:

- implement runtime reducer behavior
- implement packet generation
- add API routes
- add frontend UI
- add ingestion
- write receipts
- call command bus
- call Codex Runner
- invoke live validation
- invoke live orchestration
- invoke Pi Loop
- execute plans
- mutate source
- execute providers
- write Execution Ledger entries
- mutate WorkOrders
- add CI/default release gating
- widen release support

It also adds no database model, migration, dev-build test button, bridge adapter behavior, command-bus behavior, or daemon integration.

In plain terms: it does not implement packet generation, does not add API routes, does not add frontend UI, does not add ingestion, does not write receipts, does not call command bus, does not call Codex Runner, does not invoke live validation or live orchestration, does not invoke Pi Loop, does not execute plans or providers, does not mutate source, does not write Execution Ledger entries, does not mutate WorkOrders, does not add CI/default release gating, and does not widen release support.

It does not invoke live orchestration.
It does not execute providers.

## 8. Input Classes

The future reducer may accept these bounded input classes:

| Input class | May contain | Must not contain | Classification | Direct trust | Representation |
|---|---|---|---|---|---|
| `static_docs` | Architecture contracts, proof docs, runbooks, and bounded notes | Hidden authority or unreferenced claims | evidence | No | One ref per source document in `raw_evidence_refs` |
| `static_fixtures` | JSON packet examples and fixture metadata | Runtime state or implied approval | evidence | No | Relative fixture path and fixture status |
| `validation_result` | Static validator result, issues, warnings, and checked packet ref | Truth approval or execution permission | diagnostic | No | Validation-result ref with result and issue summary |
| `command_run_snapshot` | Bounded command-bus run metadata supplied as evidence | A command request to execute or dispatch | evidence/control-plane record | No | Snapshot ref with run identity and trust posture |
| `command_run_event_snapshot` | Bounded event records associated with a run | A live event subscription or command | evidence/control-plane record | No | Event-snapshot ref linked to its run ref |
| `receipt_metadata` | Receipt identity, path, timestamp, and status metadata | Receipt writing, receipt trust, or execution authority | evidence metadata | No | Metadata ref; never a receipt write request |
| `proof_index` | An index of source artifacts and relationships | A replacement for the source artifacts | context/evidence navigation | No | Index ref plus individual source refs where claims depend on them |
| `test_result_summary` | Concise test command, scope, and result | Raw logs, secrets, or a release verdict | diagnostic | No | Test-summary ref with bounded result text |
| `operator_supplied_context` | Explicit scope, time boundary, and review intent | Ambient authority or an instruction to execute | context | No | Context ref with actor and scope metadata |

Every input must be bounded, attributable, and represented in `raw_evidence_refs`. No input class grants authority merely by being present.

## 9. Output Classes

The future reducer may describe these output classes:

- `GuardianEvidencePacket` — the only packet output class currently allowed. It must conform to the schema family and preserve evidence refs, uncertainty, forbidden interpretations, limits, provenance, and false authority locks.
- `GuardianEvidencePacketStaticValidationResult` — a check result for packet shape and guardrails. It is not authority, truth approval, ingestion, or execution support.
- `reducer_diagnostics_summary` — bounded diagnostic information about reduction coverage, omitted inputs, warnings, contradictions, and self-check outcomes. Diagnostics are diagnostic only, not ingestion.

No other packet output class is authorized by this contract. A future output expansion requires a separate contract.

GuardianEvidencePacket is the only packet output class currently allowed.

## 10. Reducer Lifecycle

The ordered lifecycle is:

1. Receive bounded evidence input set.
2. Classify input classes.
3. Assign evidence refs.
4. Extract candidate claims.
5. Bind candidate claims to evidence refs.
6. Mark unsupported, blocked, inferred, or not_evaluated claims honestly.
7. Preserve uncertainty.
8. Preserve forbidden interpretations.
9. Set authority locks.
10. Select next gate options.
11. Produce GuardianEvidencePacket.
12. Run static validation.
13. Return packet plus validation result for human/operator review.
14. Stop.

The lifecycle has no recursive autonomous loop, source mutation, command execution, receipt writing, ingestion, Execution Ledger write, or WorkOrder mutation. There is no command execution, no receipt writing, no ingestion, no Execution Ledger write, and no WorkOrder mutation.

## 11. Reduction Depth Semantics

`review_depth` controls evidence handling and self-check policy, not model personality.

| Depth | Input budget posture | Claim ledger depth | Contradiction scan | Missing-proof handling | Self-check passes | Insufficient when |
|---|---|---|---|---|---:|---|
| `light` | Small, explicitly selected set | Primary claims only | Direct contradictions | Record obvious gaps | 1 | Evidence is broad, disputed, or cross-artifact |
| `medium` | Bounded source set with normal context | Claims, limits, and direct counterclaims | Direct and near-neighbor contradictions | Record gaps and next options | 1 | Cross-source lineage or ambiguity matters |
| `high` | Larger bounded set with provenance review | Full claim ledger and evidence bindings | Cross-source contradiction scan | Preserve uncertainty, blocked claims, and missing-proof ledger | 2 | Source authority or contradiction remains unresolved |
| `xhigh` | Maximum explicitly bounded set | Full ledger plus adversarial/context review | Deep cross-source and interpretation scan | Preserve every material uncertainty and unresolved conflict | 3, bounded | Evidence cannot be bounded or conflicts cannot be represented honestly |

Insufficient depth must produce uncertainty or a blocked/not-evaluated claim. It must not cause silent omission or authority promotion.

## 12. Bounded Self-Check Policy

The conceptual loop policy is:

```yaml
bounded: true
recursive_autonomous_loop_allowed: false
maximum_self_check_passes: controlled_by_review_depth
```

A self-check may inspect schema completeness, evidence binding, contradiction preservation, authority locks, forbidden interpretations, and limits. A failed self-check must produce uncertainty or blocked claims, not automatic repair. The reducer must stop after producing the packet plus validation result.

## 13. Evidence Reference Handling

References point to source artifacts; they do not replace them. Each ref must include a stable `ref_id`, type, relative path or URI, source system, status, trust posture, and available timestamp/hash metadata. A hash proves file continuity, not correctness.

The reducer must not paste entire artifacts into a packet, silently discard a referenced contradiction, or treat a receipt, command record, proof doc, test result, or validation result as authority.

## 14. Claim Extraction Rules

Candidate claims must be bounded, attributable, and phrased with context and temporal limits. Extract claims from evidence, not from desired product outcomes. Claims may be `supported`, `unsupported`, `blocked`, `inferred`, or `not_evaluated`.

The reducer must retain a claim when evidence is incomplete if the honest status is blocked, inferred, unsupported, or not evaluated. It must not convert uncertainty into supported language for readability.

## 15. Claim-to-Evidence Binding Rules

Every claim must reference one or more existing `raw_evidence_refs` IDs. Missing or weak evidence must be recorded in `missing_evidence`, and counterclaims must remain visible. A reduced summary cannot stand in for claim-level evidence binding.

## 16. Contradiction Handling

Contradictory evidence must be preserved in the claim ledger and uncertainty fields. The reducer may classify a claim as contested, blocked, unsupported, inferred, or not evaluated according to the schema vocabulary, but it must not silently choose the most favorable interpretation.

## 17. Missing-Proof Handling

Missing proof must become explicit uncertainty, a missing-proof ledger entry, a blocked claim, or a bounded next gate. Missing proof must never be filled with a guessed receipt, synthetic authority, or automatic repair.

## 18. Authority Lock Rules

The future reducer must emit this authority block by default, with every value false:

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

Evidence presence, validation success, a receipt, a command-run record, or an orchestration result must not promote any lock. A future contract must explicitly authorize any change.

## 19. Invariant Preservation Rules

The reducer must preserve evidence-not-authority, validation-not-execution, bounded-loop, no-source-mutation, no-ingestion, no-provider-execution, no-Pi-Loop, no-plan-execution, no-Execution-Ledger, and no-WorkOrder invariants. It must preserve the exact bridge boundary label when the packet is preflight-oriented:

```text
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

## 20. Forbidden Interpretation Rules

Every packet must state what it must not be read as. At minimum, a future reducer must prevent interpretations that its output is runtime execution, ingestion, Execution Ledger truth, WorkOrder mutation, UI support, provider execution, plan execution, or Pi Loop authorization.

## 21. Next Gate Selection Rules

Next gates are review or design steps, not execution requests. Select options based on missing proof, unresolved contracts, and risk. The recommended next gate must remain bounded and must not imply dispatch, mutation, ingestion, or release approval.

## 22. Provenance and Limits Rules

Provenance must identify reducer/profile version, input artifact IDs, source scope, and timestamps. Limits must identify input caps, summary budget, artifacts consumed, tokens consumed where measurable, and any omitted or unresolved evidence. Provenance records lineage; it does not confer trust.

## 23. Static Validation Handoff

After packet production, a future reducer may invoke the static validator only as a bounded validation handoff defined by a later implementation contract. The result checks shape and guardrails only. It does not prove reducer correctness, claim truth, evidence sufficiency, ingestion, or execution authorization.

## 24. Human Review Handoff

The packet plus validation result must be returned for human/operator review and then stop. Reviewers must inspect evidence refs, claims, uncertainty, contradictions, forbidden interpretations, authority locks, and warnings. Review does not become approval merely because validation passed.

## 25. Relationship to Authoring Template and Guide

Manual authoring remains valid before runtime reducer implementation. The template and authoring guide are static aids. Future reducer output must preserve the same authoring invariants: evidence refs, uncertainty, forbidden interpretations, and false authority locks unless separately authorized.

## 26. Relationship to Existing Fixtures

The bridge proof-chain fixture and local validator toolchain fixture are static examples. They demonstrate two evidence domains and must not be treated as runtime reducer output. A future reducer must not overfit to either fixture.

## 27. Relationship to Command Bus

The future reducer does not call command bus. Command-bus run/event records may be supplied as bounded evidence snapshots, but they do not authorize command execution, dispatch, ingestion, or mutation.

## 28. Relationship to Codex Runner Bridge

The future reducer does not call Codex Runner. Bridge proof-chain artifacts may be input evidence, but the reducer must not invoke validation, orchestration, daemon behavior, provider execution, or source mutation through the bridge.

## 29. Relationship to Runtime Tool Loop

The future reducer does not execute a runtime tool loop. It does not call tools, dispatch work, apply patches, invoke providers, or create recursive continuation. Any future tool-loop integration requires a separate explicit contract.

## 30. Relationship to Execution Ledger and WorkOrder

The future reducer does not write Execution Ledger entries or mutate WorkOrders. Adoption and mapping require separate explicit contracts after authority, identity, persistence, export, and review semantics are defined.

## 31. Relationship to Future UI

The future reducer does not add UI, routes, UI triggers, or dev-build test buttons. Future UI surfacing requires a separate read-only operator-surface contract.

## 32. Relationship to CI and Release Gates

The future reducer design does not add CI/default release gating or widen release support. A future CI opt-in validation contract must explicitly define scope, failure policy, and release-truth boundaries.

## 33. Failure Modes

| Failure | Required response |
|---|---|
| Input set exceeds bounds | Stop or narrow the input set; record uncertainty. |
| Evidence ref cannot be resolved | Preserve the ref and mark affected claims blocked or not evaluated. |
| Claim lacks evidence binding | Do not emit supported status; record missing proof. |
| Contradictions remain | Preserve them and mark the claim contested/blocked or not evaluated. |
| Self-check fails | Emit uncertainty or blocked claims; do not auto-repair. |
| Authority lock would become true | Fail closed and preserve the false lock. |
| Static validation fails | Return the failure result for review; do not execute repair. |
| Consumer requests execution | Stop; require a separate explicit contract. |

## 34. Future Allowed Slices

These are future tasks only, not implemented here:

- pure reducer library contract
- pure reducer library implementation
- reducer CLI dry-run
- packet generator contract
- packet generator implementation
- read-only operator surface contract
- dev-build-only bridge test affordance contract
- Execution Ledger adoption contract
- WorkOrder mapping contract
- CI opt-in validation contract

## 35. Forbidden Interpretations

Do not interpret this contract as:

- runtime reducer behavior
- packet generation
- runtime validator behavior
- an API route or frontend UI
- evidence ingestion or receipt writing
- command-bus or Codex Runner invocation
- live validation or orchestration
- Pi Loop invocation or plan execution
- source mutation, patch application, or provider execution
- Execution Ledger or WorkOrder mutation
- CI/default release gating
- runtime support or release support expansion

## 36. Bottom Line

This is a design contract only. A future reducer may reduce bounded evidence into a GuardianEvidencePacket, preserve evidence references and uncertainty, keep authority locks false, hand off to static validation, return for human review, and stop. It must not turn evidence into authority or summaries into execution.
