# Guardian Evidence Reducer Input-Bundle Dry-Run Loader Contract

## 1. Purpose

This contract defines a future seam for letting the existing reducer dry-run
CLI accept a `ReducerInputBundle` JSON file. It describes validation-first
loading, metadata-only mapping to reducer input objects, diagnostics-only dry
run behavior, and an explicit stop boundary.

## 2. Status

This is a docs-only contract. It does not implement an input-bundle loader,
change `reducer_dry_run.py`, or make the reducer CLI read bundle files.

Boundary summary: this contract is docs-only; it does not implement an input-bundle loader; it does not change `reducer_dry_run.py`; it does not make the reducer CLI read bundle files; it does not implement runtime reducer behavior; it does not implement packet generation; it does not add persistence; it does not add ingestion; it does not add UI; it does not add CI/default release gating; it does not authorize execution; it does not authorize source mutation; it does not authorize Pi Loop invocation; it does not authorize provider execution; it does not authorize Codexify ingestion.

### Implementation status

Local dry-run input-bundle loader behavior now exists through:

```text
python3 scripts/guardian/reducer_dry_run.py --json --input-bundle docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json
```

It validates the input-bundle JSON before constructing dry-run input objects,
reads only the input-bundle JSON file, does not read source_ref targets, maps
bundle metadata to `ReducerInputBundle` / `ReducerInputRef` objects, and calls
`dry_run_reducer` only after bundle validation passes or warns. It returns
`packet=null` and `validation_result=null`, keeps all authority locks false,
and remains diagnostics-only local tooling. It is not runtime reducer
behavior, packet generation, evidence ingestion, or release support expansion.

The packet generator contract is a separate future seam. Dry-run input-bundle
loader success is not packet generation, evidence ingestion, or authority
promotion.

See the [Guardian Evidence Packet Generator Contract](./guardian-evidence-packet-generator-contract.md) for that separate seam.

The [Guardian Evidence Bounded Read Contract](./guardian-evidence-bounded-read-contract.md)
is another separate future seam. Dry-run loader success is not bounded reading,
packet generation, evidence ingestion, or authority promotion.

The dry-run input-bundle loader remains diagnostics-only and does not read
`source_ref` targets. Bounded evidence-read tooling is a separate local script.
Dry-run loader success is not bounded reading, packet generation, evidence
ingestion, or authority promotion.

The local Make target now exists:
`make guardian-evidence-reducer-input-bundle-dry-run`. It runs:

```text
python3 scripts/guardian/reducer_dry_run.py --json --input-bundle docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json
```

It validates the input-bundle JSON before constructing dry-run input objects,
reads only the input-bundle JSON file, does not read source_ref targets, and
returns `packet=null` and `validation_result=null` with all authority locks
false. It is diagnostics-only local tooling, not runtime reducer behavior,
packet generation, evidence ingestion, CI/default release gating, or release
support expansion.

## 3. Scope

The future seam covers one input-bundle JSON file passed explicitly to a local
dry-run command. It covers the handoff from single-file static validation to
`ReducerInputBundle` and `ReducerInputRef` objects, then to the existing pure
`dry_run_reducer` skeleton. It does not add runtime reducer behavior.

## 4. Current Truth

- A reducer dry-run skeleton exists and returns diagnostics only.
- A reducer dry-run CLI exists and returns `packet=null` and
  `validation_result=null`.
- Static input-bundle template and fixture files exist.
- Single-file and batch input-bundle validators exist.
- Local Make targets exist for packet validation, reducer dry-run diagnostics,
  and input-bundle batch validation.
- No input-bundle loader exists.
- No runtime reducer implementation or packet generator exists.

## 5. Why This Exists

The input-bundle template and validators establish a bounded file shape. A
future loader needs a separate contract so accepting a file does not silently
become evidence ingestion, source reading, packet generation, or execution.

## 6. Loader Is Not Evidence Ingestion

Loader success, when implemented later, must not be evidence ingestion. A
future loader may read only the input-bundle JSON file passed to it. It must
not read `source_ref` targets, ingest evidence into Codexify durable truth, or
promote references to authority.

It must not read `source_ref` targets.

