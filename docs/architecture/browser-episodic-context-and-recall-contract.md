# Browser Episodic Context and Recall Contract

## Status

- Classification: normative architecture contract; architecture-impacting.
- Governing decision: ADR-070: Browser Episodic Context and Recall Semantics,
  proposed for architecture review.
- Governing Browser Host topology: ADR-054: Codexify Browser Host Topology and
  Release Ownership.
- Implementation status: no Browser Episode persistence or Browser Recall
  runtime is implemented by this contract.
- Release status: not current runtime proof and not a supported-beta claim.

Normative terms such as MUST, MUST NOT, SHOULD, and MAY describe requirements
for future implementation. They do not assert present behavior.

## Purpose

This contract defines the semantic, authority, persistence, provenance,
retrieval, deletion, export, and continuity boundary for two future browser
surfaces:

1. chat-backed Browser Episodes that preserve the high-signal evidence of one
   user-initiated browser interaction; and
2. optional Browser Recall that can reconstruct prior browsing activity from
   minimized browser-history metadata and derived Browser Episode/session
   records.

The contract preserves the existing separation between browser observation,
ephemeral attachment, durable application persistence, identity/memory
mutation, and browser action authority. It adds a bounded persistence rule for
an explicitly invoked, clearly labeled chat-backed Ambient Browser Turn; it
does not authorize whole-page archival, continuous DOM capture, browser
automation, or silent history-to-memory promotion.

Repository presence, documentation, a Browser Host scaffold, the current
browser-context code path, or a focused test does not prove that Browser
Episodes, Browser Recall, or ambient browser editing are shipped.

## Scope and current-truth posture

This contract covers:

- the semantic distinction between Browser Observation, Semantic Page Payload,
  Browser Episode, Ambient Browser Turn, Browser Recall, and Browser Artifact;
- the observation-to-retention ladder from raw page observation to explicitly
  authorized durable evidence;
- chat-backed continuity for browser-origin interactions;
- reuse of normal Guardian thread, project, memory, and retrieval policy;
- Browser Episode evidence, provenance, omission, truncation, freshness,
  deletion, correction, and retention semantics;
- opt-in Browser Recall over minimized history metadata and derived episodes;
- conceptual storage ownership and consistency targets without choosing a
  final database schema; and
- future export/restore, privacy, security, proof, and implementation
  prerequisites.

This contract does not change:

- the current turn-scoped browser_context behavior;
- the v1 Browser Host/Guardian attachment wire contract, whose attachment
  retention remains ephemeral and whose receipt remains not_persisted;
- normal chat message, request, attempt, queue, worker, or acceptance
  semantics;
- the Browser Host topology or release ownership accepted by ADR-054;
- the existing retrieval-router or ContextBroker behavior;
- account-export implementation;
- Continuity Context Packet migrations, models, or runtime writes; or
- docs/architecture/00-current-state.md, which remains release truth.

## Architecture terms

These terms are canonical architecture concepts. They are not a new runtime
token registry. If repeated machine-readable values are needed in a later
implementation, that implementation MUST introduce them through the bounded
canonical-token process described by canonical-token-philosophy.md.

### Browser Observation

Browser Observation is a transient, bounded observation of the active page made
under Page Observation Authority. It may contain raw DOM, semantic DOM, visible
text, page metadata, accessibility/interaction structure when separately
authorized, or a transient extraction working set.

Browser Observation is evidence input, not durable Codexify state. Raw
observation is ephemeral by default and MUST NOT be treated as ordinary
memory, personal fact, identity, project truth, or Browser Recall history.

### Semantic Page Payload

Semantic Page Payload is the bounded representation selected from a Browser
Observation because it is relevant to the user's authored browser interaction.
It is semantic evidence, not a raw DOM snapshot. It may preserve selected text,
editable text, relevant source excerpts, bounded semantic structure, provenance,
and explicit omission/truncation metadata.

A Semantic Page Payload is not durable merely because extraction produced it. It
becomes durable Browser Episode evidence only under the explicit Ambient
Browser Turn rule in this contract or another separately accepted persistence
contract.

### Browser Episode

