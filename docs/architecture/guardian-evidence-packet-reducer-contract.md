# Guardian Evidence Packet and Reducer Profile Contract

> Classification: architecture contract
> Status: docs-only schema definition — no runtime implementation
> Scope: Guardian-facing evidence reduction interface

Last updated: 2026-07-09

Source anchors:
- docs/architecture/guardian-codex-runner-bridge-proof-chain-index.md
- docs/architecture/guardian-codex-runner-preflight-bridge-contract.md
- docs/architecture/guardian-codex-runner-command-bus-live-orchestration-proof.md
- guardian/command_bus/contracts.py
- guardian/codex_runner_bridge/contracts.py
- guardian/codex_runner_bridge/adapter.py
- docs/architecture/agent-protocol-operations.md
- docs/architecture/config-and-ops.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/canonical-token-philosophy.md

## 1. Purpose

This contract defines the first canonical Guardian-facing evidence interface for reducing raw proof artifacts, command-bus run/event records, receipts, proof docs, validation output, and architecture evidence into bounded Guardian-readable packets.

Codexify currently generates many evidence surfaces — proof documents, command runs, receipts, hashes, validation logs — but has no single Guardian-facing shape for consuming, reducing, self-checking, and surfacing that evidence. This contract defines the schema family and reduction policies without implementing a runtime reducer.

## 2. Status

Status: docs-only schema definition.

This contract does not:

- implement runtime reducer code
- add persistence or database models
- add API routes
- add frontend UI
- add a dev-build test button
- add ingestion
- authorize execution, source mutation, Pi Loop, or Codexify ingestion

This contract does not add ingestion. No evidence is ingested into Codexify by this contract.

Static authoring aids are available for future fixture authors:

- [Guardian Evidence Packet Template](./templates/guardian-evidence-packet-template.v1.json)
- [Guardian Evidence Packet Authoring Guide](./guardian-evidence-packet-authoring-guide.md)

The template and guide are static authoring aids only. They do not implement packet generation, runtime reducer behavior, ingestion, execution, UI, Execution Ledger adoption, or WorkOrder mutation.

The local validator toolchain fixture demonstrates the schema outside the bridge-proof domain. Multiple fixtures make future reducer design less likely to overfit to one evidence source. This does not implement reducer behavior or generator behavior.

The [runtime reducer design contract](./guardian-evidence-packet-runtime-reducer-design-contract.md) defines the future reducer boundary. It is docs-only: it does not implement reducer code or packet generation, and it does not authorize ingestion, execution, UI, Execution Ledger adoption, or WorkOrder mutation.

Code-level contract constants now exist under `guardian/evidence_packets/contracts.py`. Future backend reducer work should use this package for repeated contract-bearing packet literals. This does not implement reducer behavior or generator behavior.

Packet literals now have a code-level source under `guardian/evidence_packets/contracts.py`, and local validators are aligned to that package. Future backend reducer work must avoid re-inventing packet literals.

Code-level reducer interface contracts now exist under `guardian/evidence_packets/reducer_contracts.py`. Future backend reducer work must use these interfaces and `guardian/evidence_packets/contracts.py`. This does not implement reducer behavior or generator behavior.

A pure reducer dry-run skeleton exists under `guardian/evidence_packets/reducer.py`. It proves lifecycle stop behavior only; it is not a reducer implementation, packet generator, or runtime support.

A local reducer dry-run CLI exists under `scripts/guardian/reducer_dry_run.py`. It proves dry-run diagnostics and stop behavior only; it is not a reducer implementation, packet generator, validation behavior, or runtime support.
The local Makefile target `guardian-evidence-reducer-dry-run` proves dry-run diagnostics and stop behavior only. It is not a reducer implementation, packet generator, validation behavior, runtime support, CI/default release gate, or release support expansion.

The static ReducerInputBundle template and fixture — the [template](./templates/guardian-evidence-reducer-input-bundle-template.v1.json) and [local tooling fixture](./fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json) — prepare future reducer input shape only. They do not implement reducer behavior, packet generation, ingestion, UI, Execution Ledger adoption, or WorkOrder mutation.

Static ReducerInputBundle validation doctrine now exists in the [input-bundle static validator contract](./guardian-evidence-reducer-input-bundle-static-validator-contract.md). It is docs-only and does not implement validator behavior, input-bundle loading, reducer behavior, packet generation, ingestion, UI, Execution Ledger adoption, or WorkOrder mutation.

