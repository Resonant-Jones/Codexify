# CX-AGENT-001: Thread Drift Detector

**Status:** Draft for implementation  
**Version:** 0.1.0  
**Last Updated:** 2026-05-06  
**Owner:** Codexify / Resonant Constructs  
**Suggested Repo Path:** `docs/specs/agents/CX-AGENT-001-thread-drift-detector.md`  
**Related Systems:** Codexify IDDB, ContextBroker, ModelRouter, PersonaEngine, VectorStore, Agent Runtime, Control Surface

---

## 1. Summary

The **Thread Drift Detector** is the first official Codexify agent loop for proactive assistance.

Its purpose is to detect unresolved obligations, missed follow-ups, tense conversational drift, and implied next steps across user communication streams, then prepare a low-risk proposal or draft without requiring the user to remember, prompt, or manually assign the task.

This loop is intentionally narrow. It does not attempt to “manage the user’s life.” It detects a specific class of friction: **conversation-derived obligations that are easy to forget but costly to miss.**

The loop should feel less like an agent dashboard and more like a quiet assistant noticing:

> “This thread looks unresolved. You said you would follow up after the meeting. I drafted a short reply. Want to review it?”

---

## 2. Product Thesis

Codexify agents should not create another management layer.

The system should reduce cognitive load by identifying moments when a user would benefit from assistance, while preserving user agency, consent, and review boundaries.

The Thread Drift Detector exists to validate a central Codexify principle:

> A tool waits for the user to remember it. An assistant reduces what the user has to remember.

---

## 3. Goals

### 3.1 Primary Goals

- Detect likely follow-ups, unresolved asks, and stale commitments from communication context.
- Convert noisy communication streams into structured candidate obligations.
- Score candidates by salience before interrupting the user.
- Draft low-risk next actions when confidence and permissions allow.
- Require user review before any external action is taken.
- Capture user feedback to improve future salience and personalization.

### 3.2 Secondary Goals

- Establish the reusable architecture for future Codexify agent loops.
- Provide a clear permission ladder for scoped agent autonomy.
- Create a measurable “proactivity without annoyance” baseline.
- Validate ContextBroker, ModelRouter, memory retrieval, and proposal UI working together.

---

## 4. Non-Goals

This agent loop must not:

- Send emails autonomously in MVP.
- Modify calendars autonomously in MVP.
- Purchase, book, subscribe, delete, archive, or irreversibly mutate external systems.
- Operate as a general-purpose life manager.
- Surface every detected task to the user.
- Create an “agent inbox” that the user must manage.
- Infer durable personal traits without explicit user approval.
- Collapse identity boundaries between personas, projects, or users.

---

## 5. Core Use Case

### Scenario

A user receives or participates in a communication thread where an obligation is implied:

- “I’ll send that over tomorrow.”
- “Can you follow up after the call?”
- “Let’s revisit this next week.”
- “I still haven’t received the file.”
- “We need your approval before Friday.”
- A tense thread appears to require a careful response.

The user may forget, delay, or miss the obligation. The agent detects the unresolved thread, evaluates whether it matters, and proposes a next step.

### Desired Output

A contextual proposal such as:

> “This thread may need a follow-up. You said you would send the revised copy after the meeting, and there has been no reply since Monday. I drafted a short response for review.”

---

## 6. Runtime Architecture

```text
Source Event
  -> Event Normalizer
  -> Candidate Obligation Detector
  -> Context Enrichment
  -> Salience Engine
  -> Permission Gate
  -> Proposal / Draft Generator
  -> User Review Surface
  -> Feedback Capture
  -> Memory + Audit Update
```

### 6.1 Components

| Component | Responsibility |
|---|---|
| Source Event | Raw event from email, calendar, chat, document, or imported conversation. |
| Event Normalizer | Converts source-specific payloads into a stable internal event format. |
| Candidate Obligation Detector | Identifies possible follow-ups, unresolved asks, tense threads, and implied tasks. |
| Context Enrichment | Adds memory, project, persona, relationship, and temporal context. |
| Salience Engine | Decides whether the candidate is worth storing, digesting, suggesting, or drafting. |
| Permission Gate | Enforces domain-level trust boundaries. |
| Proposal Generator | Creates a human-reviewable next step. |
| Review Surface | Presents the proposal in a low-friction UI. |
| Feedback Capture | Records user decisions and correction signals. |
| Audit Update | Writes traceable logs for explainability and debugging. |

