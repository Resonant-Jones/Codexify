# Future Feature Spec
## Personal Facts Inbox and Anti-Poisoning Memory Controls

### Status
Draft for review

### Purpose
Define a trust-aware memory admission system that prevents externally suggested claims about the user from silently becoming durable identity or preference state.

---

## 1. Problem Statement

Recommendation poisoning becomes dangerous when repeated third-party claims, inferred traits, or model-generated restatements are treated as if they were first-party truth.

This feature establishes a hard boundary around user-related claims so the system can adapt in the moment without silently mutating durable personal memory.

### Core Requirement

**No external statement about the user may enter durable identity, preference, or personalization state without passing through a verification pipeline.**

---

## 2. Design Goal

Create a memory architecture in which:

- personalization is flexible at response time
- durable identity writes are conservative
- provenance is always attached to candidate facts
- repeated exposure increases review priority, not truth status

### Guiding Principle

**Personalization should be permissive at render time and conservative at write time.**

---

## 3. Trust Zones

User-related information must be separated into distinct trust zones.

### 3.1 Verified Personal Facts
High-trust, durable identity state.

Examples:
- preferred name
- explicitly stated preferences
- recurring constraints directly confirmed by the user
- stable project naming choices confirmed by the user

Allowed sources:
- direct user statement
- explicit user confirmation
- user-approved authoritative import

Properties:
- durable
- eligible for long-term personalization
- retrievable as canonical user state

### 3.2 Personal Facts Inbox
Quarantine layer for candidate user facts that are not yet verified.

Examples:
- externally claimed preferences
- model inferences about the user
- claims derived from third-party content
- inferred traits from observed behavior
- imported claims from documents not explicitly approved as authoritative

Properties:
- non-canonical
- reviewable
- confirmation-oriented
- never treated as verified truth by default

### 3.3 Ephemeral Behavioral Hints
Short-lived adaptation state for the current session or thread.

Examples:
- current preference for implementation detail
- current task focus
- temporary tone preference inferred from current context

Properties:
- decays automatically
- may shape output within a session
- must not silently harden into durable identity memory

---

## 4. System Rules

### Rule 1
**External claims about the user may influence immediate response behavior, but may not mutate durable identity state.**

### Rule 2
**Inference may affect session behavior, but inference may not create durable personal facts without verification.**

### Rule 3
**Repeated exposure increases review priority, not truth score.**

### Rule 4
**Assistant restatements do not count as independent evidence.**

### Rule 5
**Every user-related candidate fact must retain provenance and verification status for its full lifecycle.**

---

## 5. Ingestion Model

All incoming user-related information begins as an **observation**, not a fact.

### Pipeline Stages
1. Ingestion
2. Normalization
3. Policy Check
4. Routing
5. Optional Verification
6. Promotion or Rejection

### 5.1 Ingestion
Capture a raw observation from one of the following source types:
- direct user statement
- user-approved document
- assistant inference
- external webpage or connector result
- imported artifact
- synthesized summary

### 5.2 Normalization
Convert the observation into structured form:
- subject
- predicate
- value
- fact type
- source type
- provenance reference
- confidence
- trust tier
- timestamps

### 5.3 Policy Check
Evaluate:
- Is the claim about the user?
- Is the claim identity-shaped, preference-shaped, biographical, or task-local?
- Is the source first-party or third-party?
- Is the claim durable or ephemeral?
- Is direct promotion allowed by policy?

### 5.4 Routing
Route the candidate to exactly one destination:
- Verified Personal Facts
- Personal Facts Inbox
- Ephemeral Behavioral Hints
- Discard

---

## 6. Promotion Policy

Candidate facts may only be promoted to durable memory through allowed promotion paths.

### 6.1 Safe Promotion Paths

#### A. Direct Confirmation
The system asks the user to verify a candidate fact.

Example flow:
- candidate enters inbox
- system asks user for confirmation
- user confirms
- candidate is promoted to verified memory

#### B. Repeated First-Party Evidence
A substantially similar fact is stated by the user in multiple separate first-party contexts.

