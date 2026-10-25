# Saved Widget Contract

> Classification: architecture contract
> Status: proposed
> Implementation status: no saved-widget persistence, listing, invocation, revision, editing, or export path exists
> Normative language: "must", "must not", "should", "proposed", "deferred", and "future" are intentional contract terms
> Companion decision: [ADR-102](./adr/102-saved-widget-identity-and-revision-boundary.md)

Purpose: Define one coherent Codexify-native contract for promoting eligible generated UI into durable, account-owned, revisioned **Saved Widgets** that can be invoked from any thread and revised conversationally.

This is a docs-only contract. It establishes architecture, not capability. Nothing described here is implemented, and nothing described here widens current release support. [`00-current-state.md`](./00-current-state.md) remains release truth.

## Purpose

Codexify already renders generated UI inside Guardian Chat. That capability answers "can the model show me an interface right now." It does not answer "can I keep this interface and use it again next week, in a different conversation."

The Library taxonomy already approves a **Widgets** filter, but that filter is honest about being unavailable: the
[Library, Projects, Spaces, and Product Surface Contract](./library-projects-spaces-product-surface-contract.md)
records that no authoritative Widget backing record, persistence mechanism, or versioned listing endpoint exists, and
that *persisting, versioning, and listing saved Widgets requires a separate approved architecture-impact task*. This
contract is that task's architectural output.

## Scope

This contract governs:

- the classification of generated UI into resource categories;
- canonical identity, account ownership, provenance, and lifecycle for the saved category;
- immutable revision semantics;
- cross-thread invocation;
- conversational revision;
- the security authority under which a saved widget executes;
- how a future saved-widget source participates in the Library projection.

This contract does **not** implement any of it. It creates no table, route, migration, frontend component, prompt
change, or artifact wire-format change.

## Vocabulary

### The three resource categories

| Category | What it is | Durable identity | Own record | In Library |
|---|---|---|---|---|
| **Presentation Artifact** | The generated-UI payload as it exists today: a `cfy-ui` marker inside canonical assistant message content. | No. It inherits the owning message's identity. | No. | No. |
| **Widget Candidate** | A Presentation Artifact that the server has evaluated against the eligibility preconditions below and found eligible. | No. It is a pointer to an artifact in a message. | No. | No. |
| **Saved Widget** | A durable, account-owned, revisioned resource with an authoritative backing record, created only by explicit user promotion. | Yes. | Yes. | Yes, once implemented and proven. |

A **Widget Candidate** is a transient judgement, not a thing. It has no ID, no listing, no lifecycle, and no
persistence. It exists only to answer "may this artifact be offered to the user for promotion?" The moment the user
declines, nothing remains.

### The two axes are independent

The existing generative UI split — `native` versus `sandbox` — is an **execution mechanism** axis. It answers "what
runs this?" The three categories above are a **resource category** axis. It answers "what kind of resource is this?"

These axes are orthogonal and must not be collapsed:

- A `native` artifact renders first-party Codexify React code with validated props. A `sandbox` artifact renders
  model-authored untrusted code under containment. That is how it *executes*.
- A Presentation Artifact, Widget Candidate, and Saved Widget are about *ownership, durability, and reuse*. That is
  what it *is*.

In V1, saved-widget eligibility is restricted to `sandbox` artifacts, because the native registry
(`frontend/src/features/chat/components/generativeUi/nativeRegistry.tsx`) holds first-party components rather than
user-owned programs. The restriction is a **V1 eligibility rule**, not a statement that `native` and `sandbox` are
resource categories. The axes stay separate so a future native-component widget can be classified without
re-litigating the vocabulary.

### What is explicitly not a Saved Widget

The following remain Presentation Artifacts no matter how much they look like a widget, and are **not** eligible for
promotion in V1:

- **Static charts** — a `native` `chart.bar` rendering fixed data.
- **Rendered data tables** — a `native` `table.rows` rendering fixed rows.
- **Informational HTML cards** — a `sandbox` artifact with markup and styling but no executable behavior.
- **One-off presentation artifacts** — any artifact whose value is a single computation whose result is captured in
  the message.

The shared reason is not aesthetic. It is that a Saved Widget is defined by **reusable executable behavior**: it
accepts fresh user input and produces a new result, and it remains useful outside the conversation that produced it.
A chart of one dataset is a picture. A calculator is a program.

### Naming disambiguation

The product corpus already uses the word *Widget* for a second, unrelated concept. The
[Library, Projects, Spaces, and Product Surface Contract](./library-projects-spaces-product-surface-contract.md)
defines a **Widget / Space Module** as a declarative drag-and-drop composition primitive placed inside a Space
(Chat, Forum, Feed, Gallery, Table, Form, and similar). That is a *composition* primitive with bindings to Space
Data, Rooms, and Library resources.

