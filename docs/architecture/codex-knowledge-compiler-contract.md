# Codex Knowledge Compiler Contract

> Classification: architecture contract
> Status: draft
> Implementation status: docs-only contract. This document defines concept and boundary only; it does not introduce runtime implementation.

## Title and Status

- Title: `Codex Knowledge Compiler Contract`
- Classification: `architecture contract`
- Status: `draft`
- Implementation posture: docs-only contract; no runtime implementation is introduced by this document

## Purpose

Codex Knowledge Compiler is the reusable, scoped compilation engine that may later transform raw project, workspace, system, or domain source material into reviewed, provenance-aware, retrieval-efficient knowledge artifacts and scoped agent knowledge graphs.

This contract generalizes the repeatable Codex Wiki / LLM Wiki / compiled project memory pattern without limiting Codexify to Obsidian, Markdown, or any single source substrate.

This document is intentionally architectural and future-facing. It does not claim runtime behavior, release support, or proof beyond the current Codexify truth surfaces.

## Non-Goals

This task does not:

- add runtime code
- add database tables
- add migrations
- add API routes
- add workers
- add cron jobs
- add UI
- enable graph writes
- change retrieval routing
- change `ContextBroker` behavior
- change identity modeling
- change persona ownership
- connect the local-model draft adapter to scheduling, publishing, Heartbeat, command dispatch, or release approval
- claim public release readiness

## Vocabulary

The following terms are canonical for this contract:

| Term | Meaning |
|---|---|
| `Codex Knowledge Compiler` | The future reusable engine that compiles bounded source material into reviewable knowledge artifacts under an explicit scope policy. |
| `Knowledge Scope` | The read/write boundary that defines what source material a compilation run may inspect and what artifact surfaces it may later affect. |
| `Source Adapter` | The future normalization seam that turns source-specific material into the compiler's conceptual source shape without changing source-of-truth ownership. |
| `Knowledge Source Item` | One normalized source record eligible for discovery, hashing, extraction, provenance, and compilation. |
| `Compiled Knowledge Artifact` | A derived, provenance-bearing output produced by the compiler, still distinct from raw source material. |
| `Retrieval Card` | A compact retrieval-oriented artifact meant to make later retrieval more efficient without replacing raw provenance. |
| `Concept Node` | A conceptual graph node representing an extracted concept, entity, topic, or durable semantic anchor. |
| `Relationship Edge` | A conceptual graph edge representing a typed relationship between nodes or artifacts. |
| `Compilation Run` | One bounded execution attempt over a declared scope, trigger, and source set. |
| `Review Gate` | The checkpoint that decides whether compiler output stays draft-only, is approved, or is policy-eligible for later publication. |
| `Publisher` | The future seam that may materialize approved outputs into durable compiled-memory, retrieval, or graph-bearing surfaces. |
| `Maintenance Finding` | A derived issue that reports drift, staleness, contradiction, orphaning, or other follow-up conditions discovered during compilation or maintenance. |
| `Scope Policy` | The rules that bound scope-local reads, writes, exclusions, review posture, and future publication behavior. |
| `Compiler Budget` | The bounded limits for one run, such as source count, model calls, wall time, artifact count, or write operations. |
| `Compiler Proof Surface` | The durable evidence record required to explain what a run discovered, skipped, proposed, approved, published, and refused. |

If any of these terms later become runtime literals, event names, statuses, or other branch-bearing values, they must graduate into the appropriate canonical token registry before spreading through routes, workers, queues, or UI surfaces.

## Scope Model

The compiler is scope-aware. The first conceptual scope kinds are:

- `project`
- `workspace`
- `system`
- `domain`

These scope kinds are not implementation claims. They are the first contractual read/write boundary vocabulary for future work.

