# Guardian Evidence Packet Generator Contract

## 1. Purpose

This contract defines a future local Guardian Evidence Packet generator seam
for the reducer pipeline. It describes how validated reducer input and bounded
evidence references may eventually become a `GuardianEvidencePacket` JSON
artifact under explicit review and validation boundaries.

## 2. Status

This is a docs-only contract. It does not implement a packet generator,
modify `reducer_dry_run.py`, modify validator scripts, generate
`GuardianEvidencePacket` output, or alter existing packet fixtures.

## 3. Scope

The contract covers future packet-generation inputs, output shape, evidence
binding, uncertainty, contradiction preservation, static validation handoff,
and human/operator review. It does not implement runtime reducer behavior,
evidence ingestion, persistence, UI, CI, or execution.

## 4. Current Truth

- Static GuardianEvidencePacket templates and fixtures exist.
- Static GuardianEvidencePacket validation exists.
- Static ReducerInputBundle template and fixture files exist.
- Single-file and batch input-bundle validators exist.
- A diagnostics-only dry-run input-bundle loader exists.
- No runtime reducer implementation exists.
- No packet generator exists.
- Dry-run diagnostics do not generate packets.

## 5. Why This Exists

The reducer pipeline needs a separate artifact-generation boundary so future
packet creation cannot silently turn bounded evidence references into source
truth, authority, execution, ingestion, or release approval.

## 6. Generator Is Not Authority

Packet generator success, when implemented later, must not imply execution
authority, source truth, receipt trust, WorkOrder mutation, or Execution Ledger
write. A future generator must preserve all authority locks as false unless a
separate authority-promotion contract exists.

## 7. Generator Is Not Execution

Packet generation is not execution. A future generator must not call command
bus, Codex Runner, live validation, orchestration, Pi Loop, provider
execution, or source mutation.

## 8. Generator Is Not Evidence Ingestion

Packet generation is not evidence ingestion. A generated packet is a bounded
summary artifact with evidence references; it is not Codexify durable truth,
Execution Ledger truth, or WorkOrder state.

## 9. Generator Is Not Runtime Reducer Behavior

This contract does not implement runtime reducer behavior. A future packet
generator may be a pure bounded transformation only after a separate reducer
implementation contract defines its authority and lifecycle boundaries.

## 10. Relationship to GuardianEvidencePacket Schema

Any future packet must conform to the existing `GuardianEvidencePacket` schema
and preserve its required fields, evidence references, claim ledger,
uncertainty, forbidden interpretations, provenance, limits, and false
authority state. A generator must not invent a parallel packet shape.

Packet may exist only after a future implementation.
packet may exist only after a future implementation.
packet must conform to GuardianEvidencePacket schema.

## 11. Relationship to ReducerInputBundle

A future generator may accept validated ReducerInputBundle metadata as one
input category. Input-bundle validation is not packet generation, file-read
approval, evidence authority, or execution authority.

## 12. Relationship to Dry-Run Loader

The dry-run loader remains diagnostics-only. Dry-run loader success is not
packet generation, evidence ingestion, or authority promotion. A future
generator is a separate seam and must not be added implicitly to
`reducer_dry_run.py`.

A local diagnostics-only evidence-packet inspection CLI option now exists through
`reducer_dry_run.py --evidence-packet`. It loads a GuardianEvidencePacket fixture,
validates it statically, and returns diagnostics output with bounded lifecycle
stop semantics. It does not produce reducer output, generate packets, read
source_ref targets, ingest evidence, or widen release support. It is mutually
exclusive with `--input-bundle` and `--input`. This inspection seam remains
diagnostics-only; it does not implement packet generation, runtime reducer
behavior, or authority promotion.
Generated packet fixture inspection through `--evidence-packet` reports bounded
count diagnostics for evidence refs, claims, uncertainty, and forbidden
interpretations. This inspection is diagnostics-only and does not change
generator behavior.