A **Saved Widget** is a different thing: a durable account-owned revisioned program promoted out of Guardian Chat.

This contract therefore uses **Saved Widget** throughout for the resource described here, and reserves *Widget /
Space Module* for the Space composition primitive. The Library's approved **Widgets filter** — described in that
contract as "saved interactive resources that have durable, authoritative backing records" — is the filter over
Saved Widgets. Space installation of a Saved Widget is **not** authorized here and is listed as a non-goal.

## Eligibility

### Server-verified preconditions

A Presentation Artifact becomes a Widget Candidate only when the server has verified all of the following against
the artifact payload itself. These are **necessary conditions**, not a sufficiency claim.

| # | Precondition | Rationale |
|---|---|---|
| E1 | The envelope parses and validates under the existing envelope rules: known `version`, known `kind`, size within the existing caps. | A saved widget is durable. A payload the renderer would reject must never be stored as promotable. |
| E2 | `kind` is `sandbox`. | The native registry holds first-party components, not user-owned programs. |
| E3 | The executable payload is present and non-empty after normalization. | Informational HTML cards have no behavior to reuse. |
| E4 | The payload shows **no external-origin indicators**: no literal `http:`, `https:`, protocol-relative `//`, `ws:`, or `wss:` reference in markup, styles, or script. | A saved widget should be self-contained. This is an *eligibility indicator*, not a proof of network independence — see [Three separate boundaries](#three-separate-boundaries). |
| E5 | The source message is an assistant message that the server can link to a **completed, accepted Guardian completion attempt**. | Generated provenance must be server-proven, not client-asserted. See [Provenance](#provenance). |
| E6 | The artifact fits the existing artifact size caps. | A durable record must fit the bounds the renderer already enforces. |

E1, E2, E3, and E6 are structural properties of the payload and its envelope. E4 is an indicator derived from
static inspection. E5 is a property of the source message's lineage.

### Three separate boundaries

Three different questions are easy to conflate here, and this contract keeps them apart:

1. **Structural envelope validation** (E1, E2, E3, E6) asks whether the payload is well-formed and within bounds.
   It is decidable by parsing, and it is decidable exactly. A payload that fails it is not storable, not promotable,
   and not renderable.
2. **Self-contained resource eligibility** (E4) asks whether the program is *plausibly* self-contained, judged from
   static indicators in the payload. It is a **heuristic filter, not a proof**.
3. **Runtime CSP enforcement** is the actual network-denial boundary. The sandbox CSP — `default-src 'none'`,
   `connect-src 'none'` — is what denies network access when a widget runs, and it is unchanged by this contract.

The limit of (2) must be stated plainly, because getting it wrong would weaken the real boundary in (3):

> **Static inspection cannot prove that arbitrary JavaScript is network-independent.**

A payload can assemble a URL at runtime, derive one from encoded data, or reach the network through a channel no
string scan would flag. A clean E4 therefore means "no obvious external-origin reference", **not** "cannot make a
network request".

That is acceptable only because (3) exists and is not weakened. E4 keeps ordinary self-contained widgets free of
pointless failed requests and keeps obviously-offsite programs out of the candidate pool; it does not guarantee
network independence, and it is not the security control. **The runtime CSP is the security control.** If a future
implementation ever renders a saved widget on a path that cannot rely on (3), that path must fail closed rather than
fall back on E4.

### What the server cannot decide

A static check cannot establish **independent utility** — whether the program is genuinely useful in a different
conversation, or whether it is merely an animated readout of the data it was generated from. It also cannot
establish the user's intent to keep it.

Therefore:

- The preconditions are a **gate**, not a grant. Passing them makes the artifact *offerable*; it does not make it a
  Saved Widget.
- The **user's explicit promotion** is the sufficient decision.
- The model holds **no authority** in this chain. It cannot declare its own output eligible, trusted, saved, or
  approved, and it cannot cause a promotion to occur. There is no model-emitted marker, prompt directive, or
  metadata field that creates a Saved Widget.

This ordering is deliberate: a classifier that could be satisfied by the artifact's own content would be a
self-certifying trust path. A classifier that produces a *candidate* and a human that promotes it keeps the trust
decision with the human.

### Promotion is explicit

Promotion requires all of:

1. The authenticated account owns the source message's thread.
2. The server has resolved a Widget Candidate for the specific artifact.
3. The user performs an explicit save action on that specific artifact.
4. The user supplies a display name.
5. The server persists the immutable snapshot and moves the `current_revision` pointer.

Absent an explicit user action, no Saved Widget record is created, no revision is created, and nothing appears in
Library. A generated candidate never replaces a saved revision on its own.

## Ownership and identity

### Canonical identity

A Saved Widget has a **stable canonical resource identity**: a server-assigned, opaque `widget_id` that does not
change across revisions, renames, or placements.

It has a **source family** of `saved_widget`. Under the Library's
[resource identity rules](./library-projects-spaces-product-surface-contract.md#resource-identity-across-source-families),
its presentation key is therefore **source-family qualified** — `saved_widget:<widget_id>` — while the canonical
source ID is preserved separately and unchanged. Cross-source deduplication by raw ID alone remains prohibited.

### Account ownership

Ownership is **server-resolved from the authenticated transport**. It is never client-supplied, client-hinted, or
derived from a Project or thread.

This mirrors the reasoning behind
[ADR-081: Project Ownership Authority](./adr/081-project-ownership-authority.md): when a resource can be owned from
two durable representations, synchronizing them preserves the defect. A Saved Widget therefore has exactly one
ownership authority — the account.

### Project and thread associations are not ownership

A Saved Widget may be referenced from many Projects and threads. Those references are **placements**, not
alternative ownership authorities:

- Canonical identity stays single and stable.
- Ownership stays account-level.
- A widget placed in a Project is still owned by the account and is still one widget, not a copy.

Account ownership must not be confused with Project placement, and placement must not become a second co-authority
in the manner ADR-081 identifies for Projects.

### Provenance

Provenance answers *how this record entered the system*, and it is read only from authoritative server-owned
metadata. It is never inferred from a filename, a URL, a MIME type, a table name, or a client-supplied field.

The server-owned linkage available today is
`chat_completion_attempts.completed_message_id` → `chat_messages.id`
(`guardian/db/models.py:1348`), which binds one durable completion attempt to the message that attempt completed.
That linkage is what proves an assistant message was produced by a completed, accepted Guardian turn.

Therefore:

- A client-supplied `role`, an `extra_meta` field, or a request body that claims assistant authorship is an
  **untrusted claim** and is never provenance. `POST /chat/{thread_id}/messages` accepts a client-supplied `role`
  and client-supplied `metadata` (`guardian/routes/chat.py:2513`, `:2534`), so both are structurally forgeable.
- When the attempt linkage is established, the Saved Widget's provenance is **`generated`** (proven).
- When it cannot be established, provenance is **`unknown`**. It is never upgraded from a claim.
- Under E5, V1 promotion requires established linkage, so a Saved Widget in V1 always carries proven `generated`
  provenance.

The provenance snapshot is **denormalized into the widget's revision record at save time** — source thread, source
message, source attempt request ID, capture time — rather than held as a live join. This matters because the
referents are not durable: `chat_messages.thread_id` and `chat_completion_attempts.thread_id` both cascade on thread
deletion (`guardian/db/models.py:1341`, `:1413`).

### Source-thread deletion

Deleting the source thread **must not** delete, alter, or un-provenance a Saved Widget.

The source thread is provenance, not the storage authority. Once the widget is saved, the account-owned widget
record and its revision snapshots are the authority. The recorded source thread, message, and attempt identifiers
become **historical references whose referents may no longer exist** — exactly like an account's record of where a
file came from after the originating project is removed.

The account export and restore contract requires that restore not silently drop lineage. That is why the
provenance snapshot is copied forward at save time rather than joined at read time: a restore can rebuild the
provenance claim without the original thread.

### Lifecycle state

A Saved Widget has exactly one lifecycle state, and it is explicit rather than inferred:

| State | Meaning | Effect on the source payload |
|---|---|---|
| `active` | The widget is live, listed, invokable, and revisable. | Served normally. |
| `archived` | The widget is retained for history but withdrawn from the active surface and from new invocation. | Served to historical references only; not invokable for new turns. |
| `deleted` | The widget has been explicitly deleted. It survives as a tombstone for transcript and audit truth. | **Not served.** No read path returns the artifact payload. |

Lifecycle state is a property of the widget and is distinct from its revision history. Moving a widget between
states does not create, overwrite, or renumber a revision, and it does not rewrite the transcript. See
[Deletion and historical references](#deletion-and-historical-references).

## Revision semantics

The revision model follows the immutable-snapshot pattern already proven by Persona Profiles —
`PersonaProfile` with a `current_revision` pointer, and `PersonaProfileRevision` with a composite
`(profile_id, revision)` primary key holding an immutable `manifest_json` snapshot
(`guardian/db/models.py:4552`, `:4605`). That pattern is a **design reference only**; Saved Widgets are not coupled
to Persona Profiles and share no table, route, or lifecycle with them.

### Required concepts

| Concept | Rule |
|---|---|
| **Stable widget ID** | Server-assigned, opaque, never changes across revisions. |
| **Revision key** | `(widget_id, revision)`. Ownership is a property *of* the widget, not a component of the key, and revision numbering is scoped to the individual widget. |
| **Monotonic revision number** | Strictly increasing, server-assigned. Never client-chosen. |
| **Immutable revision snapshot** | The artifact envelope plus its provenance, stored once and never updated in place. |
| **Current revision pointer** | A single pointer on the widget record. It identifies the revision that new invocations resolve to. |
| **Revision creation provenance** | Every revision records the base it was created from and the context that created it. |
| **Edit base revision** | The revision the edit was based on. Required on revisions produced by an edit. |

The revision key is `(widget_id, revision)`. It is deliberately **not** `(owner_user_id, revision)`. Revision
numbering belongs to the individual widget, so two widgets owned by the same account each number their own
revisions from 1 without collision. Keying by owner would make revision identity depend on an ownership attribute
instead of the resource's own identity, and would let two same-account widgets collide on a revision number.

### Rules

1. **Historical revisions are never overwritten.** A revision snapshot is written once. Correcting a mistake creates
   a new revision.
2. **The current revision pointer only moves forward.** It never decreases.
3. **Existing invocations stay pinned.** An invocation resolves an immutable revision at invoke time and records
   that revision. Later revisions do not change what an existing invocation renders. A widget is not a live view of
   its newest revision.
4. **Restoration creates, never rewinds.** Restoring an older version creates a *new* revision whose payload equals
   the older revision's payload, with the current revision as its edit base. History is preserved and the pointer
   still moves forward. The pointer is never reset to an earlier number, and no historical revision is deleted.
5. **Concurrent revision conflict is explicit.** When a revision is committed with an edit base that is no longer the
   current revision, the commit is **rejected** with a stated conflict. The existing current revision remains
   intact and unchanged. The uncommitted candidate is not silently discarded and is not silently rebased; it is
   retained so the user can re-base it deliberately.
6. **This is not a version-control subsystem.** There are no branches, merges, diffs, rebase operations, tags, named
   versions, or commit graphs. The model is a linear monotonic revision sequence with one pointer, immutable
   snapshots, and explicit conflict detection — and nothing more.

## Invocation

### The invocation is a real user turn with a reference

A Saved Widget is invoked through an **explicit, authenticated, canonical resource reference**. It is *not* invoked by
replaying `serializeUiArtifact` into a user message, and it is *not* invoked by fabricating an assistant response.

The reason the naive approach does not work is structural, not stylistic:

- The generative UI renderer is mounted in the **assistant-message branch** of `ChatBubble`
  (`frontend/src/features/chat/components/ChatBubble.tsx:673`). The user branch renders document and attachment
  tiles, not generative UI artifacts.
- The inference path strips `cfy-ui` markers from message content before the provider sees it
  (`guardian/core/chat_attachments.py:146`). A marker carried in message content is therefore not a durable
  resource reference; it is display content that the provider never receives.
- Copying the program source into every invoking message would duplicate a multi-kilobyte payload per invocation
  and would enlarge the stored message row, which the generative UI contract already names as a known limitation of
  the in-content channel.

The invocation therefore carries a **reference**, and the approved revision supplies the payload.

### The invocation record

Invocation is a **canonical transcript record of an ordinary user turn** with an attached reference:

- The turn is a real user turn with real user content, written through the existing message path. No assistant
  response is synthesized, and no synthetic user turn is introduced.
- The reference travels in the message's existing structured metadata field (`chat_messages.extra_meta`), not in
  message content, so the program source is never copied into the message row. `extra_meta` already carries
  durable lineage and capture flags for other transcript record kinds
  (`guardian/db/models.py:1430`).
- The stored reference records the **resolved** widget ID and the **resolved** revision number, not the client's
  claim. The server resolves the widget, verifies account ownership, and canonicalizes the revision on write.
  Because `POST /chat/{thread_id}/messages` accepts client-supplied `metadata`
  (`guardian/routes/chat.py:2534`), a client-forged widget reference is untrusted input and must be resolved
  server-side before it is stored.
- The reference has two distinct projections, and neither carries program source, an artifact
  envelope, or a URL. The **persisted** form is structured data — the resolved widget ID, the
  resolved revision number, and the display name — and is machine-readable only. The
  **inference** form is a bounded descriptor line carrying the widget display name and the
  revision number.
- `extra_meta` is **not automatically provider-visible context**. It is a message-record field, and
  the inference path reads message *content*. A reference sitting in `extra_meta` therefore reaches
  the provider only if the inference assembly deliberately renders a descriptor for it, and the
  reference is otherwise invisible to the model. Nothing about the field's presence implies
  disclosure.
- An inference descriptor must be **server-resolved, authorization-checked, bounded, and
  canonicalized**. It is derived from the authoritative record at assembly time, not from the
  stored client-supplied claim. It states only the widget display name and the revision number, it
  is length-capped and control-character-stripped, and it is rendered as text rather than markup.
  **Client-supplied metadata cannot establish authority**: a forged reference is resolved against
  the record, and an unresolvable one yields no descriptor at all rather than a descriptor the
  client wrote.
- The inference form is what lets the model know that a widget is present in the conversation,
  which is what conversational editing depends on. Because it is part of the invoking turn's
  rendered inference content, it stays present in that thread's later turns.
- The inference assembler drops any message whose rendered inference content is empty
  (`guardian/core/chat_completion_service.py:5511`). An invocation turn therefore always renders
  a bounded, non-empty descriptor rather than an empty user turn, and a turn that carries no
  reference and no text contributes nothing to the provider context at all.

Normal inference **never receives widget program source**. That is the whole point of the split: the
model learns *that* a named widget revision is in play and can refer to it, while the executable
payload stays in the authoritative record. Supplying the source itself is the edit path's job, and
that path is separately authorized below.

### Rendering boundary

The widget is rendered by the **host**, from the authoritative record, through the **existing** containment path:

1. The host resolves the widget and the pinned revision through an account-authorized read.
2. The host renders the approved artifact payload using the existing renderer and the existing sandbox frame.
3. The program source is fetched at render time from the authoritative record. It is not stored in the message row
   and is not duplicated per message.

The rendering surface is the **user branch** of the transcript, alongside the existing document-context tile that
`openDocInThread` already produces (`frontend/src/components/persona/layout/AppShell.tsx:2991`). A saved-widget
reference is a user-side resource attachment in the same sense and follows the same human-initiated path.

### Required invocation properties

| Requirement | How it is met |
|---|---|
| Resolve account authorization | The read path resolves the authenticated account and refuses a widget not owned by it. |
| Resolve an immutable revision | The stored reference names a specific revision; the read returns that exact snapshot. |
| Render the existing approved artifact | The same artifact envelope and the same renderer and sandbox frame are used. |
| Preserve conversation lineage | The invocation is a normal message in the normal thread, in normal order. |
| Avoid copying program source into every message | Only IDs, a name, and a revision number travel with the message. |
| Avoid fabricating an assistant response | Nothing assistant-side is synthesized. |
| Survive reload and restart | The reference is persisted in a canonical message row and re-resolved on read. |

### Human-initiated first

Initial invocation is **human-initiated through Library**. The Library surface already has an established
"open in thread" precedent for documents; a Saved Widget follows the same path — select the widget, resolve the
revision, attach the reference, and let the user send the turn.

**Model-initiated discovery and invocation are deferred.** The model in a new thread is not told that Saved Widgets
exist, and cannot list, select, or invoke one. Two reasons, both grounded in the existing system:

- A system-prompt block would spend token budget on widget metadata and would place user-authored widget names
  into the prompt, which is an injection surface.
- A tool-rail path is provider-constrained: `guardian/tools/chat_exposure.py` advertises tools only to specific
  providers, which is the same reason the generative UI contract rode the system prompt rather than the tool rail.

A user-attached reference is deterministic and provider-independent. That is the V1 mechanism.

## Conversational editing

A user must be able to invoke a Saved Widget and then ask for it to be changed, in ordinary conversation.

### Lifecycle

```text
Invoke a saved revision
  → User requests a modification
  → Resolve the authorized source
  → Supply bounded source as edit context
  → Generate a candidate revision
  → Preview inside the existing sandbox
  → User explicitly approves the save
  → Commit an immutable next revision
```

### The edit-context path is an explicit exception

Normal conversation history continues to strip generated source before provider inference. The edit path is a
**separate, explicitly authorized, per-turn context assembly** — not a relaxation of the history path and not a new
marker in the artifact channel.

For the turn that requests the edit, and only that turn:

1. The server resolves the referenced widget and revision, and verifies account authorization.
2. The approved artifact source is supplied as **bounded edit context**: clearly delimited, explicitly labeled as
   untrusted widget source, and capped.
3. The model emits the modified program as an **ordinary `cfy-ui` sandbox artifact** in the same turn. The artifact
   wire format is unchanged, and the candidate renders through the existing renderer and the existing sandbox for
   preview.
4. The candidate is a Presentation Artifact. It is **not** a Saved Widget, has no widget identity, is not listed in
   Library, and is not persisted as a revision.
5. Only on **explicit user approval** does the server commit a new immutable revision, with the edited revision as
   its edit base, and move the current revision pointer.

### Failure behavior

- A failed edit **leaves the existing saved revision intact**. Nothing is partially applied.
- A generated candidate **never** automatically replaces a saved revision.
- If the model cannot accommodate the selected source within the available context capacity, the edit **fails
  explicitly** with a stated reason and the size involved. It does not silently truncate the source and proceed with
  a partial program, and it does not modify the saved revision.

### Prompt-injection exposure, stated plainly

Widget source is model-authored content and may contain instructions. When it is supplied as edit context, it is
untrusted input that could attempt to redirect the model.

Two gates protect the system here, and they are **different gates**:

- The **persistence gate** is human approval. No model output can create, save, revise, install, or publish a Saved
  Widget without it.
- The **execution-context gate** is authority isolation. Human approval does not protect the model's own context.

The persistence gate alone is insufficient, and this contract does not rely on it alone. A fully compromised edit
turn still produces only a candidate that a human must approve — but that turn already ran with untrusted
instructions inside the model's context, and it may already have exercised tool, connector, retrieval, or other
privileged authority in the same turn, before any human ever saw a candidate.

V1 therefore constrains a source-bearing edit turn as follows:

1. It is an **inference-only candidate-generation operation**. It produces candidate output and nothing else.
2. Widget source enters the turn as **delimited, labelled untrusted data**. It does not participate in instruction
   selection, and it does not establish or influence authorization.
3. Widget source **must not grant, request, or influence authority** for tools, connectors, retrieval, or any
   privileged action. The turn's authority posture is fixed before the source is attached, and is never derived from
   the source.
4. Where this isolation **cannot be enforced**, the operation **fails closed**. It does not proceed with source
   attached, and it does not degrade into a lesser capability.

This does not invent a second Guardian control plane. The isolation is a property of *how the edit turn is
assembled*, not a new authority registry: the turn runs under the completion path's ordinary authority posture, with
no tool, connector, retrieval, or privileged-action authority attributable to the source itself.

The widget's display name is the one piece of user-authored text that reaches the provider through the descriptor
path, so it is length-capped, control-character-stripped, and treated as text rather than markup.

## Runtime containment and security

A Saved Widget remains **untrusted executable content**. Promotion to a durable, reusable resource does not
promote its trust.

### Preserved without change

Every containment property of the existing sandbox applies unchanged to a saved widget, because a saved widget
renders through the same `SandboxFrame` path:

- opaque origin — `sandbox="allow-scripts"` only, with no `allow-same-origin`
  (`frontend/src/features/chat/components/generativeUi/SandboxFrame.tsx:283`);
- the restrictive document CSP, injected before any generated content, including `default-src 'none'`,
  `connect-src 'none'`, and no `unsafe-eval` (`SandboxFrame.tsx:39`);
- no Guardian credentials, no host filesystem access, no Tauri native capabilities, no privileged APIs, no network
  access;
- the existing validated bridge semantics — source-bound, session-bound, origin-checked, schema-validated messages,
  with an allowed action set of `resize` and `send_prompt`.

### Saving grants no new capability

- The bridge action set is **unchanged**. The sandbox gains no `save`, `revise`, `install`, `publish`, or
  `authorize` action.
- The **save control is host chrome outside the iframe**, and the save path is an authenticated host action. A
  model-generated button inside a widget therefore cannot save, revise, install, publish, or authorize itself.
- The artifact's own capability set is exactly what it had as a Presentation Artifact.

### Explicit launch, and instance destruction

- A saved widget's runtime **must not** start automatically every time a historical conversation is rendered. The
  invocation surface presents an explicit launch affordance; the program starts when the user activates it.
- A running instance is **destroyed on dismissal**, so no widget runtime outlives the surface that hosted it.

This also makes "a reopened widget starts with fresh runtime state" a **containment-derived property** rather than
only a policy: the opaque origin denies the frame access to host storage, cookies, `document`, and any host API, so
there is no durable per-widget runtime store for state to persist into.

### Future-proofing for audio and canvas

Web Audio synthesizers and small canvas games are the motivating examples, and neither needs a CSP change. What
that means, precisely, is that **no sandbox permission has to be widened to attempt them** — not that they are
proven to work.

#### Web Audio: unproven

Synthesizer compatibility is **unproven** and must not be claimed as working.

- Browser autoplay rules require a **user activation** to start an `AudioContext`. An explicit launch affordance
  is a host-side click, but **a host-side click is not the same thing as a user activation inside a newly created
  sandboxed iframe**, and this contract does not assert that it is. Whether the launch gesture carries into the
  frame, and whether an `AudioContext` can be created and resumed from inside it, is **not established here**.
- The explicit-launch requirement is therefore a **necessary condition for a future audio widget, not a sufficient
  one**. It guarantees the program is started deliberately; it does not guarantee audio can start.
- Synthesizer compatibility requires **real-browser evidence** of all of the following before it may be called
  proven:
  1. `AudioContext` creation and initialization inside the sandboxed frame;
  2. user-initiated playback and, where suspended, successful resume;
  3. containment — the frame remains opaque-origin, network-denied, and free of host API access while audio runs;
  4. cleanup — the audio context and its output are torn down when the running instance is dismissed.
- Until that evidence exists, a synthesizer is a **candidate program whose runtime behavior is unverified**. A
  candidate that cannot start its audio context must degrade honestly rather than appear to work.
- If the evidence shows that an audio widget genuinely needs a permission the sandbox does not grant, that
  expansion is **separately gated** and requires its own ADR. It is **not** authorized by this contract, and this
  contract does not pre-approve it.

#### Canvas

- Canvas drawing and pixel readback inside the frame require no additional permission under the current CSP, and
  `img-src data: blob:` already permits data-URL output. Canvas is **not** subject to the audio caveat above,
  because it does not depend on an autoplay user-activation policy.
- Canvas still inherits the same containment, the same explicit launch, and the same cleanup-on-dismissal rules as
  every other saved widget.

#### Shared boundary

Neither case requires `allow-same-origin`, `connect-src`, or `eval`, and none of those may be added for this
purpose. Any future need that would actually widen the boundary — `MediaRecorder`, persistent storage, network
access, or `allow-same-origin` — requires a **separate ADR** and is **not** authorized by this contract.

## Library participation

### Until implemented and proven, nothing changes

This contract does not make the Widgets filter available. Until the implementation lands **and** is proven:

- Widgets remains **unavailable**, with a stated reason.
- **No synthetic listing** is permitted.
- **No chat-message scraping** is permitted to populate the filter.
- `All` must **not** claim complete coverage of an unavailable source.

The Library's existing "unavailable is not empty" rule — a filter with no authoritative source reports coverage as
unavailable and never as complete — continues to govern. Promoting the filter requires implementation and proof, not
this document.

### How a future saved-widget source participates

| Concern | Rule |
|---|---|
| **Source family** | `saved_widget`. |
| **Presentation identity** | Source-family qualified: `saved_widget:<widget_id>`. Canonical source ID preserved unchanged. |
| **Resource type** | `widget`. |
| **Provenance** | `generated` when server-proven attempt linkage exists; otherwise `unknown`. Never inferred from storage location. |
| **Account scope** | From the existing authenticated transport. Library must not accept or forward a client-supplied user identity. |
| **Project/thread/unscoped scope** | Exactly one of a project, a thread, or unscoped — matching the existing Documents scope contract. Scope selects *placement*, not ownership. |
| **Completeness** | The source reports one of the five existing outcomes: `complete`, `empty`, `bounded`, `uncertain`, `failed`. Only `complete` and `empty` assert coverage. `All` is complete only when every contributing source is complete-or-empty. A source failure degrades that source only. |
| **Request discipline** | A filter requests only the sources it can consume. The Widgets filter requests only the saved-widget source. |

### Library stays read-only

Library performs **no mutation**. Creating, revising, renaming, archiving, and deleting Saved Widgets belong to an
**explicitly governed authoring and lifecycle path** — a separate operation with its own authorization — and not to
the Library projection. A Library entry is a view over an authoritative resource, never a second copy and never a
second ownership system.

## Lifecycle and portability

The following is the **intended future behavior**. None of it is implemented by this contract.

| Operation | Intended behavior |
|---|---|
| **Explicit save** | The user promotes an eligible artifact. Creates the widget record and revision 1, with a provenance snapshot. |
| **Revision creation** | A new immutable revision with an edit base. The current pointer moves forward. Historical revisions are preserved. |
| **Listing** | An account-authorized, project/thread/unscoped-scoped listing over the saved-widget source, reporting completeness honestly. |
| **Invocation** | A human-initiated reference from Library, resolved to an immutable revision, rendered through the existing containment. |
| **Revision history** | Any revision is addressable by widget and revision number, and its snapshot is immutable. |
| **Widget deletion** | Deletion is an explicit, authorized lifecycle action that moves the widget to `deleted`. The widget leaves the account's Library and becomes unservable, while the canonical identity and the historical transcript references survive as a tombstone. See [Deletion and historical references](#deletion-and-historical-references). |
| **Source-thread deletion** | Does not delete, alter, or un-provenance the Saved Widget. The provenance snapshot survives; the referents may not. |
| **Export and restore** | **Not supported.** Widget export and restore are not considered supported until separately implemented and proven, and until the account export and restore contract is amended to cover them. |

### Deletion and historical references

Deletion has two obligations that must both hold, and they are only compatible if the second is enforced by
*withholding the source* rather than by destroying the reference:

1. **The historical transcript reference is preserved.** The invoking message still exists, still records that a
   widget was invoked, and still names the widget and the revision it resolved. Deleting a widget does not rewrite
   history, and it does not fabricate a deletion of content already disclosed.
2. **The executable source stops being reachable.** After deletion, no historical reference may still be able to
   fetch and run the widget's program.

Therefore:

- Deletion moves the widget and its revisions out of the servable set. The canonical identity, the ownership, and
  the revision numbering remain addressable for audit and for transcript truth, but the **artifact payload is no
  longer returned by any read path**.
- A historical invocation of a deleted widget renders an honest **unavailable / tombstone state**: the transcript
  entry remains, the reference remains, and the surface states plainly that the widget was deleted.
- It **must not** render a successful widget, a cached or mirrored copy of the old program, a stored snapshot of the
  deleted source, or an empty frame that looks like a working program. Degrading to a visible tombstone is
  required; silently degrading to a blank or a broken frame is not.
- Deletion does not rewrite unrelated historical records, and it does not un-provenance anything else.

**Source-thread deletion is a separate operation and remains independent.** Deleting the thread a widget was
generated in does not delete the widget; deleting the widget does not delete the thread. They are independent
lifecycle events with independent effects, and neither implies the other.

The account export and restore contract's guarantees — preserve canonical state, preserve source provenance,
faithfully rehydrate, never silently drop lineage or ownership — continue to govern the export artifact as it
exists today. Adding Saved Widgets to it is a separate decision, not a consequence of this contract.

## Non-goals

This contract does not, and must not be interpreted as:

- implementing saved-widget persistence, listing, invocation, revision, editing, or deletion;
- adding a database migration, an API route, or a frontend component;
- changing the `cfy-ui` artifact envelope, the artifact wire format, or any model prompt;
- adding a host bridge action, loosening the sandbox, or granting any new capability to generated UI;
- making the Library Widgets filter available;
- authorizing Space installation, Space Modules, publishing, or network access for a widget;
- adding persistent widget runtime state, or a widget runtime that survives dismissal;
- building parameterized or template widgets with declared inputs;
- adding model-initiated widget discovery or invocation;
- adding widget export or restore, or amending the account export and restore contract;
- widening release support, changing the Beta support boundary, or altering the current release gate.

## Implementation sequence

A future implementation task should be staged, and each stage should be independently reviewable. This is a
recommendation for scoping, not authorization.

1. **Schema and server-side artifact validation.** A server-side envelope validator and the eligibility
   preconditions, with no UI. Note that the backend currently only *strips* `cfy-ui` markers
   (`guardian/core/chat_attachments.py:141`); it has no envelope validator, because every validation rule has lived
   in the frontend codec. A durable, cross-thread, account-owned record makes server-side validation necessary, and
   the two sides must agree — the same discipline the shared marker corpus already exists to serve.
2. **Save and list.** The save operation, the authoritative listing, and the Library source family, with honest
   completeness reporting.
3. **Invocation.** The Library-to-composer reference path, the host-side resolution and render, and the explicit
   launch affordance.
4. **Conversational editing.** The bounded edit-context assembly, the candidate preview, and the explicit approval
   and commit path.
5. **Lifecycle.** Revision history, deletion, and the export/restore amendment — the last of which is a separate
   decision.

## ADR impact

This contract is recorded by
[ADR-102: Saved Widget Identity, Classification, and Revision Boundary](./adr/102-saved-widget-identity-and-revision-boundary.md),
which is **Proposed**. Acceptance requires a separate explicit human architecture decision and does not follow from
this document's existence.

No accepted ADR is superseded by this contract. ADR-003, ADR-069, ADR-077, ADR-081, ADR-082, and ADR-091 remain in
force, and this contract is written to preserve them.

## Bottom line

Codexify should be able to turn a good generated program into a durable, reusable, revisable resource — but only
through a chain in which the machine narrows the options and the **human** decides.

The classification keeps three ideas apart that are easy to conflate: how a thing executes, what kind of resource it
is, and who owns it. The identity model gives that resource exactly one canonical ID, one account owner, one
immutable revision sequence, and a server-proven provenance snapshot that survives the deletion of the thread it
came from. The invocation model reuses the existing renderer, the existing containment, and the existing transcript
instead of inventing a parallel channel. The editing model grants exactly one bounded exception to the
source-stripping rule, and even that exception cannot save anything without a human.

Security is unchanged. A saved widget is still untrusted code in an opaque origin with no network, no credentials,
and exactly one bridge capability that can only ask a human to send a message. Saving it grants it nothing.
