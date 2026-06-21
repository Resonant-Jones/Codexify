# IDE Ergonomics Spec Fit Review for Codexify

Date: 2026-06-21
Author: Codex
Status: assessment report
Scope: review of `/Users/resonant_jones/Keep/ide-ergonomics/` for possible inclusion in Codexify

## Executive Recommendation

The specs are worth including in Codexify, but not as current release truth and not as an immediate IDE plugin project.

Best inclusion path:

1. Import the core product pattern as a future Codexify design note: a bounded conversation-transition card that turns selected chat/workspace spans into owner-safe draft actions.
2. Treat intent-latitude tags as the strongest first proof candidate, but only the grounded parser plus validator form, starting with `[literal]` enforcement.
3. Translate Arcanum-specific vocabulary into Codexify-native contracts: Guardian intent envelopes, FlowDraft-style draft artifacts, Workspace side surfaces, task/issue packets, and receipts.
4. Keep all runtime claims out of `00-current-state.md` until there is code, validation, and supported-path proof.

Decision posture: include as planning/design input now; defer runtime implementation until a small proof packet exists.

## Sources Reviewed

Candidate source tree:

- `/Users/resonant_jones/Keep/ide-ergonomics/README.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/PRODUCT-VIEW.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/ERGONOMICS-OPPORTUNITIES.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/SPELL-IDE-ASSISTED-ARCANUM-ROUTING.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/DISCIPLINE-CANDIDATE.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/README.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/SPEC.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/FINDINGS.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/INTENT-LATITUDE-TAGS-PRODUCT-VIEW.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/development/ARCHITECTURE.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/development/IMPLEMENTATION-LAYERING.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/intent-latitude-tags/development/WORK-PACK.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/development/mvp-validation/20260619T172822Z-two-lane-mvp/MVP-TWO-LANE-SYNTHESIS.md`
- `/Users/resonant_jones/Keep/ide-ergonomics/development/mvp-validation/20260619T172822Z-two-lane-mvp/MVP-NEXT-HANDOFF.md`