A Browser Episode is durable, high-signal evidence of one user-initiated browser
interaction, linked to normal Codexify thread/message lineage. It preserves
what materially mattered to the authored interaction: the user's instruction,
selected or authored text, bounded relevant source evidence, source provenance,
a separately labeled derived summary when one exists, and the resulting
Guardian turns.

A Browser Episode is Guardian-owned application evidence. It is not a browser
history mirror, an IDDB record, a personal fact, a personality inference, or a
replacement transcript.

### Ambient Browser Turn

An Ambient Browser Turn is a user-authored Codexify turn initiated from a
browser editing or context surface rather than the full Codexify chat UI. The
browser UI may be ambient and non-conversational, but the interaction remains
chat-backed: the authored instruction is a normal durable user turn in a normal
Codexify thread, and any assistant result follows normal chat lineage.

An Ambient Browser Turn is not a browser-only transcript, a hidden shadow
conversation, or a hostname-to-thread binding.

### Browser Recall

Browser Recall is an optional retrieval capability for finding or reconstructing
prior browsing activity from minimized browser-history metadata, Browser
Episodes, and derived semantic session summaries.

Browser Recall is a separate authority domain from Page Observation Authority
and Browser Action Authority. It is explicitly opt-in, independently
disableable and revocable, independently deletable and correctable, and
retention-governed. Browser Recall records are retrieval/continuity material,
not identity truth.

### Browser Artifact

A Browser Artifact is a separately authorized high-fidelity capture such as a
screenshot, PDF, full document, or explicit page snapshot. Browser Artifacts
follow their own capture, storage, retention, deletion, provenance, and export
rules. They MUST NOT be silently created as a side effect of an Ambient
Browser Turn or Browser Recall operation.

## Nodes, trust boundaries, and threat model

### Nodes and ownership boundaries

The future architecture may involve these nodes or state holders:

| Node or state holder | Owns or performs | Does not receive by implication |
| --- | --- | --- |
| User and trusted browser UI | Initiates the action, selects/editable text, writes the instruction, chooses a thread/project, and opts into Browser Recall. | Authority from page content or a hostname. |
| Browser extension or Browser Host trusted main process | Brokers Page Observation Authority, binds a capture to the active document, and transports bounded evidence. | Durable application persistence, identity mutation, or unrestricted browser action authority. |
| Remote page renderer | Produces untrusted page state for bounded extraction. | Guardian credentials, persistence authority, project/thread selection, or policy authority. |
| Normal Codexify client and chat surfaces | Displays and reopens canonical threads/messages and future provenance. | Ownership of a parallel browser transcript. |
| Guardian | Authenticates, applies policy, owns durable application writes, assembles context, and persists normal chat lineage. | Permission from page content or automatic authority from Browser Host reachability. |
| Browser profile / Browser Host history state | Remains the source of truth for raw browser history when a future Browser Recall adapter is explicitly enabled. | IDDB, personal-fact, project, or Codexify-memory status. |
| Browser Recall derived index | Provides rebuildable retrieval material from authorized inputs. | Sole authority for browser history or permission to mutate identity/memory. |
| Model provider | Reasons over labeled evidence Guardian deliberately includes. | Browser credentials, browser action authority, or persistence authority. |
| Guardian durable storage | Stores normal chat and explicitly authorized Browser Episodes/artifacts. | Permission to retain arbitrary extracted page state. |

### Trust boundaries

The implementation MUST preserve distinct boundaries even when components run
on one device:

- the user/trusted UI boundary;
- the browser profile and Browser Host boundary;
- the remote page/renderer boundary;
- the browser-to-Guardian network boundary;
- the Guardian policy and durable-application boundary;
- the model-provider boundary; and
- the derived-index boundary.

### Threat model

The baseline threat model includes honest-but-buggy clients, navigation races,
stale editable targets, duplicate retries, partial network failure, malicious
pages, prompt injection in page content, hostile or misleading history
metadata, and a compromised remote renderer. A compromised Guardian or trusted
application boundary is outside this contract's complete solution and requires
the existing Guardian/device security model.