The local input-bundle static validator exists at `scripts/guardian/validate_reducer_input_bundle.py`. It validates bundle shape and guardrails only; it is not an input-bundle loader, reducer behavior, or packet generation.

The local input-bundle batch validator exists at `scripts/guardian/validate_reducer_input_bundles.py`. It validates static bundle shape and guardrails across templates and fixtures only; it is not an input-bundle loader, reducer behavior, packet generation, or release gating.

Local input-bundle batch validation is available through Make with
`make guardian-evidence-reducer-input-bundles-validate`. It validates static
bundle shape and guardrails across templates and fixtures only; it is not an
input-bundle loader, reducer behavior, packet generation, or release gating.

The docs-only [input-bundle dry-run loader contract](./guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md) prepares a future loader seam for diagnostics-only dry-run execution. It is not an input-bundle loader implementation, reducer behavior, packet generation, or release gating.

The local dry-run input-bundle loader exists through `reducer_dry_run.py --input-bundle`. It prepares `ReducerInputBundle` objects from validated bundle JSON for diagnostics-only dry-run. It is not runtime reducer behavior, packet generation, or release gating.

The local dry-run input-bundle loader is available through Make with
`make guardian-evidence-reducer-input-bundle-dry-run`. It prepares
`ReducerInputBundle` objects from validated bundle JSON for diagnostics-only
dry-run. It is not runtime reducer behavior, packet generation, or release
gating.

The docs-only [Guardian Evidence Packet generator contract](./guardian-evidence-packet-generator-contract.md) defines the future seam from validated reducer input to `GuardianEvidencePacket` output. It is not generator implementation, runtime reducer behavior, evidence ingestion, execution, packet output on main, or release gating.

The [Guardian Evidence Bounded Read Contract](./guardian-evidence-bounded-read-contract.md)
is a docs-only future seam between validated reducer inputs and packet-generation
evidence preparation. It is not reader implementation, packet generation,
runtime reducer behavior, evidence ingestion, execution, or release gating.

Local bounded evidence-read tooling now exists. It defines and implements the
local seam between validated reducer inputs and future packet-generation
evidence preparation. It is not packet generation, runtime reducer behavior,
evidence ingestion, execution, or release gating.

Local bounded evidence-read tooling is available through
`make guardian-evidence-bounded-read`. It provides local bounded evidence
preparation output for future packet-generation work. It is not packet
generation, runtime reducer behavior, evidence ingestion, execution, or release
gating.

The static bounded-read result fixture
`docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`
exists for future generator test input. It is not packet generation, runtime
reducer behavior, evidence ingestion, execution, or release gating.

## 3. Scope

This contract defines:

- GuardianEvidencePacket schema — the transport shape for evidence summaries
- GuardianReducerProfile schema — the configurable reduction policy
- GuardianEvidenceRef schema — a typed pointer to a source artifact
- GuardianClaimLedgerEntry schema — a truth claim with evidence binding
- GuardianAuthorityState schema — canonical authority locks
- GuardianInvariantCheck schema — invariant validation record
- GuardianUncertaintyEntry schema — documented unknowns
- GuardianForbiddenInterpretation schema — explicit non-authorized meanings
- GuardianNextGateOption schema — next evaluation step
- Four reduction depth levels (light, medium, high, xhigh)
- Bounded self-check loop policy

It does not implement any of these as runtime code.

## 4. Why This Exists

The Guardian Codex Runner bridge proof chain now spans thirteen artifacts. Command-bus invocations produce run/event records. Validation receipts carry structured evidence. Proof docs record live outcomes. An operator or Guardian agent approaching this material needs a bounded reduction surface that:

- Preserves evidence references (not authority through summary alone).
- Preserves uncertainty (not hiding blocked, failed, or partial proof).
- Preserves forbidden interpretations (not silently widening implied authority).
- Applies a configurable reduction depth (not one-size-fits-all).
- Self-checks within bounded passes (not recursive autonomous loops).

This contract defines the schema family and policies. A future reduction implementation would produce `GuardianEvidencePacket` instances from raw evidence sources according to a selected `GuardianReducerProfile`.

## 5. Current Truth

What is true now:

- Both Guardian Codex Runner bridge preflight commands are live-proven through command bus.
- Command-bus run/event records exist as operational/control-plane records — they are not automatically Guardian-readable truth.
- Proof docs, receipts, hashes, command outputs, and validation logs are evidence surfaces, not authority.
- No Guardian-facing evidence reduction surface exists today.
- This contract defines the shape for such a surface.
- No runtime reducer, persistence, UI, or ingestion is implemented.

## 6. Evidence Substrate vs Guardian-Facing Reduction

```txt
RAW EVIDENCE SUBSTRATE
  proof docs / command runs / receipts / validation logs / hashes / architecture contracts
       |
       v
  GuardianReducerProfile (selected depth, self-check policy, budget)
       |
       v
  GuardianEvidencePacket (summary, claim ledger, authority state, uncertainty, forbidden interpretations)
       |
       v
  FUTURE SURFACES (each requires a separate explicit contract):
    - read-only operator UI (separate contract)
    - dev-build test affordance (separate contract)
    - Execution Ledger adoption (separate contract)
    - WorkOrder mutation (separate contract)
```

None of the future surfaces are implemented or authorized by this contract.

## 7. Canonical Schema Family

| Schema | Purpose |
|---|---|
| `GuardianEvidencePacket` | Top-level transport shape for evidence summaries |
| `GuardianReducerProfile` | Configurable reduction depth and self-check policy |
| `GuardianEvidenceRef` | Typed pointer to a source evidence artifact |
| `GuardianClaimLedgerEntry` | Truth claim with evidence binding and confidence |
| `GuardianAuthorityState` | Canonical authority locks (always false in bridge context) |
| `GuardianInvariantCheck` | Invariant validation record |
| `GuardianUncertaintyEntry` | Documented unknown, missing evidence, or blocked condition |
| `GuardianForbiddenInterpretation` | Explicit statement of what a result does NOT mean |
| `GuardianNextGateOption` | Next evaluation step recommendation |

## 8. GuardianEvidencePacket

Top-level evidence summary shape:

```
GuardianEvidencePacket:
  schema_version: string           # e.g. "v0"
  packet_id: string                # unique packet identifier
  created_at: string               # ISO 8601 timestamp
  source_domain: string            # e.g. "guardian.codex_runner.bridge"
  evidence_class: string           # e.g. "live_validate", "dry_run_orchestration"
  review_depth: string             # "light" | "medium" | "high" | "xhigh"
  subject: string                  # human-readable subject line
  reducer_profile_ref: string      # profile_id of the profile used
  raw_evidence_refs: [GuardianEvidenceRef]  # pointers to source artifacts
  reduced_summary: string          # bounded natural-language summary
  claim_ledger: [GuardianClaimLedgerEntry]
  authority_state: GuardianAuthorityState
  invariant_checks: [GuardianInvariantCheck]
  uncertainty: [GuardianUncertaintyEntry]
  forbidden_interpretations: [GuardianForbiddenInterpretation]
  next_gate_options: [GuardianNextGateOption]
  recommended_next_gate: string | null
  loop_policy:
    max_self_check_passes: integer
    passes_executed: integer
    pass_results: [string]
  provenance:
    reducer_version: string
    profile_id: string
    input_artifact_ids: [string]
  limits:
    max_source_artifacts: integer
    summary_budget_tokens: integer
    artifacts_consumed: integer
    tokens_consumed: integer
```

## 9. GuardianReducerProfile

Configurable reduction policy:

```
GuardianReducerProfile:
  schema_version: string           # e.g. "v0"
  profile_id: string               # unique profile identifier
  review_depth: string             # "light" | "medium" | "high" | "xhigh"
  max_source_artifacts: integer    # hard cap on source artifacts consumed
  summary_budget_tokens: integer   # token budget for reduced_summary
  claim_ledger_required: boolean
  evidence_refs_required: boolean
  invariant_check_required: boolean
  contradiction_scan_required: boolean
  forbidden_interpretations_required: boolean
  uncertainty_required: boolean
  next_gate_required: boolean
  self_check_passes: integer       # number of bounded self-check loops
  adversarial_review_required: boolean
  missing_proof_ledger_required: boolean
  allowed_output_shapes: [string]  # e.g. ["GuardianEvidencePacket"]
```

The profile defines what the reducer should produce — it does not grant authority.

## 10. GuardianEvidenceRef

Typed pointer to a source evidence artifact:

```
GuardianEvidenceRef:
  ref_id: string                   # unique reference identifier
  ref_type: string                 # e.g. "proof_doc", "command_run", "receipt", "hash_report"
  uri_or_path: string              # path to the artifact
  source_system: string            # e.g. "codex_runner", "command_bus", "architecture_docs"
  content_hash: string | null      # sha256 of artifact content, if available
  timestamp: string | null         # artifact timestamp
  status: string                   # e.g. "pass", "fail", "blocked", "available"
  trust_posture: string            # e.g. "evidence_only", "not_authority"
  notes: string | null
```

## 11. GuardianClaimLedgerEntry

A truth claim with evidence binding:

```
GuardianClaimLedgerEntry:
  claim_id: string                 # unique claim identifier
  claim: string                    # the claim being made
  status: string                   # "proven" | "unproven" | "contested" | "blocked"
  evidence_refs: [string]          # ref_ids supporting this claim
  confidence: string               # "high" | "medium" | "low" | "none"
  limits:
    context_boundary: string
    temporal_boundary: string
  counterclaims: [string]          # ref_ids that contest this claim
  missing_evidence: [string]       # evidence that is known to be absent
  forbidden_interpretations: [string]  # what this claim must not be read as
```

## 12. GuardianAuthorityState

Canonical authority locks. In bridge context, all must be `false`:

```
GuardianAuthorityState:
  guardian_operational: boolean          # false
  plan_execution_allowed: boolean        # false
  pi_loop_invocation_allowed: boolean    # false
  codexify_ingestion_allowed: boolean    # false
  durable_mutation_allowed: boolean      # false
  provider_execution_allowed: boolean    # false
  patch_application_allowed: boolean     # false
  dispatch_allowed: boolean              # false
  merge_allowed: boolean                 # false
```

All values in this contract's examples remain `false`.

## 13. GuardianInvariantCheck

Invariant validation record:

```
GuardianInvariantCheck:
  invariant_id: string             # reference to invariant definition
  description: string              # human-readable invariant
  status: string                   # "holds" | "violated" | "unverified"
  evidence_refs: [string]          # ref_ids supporting this check
  notes: string | null
```

## 14. GuardianUncertaintyEntry

Documented unknown, missing evidence, or blocked condition:

```
GuardianUncertaintyEntry:
  uncertainty_id: string
  description: string              # what is uncertain and why
  severity: string                 # "blocking" | "high" | "medium" | "low"
  missing_evidence: [string]       # what evidence would resolve this
  resolution_options: [string]     # how to resolve
```

## 15. GuardianForbiddenInterpretation

Explicit statement of what a result does NOT mean:

```
GuardianForbiddenInterpretation:
  interpretation_id: string
  statement: string                # e.g. "orchestration preflight pass != plan execution authority"
  applies_to_claims: [string]      # claim_ids this interpretation constrains
  applies_to_evidence: [string]    # ref_ids this interpretation constrains
```

## 16. GuardianNextGateOption

Next evaluation step recommendation:

```
GuardianNextGateOption:
  gate_id: string
  description: string
  prerequisites: [string]          # what must be satisfied before this gate
  risk: string                     # "low" | "medium" | "high" | "blocked"
```

## 17. Reduction Depth Levels

Four reduction depths govern how much evidence is processed and how much self-check is required.

### light

- **Intended use:** Quick status glance — "did validate pass?"
- **Evidence included:** Packet subject line, status result, authority state only
- **Claim ledger required:** No
- **Invariant check required:** No
- **Contradiction scan required:** No
- **Forbidden interpretation required:** No
- **Self-check pass count:** 0 (schema validity only — no extra pass)
- **Summary budget:** Single sentence or status keyword
- **Insufficient for:** Architecture-impact decisions, operator handoff, any action that could be dangerous to forget

### medium

- **Intended use:** Normal planning and operator handoff
- **Evidence included:** Subject, status, reduced summary, evidence refs
- **Claim ledger required:** Yes
- **Invariant check required:** No (optional)
- **Contradiction scan required:** No (optional)
- **Forbidden interpretation required:** No (optional)
- **Self-check pass count:** 1 bounded pass
- **Summary budget:** Configurable token budget (default ~500 tokens)
- **Insufficient for:** Architecture-impact decisions where proof boundary language matters, decisions where missing evidence could change interpretation

### high

