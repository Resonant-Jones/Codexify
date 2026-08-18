# ADR-070: Browser Episodic Context and Recall Semantics

## Status

Proposed for architecture review.

## Date

2026-08-16

## Classification

Requires new ADR.

## Decision owners

- Human architecture authority: reviews and accepts this decision or a later
  superseding decision.
- Guardian runtime owner: owns authentication, policy, context, durable
  application persistence, chat lineage, and export/restore integration.
- Browser Host or extension owner: owns trusted browser orchestration,
  extraction, document-generation binding, and browser-origin transport.
- Browser profile/history owner: owns raw browser history and any profile
  lifecycle policy.
- Retrieval owner: owns later Browser Recall indexing and ContextBroker/router
  integration under a separate implementation review.

No individual names or runtime ownership assignments are fabricated by this
ADR.

## Supersedes

None. This ADR does not supersede ADR-054.

## Governing ADR and related contracts

- [ADR-054: Codexify Browser Host Topology and Release
  Ownership](./054-browser-host-topology-and-release-ownership.md)
- [Browser Authority and Context-Boundary
  Contract](../browser-authority-and-context-boundary-contract.md)
- [Browser Host and Guardian Contract Boundary](../browser-host-guardian-contract.md)
- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Retrieval Router Decision Table](../router-decision-table.md)
- [Data and Storage](../data-and-storage.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Continuity Storage Schema Proposal](../continuity-storage-schema-proposal.md)
- [Canonical Token Philosophy](../canonical-token-philosophy.md)

## Context

Codexify already has a private browser client boundary, future Browser Host
topology under ADR-054, bounded page extraction, a Browser Host/Guardian
contract, ordinary thread-backed chat, ContextBroker retrieval, and a
turn-scoped untrusted browser_context path. Those surfaces deliberately keep
page observation, attachment, persistence, identity/memory mutation, and
browser action authority separate.

A new product requirement needs a durable semantic boundary before feature
implementation:

- ambient browser interactions must remain chat-backed even when the browser
  surface is not conversational;
- selected or editable text plus a typed or voice instruction must be able to
  continue through normal Codexify thread/project/memory context;
- revisions and regenerations must continue from the same backing conversation;
- the backing thread must remain reopenable in normal Codexify chat;
- raw DOM and page furniture must remain ephemeral by default;
- the durable record must preserve the evidence that mattered to the
  interaction, not every value exposed to an extractor; and
- future browsing recall must be useful without silently turning browser
  activity into identity or personal memory.

The existing contracts do not by themselves authorize those new persistence
semantics. ADR-054 governs Browser Host topology and Guardian ownership, but it
does not decide Browser Episode retention, browser-history recall authority, or
the relationship between derived browsing activity and Codexify memory.

Current release truth remains unchanged: Browser Host and related browser
surfaces are not shipped Beta behavior. The current browser_context path is
turn-scoped, labeled as untrusted evidence, and intentionally does not prove
Browser Episode persistence or Browser Recall. The Continuity Context Packet
schema is a proposal only; no proposed continuity table is treated as live.

## Decision

Codexify adopts the following future architecture semantics.

### 1. Canonical concepts

The companion contract defines the following terms:

- Browser Observation: transient, bounded active-page observation.
- Semantic Page Payload: bounded relevant representation selected from that
  observation.
- Browser Episode: Guardian-owned durable, high-signal evidence of one
  user-initiated browser interaction linked to normal chat lineage.
- Ambient Browser Turn: a browser-surface-initiated normal Codexify user turn.
- Browser Recall: optional retrieval over minimized history metadata, episodes,
  and derived session summaries.
- Browser Artifact: separately authorized high-fidelity capture.

These are architecture concepts. This ADR does not create runtime tokens,
database tables, API routes, or schema names for implementation.

### 2. Normal chat is the continuity spine

Ambient browser interactions MUST use normal Codexify chat lineage:

- the authored instruction is a normal durable user turn;
- the assistant result uses the ordinary message/request/attempt lifecycle;
- one interaction sequence has one backing Codexify thread;
- later edits and regenerations may continue in that thread;
- the thread is reopenable in ordinary chat surfaces;
- Start fresh creates a new thread/lineage and does not delete the old one; and
- browser surfaces do not own a shadow transcript, queue, worker, or completion
  truth surface.

Browser-origin provenance may identify the entry surface, but it remains
subordinate to canonical chat thread/message state and does not change normal
chat roles or conversation-origin semantics.

### 3. Continuity is interaction-driven, not hostname-driven