The architecture MUST fail closed when a page, renderer, history entry, or
derived summary attempts to widen observation, choose persistence, select a
thread/project, mutate identity, or invoke an action. Prompt-injection
resistance MUST be structural: page-derived values remain labeled evidence
through extraction, transport, retrieval, and model assembly.

## Authority model

The following inequality is normative:

Page Observation Authority != Browser Recall Authority != Browser Action Authority

| Authority domain | Grants | Does not grant |
| --- | --- | --- |
| Page Observation Authority | A bounded, user-initiated observation of the active page/document. | Browser history access, durable persistence, memory writes, or browser actions. |
| Browser Recall Authority | Explicit access to minimized browser-history metadata and the derived Browser Recall surface, subject to retention and deletion policy. | Page-body capture, screenshots, identity inference, or browser actions. |
| Browser Action Authority | A future, separately contracted capability to perform a named browser action. | Observation, history access, durable evidence, or permission to infer user intent. |
| Guardian connectivity authority | Authenticated use of permitted Codexify application routes. | Page observation, Browser Recall, or durable retention by itself. |
| Ambient Browser Turn authorization | One clearly labeled, user-invoked chat-backed interaction and the bounded evidence needed to preserve what the interaction addressed. | Retention of the rest of the page, Browser Recall opt-in, action authority, or memory mutation. |
| Browser Artifact authorization | One explicitly authorized high-fidelity capture. | Ambient whole-page archival or Browser Recall. |

Page content, a URL, a title, a history entry, a model output, or a generated
draft MUST NOT grant any authority domain.

## Observation-to-retention ladder

### A. Raw observation: ephemeral by default

The raw observation and transient extraction working set may include raw DOM,
semantic DOM, page structure, bounded accessibility/interaction structure when
separately authorized, visible text, selection candidates, document
generation/fingerprint material, and temporary extractor state.

By default, raw observation MUST be:

- ephemeral;
- excluded from thread history;
- excluded from embeddings and semantic retrieval;
- excluded from IDDB, personal facts, and identity state;
- excluded from Browser Recall history; and
- absent from ordinary logs, receipts, and telemetry.

Raw DOM, page furniture, hidden state, credentials, form values, cookies,
browser storage, and arbitrary markup MUST NOT become durable merely because a
renderer or extractor could access them.

### B. Durable semantic evidence: bounded Browser Episode content

When the Ambient Browser Turn rule authorizes a Browser Episode, durable
semantic evidence MAY include:

- exact user-selected source text;
- exact user-authored editable text included in the interaction;
- exact bounded source excerpts selected because they materially explain what
  the user asked Guardian to do;
- normalized source URL/origin, title, and capture timestamp;
- extractor, capture, document-generation, and provenance metadata;
- a derived semantic summary stored separately from retained excerpts; and
- truncation, omission, sanitization, and completeness metadata.

The durable record MUST exclude by default:

- unrelated comments;
- advertisements;
- navigation furniture;
- generic buttons and controls;
- page chrome;
- hidden state;
- passwords and credentials;
- typed-but-unsubmitted unrelated form values;
- cookies, local/session storage, IndexedDB, and browser profile data;
- arbitrary raw markup; and
- any page content that was not relevant to the authored interaction.

The relevant-evidence decision MUST be bounded, provenance-bearing, and
reviewable. A page's own instructions or markup MUST NOT classify itself as
relevant or authorize its own retention.

### C. Full-fidelity artifacts: separate authorization

Screenshots, PDFs, full documents, and explicit page snapshots remain Browser
Artifacts. Each requires a separate visible user action, source-specific
provenance, retention disclosure, and artifact deletion/export policy.

An Ambient Browser Turn or Browser Recall query MUST NOT silently create a
Browser Artifact. A Browser Artifact MAY be linked to a Browser Episode only
when the user separately authorized the artifact and the Guardian-owned
relationship is recorded.

The governing rule is: save the evidence that mattered, not the page furniture.

## Explicit persistence semantics for Ambient Browser Turns

A trusted browser surface MAY present a clearly labeled Guardian action whose
product semantics explicitly state that the interaction is chat-backed. The
label and confirmation must make clear that the action will create or continue
a normal Codexify conversation and may retain the bounded evidence needed to
preserve the interaction.