Conditions:
- evidence must be first-party
- assistant restatements do not count
- threshold logic must be explicit and reviewable

#### C. User-Approved Authoritative Import
The user explicitly marks a document or data source as authoritative for personal preferences or profile information.

### 6.2 Unsafe Promotion Paths
The system must never promote a fact because:
- many websites repeat it
- many model outputs repeat it
- retrieval surfaces it frequently
- it appears statistically likely
- another persona or agent asserted it confidently
- the system itself echoed the same claim multiple times

---

## 7. Personal Facts Inbox Requirements

The Personal Facts Inbox serves as the only gateway for non-user-originating personal claims.

### 7.1 Inbox States
- `new`
- `needs_confirmation`
- `confirmed`
- `rejected`
- `expired`
- `conflicted`

### 7.2 Inbox Actions
- request confirmation from user
- hold for corroboration
- suppress from promotion
- reject and store negative evidence
- expire after configured time window
- merge duplicates while preserving provenance

### 7.3 UX Requirements
The system should expose clear trust language for user-facing review surfaces.

Suggested labels:
- Observed, not verified
- Suggested by external context
- Needs confirmation before affecting long-term personalization
- Rejected
- Conflicted

---

## 8. Provenance Requirements

Every candidate fact must store provenance metadata.

### Minimum Required Metadata
- candidate ID
- subject ID
- predicate
- value
- fact type
- source type
- source reference
- originator
- confidence
- trust score
- verification status
- observation count
- contradiction count
- first seen timestamp
- last seen timestamp

### Example Candidate Record
```json
{
  "fact": "User prefers vendor-neutral AI architecture",
  "subject": "user",
  "fact_type": "preference",
  "source_type": "external_claim",
  "source_id": "conversation:1234:msg8",
  "originator": "assistant",
  "confidence": 0.42,
  "verification_status": "unverified",
  "observations": 3,
  "contradictions": 0,
  "first_seen_at": "2026-03-13T10:12:00Z",
  "last_seen_at": "2026-03-13T10:14:00Z"
}
```

### Provenance Rule
No user-related candidate fact may be promoted without intact provenance.

---

## 9. Risk and Detection Model

The system should score candidate facts for poisoning risk before any durable write is allowed.

### 9.1 Risk Signals
Increase poisoning risk when:
- the source is third-party
- the claim is about the user rather than the task
- the claim shapes identity, preference, or biography
- the same claim appears across low-independence sources
- wording is suspiciously templated
- the claim arrives via recommendation or discovery systems
- the assistant has previously emitted similar phrasing without user confirmation

### 9.2 Trust Signals
Reduce poisoning risk when:
- the user states the fact directly
- the user confirms the fact explicitly
- the source is a user-approved document
- the candidate is highly consistent with already verified facts
- recent first-party evidence exists

### 9.3 Suggested Scores
Each candidate may include:
- `identity_risk_score`
- `source_independence_score`
- `promotion_eligibility`

These scores should support policy decisions, not replace them.

---

## 10. Failure Modes to Defend Against

### 10.1 Echo Poisoning
A bad inference is repeated by the system and mistaken for corroboration.

Mitigation:
- do not count assistant restatements as independent observations
- maintain originator identity on all observations

### 10.2 Retrieval Laundering
A retrieved memory appears authoritative merely because it exists in storage.

Mitigation:
- surface provenance and verification status at retrieval time
- distinguish verified from inbox from ephemeral memory in retrieval APIs

### 10.3 Persona Contamination
A persona-local inference becomes canonical user truth and spreads across agents.

Mitigation:
- isolate persona-local adaptation from canonical user facts
- require canonical promotion through shared verification policy

### 10.4 UI Ambiguity
The user cannot tell whether the system knows, infers, or suspects something.

Mitigation:
- label each item as verified, inferred, suggested, rejected, or conflicted

---

## 11. Minimum Viable Implementation

The initial version should include four mandatory checks.