## 13. Relationship to Static Packet Validation

A future packet generator must hand generated output to the existing packet
static validator, or to a future explicitly contracted validation seam, before
operator surfacing. Validation checks shape and guardrails; it does not prove
claim truth or authorize execution.

## 14. Relationship to Input-Bundle Validation

Input-bundle validation can feed future generator prerequisites only through a
separate generator implementation. Validator success is not packet generation,
evidence authority, or runtime reducer support.

## 15. Relationship to Packet Fixtures

Existing packet fixtures remain static examples and must not be altered by this
contract. A future generated packet fixture requires a separate task, real
evidence provenance, review, and explicit fixture policy.

## 16. Required Generator Inputs

A future generator may require these bounded input categories:

- validated ReducerInputBundle metadata
- bounded evidence references
- operator context
- reducer profile or review depth
- validation result for input bundle
- explicit limits
- optional prior static validation result references

Inputs are references and metadata unless a separate evidence-read contract
explicitly authorizes reading. The generator must not treat input presence as
authority.

## 17. Required Generator Outputs

A future implementation should define a JSON-like result named
`GuardianEvidencePacketGeneratorResult`:

```text
{
  "schema_version": string,
  "generator_contract_version": string,
  "input_bundle_ref": string,
  "input_bundle_validation_result_ref": string,
  "packet": object | null,
  "packet_validation_result": object | null,
  "authority_state": object,
  "diagnostics": object,
  "limits": [string]
}
```

Required future limits must state: no execution, no evidence ingestion, no
command bus, no Codex Runner, no Pi Loop, no source mutation, no provider
execution, no WorkOrder mutation, no Execution Ledger write, and no release
support expansion.

Limits summary: no execution; no evidence ingestion; no command bus; no Codex Runner; no Pi Loop; no source mutation; no provider execution; no WorkOrder mutation; no Execution Ledger write; no release support expansion.

## 18. Evidence Reference Rules

Future diagnostics must include `source_ref_read_policy`, `evidence_ref_count`,
`claim_count`, `uncertainty_count`, `forbidden_interpretation_count`, and
`contradiction_count`.

Evidence references must point to bounded source artifacts and preserve
identity, source scope, timestamps, status, trust posture, and notes. A future
packet generator must not paste entire artifacts, silently replace references
with conclusions, or read `source_ref` targets unless a separate evidence-read
contract explicitly allows that path.

## 19. Claim Ledger Rules

Every future claim must bind to one or more evidence references. Supported,
unsupported, blocked, inferred, and not-evaluated statuses remain valid. The
generator must not convert uncertainty, missing evidence, or an inferred claim
into supported language for readability.

## 20. Authority State Rules

The future generator must preserve all authority locks as false by default.
Packet generation must never promote evidence to authority. Any non-false
authority state requires a separate explicit authority-promotion contract.

## 21. Uncertainty Rules

The generator must preserve uncertainty, missing proof, unresolved evidence,
and confidence limits. High and xhigh review-depth inputs must not silently
drop uncertainty or convert warnings into certainty.

## 22. Forbidden Interpretation Rules

Every future packet must state what it must not be read as, including runtime
execution, evidence ingestion, source truth, Execution Ledger truth, WorkOrder
mutation, UI support, provider execution, plan execution, and Pi Loop
authorization.

## 23. Contradiction Handling

The generator must never silently drop contradictions. Contradictory evidence
must remain represented in the claim ledger, uncertainty, evidence references,
or diagnostics. A failed self-check must produce blocked or uncertain output,
not automatic repair or favorable interpretation.

## 24. Source Reference Boundary

A future packet generator must not read source_ref targets unless a separate
evidence-read contract explicitly allows that path. It must not execute
source_ref targets or mutate source_ref targets. It must not call command bus,
Codex Runner, live validation, orchestration, Pi Loop, provider execution, or
source mutation.

## 25. Validation Requirement