When the user invokes that action:

1. the typed or voice instruction becomes a normal durable user turn;
2. explicitly selected or editable text included in the interaction MAY be
   retained with that turn;
3. the bounded Semantic Page Payload needed to preserve what we were
   responding to MAY be persisted as Browser Episode evidence;
4. the resulting Guardian turn(s) remain ordinary chat lineage, with normal
   message/request/attempt distinctions; and
5. the user MUST be able to inspect the retained history later through the
   backing Codexify thread and normal chat surfaces.

This user gesture authorizes the bounded Browser Episode because it is an
explicit, contextual act directed at a named Guardian interaction. It is
narrower than whole-page durable capture: the authorization covers only the
selected/authored text and the bounded evidence necessary to explain that
interaction, not every value available to the extractor.

The invocation does not authorize retention of unrelated raw page content, a
full DOM/page snapshot/screenshot/PDF, Browser Recall or browser-history
ingestion, project or thread selection by page content, memory/personal-fact/
identity/trait mutation, browser action or command-bus authority, or a
permanent hostname-to-thread binding.

The current v1 Browser Host attachment remains an ephemeral operation. Future
Browser Episode persistence MUST be a separately versioned Guardian-owned
write and MUST NOT reinterpret an existing not_persisted attachment receipt as
proof of durable persistence.

## Chat-backed continuity and provenance

### Normal conversation lineage

Ambient browser work MUST use normal Codexify conversation lineage:

- there is no stateless shadow conversation store;
- the browser surface does not own transcript truth;
- one Ambient Browser interaction sequence has one backing Codexify thread;
- subsequent edits and regeneration attempts MAY continue in that same thread;
- the same thread MUST be reopenable in normal Codexify chat surfaces;
- a user MAY intentionally switch to another thread or start fresh;
- Start fresh creates a new thread and interaction lineage without destroying
  the old thread; and
- pinning or opening the thread is presentation behavior, not persistence
  authority.

The normal chat contract remains authoritative for authored message identity,
request identity, attempt identity, queued acceptance, worker execution,
assistant persistence, replay, and completion state. Ambient entry does not
create a second queue, worker, completion lifecycle, or transcript format.

### Browser-origin provenance

Future durable lineage MUST be able to identify, without changing the normal
chat role model, that a thread or turn originated from or continued through a
browser surface. Provenance MAY support a future browser-origin badge, source
URL/title display on a relevant Browser Episode, Open in Chat, and an
inspectable evidence link from the thread history.

Browser-origin provenance MUST remain subordinate to canonical thread and
message records. It is not a new conversation-origin value, identity proof,
project binding, or permission grant.

### No hostname identity

There is no automatic example.com to thread X or reddit.com to project Y
binding. Thread continuity is interaction-driven, not hostname-driven.

- A hostname cannot select the backing thread.
- Page content cannot select the backing thread.
- Page content cannot select a project, persona, retention policy, or memory
  scope.
- Explicit project selection resolves through canonical Codexify project and
  context machinery.
- A user-selected or trusted-client-selected thread/project binding MUST be
  validated by Guardian rather than accepted from page content.

## Project, memory, and retrieval behavior

Ambient Browser Turns reuse normal Guardian context and retrieval machinery.
They do not create a browser-specific memory engine.

- An explicit project selection such as @ProjectName resolves through canonical
  Codexify project/context machinery.
- Project scope is user-selected or trusted-client-selected, never
  page-selected.
- Relevant personal memory MAY be read only under existing memory and retrieval
  policy.
- Relevant prior chat history MAY be read only under existing retrieval policy.
- Browser evidence is one labeled, untrusted evidence source alongside those
  sources.
- A Browser Episode does not automatically enter personal memory, IDDB, or
  personal facts.
- The browser interaction does not itself authorize memory mutation.
- No durable trait inference, personality inference, or personal-fact creation
  may be derived from visited pages, browsing behavior, or generated drafts.

