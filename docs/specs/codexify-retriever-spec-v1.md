# Codexify Retriever Spec v1
---

id: codexify_retriever_spec_v1
title: Codexify Retriever Spec v1
type: system_spec
status: draft
created: 2026-04-12
updated: 2026-04-12
tags:

* codexify
* retriever
* rag
* retrieval
* embeddings
* ranking
* chunking
* context-broker

---

# Codexify Retriever Spec v1

## Canonical Definition

> The Retriever is the subsystem responsible for selecting, ranking, and returning the most relevant knowledge fragments given a query and a scoped context defined by the ContextBroker.

---

## 1. Purpose

This spec defines:

* How documents are chunked
* How embeddings are generated and stored
* How queries are executed
* How results are ranked and filtered
* How retrieval integrates with Workspace Profiles

---

## 2. Design Principles

### 2.1 Retrieval is Scoped

All retrieval must respect:

* Workspace boundaries
* Active knowledge sources
* Visible projects

### 2.2 Recall First, Then Precision

Initial retrieval should favor **recall**, followed by aggressive reranking.

### 2.3 Source Awareness Matters

Not all knowledge sources are equal. Priority must influence ranking.

### 2.4 Chunk Quality > Chunk Quantity

Bad chunking destroys retrieval quality more than weak embeddings.

### 2.5 Deterministic Filtering Layer

Post-retrieval filtering must be predictable and explainable.

---

## 3. Retrieval Pipeline

```text
Query
 ↓
Preprocessing
 ↓
Embedding
 ↓
Vector Search (topK wide)
 ↓
Reranking
 ↓
Filtering
 ↓
ContextBroker
```

---

## 4. Query Preprocessing

### Input

```ts
interface RetrievalQuery {
  query: string;
  workspaceContext: ResolvedWorkspaceContext;
}
```

---

### Steps

1. Normalize text
2. Strip low-signal tokens (optional)
3. Expand query (future phase)

---

### Example

```ts
cleanQuery = normalize(query);
```

---

## 5. Embedding Strategy

### Requirements

* Deterministic per model
* Namespace-aligned with knowledge source
* Cached where possible

---

### Schema linkage

Each chunk:

```ts
embeddingNamespace = knowledgeSource.embeddingNamespace;
```

---

### Recommendation (initial)

* Use a single embedding model per environment
* Avoid mixing embeddings across models unless versioned

---

## 6. Chunking Strategy

### Goals

* Preserve semantic coherence
* Avoid fragmenting meaning
* Enable cross-document linking

---

### Baseline rules

| Rule       | Value                        |
| ---------- | ---------------------------- |
| Chunk size | 300–800 tokens               |
| Overlap    | 10–20%                       |
| Boundaries | Prefer headings / paragraphs |

---

### Obsidian-specific enhancements

* Split by:

  * headings (`#`, `##`)
  * bullet groups
  * note sections

---

### Anti-patterns

❌ Fixed-size blind chunking
❌ Splitting mid-concept
❌ Ignoring markdown structure

---

## 7. Vector Search

### Execution

```ts
results = vectorStore.query({
  queryEmbedding,
  knowledgeSourceIds,
  projectIds,
  topK: 40
});
```

---

### Why topK = 40?

* High recall phase
* Reranking will reduce

---

## 8. Reranking Layer

### Inputs

* similarity score
* source priority
* recency (optional)
* chunk density

---

### Scoring function (conceptual)

```ts
score =
  (similarity * 0.6) +
  (sourcePriority * 0.2) +
  (recencyBoost * 0.1) +
  (chunkQuality * 0.1);
```

---

### Output

Top 8–15 chunks

---

## 9. Source Priority

Defined in:

```ts
WorkspaceKnowledgeSource.priority
```

---

### Behavior

Higher priority sources:

* rank higher
* survive filtering longer

---

### Example

| Source        | Priority |
| ------------- | -------- |
| Work Vault    | 10       |
| Global Notes  | 5        |
| External Docs | 2        |

---

## 10. Filtering

### Goals

* Remove redundancy
* Remove low-signal chunks
* Maintain diversity

---

### Rules

* Max 2–3 chunks per document
* Drop near-duplicates
* Ensure multi-source coverage

---

### Example

```ts
filtered = dedupe(results);
filtered = limitPerDocument(filtered, 3);
```

---

## 11. Output Contract

```ts
interface RetrievalResult {
  chunkId: string;
  content: string;

  documentId: string;
  knowledgeSourceId: string;
  projectId?: string;

  score: number;
}
```

---

## 12. Integration with ContextBroker

### Input

```ts
retrieve({
  query,
  knowledgeSourceIds,
  projectIds
});
```

---

### Output used for

* context blocks
* citations (future)
* memory linking

---

## 13. Failure Modes

### 13.1 Low Recall

Fix:

* increase topK
* improve chunking
* adjust embedding model

---

### 13.2 Irrelevant Results

Fix:

* tune reranking
* adjust source priority
* refine chunk boundaries

---

### 13.3 Overload

Fix:

* aggressive filtering
* token budgeting
* summarization

---

## 14. Phase Plan

### Phase 1 (Now)

* Basic chunking
* Single embedding model
* Vector search
* Simple rerank

---

### Phase 2

* Hybrid search (keyword + vector)
* Better reranking models
* query expansion

---

### Phase 3

* Graph-aware retrieval
* cross-document reasoning
* adaptive retrieval strategies

---

## 15. Strategic Position

This Retriever is:

* Not just a vector search wrapper
* Not just a markdown crawler

It is:

> A **controlled recall engine** tuned to workspace context and source intent.

---

## 16. Key Insight

Karpathy-style wiki works because:

* structure is human-readable
* links encode relationships

But it fails at scale.

Codexify bridges that gap:

* Human structure (Obsidian)
* Machine retrieval (this system)

---

## 17. Summary

> The Retriever determines what the system remembers in the moment.
> The ContextBroker determines how that memory is used.

Together, they define system intelligence.