---

## 7. MVP Scope

### 7.1 Included in MVP

- Email or imported communication thread ingestion.
- Candidate obligation detection.
- Salience scoring.
- Level 1 to Level 3 permissions only:
  - Read
  - Suggest
  - Draft
- Draft reply generation.
- User review UI.
- Feedback actions:
  - Helpful
  - Not important
  - Wrong context
  - Too soon
  - Too late
  - Do not surface threads like this
- Audit logging.

### 7.2 Excluded from MVP

- Auto-send.
- Calendar mutation.
- Shopping, booking, payments, subscriptions.
- Cross-user delegation.
- Multi-agent orchestration.
- Persistent background execution beyond event polling or scheduled scans.
- Unbounded screen observation.

---

## 8. Trigger Sources

### 8.1 Initial Sources

| Source | Trigger Event |
|---|---|
| Email Connector | New unread message, reply received, thread stale beyond threshold. |
| Imported Chat Logs | New indexed conversation chunk containing obligation language. |
| Calendar Connector | Meeting ended, meeting upcoming, follow-up window opened. |
| Codexify Memory | Existing memory retrieved as relevant to the thread. |

### 8.2 Future Sources

| Source | Trigger Event |
|---|---|
| Browser Context | User repeatedly visits related project pages or form pages. |
| Local Files | Recently edited documents imply pending delivery. |
| Task Systems | Open task remains unresolved after related communication. |
| Voice Notes | User records a commitment or reminder-like statement. |

---

## 9. Data Contracts

### 9.1 SourceEvent

```ts
export type SourceType = "email" | "calendar" | "chat" | "document" | "browser";

export interface SourceEvent {
  id: string;
  sourceType: SourceType;
  sourceId: string;
  userId: string;
  personaId?: string;
  projectId?: string;
  occurredAt: string;
  receivedAt: string;
  actor?: {
    name?: string;
    email?: string;
    relationshipHint?: string;
  };
  title?: string;
  bodyText: string;
  metadata?: Record<string, unknown>;
}
```

### 9.2 CandidateObligation

```ts
export type DetectedIntent =
  | "follow_up"
  | "reply_needed"
  | "schedule"
  | "send_file"
  | "approval_needed"
  | "clarify"
  | "deescalate"
  | "task";

export type Urgency = "low" | "medium" | "high";

export interface CandidateObligation {
  id: string;
  sourceEventId: string;
  sourceType: SourceType;
  detectedIntent: DetectedIntent;
  confidence: number;
  urgency: Urgency;
  relatedProjectId?: string;
  relatedPersonaId?: string;
  suggestedNextStep: string;
  evidence: EvidenceSnippet[];
  detectedAt: string;
  expiresAt?: string;
}

export interface EvidenceSnippet {
  sourceId: string;
  quote: string;
  timestamp?: string;
  relevance: number;
}
```

### 9.3 ContextEnvelope

```ts
export interface ContextEnvelope {
  userId: string;
  personaId?: string;
  projectId?: string;
  sourceEvent: SourceEvent;
  candidate: CandidateObligation;
  retrievedMemories: RetrievedMemory[];
  relatedThreads: RelatedThreadSummary[];
  calendarSignals?: CalendarSignal[];
  userPreferenceHints?: UserPreferenceHint[];
}

export interface RetrievedMemory {
  id: string;
  text: string;
  tags: string[];
  relevance: number;
  source?: string;
  createdAt?: string;
}

export interface RelatedThreadSummary {
  id: string;
  summary: string;
  relevance: number;
  lastActivityAt?: string;
}

export interface CalendarSignal {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
  relevance: number;
}

export interface UserPreferenceHint {
  key: string;
  value: string;
  confidence: number;
}
```

### 9.4 SalienceResult

```ts
export type SalienceAction = "store" | "digest" | "suggest" | "draft";

export interface SalienceResult {
  candidateId: string;
  score: number;
  action: SalienceAction;
  reasons: string[];
  penalties: string[];
  computedAt: string;
}
```

### 9.5 AgentProposal

```ts
export type ProposedAction =
  | "draft_reply"
  | "create_reminder"
  | "suggest_follow_up"
  | "ignore";

export interface AgentProposal {
  id: string;
  candidateId: string;
  title: string;
  summary: string;
  proposedAction: ProposedAction;
  draft?: string;
  requiresApproval: true;
  confidence: number;
  salienceScore: number;
  evidence: EvidenceSnippet[];
  createdAt: string;
  expiresAt?: string;
}
```

