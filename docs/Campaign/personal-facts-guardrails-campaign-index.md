# Personal Facts Guardrails Campaign Index Proposal

## 1. Classification

- Workflow lane: architecture-impact
- Campaign status: proposed
- Implementation status: no runtime behavior changed by this document
- Primary subsystem: Personal Facts / memory lifecycle / identity boundary
- Release posture: local-first beta hardening only, no release promise expansion

## 2. Purpose

The Personal Facts system is now producing visible quarantined candidates, which proves the lifecycle is alive but also exposes noisy extraction behavior that needs guardrails before optimization. This campaign exists to build explicit, testable guardrails around the personal facts candidate lifecycle before the system scales with imported chat history and before review burden becomes unmanageable.

This document is a **Campaign Index Proposal** only. It defines scope, invariants, guardrail domains, and a proposed task sequence. It does not change runtime behavior, extractor logic, database schema, approval endpoints, retrieval behavior, or UI behavior.

## 3. Problem statement

The current personal facts extraction pipeline exhibits several classes of noise that undermine the system's reliability:

- **Sentence-fragment keys**: candidate extraction can produce keys that are syntactically partial sentences rather than structured fact statements.
- **Imported assistant prose misread as user identity**: OpenAI export import feeds the chat history stream with assistant-authored text, examples, generated prose, jokes, quoted content, and stale statements. Without source-role awareness, the extractor may treat assistant-authored language as durable user facts.
- **Confidence scores alone are insufficient**: a confidence score without source-role, provenance, shape, and eligibility gates is advisory, not authoritative.
- **Quarantine protects runtime but review burden can become high**: the quarantine/segregation model correctly prevents unverified facts from entering retrieval. However, a firehose of noisy candidates increases the review workload and erodes user trust.
- **No explicit gates before promotion**: the system needs explicit, testable guardrails that operate on candidates before they reach the promotion-eligibility boundary, not just better cleanup after extraction.

## 4. Current-truth anchors

### What is true now

- Personal facts exist as higher-level fact memory in the storage model (`personal_facts`, `personal_fact_evidence`, `personal_fact_revisions` tables per `docs/architecture/data-and-storage.md`).
- Personal fact evidence and revisions exist and must remain part of the lifecycle.
- Candidate facts must remain outside runtime use until explicitly approved (per ADR-013 Verified Personal Facts Context Injection).
- OpenAI export import into chat history exists on `main` (per `docs/architecture/00-current-state.md`).
- The quarantine model correctly prevents candidate facts from participating in retrieval, prompt assembly, or runtime behavior.

### What is not yet true

- OpenAI export import does not imply general third-party sync support.
- Current release posture remains local-first beta hardening.
- This proposal does not prove or change runtime support.
- No source-role guardrails currently gate candidate creation.
- No canonical rejection reason tokens exist for the candidate lifecycle.

### What this campaign may assume

- The personal facts tables (`personal_facts`, `personal_fact_evidence`, `personal_fact_revisions`) are stable and will not be restructured by this campaign.
- The quarantine-to-approved lifecycle is the correct contract and will not be inverted.
- OpenAI export import will continue to produce import-source labels on messages, giving the guardrail layer a source-of-truth hook.
- Personal fact persistence paths, approval endpoints, and retrieval injection seams exist and are testable.
- The account export + restore contract applies to facts, evidence, and revision lineage.

## 5. Guardrail domains

### A. Source-role and authorship guardrails

Imported assistant text, quoted text, examples, generated prose, and system-like text must not become user facts without explicit evidence that the user authored or approved the statement.

The campaign must distinguish:
- User-authored claims (first-person, in-chat user turns)
- Assistant-authored language (generated prose, explanations, examples)
- Quoted user text embedded in assistant turns
- System-level or `user_editable_context` blocks that describe user preferences but are not durable identity facts

### B. Candidate shape guardrails

Reject or quarantine-with-reason candidates whose keys are:
- Sentence fragments rather than complete statements
- Excessively long (prose paragraphs masquerading as fact keys)
- Prompt-like or instruction-like (e.g., "You are a helpful assistant who knows the user...")
- Derived from prose rather than a canonical schema

Prefer canonical fact domains over freeform key sprawl. A fact key should be a self-contained, reviewable statement about the user, not a snippet of conversation.

### C. Evidence and provenance guardrails