The existing retrieval router remains the policy seam. A future Browser Recall
query may use an explicit timeline/provenance/recall posture, but implementation
MUST define that adoption in a later retrieval-impact task rather than silently
changing the current router. Browser Recall results MUST remain labeled as
derived browser evidence and MUST preserve source provenance.

## Evidence preservation and provenance

For a durable Browser Episode:

- exact relevant source excerpts SHOULD be preserved when practical;
- a derived semantic summary MUST be stored separately from source excerpts;
- the summary MUST NOT replace the historical source evidence;
- summary provenance MUST link back to the retained excerpts and their source;
- source URL, origin, title, and capture time MUST be recorded subject to
  approved minimization;
- extractor/capture identity and document generation/fingerprint MUST be
  recorded;
- omitted, sanitized, and truncated material MUST be explicit; and
- page content MUST remain structurally labeled as untrusted evidence.

An LLM-generated summary is an interpretation. It cannot become the only
record of what the user actually saw or selected when relevant source evidence
was retained.

At minimum, a conceptual Browser Episode record has these relationships or
fields, without selecting a final SQL schema:

| Conceptual field | Meaning |
| --- | --- |
| Episode identity | Immutable identity for one retained interaction evidence record. |
| Account scope | Guardian-owned user/account boundary. |
| Backing lineage | Normal Codexify thread ID, authored user message ID, and resulting Guardian message/attempt references. |
| User instruction | Exact user-authored instruction, with voice transcription only under a future authorized voice contract. |
| Selected/authored text | Exact text intentionally included, subject to secret/form-field exclusion. |
| Relevant source excerpts | Bounded exact evidence that materially explains the interaction. |
| Derived summary | Separate semantic interpretation with explicit source links. |
| Source provenance | URL/origin/title/time, capture mode, extractor identity, document generation/fingerprint, and transformation chain. |
| Omission/integrity metadata | Hash/length where appropriate, truncation, omitted material, sanitization, and completeness status. |
| Retention/deletion state | User-visible retention, expiry/deletion, correction, and retrieval eligibility. |

No conceptual field grants authority to the page or model.

## Freshness, generations, and stale state

The existing document-generation and fingerprint idea remains normative for
future Ambient Browser Turns:

- raw page observation MUST be refreshed for a new invocation when the
  page/document generation changes;
- a pending editable-target grant MUST be bound to document generation, origin,
  and relevant content fingerprint;
- a stale grant MUST NOT overwrite newly changed user text;
- a changed document or origin requires a new capture and new provenance;
- old Browser Episodes remain historical evidence and MUST NOT be silently
  mutated to match the current page; and
- browser thread continuity does not imply reuse of stale DOM or stale page
  context.

An update to the page creates a new observation and, if explicitly invoked and
retained, a new Browser Episode lineage. It is never an in-place rewrite of an
older episode merely because the hostname or thread is the same.

## Browser Recall authority and source ownership

### Separate, opt-in authority

Browser Recall MUST be explicitly opted into, separately disableable and
revocable, independently deletable and correctable, bounded by an account/user
retention policy, excluded from identity/personality/trait inference, and
governed by provenance and export/recovery rules.

Page Observation Authority MUST NOT silently imply Browser Recall Authority.
Browser Recall Authority MUST NOT silently imply permission to observe page
bodies, capture screenshots, or execute browser actions.

### Raw browser history

When a future Browser Recall adapter is explicitly authorized, raw browser
history remains browser/Browser Host profile state. It may contain a URL, title,
visit timestamp, and navigation/session metadata when available.

Raw browser history is owned by the browser profile/Browser Host source
authority. It is not IDDB, a personal-fact store, ordinary Codexify project
truth, a durable personality trait, or automatically part of
Codexify-Export.zip.

Clearing browser history changes source availability for future Browser Recall
rebuilds. It does not silently rewrite or delete a separately retained
user-authored chat turn or Browser Episode.

### Derived Browser Recall records

Derived Browser Recall records MAY index minimized history metadata, link
Browser Episode IDs to backing Codexify thread/message IDs, create bounded
semantic session/activity summaries, support retrieval and Open in Chat
reconstruction, and carry retention/deletion/correction/rebuild provenance.