Future generator input must pass the applicable input-bundle static validation
before generation begins. A failed input validation must stop generation. A
passing validation result is shape and guardrail evidence only, not truth,
authority, ingestion, execution, or release approval.

## 26. Output Validation Requirement

Any future packet output must conform to the GuardianEvidencePacket schema and
must be produced only after the future generator's bounded checks. The packet
validation result must be produced by the existing packet static validator or
a future explicitly contracted validation seam. Passing packet validation is
not claim truth, evidence authority, execution support, or release approval.

## 27. Error and Exit Semantics

A future generator implementation must fail closed on malformed input,
missing evidence bindings, authority-lock violations, contradictory evidence
loss, or validation failure. It must report bounded diagnostics and stop. It
must not repair source, retry into execution, write receipts, mutate durable
state, or broaden scope after failure.

## 28. Relationship to Execution Ledger and WorkOrder

The future generator must not mutate WorkOrders or write Execution Ledger
entries. Execution Ledger adoption and WorkOrder mapping require separate
explicit contracts for identity, authority, persistence, export, review, and
failure semantics.

## 29. Relationship to UI and CI

This contract does not add UI, API routes, dev-build test buttons, CI/default
release gating, or release support expansion. Future read-only operator
surfacing and CI opt-in validation require separate contracts.

## 30. Forbidden Interpretations

This contract must not be interpreted as packet generator implementation,
packet output on main, runtime reducer behavior, evidence ingestion, source
truth, authority promotion, execution support, receipt trust, UI support, CI
gating, release gating, or release support expansion.

Boundary summary: this contract does not implement a packet generator; it does not modify `reducer_dry_run.py`; it does not modify validator scripts; it does not generate GuardianEvidencePacket output; it does not alter existing packet fixtures; it does not implement runtime reducer behavior; it does not implement evidence ingestion; it does not add persistence; it does not add UI; it does not add CI/default release gating; it does not authorize execution; it does not authorize source mutation; it does not authorize Pi Loop invocation; it does not authorize provider execution; it does not authorize Codexify ingestion.

A future packet generator must not read source_ref targets unless a separate evidence-read contract explicitly allows that path.
Future generator boundary summary: a future packet generator must not call command bus; a future packet generator must not call Codex Runner; a future packet generator must not mutate WorkOrders; a future packet generator must not write Execution Ledger entries.

This contract does not generate `GuardianEvidencePacket` output.

## 31. Future Allowed Slices

The following are future tasks only and are not implemented here:

- bounded evidence-read contract
- bounded evidence-read implementation
- pure packet generator implementation
- packet generator focused tests
- packet generator Make target
- generated packet fixture
- packet static validation integration
- read-only operator surface contract
- Execution Ledger adoption contract
- WorkOrder mapping contract
- CI opt-in validation contract

## 32. Bottom Line

This docs-only contract defines a future bounded packet-generation seam. It
does not generate packets, implement a generator, alter fixtures, implement
runtime reducer behavior, ingest evidence, add persistence or UI, authorize
execution, or widen CI/release support.

### Required future conceptual flow

```text
Validated ReducerInputBundle
  -> future bounded evidence preparation contract
  -> future packet generator
  -> GuardianEvidencePacket
  -> static packet validator
  -> human/operator review
  -> future UI, Execution Ledger, WorkOrder, CI, or runtime use only through separate contracts
```

The flow must be read with these boundaries: packet generation is not
execution; packet generation is not evidence authority; packet generation is
not source truth; packet generation is not receipt trust; packet generation is
not WorkOrder mutation; packet generation is not Execution Ledger write; and
packet generation is not release approval.

packet generation is not execution; packet generation is not evidence authority; packet generation is not source truth; packet generation is not receipt trust; packet generation is not WorkOrder mutation; packet generation is not Execution Ledger write; packet generation is not release approval.