### 9.6 UserFeedback

```ts
export type FeedbackSignal =
  | "helpful"
  | "not_important"
  | "wrong_context"
  | "too_soon"
  | "too_late"
  | "bad_draft"
  | "do_not_surface_similar";

export interface UserFeedback {
  proposalId: string;
  userId: string;
  signal: FeedbackSignal;
  note?: string;
  createdAt: string;
}
```

### 9.7 AgentAuditLog

```ts
export interface AgentAuditLog {
  id: string;
  agentLoopId: "thread_drift_detector.v1";
  userId: string;
  sourceEventId: string;
  candidateId?: string;
  proposalId?: string;
  stage:
    | "observed"
    | "candidate_detected"
    | "context_enriched"
    | "salience_scored"
    | "permission_checked"
    | "proposal_created"
    | "user_feedback_recorded";
  summary: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}
```

---

## 10. Detection Logic

### 10.1 Candidate Signals

The detector should look for signals including:

| Signal Type | Examples |
|---|---|
| Commitment Language | “I’ll send,” “I’ll follow up,” “I can get that to you.” |
| Request Language | “Can you,” “Please send,” “Could you confirm.” |
| Temporal Language | “By Friday,” “tomorrow,” “next week,” “after the meeting.” |
| Staleness | Thread has no reply after expected response window. |
| Tension | Escalating tone, complaint language, repeated unanswered asks. |
| Approval Dependency | “Need your sign-off,” “waiting on approval.” |
| Attachment Gap | Message references a file, but no file is present or sent. |
| Meeting Follow-Up | Meeting ended and related thread has implied action items. |

### 10.2 Detector Output Rule

The detector must output only **candidate obligations**, never direct user-facing notifications.

This prevents over-eager proactivity and allows salience, permissions, and feedback history to determine whether anything should surface.

---

## 11. Salience Scoring

### 11.1 Inputs

| Input | Description |
|---|---|
| Confidence | Model confidence that an obligation exists. |
| Urgency | Deadline pressure or time sensitivity. |
| Relationship Weight | Importance of sender or thread participants. |
| Project Relevance | Whether the thread maps to an active project. |
| Recency Pressure | Whether the thread is approaching or passing a likely response window. |
| User Feedback History | Prior corrections for similar threads. |
| Notification Budget | Whether the user has already received too many nudges recently. |

### 11.2 Baseline Formula

```ts
salience =
  confidence * 0.35 +
  urgencyWeight * 0.25 +
  relationshipWeight * 0.15 +
  projectRelevance * 0.15 +
  recencyPressure * 0.10;
```

### 11.3 Thresholds

| Score | Action | Behavior |
|---:|---|---|
| `< 0.45` | Store | Record silently for later retrieval. |
| `0.45 - 0.65` | Digest | Include in daily or contextual digest. |
| `0.65 - 0.80` | Suggest | Surface concise suggestion. |
| `> 0.80` | Draft | Prepare a draft for review. |

### 11.4 Penalties

Apply score penalties for:

- Similar proposal recently dismissed.
- Low-quality source text.
- Ambiguous sender identity.
- Conflicting calendar or memory evidence.
- User currently in focus mode.
- Too many agent suggestions in the current notification window.
- User previously marked similar threads as not important.

---

## 12. Permission Ladder

Permissions must be scoped by domain, connector, persona, and project.

| Level | Name | Capability |
|---:|---|---|
| 1 | Read | Agent can inspect permitted source context. |
| 2 | Suggest | Agent can surface a proactive suggestion. |
| 3 | Draft | Agent can prepare a draft or next step for user review. |
| 4 | Act With Confirmation | Agent can prepare external action but requires explicit approval before execution. |
| 5 | Autonomous | Agent can execute trusted recurring actions without per-action approval. |

### MVP Limit

The Thread Drift Detector MVP must not exceed **Level 3: Draft**.

---

## 13. Runtime Flow

### 13.1 Observe

1. Connector emits `SourceEvent`.
2. Event Normalizer validates and stores the event.
3. Event is queued for agent evaluation.

### 13.2 Detect

1. Candidate Obligation Detector receives normalized event.
2. Detector extracts obligation signals.
3. Detector produces zero or more `CandidateObligation` records.
4. Detector writes audit log.

