# Reconstructible Context and Portable Reasoning Environment

**Classification:** Architecture concept / doctrine  
**Status:** Proposed — not current runtime truth  
**Scope:** Reasoning continuity, project-state portability, retrieval, conversational history, memory boundaries, and task-generation architecture  
**Last updated:** 2026-08-14

## Purpose

Define an architectural model for preserving high-quality reasoning continuity without requiring an assistant, project, or account to maintain an opaque or permanently accumulated model of the user and system.

The motivating observation is that the Codexify development workflow increasingly behaves like a **portable reasoning environment**:

1. The human provides direction.
2. Canonical project artifacts establish current truth.
3. Architecture contracts constrain valid movement.
4. Repository and proof evidence establish what actually exists.
5. A reasoning engine resolves the next useful action.
6. The action is emitted through a deterministic execution protocol.

Under this model, conversational history remains valuable, but it is not required to be the sovereign representation of project state.

The architectural question is therefore not:

> How can the system remember everything?

It is:

> What is the minimum sufficient state from which the system can reconstruct the context required for the current decision?

## Non-Claim

This document does **not** claim knowledge of ChatGPT, Claude, Hermes, or any other model provider's private internal memory or retrieval implementation.

The architecture described here is a Codexify design hypothesis derived from the observed development workflow and the project's existing contracts.

It should be evaluated independently through controlled portability experiments.

## 1. Core Thesis

Codexify should distinguish between:

- **authoritative state**
- **retrievable evidence**
- **derived context**
- **reasoning**
- **conversation**

These are related but must not collapse into one persistence mechanism.

The preferred model is:

```text
Authoritative artifacts
        +
Historical evidence
        +
Current human intent
        +
Retrieval policy
        ↓
Reconstructed working context
        ↓
Reasoning engine
        ↓
Bounded next action
```

The reconstructed working context is temporary.

It may contain:

- project state
- relevant history
- recent decisions
- causal relationships
- current blockers
- architectural invariants
- selected prior conversations

It does not need to become a permanent global representation of the system or user.

## 2. Existing Codexify Evidence

Codexify already contains several architectural decisions that point toward this model.

### 2.1 Task generation is designed to be self-contained

The Axis Codexify Task Spec Protocol requires each engineering Task Spec to contain the evidence, files, validation surface, execution lane, and closeout requirements necessary for an agent to operate without hidden conversational state.

See:

- [`Axis-Codexify-Task-Spec-Protocol`](../architecture/../architecture/Axis-Codexify-Task-Spec-Protocol.txt) when present in the repo-native docs tree
- [`agent-protocol-operations.md`](./agent-protocol-operations.md)
- [`codexify-issue-template-contract.md`](./codexify-issue-template-contract.md)

This means the intended execution artifact is already designed to cross reasoning-engine and session boundaries.

A valid task should not require:

> Remember what we talked about three weeks ago.

The missing context must instead be recoverable from explicit evidence.

### 2.2 Current truth already has an external authority

[`00-current-state.md`](./00-current-state.md) is explicitly defined as Codexify's short-form authority for:

- release readiness
- supported install path
- active blockers
- current priorities
- present release promises

It overrides older architecture and planning language on short-horizon reality.

The broader architecture KB then provides a routing layer into deeper structural documents rather than expecting an assistant to remember the system topology from prior conversations.

See [`README.md`](./README.md).

This establishes an important principle:

> Current project truth belongs to governed artifacts, not assistant recollection.

### 2.3 Retrieval already favors reconstruction over universal graph traversal

The retrieval-router doctrine defines several retrieval postures and explicitly permits conversation-only, local, temporal, semantic, and graph-enriched reasoning.

Graph context is optional enrichment rather than mandatory ceremony. Retrieval starts narrow and widens only when policy or evidence requires it.

See [`router-decision-table.md`](./router-decision-table.md).

This supports an architecture where relationships may be reconstructed when useful instead of requiring every relationship to exist permanently in one canonical graph.

### 2.4 Codexify already treats relationships as first-class portable state

The Account Export + Restore Contract requires preservation of:

- project membership
- thread/message structure
- artifact relationships
- document linkage
- provenance
- source lineage
- explicit identifiers and relationships

See [`account-export-restore-contract.md`](./account-export-restore-contract.md).

This distinction is central.

Content alone is insufficient.

A transcript export can preserve the **nodes** while losing important **edges**.

Portable reasoning therefore requires enough metadata to reconstruct the edges that matter.

## 3. The Five-Layer Reasoning Model

The current workflow can be decomposed into five independent layers.

### Layer 1 — Reasoning Engine

Examples:

- GPT
- Claude
- Hermes
- DeepSeek
- local models
- future reasoning providers

The engine performs inference.

It is not authoritative project state.

Different engines may produce different judgments over the same evidence.

Portability does not require identical output. It requires preservation of the conditions necessary for **functional continuity**.

