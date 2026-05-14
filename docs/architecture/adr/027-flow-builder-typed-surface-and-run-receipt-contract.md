---
tags:
* architecture
* adr
* flow-builder
* typed-surface
* run-receipt
* variable-chip
* validation
* semantic-step
  aliases:
* ADR-027
* Flow Builder Typed Surface and Run Receipt Contract
---

# ADR-027: Flow Builder Typed Surface and Run Receipt Contract

## Status

Accepted

## Date

2026-05-13

## Context

ADR-006 (Flow Builder Elicitation Lane) established the upstream lane from tacit expertise to validated, compiled workflow structure. ADR-014 (Flow Builder Thread, Draft, and Receipts Contract) established `GuardianThread`, `FlowDraft`, `FlowBuilderView`, and `FlowRunReceipt` as canonical contract terms with defined provenance rules. Both ADRs are accepted and are the governing base for all Flow Builder work.

A subsequent research note (`flow-builder-surface-research-application.md`) applied external Workspace Studio observations to Codexify planning and identified a set of typed workflow vocabulary candidates — `VariableChip`, `TypedStepOutput`, `SemanticStep`, `ConditionalContainer`, `ValidationIssue`, `TestRun`, `Activation` — that are not yet defined as contracts in the existing ADR corpus.

Codexify now needs a canonical contract that locks in the typed surface vocabulary, the run receipt doctrine, and the token discipline requirements before any implementation work begins. Without this contract, future work risks semantic drift, inconsistent terminology, and implicit runtime assumptions that are harder to fix after code exists.

## Problem Statement

The existing Flow Builder ADRs define the elicitation lane (ADR-006) and the thread/draft/receipt relationship (ADR-014), but they do not define:

- the typed step surface (`ActionStep`, `SemanticStep`)
- the typed variable system (`VariableChip`, `TypedStepOutput`)
- conditional control flow as a structured container
- the validation issue taxonomy
- the distinction between TestRun and Activation
- the complete RunReceipt contract
- token discipline requirements for workflow literals

Future implementation work on Flow Builder must not proceed without these contracts. Semantic drift in any of these areas would break the authoring-to-receipt chain, the provenance contract, or the token discipline that keeps Codexify's runtime honest.

## Decision

Codexify adopts a typed Flow Builder surface contract for future implementation planning. This ADR canonizes the vocabulary introduced in the research note, extends the concepts defined in ADR-006 and ADR-014, and establishes the run receipt doctrine as a binding contract for future implementation.

The canonical concept family is:

| Canonical term | Established by | Status in this ADR |
|---|---|---|
| `GuardianThread` | ADR-014 | Confirmed |
| `FlowDraft` | ADR-014 | Confirmed and extended |
| `FlowBuilderView` | ADR-014 | Confirmed |
| `FlowRunReceipt` | ADR-014 | Confirmed and extended |
| `Starter` | New | Defined here |
| `ActionStep` | New | Defined here |
| `SemanticStep` | New | Defined here |
| `VariableChip` | New | Defined here |
| `TypedStepOutput` | New | Defined here |
| `ConditionalContainer` | New | Defined here |
| `ValidationIssue` | New | Defined here |
| `TestRun` | New | Defined here |
| `Activation` | New | Defined here |

This ADR does not implement any of these concepts. It establishes the contract that future implementation must follow.

## Canonical Concept Definitions

### GuardianThread

**Meaning:** The durable conversation container for Guardian chat. The canonical authorship lane and the only canonical chat history container in this contract.

**Allowed role:** The canonical conversation substrate for Flow Builder authoring and the origin source for `FlowDraft` provenance.

**Non-goals:** Not a run container. Not a flow artifact.

**Implementation status:** `contract-only` — defined in ADR-014, confirmed here.

---

### FlowDraft

**Meaning:** The canonical authored flow artifact. A `FlowDraft` captures the flow being shaped, edited, validated, and later run. It is not a chat transcript. It holds a `Starter`, ordered steps, and a validation state.