### 13.3 Enrich

1. ContextBroker retrieves related memories, projects, threads, and calendar signals.
2. ContextBroker builds `ContextEnvelope`.
3. Identity boundaries are enforced before context is passed to the model.

### 13.4 Score

1. Salience Engine computes `SalienceResult`.
2. Notification budget and prior feedback penalties are applied.
3. Candidate is routed to store, digest, suggest, or draft.

### 13.5 Propose

1. Permission Gate checks domain trust level.
2. Proposal Generator creates `AgentProposal` if allowed.
3. Proposal is shown to the user only if salience and permissions allow.

### 13.6 Feedback

1. User accepts, dismisses, edits, or marks proposal feedback.
2. Feedback updates future salience behavior.
3. Audit log records the result.

---

## 14. UI Contract

### 14.1 Proposal Card

A proposal should contain:

- Clear title.
- One-sentence summary.
- Why it surfaced.
- Evidence snippets.
- Draft preview if applicable.
- Actions:
  - Review Draft
  - Remind Me Later
  - Not Important
  - Ignore
  - Do Not Surface Similar

### 14.2 Tone

The UI should avoid alarm language unless urgency is clearly high.

Preferred style:

> “This thread may need a follow-up.”

Avoid:

> “Urgent: You failed to respond.”

### 14.3 No Agent Inbox Rule

The UI must not become a persistent list of unmanaged agent chores.

If multiple low-priority candidates exist, group them into a digest rather than creating individual cards.

---

## 15. API Surface

These endpoint names are illustrative and may be adapted to existing repo conventions.

```http
POST /api/agent-loops/thread-drift/observe
```

Accepts a normalized or source-specific event for evaluation.

```http
GET /api/agent-proposals?status=pending
```

Returns pending user-reviewable proposals.

```http
POST /api/agent-proposals/:proposalId/feedback
```

Records user feedback signal.

```http
POST /api/agent-proposals/:proposalId/approve
```

Approves a draft or proposed next step. For MVP, approval may only mark the draft as accepted or copy it to a review surface. It must not send externally unless a separate action path exists with explicit user confirmation.

```http
POST /api/agent-proposals/:proposalId/dismiss
```

Dismisses the proposal and updates feedback history.

---

## 16. Persistence Model

Minimum persistent records:

| Table / Collection | Purpose |
|---|---|
| `source_events` | Normalized incoming events. |
| `candidate_obligations` | Detected unresolved commitments or implied tasks. |
| `agent_salience_results` | Scoring outputs and routing decisions. |
| `agent_proposals` | User-facing suggestions and drafts. |
| `agent_feedback` | User correction and preference signals. |
| `agent_audit_logs` | Traceability and debugging. |

---

## 17. Safety, Privacy, and Identity Boundaries

### 17.1 Required Guardrails

- Never send, delete, archive, purchase, book, or externally mutate without explicit user approval.
- Do not infer durable user traits from a single thread.
- Do not share context across personas unless explicitly allowed.
- Do not use one project’s memory to act in another project unless cross-project permission exists.
- Preserve evidence snippets for explainability.
- Make all proposals dismissible.
- Allow the user to reduce or disable proactive behavior by domain.

### 17.2 Data Minimization

Only retrieve context necessary to evaluate the candidate obligation.

The agent should prefer:

1. Current thread.
2. Related recent thread summaries.
3. Project-linked memories.
4. User-approved preference hints.

Avoid broad memory retrieval unless the candidate cannot be evaluated safely without it.

---

## 18. Failure Modes and Mitigations

| Failure Mode | Description | Mitigation |
|---|---|---|
| False Urgency | Agent overstates importance. | Require evidence snippets and deadline confidence. |
| Over-Notification | Agent creates too many suggestions. | Apply notification budget and digest routing. |
| Bad Personalization | Agent misunderstands relationship or tone. | Capture feedback and allow per-contact adjustments. |
| Draft Tone Mismatch | Draft sounds unlike user. | Route through persona/style layer and require review. |
| Context Bleed | Wrong project or persona context is used. | Enforce ContextBroker identity boundaries. |
| Hallucinated Obligation | Agent invents a task not present in evidence. | Require evidence-backed candidate generation. |
| Privacy Creep | Agent retrieves too much data. | Restrict retrieval scope and log context use. |
| New Inbox Creation | User now has to manage agent proposals. | Suppress low-salience items and batch digest. |