Every candidate must preserve enough source evidence to support review:
- Source type (chat message, imported conversation, manual entry)
- Import/source label when applicable (e.g., `chatgpt_import`, `claude_import`)
- Source text excerpt with enough context for human review
- Role (user, assistant, system, tool) when available
- Timestamp when available
- Confidence and reason metadata

No silent promotion without evidence. Evidence rows must remain auditable and must not be dropped during lifecycle transitions.

### D. Confidence and risk posture guardrails

Confidence is advisory, not authority:
- High confidence must not bypass quarantine.
- Low or ambiguous confidence should produce clearer review posture (e.g., "low confidence — verify before promotion") rather than hidden discard unless policy explicitly says discard is safe for that class.
- Confidence thresholds alone are not a substitute for source-role and shape guardrails.

### E. Runtime eligibility guardrails

Only verified, active facts are runtime-eligible:
- Candidate facts must not participate in retrieval, prompt assembly, or runtime behavior.
- Disputed facts must not participate.
- Retired, deleted, or unresolved facts must remain excluded.
- The verified-active boundary is the only runtime gate. Expanding runtime eligibility requires explicit ADR alignment.

### F. Mutation and lifecycle guardrails

Approve, edit-then-approve, dispute, retire, amend, and delete must remain auditable:
- Revisions must preserve lineage and not overwrite history silently.
- Lifecycle transitions must be recorded in `personal_fact_revisions`.
- Restoration from export must preserve the full lifecycle record.

### G. Import-aware guardrails

OpenAI export import should be treated as source material, not identity truth:
- Imported history may contain role ambiguity, assistant prose, examples, jokes, quoted text, and stale facts.
- The extractor must be more skeptical on imported data than on explicitly reviewed facts.
- Import source labels (`chatgpt_import`, `claude_import`) should be visible in the review UI.
- A confidence adjustment or flag for imported-source candidates may be appropriate if the extractor cannot distinguish authorship.

### H. UI review guardrails

Review UI should help the user sort signal from trash:
- The UI should expose why a candidate exists (source type, source excerpt, role).
- The UI should expose why a candidate is blocked, risky, or eligible for review (rejection reason, confidence posture, source-role flag).
- The UI must not imply candidate facts are trusted memory.
- Review actions (approve, edit, dispute, delete) must preserve audit lineage.

### I. Evaluation and proof guardrails

Add fixtures for:
- Good facts (clear user-authored statements)
- Noisy fragments (partial sentences, conversational snippets)
- Assistant-authored statements (generated prose, explanations, examples)
- Quoted user text embedded in assistant turns
- Stale facts (outdated claims)
- Contradictory facts (conflicting statements)
- Sensitive identity-like claims (traits, demographics, location, health)

Proof must show both positive extraction (good facts survive) and safe rejection (noisy/risky candidates are blocked or quarantined with explicit reason codes).

## 6. Proposed campaign sequence

This is a multi-task campaign. The tasks below are proposed and sequenced. They are not implemented by this document.

### Task 1: Create Personal Facts Guardrails Campaign Index Proposal

**This current docs-only task.** Creates the campaign index proposal defining scope, invariants, guardrail domains, and task sequence.

### Task 2: Add Personal Facts candidate policy contract

- **Proposed target**: `docs/architecture/personal-facts-guardrails-contract.md` or another agreed architecture location.
- **Scope**: define accepted candidate states, rejection reasons, source-role policy, canonical fact domains, and runtime eligibility invariants.
- **Architecture-impact**: yes.

### Task 3: Add extractor guardrail fixtures and tests

- **Proposed targets**: discover from current extractor/test locations.
- **Scope**: prove legitimate facts survive and noisy candidates are rejected or marked with explicit reason codes.
- **Constraint**: no runtime behavior should change before tests define the seam.

### Task 4: Implement backend candidate guardrails

- **Proposed target discovery**: extractor service, candidate creation path, personal facts persistence path.
- **Scope**: add pure validation/gating before candidate persistence or before promotion eligibility.
- **Constraint**: must use canonical reason tokens if repeated across backend/frontend/tests (per `docs/architecture/canonical-token-philosophy.md` and `docs/architecture/runtime-protocol-token-contract.md`).

### Task 5: Add review UI reason surfaces

- **Proposed target discovery**: Personal Facts settings/review components.
- **Scope**: show source, role, reason, confidence, and runtime posture clearly.
- **Constraint**: must remain token/layout compliant.