- **Intended use:** Architecture-impact decisions
- **Evidence included:** Full claim/evidence map, invariant checks, uncertainty entries, forbidden interpretations
- **Claim ledger required:** Yes, with counterclaims and missing evidence
- **Invariant check required:** Yes
- **Contradiction scan required:** Yes
- **Forbidden interpretation required:** Yes
- **Self-check pass count:** At least 2 bounded passes
- **Summary budget:** Configurable token budget (default ~2000 tokens)
- **Insufficient for:** Dangerous-to-forget decisions where multiple independent adversarial reviews are warranted

### xhigh

- **Intended use:** Dangerous-to-forget decisions
- **Evidence included:** Exhaustive artifact map within configured budget, full claim/evidence/counterclaim ledger, missing-proof ledger
- **Claim ledger required:** Yes, with counterclaims and missing evidence
- **Invariant check required:** Yes
- **Contradiction scan required:** Yes
- **Forbidden interpretation required:** Yes
- **Self-check pass count:** At least 3 bounded passes, including one adversarial review pass
- **Adversarial review required:** Yes
- **Missing proof ledger required:** Yes
- **Summary budget:** Configurable token budget (default ~5000 tokens)
- **Must not become:** An autonomous recursive loop — passes are bounded, not iterative

## 18. Bounded Self-Check Loop Policy

The reducer may self-check within bounded passes as defined by the profile. After the maximum pass count is reached:

- The reducer must stop.
- Any remaining unresolved items move to the uncertainty ledger.
- No additional pass may be automatically initiated.
- No recursive autonomous execution loop is permitted.

Self-check passes produce pass results (e.g., `pass_1_ok`, `pass_2_contradiction_found`, `pass_3_adversarial_ok`). These are recorded in `loop_policy.pass_results`.

## 19. Claim and Evidence Binding Rules

- Every claim in `claim_ledger` must have at least one `evidence_refs` entry if `claim_ledger_required` is true in the profile.
- Claims without supporting evidence must be marked `status: "unproven"` with `confidence: "none"`.
- Counterclaims in `missing_evidence` must be listed when known.
- Forbidden interpretations must be attached to claims they constrain.
- Evidence refs link to original artifacts — the packet is a summary, not a replacement.

## 20. Contradiction and Missing-Proof Handling

When contradiction scan is required (high/xhigh):

- Conflicting claims must be recorded with `status: "contested"`.
- Both sides must link to their supporting evidence refs.
- Contradictions that cannot be resolved within the self-check budget move to the uncertainty ledger.

When missing-proof ledger is required (xhigh):

- Known gaps in evidence must be explicitly listed.
- Each gap must include what evidence would be needed and why it is missing.
- The summary must state what confidence is reduced due to missing proof.

## 21. Authority Boundary

All authority locks in `GuardianAuthorityState` remain `false` when reducing bridge evidence. The reducer must not:

- Elevate `plan_execution_allowed` from false to true.
- Elevate `pi_loop_invocation_allowed` from false to true.
- Elevate `codexify_ingestion_allowed` from false to true.
- Elevate any lock from the value present in the source evidence.

The reducer summarizes evidence — it does not grant authority.

## 22. Relationship to Bridge Proof Chain

The bridge proof-chain index (`guardian-codex-runner-bridge-proof-chain-index.md`) is an evidence source candidate for future `GuardianEvidencePacket` production.

The index itself is not a `GuardianEvidencePacket`. The index does not authorize ingestion, execution, UI, Pi Loop invocation, or source mutation.

A future reducer implementation producing packets from bridge proof chain evidence must preserve the bridge boundary label and all false authority locks in every produced packet.

## 23. Relationship to Command Bus

Command-bus run/event records are operational/control-plane records. They are candidate evidence sources for the reducer but are not `GuardianEvidencePacket` instances themselves.

A future `GuardianEvidencePacket` may reference command-bus records as `GuardianEvidenceRef` entries with `ref_type: "command_run"`.

Command-bus records remain separate from evidence packets unless a future adoption contract explicitly connects them.

## 24. Relationship to Execution Ledger and WorkOrder

Execution Ledger adoption and WorkOrder mutation are separate future contracts. This contract does not:

- Connect `GuardianEvidencePacket` to Execution Ledger semantics.
- Connect `GuardianEvidencePacket` to WorkOrder semantics.
- Authorize durable mutation based on evidence reduction.