| Scope kind | What it may read | What it may write | Likely cadence | Review requirement posture | Examples |
|---|---|---|---|---|---|
| `project` | Project-bound threads, project documents, project artifacts, project-local notes, project-local audits, and project-local repo evidence that policy allows | Draft compiled artifacts, proof records, and later approved project-scoped outputs only within the same project boundary | Manual or changed-source-triggered is likely; continuous background execution is not implied | Human review is the default posture unless a future narrow policy explicitly approves auto-publish for low-risk outputs | A project wiki draft, project decision digest, project retrieval cards |
| `workspace` | Same-user local workspace material such as workspace-local notes, repo files, local documents, or local audits allowed by policy | Draft workspace-scoped artifacts, proof records, and later approved workspace-local outputs | Manual, scheduled, or changed-source-triggered is possible later; none are implemented here | Review must remain explicit when workspace data could widen recall or durable memory | A workspace-local knowledge pack, Obsidian-backed draft index, repo knowledge cards |
| `system` | Codexify-owned system docs, audits, architecture notes, runbooks, and runtime evidence that governance later permits | Draft system knowledge artifacts, proof records, and later approved system reference outputs | Likely periodic or release-triggered in the future | Review should be strict because system-scoped output can look authoritative | A release-readiness digest, architecture reference cards, operator maintenance findings |
| `domain` | A declared bounded corpus for a topic, client, field, or knowledge domain that policy explicitly scopes | Draft domain artifacts, proof records, and later approved domain-specific knowledge outputs | Manual or scheduled is plausible later | Review must verify that domain outputs stay attributable and do not impersonate canonical truth | A domain glossary, contradiction report, domain concept graph draft |

## Pipeline Model

The reusable future pipeline is:

`discover sources -> normalize -> detect changes -> extract -> relate -> compile -> review -> publish -> retrieve -> maintain`

| Phase | Purpose | Allowed side effects for this future phase | Prohibited side effects | Required provenance expectations |
|---|---|---|---|---|
| `discover sources` | Enumerate candidate source items within the declared scope and policy boundary | Discovery logs, candidate lists, and bounded proof metadata | Hidden widening beyond scope, silent source mutation, durable publication | Every candidate must be attributable to a scope kind, scope id, and source origin |
| `normalize` | Convert source-specific material into the conceptual source shape used by later phases | Ephemeral normalization output, hashes, and proof metadata | Rewriting raw sources, silently dropping provenance, declaring normalized shape as source-of-truth | Normalized items must preserve enough provenance to jump back to raw origin |
| `detect changes` | Determine which sources are new, changed, unchanged, excluded, or stale for this run | Change summaries, hashes, skip reasons, and proof metadata | Guessing changes without evidence, mutating raw content to force diffs | Hashes, timestamps, and exclusion reasons must remain traceable per item |
| `extract` | Derive candidate summaries, decisions, concepts, facts, or issue signals from normalized source items | Draft extraction artifacts and proof metadata | Durable publication without review, subjective labeling without policy support | Every extracted proposal must point back to the contributing source items |
| `relate` | Propose semantic relationships across extracted items, concepts, decisions, or artifacts | Draft relationship proposals and proof metadata | Treating proposed relationships as canonical truth, emitting graph writes by default | Each proposed relationship must record why it exists and which sources support it |
| `compile` | Assemble higher-level artifacts optimized for later review, retrieval, or graph use | Draft compiled artifacts, retrieval-card proposals, and proof metadata | Overwriting raw sources, publishing by implication, widening retrieval policy | Compiled artifacts must preserve source coverage and derivation lineage |
| `review` | Decide whether draft outputs stay draft-only, are approved, or are blocked | Review notes, approval metadata, rejection metadata | Silent approval, policy bypass, retroactive provenance rewriting | Review decisions must remain attributable to reviewer identity or policy source |
| `publish` | Materialize approved outputs into future durable artifact surfaces | Explicit writes to approved durable surfaces, bounded indexes, or portable artifacts if later implemented | Publishing unreviewed output by default, widening release claims, bypassing exclusions | Published outputs must preserve source provenance, review state, and publication context |
| `retrieve` | Make approved artifacts available to future retrieval or lookup flows if governance later permits | Retrieval-visible indexes or cards for approved outputs only | Implicit retrieval visibility for draft artifacts, bypassing retrieval policy, treating searchability as proof of use | Retrieval-visible outputs must retain provenance and approval state |
| `maintain` | Detect drift, contradictions, stale artifacts, orphaning, or recompile needs over time | Maintenance findings, re-review flags, and proof metadata | Silent auto-rewrite of published truth, hidden background widening | Maintenance output must explain what changed, what is stale, and which sources or artifacts were examined |

## Source Adapter Contract

Future source adapters should normalize source material into a shape conceptually equivalent to:

```ts
type KnowledgeSourceItem = {
  sourceId: string;
  scopeKind: "project" | "workspace" | "system" | "domain";
  scopeId: string;
  sourceType:
    | "thread"
    | "message"
    | "document"
    | "artifact"
    | "obsidian_note"
    | "repo_file"
    | "audit"
    | "external";
  title?: string;
  contentRef?: string;
  contentHash: string;
  createdAt?: string;
  updatedAt?: string;
  provenance: {
    threadId?: string;
    messageId?: string;
    projectId?: string;
    artifactId?: string;
    documentId?: string;
    filePath?: string;
    url?: string;
  };
};
```

