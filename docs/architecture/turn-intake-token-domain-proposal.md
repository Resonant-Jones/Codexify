# Turn Intake Token Domain Proposal

Purpose: Evaluate which repeated Turn Intake Compiler and Fixture Pack values are contract-bearing enough to deserve promotion into canonical token registries later.
Classification: architecture token-domain proposal
Implementation status: docs-only proposal; no runtime tokens, registries, tests, prompt wiring, classifier behavior, or routing behavior implemented by this document
Last updated: 2026-06-29
Source anchors / governing docs:
- docs/architecture/turn-intake-compiler-contract.md
- docs/architecture/turn-intake-fixture-pack.md
- docs/architecture/README.md
- docs/architecture/00-current-state.md
- docs/architecture/canonical-token-philosophy.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/router-decision-table.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md
- docs/architecture/adr/024-context-command-and-active-connector-semantics.md

This is a proposal only. It is not an implemented token registry and does not prove runtime support.

Projection note: [fixtures/turn-intake-fixtures.v1.json](./fixtures/turn-intake-fixtures.v1.json) preserves fixture vocabulary as machine-readable candidate values. The JSON projection does not implement canonical runtime tokens, and any tokenization still requires a separate explicit task.

## Purpose

The Turn Intake Compiler Contract and Turn Intake Fixture Pack introduced repeated vocabulary around intent, authority, retrieval posture, evidence labels, mutation posture, and outcome shape.

Some of that vocabulary is just documentation language. Some of it is already contract-bearing enough that future runtime implementation should treat it as canonical token material instead of letting it drift into ad hoc strings.

This proposal separates those categories before any runtime token registry is created.

## Interpretation Rule

This document is a proposal only.

It does not define runtime support, does not create a registry, and does not authorize backend or frontend code to import these values yet.

## Why Token Discipline Applies

The Canonical Token Philosophy applies here because repeated turn-intake values are likely to become system truth surfaces later.

If these values survive into runtime implementation, code may branch on them, tests may assert them, traces and diagnostics may expose them, retrieval and action routing may depend on them, and operators may use them to distinguish safe, ambiguous, blocked, or executable turns.

That makes them dangerous to rename casually and easy for future agents to reinvent inconsistently.

## Source Vocabulary Inventory

| Vocabulary family | Example values | Current form | Token-bearing? | Proposal status |
|---|---|---|---|---|
| Interpreted intent | `conversation`, `answer_question`, `retrieve_context`, `summarize`, `draft_artifact`, `propose_action`, `execute_action`, `inspect_state`, `clarify`, `refuse_or_boundary` | repeated contract and fixture values | yes | candidate token domain |
| Authority speaker | `user`, `operator`, `runtime`, `system` | repeated contract and fixture values | yes | candidate token domain |
| Authority capability booleans | `canMutateState`, `canCallTools`, `canWriteMemory`, `canWidenRetrieval` | structural booleans in the contract | not as tokens yet | remain structural for now |
| Retrieval max scope | `conversation`, `thread`, `project`, `workspace`, `global` | repeated contract and fixture values | yes | candidate token domain |
| Evidence authority | `none`, `user_context`, `retrieved_untrusted_context`, `runtime_receipt` | repeated contract and fixture values | yes | candidate token domain |
| Actionability flags | `requiresModel`, `requiresRetrieval`, `requiresToolOrCommand`, `requiresWorldOrStateMutation`, `requiresClarification` | structural booleans in the contract | not as tokens yet | remain structural for now |
| Mutation posture | `not_allowed`, `clarify_required`, `proposal_only`, `gate_required`, `allowed_after_gate` | derived candidate vocabulary from the fixture pack | yes, if later surfaced in traces or diagnostics | needs more fixture evidence |
| Outcome | `answer`, `retrieve_then_answer`, `draft`, `propose_only`, `clarify_before_action`, `refuse`, `inspect_only`, `execute_only_after_gate` | repeated fixture expectations | yes | candidate token domain |
| Refusal / clarification reason categories | missing target, missing bounds, ambiguous authority, authority smuggling, unsupported release claim, identity boundary, memory policy block, retrieved text not authority | currently prose-heavy in fixtures | maybe | needs more fixture evidence |

## Promotion Criteria

A turn-intake value should graduate into a canonical token when most of the following are true:

- it appears in both the contract and the fixture pack
- it is likely to be asserted in tests later
- it is likely to be emitted in traces or diagnostics later
- it is likely to shape runtime branching later
- it is likely to cross backend, frontend, or shared-runtime boundaries later
- it would be dangerous to rename casually
- it is likely to be re-invented by future agents

Values should remain local fixture labels for now when they are:

- prose-only scenario text
- one-off reason wording
- human-readable explanation strings
- fixture-specific examples that do not drive branching
- derived labels that can still be computed from other contract fields without losing meaning

## Proposed Token Domains

### `TurnIntent`

These values are strong candidates for future tokenization now because they appear in both the contract and the fixture pack and are likely to drive runtime branching.

| Candidate value | Recommendation | Why |
|---|---|---|
| `conversation` | recommended now | Baseline non-action posture; likely to branch context and model behavior. |
| `answer_question` | recommended now | Common answer path; likely to shape retrieval posture. |
| `retrieve_context` | recommended now | Explicit pre-answer retrieval posture; likely to gate context assembly. |
| `summarize` | recommended now | Recurring authored-output posture with distinct context needs. |
| `draft_artifact` | recommended now | Distinct artifact-drafting posture that may affect context and output shape. |
| `propose_action` | recommended now | Must stay distinct from execution to prevent authority smuggling. |
| `execute_action` | recommended now | Dangerous boundary value; should be explicit and canonical if execution ever proceeds. |
| `inspect_state` | recommended now | Diagnostic or provenance posture likely to affect retrieval and evidence treatment. |
| `clarify` | recommended now | Important downgrade posture for ambiguous turns. |
| `refuse_or_boundary` | recommended now | Necessary boundary posture for unsupported, unsafe, or out-of-scope turns. |