### Task 6: Add import-aware regression proof

- **Scope**: prove OpenAI export import cannot silently convert assistant prose or noisy fragments into trusted runtime facts.
- **Constraint**: should include representative imported-history fixtures.

### Task 7: Add lifecycle proof for approve/edit/dispute/retire

- **Scope**: prove approved active facts are eligible, and candidate/disputed/retired facts remain excluded.
- **Constraint**: tests must verify all lifecycle states.

## 7. ADR impact

- **Classification**: No ADR impact for this docs-only proposal.
- **Reason**: This task creates a campaign index proposal and does not change accepted runtime behavior, storage schema, retrieval behavior, or identity policy.
- **Warning**: Later implementation tasks may require ADR alignment or a new ADR if they alter the Personal Facts lifecycle, runtime eligibility semantics, source-of-truth boundaries, identity consent behavior, or export/restore lineage guarantees.
- **Governing docs/contracts consulted**:
  - `docs/architecture/00-current-state.md`
  - `docs/architecture/adr/adr-index.md`
  - `docs/architecture/README.md`
  - `docs/architecture/data-and-storage.md`
  - `docs/architecture/account-export-restore-contract.md`
  - `docs/architecture/agent-protocol-operations.md`
  - `docs/architecture/canonical-token-philosophy.md`
  - `docs/architecture/runtime-protocol-token-contract.md`
  - `docs/architecture/self-extending-agent-plugin-system.md`
  - `docs/architecture/persona-studio-spec.md`
  - `docs/architecture/kb-validity-matrix.md`
  - `docs/architecture/adr/013-verified-personal-facts-context-injection.md` (governing ADR for runtime eligibility)
  - `docs/architecture/adr/007-memory-graph-derived-write-hook.md` (governing ADR for derived candidate emission)

## 8. Invariants

These are non-negotiable rules for this campaign:

1. No durable trait inference without explicit approval.
2. Imported source text is evidence, not identity truth.
3. Candidate facts do not participate in retrieval, prompt assembly, or runtime behavior.
4. Verified active facts are the only runtime-eligible personal facts.
5. Confidence scores never override quarantine.
6. Evidence and revision lineage must not be silently dropped.
7. Assistant-authored text must not be promoted as user identity.
8. Guardrail reason labels that cross backend/frontend/tests must become canonical tokens before they spread.
9. This campaign must not widen the current beta release promise.

## 9. Proof surface

Proof expected across later tasks:

- **Unit tests** for pure guardrail classification (shape, role, confidence filters).
- **Fixture tests** for imported-history noise (assistant prose, fragments, quoted text, stale facts).
- **Backend seam tests** for candidate creation gates and promotion eligibility gates.
- **UI tests** for reason display and runtime posture labels.
- **Regression proof** that candidate, disputed, and retired facts are not runtime-injected into retrieval, prompt assembly, or provider context.
- **Docs validation** for campaign and contract updates (files exist, key assertions grepable).

## 10. Documentation follow-through

- This task creates only the campaign index proposal.
- Do not update `docs/architecture/00-current-state.md` in this task.
- Do not update `docs/architecture/README.md` in this task.
- `docs/Campaign/` has an existing convention of standalone campaign files without a central registry README. If a campaign registry convention exists, adding a link to this proposal is deferred to a later docs-hygiene task.
- No other architecture docs are modified by this task.

## 11. Non-goals

This campaign index proposal explicitly excludes:

- No extractor changes.
- No regex or LLM extraction tuning.
- No schema migration.
- No API route changes.
- No frontend component changes.
- No runtime retrieval or prompt assembly changes.
- No approval workflow behavior changes.
- No release claim expansion.
- No ADR creation in this first task.

## 12. Proposed first implementation task after this proposal

**Add a Personal Facts candidate policy contract before changing code.**

Doctrine should precede implementation because this touches identity, memory, evidence, and runtime eligibility. The policy contract should define:

- Accepted candidate states
- Rejection reason tokens
- Source-role classification policy
- Canonical fact domain taxonomy
- Runtime eligibility invariants
- Import-source treatment rules

This contract should live at `docs/architecture/personal-facts-guardrails-contract.md` (or an agreed architecture location) and should be reviewed for ADR alignment before extractor or persistence code is changed.