The exact runtime type may differ later. The provenance requirements do not. A future implementation may rename fields, add fields, or encode them differently, but it must preserve the ability to attribute source origin, scope, and derivation without collapsing raw source ownership.

## Output Artifact Contract

The first conceptual output families are:

| Artifact family | Purpose | Source provenance requirement | Review posture | Retrieval-visible before approval |
|---|---|---|---|---|
| `CodexEntryDraft` | Human-readable draft entry that packages a bounded compiled result for review or later save behavior | Must point to the source scope and contributing source items or ranges | Draft-only by default | No |
| `SourceSummary` | Condensed summary of one source item or a tightly bounded source set | Must preserve item-level provenance and content-hash linkage | Review required before durable publication | No |
| `ConceptCard` | Reviewable concept artifact describing an extracted concept and why it matters | Must cite supporting source items and conflicting evidence when present | Review required | No |
| `DecisionRecord` | Extracted or compiled record of a project, system, or domain decision with provenance | Must preserve source decision lineage and decision-confidence basis | Review required, especially when it could look authoritative | No |
| `RetrievalCard` | Compact retrieval-oriented artifact that later helps retrieval efficiency or explainability | Must preserve source lineage and approval state | Review required before any retrieval visibility | No |
| `RelationshipEdge` | Proposed relationship between concepts, artifacts, or decisions | Must preserve supporting source references and relation rationale | Review required before durable graph or retrieval use | No |
| `MaintenanceFinding` | Issue artifact reporting drift, staleness, orphaning, or policy follow-up needs | Must identify the examined artifact/source set and the evidence for the finding | Review recommended; policy may later allow low-risk auto-publish with strict proof | Not by default |
| `ContradictionFinding` | Issue artifact reporting competing claims, conflicting decisions, or unresolved semantic conflict | Must preserve all materially conflicting source references | Review required | No |

## Review Gate Doctrine

- Unreviewed compiler output is draft-only by default.
- Publishing to durable compiled memory requires an explicit review or a policy-approved auto-publish rule.
- Identity-sensitive or user-trait-like output must not bypass IDDB policy.
- Diary, excluded, and private-source policies must be respected.
- No durable subjective labels may be created without explicit consent and policy support.

Review gates exist to keep compiled knowledge attributable and reversible instead of silently turning draft interpretation into canonical truth.

## Scheduling and Budget Doctrine

Future compiler runs may be:

- manual
- scheduled
- changed-source triggered
- event triggered

This contract does not implement scheduling.

Future runs must declare and respect bounded budgets, including:

- max sources per run
- max model calls
- max wall time
- max artifacts
- max graph edges
- max retrieval cards
- max write operations

Every future recurring compiler run must use leases or equivalent ownership to prevent duplicate concurrent runs for the same scope.

## Proof Surface

Any future implementation must provide a durable compiler proof surface that records at least:

- scope kind and scope id
- run id
- trigger kind
- source candidates discovered
- changed sources detected
- sources skipped with reasons
- draft artifacts generated
- artifacts approved
- artifacts published
- retrieval cards generated
- graph edges proposed or emitted
- budget used
- errors and retry posture
- provenance summary
- policy exclusions
- review status

Debug traces are diagnostic only and cannot replace durable run or proof records.

## Invariants

The following invariants are non-negotiable:

- The compiler is scope-aware but domain-agnostic.
- Scopes configure what may be read and written; scopes do not fork compiler logic.
- Raw sources must not be overwritten by compilation.
- Published compiled artifacts must preserve source provenance.
- Reviewable drafts must remain distinguishable from confirmed or published knowledge.
- Identity modeling must remain governed by IDDB policy.
- Personas may consume scoped compiled knowledge but must not own user identity.
- Graph writes remain default-off unless governed by graph-write contracts and runtime flags.
- Retrieval policy remains governed by the retrieval router and `ContextBroker` contracts.
- Route or queue acceptance must not be represented as completed compilation.
- No future background loop may silently widen the release promise.

## Relationship to Existing Systems

This contract relates to the current architecture as follows:

- Codex entries and thread-artifact lineage:
  compiled outputs may later produce Codex-entry-like drafts or saved artifacts, but lineage must remain source-addressable and export-safe. This contract does not claim a live Codex Knowledge Compiler path today.
