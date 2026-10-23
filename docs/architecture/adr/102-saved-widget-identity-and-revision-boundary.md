---
tags:
* architecture
* adr
* generative-ui
* library
* guardian
* identity
* revision
* security
aliases:
* ADR-102
* Saved Widget Identity, Classification, and Revision Boundary
---

# ADR-102: Saved Widget Identity, Classification, and Revision Boundary

## Status

Proposed. Not accepted. Acceptance requires a separate explicit human architecture decision.

## Date

2026-10-23

## Companion contract

[Saved Widget Contract](../saved-widget-contract.md)

## Context

Codexify can generate interactive UI inside Guardian Chat. The
[Generative UI Contract](../generative-ui-contract.md) governs that channel: a `cfy-ui` marker inside canonical
assistant message content, a native component registry for first-party renderers, a sandboxed `srcdoc` frame for
model-authored code, a bounded host bridge whose single capability prefills the composer rather than sending, and
provider-side stripping of artifact source before inference.

That capability answers *"can the model show me an interface right now."* It does not answer *"can I keep this
interface and use it again next week, in a different conversation."*

Three facts make the gap structural rather than a missing feature:

1. **Artifacts have no durable identity.** An artifact is part of the canonical assistant message's own content. It
   is owned by that message and that thread. There is no resource that can outlive its message, be named, be listed,
   or be resolved later.
2. **The Library already claims the filter and honestly refuses it.** The
   [Library, Projects, Spaces, and Product Surface Contract](../library-projects-spaces-product-surface-contract.md)
   approves four filters including **Widgets**, and records that no authoritative Widget backing record, persistence
   mechanism, or versioned listing endpoint exists. It requires that persisting, versioning, and listing saved
   Widgets happen under a separate approved architecture-impact task, and that the filter must never be filled by
   synthesizing or scraping chat-message artifacts.
3. **A trusted-looking program is currently disposable and thread-scoped.** The security posture of generated UI
   assumes a narrow blast radius: one message, one thread, stripped before inference, with a bridge that can only
   ask a human to send. Promoting such a program to a durable, cross-thread, user-invoked resource changes that
   posture, so the promotion boundary must be decided deliberately rather than by accident of implementation.

The motivating use cases are categorically different from what generative UI currently produces. A trip calculator
with reusable equations and fresh inputs, a synthesizer with controls and locally generated audio, and a small
browser game with reusable rules are **programs**, not one-off charts, tables, or informational cards. They are
valuable precisely because they are reusable and accept fresh input, and that property — not the fact that they
contain UI — is what makes them worth keeping.

Several product questions were already resolved by the human before this decision, and are treated as settled input
rather than open questions: widget runtime state need not persist; a reopened widget starts with fresh runtime
state; widgets must be reusable across conversations; any invoked widget can be reworked conversationally;
revisions must be durable and independently addressable; saving and revising require explicit user action; static
charts and one-off visualizations are not reusable widgets merely because they use generative UI; and no new ambient
sandbox permissions are authorized.

What remained open is the architecture: classification, identity, ownership, provenance, revision semantics,
invocation, editing, and security authority. This ADR settles that architecture and defers all implementation.

## Decision

### 1. Classification is explicit and enforceable

Three resource categories are distinguished, and the existing `native`/`sandbox` split is explicitly **not** one of
them:

- **Presentation Artifact** — the generated-UI payload as it exists today. No durable identity, no own record, not
  listed anywhere.
- **Widget Candidate** — a Presentation Artifact the server has evaluated against eligibility preconditions and
  found eligible. A transient judgement with no ID, no record, and no persistence.
- **Saved Widget** — a durable, account-owned, revisioned resource with an authoritative backing record.

`native` versus `sandbox` is an **execution mechanism** axis. The three categories are a **resource category** axis.
The axes are orthogonal. Rendering type and resource category must never be conflated, and a Saved Widget is not
defined by how it renders.

V1 eligibility is restricted to **self-contained sandboxed interactive programs**. Static charts, rendered data
tables, informational HTML cards, and one-off presentation artifacts are not Saved Widgets, however much UI they
contain. The shared reason is reusable executable behavior: a Saved Widget accepts fresh user input, produces a new
result, and remains useful outside the conversation that produced it.

### 2. Classification never grants the model authority over its own trust

Eligibility is evaluated by the **server** against the artifact payload, as a set of necessary conditions: the
envelope parses and validates; the kind is `sandbox`; the executable payload is present; the payload references no
external origin; the size is within the existing caps; and the source message is linked by the server to a completed,
accepted Guardian completion attempt.