---

## 19. Evaluation Metrics

### 19.1 Product Metrics

| Metric | Target |
|---|---|
| Helpful Proposal Rate | Percentage of proposals marked helpful. |
| False Positive Rate | Percentage marked not important or wrong context. |
| Draft Acceptance Rate | Percentage of drafts reviewed or used. |
| Notification Fatigue Rate | Dismissals without review over time. |
| Good Catch Rate | User marks proposal as something they had forgotten. |

### 19.2 System Metrics

| Metric | Target |
|---|---|
| Detection Latency | Time from source event to candidate. |
| Proposal Latency | Time from source event to proposal. |
| Retrieval Cost | Number and size of memory/context retrievals. |
| Model Cost | Tokens and provider cost per evaluated event. |
| Audit Completeness | Percentage of surfaced proposals with evidence logs. |

---

## 20. Test Plan

### 20.1 Unit Tests

- Detects explicit follow-up language.
- Detects implicit unanswered request.
- Detects stale thread after configurable threshold.
- Does not detect obligation in casual conversation.
- Applies urgency correctly for deadlines.
- Applies notification budget penalty.
- Blocks proposal when permission level is insufficient.

### 20.2 Integration Tests

- Email event produces candidate obligation.
- Candidate enrichment retrieves only allowed project/persona context.
- High-salience candidate produces draft proposal.
- Medium-salience candidate produces suggestion only.
- Low-salience candidate stores silently.
- User feedback updates later salience behavior.

### 20.3 Regression Tests

- No external send action occurs in MVP.
- Evidence is required for every surfaced proposal.
- Proposal generation fails closed when context is ambiguous.
- Persona boundary violations are rejected.
- Project boundary violations are rejected.

---

## 21. Implementation Phases

### Phase 0: Data Contracts

- Add TypeScript contracts.
- Add persistence models.
- Add audit log schema.

### Phase 1: Event Ingestion

- Normalize email or imported thread events.
- Store `SourceEvent` records.
- Add queue hook for evaluation.

### Phase 2: Candidate Detection

- Implement basic rule-based detector.
- Add model-assisted detector behind feature flag.
- Require evidence snippets for each candidate.

### Phase 3: Context Enrichment

- Connect ContextBroker retrieval.
- Enforce persona and project boundaries.
- Add memory retrieval budget.

### Phase 4: Salience Engine

- Implement baseline scoring formula.
- Add notification budget.
- Add user feedback penalties.

### Phase 5: Proposal Generation

- Generate suggestion cards.
- Generate draft replies at permission Level 3.
- Store proposal with evidence and audit trace.

### Phase 6: Review UI

- Add proposal card.
- Add draft review surface.
- Add feedback actions.

### Phase 7: Learning Loop

- Feed user feedback into scoring.
- Add per-domain and per-contact adjustments.
- Add digest mode.

---

## 22. Definition of Done

The MVP is complete when:

- A permitted communication event can produce a candidate obligation.
- Candidate obligations are evidence-backed.
- Salience scoring determines whether to store, digest, suggest, or draft.
- The system can generate a draft reply for high-salience candidates.
- The user can review, dismiss, or provide feedback.
- No external action occurs without explicit approval.
- All surfaced proposals have audit logs.
- Identity, project, and persona boundaries are enforced.
- Low-confidence events fail silently or route to digest, not interruption.

---

## 23. Open Questions

- Should thread staleness thresholds be global, per-project, or per-contact?
- Should the first detector be rule-based, model-based, or hybrid?
- Should drafts use the active persona, the user’s default writing profile, or a project-specific tone profile?
- How should Codexify represent “relationship weight” without creating invasive profiling?
- Should dismissed proposals decay future salience globally or only for similar source patterns?
- Should reminders be stored in Codexify only, or optionally exported to calendar/task systems later?

---

## 24. Future Extensions

- Calendar follow-up agent.
- Meeting action item extractor.
- Tense thread de-escalation assistant.
- Document delivery watcher.
- Project promise tracker.
- Household logistics watcher.
- Workstream drift detector.
- Browser-based “you seem stuck here” assistant.
- Cross-device Scout notifications.

---

## 25. Architectural Principle

The Thread Drift Detector is not valuable because it can act.

It is valuable because it can decide when action may be useful, preserve restraint, and keep the user sovereign.

The agent should not ask the user to manage it.

The agent should quietly reduce the number of things the user has to remember.