Future loader boundary summary: it must not call packet validators; it must not call command bus; it must not call Codex Runner; it must not invoke live validation; it must not invoke orchestration; it must not write receipts; it must not mutate WorkOrders; it must not write Execution Ledger entries.

## 7. Loader Is Not Packet Generation

Loader success must not be packet generation. The loader maps bundle metadata
into in-memory reducer input objects and then calls the existing diagnostics-
only dry-run skeleton. It must preserve `packet=null` and
`validation_result=null` unless a later explicit packet-generation contract
changes that boundary.

## 8. Proposed Future CLI Surface

A future implementation may add this explicit option to the existing local
CLI:

```text
python3 scripts/guardian/reducer_dry_run.py --json --input-bundle docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json
```

This command is proposed only. This contract does not change
`reducer_dry_run.py` and does not make the reducer CLI read bundle files.

## 9. Input-Bundle Validation Requirement

The future loader must run single-file input-bundle static validation before
constructing dry-run input objects. If validation returns `fail`, the loader
must stop without calling `dry_run_reducer`. A `pass` or `pass_with_warnings`
result permits the bounded metadata mapping step, but is not file-read
approval, evidence ingestion, packet generation, or runtime reducer support.

If validation returns `fail`, the loader must stop before `dry_run_reducer`.
If validation returns `fail`, the loader must stop without calling `dry_run_reducer`.

The future loader must not validate `GuardianEvidencePacket` fixtures, call
packet validators, call the batch validator as a substitute for the selected
file, or treat validation as truth approval.

## 10. Bundle-to-Reducer Mapping

After a passing single-file validation result, the future loader may construct
one `ReducerInputBundle` with:

- `bundle_id` from the JSON bundle
- `review_depth` from the JSON bundle
- `operator_context` from the JSON bundle
- `inputs` as a tuple of `ReducerInputRef` objects

Each JSON input object maps only these metadata fields:

- `input_id` -> `ReducerInputRef.input_id`
- `input_class` -> `ReducerInputRef.input_class`
- `source_ref` -> `ReducerInputRef.source_ref`
- `evidence_posture` -> `ReducerInputRef.evidence_posture`
- `notes` -> `ReducerInputRef.notes`

Mapping a string into `source_ref` does not read, resolve, fetch, or authorize
the referenced target.

## 11. Source Reference Boundary

A future loader may read only the input-bundle JSON file passed to it. It must
not read source_ref targets, execute source_ref targets, or mutate source_ref
targets. Relative paths, URLs, symbolic references, and operator notes remain
metadata until a separate contract authorizes a source-reading boundary.

## 12. Operator Context Handling

Operator context is copied as bounded metadata for the dry-run input bundle.
It is not an instruction to execute, ingest, read source artifacts, invoke
providers, or mutate state. The future loader must preserve context without
upgrading its claims or dropping its non-authority language.

## 13. Validation Result Handling

The single-file validation result should be returned as diagnostic context in
the future combined result. A failed result stops before `dry_run_reducer`.
Pass and pass-with-warnings results permit only the in-memory metadata mapping
described here. Validation success does not prove source_ref truth or claim
truth.

## 14. Dry-Run Result Handling

The future loader may call `dry_run_reducer` only after successful bundle
validation. The existing dry-run skeleton must remain the authority for the
bounded lifecycle and must return diagnostics only. The loader must not add
reduction, packet generation, validation behavior, ingestion, or execution.

## 15. Output Shape Guidance

The future loader should expose a JSON-like shape named
`GuardianEvidenceReducerInputBundleDryRunResult`:

```text
{
  "schema_version": string,
  "input_bundle_ref": string,
  "input_bundle_validation_result": object,
  "reducer_result": object,
  "packet": null,
  "validation_result": null,
  "authority_state": object,
  "limits": [string]
}
```

Required future output boundaries:

- `packet` must be `null`.
- `validation_result` must be `null`.
- `authority_state` must keep all authority locks false.
- `reducer_result.diagnostics.lifecycle_steps_completed` must remain
  `receive_bounded_evidence_input_set`, `classify_input_classes`, `stop`
  until a later explicit reducer implementation changes it.
- `limits` must state no source_ref reads, evidence ingestion, packet
  generation, runtime reducer behavior, command bus, Codex Runner, Pi Loop,
  provider execution, source mutation, WorkOrder mutation, Execution Ledger
  write, or release support expansion.