### Layer 2 — Operating Doctrine

This layer determines how reasoning should be converted into action.

Examples:

- Axis instructions
- Codexify Task Spec Protocol
- architecture-impact classification
- evidence-posture rules
- source-authority hierarchy
- identity and sovereignty constraints
- validation requirements

This layer answers:

> Given what we know, how are we permitted to move?

It is one of the highest-value portable artifacts in the system.

### Layer 3 — Canonical Project State

This layer contains externally inspectable project truth.

Examples:

- repository state
- current-state documentation
- ADRs
- architecture contracts
- schemas
- tests
- proof receipts
- decision logs
- current task/campaign state

This layer answers:

> Where are we now?

Git history is particularly valuable because it records actual transitions rather than reconstructed recollections of those transitions.

### Layer 4 — Current Human Direction

This is the operator's active intent.

Examples:

> This is where we are and this is where I want to go.

> I want to simplify this subsystem without changing the user experience.

> TTS can remain outside beta, but I want the rest of this surface included.

This layer answers:

> Where should we move?

The human does not necessarily need to specify the path.

The reasoning system determines the next traversable edge from canonical state toward the desired state.

### Layer 5 — Historical Conversation

Conversation preserves context that may never have graduated into canonical artifacts.

Its highest-value contents are often not implementation facts.

They are:

- rationale
- rejected alternatives
- evolving intent
- aesthetic judgment
- uncertainty
- preference
- counterfactual reasoning
- unfinished ideas
- explanations for why a technically valid direction was rejected

Conversation therefore answers a different question:

> Why did this direction make sense to us?

This makes transcript history extremely valuable as an archaeological corpus while still allowing it to remain non-authoritative.

## 4. Minimum Sufficient Continuity State

The minimum portable Codexify reasoning environment should be substantially smaller than the complete historical transcript corpus.

A proposed **Continuity Kernel** contains:

### A. Operating doctrine

- project instructions
- Axis Task Spec Protocol
- architectural source-authority rules
- sovereignty and identity constraints

### B. Current truth

- `00-current-state.md`
- architecture KB entrypoint
- relevant accepted ADRs
- current contracts
- supported-profile posture

### C. Implementation evidence

- repository checkout
- Git history
- relevant tests
- proof artifacts
- migration state

### D. Decision context

A compact ledger containing only decisions that are difficult to infer from code:

- important rationale
- explicitly rejected alternatives
- unresolved architectural questions
- current strategic direction
- intentional deferrals
- decisions whose absence would invite future architectural drift

### E. Current operator intent

The human's present directional instruction.

This yields:

```text
Continuity Kernel
    │
    ├── Operating doctrine
    ├── Current truth
    ├── Implementation evidence
    ├── Decision / intention ledger
    └── Current human direction
             │
             ▼
      Retrieval + reasoning
             │
             ▼
         Next action
```

Historical conversations remain available as secondary evidence when this kernel is insufficient.

## 5. Conversation as Archive, Not Bootloader

The full transcript corpus should not be discarded.

Its architectural role should instead be narrowed.

Conversation history is best treated as an **archaeological evidence store**.

Typical retrieval questions include:

- Why did we reject this approach?
- When did this concept first emerge?
- What alternatives were discussed?
- What was the intended product experience?
- Was this implementation a temporary compromise?
- Which later architecture grew from this earlier idea?

Historical conversation becomes a retrieval source.

It does not need to be loaded continuously.

This prevents system continuity from becoming proportional to transcript size.

## 6. Reconstructible Graph Doctrine

Codexify should avoid making a universal memory graph the sole owner of meaning.

Instead, durable systems should preserve high-quality source material and enough structured metadata to reconstruct useful relationship graphs on demand.

Canonical substrate:

```text
messages
documents
artifacts
commits
decisions
proofs
events
timestamps
scope
provenance
stable identifiers
typed relationships
authority
```

Runtime derivation:

```text
              Durable corpus
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
    semantic      temporal    relational
    retrieval     retrieval    retrieval
       │            │            │
       └────────────┼────────────┘
                    ▼
          Working relationship graph
                    │
                    ▼
                Reasoning
```

The working graph may be discarded after the task.

Another query may construct a different subgraph from the same source corpus.

The authoritative truth remains the source artifacts and their provenance.

## 7. Materialized Graphs Remain Useful

This doctrine does not prohibit Neo4j, knowledge graphs, embeddings, indexes, timelines, caches, or derived memory stores.

It changes their authority.

A derived graph may provide:

- traversal speed
- relationship discovery
- provenance navigation
- timeline reconstruction
- clustering
- entity linking
- retrieval acceleration

But where practical, it should behave like a **materialized cognitive index**:

```text
source corpus
    ↓
derived graph/index
    ↓
fast retrieval
```

rather than:

```text
graph
    ↓
only surviving representation of truth
```

If the graph can be destroyed and reconstructed without losing canonical information, sovereignty and recovery characteristics improve considerably.