**Allowed role:** The canonical identity-bearing artifact for a single workflow definition. Owned by the originating `GuardianThread` and its provenance chain.

**Non-goals:** Not a chat message. Not a compiled execution plan. Not a run receipt.

**Implementation status:** `contract-only` — defined in ADR-014, extended here to include the `Starter` and typed step surface.

---

### FlowBuilderView

**Meaning:** The Builder presentation of a `FlowDraft`. Its center is the graph or canvas; the chat lane is a secondary support lane.

**Allowed role:** An alternate view over one `FlowDraft`. Projects the draft for authoring and inspection.

**Non-goals:** Not the canonical flow artifact itself. Not a separate chat system.

**Implementation status:** `contract-only` — defined in ADR-014, confirmed here.

---

### FlowRunReceipt

**Meaning:** An immutable operational record summarizing a single run attempt. Distinct from ordinary chat messages. Belongs to a `FlowDraft`'s own receipt stream.

**Allowed role:** The durable proof surface for flow execution. The authoritative evidence of what happened during a run.

**Non-goals:** Not a chat message. Not a transient debug trace. Not replaceable by task events alone.

**Implementation status:** `contract-only` — defined in ADR-014, extended here with a complete field contract.

---

### Starter

**Meaning:** The single trigger entry point of a `FlowDraft`. The Starter is the only trigger surface a `FlowDraft` may have at activation time. The Starter may be a schedule (time-based), an event (external trigger), or a manual launch. Exactly one Starter is permitted per `FlowDraft`.

**Allowed role:** The execution trigger. Defines when and how a flow activates. Must be compatible with the execution engine.

**Non-goals:** Not a step. Not a variable. Not a conditional. Not a multi-trigger model.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### ActionStep

**Meaning:** A deterministic or AI operation that follows the Starter in a `FlowDraft`. An `ActionStep` has a step schema with typed inputs, required/optional field annotations, and named outputs. It is the unit of execution in the ordered step sequence.

**Allowed role:** The unit of authored workflow structure. May be deterministic or AI-backed. Composes into the ordered step sequence after the `Starter`.

**Non-goals:** Not a freeform graph node. Not a generic model call wrapper. Not a recursive agent loop.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### SemanticStep

**Meaning:** An AI-anchored `ActionStep` whose behavior is determined by a named semantic intent rather than a raw model call. Examples include classify, summarize, extract, decide, transform, and route. A `SemanticStep` has a structured input shape, a semantic intent identifier, a typed output schema, defined uncertainty behavior, and receipt metadata.

**Allowed role:** The bounded AI operation primitive. Replaces generic LLM calls with typed, inspectable semantic contracts. Feeds output into the variable-chip registry.

**Non-goals:** Not a generic planner. Not a recursive agent loop. Not an unbounded tool-call chain. Not a hidden prompt blob without an explicit output schema.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### VariableChip

**Meaning:** A typed, source-scoped placeholder for data from a prior step or Starter. Displayed in the flow authoring UI as a chip. Carries a canonical type (text, email, date, URL, document reference, boolean, etc.), a source-step lineage reference, and compatibility rules that govern which step fields can accept it.

**Allowed role:** The authoring-time reference to step outputs. Enables type-safe step wiring. Backed by a `TypedStepOutput`.

**Non-goals:** Not a raw display label. Not a string with no type metadata. Not a freeform path reference in the UI.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### TypedStepOutput

**Meaning:** A named output produced by an `ActionStep` or `SemanticStep`. The canonical output artifact that backs a `VariableChip`. A `TypedStepOutput` has a stable identifier, a source step reference, a canonical type, a display label, and compatibility rules. The type metadata enables field-compatibility filtering in the variable-chip registry.

**Allowed role:** The canonical output unit for typed step wiring. The stable truth source that `VariableChip` references.

**Non-goals:** Not a raw string. Not a step-internal ephemeral value without stable identity.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### ConditionalContainer

**Meaning:** A structured branching control on a `FlowDraft` that contains a condition (a boolean `VariableChip` or step output), a logical operator, and at least one nested substep. The condition result is evaluated at run time to determine which branch executes. The container is not a freeform graph edge or arbitrary DAG split.

