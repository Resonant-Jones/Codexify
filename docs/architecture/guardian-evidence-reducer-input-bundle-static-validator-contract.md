# Guardian Evidence Reducer Input-Bundle Static Validator Contract

## 1. Purpose

This contract defines static validation doctrine for JSON files shaped like a
`ReducerInputBundle`. It describes how future tooling may check shape, allowed
literals, source-reference boundaries, operator context, provenance, and
no-action guardrails before any future loader or reducer work.

## 2. Status

This is a docs-only architecture contract. It defines static validation doctrine only. It does not implement a validator.

### Implementation status

A local static validator now exists at `scripts/guardian/validate_reducer_input_bundle.py`. It validates ReducerInputBundle templates and fixtures for shape and guardrails. It reads only the bundle JSON file under validation and does not read source_ref targets, implement input-bundle loading, implement reducer behavior, or generate `GuardianEvidencePacket` output. It does not call command bus, Codex Runner, live validation, orchestration, Pi Loop, provider execution, or source mutation.

A local batch validator now exists at `scripts/guardian/validate_reducer_input_bundles.py`. It validates reducer input-bundle templates and fixtures by invoking the single-file validator logic. It reads only bundle JSON files under validation, does not read source_ref targets, implement input-bundle loading, implement reducer behavior, or generate `GuardianEvidencePacket` output, and does not call command bus, Codex Runner, live validation, orchestration, Pi Loop, provider execution, or source mutation. It is not CI/default release gating.

The [input-bundle dry-run loader contract](./guardian-evidence-reducer-input-bundle-dry-run-loader-contract.md) depends on single-file static validation before any future dry-run bundle loading. Validator success is not file-read approval, evidence ingestion, packet generation, or runtime reducer support.

The local dry-run input-bundle loader consumes the single-file validator result before constructing dry-run inputs. Validator success remains not file-read approval, evidence ingestion, packet generation, or runtime reducer support.

The local Make target now exists:
`make guardian-evidence-reducer-input-bundles-validate`. It runs
`python3 scripts/guardian/validate_reducer_input_bundles.py --json` and
validates reducer input-bundle templates and fixtures for static shape and
guardrails only. It does not read source_ref targets, implement input-bundle
loading or reducer behavior, generate `GuardianEvidencePacket` output, or call
command bus, Codex Runner, live validation, orchestration, Pi Loop, provider
execution, or source mutation. It is not CI/default release gating.

Examples:

```text
python3 scripts/guardian/validate_reducer_input_bundle.py docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json --json
python3 scripts/guardian/validate_reducer_input_bundle.py docs/architecture/templates/guardian-evidence-reducer-input-bundle-template.v1.json --json
python3 scripts/guardian/validate_reducer_input_bundles.py --json
```

It does not add persistence, ingestion, UI, or CI/default release gating. It
does not authorize execution or source mutation, and it does not implement an
input-bundle loader, make the reducer CLI read bundle files, runtime reducer
behavior, or packet generation.

Boundary summary: this contract does not implement a validator; it does not implement an input-bundle loader; it does not make the reducer CLI read bundle files; it does not implement runtime reducer behavior; it does not implement packet generation; it does not add ingestion; it does not add UI; it does not add CI/default release gating; it does not authorize execution; it does not authorize source mutation; it does not authorize Pi Loop invocation; it does not authorize provider execution; it does not authorize Codexify ingestion.

Additional boundary summary: static validation does not prove source reference truth; static validation does not authorize reading source-reference targets; static validation does not generate GuardianEvidencePacket output; static validation does not mutate WorkOrders; static validation does not write Execution Ledger entries.

## 3. Scope

The contract covers bounded input-bundle templates and static fixtures. It
does not implement an input-bundle loader, make the reducer CLI read bundle
files, implement runtime reducer behavior, or implement packet generation.

## 4. Why This Exists

An input bundle names bounded references that a future reducer might receive.
The references need a stable shape and explicit non-authority language before
future tooling can safely consume them. Static validation is a hygiene check,
not a trust decision.

## 5. Current Truth

- A pure `ReducerInputBundle` interface exists in
  `guardian/evidence_packets/reducer_contracts.py`.
- A static input-bundle template and local-tooling fixture exist.
- The reducer dry-run CLI returns diagnostics only, with `packet=null` and
  `validation_result=null`.
- No input-bundle loader, input-bundle validator, runtime reducer, or packet
  generator exists.

## 6. Validation Is Not Authority

Static validation checks shape, allowed values, and guardrail presence only.
It does not prove source reference truth or source_ref truth, authorize reading source-reference
targets, promote an input bundle to evidence authority, generate a
`GuardianEvidencePacket`, mutate WorkOrders, or write Execution Ledger
entries. Validation is not execution, ingestion, or truth approval.

## 7. Input-Bundle Files Covered

Future implementations may cover JSON files under the documented template and
fixture surfaces that declare `guardian_evidence_reducer_input_bundle.v1`:

- `docs/architecture/templates/guardian-evidence-reducer-input-bundle-template.v1.json`
- `docs/architecture/fixtures/guardian-evidence-reducer-input-bundle*.json`

## 8. Input-Bundle Files Not Covered

This contract does not cover packet fixtures, arbitrary source artifacts,
runtime request bodies, receipts, command-bus records as authority, or files
outside an explicitly bounded validation surface. The packet batch validator
does not validate input bundles.

## 9. Validator Output Shape

Future tooling should use a JSON-like result named
`GuardianEvidenceReducerInputBundleStaticValidationResult`:

```text
{
  "schema_version": "guardian_evidence_reducer_input_bundle_static_validation_result.v1",
  "validated_bundle_ref": string,
  "validator_contract_version": string,
  "result": "pass" | "pass_with_warnings" | "fail",
  "issue_count": integer,
  "issues": [
    {
      "issue_id": string,
      "severity": "error" | "warning" | "info",
      "code": string,
      "path": string,
      "message": string,
      "input_ref": string,
      "remediation_hint": string
    }
  ],
  "checked_at": string,
  "checked_by": string,
  "limits": object
}
```

The result shape is future doctrine, not an implemented runtime token or
script.

## 10. Validation Phases

A future static validator may proceed in bounded phases:

1. Parse JSON without reading any `source_ref` target.
2. Check the top-level schema and required fields.
3. Check review depth, input classes, and input object fields.
4. Check source-reference and operator-context language.
5. Check provenance, limits, template/fixture markers, and no-action boundaries.
6. Emit diagnostics for human/operator review and stop.

The validator must not execute anything, write receipts, ingest evidence, or
generate packet output.

## 11. Required Top-Level Bundle Checks

The required schema version is `guardian_evidence_reducer_input_bundle.v1`.
Every bundle must include:

- `schema_version`
- `bundle_id`
- `review_depth`
- `inputs`
- `operator_context`
- `provenance`
- `limits`

`inputs` must be a bounded list. `operator_context` must be a list of strings.
`provenance` and `limits` must be present even when a future bundle has no
inputs.

## 12. Review Depth Checks

Allowed `review_depth` values are exactly:

- `light`
- `medium`
- `high`
- `xhigh`

Review depth controls evidence handling and self-check policy, not model
personality. It does not grant authority or authorize execution.

## 13. Input Class Checks

Allowed `input_class` values are exactly:

- `static_docs`
- `static_fixtures`
- `validation_result`
- `command_run_snapshot`
- `command_run_event_snapshot`
- `receipt_metadata`
- `proof_index`
- `test_result_summary`
- `operator_supplied_context`

An input class describes the reference category. It does not assert that the
referenced artifact exists, was read, is correct, or is authoritative.

## 14. Input Object Field Checks

Every input object must include:

- `input_id`
- `input_class`
- `source_ref`
- `evidence_posture`
- `notes`

`input_id`, `input_class`, `source_ref`, and `evidence_posture` should be
strings. `notes` should be a list of bounded strings. Missing or malformed
fields are shape failures in future validation.

## 15. Source Reference Rules

`source_ref` values are references, not authorization to read files. Static
validation must not read, stat, resolve, fetch, or otherwise inspect the
referenced target. It should flag absolute paths, secret-like values, claims
that a file was read, and language that turns a reference into ingestion.

Source references should be stable, bounded, and reviewable. They should not
embed entire artifacts, credentials, access tokens, or unbounded command
output.

## 16. Operator Context Rules

Operator context must explain bounded purpose and non-authority posture. It
should state when references are symbolic or reference-only and should not
claim that a source was read unless a separate, explicit evidence process
proves that fact. Operator context is explanatory metadata, not an execution
request.

## 17. Provenance Rules

`provenance` must identify whether the file is a template or static fixture.
`template: true` is required for authoring templates. `static_fixture: true`
is required for static fixtures. Provenance records lineage and authoring
status; it does not confer trust, authority, or permission to load inputs.

## 18. Limits and Boundary Rules

`limits` must preserve non-action boundaries. At minimum, future bundles must
make clear that they do not authorize file reads, evidence ingestion, packet
generation, runtime reducer behavior, command-bus calls, Codex Runner calls,
Pi Loop invocation, source mutation, provider execution, Execution Ledger
writes, WorkOrder mutation, UI support, CI gating, or release expansion.

The bundle must not authorize execution, source mutation, Pi Loop invocation,
provider execution, or Codexify ingestion. No authority lock may be inferred
from input presence or validation status.

## 19. Template vs Fixture Rules

Templates are authoring aids and must identify themselves with
`provenance.template: true`. They are not evidence and are not packet
fixtures. Static fixtures must identify themselves with
`provenance.static_fixture: true` and must represent a bounded, reviewable
input set. A future validator may validate both surfaces, but packet fixture
validation must not silently treat templates as packets.