Derived records MUST identify themselves as derived and rebuildable, preserve
source timestamps and provenance, remain distinguishable from raw history and
normal personal memory, never become the sole authoritative copy of raw
history, and never be promoted into IDDB, personal facts, project truth, or
personality inference merely because they are indexed or summarized.

## Minimum Browser Recall shape

The future architecture SHOULD support queries such as:

- What was that website I used when researching independent browser engines?
- What was I doing Tuesday night when I found that Safari extension article?
- Find the Reddit discussion where I was writing about identity and memory.
- Open the thread associated with that browser interaction.

A minimal derived recall record can represent:

- normalized URL;
- hostname/origin;
- title;
- observed/visited timestamp;
- optional bounded time range or session grouping;
- optional derived activity summary;
- associated Browser Episode IDs;
- associated Codexify thread/message IDs;
- explicit project association only when the user actually selected it; and
- source, derivation, retention, deletion, and correction provenance.

Browser Recall MUST NOT require DOM, screenshots, or page-body capture. URL
paths, query strings, fragments, titles, and summaries remain privacy-sensitive
and MUST be minimized according to a separately accepted recall retention
policy.

### Temporal and session summarization

Browser Recall MAY later derive bounded activity clusters such as:

Safari extension research — 22:04–22:47

These summaries are derived interpretations. Source history entries remain
separately identifiable; the time range and grouping method are provenance
bearing; summaries are correctable and deletable; summaries may be rebuilt
when source history or Browser Episodes change; and no summary may be promoted
into IDDB/personality truth merely because it exists.

## Storage ownership and consistency

This contract defines conceptual ownership only. It does not invent tables,
migrations, a final SQL schema, or a parallel browser_memories store.

| State | Source of truth / owner | Consistency target |
| --- | --- | --- |
| Normal chat threads/messages | Guardian-owned Codexify chat persistence | Strong lineage and ordinary chat semantics. |
| Browser Episode | Guardian-owned durable application evidence linked to thread/message lineage | Strong linkage at the durable write boundary; an episode is not reported as complete without an inspectable lineage result. |
| Raw Browser Observation | Browser/Host transient state | Ephemeral and generation-bound; stale observations are rejected. |
| Raw browser history/profile | Browser/Browser Host profile state | Browser-local source truth; availability may lag or partition from Guardian. |
| Browser Recall index/session summaries | Derived retrieval state | Eventual, idempotent, rebuildable, and never authoritative over raw history or chat. |
| Browser Artifacts | Guardian artifact storage after explicit capture | Strong artifact ownership/provenance under artifact policy. |
| Continuity Context Packets | Future storage envelope only if separately implemented | Proposal/reference only; no current table or runtime write. |

The Continuity Context Packet proposal is a natural future envelope because it
already models structured evidence, summary, payload, provenance, sensitivity,
and retention. It does not authorize treating continuity_context_packets or any
other proposed table as live.

Conflict policy:

- raw history conflicts resolve in favor of the browser profile source, with
  source timestamps and uncertainty preserved;
- Browser Episode conflicts resolve in favor of Guardian-owned explicit user
  turns and retained evidence, with correction lineage rather than silent
  overwrite;
- derived indexes and summaries may be recomputed from canonical inputs;
- a user correction to a derived summary MUST remain distinguishable from the
  original derivation; and
- a derived record MUST NOT delete or rewrite a source thread, episode, or
  browser-history row by convenience.

Future adapters MUST use idempotency keys, bounded retry/backoff, replay-safe
upserts, and dead-letter or operator-visible failure handling. A partition or
index lag is not permission to duplicate a Browser Episode or promote derived
data to authority.

## Retention, deletion, and correction

Retention is explicit per authority domain. Page observation, Browser Episode,
Browser Recall, Browser Artifact, normal chat, and raw browser history MUST NOT
share an implicit retention policy.

The following deletion effects are normative:

- deleting a normal Browser-backed chat thread follows ordinary Codexify thread
  deletion semantics;
- deleting a Browser Episode removes its retained evidence from future Browser
  Recall and other episode retrieval, subject to an explicit deletion receipt,
  but does not rewrite the external website;