Packet generation is not execution; packet generation is not evidence authority; packet generation is not source truth; packet generation is not receipt trust; packet generation is not WorkOrder mutation; packet generation is not Execution Ledger write; packet generation is not release approval.

The [Guardian Evidence Bounded Read Contract](./guardian-evidence-bounded-read-contract.md)
is a separate docs-only seam. A future packet generator implementation must
depend on bounded evidence-read output before turning source references into
packet evidence. Bounded read success is not authority, source truth approval,
evidence ingestion, execution, WorkOrder mutation, or an Execution Ledger
write. This generator contract still does not implement packet generation.

Local bounded evidence-read tooling now exists. Future packet generator
implementation may consume its bounded read results only through a separate
generator implementation. Bounded read success remains not authority, not
source truth approval, not evidence ingestion, not execution, not WorkOrder
mutation, and not an Execution Ledger write.
Bounded read output may feed future packet generation only through a separate generator implementation.

### Implementation status

Local stdout-only packet generator tooling now exists at
`scripts/guardian/generate_evidence_packet.py`. It accepts one bounded-read
result JSON file, reads only that file, does not read `source_ref` targets, and
generates `GuardianEvidencePacket` output in memory/stdout only. It validates
the generated packet with static packet validation, does not write packet
fixtures, ingest evidence, promote evidence to authority, implement runtime
reducer behavior, or call command bus, Codex Runner, live validation,
orchestration, Pi Loop, provider execution, source mutation, WorkOrder
mutation, or Execution Ledger writes. It is not CI/default release gating or
release support expansion.

```bash
python3 scripts/guardian/generate_evidence_packet.py docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json --json
```

The generator fails closed when bounded-read input contains no usable read
evidence refs. `pass_with_warnings` is insufficient unless at least one usable
read evidence ref exists. Supported claims must never have empty
`evidence_refs`; skipped-only bounded-read input is failure/not-generated, not
a successful packet.

A local Make target now exists:
```bash
make guardian-evidence-packet-generate
```
It runs:
```bash
python3 scripts/guardian/generate_evidence_packet.py docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json --json
```
It consumes bounded-read result JSON only. It emits generated
GuardianEvidencePacket output inside the generator result to stdout only. It
validates generated packet output with static packet validation. It does not
write packet fixtures. It does not implement runtime reducer behavior. It does
not ingest evidence. It is not CI/default release gating. It is not release
support expansion.

The generator fails closed when `read_results` contains a non-object entry
(e.g. `null`). Malformed bounded-read input must produce bounded diagnostics,
not Python tracebacks. The generator emits a `malformed_read_result_entry`
error code, exits 1, and does not emit a packet. Non-object `read_results`
entries must never produce a successful packet. Supported claims must still
never have empty `evidence_refs`.

The static bounded-read result fixture
`docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`
exists and may be used by future packet generator tests only through a separate
generator implementation. Fixture presence is not packet generation, source
truth approval, evidence ingestion, WorkOrder mutation, or an Execution Ledger
write.

A static generated GuardianEvidencePacket fixture now exists at
`docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`.
It was produced by running the local stdout-only generator against the bounded-read
fixture and checking in only the top-level `packet` object from the generator result.
It is a static fixture, not runtime reducer output, not evidence ingestion, not
WorkOrder mutation, not an Execution Ledger write, and not release support
expansion. The fixture preserves all provenance, evidence refs with content hashes,
uncertainty with the skipped-source representation, forbidden interpretations with
the boundary label, and all authority locks false. It must be kept in sync with
the live generator output; the focused test
`tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py`
asserts structural equivalence between the static fixture and fresh generator output.

Local bounded evidence-read tooling is now available through
`make guardian-evidence-bounded-read`. Future packet generator implementation
may consume bounded read results only through a separate generator
implementation. Make target success remains not authority, not source truth
approval, not evidence ingestion, not execution, not WorkOrder mutation, and
not an Execution Ledger write. This generator contract still does not implement
packet generation.