### 11.1 Subject Check
Determine whether the claim is about:
- the user
- another person
- the world
- the current task

Only user-directed durable claims require strict admission control.

### 11.2 Source Trust Check
Classify source as one of:
- direct user
- user-approved artifact
- assistant inference
- external web or page
- third-party connector
- generated synthesis

### 11.3 Durability Check
Classify claim as:
- ephemeral session hint
- medium-term preference candidate
- durable identity fact

### 11.4 Promotion Gate
Allow direct write to durable memory only if:
- source is direct user, or
- source is explicitly user-approved and allowed by policy

All other user-related durable candidates must route to the inbox.

---

## 12. Data Model Suggestion

```ts
type VerificationStatus =
  | "unverified"
  | "needs_confirmation"
  | "verified"
  | "rejected"
  | "expired"
  | "conflicted";

type MemoryTier =
  | "ephemeral"
  | "inbox"
  | "verified";

type SourceType =
  | "user_stated"
  | "user_approved_doc"
  | "assistant_inference"
  | "external_claim"
  | "connector"
  | "generated_synthesis";

interface PersonalFactCandidate {
  id: string;
  subjectId: string;
  predicate: string;
  value: string;
  factType: "identity" | "preference" | "biography" | "constraint";
  sourceType: SourceType;
  sourceRef: string;
  originator: string;
  confidence: number;
  trustScore: number;
  identityRiskScore?: number;
  sourceIndependenceScore?: number;
  promotionEligibility?: boolean;
  verificationStatus: VerificationStatus;
  memoryTier: MemoryTier;
  observationCount: number;
  contradictionCount: number;
  createdAt: string;
  updatedAt: string;
}
```

---

## 13. Retrieval Requirements

Any retrieval layer that returns user-related facts must preserve trust boundaries.

### Retrieval Rules
- verified memory should be queryable as canonical user state
- inbox items should only be returned when review, confirmation, or audit is relevant
- ephemeral hints should be excluded from canonical identity retrieval
- verification status and provenance must be available to downstream logic

### Retrieval Safety Requirement
The system must not collapse verified, inbox, and ephemeral memory into a single undifferentiated memory stream.

---

## 14. Non-Goals

This feature does not attempt to:
- eliminate all personalization inference
- ban short-lived adaptation
- solve general misinformation on the web
- infer identity from repeated third-party statements
- replace user confirmation with probabilistic confidence

---

## 15. Acceptance Criteria

This feature is successful if the following are true:

1. External claims about the user never write directly into durable memory.
2. Every candidate fact carries provenance and verification state.
3. Repetition of a third-party claim does not increase its truth status.
4. Assistant restatements do not count as independent evidence.
5. The Personal Facts Inbox acts as the mandatory gateway for unverified durable claims.
6. Verified memory remains cleanly separated from inbox and ephemeral memory.
7. The user can review, confirm, or reject candidate facts.
8. Retrieval surfaces distinguish verified facts from inferred or suggested ones.

---

## 16. Canonical Summary

This feature is not merely a memory system. It is a **fact admission control layer for user identity**.

### Canonical Boundary Statement
**The model may hear many things about the user. It may remember very few.**

### Canonical Architectural Statement
**Personalization is allowed to be adaptive in the moment, but durable identity writes must pass through verification.**

---

## 17. Future Extensions

Potential future additions:
- user-facing review queue for inbox facts
- contradiction resolution workflows
- policy-specific thresholds by fact type
- persona-scoped inbox partitions
- admin or audit tooling for memory promotions
- signed source attestations for trusted imports
- negative evidence storage to suppress repeated rejected claims

---

## 18. Open Questions

- What threshold, if any, should allow repeated first-party evidence to auto-promote a fact?
- Should some fact types always require explicit confirmation even when first-party repeated?
- How long should unconfirmed inbox items persist before expiration?
- Should rejected facts create durable suppression rules?
- How should cross-persona or cross-agent evidence be handled when provenance differs but subject is the same?
- Should user-approved imports be globally authoritative or scoped by source type?

