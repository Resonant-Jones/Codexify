# Execution Kernel — Phase 0 Preparation

Status: Pre-implementation  
Scope: Current runtime hardening only  
Non-goal: Do not implement execution graphs, agents, or orchestration runtime in this phase  

---

## Purpose

Prepare Codexify’s current runtime so a future native execution kernel can attach cleanly without introducing ambiguity, identity drift, or architectural instability.

Phase 0 is not feature work.  
It is **foundation hardening**.

---

## Success Criteria

- Fresh supported-path proof exists on current `main`
- Request lifecycle is observable and unambiguous
- Provider state and request state are clearly separated
- Runtime vocabulary is canonicalized
- Retrieval posture is explainable and inspectable
- Provenance is preserved across all artifacts
- Workspace is useful in real user workflows
- Diagnostics are powerful but contained

---

## Tier 1 — Core Loop Integrity (Required Before Anything Else)

### 1. Supported Path Proof (Current Tip)

Re-run full Compose proof on the exact current `main` tip.

Must include:

- [ ] Clean-start migration
- [ ] Chat completion acceptance
- [ ] Assistant persistence
- [ ] Upload → parse → embed → retrieve
- [ ] Health surface reconciliation:
  - `/health`
  - `/health/chat`
  - `/api/health/llm`
  - `/api/health/retrieval`
  - `/api/llm/catalog`

Exit condition:
> Proof artifact exists for the exact commit being shipped.

---

### 2. Request State Visibility

Normalize request lifecycle visibility across backend + frontend.

Must include:

- [ ] Canonical request states used everywhere
- [ ] Canonical provider states used everywhere
- [ ] `messageId` vs `requestId` separation visible
- [ ] Replay / orphan / retry states inspectable
- [ ] Attempt-level timestamps available (queued, ack, firstToken, completed)

Exit condition:
> Any response can be traced to a specific attempt of a specific message.

---

### 3. Runtime Token Canonicalization

Eliminate ad hoc runtime literals.

Must include:

- [ ] All lifecycle states come from canonical registry
- [ ] All provider states come from canonical registry
- [ ] No inline string status logic in routes, UI, or workers
- [ ] Tests assert token usage where relevant

Exit condition:
> Runtime vocabulary is defined once and reused everywhere.

---

### 4. Event Trace Truth Surfaces

Strengthen operator visibility.

Must include:

- [ ] Task lifecycle breadcrumbs are consistent (`created`, `running`, `completed`, etc.)
- [ ] Visibility degradation is explicitly logged
- [ ] Correlation across:
  - health endpoints
  - task events
  - logs
  - persisted messages
- [ ] Queue acceptance vs completion clearly distinguishable

Exit condition:
> Operators can diagnose stuck or delayed work without guessing.

---

## Tier 2 — Structural Stability

### 5. Retrieval Router Discipline

Keep retrieval policy outside prompt improvisation.

Must include:

- [ ] Retrieval decisions come from router policy, not prompt text
- [ ] `source_mode` visible in trace
- [ ] `widen_reason` visible in trace
- [ ] Active-thread-first behavior preserved
- [ ] No hidden widening logic

Exit condition:
> Retrieval behavior is explainable and reproducible.

---

### 6. Provenance Preservation

All artifacts must retain lineage.

Must include:

- [ ] Thread → message → artifact links preserved
- [ ] Document and media links remain explicit
- [ ] No derived artifact without source reference
- [ ] Export/restore assumptions not violated

Exit condition:
> Every artifact can answer: where did this come from?

---

### 7. Storage & Lifecycle Invariants

Verify durability before adding new entities.

Must include:

- [ ] Thread/message persistence invariants validated
- [ ] Document linkage correctness verified
- [ ] Media dedupe and alias behavior stable
- [ ] Event ordering (outbox) remains consistent
- [ ] Project/thread/document relationships intact

Exit condition:
> Existing storage can safely anchor future runtime entities.

---

### 8. Identity Boundary Integrity

Prevent execution features from contaminating identity.

Must include:

- [ ] Execution artifacts do not mutate identity layers
- [ ] Persona does not own identity
- [ ] Sensitive topics remain excluded unless explicitly promoted
- [ ] Diary/exclusion rules remain intact

Exit condition:
> Identity remains user-owned and explicitly controlled.

---

## Tier 3 — Product Reality Layer

### 9. Workspace Usability

Workspace must function as a real surface.

Must include:

- [ ] Shelf is usable (pinned + recent items)
- [ ] Scratchpad is persistent and low-friction
- [ ] Inspector works without breaking flow
- [ ] Workspace persists across views
- [ ] Drawer states behave correctly (collapsed / peek / open / focused)

Exit condition:
> Workspace feels like a working surface, not a placeholder.

---

### 10. Diagnostics Containment

Diagnostics must not pollute the primary UX.

Must include:

- [ ] No diagnostics in chat stream
- [ ] Diagnostics only in:
  - Settings → Diagnostics
  - explicit popovers
  - developer mode
- [ ] Retrieval traces show raw evidence (not rewritten)
- [ ] Metadata always visible (source, score, depth, timestamp)

Exit condition:
> Diagnostics are powerful but never intrusive.

---

### 11. Local Knowledge Stability (Obsidian / Vaults)

Preserve local-first knowledge reliability.

Must include:

- [ ] Ingest is idempotent
- [ ] Rename/move/delete correctly handled
- [ ] Embedding lifecycle remains stable
- [ ] Retrieval returns expected chunks
- [ ] No connector expansion in this phase

Exit condition:
> Local knowledge behaves predictably and repeatably.

---

### 12. Command Bus / Orchestration Containment

Do not expand execution surfaces yet.

Must include:

- [ ] Command bus remains internal
- [ ] Delegation remains non-release surface
- [ ] No UI claims about agent execution
- [ ] No widening of runtime promises

Exit condition:
> Internal power stays internal until proven.

---

## Out of Scope (Strict)

Do NOT implement:

- TaskGraph runtime
- Agent orchestration layer
- Multi-step execution planning
- Approval systems
- Tool chaining frameworks
- Autonomous execution loops

These belong to Phase 1+.

---

## Final Definition of Done

Phase 0 is complete when:

- The current runtime is **provably correct**
- The system is **observable without ambiguity**
- The data model is **stable and trustworthy**
- The UX is **useful in real workflows**
- The architecture is **ready to accept a higher-order runtime without refactor pressure**

---

## Guiding Principle

Do not build the execution engine yet.

Make the system something worth executing on.