- `ContextBroker` and retrieval router policy:
  future compiler outputs may later become retrieval inputs or retrieval aids, but retrieval policy remains separately governed by ADR-004, the retrieval router decision table, and current `ContextBroker` doctrine.
- workspace-local Obsidian retrieval:
  workspace-local retrieval is already its own supported runtime seam. This contract does not redefine Obsidian selection, injection, or proof; it only reserves a future source-adapter lane that could normalize workspace-local note material under explicit scope policy.
- vector retrieval:
  future approved artifacts may later become retrieval-efficient surfaces, but this contract does not change vector-store behavior, indexing, or retrieval visibility.
- optional graph context:
  the compiler may later propose concept nodes or relationship edges, but graph writes remain governed by existing graph-write contracts and explicit runtime flags.
- command bus and future tool/workflow plugins:
  future compiler tooling may eventually use plugin or command-bus-adjacent lanes, but plugin sovereignty, permissions, lineage, and runtime-binding rules remain governed by ADR-010 and related contracts.
- cron and scheduling:
  future recurring compilation may use scheduling, but no scheduler contract or implementation is introduced here.
- local-model draft adapter:
  future low-risk draft generation may eventually consume local-model lanes, but the current local-model draft adapter remains internal or manual only and is not connected here to scheduling, publishing, command dispatch, Heartbeat, or release approval.
- export and restore provenance:
  if compiled artifacts later become portable account state, they must preserve provenance, lineage, relationship semantics, and restore behavior consistent with the account export and restore contract.

Unimplemented relationships remain future-facing and must not be presented as release truth until they are separately proven.

## First Implementation Slice Recommendation

Recommended next slice:

`Project-scoped Knowledge Compiler dry-run harness`

That dry-run should:

- load a small bounded set of project, thread, message, and document source items
- normalize them
- detect changed sources by hash
- produce draft artifact proposals in memory or test fixtures
- return a proof report
- perform no durable writes except optional test-only fixtures
- not change retrieval behavior
- not publish artifacts
- not emit graph writes

This slice is recommended because it exercises scope policy, provenance, change detection, draft generation, and proof reporting without widening the supported runtime promise.

## Implementation Note: Backend Dry-Run Harness

A backend-only dry-run harness now exists under `guardian/knowledge_compiler/`.

It proves only:

- project-scoped source normalization contracts
- deterministic hash-based change detection
- draft-only compiled artifact proposals
- dry-run proof report shape

It does not prove:

- persistence
- routing
- retrieval behavior
- scheduling
- graph writes
- model execution
- UI review
- publication
- export/restore inclusion
- autonomous maintenance

Validation command used:

- `pytest -v tests/knowledge_compiler/test_dry_run.py`

Test file path:

- `tests/knowledge_compiler/test_dry_run.py`

Future live behavior still requires separate implementation work and the documentation follow-through described below. This dry-run harness is proof of a pure backend seam only; it is not a release promise.

## Documentation Follow-Through

Future implementation tasks should update related architecture docs only when live behavior changes:

- `00-current-state.md` only when runtime behavior changes
- `flows.md` when a live flow exists
- `data-and-storage.md` when persistence changes
- `router-decision-table.md` if retrieval routing changes
- `runtime-protocol-token-contract.md` if new statuses, events, or machine-readable values become runtime tokens
- `account-export-restore-contract.md` if compiled artifacts become portable account state

## Governing References

- [`00-current-state.md`](./00-current-state.md)
- [`router-decision-table.md`](./router-decision-table.md)
- [`runtime-protocol-token-contract.md`](./runtime-protocol-token-contract.md)
- [`account-export-restore-contract.md`](./account-export-restore-contract.md)
- [`self-extending-agent-plugin-system.md`](./self-extending-agent-plugin-system.md)
- [`delegation-runtime.md`](./delegation-runtime.md)
- [`adr/004-retrieval-policy-as-control-plane.md`](./adr/004-retrieval-policy-as-control-plane.md)
- [`adr/010-self-extending-agent-plugin-system.md`](./adr/010-self-extending-agent-plugin-system.md)
- [`adr/015-continuity-engine-working-set-and-decay-contract.md`](./adr/015-continuity-engine-working-set-and-decay-contract.md)
- [`adr/016-continuity-governance-surface-contract.md`](./adr/016-continuity-governance-surface-contract.md)
- [`adr/024-context-command-active-connector-semantics.md`](./adr/024-context-command-active-connector-semantics.md)
- [`adr/029-codex-entry-command-first-draft-flow.md`](./adr/029-codex-entry-command-first-draft-flow.md)
