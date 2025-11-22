# **PULSEOS EVENT GRAPH & AGENT PLAYBOOK SYSTEM SPEC (v0.1)**

_A sovereign alternative to ACE-style self-improving contexts, with explicit event lineage, agent transparency, and user sovereignty._

---

# **0. Overview**

This spec defines the architecture for a **unified event logging + agent knowledge evolution system** modeled after the ACE design patterns found throughout the paper (especially pages 3–6, 14–20).

Codexify will maintain:

1. **Event Graph** — immutable timeline of events and their causal structure.

2. **Agent Playbook** — modular, agent-editable strategic knowledge.

3. **User Memory** — immutable, verbatim logs separate from agent knowledge.

4. **Reflection Pipeline** — Generator→Reflector→Curator triad adapted for sovereign mode.

5. **Delta Update Engine** — incremental bullet-level updates, not monolithic rewriting.

6. **Grow-and-Refine Engine** — pruning, deduplication, consolidation, governed by embeddings.

7. **Audit Mode** — explainable lineage for all agent actions.

Distinct separation of user memory and agent evolution resolves the “collapse” problem described on page 3 of the ACE paper.

2510.04618

---

# **1. EVENT GRAPH**

## **1.1 Purpose**

Provide a _first-class_, queryable timeline of everything that happens:

- user actions

- agent actions

- problems attempted

- reasoning traces

- tool usage

- successes / failures

- reflections

- playbook updates

The Event Graph replaces “unstructured logs” and allows **graph-RAG** across time.

---

# **1.2 Storage**

Stored in **Neo4j** under `:Event` nodes and typed relationships.

### **1.3 Node Type: Event**

`Event {     id: UUID     timestamp: ISO8601     actor: "user" | "agent" | "system"     event_type:         "user_message" |        "agent_action" |        "reasoning_trace" |        "tool_call" |        "tool_result" |        "reflection" |        "playbook_update" |        "error" |        "success" |        "task_completed"             payload_raw: text (immutable)     payload_vector: embedding     metadata: map<string, any> }`

### **1.4 Relationship Types**

`:NEXT            // chronological chain :CAUSES          // causal dependency :DERIVED_FROM    // reflection derived from event :UPDATED_PLAYBOOK_FROM // curator update originated here :USES_CONTEXT    // links event to specific playbook bullets or memory shards`

ACE uses a latent version of this structure across Reflector/Curator interactions (page 5 diagram). Codexify formalizes it into a graph.

2510.04618

---

# **2. AGENT PLAYBOOK**

The Agent Playbook is a structured, modular knowledge base — the sovereign form of ACE’s “evolving context playbook” (page 4–6).

Unlike ACE, **user memory and agent playbook are strictly separate**.

---

## **2.1 Structure**

Playbook is stored as JSON + graph:

`PlaybookSection {     id: UUID     name: string     bullets: [Bullet] }  Bullet {     bullet_id: "ctx-00123" (auto-generated)     helpful_count: int     harmful_count: int     neutral_count: int     content: text (1–5 sentences)     vector: embedding     created_at: timestamp     updated_at: timestamp }`

---

## Sections (initial core set)

- `strategies_and_hard_rules`

- `apis_and_tools`

- `troubleshooting`

- `schemas_and_formats`

- `verification_checklist`

- `domain_knowledge`

- `pitfalls`

- (extendable per persona)

These mirror the ACE structures in the _example playbooks_ on page 4 of the paper.

2510.04618

---

# **3. REFLECTION PIPELINE**

Faithful to ACE’s three-part structure (generator, reflector, curator), but tuned for sovereign mode.

### **3.1 Generator**

- Produces a reasoning trajectory.

- Logs an Event of type `reasoning_trace`.

- References which playbook bullets were used.

### **3.2 Reflector**

- Diagnoses errors based on:

  - tool execution feedback

  - task result correctness

  - environment signals

  - domain logic

- Tags bullets as helpful/harmful/neutral.

- Emits Event type: `reflection`.

ACE describes this precisely on pages 19–22, including bullet-level tagging.

2510.04618

### **3.3 Curator**

- Reads reflection.

- Outputs **delta updates** only.

- No rewriting of existing bullets.

- Adds new bullets via `"ADD"` ops.

- Produces Event type: `playbook_update`.

ACE specifies exactly this behavior on pages 20–23.

2510.04618

---

# **4. DELTA UPDATE ENGINE**

Codexify’s version of ACE’s “Incremental Delta Updates” (page 5).

### **4.1 Behavior**

- No bullet is ever overwritten.

- Updated counters adjust helpful/harmful signals.

- New bullets merge in as siblings.

### **4.2 Merging Rules**

`if bullet_similarity < threshold:     ADD new bullet else:     update counters only`

Threshold ~0.85 cosine similarity.

---

# **5. GROW-AND-REFINE ENGINE**

Parallel to ACE’s “grow-and-refine” step on page 6.

2510.04618

### **5.1 Triggers**

- playbook size > user-defined budget

- agent repeatedly struggles with same domain

- end-of-day consolidation

- low-latency background job

### **5.2 Operations**

- deduplicate bullets

- merge near-duplicates (counter aggregation)

- cluster into new sections

- compress outdated or deprecated ones

- preserve originals in event graph

---

# **6. USER MEMORY BOUNDARY**

A hard separation between:

- **User Memory (immutable, human-authored)**

- **Agent Playbook (mutable, agent-evolving)**

There is no cross-contamination.  
Reflections from user inputs _may_ inform playbook deltas, but user memory itself is never altered.

This directly prevents ACE-style “context collapse” shown in the chart on page 3.

2510.04618

---

# **7. AUDIT LOGGING**

Every agent action is:

- linked to the bullets used

- linked to the past reflections influencing the action

- linked to the tool results

The user can always:

- inspect why the agent acted

- view lineage

- prune bullets

- correct agent misunderstandings

This fulfills the goal of sovereign, transparent agents.

---

# **8. INTERFACE / API SURFACE**

Codexify modules that will consume these structures:

- **`ContextBroker`**  
    Fetches:

  - top-N bullets by similarity

  - relevant event slices

  - persona shards

  - environment sensors

- **`ModelRouter`**  
    Uses event lineage in scoring.

- **`ThreadVault`**  
    Stores bullets and events snapshot in local DB.

- **`GraphWrag`**  
    Neo4j driver: read/write events and causal graph.

---

# **9. PHASES OF AGENT LEARNING**

Mirrors the ACE adaptation loop:

### **Phase 0 — Bootstrapping**

Seed Playbook with user-provided domain knowledge or persona shard strategies.

### **Phase 1 — Observation**

Collect raw events (no updates yet).

### **Phase 2 — Reflection**

Run Reflector over trajectories.

### **Phase 3 — Curation**

Curator produces deltas.

### **Phase 4 — Integration**

Grow-and-refine merges deltas into Playbook.

### **Phase 5 — Retrieval**

Generator uses updated Playbook to answer new tasks.

Everything is explicit, controlled, revertible.

---

# **10. WHAT THIS SYSTEM ENABLES**

- ACE-style self-improving agents without data drift

- Full explainability

- Causal introspection

- Playbook evolution that stays aligned with user sovereignty

- Structured debugging

- Agent behavior that gets better over time

- Local-first adaptation

- Clear separation between “my memories” and “the agent’s strategy”

---