No browser domain, hostname, URL, page title, or page content is a permanent
thread identity. There is no automatic domain-to-thread or domain-to-project
binding. A user-selected or trusted-client-selected thread/project is resolved
through canonical Guardian context machinery; page content cannot select it.

### 4. A clearly chat-backed action authorizes bounded Episode evidence

A trusted browser surface may present a clearly labeled Guardian action whose
product semantics explicitly state that the interaction is chat-backed. When
the user invokes it:

- the instruction is durable normal chat input;
- explicitly selected or editable text may be retained;
- the bounded Semantic Page Payload needed to preserve what the interaction
  addressed may become durable Browser Episode evidence;
- the resulting Guardian turns remain linked to the backing thread; and
- the user can inspect the retained history through normal Codexify chat.

The authorization is contextual and narrow. It covers only selected/authored
text and bounded relevant evidence needed to explain the interaction. It does
not authorize the rest of the page, raw DOM, page furniture, hidden state,
unrelated comments/ads/controls, credentials, passwords, cookies, storage,
unsubmitted unrelated form values, or arbitrary markup.

Raw page observation remains ephemeral by default. Full-fidelity screenshots,
PDFs, full documents, and page snapshots remain separately authorized Browser
Artifacts. Existing v1 Browser Host attachment remains ephemeral and
not_persisted; this ADR does not reinterpret that wire result as durable
persistence.

### 5. Exact evidence and derived summaries stay distinct

A Browser Episode should preserve exact relevant source excerpts when
practical, together with selected/authored text and source provenance. A
derived semantic summary is stored separately and links back to the retained
evidence. A summary cannot replace historical source evidence merely because
it is easier to retrieve.

The governing evidence doctrine is: save the evidence that mattered, not the
page furniture.

Every retained Episode must keep page content structurally labeled as
untrusted evidence. A page, model output, or generated draft cannot select
relevance, retention, project, thread, memory scope, or authority.

### 6. Browser Recall is a separate authority domain

The authority relationship is:

Page Observation Authority != Browser Recall Authority != Browser Action Authority

Browser Recall is explicitly opt-in, separately disableable and revocable,
independently deletable and correctable, retention-bounded, and provenance
aware. Page Observation Authority does not grant Browser Recall. Browser Recall
does not grant page-body capture, screenshot capture, or browser action.

Raw browser history remains browser/Browser Host profile state. It is not IDDB,
personal memory, a personal fact, ordinary project truth, or a durable
personality inference. Derived Browser Recall records are rebuildable
retrieval/continuity material and must never become the sole authoritative copy
of raw history.

Future recall records may contain normalized URL, hostname/origin, title,
observed/visited time, bounded session range, derived activity summary,
associated Browser Episode IDs, associated Codexify thread/message IDs, an
explicitly selected project association, and retention/provenance metadata.
DOM, screenshots, or page-body capture are not required for recall.

### 7. Normal context and retrieval policy remains authoritative

Ambient Browser Turns reuse canonical Guardian project, memory, thread, and
retrieval machinery:

- explicit project selection is resolved by normal Codexify context policy;
- prior chat and relevant personal memory are read only under existing policy;
- browser evidence is one labeled untrusted evidence source; and
- the browser interaction does not authorize memory mutation.

Visited pages, browsing behavior, derived session summaries, and generated
drafts cannot silently create personal facts, identity traits, personality
inferences, or IDDB writes. Any future router adoption for Browser Recall is a
separate retrieval-impact implementation task.

### 8. Freshness and stale-state rules are preserved

New invocations refresh page observation when document generation changes.
Editable-target grants are bound to origin, document generation, and relevant
fingerprint. A stale grant cannot overwrite newly changed user text. A new
capture creates new provenance, and an older Browser Episode is never silently
mutated to match the current page. Thread continuity does not reuse stale DOM.

## Authority model

Guardian retains policy and durable application persistence authority. The
browser/Browser Host owns transient page and profile state. Normal Codexify
chat owns the transcript. A derived Browser Recall index owns only rebuildable
retrieval material. A future Browser Action surface requires a separate
capability contract with explicit grant, origin binding, idempotency, retry,
cancellation, receipt, and audit semantics.

The main trust boundaries are user/trusted UI, Browser Host/profile,
remote-page renderer, network transport, Guardian application policy,
provider, and derived index. The threat model includes malicious pages,
prompt injection, stale documents, duplicate retries, partitions, and
honest-but-buggy extractors. Page-derived content is always evidence and never
authority.

## Data ownership