Codexify anchors:

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/codexify_workspace_surface_spec_v_1.md`
- `docs/architecture/adr/006-flow-builder-elicitation-lane.md`
- `docs/architecture/adr/014-flow-builder-thread-draft-and-receipts-contract.md`
- `docs/architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/Ops/codexify-issue-template-contract.md`
- `docs/Ops/docs-to-issue-compiler-protocol.md`

## Current Codexify Fit

Codexify's current supported reality is local-first beta hardening: local Docker Compose, local-only provider posture, chat completion, upload/embed/readback, and workspace-local retrieval. The current truth file explicitly says not to assume command bus expansion, delegation, federation, graph writes, UI dispatch, lease allocation, live agent execution, merge automation, or autonomous self-modification as release-proven.

That matters because IDE Ergonomics repeatedly touches surfaces that look executable: route cards, handoff composers, subagent previews, action buttons, and receipts. Those are valuable, but in Codexify they must enter as draft/proof surfaces first.

The best fit is not "ship IDE Ergonomics." The best fit is:

- Workspace/Guardian UX pattern: selected spans become transition candidates.
- Flow Builder/Guardian doctrine: conversation output becomes inspectable draft artifacts before execution.
- Intent Spine doctrine: user-facing action requests normalize into Guardian-owned envelopes before any dispatch.
- Docs-to-issue compiler doctrine: route suggestions can become issue/task candidates, not proof that work exists.
- Runtime token discipline: any future card states or verdicts need canonical token review before runtime use.

## What Is Worth Keeping

### 1. Bounded conversation-transition card

This is the strongest overall product pattern.

The MVP validation rejected a three-widget approach and selected a single transition card over static fixtures. That is the right shape for Codexify because it validates recognition and routing before implementation.

Codexify-native translation:

| Source idea | Codexify equivalent |
| --- | --- |
| conversation span | Guardian message span or Workspace selected artifact span |
| action candidate | transition candidate draft |
| route menu | bounded intent proposal menu |
| owner | Guardian rail, Flow Builder lane, issue/task compiler, Workspace scratchpad, or docs review lane |
| artifact preview | draft issue packet, FlowDraft outline, Scratchpad side note, handoff note, or proof-needed packet |
| receipt | draft/proof receipt, not execution evidence unless a runtime rail actually runs |

Recommended inclusion: yes, as a future design note or issue candidate.

Do not include as: current runtime support, release feature, or autonomous action surface.

### 2. Side-node capture

The side-node idea maps cleanly onto Codexify's Workspace Scratchpad and Shelf model.

Useful Codexify interpretation:

- A useful aside can be parked without changing the active thread/task.
- The parked item should preserve source span, origin thread, and classification.
- Promotion should be explicit: scratchpad note, task candidate, issue packet, FlowDraft seed, or knowledge candidate.

This is low-risk if treated as draft capture and high-risk if it silently mutates memory, current task scope, or release claims.

Recommended inclusion: yes, as Workspace/Guardian design input.

### 3. Handoff composer

The handoff composer is useful because Codexify already values thread continuity, proof boundaries, and scoped task packets.

Codexify-native fields should be:

- destination lane;
- source thread/message scope;
- summary;
- open gaps;
- constraints;
- validation needed;
- proof tier;
- whether execution is authorized;
- release-claim impact.

Recommended inclusion: yes, but as a draft/handoff artifact only.

### 4. Subagent or delegated-run preview

The preview pattern is good. The execution implication is dangerous.

Codexify current truth does not support presenting live agent execution, lease allocation, UI dispatch, merge automation, or autonomous release-ready coding-worker behavior as shipped. So the only safe form is a preview that shows role lanes, receipt requirements, context visibility, approval state, and fallback path.

Recommended inclusion: yes, as future planning UX; no runtime dispatch without separate Guardian/delegation proof.

### 5. Intent-latitude tags

This is the sharpest candidate for an isolated proof.

The spec correctly distinguishes:

- naive tags: killed as ceremony because the model merely reads an English label;
- grounded tags: meaningful only when enforced by a parser/validator outside the model.

Codexify should not import the full `[literal]` / `[goal]` / `[constraint]` surface at once. The L0 proof should be only:

- parse tagged prompt spans;
- reject malformed or unknown tags;
- normalize deterministically;
- check `[literal]` content appears verbatim in output;
- report failures honestly;
- report unsupported checks as unenforced rather than passed.

Recommended inclusion: yes, as a narrow proof-needed issue or experimental design packet.

Do not include yet:

- `[goal]` as a reliable judge-backed validator;
- `[constraint]` as enforceable unless a predicate exists;
- any claim that models understand tags;
- runtime rejection/regeneration behavior.

## What Should Not Be Imported Directly

The Arcanum terms should not be copied wholesale into Codexify docs unless Codexify is explicitly adopting Arcanum as a product-facing subsystem.

Avoid direct import of:

- `spellcraft`;
- `sigil-development`;
- `necronomicon`;
- `definitions-governance`;
- `ontology-harness`;
- `discipline-governance`;
- Arcanum route IDs as Codexify canonical tokens.

Reason: Codexify already has its own governing vocabulary: Guardian, Workspace, FlowDraft, Intent Envelope, Campaign Runner, issue packets, runtime protocol tokens, receipts, and current-state release gates. Importing a parallel vocabulary would increase cognitive load and contract drift.

Instead, preserve the underlying discipline:

- preview before execution;
- candidate before promotion;
- owner-specific artifacts;
- explicit approval before mutation;
- durable provenance;
- receipts for accepted/rejected/blocked outcomes;
- no release claim without proof.

## Architecture Impact

Classification: architecture-impacting if implemented; docs/design-only if kept as a review artifact.

Likely governing Codexify contracts:

- `00-current-state.md`: prevents premature release claims.
- ADR-006 Flow Builder Elicitation Lane: conversation-to-structure before execution.
- ADR-014 Flow Builder Thread, Draft, and Receipts Contract: separates transcript, draft, and run evidence.
- ADR-022 Guardian Intent Spine: normalizes user action requests before dispatch.
- Runtime Protocol Token Contract: governs any future status/verdict literals.
- Workspace Surface Spec v1: natural home for side notes, shelf, scratchpad, and inspector patterns.
- Docs-to-Issue Compiler Protocol: natural home for turning docs/conversation insights into task candidates.

Potential ADR need:

- No new ADR is needed for a docs-only fit review.
- A future runtime transition-card implementation likely needs either an ADR addendum or a new contract if it introduces durable transition candidates, new intent envelope fields, new receipt types, or dispatch semantics.
- Intent-latitude L0 parser/checker can probably begin as a proof-needed task without a new ADR if it is isolated from live runtime behavior.

## Decentralized / Local-First Review

Nodes:

- User laptop running Codexify local Compose.
- Browser/frontend Workspace and Guardian surfaces.
- Guardian backend and worker processes.
- Local persistence: Postgres, Redis, file-backed artifacts where applicable.
- Optional future peers or cloud relays are out of scope for first proof.

Trust boundaries:

- Device boundary: local-only mode is the current supported posture.
- User boundary: selected spans and annotations are user-authored or user-approved.
- Runtime boundary: draft surfaces must not dispatch until Guardian policy accepts an intent.
- Persistence boundary: scratch notes, transition candidates, FlowDrafts, and receipts must not collapse into chat messages.
- Network boundary: no external provider or peer sync is required for first proof.

Threat model:

- Honest-but-buggy assistant misclassifies a span or suggests the wrong route.
- User accidentally approves a route thinking it is only a preview.
- Future malicious or compromised plugin/peer tries to turn a preview into execution.
- Metadata leakage from captured spans, route labels, or handoff notes if synced later.

Default data model if pursued:

- State ownership: user owns selected spans and annotations; Guardian owns normalized intents and dispatch receipts; draft artifacts own their own provenance.
- Consistency target: local strong consistency for draft creation; eventual consistency only if future peer sync is introduced.
- Conflict policy: app-level merge or human-in-the-loop for draft artifacts; no hidden conflict resolution.
- Identity binding: actor id, source surface, thread/message scope, and approval state must be explicit.

Network reality:

- First proof should work offline.
- Retry/idempotency only matters once draft creation or intent dispatch persists.
- If transition candidates become durable, use idempotency keys based on source thread/message/span plus candidate kind.
- Backpressure is not relevant for static fixtures, but becomes relevant if automatic span detection runs on live message streams.

Security posture:

- Capability-based routing is preferable to ambient "button can do anything."
- No security-by-prompt: enforcement must live in Guardian policy, parser/validator code, and explicit approval gates.
- Metadata leakage should be called out before any sync or export path includes transition candidates.

Upgrade / compatibility:

- Do not add durable schema until the UI/proof validates the concept.
- If durable candidates are added later, version the candidate schema and receipt shape.
- Keep route kinds registry-backed; do not scatter ad hoc strings across frontend/backend.

## First Minimal Codexify Slice

Recommended first slice: Intent-latitude `[literal]` proof, because it is small, falsifiable, and does not require UI or runtime dispatch.

Task shape:

- Lane: proof-needed.
- Runtime layer: not runtime, unless wired into a validator later.
- Target surface: parser/checker fixture proof.
- Success: parser rejects malformed tags; `[literal]` intact output passes; paraphrased output fails; unsupported checks are reported as unenforced.
- Kill condition: if real model outputs never trigger a useful literal failure, keep the idea out of product work.

Second slice, only after that:

- Static conversation-transition-card fixtures.
- No backend dispatch.
- Produce markdown or JSON previews for route menu, owner, boundary, artifact preview, and blocked actions.
- Pass condition: reviewer can tell what would be drafted, what will not happen automatically, and who owns the next step.

## Decision Matrix

| Candidate | Include? | Priority | Why |
| --- | --- | --- | --- |
| Bounded conversation-transition card | Yes, design input | P1 | Strong fit with Guardian/Workspace/Flow Builder; needs fixture proof before runtime. |
| Intent-latitude `[literal]` validator | Yes, proof-needed | P1 | Small, falsifiable, local-first, no model dependency for core check. |
| Side-node capture | Yes, design input | P2 | Good Workspace Scratchpad/Shelf fit; risk is silent promotion. |
| Handoff composer | Yes, design input | P2 | Useful for task/session continuity; must stay draft-only. |
| Delegated-run preview | Yes, deferred | P3 | Product value is real, but current release truth forbids implying live dispatch. |
| Full IDE plugin | Not yet | Hold | Host feasibility and UI proof are untested. |
| Arcanum spell/discipline artifacts | Not directly | Hold | Vocabulary and lifecycle owners are not Codexify-native. |
| `[goal]` / `[constraint]` judge enforcement | Not yet | Hold | Judge-grounding is explicitly unresolved and should remain FLAG-grade. |

## Risks If Included Poorly

1. Release claim drift: action cards look like shipped execution even if they only draft.
2. Vocabulary fork: Arcanum terms compete with Guardian/Workspace/Flow Builder terms.
3. Prompt-magic trap: tags are treated as model-understood instead of validator-enforced.
4. Execution ambiguity: preview, approval, dispatch, and receipt collapse into one button.
5. Persistence ambiguity: side notes, chat history, draft artifacts, and run receipts become indistinguishable.

## Recommended Next Decision

Approve inclusion only at the concept/proof level:

1. Create a Codexify issue candidate for `Validate intent-latitude literal checker proof`.
2. Create a separate design note candidate for `Define bounded conversation-transition card fixtures`.
3. Do not update `00-current-state.md`.
4. Do not add UI dispatch, subagent spawn, task execution, or release wording.
5. Reassess after proof artifacts exist.

Bottom line: these specs contain useful Codexify-shaped ideas. The right move is selective assimilation under Codexify's existing contracts, with proof-first sequencing and no premature runtime claim.