Passing those conditions makes an artifact **offerable**. It does not make it saved.

**Explicit user promotion is the sufficient decision.** No model-emitted marker, prompt directive, or metadata field
can create a Saved Widget, and a generated candidate never replaces a saved revision on its own. A classifier
satisfied by the artifact's own content would be a self-certifying trust path; a classifier that produces a
candidate and a human who promotes it keeps the trust decision with the human.

### 3. One canonical identity, one account owner

A Saved Widget has a stable, server-assigned, opaque canonical ID that survives revisions, renames, and
placements, and a source family of `saved_widget` whose presentation key is source-family qualified as
`saved_widget:<widget_id>`, with the canonical source ID preserved separately and unchanged.

Ownership is **server-resolved from the authenticated transport** and is never client-supplied, client-hinted, or
derived from a Project or thread. Project and thread associations are **placements**, not alternative ownership
authorities: a widget may be referenced from many Projects and threads without duplication of canonical identity.

Provenance is read only from authoritative server-owned metadata. The linkage available today is
`chat_completion_attempts.completed_message_id` → `chat_messages.id`. A client-supplied `role` or `extra_meta`
field is an untrusted claim and is never provenance. Provenance that cannot be established is `unknown`, never
upgraded from a claim.

The provenance snapshot is **denormalized into the revision record at save time** rather than held as a live join,
because the referents cascade on thread deletion. Deleting the source thread does not delete, alter, or
un-provenance a Saved Widget: the source thread is provenance, not the storage authority.

### 4. Revisions are immutable, monotonic, and linear

The revision model follows the immutable-snapshot pattern already proven by Persona Profiles — a stable record
with a `current_revision` pointer, and revisions keyed by `(owner_id, revision)` holding an immutable snapshot — as
a **design reference only**, with no coupling to Persona Profiles.

A Saved Widget has a stable widget ID, a strictly increasing server-assigned revision number, an immutable revision
snapshot, a current-revision pointer, revision creation provenance, and an edit base revision.

- Historical revisions are never overwritten; corrections create new revisions.
- The current-revision pointer only moves forward.
- **Existing invocations stay pinned** to the revision they resolved at invoke time. A widget is not a live view of
  its newest revision.
- Restoring an older version **creates** a new revision with that payload rather than rewinding the pointer or
  deleting history.
- A commit whose edit base is no longer current is **rejected as an explicit conflict**; the current revision
  remains intact and the candidate is retained for deliberate re-basing.
- This is **not** a general version-control subsystem: no branches, merges, diffs, rebase, tags, or named versions.

### 5. Invocation uses a canonical reference, not a replayed artifact

A Saved Widget is invoked through an explicit, authenticated, canonical resource reference. Replaying
`serializeUiArtifact` into a user message does not work and is not the design: the generative UI renderer is
mounted in the assistant-message branch of `ChatBubble`, and the inference path strips `cfy-ui` markers, so a
marker carried in message content is display content rather than a durable resource reference. Copying program
source into every invoking message would also duplicate a multi-kilobyte payload per invocation.

Invocation is therefore a **canonical transcript record of an ordinary user turn with an attached reference**. The
turn is real, no assistant response is synthesized, and no synthetic user turn is introduced. The reference travels
in the message's existing structured metadata field rather than in message content, so program source is never
copied into the message row. The server resolves the widget, verifies account authorization, and canonicalizes the
revision on write, because a client-forged reference is untrusted input.

The widget is rendered by the **host** from the authoritative record, through the **existing** renderer and the
**existing** sandbox frame, in the user-side transcript surface alongside the established document-context tile.

Invocation resolves account authorization, resolves an immutable revision, renders the existing approved artifact,
preserves conversation lineage, avoids copying program source into messages, avoids fabricating an assistant
response, and survives reload and restart.

**Initial invocation is human-initiated through Library.** Model-initiated discovery and invocation are deferred:
a system-prompt block would spend token budget and place user-authored widget names into the prompt, and the
tool-rail path is provider-constrained, which is the same reason the generative UI contract rode the system prompt
rather than the tool rail.

### 6. Conversational editing is one bounded, authorized exception

The lifecycle is: invoke a saved revision → request a modification → resolve the authorized source → supply bounded
source as edit context → generate a candidate revision → preview inside the existing sandbox → **user explicitly
approves** → commit an immutable next revision.

Normal conversation history continues to strip generated source before provider inference. The edit path is a
**separate, explicitly authorized, per-turn context assembly**, not a relaxation of the history path and not a new
marker in the artifact channel. The model emits the modified program as an ordinary `cfy-ui` sandbox artifact, so
the artifact wire format is unchanged and the candidate renders through the existing renderer and sandbox.

