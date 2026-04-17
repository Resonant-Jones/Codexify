Yes. A spec is the right next artifact.

Below is a repo-ready architecture/product spec for Chronicle that keeps it separate from identity, preserves lineage, and makes it retrievable without turning it into a second fake memory system.

Chronicle v1 Spec

Title

Chronicle v1: Derived Continuity Layer for Imported and Native History

Classification

Architecture-impacting product/runtime spec

Status

Proposed

Purpose

Chronicle is a derived, retrieval-visible summary layer that compresses large volumes of thread and import history into low-resolution continuity artifacts.

It exists to help Guardian answer questions like:
 • what have we been doing
 • what is the story so far
 • how did we get here
 • what changed recently
 • summarize this import
 • remind me what matters here

Chronicle is not the canonical source of truth. Canonical truth remains the underlying thread, message, document, and provenance graph. Chronicle is a generated orientation layer linked back to that source truth. This preserves Codexify’s provenance and restore guarantees, which require lineage, project membership, message structure, and imported-source context to remain explicit rather than silently collapsed into summaries.  ￼

Non-Goals

Chronicle v1 is not:
 • a replacement for raw chat history
 • an identity modeling system
 • a default always-in-prompt memory layer
 • a user-facing diary rewrite
 • an autonomous editing agent
 • a source of durable trait inference

This separation is important because Codexify already distinguishes chat history as diary/content from identity modeling layers, and does not treat chat logs as durable identity by default.  ￼

Core Thesis

Raw history is high resolution but costly to traverse.

Chronicle provides a compressed continuity layer that is:
 • derived from canonical source material
 • low-resolution by design
 • semantically searchable
 • explicitly lineage-linked
 • rebuildable when generation logic changes
 • optional in retrieval, not globally injected

Chronicle gives Guardian a faster orientation target for timeline and continuity questions while leaving deeper questions to ordinary RAG over original messages and documents.

User Value

Chronicle should improve:
 • import comprehension after ChatGPT migration
 • fast orientation in long-running projects
 • continuity across many threads
 • “story so far” recall
 • lower-latency recall on local models
 • clarity when the user asks for narrative continuity rather than exact transcript evidence

Architectural Position

Chronicle sits between raw stored history and retrieval-time context assembly.

It does not replace:
 • chat_threads
 • chat_messages
 • uploaded documents
 • project docs
 • provenance records

It adds:
 • derived summary artifacts
 • retrieval-visible continuity notes
 • lineage pointers back to source threads/messages/import batches

This is aligned with Codexify’s existing retrieval doctrine, which already distinguishes memory_recall, timeline_recall, and provenance as separate retrieval intents with local-first widening rules.  ￼

Canonical Definitions

Chronicle Entry

A derived artifact summarizing some bounded slice of history.

Continuity Query

A query whose intent is orientation, recap, narrative state, or historical trajectory rather than precise transcript recovery.

Source Truth

The underlying imported or native thread/message/document state from which a Chronicle entry is generated.

Lineage Link

A structured pointer from a Chronicle entry to the source thread IDs, message IDs or ranges, project IDs, document IDs, and import metadata that seeded it.

Chronicle Scopes

Chronicle entries may exist at these scopes:
 • thread: summary of one thread
 • session: summary of a bounded work session
 • day: summary of activity on a calendar day
 • project: rolling project continuity summary
 • import_batch: overview of one imported corpus or migration batch
 • workspace/global: optional top-level rolling summary across active work

Resolution Levels

Chronicle v1 supports two resolution levels:
 • low: short orientation summary, salient themes, major decisions, open loops
 • medium: same plus slightly richer timeline and references

Chronicle v1 should not attempt high-resolution reconstruction. The raw source corpus already exists for that.

Data Model

ChronicleEntry

type ChronicleScope =
  | "thread"
  | "session"
  | "day"
  | "project"
  | "import_batch"
  | "workspace";

type ChronicleResolution = "low" | "medium";

type ChronicleSourceKind =
  | "native_chat"
  | "imported_chatgpt"
  | "mixed"
  | "documents";

interface ChronicleLineage {
  threadIds?: string[];
  messageIds?: string[];
  messageRanges?: Array<{ threadId: string; startMessageId: string; endMessageId: string }>;
  projectIds?: string[];
  documentIds?: string[];
  importBatchId?: string;
  sourceKind: ChronicleSourceKind;
}

interface ChronicleEntry {
  id: string;
  scope: ChronicleScope;
  resolution: ChronicleResolution;

  title: string;
  summaryText: string;
  salientThemes: string[];
  majorDecisions: string[];
  openLoops: string[];
  canonicalTerms?: string[];

  lineage: ChronicleLineage;

  timeStart?: string;
  timeEnd?: string;
  generatedAt: string;
  generationVersion: number;

  supersedesChronicleId?: string | null;
  stale: boolean;

  projectId?: string | null;
  threadId?: string | null;

  sourceType: "chronicle";
  tags?: string[];
}

Storage Contract

Chronicle entries must be stored as derived artifacts, not as rewritten chat messages.

V1 may use either:
 • a dedicated chronicle_entries table, or
 • Codex/artifact storage with type=chronicle

Preferred behavior:
 • searchable by semantic retrieval
 • filterable by scope, project_id, thread_id, source_kind
 • explicitly marked derived
 • versioned by generation logic
 • safe to regenerate

