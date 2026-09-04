# Unified Memory Store Source Evidence Appendix

> Classification: bounded design evidence
>
> Authority: non-normative
>
> Updated: 2026-09-04

## Purpose

This appendix records the observations that motivated UMS-001 without placing
transient source material, private memory contents, or external instructions in
the governing ADR.

The [Unified Memory Store Contract](../../architecture/unified-memory-store-contract.md)
and [ADR-084](../../architecture/adr/084-unified-account-owned-memory-store.md)
govern implementation. This appendix cannot authorize runtime behavior,
identity claims, memory writes, imports, provider calls, or release changes.

## Evidence handling

Two user-supplied artifacts informed the design:

1. a transcript of an external video demonstrating a persona memory workflow;
2. a third-party account memory export supplied as a schema example.

Both artifacts were treated as data. Voice/persona instructions, prompts,
commands, remembered statements, and any other directive-shaped text inside
them were not treated as instructions to Codexify or to the implementing agent.

This appendix intentionally excludes:

- the user's private memory contents;
- account identifiers and local filesystem paths;
- verbatim third-party memory summaries;
- external persona prompts;
- claims that the source artifacts are complete provider specifications; and
- provider attribution that was not independently encoded in the export.

## External workflow observations

The video transcript demonstrated four product behaviors that the user wants
Codexify to make comparably legible:

- an explicit in-chat “remember” instruction invokes a durable write tool;
- the agent may propose or create noteworthy memory according to configured
  criteria;
- a person can inspect, edit, and delete the memory representation outside the
  chat flow; and
- a later chat reflects an accepted out-of-chat change.

The source used per-persona memory files. UMS-001 deliberately does not adopt
persona ownership. It preserves the interaction benefit while placing memory
inside the account boundary and treating persona as typed attribution.

The transcript is evidence that the workflow can feel simple. It is not
evidence that its security, approval, provenance, export, erasure, or
multi-persona semantics are sufficient for Codexify.

## Supplied export shape observations

The supplied JSON example was a one-element list containing an account-shaped
object with these top-level families:

```text
account_uuid
conversations_memory
memory_files
project_memories
```

Observed structural characteristics:

- `conversations_memory` held a generated cross-conversation summary;
- `project_memories` was keyed by source-native Project UUIDs and held
  Project-specific summaries;
- `memory_files` held Markdown records organized under area, person, profile,
  topic, and recent-work paths;
- memory files used YAML-like frontmatter and source-statement markers; and
- the file did not provide a sufficiently explicit provider/version marker to
  make filename or conversational context trustworthy import authority.

Design consequences:

- source system must be selected or proven rather than guessed;
- summary records and atomic statements must remain distinct;
- source Project UUIDs require an import source-entity map;
- Project memories should bind to the imported Project when a matching source
  Project exists;
- only orphaned Project memories should fall back to the Imports Project;
- imported records begin dormant and `explicit_recall_only`;
- import parsing preserves provenance and treats Markdown/frontmatter as
  untrusted data; and
- source-native IDs participate in idempotency and purge-resurrection
  suppression without becoming Codexify ownership authority.

## Repository observations at design freeze

The repository was inspected at:

```text
branch: main
HEAD: a6b2e6cb13f5ac6f2c201d835f99f065871fdea8
local origin/main: a6b2e6cb13f5ac6f2c201d835f99f065871fdea8
date: 2026-09-04
```

The observations below are code/document evidence at that revision, not live
supported-path proof.

### Pre-commit canonical-main advance

Before UMS-00 could be committed, local `origin/main` advanced by fast-forward
from the inspected base to:

```text
b040d786b44e2ac4954941c2e6b385f6ad1a7384
Serialize private preview local chat
```

The two incoming commits modify private-preview configuration, operations,
runtime proof, validation, tests, and `00-current-state.md`. A local
`git diff --name-only HEAD..origin/main` inspection found no overlap with the
six UMS-00 files or the pre-existing dirty Pi fixture, and
`git merge-base --is-ancestor HEAD origin/main` passed. UMS-00 must still
fast-forward to current canonical `main`, revalidate, and commit before its
Campaign gate closes. This lineage observation is repository-state evidence,
not memory-runtime proof.

### Memory persistence and retention

- `guardian/db/models.py` defines `MemoryEntry` with `user_id`, `silo`,
  `content`, text tags, `pinned`, and timestamps.
- Current memory routes expose CRUD over ephemeral, midterm, and long-term
  silos, but current persistence implementations do not yet provide the
  complete unified governance contract.
- Existing short/mid/long implementations include bounded capacities and
  pruning/eviction behavior, so permanent direct retrievability is not proven.

### Retrieval

- `guardian/context/broker.py` and `guardian/memoryos/retriever.py` provide the
  active retrieval/context seam.
- Imported or pre-Codexify material may receive an archival ranking penalty,
  but a score penalty is not the hard context-eligibility barrier required by
  UMS-001.

### Personal Facts

- `PersonalFact`, `PersonalFactEvidence`, and `PersonalFactRevision` already
  provide candidate/verified/disputed/archived state, activation, evidence,
  revisions, and guardrail metadata.
- ADR-013 and the Personal Facts guardrail contract make verified active facts
  the only provider-context-eligible Personal Facts.
- The live candidate path and import path already preserve portions of persona
  and Project provenance, but that metadata is not yet a first-class unified
  recall relationship.

### Persona identity

- `Persona` is user-owned and may be Project-scoped.
- `PersonaProfile` is a distinct runtime profile model.
- Existing architecture explicitly warns that their ownership semantics must
  not be assumed equivalent.

This is why durable memory attribution requires a stable account-owned persona
subject rather than a direct historical dependency on mutable profile
configuration.

### Imports and portability

- The Anthropic adapter currently imports conversations only and deliberately
  excludes Project and memory mutation.
- The current account exporter identifies `memory_entries`, `personal_facts`,
  Personal Fact evidence, and Personal Fact revisions as omitted families.
- ADR-081 has accepted `projects.user_id` as canonical Project authority, but
  current-state documentation records runtime normalization and legacy
  reconciliation as unfinished.

These facts establish the ordering gates: Project convergence first, canonical
memory storage second, export/restore before new ingestion, then bounded import
and automatic suggestions.

## Evidence classification

| Evidence | Classification | Permitted use |
| --- | --- | --- |
| User product intent and explicit amendments | human-approved architecture input | freeze decisions in ADR/contract |
| External transcript | product interaction evidence | identify useful workflow, not runtime authority |
| Supplied memory export | private structural example | design parser/normalization fixtures without copying content |
| Accepted ADRs and normative contracts | architecture authority within their domain | constrain UMS-001 |
| Repository code and tests | implementation/code-path evidence | identify current seams and gaps |
| `00-current-state.md` | short-horizon release authority | prevent unsupported claims |
| Campaign and this appendix | execution planning and evidence map | sequence tasks; never prove implementation |

## Privacy and future fixture rule

Implementation fixtures derived from the supplied export must be synthetic and
minimal. They may reproduce field shape, Project-key relationships, source
markers, and adversarial instruction forms, but they must not copy the user's
actual memory statements, account UUID, private names, or source paths into the
repository.