**Allowed role:** The structured control-flow node. Enables readable, contained branching without requiring an arbitrary graph model.

**Non-goals:** Not an arbitrary DAG split. Not a recursive loop construct. Not a freeform edge between non-adjacent steps without a future ADR explicitly expanding the model.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### ValidationIssue

**Meaning:** A structured validation finding attached to a step or flow. A `ValidationIssue` has a severity, a machine-readable code, and a human-readable hint. Validation issues gate `TestRun` and `Activation` eligibility. Validation success does not prove execution success.

**Allowed role:** The canonical surface for validation feedback. Drives the authoring UX and the eligibility gate for test and activation.

**Non-goals:** Not an execution failure. Not a runtime error. Not a trace suppression reason. Must be canonically tokenized separately from existing runtime protocol tokens.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### TestRun

**Meaning:** An explicit execution of a `FlowDraft` or a compiled execution plan with sample inputs, run outside the live activated path. A `TestRun` produces ephemeral receipts and does not trigger durable side effects that affect external systems. It is the manual, isolated execution mode that precedes `Activation`.

**Allowed role:** The isolated, pre-activation proof surface. Validates that the authored flow executes without live side effects.

**Non-goals:** Not a live activation. Not a durable run. Not a trigger registration.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

### Activation

**Meaning:** The durable enablement of a `FlowDraft`. A valid `FlowDraft` transitions from a saved or tested artifact to a trigger-registered state. `Activation` gates on validation completeness, permission checks, and trust-boundary review. An activated flow persists its trigger subscription until explicitly deactivated.

**Allowed role:** The durable live state. Triggers are registered and the flow executes on its `Starter` schedule or event.

**Non-goals:** Not a test run. Not ephemeral. Not a one-shot execution.

**Implementation status:** `contract-only` — defined here as a new canonical term.

---

## Runtime Semantics

This section states the canonical runtime semantics that any future Flow Builder implementation must respect.

### Authoring does not equal execution

Authoring a `FlowDraft` — writing steps, wiring variables, setting conditions — produces a structured artifact, not a running workflow. Authoring changes the draft state only. It does not trigger execution, queue work, or emit receipts.

### Validation does not equal activation

A `FlowDraft` may be fully validated (zero `ValidationIssue`s) and still not be activated. Validation confirms structural correctness and completeness. Activation additionally requires permission checks, trust-boundary review, and trigger registration.

### Activation does not equal successful run

An activated flow runs when its `Starter` fires. Activation registration does not prove that the run succeeded, produced expected outputs, or completed without error. Run outcome is determined by the `RunReceipt`, not by the activation state.

### Route acceptance does not equal completion

When a future implementation routes a flow execution request, route acceptance means the request was accepted into the queue or execution pipeline. It does not mean the run completed, succeeded, or produced receipts. This mirrors the existing Codexify doctrine for chat completion: acceptance is not completion.

### Task-event publication does not equal UI receipt

When a future implementation publishes step-level or run-level events, event publication is a transport acknowledgment, not proof that a UI surface has rendered the event or the updated receipt state. This mirrors the existing Codexify doctrine for task events.

### Receipt evidence is the proof surface

The `FlowRunReceipt` is the canonical proof surface for a specific execution attempt. When implemented, it is the authoritative record of what the run did, what it produced, and what its terminal state was. It is not replaceable by logs, task events, or transient debug traces alone.

## Typed Variables and Outputs

### Variable chip contract

`VariableChip`s represent source-scoped references to prior step outputs or `Starter` payloads. A `VariableChip` must not be a raw display label only. It must carry stable identity, type metadata, and lineage.

### Typed output contract

`TypedStepOutput`s require:

- stable canonical identifier (not a transient runtime key)
- source step reference (the step that produced the output)
- canonical type drawn from a defined type domain
- display label
- compatibility rules for field wiring

### No raw path-string UX

Future implementation must not use raw path-string references as the primary user model for variable wiring. Typed chip references backed by `TypedStepOutput` identity are the required authoring model.

