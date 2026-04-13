---

id: codexify_ingestion_indexing_spec_v1
title: Codexify Ingestion & Indexing Spec v1
type: system_spec
status: draft
created: 2026-04-12
updated: 2026-04-12
tags:

* codexify
* ingestion
* indexing
* obsidian
* rag
* pipeline
* embeddings
* sync

---

# Codexify Ingestion & Indexing Spec v1

## Canonical Definition

> The Ingestion & Indexing system transforms external and internal knowledge sources into structured, chunked, and retrievable memory aligned with Codexify’s retrieval architecture.

---

## 1. Purpose

This spec defines:

* How knowledge sources are ingested
* How documents are parsed and normalized
* How chunks are created
* How embeddings are generated
* How updates and re-indexing are handled

---

## 2. Design Principles

### 2.1 Ingestion is Idempotent

Running ingestion multiple times must not create duplicates.

### 2.2 Incremental by Default

Only changed or new documents should be reprocessed.

### 2.3 Source is Ground Truth

The external source (Obsidian, etc.) remains authoritative.

### 2.4 Structure Preservation

Markdown structure must be preserved during parsing.

### 2.5 Fast Feedback Loop

Initial indexing should be quick enough to feel responsive.

---

## 3. Pipeline Overview

```text
KnowledgeSource
   ↓
File Discovery
   ↓
Document Parsing
   ↓
Normalization
   ↓
Chunking
   ↓
Embedding
   ↓
Storage (DB + Vector Store)
```

---

## 4. Source Types

Initial support:

* Obsidian Vault (primary)
* ChatGPT Export
* Manual Notes
* Project Documents

Future:

* Google Drive
* Notion
* Web ingestion

---

## 5. File Discovery

### For Obsidian

```ts
scanDirectory(vaultPath)
  → return all .md files
```

---

### Metadata extracted

* file path
* file name
* last modified timestamp
* tags (frontmatter + inline)

---

## 6. Document Parsing

### Input

```ts
interface RawDocument {
  path: string;
  content: string;
}
```

---

### Output

```ts
interface ParsedDocument {
  title: string;
  content: string;
  headings: Heading[];
  tags: string[];
  metadata: Record<string, unknown>;
}
```

---

### Parsing Rules

* Extract YAML frontmatter
* Detect headings (`#`, `##`, etc.)
* Preserve markdown structure
* Normalize line breaks

---

## 7. Change Detection

### Strategy

Each document gets:

```ts
rawHash = hash(content)
```

---

### Logic

```ts
if (existing.rawHash === new.rawHash) {
  skip ingestion
}
else {
  reprocess
}
```

---

## 8. Chunking

### Strategy

Chunk by **semantic structure**, not fixed size.

---

### Priority order

1. Heading sections
2. Paragraph groups
3. Bullet clusters

---

### Fallback

If section too large:

* split by token window
* maintain overlap

---

### Output

```ts
interface Chunk {
  documentId: string;
  chunkIndex: number;
  content: string;
  tokenCount: number;
}
```

---

## 9. Embedding

### Process

```ts
for each chunk:
  embedding = embed(chunk.content)
```

---

### Storage

* Vector DB (Chroma / PGVector)
* Linked via `embeddingId`

---

### Namespace

```ts
embeddingNamespace = knowledgeSource.id
```

---

## 10. Database Writes

### Document

* insert or update `IndexedDocument`

---

### Chunks

* delete old chunks (if reprocessing)
* insert new chunks

---

### Guarantee

* No duplicate chunks
* No orphaned embeddings

---

## 11. Incremental Indexing

### Trigger conditions

* file added
* file modified
* manual reindex

---

### Optional future

```ts
watch(vaultPath)
  → detect file changes
  → enqueue ingestion job
```

---

## 12. Queue + Worker Model

### Required

* ingestion jobs should be async
* processed by worker

---

### Job structure

```ts
interface IngestionJob {
  knowledgeSourceId: string;
  filePath?: string;
  mode: "full" | "incremental";
}
```

---

### Flow

```text
enqueue job
  ↓
worker picks job
  ↓
process documents
  ↓
update DB + embeddings
```

---

## 13. Error Handling

### Failures

* file read errors
* parsing errors
* embedding failures

---

### Strategy

* log error
* mark document as failed
* continue processing

---

## 14. Performance Targets

| Operation          | Target   |
| ------------------ | -------- |
| Small vault ingest | < 5 sec  |
| Medium vault       | < 30 sec |
| Incremental update | < 1 sec  |

---

## 15. Observability

Track:

* files processed
* chunks created
* embedding latency
* errors per source

---

## 16. Integration with KnowledgeSource

Update fields:

```ts
knowledgeSource.indexStatus
knowledgeSource.lastIndexedAt
knowledgeSource.docCount
knowledgeSource.chunkCount
```

---

## 17. Phase Plan

### Phase 1 (Now)

* manual ingest command
* basic parsing + chunking
* embedding + storage

---

### Phase 2

* file watcher
* incremental indexing
* retry logic

---

### Phase 3

* multi-source ingestion
* cross-source linking
* ingestion prioritization

---

## 18. Strategic Role

This system is:

* The bridge between human knowledge and machine retrieval
* The foundation of Codexify’s “memory OS”
* The difference between static notes and living intelligence

---

## 19. Key Insight

Karpathy-style systems rely on:

* LLM restructuring
* implicit linking

Codexify adds:

* deterministic indexing
* scalable retrieval
* cross-source integration

---

## 20. Summary

> Ingestion determines what the system *knows*.
> Retrieval determines what the system *recalls*.
> ContextBroker determines what the system *understands*.

Together, they define Codexify’s intelligence loop.