A failed edit leaves the existing saved revision intact. A generated candidate never automatically replaces a saved
revision. When the model cannot accommodate the selected source within available context capacity, the edit fails
explicitly with a stated reason rather than silently truncating the source and proceeding with a partial program.

Widget source is untrusted and may contain instructions. The mitigation is not source sanitization but the chain of
authority: the source is delimited and labeled as data, and no model output can create, save, revise, install, or
publish a Saved Widget.

### 7. Runtime containment is unchanged, and saving grants no capability

A Saved Widget remains untrusted executable content. The opaque-origin sandbox, the restrictive CSP including
`default-src 'none'` and `connect-src 'none'`, the absence of `eval` and `new Function`, the absence of Guardian
credentials, filesystem access, and network access, and the existing validated bridge semantics all apply
unchanged — because a saved widget renders through the same path.

**The bridge action set is unchanged.** The sandbox gains no `save`, `revise`, `install`, `publish`, or `authorize`
action. The save control is **host chrome outside the iframe**, and the save path is an authenticated host action,
so a model-generated button cannot save, revise, install, publish, or authorize itself. Saving a widget grants it
nothing.

A saved widget's runtime **must not** start automatically every time a historical conversation is rendered; an
explicit launch affordance starts it, and a running instance is destroyed on dismissal. Because the opaque origin
denies the frame access to host storage, cookies, `document`, and host APIs, "a reopened widget starts with fresh
runtime state" is a containment-derived property and not only a policy.

Web Audio synthesizers and canvas games are compatible with the existing containment without any CSP change, since
browser autoplay rules require a user gesture — which explicit launch already supplies — and canvas drawing needs
no additional permission. Any future need that would genuinely widen the boundary requires a separate ADR.

### 8. Library semantics are preserved, including unavailable versus empty

This decision does **not** make the Widgets filter available. Until implementation lands and is proven, Widgets
remains unavailable with a stated reason, no synthetic listing is permitted, no chat-message scraping is permitted,
and `All` must not claim complete coverage of an unavailable source.

When a future saved-widget source exists, it participates as source family `saved_widget`, resource type `widget`,
with source-family-qualified presentation identity, provenance read only from authoritative metadata, account scope
from the existing authenticated transport, and scope exactly one of project, thread, or unscoped — where scope
selects *placement*, not ownership. It reports one of the five existing completeness outcomes, and only `complete`
and `empty` assert coverage.

**Library remains a read-only projection.** Creating, revising, renaming, archiving, and deleting Saved Widgets
belong to an explicitly governed authoring and lifecycle path, not to the Library projection.

### 9. Portability is deferred, not assumed

Export and restore of Saved Widgets are **not supported** until separately implemented and proven and until the
account export and restore contract is amended to cover them. The existing account export and restore guarantees —
preserve canonical state, preserve source provenance, faithfully rehydrate, never silently drop lineage or
ownership — continue to govern the export artifact as it exists today.

## Why a separate authoritative resource is justified

The alternative — treating a saved widget as a chat message, a document, or a Library projection artifact — was
rejected on specific grounds rather than preference:

- **A chat message is not a resource.** Its identity is the message's, its lifetime is the thread's, and it cannot
  be named, listed, resolved independently, or referenced from another thread.
- **A document is a different category.** Documents are uploaded, imported, or generated *content* with authored
  content semantics. A saved widget is an executable program. Filing one as the other would either pollute the
  document category or quietly redefine what a document is.
- **A Library projection is not a storage authority.** The Library contract is explicit that a Library entry is a
  view over an authoritative resource, never a second copy and never a second ownership system. Populating the
  Widgets filter from chat messages is explicitly prohibited.
- **An in-content marker is not a durable reference.** The inference path strips `cfy-ui` markers, and the
  generative UI contract already names the enlarged-message-row limitation of the in-content channel. Storing
  program source per invocation would duplicate it and would make the artifact's identity depend on message
  content rather than on a resource.