Any future Execution Ledger or WorkOrder integration requires explicit, separate contracts.

## 25. Relationship to Future UI

A future read-only operator UI for consuming `GuardianEvidencePacket` instances is a separate future surface. This contract does not:

- Define UI components or layouts.
- Add a dev-build test button.
- Authorize automated UI generation from packets.

UI surfacing requires a separate explicit contract.

## 26. Example Fixture

An illustrative static example GuardianEvidencePacket fixture exists at [`fixtures/guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json`](./fixtures/guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json). The fixture uses the Guardian Codex Runner bridge proof chain as the first worked example.

Key properties of the fixture:

- The fixture is illustrative and static — it is not generated by runtime code.
- The fixture is not persisted by an ingestion path.
- The fixture uses the bridge proof chain as source evidence.
- Future runtime implementation must conform to this contract before producing packets.
- The fixture preserves the exact four-line bridge boundary label.
- All nine authority locks remain false in the fixture.

A static validator contract for GuardianEvidencePacket shape and guardrail checks exists at [`guardian-evidence-packet-static-validator-contract.md`](./guardian-evidence-packet-static-validator-contract.md). The static validator contract defines future packet shape checks and guardrail checks. Static validation is not authority. Static validation does not prove claim truth. Static validation does not implement runtime reducer behavior.

A local static validator script exists at `scripts/guardian/validate_evidence_packet.py`. The script can check packet shape before future operator surfacing. Passing static validation is not evidence adoption. Passing static validation is not Execution Ledger truth. Passing static validation is not WorkOrder mutation.

A local batch validator exists at `scripts/guardian/validate_evidence_packets.py`. It can check all current GuardianEvidencePacket fixtures before future operator surfacing. Passing batch validation is not evidence adoption. Passing batch validation is not Execution Ledger truth. Passing batch validation is not WorkOrder mutation. Passing batch validation is not runtime support.

Future reducer implementations should produce packets that pass static validation before operator surfacing.

## 27. Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Packet reports authority lock as true | Reducer elevated a lock from source evidence | Authority locks must match source; contract enforces this |
| Summary drops uncertainty | Medium/light depth, or configuration error | High/xhigh depth requires uncertainty; missing uncertainty flagged in self-check |
| Claim lacks evidence refs | Reducer not enforcing evidence binding | Claim ledger rules (section 19) require evidence refs for proven claims |
| Self-check exceeds budget | Profile misconfigured | Loop policy enforces max passes; unresolved items move to uncertainty |
| Packet mistaken for authority | Consumer ignores authority locks and forbidden interpretations | Forbidden interpretations explicitly constrain meaning; docs state packet is not authority |
| Packet used as ingestion trigger | Consumer treats packet production as Codexify ingestion | This contract explicitly prohibits ingestion without a separate adoption contract |

## 28. Future Allowed Slices

Future slices beyond this contract remain deferred. Any implementation work would require separate contracts for:

- Runtime reducer service
- Database persistence for packets
- Read-only operator UI
- Dev-build test affordance
- Execution Ledger adoption
- WorkOrder mutation
- Bridge proof → evidence pipeline connection

None of these are authorized by this contract.

## 29. Forbidden Interpretations

Do not interpret this contract as meaning:

- a runtime reducer is implemented
- evidence has been ingested into Codexify
- Guardian UI is shipped
- a dev-build test button exists
- packet production = Execution Ledger write
- packet production = WorkOrder mutation
- evidence reduction = plan execution authorization
- evidence reduction = Pi Loop invocation authorization
- evidence reduction = source mutation authorization
- evidence reduction = provider execution authorization
- evidence reduction = Codexify ingestion
- the reducer is an autonomous agent loop
- self-check passes are recursive
- reduction depth controls model personality (it controls evidence handling and self-check policy)

## 30. Bottom Line

This contract defines the first canonical Guardian-facing evidence interface for reducing raw proof artifacts, command-bus run/event records, receipts, and architecture evidence into bounded Guardian-readable packets.

Nine schemas are defined. Four reduction depths (light, medium, high, xhigh) govern evidence handling and self-check policy. Bounded self-check loops prevent autonomous recursion. All authority locks remain false.

This is a docs-only contract. No runtime reducer, persistence, UI, ingestion, or execution authority is implemented or authorized.

```txt
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

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