## 16. Error and Exit Semantics

The future loader should use these bounded semantics:

- Exit 0 when bundle validation is `pass` or `pass_with_warnings` and the
  dry-run returns diagnostics.
- Exit 1 when bundle validation fails.
- Exit 2 for CLI usage errors.
- Never call `dry_run_reducer` after failed bundle validation.

## 17. Relationship to ReducerInputBundle Contracts

`guardian/evidence_packets/reducer_contracts.py` defines the pure
`ReducerInputBundle` and `ReducerInputRef` interfaces and allowed input
classes. A future loader must use those contracts rather than invent a second
input shape.

## 18. Relationship to Input-Bundle Static Validator

The future loader depends on single-file static validation before any dry-run
bundle loading. Validator success is not file-read approval, evidence
ingestion, packet generation, or runtime reducer support.

## 19. Relationship to Input-Bundle Batch Validator

The batch validator remains local hygiene tooling for known templates and
fixtures. A future loader validates the one explicitly passed bundle file
before mapping it; it must not use batch discovery as an implicit load or
execution request.

## 20. Relationship to Reducer Dry-Run CLI

The existing CLI remains unchanged by this contract. A future `--input-bundle`
option would be a separate implementation slice that preserves diagnostics-
only behavior, false authority locks, and the bounded receive/classify/stop
lifecycle.

## 21. Relationship to Packet Validation

The future loader must not call packet validators or validate
`GuardianEvidencePacket` fixtures as part of bundle loading. Packet
validation remains a separate static contract and does not authorize packet
generation or execution.

## 22. Relationship to Runtime Reducer

This contract does not implement runtime reducer behavior. The future loader
only prepares bounded in-memory inputs for the existing dry-run skeleton. A
working reducer requires a separate explicit contract and implementation.

## 23. Relationship to Execution Ledger and WorkOrder

The future loader must not mutate WorkOrders or write Execution Ledger
entries. Adoption and mapping require separate contracts for identity,
authority, persistence, export, review, and failure semantics.

## 24. Relationship to UI and CI

This contract does not add persistence, ingestion, UI, API routes, dev-build
test buttons, or CI/default release gating. A future operator surface or CI
opt-in validation lane requires a separate contract.

## 25. Forbidden Interpretations

This contract is not an input-bundle loader implementation, runtime reducer,
packet generator, evidence ingestion path, execution path, source-read
approval, UI feature, CI gate, release gate, or release support expansion.
It does not authorize execution, source mutation, Pi Loop invocation, provider
execution, Codexify ingestion, command bus, Codex Runner, live validation,
orchestration, receipts, WorkOrder mutation, or Execution Ledger writes.

## 26. Future Allowed Slices

The following are future tasks only and are not implemented here:

- reducer dry-run input-bundle loader implementation
- focused loader tests
- optional Make target for dry-run with static fixture
- pure reducer implementation contract
- pure reducer implementation
- packet generator contract
- packet generator implementation
- read-only operator surface contract
- Execution Ledger adoption contract
- WorkOrder mapping contract
- CI opt-in validation contract

## 27. Bottom Line

This docs-only contract defines a future validation-first, metadata-only seam
for reducer dry-run input bundles. It does not implement an input-bundle
loader, change `reducer_dry_run.py`, make the reducer CLI read bundle files,
implement runtime reducer behavior, generate packets, add persistence or
ingestion, add UI, authorize execution, or widen CI/release support.

### Required future loader sequence

```text
1. Parse CLI arguments.
2. Read only the input-bundle JSON file.
3. Run single-file input-bundle static validation.
4. If validation result is fail, stop without calling dry_run_reducer.
5. If validation result is pass or pass_with_warnings, construct ReducerInputBundle.
6. Map each JSON input object to ReducerInputRef without reading source_ref.
7. Preserve bundle_id, review_depth, operator_context, input_id, input_class, source_ref, evidence_posture, and notes.
8. Call dry_run_reducer.
9. Return combined diagnostics.
10. Stop.
```

A future loader must not call packet validators, command bus, Codex Runner,
live validation, or orchestration; it must not write receipts, mutate
WorkOrders, or write Execution Ledger entries.