A separate authoritative resource is therefore the minimum structure that satisfies durable identity, single
ownership, immutable revision, cross-thread invocation, and honest listing.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| **Synthesize the Widgets filter from chat-message artifacts** | Explicitly prohibited by the Library contract. It also produces a list whose identity is the message's, not a resource's, and would make "saved" indistinguishable from "once said in a thread". |
| **Reuse the in-content `cfy-ui` marker for invocation** | The renderer is mounted in the assistant branch, the inference path strips the marker, and program source would be duplicated into every invoking message. It is a display channel, not a resource reference. |
| **Fabricate an assistant message carrying the widget** | Forbidden by the transcript-integrity doctrine this decision preserves, and it would corrupt the conversation lineage. |
| **Keep the widget as a document** | Wrong resource category, and it would either pollute the document taxonomy or redefine what a document is. |
| **Model-declared eligibility** | A self-certifying trust path. The artifact's own content would satisfy the classifier that is supposed to judge it. |
| **Model-initiated discovery via a system-prompt widget list** | Spends token budget, places user-authored names in the prompt, and scales poorly with widget count. |
| **Model-initiated discovery via the tool rail** | Provider-constrained. `guardian/tools/chat_exposure.py` advertises tools only to specific providers, which is why the generative UI contract rode the system prompt instead. |
| **A general widget runtime with persistent state, network, or install semantics** | Not authorized. It would widen the sandbox boundary and require a separate ADR. |
| **A general version-control subsystem for widget revisions** | Disproportionate. A linear monotonic revision sequence with one pointer, immutable snapshots, and explicit conflict detection is sufficient. |
| **Live-linking invocations to the current revision** | Would break pinning. An existing invocation must keep showing the revision it resolved, or history silently changes under the user. |
| **A new marker type for widget references** | Unnecessary. The existing structured metadata field on the message row already carries lineage for other record kinds, and using it avoids a wire-format change. |

## Governing ADRs

This decision extends and is bounded by:

- [ADR-003: Message Identity vs Request Identity](003-message-identity-vs-request-identity.md) — preserved. A widget
  is not a message, a request, or an attempt. Widget identity and revision identity are resource identities and bind
  to no attempt.
- [ADR-069: Codexify Beta Runtime Support Boundary](069-codexify-beta-runtime-support-boundary.md) — preserved. This
  decision changes no release class and widens no support promise.
- [ADR-077: Sandbox Execution Authority and Provider Boundary](077-sandbox-execution-authority-and-provider-boundary.md) —
  preserved. The deny-by-default network posture and the untrusted-content boundary are unchanged.
- [ADR-081: Project Ownership Authority](081-project-ownership-authority.md) — preserved and reinforced. A Saved
  Widget has exactly one ownership authority. Project association is placement and must not become a second
  co-authority, which is the defect class ADR-081 exists to prevent.
- [ADR-082: Persona Profile Manifest and Binding Authority](082-persona-profile-manifest-and-binding-authority.md) —
  preserved and used as a design reference for immutable revision snapshots only. Saved Widgets are not coupled to
  Persona Profiles.
- [ADR-091: Durable Chat Completion Attempt Authority](091-durable-chat-completion-attempt-authority.md) — preserved
  and relied upon for server-owned completion-attempt linkage as the basis of generated provenance.

**No accepted ADR is superseded by this decision.** The generative UI contract and the Library contract are
extended, not replaced: the former continues to govern the artifact channel unchanged, and the latter continues to
govern the Library projection and its unavailable-versus-empty semantics unchanged.

## Invariants

### Preserved

1. Generated UI is untrusted and is never granted Guardian credentials, host filesystem access, Tauri native
   capabilities, privileged APIs, or network access.
2. The sandbox frame runs in an opaque origin with `allow-scripts` only.
3. Every bridge message is source-bound, session-bound, origin-checked, and schema-validated; unknown or malformed
   messages are ignored.
4. The bridge exposes exactly one host capability in the generative UI slice, and it only prefills the composer; it
   cannot cause a turn.
5. Generated UI source is stripped before provider inference on the normal history path.
6. Only registered native components may execute as first-party code; an unknown component ID degrades to text.
7. A render-time failure inside an artifact degrades to an inline notice and never blanks the transcript.
8. ADR-003 message-versus-request identity, with no artifact or widget bound to request or attempt identity.
9. Library is not a new persistence authority, and a Library entry is a view over an authoritative resource.
10. An unavailable filter is never represented as a complete empty result, and an incomplete projection is never
    presented as complete.
11. Provenance is proven, never inferred from storage location, filename, URL, MIME type, or filter membership.
12. Presentation identity is source-family qualified; canonical source IDs are preserved unchanged.
13. Account, Project, thread, and resource identity remain distinct, and placement is not ownership.
14. No release, provider, or inference configuration claim changes.

### Introduced

1. A Presentation Artifact, a Widget Candidate, and a Saved Widget are distinct resource categories, and the
   execution-mechanism axis is orthogonal to the resource-category axis.
