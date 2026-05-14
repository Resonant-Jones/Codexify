# Flow Builder Surface Research Application

## Purpose

This note applies external Workspace Studio observations to Codexify planning. It is a research-to-architecture interpretation note only. It does not change Codexify runtime behavior, does not add schemas or routes, and does not claim any described concept is currently implemented.

The Workspace Studio document is external product research. It is not Codexify runtime truth. All Codexify-specific statements in this note are anchored to existing architecture docs (listed in [Source Inputs](#source-inputs)) unless explicitly marked as a future candidate or proposal.

## Source Inputs

### External research
- [Workspace Studio Flow Builder Surface Inspection](https://github.com/ResonantJones/codexify/blob/main/docs/research/workspace-studio-flow-builder-surface-inspection.docx) — first-pass live UI exploration, 2026-05-13

### Codexify architecture corpus
- [ADR-006: Flow Builder Elicitation Lane](./adr/006-flow-builder-elicitation-lane.md) — accepted; defines upstream `interview -> extract -> normalize -> validate -> compile -> execute` lane
- [ADR-014: Flow Builder Thread, Draft, and Receipts Contract](./adr/014-flow-builder-thread-draft-and-receipts-contract.md) — accepted; defines `GuardianThread`, `FlowDraft`, `FlowBuilderView`, `FlowRunReceipt`, and provenance rules
- [ADR Index](./adr/adr-index.md) — canonical ADR map
- [00-current-state.md](./00-current-state.md) — live operational truth; Codexify is in local-first beta hardening with no Flow Builder runtime surface in the current release promise
- [flows.md](./flows.md) — current runtime flows; chat completion, tool execution, cron
- [runtime-protocol-token-contract.md](./runtime-protocol-token-contract.md) — canonical token definitions for statuses, events, and error codes
- [data-and-storage.md](./data-and-storage.md) — current storage entities and invariants
- [system-overview.md](./system-overview.md) — current runtime components and topology

## Research-Derived Observations

The following Workspace Studio concepts were observed in the live UI and are summarized here as research inputs, not Codexify claims.

### Single Starter
Workspace Studio exposes one Starter per flow. The Starter is the trigger event or schedule. This enforces a linear entry point rather than a multi-trigger graph.

### Ordered Action Steps
Steps follow a fixed sequential order after the Starter. The model is Apple Shortcuts-style linear automation rather than arbitrary DAG authoring.

### AI Semantic Steps
AI operations appear as named, typed step types rather than generic model calls. Observed primitives include:

- **Extract** — structured extraction of named fields (action items, email addresses, sentiment, etc.) from input content; up to 7 predefined options; compiles to named output variables
- **Decide** — boolean classifier; fail-closed default-to-false when information is insufficient; used in combination with Check if for branching
- **Summarize** — summarization primitive; output is a named variable
- **Ask Gemini / Ask a Gem** — profile/persona-anchored model invocation with source control (All sources, Specific sources, Web search, Workspace); separates retrieval policy from model call
- **Recap unread emails** — domain-specific multi-message summarization

### Typed Variable Chips
Variables are displayed as colored chips in the UI. Key behaviors observed:

- Sourced from prior steps; carry source-step lineage
- Filtered by field-compatible type (email address, date, text, URL, etc.)
- Insertable via a Variables button or `@` syntax
- Not raw string interpolation; carry type metadata and compatibility rules

### Conditional Container (Check if)
Check if is a nested substep container, not a freeform graph edge. It accepts logical operators (`is true`, `AND`, `OR`) and requires at least one nested substep. The product prefers nested, readable control flow over arbitrary DAG branching as the default authoring model.

### Continuous Validation
Step cards show red issue indicators when required fields or child steps are missing. Save changes, Test run, Run, and Turn on are all gated by validation status. Validation checks structure, required values, variable compatibility, resource existence, resource access, and activation readiness. DOM-exposed validation hints surface access problems, deleted resources, and unsupported manual input.

### Test Run versus Turn on
Test run is a manual execution mode with sample inputs, separate from live activation. Turn on is live activation after validation passes. These are distinct operational states.

### Activity / Run History Implication
A run history surface is implied by the Activity panel. Per-step receipts and failure timestamps are suggested by the observed permission and scheduling surface.

### Permission and Sharing Warnings
Inline trust-boundary warnings appear for:
- third-party integrations receiving Google Account data through variables
- flows using steps that include people outside the organization
- documents inheriting sharing from parent folders
- Gem source restrictions (private Gems only, no external attachments)

## Codexify-Relevant Concept Mapping

| Workspace Studio concept | Codexify analogue today | Codexify future candidate | Implementation status | Notes |
|---|---|---|---|---|
| Single Starter | Cron trigger registration; command-bus invoke event | `Starter` primitive on `FlowDraft` | `proposed` | ADR-014 establishes `FlowDraft` as canonical artifact; Starter is not yet defined |
| Ordered Action steps | Command bus ordered run sequence; cron sequential steps | `ActionStep` ordered sequence on `FlowDraft` | `proposed` | ADR-006 proposes compile/execute lane; ordered step semantics not yet defined |
| AI semantic steps (Extract, Decide, Summarize) | Chat completion with tool-loop bounded tool call | `SemanticStep` typed primitives on `FlowDraft` | `proposed` | ADR-006 names elicitation/output as design candidates; no Flow Builder AI step implementation exists |
| Ask Gemini / Ask a Gem | Persona/profile invocation in chat completion | Profile-anchored model invocation step with source control | `proposed` | Persona Studio exists in Codexify (shell-integrated config); not yet a step-level invocation |
| Typed variable chips | Prompt variable interpolation; command-bus args | `VariableChip` / `TypedStepOutput` registry keyed by source step | `proposed` | No typed variable registry exists; command-bus uses JSON args without chip UI |
| Check if conditional container | None currently | `ConditionalContainer` structured branching on `FlowDraft` | `proposed` | ADR-006 mentions conditional logic as design space; no branching model defined |
| Continuous validation | Request/response validation; command-bus blocked runs | `ValidationIssue` taxonomy with graph-aware checks | `proposed` | No Flow Builder validation surface; cron jobs have basic schedule validation only |
| Test run | None for flow authoring | `TestRun` harness with sample inputs and ephemeral receipts | `proposed` | No flow test surface; command-bus has run events but no draft/test mode |
| Turn on (activation) | Cron job scheduling; command-bus policy | `Activation` with trigger registration and permission checks | `proposed` | Cron scheduling is the closest analogue; no flow activation model exists |
| Activity / Run history | `cron_runs` / `command_run_events` / task events | `FlowRunReceipt` per-run evidence surface | `proposed` | ADR-014 defines `FlowRunReceipt` as a canonical term; receipts are not yet implemented as first-class entities |
| Permission and sharing warnings | `command_bus` policy evaluation; OAuth connection surface | Trust-boundary warnings inline on flow steps and variable wiring | `proposed` | OAuth connections exist in Codexify; no inline flow authoring warnings |
| Variable type filtering (email, date, URL) | Prompt field typing in system prompt builder | Canonical token domains for variable types with compatibility rules | `proposed` | No variable-chip system; runtime tokens exist for request lifecycle only |

**Implementation status key:**
- `current` — proven in current Codexify runtime on `main`
- `adjacent` — related capability exists but on a different surface (e.g., cron scheduling is adjacent to activation)
- `proposed` — named in ADR or planning doc but not yet implemented
- `unknown` — neither implemented nor named in current docs; interpretation from Workspace Studio only

## Proposed Codexify Flow Builder Vocabulary

The following terms are proposed without claiming implementation. They are defined here as a vocabulary reference for future task decomposition. They align with the terminology already established in ADR-006 and ADR-014.

### FlowDraft
The canonical authored flow artifact. Already defined in ADR-014. A `FlowDraft` is not a chat transcript; it captures the flow being shaped, edited, validated, and later run. It has a Starter, ordered steps, and validation state.

### Starter
The single trigger entry point of a `FlowDraft`. The Starter may be a schedule (time-based), an event (external trigger), or a manual launch. Codexify currently has cron scheduling as a related surface, but Starter is not yet a first-class `FlowDraft` primitive.

### ActionStep
A deterministic or AI operation that follows the Starter in a `FlowDraft`. An `ActionStep` has a schema with typed inputs and named outputs. Codexify currently has command-bus tool invocations and bounded tool turns as adjacent surfaces, but no typed step registry.

### SemanticStep
An AI-anchored `ActionStep` whose behavior is determined by a named semantic intent (e.g., Extract, Decide, Summarize) rather than a raw model call. A `SemanticStep` has a structured input, a semantic intent classifier, and typed output variables. This term is not currently used in Codexify docs.

### VariableChip
A typed, source-scoped placeholder displayed in the flow authoring UI. A `VariableChip` carries a canonical type (text, email, date, URL, document reference, boolean, etc.), a source-step lineage, and compatibility rules for step field wiring. This term is not currently used in Codexify docs.

### TypedStepOutput
A named output produced by an `ActionStep` or `SemanticStep`. A `TypedStepOutput` is the canonical output artifact that backs a `VariableChip` when that output is used as an input to a downstream step. The type metadata enables field-compatibility filtering.

### ConditionalContainer
A structured branching control on a `FlowDraft`. A `ConditionalContainer` contains a condition (typically a boolean `VariableChip` or step output), a logical operator, and at least one nested substep. The condition result is evaluated at run time to determine which branch executes. This term is not currently used in Codexify docs.

### ValidationIssue
A structured validation finding attached to a step or flow. A `ValidationIssue` has a severity, a machine-readable code, and a human-readable hint. Validation issues gate TestRun and Activation. Codexify has protocol tokens for machine-readable error codes (see runtime-protocol-token-contract.md) but no Flow Builder validation issue taxonomy.

### TestRun
An ephemeral execution of a `FlowDraft` with sample inputs, run outside the live activated path. A `TestRun` produces ephemeral receipts and does not trigger side effects that affect external systems. The distinction between `TestRun` and `Activation` mirrors the workspace Studio pattern of separating manual test from live trigger registration.

### Activation
The transition of a `FlowDraft` from a saved or tested artifact to a live trigger-registered state. Activation gates on validation completeness and permission checks. Codexify has cron job activation as an adjacent surface but no flow activation model.

### RunReceipt
An immutable operational record summarizing a single run attempt. Already defined in ADR-014. A `RunReceipt` is distinct from a chat message and belongs to a `FlowDraft`'s own receipt stream. It carries trigger, startedAt, completedAt, per-step status, output variables, side-effect references, and any approval events. Codexify has `cron_runs` and `command_run_events` as adjacent surfaces, but `FlowRunReceipt` is not yet implemented.

## Non-Goals

This note does not:

- Implement any runtime behavior, schema, route, or worker
- Migrate any database schema or define new persistence models
- Implement any UI component, surface, or interaction
- Implement an autonomous agent loop or recursive tool execution
- Expand the supported beta release surface
- Claim any named concept in [Proposed Vocabulary](#proposed-codexify-flow-builder-vocabulary) is implemented on the current `main` tip
- Collapse command bus, cron, chat completion, and Flow Builder into a generic "agent" abstraction
- Introduce persona or identity ownership claims for Flow Builder entities

## Implementation Task Candidates

These are atomic future work candidates derived from the research mapping. They are ordered by dependency and do not imply a committed implementation timeline.

1. **Flow Builder vocabulary/contract note refinement** — align the terms in [Proposed Vocabulary](#proposed-codexify-flow-builder-vocabulary) with existing ADR-006 and ADR-014 terminology; produce a consolidated Flow Builder glossary note.
2. **FlowDraft schema proposal** — define the persistence shape for `FlowDraft`, its relationship to `GuardianThread`, and the origin provenance chain. Draft as a contract note; ADR needed before implementation.
3. **Typed variable-chip model proposal** — define `VariableChip` and `TypedStepOutput` with canonical type domains, source-step lineage, and compatibility rules. This likely requires a new section in the runtime-protocol-token-contract.md for variable type tokens.
4. **Validation issue taxonomy proposal** — define `ValidationIssue` severity levels, machine-readable codes, and hint surface. Align with existing protocol token doctrine.
5. **AI semantic-step contract proposal** — define `SemanticStep` as a typed step kind, map it to the elicitation lane in ADR-006, and specify how its output feeds the variable-chip registry. Include the fail-closed semantics for `Decide`-style steps.
6. **ConditionalContainer UI prototype** — define the authoring surface for `ConditionalContainer`, including condition construction, operator semantics, and substep nesting rules. Requires a separate prototype contract note.
7. **TestRun and Activation receipt model** — define the ephemeral `TestRun` harness contract and the durable `Activation` trigger registration model. `RunReceipt` is already named in ADR-014; this task fills in the test/activation distinction.
8. **Run activity / proof surface design** — define the operator-facing surface for inspecting `FlowRunReceipt` streams per draft. This is the Activity panel analogue. Must preserve the distinction between run evidence and ordinary chat history per ADR-014.

## Open Questions

1. **Decide fail-closed semantics** — In Workspace Studio, `Decide` defaults to `false` when information is insufficient. Should Codexify's `SemanticStep.Decide` fail closed (block execution), fail open (continue on default branch), or route to a review step? The fail-closed behavior favors automation safety; routing to review preserves explicit unknown state.
2. **Variable chip type domains** — Should `VariableChip` types be backed by canonical token domains (as in runtime-protocol-token-contract.md) or by a separate type system? Using the existing protocol token registry would align variable types with the broader Codexify status/event vocabulary.
3. **Command bus and cron reuse** — Which current primitives can be reused for Flow Builder execution? Cron already has scheduling and run history. Command bus already has policy evaluation and run event streaming. It may be possible to compose Flow Builder execution from these primitives rather than inventing a new execution layer.
4. **Run receipt canonical home** — Where should `FlowRunReceipt` live? ADR-014 says it belongs to the `FlowDraft`, but the persistence layer is not yet defined. Options include a dedicated `flow_run_receipts` table (alongside `cron_runs` and `command_runs`) or a derived surface over existing run event streams.
5. **User-owned provenance preservation** — ADR-014 requires origin provenance (`origin_thread_id`, `origin_message_id`, `origin_project_id`) to survive from conversation into draft and from draft into receipts. How should the export/restore path preserve this provenance chain without coupling the flow artifact to transient thread state?
6. **Trust-boundary warnings in flow authoring** — Workspace Studio surfaces inline warnings for third-party data access, external people, and inherited sharing. Should Codexify emit inline trust-boundary warnings for Flow Builder steps that read/write external connectors, or rely on the existing OAuth connection surface?
7. **Single Starter constraint** — Workspace Studio enforces exactly one Starter per flow. Should Codexify adopt the same constraint, or should multiple trigger types be allowed on a single `FlowDraft`? The single-Starter model simplifies the execution trigger surface but may limit expressiveness.
8. **Test run scope** — Should `TestRun` allow side effects that write to external systems, or should side effects be stubbed/isolated during test mode? Workspace Studio implies isolated test mode; an integration test mode could be a separate capability.

## Documentation Follow-Through

### Should this note be linked from `/docs/architecture/README.md`?

Yes. This note belongs in the Codexify architecture corpus as a research interpretation note. It should be linked from the main `README.md` alongside the existing Flow Builder ADRs (ADR-006 and ADR-014) so that future planning can find it without searching.

Suggested link location in `README.md`:

```
- [Flow Builder Surface Research Application](./flow-builder-surface-research-application.md) — research-derived concept mapping from Workspace Studio to Codexify Flow Builder vocabulary and future task candidates.
- [Flow Builder Elicitation Lane ADR](./adr/006-flow-builder-elicitation-lane.md)
- [Flow Builder Thread, Draft, and Receipts Contract ADR](./adr/014-flow-builder-thread-draft-and-receipts-contract.md)
```

### Is an ADR needed before implementation begins?

Yes. Before any implementation of the concepts described here — `FlowDraft` persistence, `VariableChip` registry, `SemanticStep` contract, `ValidationIssue` taxonomy, or `RunReceipt` surface — a separate ADR must be authored and accepted.

This note is a research interpretation, not an architectural decision. ADR-006 and ADR-014 are the governing accepted ADRs for Flow Builder. Any implementation work that expands the vocabulary defined here (e.g., defining a new `FlowDraft` schema, a new execution primitive, or a new validation surface) requires a new ADR that references both this note and the governing ADRs.

### ADR impact statement

**Classification:** No ADR impact.

This note is a documentation-only research interpretation. It does not change accepted runtime semantics, does not introduce new schemas or routes, and does not alter the release surface. ADR-006 and ADR-014 remain the governing Flow Builder ADRs. This note is compatible with both.

**Governing ADRs:**

- [ADR-006: Flow Builder Elicitation Lane](./adr/006-flow-builder-elicitation-lane.md) — defines the upstream elicitation lane; this note extends the vocabulary but does not change the lane doctrine
- [ADR-014: Flow Builder Thread, Draft, and Receipts Contract](./adr/014-flow-builder-thread-draft-and-receipts-contract.md) — defines `FlowDraft`, `FlowBuilderView`, `FlowRunReceipt`, and provenance rules; this note aligns its vocabulary with these terms and adds new candidates not yet in ADR-014

**No new ADR is authored in this task.** The task creates a research note only.