### Token discipline for variable types

Contract-bearing variable types and `ValidationIssue` codes must follow canonical token discipline as defined in `runtime-protocol-token-contract.md` and `canonical-token-philosophy.md`. New literal values for these domains must be added to a bounded registry before use, not invented inline.

## Semantic Step Contract

### Bounded AI primitives

AI steps must be bounded semantic primitives, not arbitrary hidden prompt blobs. Each `SemanticStep` must declare:

- expected input shape
- output shape and type
- uncertainty behavior (what happens when the step cannot produce a confident result)
- receipt metadata requirements

### Candidate examples

Candidate `SemanticStep` kinds include:

- **extract** — structured field extraction from unstructured input; output is a set of named typed variables
- **decide** — boolean classification; must explicitly define what happens on `unknown` or insufficient evidence (fail-closed default, explicit `unknown` routing, or review step routing)
- **summarize** — summarization of structured input; output is a text variable
- **classify** — categorical classification with defined label set
- **transform** — content transformation with defined input and output type
- **route** — conditional routing based on content analysis

### Uncertainty behavior

The `SemanticStep.Decide` variant must explicitly define its uncertainty behavior before runtime implementation. The research note identified two candidate strategies:

- **fail closed** — block execution or default to a safe branch when confidence is insufficient
- **route to review** — preserve an explicit `unknown` state and route to a review step or human checkpoint

A future implementation ADR must select and justify the chosen behavior. Ambiguous default behavior is not permitted.

### No generic recursive agent loops

A `SemanticStep` is not a generic planner, not a recursive agent loop, and not a multi-turn tool-call chain. It is a single, bounded, typed AI operation with an explicit input-output contract. Implementing a generic recursive agent loop under the `SemanticStep` concept is explicitly out of scope.

## Conditional Containers

### Structured control flow

A `ConditionalContainer` is a structured control-flow node on the `FlowDraft`. It contains at least one nested substep. It is not a freeform graph edge and not an arbitrary DAG split.

### Nested substeps

`ConditionalContainer` requires at least one nested substep. A container with no substeps is invalid and must produce a `ValidationIssue`.

### Default authoring model

Codexify's default Flow Builder authoring model is linear sequential steps with structured conditional containers, not arbitrary graph branching. Any future expansion to freeform DAG authoring requires a separate ADR.

### Readable execution receipts

Execution receipts for conditional branches must remain readable and attributable. Step receipts within a `ConditionalContainer` must carry the branch context so audit surfaces can reconstruct which path executed.

## Validation Contract

### First-class validation objects

`ValidationIssue`s are first-class contract objects. A `ValidationIssue` carries:

- severity (error, warning, info)
- machine-readable code (canonical token)
- human-readable hint
- step or flow scope reference

### Validation issue categories

Validation must distinguish at minimum:

- missing required fields
- incompatible variable types
- missing substeps in a `ConditionalContainer`
- inaccessible resource references
- unsupported manual input values
- deleted or unavailable referenced resources
- permission and trust-boundary risks
- structural incompleteness (e.g., no `Starter`, no steps)

### Validation gates

Validation success (zero errors) permits `TestRun` or `Activation` eligibility only. It does not prove that the flow will execute successfully, produce correct outputs, or avoid runtime errors. Validation gates are authoring-time checks, not execution guarantees.

### Token discipline for validation codes

`ValidationIssue` codes must be canonical tokens in a bounded registry, not inline string literals. This registry is distinct from the existing runtime protocol token registry. A future implementation task must define the registry shape and the machine-readable code scheme.

## Test Run, Activation, and Run Receipt

### TestRun

`TestRun` is an explicit execution against a draft or compiled execution plan without durable activation. It runs with sample inputs, may stub or isolate side effects, and produces an ephemeral run receipt that is not persisted as a durable `FlowRunReceipt`. `TestRun` validates the authored flow before the user commits to live activation.

### Activation

`Activation` is a durable enablement or subscription state for a valid `FlowDraft`. It requires:

- zero validation errors on the draft
- completed permission and trust-boundary review
- trigger registration for the `Starter`

An activated flow persists its trigger registration until explicitly deactivated. Deactivation does not delete the draft or its run history.

### FlowRunReceipt: complete field contract

When implemented, a `FlowRunReceipt` is required to carry at minimum:

| Field | Purpose |
|---|---|
| `run_id` | Stable identifier for this run attempt |
| `flow_draft_id` | Reference to the `FlowDraft` or compiled flow that was executed |
| `activation_id` | Reference to the activation that triggered this run, if applicable |
| `source_trigger` | Manual, scheduled, or event-based initiator |
| `step_receipts` | Per-step status, outputs, and error metadata |
| `command_run_ids` | Where the command bus is used, the `commandRunId` references for traceability |
| `retrieval_posture` | Where retrieval is used, the effective retrieval posture snapshot |
| `semantic_step_metadata` | Where `SemanticStep`s are used, input shape, uncertainty outcome, and output metadata |
| `provenance_links` | Origin thread/message/project references per ADR-014 provenance rules |
| `started_at` | Run start timestamp |
| `completed_at` | Run terminal timestamp when applicable |
| `terminal_state` | Canonical terminal state token (succeeded, failed, cancelled, timed_out, etc.) |
| `failure_reason` | When terminal state is non-successful, a machine-readable code and human-readable reason |

### Receipt uniqueness and immutability

A `FlowRunReceipt` is immutable once written. It may not be overwritten by a later run with the same `run_id`. A new run creates a new `run_id`. Receipt immutability is required for auditability and provenance.

### Receipt vs task events

`FlowRunReceipt` is the durable evidence surface. Task events (e.g., `task.created`, `task.completed`) are the transient lifecycle signals. A future implementation must not substitute task events for the receipt contract. Task events may inform receipt contents, but they do not replace the receipt.

## Provenance and Export/Restore

### Lineage-bearing artifacts

`FlowDraft`s, activations, and `FlowRunReceipt`s are lineage-bearing artifacts when implemented. Source thread/message links must be preserved per the provenance rules in ADR-014.

### Export/restore must not silently drop lineage

The account export/restore contract (`account-export-restore-contract.md`) applies to Flow Builder artifacts. Export must not silently drop `FlowDraft` provenance, `Activation` lineage, or `FlowRunReceipt` run history. If any of these artifacts are excluded from an export format, the exclusion must be explicit in the manifest and documented.

### Explicit artifact inclusion

A future implementation task must determine whether Flow Builder artifacts are included in the full-account export and must update the export surface table accordingly. If they are included, the export must preserve the provenance chain end-to-end.

## Permission and Identity Boundaries

### Flow Builder permission constraints

Flow Builder must not let workflow plugins mutate:

- Identity Mirror / IDDB
- persona ownership rules
- canonical runtime tokens
- message-versus-attempt identity semantics
- export/restore lineage guarantees
- queue/worker acceptance semantics

This extends the identity boundary doctrine from `self-extending-agent-plugin-system.md` and `account-export-restore-contract.md` into the Flow Builder surface.

### Permission requirements

Permissions must be explicit for:

- external data access by step types
- third-party integrations
- user data movement outside the current scope
- side effects that write to external systems

### Trust-boundary warnings

Future Flow Builder UI must expose trust-boundary warnings inline where a step can move user data outside its current scope, access third-party services, or involve people outside the account boundary. This mirrors the Workspace Studio pattern of inline security copy without requiring a full policy model.

## Non-Goals

This ADR does not:

- Implement any runtime behavior, schema, route, or worker
- Migrate any database schema or define new persistence models
- Implement any UI component, surface, or interaction
- Add any new route or API endpoint
- Add any new worker or queue
- Change command bus behavior
- Change cron behavior
- Implement an autonomous recursive agent loop
- Expand the supported beta release surface
- Claim any concept defined here is implemented on the current `main` tip

## Consequences

### Positive