### `TurnAuthoritySpeaker`

Speaker classification should never override the platform authority hierarchy. It only labels who is speaking in the turn posture; it must not convert retrieved text into instruction authority.

| Candidate value | Recommendation | Why |
|---|---|---|
| `user` | recommended now | Primary authored turn source. |
| `operator` | recommended now | Distinguishes operator-authored control surfaces from ordinary user text. |
| `runtime` | recommended now | Useful for runtime-triggered posture labels and diagnostic traces. |
| `system` | recommended now | Needed to distinguish system-triggered context or prompt surfaces from authored content. |

### `TurnRetrievalScope`

This domain maps directly onto the retrieval posture ceiling from the Retrieval Router Decision Table.

The scope is a ceiling, not permission to widen automatically.

| Candidate value | Recommendation | Why |
|---|---|---|
| `conversation` | recommended now | Bound to active thread history. |
| `thread` | recommended now | Useful for thread-local evidence without project-wide widening. |
| `project` | recommended now | Common local-retrieval ceiling for project-aware turns. |
| `workspace` | recommended now | Distinct from project scope and useful for local working-set retrieval. |
| `global` | recommended now | Only safe as an explicit broadened ceiling, never by implication. |

### `TurnEvidenceAuthority`

Evidence labels are contract-bearing because they tell the runtime and operator what kind of context is being shown.

| Candidate value | Recommendation | Why |
|---|---|---|
| `none` | recommended now | Needed for turns with no evidence payload. |
| `user_context` | recommended now | Labels authored user context. |
| `retrieved_untrusted_context` | recommended now | Needed to preserve the distinction between evidence and instruction. |
| `runtime_receipt` | recommended now | Important for trace-backed or operator-facing receipts. |

### `TurnMutationPosture`

This domain is likely contract-bearing, but it may be worth one more round of fixture evidence before runtime tokenization.

| Candidate value | Recommendation | Why |
|---|---|---|
| `not_allowed` | needs more fixture evidence | Useful as a default posture label, but often derivable from other fields. |
| `clarify_required` | needs more fixture evidence | Important downgrade posture, but it may be enough to derive from ambiguity rules for now. |
| `proposal_only` | needs more fixture evidence | Useful for plan-versus-execution separation; could be derived from intent. |
| `gate_required` | needs more fixture evidence | Important if traces or diagnostics need a named pre-execution posture. |
| `allowed_after_gate` | needs more fixture evidence | Strong execution-lane label, but only if future runtime emits it explicitly. |

### `TurnOutcome`

Outcome values are strong candidates for future tokenization because they are compact, operator-readable, and likely to cross runtime boundaries.

| Candidate value | Recommendation | Why |
|---|---|---|
| `answer` | recommended now | Canonical ordinary reply outcome. |
| `retrieve_then_answer` | recommended now | Distinguishes a retrieval-mediated answer from a direct conversational answer. |
| `draft` | recommended now | Distinct authored-artifact outcome. |
| `propose_only` | recommended now | Keeps planning separate from execution. |
| `clarify_before_action` | recommended now | Explicit ambiguity-handling outcome. |
| `refuse` | recommended now | Canonical boundary or safety outcome. |
| `inspect_only` | recommended now | Distinguishes read-only diagnostic/provenance handling. |
| `execute_only_after_gate` | recommended now | Makes the action gate explicit without claiming execution happened. |

### `TurnBoundaryReason`

Refusal and clarification reasons should stay local prose until runtime adoption proves they need a normalized registry.

Candidate reason categories worth watching:

- missing target
- missing bounds
- missing authority
- ambiguous action
- authority smuggling
- unsupported release claim
- identity boundary
- memory policy block
- retrieved text not authority
- execution gate required

At present these are better treated as prose-first fixture guidance, with future tokenization only if traces, diagnostics, or tests need machine-readable reason codes.

## Registry Placement Guidance

If these values later become runtime tokens, the most likely canonical home is the existing backend token registry boundary, with frontend mirroring only if a UI or shared-runtime surface consumes them.

Practical placement rule:

- backend canonical first
- frontend mirror only if surfaced to UI/shared runtime
- docs-only proposal remains the source of semantic guidance until a future implementation task promotes the values

Do not split the same domain across ad hoc local literals.

## Future Implementation Slices

Possible follow-on slices, once a future implementation task is authorized:

- backend token registry for promoted turn-intake values
- frontend/shared-runtime mirror for any UI-visible values
- classifier fixture tests
- trace surface mapping
- retrieval/action routing integration
- action-gate diagnostics

## Open Questions

- Which of the mutation-posture and refusal-reason values should graduate into canonical runtime tokens first?
- Should the runtime registry live in the existing protocol-token module or in a bounded turn-intake-specific registry that is mirrored where needed?
- Should `TurnMutationPosture` remain derivable, or should it become a first-class token domain if traces need explicit posture labels?
- Should `TurnBoundaryReason` become machine-readable only after trace and diagnostics requirements are proven?
- Which of the turn-intake values should be shared across backend, frontend, and diagnostics surfaces versus kept backend-only?