## 8. Identity Implication

The reconstructible-context model also provides a safer identity boundary.

Instead of maintaining:

> one authoritative evolving model of the person

the system can preserve:

- authored statements
- explicit preferences
- consented durable facts
- decisions
- provenance
- temporal evidence

and construct only the identity context needed for a specific interaction.

This aligns with Codexify's existing doctrine that personas may depend on identity without owning or directly rewriting identity state.

See [`self-extending-agent-plugin-system.md`](./self-extending-agent-plugin-system.md).

Derived interpretation should remain subordinate to source evidence.

## 9. Provider Portability

A portable reasoning environment should support multiple inference engines over the same governed state.

Conceptually:

```text
                    Codexify Continuity Kernel
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
              GPT           Claude         Hermes
               │              │              │
               └──────────────┼──────────────┘
                              ▼
                    Same governance boundary
                              │
                              ▼
                     Comparable next actions
```

Outputs need not be identical.

The portability target is:

- comparable understanding of current state
- preservation of architecture invariants
- preservation of source authority
- bounded task selection
- equivalent evidence requirements
- no dependence on private historical state unavailable to another engine

Reasoning quality remains provider-dependent.

Architecture truth does not.

## 10. Expected Sources of Cross-Engine Variance

Even with identical project data, different systems may vary because of:

- reasoning quality
- retrieval implementation
- context-window behavior
- ranking algorithms
- instruction precedence
- tool availability
- repository visibility
- model priors
- summarization behavior
- orchestration performed by the host platform

The architecture should therefore optimize for **bounded variability**, not deterministic textual identity.

A successful portable environment should cause different capable engines to remain inside the same architectural corridor.

## 11. Failure Modes

### 11.1 Transcript Sovereignty

Treating chat history as canonical project state.

Failure:

- important truth becomes difficult to audit
- context becomes provider-bound
- project continuity degrades as corpus size grows

Mitigation:

- graduate durable decisions and runtime truth into canonical artifacts

### 11.2 Graph Sovereignty

Treating a derived graph as the only surviving representation of relationships.

Failure:

- inference becomes indistinguishable from evidence
- bad extraction can become durable truth
- recovery becomes dependent on one derived store

Mitigation:

- retain provenance-rich source relationships and make graph projections reproducible

### 11.3 Document Dump Portability

Assuming that copying all documents into another model recreates the same environment.

Failure:

- source authority is lost
- relationships disappear
- retrieval boundaries become ambiguous
- historical and current truth become indistinguishable

Mitigation:

- preserve metadata, relationship types, authority class, provenance, and retrieval scope

### 11.4 Hidden Intent Loss

Relying exclusively on code and documentation.

Failure:

- rejected options may be repeatedly reconsidered
- product direction can become technically correct but strategically wrong
- intentional deferrals look like forgotten work

Mitigation:

- maintain a small decision/intention ledger
- retrieve historical conversations when rationale is missing

## 12. Portability Experiment

This architecture should be tested rather than assumed.

Construct a **Cold-Start Axis Packet** containing only:

1. operating instructions
2. Task Spec Protocol
3. current-state document
4. architecture KB entrypoint
5. relevant ADR index
6. repository access or equivalent Git evidence
7. compact decision/intention ledger

Do **not** include historical conversation.

Give the same packet to multiple capable reasoning engines.

Ask each engine the same representative Codexify questions.

Example evaluation classes:

- identify the next beta-hardening task
- classify an architecture-impacting change
- determine whether a requested feature widens the supported release promise
- propose the next implementation slice toward a stated product goal
- identify which evidence is missing before a runtime claim is allowed

Compare:

- architecture compliance
- task selection
- source selection
- unsupported assumptions
- invariant preservation
- evidence requirements
- strategic alignment

Then repeat the experiment with selected historical conversation available.

The delta measures the actual value of transcript continuity.

## 13. Architectural Interpretation

The working hypothesis is:

> Codexify's valuable continuity may live primarily in the structure surrounding the reasoning engine rather than inside accumulated assistant memory.

More specifically:

```text
Documents carry architecture.

Git carries implementation history.

Proofs carry demonstrated reality.

Protocols carry operating behavior.

Decision records carry durable rationale.

The human carries current intent.

Conversation carries historical texture.

Retrieval assembles the relevant subset.

The model reasons over it.
```

No single layer needs to impersonate all the others.

## 14. Design Direction

Codexify should optimize for **reconstructible continuity**.

A strong continuity system should make it possible to:

- replace the reasoning engine
- lose ephemeral derived indexes
- start a new conversation
- migrate to another node
- restore from an export
- rebuild contextual relationship graphs

without losing the authoritative state required to continue meaningful work.

The desired property is not perfect memory.

It is:

> **The ability to reconstruct enough truthful context, from inspectable evidence, to continue deliberate action.**

That is a substantially smaller and more sovereign problem.