| Data | Canonical owner | Status under this ADR |
| --- | --- | --- |
| Normal threads/messages | Guardian / Codexify chat persistence | Existing conversation truth. |
| Browser Episode | Guardian durable application storage | Future, not implemented. |
| Raw Browser Observation | Browser Host/extension transient state | Ephemeral by default. |
| Raw browser history/profile | Browser/Browser Host profile | Future Recall source, not IDDB. |
| Browser Recall index/session summary | Derived retrieval state | Future, eventual and rebuildable. |
| Browser Artifact | Guardian artifact storage after explicit capture | Separate future artifact path. |
| Continuity Context Packet | Proposed future envelope | No table or runtime write exists. |

No parallel browser_memories canonical store is created. The Continuity Context
Packet proposal is a possible future envelope because it models payload,
summary, provenance, sensitivity, and retention, but it is not implementation
authority.

## Retention, deletion, and correction

Retention policies are separate for observation, chat, Browser Episode,
Browser Recall, Browser Artifact, and raw history.

- Normal Browser-backed thread deletion follows ordinary chat semantics.
- Deleting an Episode removes its evidence from future retrieval/recall and
  does not rewrite the external website.
- Correcting an Episode preserves correction lineage where audit policy
  requires it and does not silently replace historical evidence.
- Clearing browser history changes future Recall source availability but does
  not silently erase a separately retained chat turn or Episode.
- Recall indexes and session summaries are removable and rebuildable.
- Deleting a derived Recall row does not delete its source thread, Episode, or
  raw history.
- Browser Recall disablement stops future Recall activity and applies the
  separately disclosed removal/quarantine policy.
- Browser Artifacts follow their own deletion policy.

No convenience cascade crosses from derived recall to source chat, from raw
history to Guardian application state, or from page observation to identity or
memory state.

For consistency, chat/Episode lineage is a Guardian durable-write invariant;
raw history remains browser-local source truth; and Recall indexes/summaries are
eventual, idempotent, and rebuildable. Future adapters require idempotency
keys, replay-safe retries, bounded backoff, and an operator-visible dead-letter
or failure path.

## Export and restore implications

Guardian-owned Browser Episodes require lineage-preserving account export and
restore before runtime persistence is complete. Restore must preserve thread
and message relationships, source URL/title/time/provenance, selected/authored
text, retained evidence, summary-to-evidence links, and omission/truncation
metadata, including any local-ID remapping.

Raw browser profile/history state is not automatically part of
Codexify-Export.zip. Browser Host profile backup/export requires a separate
browser-profile contract. Derived Recall indexes may be rebuilt, but the
canonical inputs needed to rebuild them require an explicit ownership/export
policy. This ADR does not modify the Account Export + Restore Contract.

## Compatibility and migration implications

This ADR is documentation-only:

- no runtime migration exists;
- no database model, table, or index is selected;
- no browser-history import exists;
- no canonical runtime token is added;
- existing browser_context behavior remains unchanged;
- existing Browser Host protocol compatibility remains unchanged;
- existing message/request/attempt, queue, worker, and acceptance semantics
  remain unchanged;
- existing account export behavior remains unchanged; and
- current release/support configuration remains unchanged.

Future Browser Episode persistence, Browser Recall history access, canonical
tokens/schema, router integration, and export/restore support each require
separate reviewed implementation or contract slices. Rolling upgrades must
preserve older thread/message state and fail closed on incompatible Episode or
Recall schemas.

## Alternatives considered

### Treat raw browser history as ordinary Codexify memory

Rejected. Browser profile history has a different source owner, privacy
boundary, correction model, and retention policy. Treating visits as memory
would silently create identity, personality, or project claims.

### Persist every captured page or raw DOM snapshot

Rejected. It would retain page furniture, secrets, hidden state, unrelated
content, and prompt-injection material without a bounded user-authored reason.
It would also turn observation capability into silent archival authority.

### Store only an LLM-generated summary

Rejected. Summaries are derived interpretations and cannot replace exact
relevant evidence when source preservation is necessary for provenance,
correction, or user inspection.

### Give each domain or hostname a permanent thread

Rejected. Thread continuity should reflect an interaction sequence chosen by the
user, not a website taxonomy. A domain cannot select a project, thread, or
retention scope.

### Create a browser-only transcript

Rejected. It would split conversation truth, make normal chat reopening
ambiguous, and create duplicate request/attempt/persistence semantics.

### Make Browser Recall part of Page Observation Authority

Rejected. Page observation and history retrieval have different sensitivity,
source ownership, consent, retention, deletion, and export requirements.

### Use the proposed Continuity tables immediately

