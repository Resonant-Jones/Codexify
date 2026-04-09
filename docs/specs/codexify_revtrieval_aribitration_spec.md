# Codexify Retrieval Arbitration Spec v0.1

## 1. Purpose

Define how Guardian decides:

* when to use **Obsidian (compiled memory)**

* when to use **RAG (raw retrieval)**

* when to use **external tools (delegated)**

Without this, the system becomes:

* inconsistent

* non-debuggable

* user-trust fragile

---

# 2. Core Principle

> **Prefer compiled knowledge. Fall back to retrieval. Escalate to external.**

Because:

* compiled wiki = accumulated understanding

* RAG = re-deriving understanding each time

* external = last resort for missing data

This mirrors Karpathy’s shift:

> “compile once, reuse instead of re-deriving every query” ([Agent Wars][1])

---

# 3. Intent Classification (first decision)

Every query must be classified before retrieval.

```ts

type Intent =

| "conversation_only"

| "direct_qa"

| "memory_recall"

| "concept_explanation"

| "relationship_reasoning"

| "exploratory"

| "external_lookup"

| "action_command"

```

---

# 4. Source Capabilities (truth table)

| Source | Strength | Weakness |

| -------- | ------------------------------- | ------------------------------- |

| Obsidian | structured, linked, synthesized | incomplete, stale |

| RAG | broad, raw, up-to-date ingest | lossy, unstructured |

| External | fresh, global | slow, costly, non-deterministic |

---

# 5. Decision Tree (actual logic)

```text

IF intent == conversation_only:

use conversation only

STOP

IF intent == action_command:

route to command bus

STOP

IF intent in [concept_explanation, relationship_reasoning]:

TRY obsidian FIRST

IF confidence high:

RETURN

ELSE:

FALLBACK to RAG

IF intent in [memory_recall]:

TRY obsidian FIRST

IF insufficient:

FALLBACK to RAG

IF intent == direct_qa:

TRY obsidian FIRST

IF no match:

USE RAG

IF intent == exploratory:

USE RAG FIRST

OPTIONALLY enrich with obsidian

IF intent == external_lookup:

USE external tool

```

---

# 6. Confidence Model (this is critical)

Guardian must evaluate:

```ts

type RetrievalConfidence = {

coverage: number // did we find relevant nodes?

cohesion: number // do nodes connect meaningfully?

freshness: number // how recently updated?

}

```

### Rule

```text

IF coverage < threshold OR cohesion < threshold:

fallback

```

---

# 7. Obsidian Query Strategy (not search, navigation)

This is where your system differs from RAG.

Instead of:

```text

query → similarity search → chunks

```

Do:

```text

query

↓

index.md (entry point)

↓

select relevant nodes

↓

follow links

↓

assemble context

```

Because:

> wiki navigation preserves relationships that RAG can miss ([LM Market Cap][2])

---

# 8. RAG Fallback Rules

RAG is used when:

* no matching wiki nodes

* wiki incomplete

* user explicitly asks for documents

```text

RAG is:

fallback OR breadth-expansion

```

Never primary for structured reasoning if wiki exists.

---

# 9. Hybrid Mode (important)

Sometimes you want both.

```text

1. Get base understanding from Obsidian

2. Expand with RAG

3. Merge

```

Use when:

* partial wiki coverage

* user asks “latest + explanation”

* wiki exists but incomplete

---

# 10. External Tool Escalation

Only trigger when:

* user explicitly asks

* or system detects missing knowledge

```text

IF (obsidian + rag) fail:

escalate → external

```

Examples:

* web search

* Groq Compound

* APIs

---

# 11. Source Selector Override

User control must override system logic.

```text

IF source_mode == obsidian:

force obsidian-first

IF source_mode == project:

force RAG-first

IF source_mode == hybrid:

use arbitration logic

```

This aligns with your existing retrieval doctrine seam

---

# 12. Feedback Loop (this is where it becomes alive)

After answering:

```text

IF answer required synthesis not in wiki:

suggest:

"Save to Obsidian?"

```

This creates:

```text

RAG → Answer → Wiki → Future queries faster

```

Which is exactly the compounding behavior Karpathy describes:

> knowledge base “gets stronger over time” ([techbuddies.io][3])

---

# 13. Failure Modes (explicit)

Guardian must detect and avoid:

### 1. False confidence

* wiki has partial info

* answer sounds complete but isn’t

### 2. Stale knowledge

* wiki outdated

* newer info exists in RAG

### 3. Fragmented retrieval

* RAG returns unrelated chunks

* no cohesion

---

# 14. Debug Surface (important for trust)

Expose:

```text

Source Used:

- Obsidian

- RAG

- Hybrid

Confidence:

- High / Medium / Low

Fallback triggered:

- Yes / No

```

This makes the system explainable.

---

# 15. Final System Behavior (compressed)

```text

User Query

↓

Intent Classifier

↓

Retrieval Router

↓

[Obsidian] → primary reasoning

[Fallback → RAG]

[Fallback → External]

↓

Answer

↓

Optional: Save to Obsidian

```

---

# 16. What you just unlocked

You now have:

* **Command system → control plane**

* **Obsidian → compiled memory**

* **RAG → raw memory**

* **Router → intelligence layer**

That’s the full stack.

---

# Final note

Most systems stop at:

> “retrieve relevant chunks”

You now have:

> “decide *how knowledge should be formed before answering*”

That’s a higher-order system.

---