- deleting/correcting a Browser Episode MUST preserve the fact that a lineage
  record was corrected or deleted where audit policy requires it, without
  retaining prohibited content;
- clearing raw browser history affects Browser Recall source availability but
  does not silently erase a separately retained user-authored chat turn or
  Browser Episode;
- derived Browser Recall indexes and session summaries MUST be removable and
  rebuildable;
- deleting a derived recall record MUST NOT implicitly delete its source chat
  thread, Browser Episode, or raw history;
- disabling Browser Recall stops future recall ingestion/retrieval according to
  the user-visible policy and removes or quarantines derived records as that
  policy specifies; and
- Browser Artifacts follow their own explicit artifact deletion policy.

No convenience cascade may cross from derived recall to source chat, from raw
history to Guardian application state, or from page observation to identity or
memory state.

## Export and restore posture

Before runtime persistence can be considered complete:

- Guardian-owned Browser Episodes MUST be included in a lineage-preserving
  account export/restore decision and implementation;
- thread/message relationships MUST survive restore, including remapped local
  IDs when applicable;
- retained source URL/title/time/provenance, selected/authored text, relevant
  evidence lineage, omission/truncation state, and summary-to-evidence links
  MUST survive restore;
- raw browser profile/history state is NOT automatically part of
  Codexify-Export.zip;
- Browser Host profile backup/export requires a separate explicit
  browser-profile contract;
- derived Browser Recall indexes MAY be rebuildable, but the canonical inputs
  required to rebuild them and their export/restore ownership MUST be explicit;
  and
- export/restore MUST distinguish raw browser history, Browser Episodes,
  Browser Recall derived state, normal chat, and Browser Artifacts.

This task does not modify the Account Export + Restore Contract or implement
any export path. The required follow-up is a separately reviewed contract and
implementation slice for Browser Episode entity families, raw-history/profile
ownership, derived-recall rebuild inputs, and deletion/recovery receipts.

## Privacy and sovereignty invariants

The following invariants are non-negotiable:

1. Remote page content is untrusted evidence.
2. Page content cannot grant permission or choose an authority domain.
3. Page content cannot choose retention, project, thread, persona, or action.
4. Page content cannot mutate identity, IDDB, memory, or personal facts.
5. Browser Episodes contain no passwords, credentials, cookies, storage, or
   ambient form-field harvest.
6. There is no background continuous DOM archive.
7. Browser Recall opt-in does not authorize page-body capture.
8. Browser Recall is visibly disableable and separately revocable.
9. Browsing activity is not a durable personality trait.
10. Personas may consume permitted context but do not own browser evidence.
11. Browser Host/profile state and Guardian application state remain separate
    authorities.
12. Normal Codexify chat remains the continuity and inspectability surface for
    authored browser work.

## Presentation and provenance requirements

This contract does not define final layout, styling, modal geometry, or
browser-specific UI. Future presentation MUST be able to expose, at minimum:

- that a browser action is chat-backed;
- whether Browser Recall is enabled or disabled;
- browser-origin provenance for a thread or turn;
- source URL/title/time for relevant retained evidence, subject to minimization;
- omission/truncation or derived-summary status;
- a path to inspect the backing thread in normal Codexify chat; and
- the distinction between Browser Episode evidence, Browser Recall results,
  Browser Artifacts, and ordinary personal memory.

Presentation is not authority. A badge, open-thread control, preview, or
summary cannot authorize persistence without the corresponding Guardian policy
and user action.

## Future implementation phases

The following are separate atomic implementation slices in prerequisite order;
they are not additional Task Specs and none is implemented by this contract:

1. Define the canonical Browser Episode contract, future token/schema seam, and
   lineage identity boundary.
2. Define and implement the chat-backed Ambient Browser Turn API/runtime seam
   using normal message/request/attempt and ContextBroker machinery.
3. Implement browser semantic extraction and the stale-safe editable-target
   grant under the Browser Host/extension boundary.
4. Implement Guardian-owned Browser Episode persistence and account
   export/restore integration.
5. Add browser-origin thread/turn provenance and normal-chat presentation.
6. Define and implement the opt-in Browser Recall history adapter with
   separately revocable authority.