- Future Flow Builder implementation work has a canonical vocabulary that prevents terminology drift.
- The run receipt contract establishes a clear proof surface before implementation begins.
- Token discipline requirements prevent ad hoc literals for workflow statuses, validation codes, and semantic step kinds.
- The conditional container model keeps the default authoring surface readable and bounded.
- Provenance and export/restore expectations are explicit, preventing silent lineage loss.

### Negative / risks

- More ceremony before implementation: each implementation task must first align to this vocabulary.
- The bounded conditional container model may limit expressiveness for users who need arbitrary graph branching; a future ADR can expand the model.
- Semantic step uncertainty behavior is not yet resolved; a future ADR must select the behavior before implementation.
- Variable type domains are not yet defined; a future implementation task must define them in the token registry.

### Vocabulary alignment required

Future Flow Builder work — including schema proposals, UI prototypes, backend contracts, and token registry extensions — must align to the vocabulary defined in this ADR. Drifting from this vocabulary without a superseding ADR is a process violation.

## Implementation Follow-Through

The following are atomic future work candidates. They do not imply a committed timeline. Each requires its own task scoping and, where noted, a separate ADR before implementation.

1. **FlowDraft schema proposal** — define the persistence shape for `FlowDraft`, its relationship to `GuardianThread`, the `Starter` surface, and the origin provenance chain. ADR required before implementation.
2. **VariableChip and TypedStepOutput contract** — define stable identity, canonical type domains, source-step lineage, and compatibility rules. Requires alignment with the runtime-protocol-token-contract.md token registry.
3. **ValidationIssue taxonomy and token registry** — define severity levels, machine-readable codes, and hint surface for all validation categories. Requires a new bounded token registry distinct from the existing runtime protocol token registry.
4. **SemanticStep contract** — define the bounded AI step primitive family, input/output schemas, and uncertainty behavior. Requires a separate ADR to resolve `Decide`-style uncertainty behavior.
5. **ConditionalContainer authoring contract** — define condition construction, operator semantics, substep nesting rules, and execution receipt shape for branch context. Requires a prototype contract note before implementation.
6. **TestRun and Activation backend contract** — define the ephemeral `TestRun` harness and durable `Activation` trigger registration model. Aligns with the existing cron and command-bus surfaces.
7. **FlowRunReceipt persistence model** — define the storage shape for receipts and the relationship to `FlowDraft`. ADR-014 establishes the term; this task fills in the persistence contract.
8. **Flow activity/proof surface** — define the operator-facing surface for inspecting `FlowRunReceipt` streams per draft. Must preserve the distinction between run evidence and ordinary chat history per ADR-014.
9. **Export/restore workflow artifact inclusion** — determine whether `FlowDraft`, `Activation`, and `FlowRunReceipt` are included in full-account export and update the export surface table accordingly.

## Documentation Follow-Through

- Update the ADR Index (`docs/architecture/adr/adr-index.md`) to include ADR-027 with title, status, and a one-sentence summary.
- Update the architecture README (`docs/architecture/README.md`) Flow Builder cluster to include ADR-027 after ADR-006 and ADR-014.
- Link `flow-builder-surface-research-application.md` as a research input note from the ADR-027 record and from the README Flow Builder cluster.
- Keep the research note classified as research input, not runtime truth.

## Links

* [[ADR Index|adr-index]]
* [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]]
* [[014-flow-builder-thread-draft-and-receipts-contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]]
* [[flow-builder-surface-research-application|Flow Builder Surface Research Application]]
* [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
* [[canonical-token-philosophy|Canonical Token Philosophy]]
* [[agent-tool-loop-contract|Agent Tool Loop Contract]]
* [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
* [[account-export-restore-contract|Account Export + Restore Contract]]
* [[flows|Critical Flows]]
* [[data-and-storage|Data and Storage]]
* [[00-current-state]]

## Notes

This ADR establishes the typed surface and run receipt contract for future Flow Builder implementation. It does not claim the runtime already ships any of the concepts defined here. ADR-006 and ADR-014 are the governing accepted ADRs. This ADR extends both without superseding them.