2. Saved-widget eligibility is a server-verified set of necessary preconditions, and **explicit user promotion is
   the only sufficient decision**. No model output can create, save, revise, install, publish, or authorize a
   Saved Widget.
3. A Saved Widget has exactly one canonical ID and exactly one account owner; Project and thread associations are
   placements and never alternative ownership authorities.
4. Generated provenance is established by server-owned completion-attempt linkage, and a client-supplied role or
   metadata field is never provenance.
5. A Saved Widget's provenance is an immutable snapshot captured at save time, and the deletion of the source thread
   does not delete, alter, or un-provenance it.
6. Revisions are immutable, monotonically increasing, server-assigned, and linear, with a forward-only
   current-revision pointer, explicit edit-base conflict detection, and create-on-restore rather than rewind.
7. An existing invocation is pinned to the revision it resolved.
8. Invocation is a canonical transcript record carrying a resolved resource reference, rendered by the host through
   the existing renderer and containment, and never by replaying an artifact into message content or fabricating an
   assistant response.
9. The source-supplying edit path is a separate, explicitly authorized, per-turn context assembly, and normal
   history continues to strip generated source.
10. Saving a widget grants no new capability, the bridge action set is unchanged, and the save control is host
    chrome outside the iframe.
11. A saved widget's runtime starts only on explicit launch and is destroyed on dismissal.
12. Library remains a read-only projection, and widget mutations belong to a separate governed authoring path.
13. Widget export and restore are not supported until separately implemented and proven.

## Approved product intent versus unaccepted implementation architecture

**Approved product intent** — settled by the human before this decision and recorded here unchanged: widget runtime
state need not persist; a reopened widget starts with fresh runtime state; widgets are reusable across
conversations; an invoked widget can be reworked conversationally; revisions are durable and independently
addressable; saving and revising require explicit user action; static charts and one-off visualizations are not
reusable widgets merely because they use generative UI; and no new ambient sandbox permissions are authorized. The
Library's four-filter taxonomy, including **Widgets**, is likewise already approved product direction.

**Unaccepted implementation architecture** — proposed by this ADR and requiring a separate explicit human
architecture decision before any of it is built:

- the specific table and column shape for widget and revision records;
- the specific route family, paths, and request/response shapes;
- the specific revision-snapshot column type and its serialization;
- the specific metadata field and descriptor format used to carry a widget reference on a message;
- the specific edit-context assembly mechanism and its size budget;
- the specific ordering and conflict-response details of the commit operation;
- the staged implementation sequence and its slice boundaries.

None of the above is implemented. This ADR records architecture only.

## Consequences

### Positive

- A user can keep a generated program, reuse it across conversations, and revise it in ordinary language, without
  the program ever becoming trusted content.
- The Library's Widgets filter gains an honest path to becoming real, with identity, provenance, and completeness
  already settled.
- The revision model is minimal enough to implement and to reason about, and does not create a general
  version-control subsystem.
- The existing generative UI channel, renderer, sandbox, and bridge are reused rather than duplicated, so the blast
  radius of the feature is concentrated in the new resource, not in the existing channel.

### Costs and risks

- A saved widget is functionally a user-installed, model-authored program with a long life. Its containment is
  unchanged, but its lifetime is not. Explicit launch and the unchanged bridge are what keep that acceptable.
- Widget source supplied as edit context is untrusted instruction-shaped content. The control is the human approval
  gate, not sanitization.
- A durable cross-thread record requires a server-side artifact envelope validator, which does not exist today —
  the backend currently only strips `cfy-ui` markers, and every validation rule lives in the frontend codec. The two
  sides must be kept in agreement, which the shared marker corpus already exists to serve.
- Revisions multiply stored copies of program source, which is a storage cost the in-content channel did not incur.

## Deferred and explicitly not claimed

- No runtime implementation. No table, route, migration, or frontend component exists for any of this.
- No release-support change. Per ADR-069 and `00-current-state.md`, the current release gate is unchanged and this
  decision widens no release class.
- No Library Widgets availability. The filter remains unavailable until implementation and proof.
- No end-to-end saved-widget runtime qualification, and no live evidence of any kind.
- No widget export or restore.
- No Space installation, no publishing, no network access for a widget, no persistent widget runtime state, and no
  parameterized templates.
- No model-initiated widget discovery or invocation.
- No change to the sandbox, the CSP, the bridge, the artifact envelope, the artifact wire format, or any prompt.
- No acceptance. This ADR is **Proposed**. It must not be read as an accepted decision, and it must not be marked
  Accepted without a subsequent explicit human decision.