## 20. Pass / Fail / Warning Semantics

- `pass` means no documented error or warning was found in the checked shape
  and guardrails.
- `pass_with_warnings` means the shape is usable but a human should review
  warnings such as absolute-path risk or weak boundary language.
- `fail` means required structure, allowed literals, or mandatory guardrails
  are missing or invalid.

None of these results proves source truth, evidence sufficiency, authority,
ingestion, execution, or release readiness.

## 21. Candidate Issue Code Vocabulary

Candidate future issue codes are:

- `bundle_json_invalid`
- `bundle_schema_version_missing`
- `bundle_schema_version_unsupported`
- `bundle_required_field_missing`
- `review_depth_invalid`
- `inputs_missing`
- `input_required_field_missing`
- `input_class_invalid`
- `source_ref_missing`
- `source_ref_absolute_path_warning`
- `source_ref_secret_risk`
- `source_ref_file_read_claim`
- `operator_context_not_list`
- `provenance_missing`
- `template_marker_missing`
- `static_fixture_marker_missing`
- `limits_missing`
- `boundary_language_missing`
- `evidence_ingestion_claim_risk`
- `packet_generation_claim_risk`
- `runtime_reducer_claim_risk`
- `execution_claim_risk`
- `ci_release_gate_claim_risk`

These are candidate validator issue codes, not runtime protocol tokens, until
a future implementation promotes them through the runtime token process.

## 22. Relationship to ReducerInputBundle Contracts

The code-level contracts in `guardian/evidence_packets/reducer_contracts.py`
define pure dataclasses and allowed input classes. This document describes
future static file-validation doctrine around those shapes. It does not alter
the package, add a loader, or authorize runtime use.

## 23. Relationship to Reducer Dry-Run CLI

The local reducer dry-run CLI remains diagnostics-only. This contract does not
make `scripts/guardian/reducer_dry_run.py` read bundle files, validate bundle
files, generate packets, or load source references.

## 24. Relationship to Packet Validation

GuardianEvidencePacket static validation is a separate contract. Input-bundle
validation does not validate packet fixtures, and packet validation does not
validate input bundles. Neither promotes evidence to authority.

## 25. Relationship to Future Input-Bundle Loader

A future loader must be separately contracted. It must define whether and how
references are read, how identity and permissions bind to that read, how
errors are surfaced, and how source truth is distinguished from a symbolic
reference. This contract authorizes none of those actions.

## 26. Relationship to Runtime Reducer

Runtime reducer behavior requires a separate contract and implementation. A
valid input bundle is not runtime support, packet generation, execution
authority, or evidence ingestion.

## 27. Relationship to Execution Ledger and WorkOrder

This contract does not write Execution Ledger entries or mutate WorkOrders.
Adoption and mapping require separate explicit contracts covering identity,
authority, persistence, export, review, and failure semantics.

## 28. Relationship to UI and CI

This contract adds no UI, API route, dev-build test button, CI integration, or
default release gate. Read-only operator surfacing and CI opt-in validation
require separate contracts.

## 29. Failure Modes

Future tooling should treat malformed JSON, unsupported schema versions,
missing fields, invalid literals, absolute or secret-like references, claims
of file reads, missing provenance, and missing boundary language as explicit
diagnostics. It must stop at static reporting and must not repair, load,
execute, ingest, or mutate anything.

## 30. Future Allowed Slices

The following are future tasks only and are not implemented here:

- input-bundle static validator implementation
- input-bundle batch validator implementation
- input-bundle Make target
- reducer dry-run input-bundle loader contract
- reducer dry-run input-bundle loader implementation
- pure reducer library implementation
- packet generator contract
- packet generator implementation
- read-only operator surface contract
- Execution Ledger adoption contract
- WorkOrder mapping contract
- CI opt-in validation contract

## 31. Forbidden Interpretations

This document must not be read as runtime validator behavior, input-bundle
loading, runtime reducer behavior, packet generation, evidence ingestion,
execution support, UI support, CI/default release gating, release support
expansion, source-read approval, Pi Loop authorization, provider execution,
Codexify ingestion, WorkOrder mutation, or Execution Ledger truth.

## 32. Bottom Line

The input-bundle static validator contract defines shape and guardrail
doctrine for future human-reviewed tooling. It does not implement a validator,
loader, reducer, generator, ingestion path, execution path, persistence, UI,
or CI/release gate. Static validation is a bounded preparation check, not
authority.

### Conceptual flow

```text
ReducerInputBundle template or fixture
  -> static input-bundle validator
  -> GuardianEvidenceReducerInputBundleStaticValidationResult
  -> human/operator review
  -> future input-bundle loader, reducer, UI, Execution Ledger, or WorkOrder work only through separate contract
```

The conceptual flow does not read `source_ref` targets, execute anything,
write receipts, ingest evidence, generate `GuardianEvidencePacket` output,
mutate WorkOrders, or write Execution Ledger entries.
