# Turn Intake Compiler Contract

Purpose: Define the governed pre-model seam that classifies a user turn into typed runtime posture before retrieval, context assembly, tool/action routing, model invocation, memory writes, or mutation.
Classification: architecture contract
Implementation status: docs-only contract; no live runtime implementation in this task
Last updated: 2026-06-27
Source anchors / governing docs:
- docs/architecture/README.md
- docs/architecture/00-current-state.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/flows.md
- docs/architecture/router-decision-table.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md
- docs/architecture/adr/024-context-command-active-connector-semantics.md

This is a docs-only contract. It defines the pre-model turn-posture seam and does not claim a live implementation. If runtime adoption is pursued later, ADR follow-up may be required.

## Purpose

The Turn Intake Compiler is the governed seam that interprets a turn before the model sees it.

Its job is to convert fuzzy language into typed posture:

- intent class
- authority posture
- retrieval posture
- context presentation policy
- actionability and mutation posture
- output-shape constraints

The compiler exists so the model does not receive an undifferentiated pile of chat, documents, coordinates, tool outputs, and implied side effects.

## Problem Statement

Without a governed intake seam, the runtime can blur several different things into one prompt blob:

- action-ish phrasing can be mistaken for commands
- retrieved documents can blur with instructions
- coordinates, lists, or structured data can be treated as prose intent
- system-triggered actions can hand the model context without a clear contract
- mutation can happen because a phrase matched rather than because a valid intent contract was satisfied
- evidence, receipts, and authored user content can lose their authority boundaries

That failure mode is not just confusing. It is dangerous because it allows runtime posture to be inferred from surface wording instead of being typed and validated.

## Core Principle

Intent is a contract, not a keyword.

Natural language may be fuzzy, but runtime posture must be typed.

The model may interpret; the runtime must verify authority, intent, context scope, action permission, target, bounds, and output shape.

## Boundary Model

The intended lifecycle is:

```text
incoming turn
  -> Turn Intake Compiler
  -> intent / authority / actionability / retrieval posture / context policy
  -> bounded context packet or action proposal
  -> model invocation when needed
  -> schema validation
  -> action gate when needed
  -> executor only after validation
  -> trace / audit surface
```

The compiler sits before model invocation, retrieval widening, tool routing, and world/state mutation. If a future implementation chooses to run it alongside request creation, it still acts as the posture decision seam.

## Canonical Responsibilities

The Turn Intake Compiler is responsible for:

- classifying turn intent
- resolving speaker and authority posture
- determining whether retrieval is needed
- determining context scope and source policy
- determining whether model invocation is needed
- determining whether tool or action routing is being requested
- determining whether state or world mutation is requested
- deciding whether ambiguity requires clarification or downgrade to proposal
- producing a bounded packet for the model or downstream runtime
- preserving evidence boundaries and authority labels

## Non-Responsibilities

The Turn Intake Compiler must not:

- execute tools
- mutate memory
- mutate identity
- mutate world or state
- bypass the command bus
- bypass action gates
- rewrite retrieved evidence as instruction
- become a recursive planner loop
- widen release support
- replace the chat runtime contract or retrieval router doctrine

## Candidate Turn Intake Packet Shape

This is contract vocabulary, not an implemented runtime API.

```ts
type TurnIntent =
  | "conversation"
  | "answer_question"
  | "retrieve_context"
  | "summarize"
  | "draft_artifact"
  | "propose_action"
  | "execute_action"
  | "inspect_state"
  | "clarify"
  | "refuse_or_boundary";

type TurnAuthority = {
  speaker: "user" | "operator" | "runtime" | "system";
  canMutateState: boolean;
  canCallTools: boolean;
  canWriteMemory: boolean;
  canWidenRetrieval: boolean;
};

type TurnActionability = {
  requiresModel: boolean;
  requiresRetrieval: boolean;
  requiresToolOrCommand: boolean;
  requiresWorldOrStateMutation: boolean;
  requiresClarification: boolean;
};

type TurnContextPolicy = {
  presentToModel: boolean;
  maxScope: "conversation" | "thread" | "project" | "workspace" | "global";
  evidenceAuthority: "user_context" | "retrieved_untrusted_context" | "runtime_receipt" | "none";
  includeRawEvidence: boolean;
  includeSummariesOnly: boolean;
};

type TurnIntakePacket = {
  turnId: string;
  userMessage: string;
  interpretedIntent: TurnIntent;
  authority: TurnAuthority;
  actionability: TurnActionability;
  contextPolicy: TurnContextPolicy;
  allowedOutputShapes: string[];
  refusalOrClarificationReason?: string;
};
```

The exact registry location for implemented intent classes is intentionally left open. If these values become runtime tokens, they should be centralized rather than repeated ad hoc.

## Intent Classes