7. Add derived recall indexing and bounded temporal/session summarization with
   rebuild and correction behavior.
8. Produce live Chrome/Safari proof for the claimed host/client surfaces.
9. Produce security, deletion, recovery, replay, partition, and export/restore
   proof.

Each slice requires its own scope, governing review, implementation proof, and
current-truth reconciliation. No phase promotes this architecture into the
supported Beta surface by acceptance alone.

## Required future proof surfaces

Before any implementation or product claim, the applicable tasks MUST prove:

1. separate Page Observation, Browser Recall, Browser Action, and Guardian
   connectivity permissions;
2. explicit user initiation and clear chat-backed semantics for Ambient Browser
   Turns;
3. exact user-selected/authored text preservation without unrelated-page
   retention;
4. raw DOM, secret, credential, storage, hidden-state, and unrelated-form
   exclusion;
5. normal Codexify thread/message/attempt lineage and thread reopenability;
6. stale document-generation rejection and no overwrite of changed editable
   text;
7. exact evidence plus separately linked summaries, omission/truncation, and
   source provenance;
8. user-selected project/context resolution and page-content non-authority;
9. opt-in, revocation, deletion, correction, and retention behavior for Browser
   Recall;
10. eventual/rebuildable derived-index behavior under retry, duplication, and
    network partition;
11. Browser Episode deletion without accidental source-thread or website
    mutation;
12. export/restore lineage for Guardian-owned episodes and explicit raw-history
    ownership boundaries;
13. no IDDB, personal-fact, personality, or identity mutation from browsing;
14. Browser Artifact separation; and
15. live proof for each claimed browser host, extraction mode, and recovery path.

Docs, schemas, fixtures, or a successful local unit test prove only their own
surface. They do not prove runtime persistence, recall, release support, or
end-to-end browser behavior.

## Current implementation posture and non-goals

What is true now:

- normal Codexify chat threads/messages are durable conversation state;
- the current browser-context path carries labeled, turn-scoped untrusted
  evidence and deliberately avoids silent memory/retrieval persistence;
- ADR-054 governs future Browser Host topology and Guardian ownership;
- bounded capture/extraction code records document generation/fingerprint and
  keeps current attachment explicitly ephemeral; and
- the Continuity Context Packet storage model is a proposal only.

What is not yet true:

- no Browser Episode persistence runtime exists;
- no Browser Recall runtime, history adapter, or semantic-session index exists;
- no ambient inline text-edit or voice-driven browser UI exists;
- no browser-origin thread metadata/token is implemented by this task;
- no raw browser history is Codexify memory; and
- no proposed Continuity table is a live persistence surface.

Non-goals of this contract include:

- browser extension, Browser Host, Chrome, or Safari implementation;
- history API access, browser-history import, or profile backup;
- DOM reader, Semantic DOM, editable-field replacement, or voice code;
- browser action/automation, autonomous browsing, or command-bus authority;
- database models, migrations, vector indexing, or Continuity table writes;
- ContextBroker or retrieval-router behavior changes;
- memory, IDDB, personal-fact, persona, or identity writes;
- account export implementation;
- screenshots, PDFs, or page archival;
- release/support configuration or a new Beta claim; and
- unrelated ADR/index or architecture-corpus cleanup.

## Governing and related sources

- docs/architecture/00-current-state.md
- docs/architecture/adr/054-browser-host-topology-and-release-ownership.md
- docs/architecture/adr/070-browser-episodic-context-and-recall.md
- docs/architecture/browser-authority-and-context-boundary-contract.md
- docs/architecture/browser-host-guardian-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/router-decision-table.md
- docs/architecture/data-and-storage.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/continuity-storage-schema-proposal.md
- docs/architecture/canonical-token-philosophy.md
- guardian/tests/core/test_chat_completion_browser_context.py
- browser_host/src/runtime/capture.js
- browser_host/src/runtime/remote-tab.js

docs/architecture/00-current-state.md remains the short-horizon release
authority. Acceptance of this contract or ADR-070 does not create runtime,
schema, export, recall, browser-host, or supported-release proof.