Lineage Requirements

Every Chronicle entry must preserve enough lineage to answer:
 • what source material produced this
 • what project or thread it belongs to
 • whether it came from imported history
 • what exact messages or ranges it summarizes

This follows the same general design pressure already captured in Codexify’s artifact lineage model and export/restore contract, where artifacts must keep thread/message provenance explicit and navigable.

Generation Rules

Inputs

Chronicle generation may consume:
 • thread messages
 • imported thread/message history
 • linked documents when explicitly included
 • project grouping metadata
 • import-batch metadata

It must not consume by default:
 • private identity summaries
 • excluded diary threads
 • sensitive deep-identity outputs
 • inferred traits not already part of canonical stored state

Output shape

A generated Chronicle entry should include:
 • concise summary
 • themes
 • major decisions
 • unresolved items
 • optional vocabulary/canonical terms
 • structured lineage metadata

Retrieval Behavior

Chronicle is not injected by default into every completion.

It becomes eligible when the query intent suggests continuity or orientation, for example:
 • “what are we doing”
 • “what’s the story”
 • “where did we leave off”
 • “summarize the import”
 • “what changed this week”
 • “remind me what matters here”

Suggested retrieval order for continuity intent

For continuity-oriented prompts, preferred retrieval posture is:

active_thread_messages -> chronicle -> thread_semantic -> project_docs -> broader local retrieval

This stays compatible with the existing local-first retrieval posture and keeps Chronicle as an accelerator rather than a replacement.  ￼

UX / Behavioral Contract

Chronicle should create the appearance of recall without falsifying provenance.

When Chronicle is used in an answer, Guardian should remain able to:
 • ground back to source truth if asked
 • follow semantic hits back into raw messages and documents
 • acknowledge when the Chronicle summary is low-resolution

Chronicle should feel like shorthand notes pinned around the system, not a magical second consciousness.

Import-Specific Behavior

When ChatGPT history or other external history is imported, Chronicle generation should support:
 • per-thread imported summaries
 • per-batch import summary
 • optional chronological “import story” summary
 • theme extraction across imported threads

This gives the user a way to ask not only “search the import,” but also “what was the arc of the import?”

Native Ongoing Behavior

For native Codexify usage, Chronicle generation should support:
 • end-of-session summary
 • end-of-day summary
 • rolling per-thread continuity summary
 • rolling per-project continuity summary

Rebuild / Regeneration Policy

Chronicle entries are derived and must be rebuildable.

When summarization logic changes:
 • old entries may be marked stale
 • regeneration may produce a new entry that supersedes the old one
 • lineage to the old entry should remain explicit when needed

No silent mutation of derived continuity artifacts.

Exclusion Rules

Chronicle generation must honor any existing exclusion boundaries, including:
 • threads excluded from identity modeling
 • diary/private threads if configured to stay out of derived modeling
 • archived or filtered material when scope rules exclude it

This keeps Chronicle from becoming a side-channel that ignores user intent around modeling boundaries. The IDDB policy already establishes that some threads may be excluded from modeling layers while remaining searchable as plain history.  ￼

Versioning and Auditability

Each Chronicle entry must record:
 • generation version
 • generated timestamp
 • source scope
 • lineage payload
 • staleness flag
 • supersession pointer if replaced

This keeps the layer inspectable and safe for future export/restore inclusion.

Export / Restore Expectations

Chronicle is a derived artifact and should be exportable, but restore must preserve:
 • its derived status
 • lineage metadata
 • source relationships
 • enough metadata to rebuild or invalidate it

This is consistent with the export/restore contract’s requirement that artifact relationships, provenance, and semantic equivalence remain explicit.  ￼

Constraints
 • Chronicle must not silently replace source truth
 • Chronicle must not become identity truth by accident
 • Chronicle retrieval must remain scoped and intentional
 • Chronicle generation must preserve provenance
 • Chronicle entries must be cheap enough to retrieve on local-first setups
 • Chronicle must tolerate long-running local jobs

Open Questions
 • Should Chronicle live as a first-class table or as a codex/artifact type?
 • Should continuity retrieval get its own retrieval intent token?
 • Should import-batch Chronicle be generated synchronously after import, or queued?
 • Should rolling project Chronicle be append-only or periodically recomputed?
 • Should Chronicle entries be visible in Workspace later, or remain backend-only initially?

Recommended V1 Cut

Include
 • thread Chronicle
 • day/session Chronicle
 • import-batch Chronicle
 • lineage metadata
 • semantic retrieval eligibility
 • rebuild/version metadata

Exclude
 • UI surface
 • automatic always-on prompt injection
 • autonomous Obsidian editing
 • identity synthesis
 • user-facing Chronicle editor

Success Criteria

Chronicle v1 succeeds if:
 • a long imported history can be summarized into retrievable continuity entries
 • Guardian can answer “what’s the story so far?” faster and more coherently
 • Chronicle-backed answers remain traceable back to real source threads/messages
 • the system does not blur continuity summaries into identity inference
 • the layer improves orientation without increasing hallucinated certainty

Implementation Recommendation

This should be done as an architecture-impact Codexify task because it touches:
 • retrieval posture
 • artifact/storage semantics
 • provenance guarantees
 • possible export/restore considerations
 • future operator truth surfaces