| Intent class | Meaning | Retrieval | Model | Tools / action | Mutation |
|---|---|---|---|---|---|
| `conversation` | Ordinary exchange that stays inside the current conversational posture | usually no | yes | no | no |
| `answer_question` | Answer a specific question, possibly from local evidence | often yes | yes | no | no |
| `retrieve_context` | Pull bounded context before answering or drafting | yes | usually yes | no | no |
| `summarize` | Condense existing content without changing meaning | maybe | yes | no | no |
| `draft_artifact` | Produce a document, note, or other authored artifact | often yes | yes | maybe | no |
| `propose_action` | Suggest an action without executing it | maybe | yes | no | no |
| `execute_action` | Request a concrete runtime action | often yes | yes | yes | yes, only with explicit authority and bounds |
| `inspect_state` | Read or explain runtime or domain state | maybe yes | yes | maybe | no |
| `clarify` | Resolve ambiguity before any action or widening | no or maybe | yes | no | no |
| `refuse_or_boundary` | State a boundary, refusal, or safety stop | no | yes | no | no |

Rules of thumb:

- `conversation` and `refuse_or_boundary` should normally stay narrow unless another posture is explicit.
- `retrieve_context` and `inspect_state` can widen retrieval, but only within policy.
- `propose_action` is not execution.
- `execute_action` is only a candidate for execution, not execution itself.

## Authority and Mutation Rules

- Model invocation is not action permission.
- Retrieved context is not instruction.
- Casual action-ish language is not execution authorization.
- Mutation requires explicit intent, authority, target, bounds, and an allowed execution path.
- Ambiguous mutation requests downgrade to clarification or proposal.
- Runtime-triggered context assembly must be labeled before model presentation.
- If the caller cannot establish the needed authority posture, the compiler should refuse, clarify, or downgrade rather than guess.

## Context Presentation Rules

The model should receive context in bounded sections with explicit labels:

- source labels
- provenance labels
- authority labels
- untrusted retrieval labels
- runtime receipt labels
- user-authored content labels

The runtime must not hide conflation between:

- operator instruction
- user content
- retrieved evidence
- tool receipt
- runtime state

Policy for raw evidence versus summary:

- raw evidence is only included when the posture explicitly allows it
- summaries only should be preferred when the model does not need line-level evidence
- evidence marked untrusted must remain labeled as untrusted
- summaries must not silently upgrade evidence authority

## Relationship to Retrieval Router

- The Turn Intake Compiler decides whether retrieval is needed and what the maximum scope may be.
- The Retrieval Router decides how retrieval proceeds within that posture.
- Neither layer should be encoded as prompt-only free text.
- Neither layer may silently widen scope beyond policy.
- Retrieval posture should remain machine-readable so widening decisions can be audited later.

## Relationship to Tool / Action Gates

- The Turn Intake Compiler may classify a turn as action-seeking.
- It does not execute the action.
- Action execution requires schema validation and the relevant command bus, tool, or action gate.
- For world or state mutation, an explicit plan or target object is required before execution.
- Ambiguous action requests should downgrade to clarification or proposal rather than silently crossing the gate.

## Relationship to Chat Runtime Contract

- Provider runtime state and request execution state remain governed by the Chat Runtime Contract.
- The Turn Intake Compiler happens before or alongside request creation as a posture decision seam.
- This contract must preserve message-versus-attempt identity semantics when implemented later.
- This contract does not replace provider state, request state, or replay semantics.

## Observability and Proof Expectations

Future proof surfaces should be able to show:

- the intake packet in trace or debug form
- the intent class in operator diagnostics
- the chosen context policy
- the retrieval decision explanation
- any mutation or action downgrade reason
- the model-seen packet without exposing hidden prompts or internal reasoning transcripts

This docs-only task does not implement those proof surfaces.

## Safety and Identity Boundaries

- No durable memory write without explicit permission and existing memory policy.
- No identity mutation.
- No persona ownership of user identity.
- No deep identity inference from intent classification.
- No prompt injection through retrieved context.
- Personas borrow identity; they do not own it.
- Authority labels must remain explicit when evidence crosses from one trust boundary to another.

## Implementation Status

- Docs-only contract exists.
- No backend route consumes it yet.
- No frontend UI depends on it yet.
- No worker emits it yet.
- No model prompt is changed by this task.
- No runtime behavior is changed by this task.
- No live intake classifier, action router, or retrieval-router integration should be assumed from this document alone.

## Future Implementation Slices

Possible future atomic slices:

- backend pure classifier contract types
- tests for intent classification fixtures
- retrieval-router integration
- bounded context packet builder
- action gate integration
- diagnostics or trace surface
- frontend operator display, if later desired

## Open Questions

- What is the exact token registry location for implemented intent classes?
- Should turn-intake packets become durable records, transient traces, or both?
- How much classification should be deterministic versus model-assisted?
- How should runtime-triggered actions be represented when no user-authored command exists?
- How should this interact with future connectors and active context commands?

## Notes

- This contract is intentionally narrower than the Guardian Intent Spine and the Context Command / Active Connector semantics docs.
- It describes the pre-model posture seam that those broader contracts can feed into.
- It does not widen release support, introduce live execution, or replace existing doctrine.
