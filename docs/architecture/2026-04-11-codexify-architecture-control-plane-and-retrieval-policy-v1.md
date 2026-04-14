# 📐 Codexify Architecture — Control Planes & Retrieval Policy (v1)

---

# 1. Purpose

Codexify is a **policy-driven retrieval system**.

Its architecture separates:

```text
User intent
System interpretation
Retrieval policy
Execution behavior
Observability
```

This separation exists to ensure:

* deterministic behavior
* traceable decisions
* stable retrieval under scale

Modern RAG systems require this separation because retrieval failures often occur **before generation**, not during it ([Cloudian][1])

---

# 2. Core System Model

Codexify operates on a **layered control architecture**:

```text
Input
  ↓
Intent Plane
  ↓
Interpretation Plane
  ↓
Policy Plane
  ↓
Execution Plane
  ↓
Observability Plane
```

Each layer has a strict responsibility.

---

# 3. Control Planes

---

## 3.1 Intent Plane (Frontend-owned)

Represents **user-declared intent**.

```ts
slash_intent = {
  commandId,
  intentKind,
  retrievalHint
}
```

Properties:

* explicit
* user-controlled
* transport-safe

Rules:

* Never inferred from prompt text
* Never mutated downstream

---

## 3.2 Interpretation Plane (Backend-owned)

Maps intent → system meaning.

```ts
retrieval_override = {
  mode,
  reason
}
```

Derived from:

```text
retrieval_override = f(slash_intent)
```

Properties:

* deterministic
* bounded
* side-effect free

Rules:

* Must not inspect prompt text
* Must not depend on runtime state
* Must not execute behavior

---

## 3.3 Policy Plane (System control layer)

Defines how retrieval operates.

```ts
effective_policy = merge(default_policy, retrieval_override)
```

This is the **critical layer**.

Properties:

* system-owned
* authoritative
* inspectable

Rules:

* override constrains policy
* override never replaces policy
* policy remains valid without override

---

## 3.4 Execution Plane (Retrieval system)

Executes retrieval using policy.

```text
ContextBroker → retrieve_with_policy(effective_policy)
```

Responsibilities:

* data selection
* chunk retrieval
* fallback logic

Rules:

* no intent parsing
* no interpretation logic
* no policy mutation

---

## 3.5 Observability Plane (Diagnostics)

Surfaces system state.

```ts
payload_summary = {
  slash_intent,
  retrieval_override,
  effective_policy,
  retrieval_posture
}
```

Purpose:

* debugging
* auditing
* system transparency

Production RAG systems require separate monitoring for retrieval and generation to diagnose failures accurately ([Cloudian][1])

---

# 4. Data Flow

Canonical pipeline:

```text
User Input
  ↓
Slash Parser
  ↓
slash_intent
  ↓
Backend Route
  ↓
retrieval_override
  ↓
Policy Merge
  ↓
effective_policy
  ↓
ContextBroker
  ↓
Retrieval Execution
  ↓
Trace
  ↓
retrieval_posture (UI)
```

---

# 5. Retrieval Policy Contract

---

## 5.1 Default Policy

```ts
DefaultPolicy = {
  source_mode: "thread" | "project" | "personal_knowledge"
  widening_enabled: boolean
  identity_scope: "user_only"
}
```

---

## 5.2 Override Contract

```ts
RetrievalOverride = {
  mode: "none" | "conversation" | "project" | "personal_knowledge"
  reason: string
}
```

---

## 5.3 Merge Rule

```ts
effective_policy = merge(default_policy, retrieval_override)
```

Constraint:

```text
override modifies policy
override does not replace policy
```

---

# 6. System Invariants (NON-NEGOTIABLE)

---

## 🔒 6.1 Thread-first retrieval

```text
active thread is always searched first
```

---

## 🔒 6.2 Identity boundaries

```text
no cross-user retrieval
no archived thread leakage
```

---

## 🔒 6.3 Fallback safety

```text
if retrieval fails:
  fallback logic executes
```

Routing must remain conservative to avoid incorrect paths ([Interview AiBox][2])

---

## 🔒 6.4 No prompt-based routing

```text
prompt text must not influence retrieval scope
```

---

## 🔒 6.5 Single source of intent truth

```text
intent = slash_intent ONLY
```

No re-parsing allowed.

---

# 7. Retrieval Posture (Observability Contract)

---

## Definition

Retrieval posture is a **human-readable snapshot of retrieval state**.

```ts
retrieval_posture = {
  source_mode
  boundary_label
  retrieval_override_mode
  widen_reason
  conversation_only?
}
```

---

## Purpose

* explain retrieval behavior
* remove ambiguity
* reduce debugging cost

---

## Source of truth

```text
retrieval_posture derives from effective_policy + trace
```

Frontend must not redefine it.

---

# 8. Flow Builder Integration

---

## New Capability

Flow Builder now supports:

```text
actions + control signals
```

---

## Mapping

```text
slash command → intent → override → policy
```

Example:

```text
/doc     → project retrieval
/focus   → strict thread
/global  → widening allowed
/memory  → personal knowledge
```

---

## Implication

Flow Builder becomes:

> a system for orchestrating **behavioral policy**, not just actions

---

# 9. Observability Surfaces

---

## Command Center

Displays:

* retrieval_posture
* effective_policy
* trace metadata

Purpose:

* operator insight
* debugging
* system verification

---

## Chat Surface

Does NOT show:

* retrieval internals
* posture
* policy

This separation is intentional.

---

# 10. Anti-Patterns (Do Not Implement)

---

## ❌ Override replaces policy

Breaks system guarantees

---

## ❌ Prompt-driven routing

Creates hidden logic

---

## ❌ Dual interpretation layers

Creates drift

---

## ❌ Frontend-defined posture

Breaks observability integrity

---

# 11. System Classification

Codexify is now:

> **a policy-driven retrieval system with explicit intent and observable execution**

Not:

* a prompt wrapper
* a static RAG pipeline
* a chat-first architecture

---

# 🧠 Final Summary

You have built:

```text
Intent → Interpretation → Policy → Retrieval → Observability
```

This is the same structure used in:

* enterprise RAG systems
* agentic retrieval pipelines
* multi-source routing systems

---

# 🧭 One-line doctrine

> Codexify does not guess what to retrieve.
> It **decides, enforces, and explains** how retrieval happens.

---