Rejected for this task. The Continuity Storage Schema Proposal is explicitly
docs-only and does not authorize migrations, models, or runtime persistence.

## Consequences

### Positive

- ambient browser work remains inspectable as normal Codexify conversation;
- users can preserve high-signal browser evidence without whole-page archival;
- exact evidence and derived interpretation remain distinguishable;
- browser history can later support useful recall without becoming identity truth;
- raw profile state, Guardian application state, and derived retrieval state have
  explicit owners;
- stale documents, duplicate retries, partitions, deletion, and export are
  named before implementation; and
- ADR-054's Browser Host topology and current v1 attachment compatibility are
  preserved.

### Costs and risks

- Browser Episode persistence requires a new Guardian-owned schema and
  export/restore surface;
- Recall requires a separate opt-in authority and browser-profile adapter;
- evidence minimization and relevance selection require careful security proof;
- derived summaries can be wrong and require correction/rebuild behavior;
- browser-origin presentation and thread selection need explicit UI work; and
- live Chrome/Safari, deletion, recovery, and privacy proofs remain open.

### Compatibility consequence

Acceptance of this ADR does not create a runtime, schema, support, or release
claim. It creates a durable boundary that future implementation must not
reinterpret casually.

## Explicit non-goals

This ADR does not authorize or implement:

- a browser extension, Browser Host edit, Chrome manifest, or Safari port;
- context-menu, inline-edit, editable-field replacement, or voice UI;
- history API access, browser-history import, or profile backup;
- a DOM reader, Semantic DOM implementation, or continuous capture;
- screenshots, PDFs, full-page archival, or artifact storage;
- Browser Episode database models, migrations, vector indexes, or routes;
- Browser Recall adapters, indexing, or session summarization;
- ContextBroker or retrieval-router behavior changes;
- memory, IDDB, personal-fact, persona, or identity writes;
- browser action/automation, autonomous browsing, or command-bus authority;
- account export implementation;
- new canonical runtime tokens;
- a hostname-to-thread binding; or
- a new release/support claim.

## Proof requirements

Future implementation tasks must prove:

1. separate Page Observation, Browser Recall, Browser Action, and Guardian
   connectivity permission states;
2. clearly labeled chat-backed user invocation;
3. normal durable thread/message/attempt lineage and normal-chat reopening;
4. bounded evidence preservation and exclusion of raw DOM, page furniture,
   credentials, hidden state, unrelated form values, and secrets;
5. summary-to-evidence provenance and explicit omission/truncation;
6. stale generation/fingerprint rejection without overwriting changed text;
7. user-selected project/context resolution and page-content non-authority;
8. opt-in, disable, revoke, retention, deletion, correction, replay, and
   rebuild behavior for Recall;
9. no silent identity, memory, personal-fact, or personality mutation;
10. Episode deletion without source-thread or external-site mutation;
11. lineage-preserving export/restore and raw-history ownership boundaries;
12. Browser Artifact separation; and
13. live proof for each claimed browser host, extraction mode, and recovery path.

Documentation, schemas, fixtures, focused tests, or a local scaffold prove only
their own surface. They do not prove shipped functionality or release support.

## Implementation sequencing

The companion contract records the prerequisite order. Each item is a separate
atomic task, not a task specification created by this ADR:

1. canonical Browser Episode contract/token/schema seam;
2. chat-backed Ambient Browser Turn API/runtime seam;
3. semantic extraction and stale-safe editable-target grant;
4. Browser Episode persistence plus export/restore;
5. browser-origin thread/UI provenance;
6. opt-in Browser Recall history adapter;
7. derived recall indexing and temporal/session summaries;
8. live Chrome/Safari proof; and
9. security, deletion, recovery, replay, partition, and export/restore proof.

No item may widen the supported release claim without the current-state and
supported-profile reconciliation required by the repository's release doctrine.

## Current-truth boundary and documentation follow-through

ADR-054 continues to own Browser Host technology, topology, repository
incubation, release ownership, and Guardian boundary. ADR-070 owns Browser
Episode and Browser Recall semantics. The Browser Authority and Context-Boundary
Contract remains the host-neutral observation/attachment boundary and now
cross-references this narrower durable-evidence decision.

Neither ADR proves shipped browser functionality. docs/architecture/00-current-
state.md remains release truth. No runtime/source file, migration, export
implementation, canonical token, or supported-profile setting is changed by
this ADR.

The required documentation routing is:

- the companion Browser Episodic Context and Recall Contract;
- the Browser Authority and Context-Boundary Contract cross-reference;
- the architecture README browser routing; and
- exactly one ADR-070 index entry.
