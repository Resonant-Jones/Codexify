# Browser Authority and Context-Boundary Contract

## Status

- Classification: normative architecture contract; architecture-impacting.
- Implementation status: not implemented.
- Release status: not current runtime proof and not a supported-beta claim.
- Current-client boundary: ADR-051 continues to govern the private Chrome
  side-panel client's authentication, credential storage, and transport modes.
- Future boundary: this contract constrains any later Browser Host, page
  observation, context capture, attachment, or persistence implementation.
- Episodic/recall boundary: ADR-070 and the Browser Episodic Context and Recall
  Contract define the later chat-backed Browser Episode and separately opt-in
  Browser Recall semantics; they do not prove implementation.

## Purpose

This contract defines how browser-derived content may cross from a page or
renderer into Codexify reasoning without acquiring identity, credential,
command, persistence, or browser-action authority. It separates Guardian
connectivity from page observation, makes capture user-initiated and bounded,
and preserves provenance across ephemeral attachment and explicitly authorized
durable persistence.

Ordinary page capture remains ephemeral by default. A clearly labeled,
chat-backed Ambient Browser Turn is a narrower future exception governed by
ADR-070: the user action may authorize a normal durable chat turn and bounded
Browser Episode evidence, but never the rest of the page or raw DOM. Browser
Recall is a distinct authority domain and is not implied by page observation.

The contract is host-neutral. Repository presence, documentation, or the
current side-panel client does not prove that capture, a Browser Host, browser
actions, or durable browser context exists.

Normative terms such as **MUST**, **MUST NOT**, **SHOULD**, and **MAY** describe
requirements for future implementation. They do not assert present behavior.

## Scope

This contract covers:

- the current private Chrome side-panel client where its existing trust boundary
  intersects future browser context intake;
- a future Browser Host without selecting its technology or repository;
- page metadata, user-selected text, and bounded extraction of visible page
  content;
- screenshots or documents only when separately authorized for the individual
  capture;
- transfer of a bounded context envelope to Guardian;
- ephemeral request attachment;
- explicit durable persistence initiated or confirmed by the user; and
- failure, provenance, retention, and observability requirements for those
  operations.

This contract does not authorize or select:

- a host technology or repository split;
- tab inventory, cookies, passwords, downloads, autofill, browser history,
  profiles, or sessions;
- browser automation, page actions, form submission, navigation, or mutation;
- background, continuous, history-wide, or unsolicited capture;
- identity or memory mutation;
- unrestricted filesystem access; or
- command-bus invocation.

## Canonical Actors and Trust Zones

| Actor | Trust zone | Responsibility | Explicit boundary |
|---|---|---|---|
| User | Human authority | Initiates capture, reviews scope, authorizes attachment, and separately authorizes durable persistence. | Page content cannot impersonate the user or supply consent. |
| Trusted Browser Client | Trusted extension or host UI context | Presents capture controls, permission state, preview, provenance, and Guardian connectivity. | It receives no ambient authority from the page and may use only separately granted capabilities. |
| Browser Permission Broker | Browser/host control plane | Grants, denies, revokes, and reports the smallest observation scope supported by the host. | A grant is page-observation authority only; it is not Guardian connectivity, attachment, persistence, or action authority. |
| Remote Page Renderer | Untrusted page/renderer process | Renders remote content and exposes only host-mediated observable state. | It never receives Guardian credentials, command authority, persistence authority, or unrestricted host access. |
| Browser Context Adapter | Least-privileged extraction boundary | Converts an authorized observation into a bounded, typed Browser Context Envelope. | It cannot call Guardian directly, retain credentials, widen scope, or act on the page. |
| Future Browser Host | Trusted orchestration boundary, if implemented | Isolates page processes, brokers permissions, coordinates capture, and transports approved envelopes. | Its existence, technology, and repository are undecided; it has no implicit action authority. |
| Codexify Frontend / Guardian client | Trusted Codexify client boundary | Displays preview and failure state, submits explicitly approved attachment or persistence requests, and preserves chat independence. | It must not treat page permission as Guardian authorization. |
| Guardian | Policy and application authority | Authenticates the client, validates context and correlation, attaches accepted context, and owns any explicit durable write. | It does not infer capture consent, browser-action authority, identity mutation, or durable retention from content. |
| Model Provider | External reasoning boundary | Reasons over the bounded content Guardian deliberately includes. | It receives no credentials or browser authority and cannot elevate page instructions into permissions. |
| Command Bus | Separate capability and execution boundary | Executes only separately contracted, authorized commands. | This contract provides no command-bus invocation or browser-action token. |
| Durable Storage | Guardian-mediated persistence boundary | Stores only explicitly authorized records with provenance and retention metadata. | Storage availability is not permission to persist. |
| Identity / Memory systems | Separate sensitive-data boundary | Apply their own write, provenance, consent, correction, and deletion contracts. | Browser context does not enter identity or memory through attachment alone. |

The current side panel and its service worker are trusted browser-client
contexts within ADR-051's narrow responsibilities. A future Browser Host may
contain both trusted chrome/UI contexts and untrusted remote renderer contexts.
Remote page renderers are never trusted Codexify authority surfaces.

The device, browser process, renderer, network, Codexify client, Guardian,
provider, and storage boundaries remain distinct even when several components
run on one machine.

## Authority Matrix

Legend: **yes** means the actor may exercise the authority only within this
contract's explicit conditions; **broker** means it mediates an authority but
does not originate it; **separate contract** means this contract grants none.

| Actor | Observe page | Capture content | Attach to request | Persist durably | Act on page | Mutate identity / memory | Access credentials | Access filesystem | Invoke Command Bus |
|---|---|---|---|---|---|---|---|---|---|
| User | yes, through UI | authorizes | authorizes | separately authorizes | separate contract | separate contract | owns entry decisions | separate host policy | separate contract |
| Trusted Browser Client | broker | broker | submits approved request | submits separate approved request | no | no | only ADR-051 trusted context | no unrestricted access | no |
| Browser Permission Broker | broker | no | no | no | no | no | no | no | no |
| Remote Page Renderer | exposes rendered state | no | no | no | no | no | no | no | no |
| Browser Context Adapter | within grant | yes, bounded | no | no | no | no | no | no | no |
| Future Browser Host | broker | broker | transports approved envelope | transports separate request | no | no | trusted transport only if separately designed | no unrestricted access | no |
| Codexify Frontend / Guardian client | preview only | no | yes, after approval | requests separately | no | no | trusted client rules only | no unrestricted access | no |
| Guardian | no | no | validates and attaches | yes, after separate authorization | no | no under this contract | backend/client auth boundary | application-scoped only | separate contract |
| Model Provider | no | no | receives selected context | no | no | no | no | no | no |
| Command Bus | no | no | no | no | separate future command | separate contract | capability-scoped only | capability-scoped only | executes authorized commands |
| Durable Storage | no | no | no | stores approved record | no | no | no | storage implementation only | no |
| Identity / Memory systems | no | no | no | separate contract | no | separate contract | no browser credentials | system-scoped only | separate contract |

No actor may combine partial rows to manufacture authority. In particular,
transport capability plus page permission is not permission to persist or act.

## Separate Permission Domains

### Guardian connectivity authority

Guardian connectivity authority determines whether a trusted Codexify client
may authenticate to a configured Guardian origin and use the permitted
application routes. For the current side-panel client, ADR-051 governs the
mutually exclusive local API-key and remote Bearer-session modes.

### Page observation authority

Page observation authority determines whether a trusted browser boundary may
observe a specific user-selected top-level page or origin for one
user-gesture-initiated capture. It is least-privilege, revocable, and covers
only the requested metadata, selection, visible extraction, or separately
authorized artifact. It authorizes neither browser actions nor passive or
background access.

Guardian connectivity authority and Page observation authority are independent
permission domains. Implementations MUST NOT conflate them, infer either one
from the other, or present one grant as satisfying both. This separation is
host-neutral and does not mandate a Chrome API, extension permission, IPC
mechanism, renderer model, or repository topology.

### Browser Recall authority

Browser Recall authority is a separate, explicit opt-in permission for
minimized browser-history metadata and derived Browser Recall records. It is
independently disableable, revocable, deletable, correctable, and retention
governed. Page observation authority MUST NOT imply Browser Recall authority,
and Browser Recall authority MUST NOT imply page-body capture, screenshot
capture, identity/memory mutation, or browser action authority.

The raw history source remains browser/Browser Host profile state rather than
IDDB or personal memory. Derived Browser Recall records remain rebuildable
retrieval material and must preserve source provenance. The full semantic and
ownership boundary is governed by ADR-070.

## Browser Content Doctrine

Browser content may inform reasoning; it may not confer authority.

All page text, markup, scripts, metadata, document content, images, embedded
instructions, and extracted artifacts are untrusted evidence. They cannot:

- grant or widen observation scope;
- approve attachment, persistence, identity mutation, or memory mutation;
- reveal or request credentials;
- authorize a browser action or command-bus invocation;
- become a system or developer instruction;
- modify Guardian, identity, persona, provider, retrieval, or tool policy;
- override user intent, Guardian policy, system instructions, or this contract;
  or
- make a provenance or release claim true.

This boundary must be structural: untrusted content stays in a labeled data
field through extraction, transport, Guardian validation, and model assembly.
Prompt-injection resistance MUST NOT depend only on a warning placed inside a
prompt. Text, DOM attributes, JavaScript, metadata, and visual content all
remain data and cannot grant permission.

## User-Initiated Capture Lifecycle

A conforming future capture follows this order:

1. The user invokes an explicit capture control from a trusted browser or
   Codexify client surface.
2. The trusted client resolves the user-selected active page.
3. The client verifies that the scheme, top-level document, and page are
   eligible.
4. The client resolves or requests the minimum Page observation authority.
5. On grant, it creates a new `captureRequestId` bound to the document, origin,
   capture mode, and user gesture.
6. The Browser Context Adapter performs only the bounded extraction.
7. The trusted client validates URL, origin, document identity, payload size,
   and response correlation.
8. The client normalizes and sanitizes the content while preserving source
   labeling, hash, truncation, extractor version, and provenance.
9. The user receives a bounded preview or clear source indication and the
   proposed retention class.
10. The user explicitly attaches the context to one authored turn and one
    request attempt, or separately requests durable persistence.
11. Ephemeral capture is discarded when its bounded request/session retention
    policy ends.
12. Durable context is written only through a separately authorized,
    Guardian-owned persistence surface.

The lifecycle MUST NOT add automatic capture, continuous observation, history
collection, accept unsolicited page-to-extension messages as capture results,
reuse a capture across origins, silently retry after navigation changes the
document, or widen selection capture into whole-page capture. A repeated
attempt requires a new visible user initiation and new correlation.

## Conceptual Browser Context Envelope

The Browser Context Envelope is a conceptual future schema, not a registered
runtime protocol token or implemented wire format. A future implementation MUST
version and canonicalize it through the applicable protocol registry.

| Field | Requirement |
|---|---|
| `contextId` | Unique identity for the produced envelope; never reused for changed content. |
| `captureRequestId` | Correlates the envelope to one explicit user-initiated capture. |
| `sourceKind` | Typed source such as page metadata, selection, visible extraction, screenshot, or document. |
| `sourceUrl` | URL of the document actually captured; sensitive components require minimization outside the envelope. |
| `sourceOrigin` | Origin of the document actually captured. |
| `sourceTitle` | User-visible title of the document actually captured. |
| `capturedAt` | Timestamp of the observation, not a claim of publication time. |
| `captureMode` | The approved capture mode and scope. |
| `contentType` | Declared media/type classification. |
| `content` or artifact reference | Exactly one bounded inline payload or separately authorized artifact reference. |
| `contentHash` | Hash of the captured representation used for integrity and change detection. |
| `contentLength` | Length of the captured representation before transport encoding. |
| `truncated` | Explicit boolean plus any available truncation boundary. |
| `extractorVersion` | Versioned adapter/extractor identity. |
| `permissionScope` | The observation scope actually granted, never the manifest maximum. |
| `retentionClass` | At minimum ephemeral attachment or separately authorized durable candidate. |
| `userInitiated` | Must be true; false or absent is rejected. |
| `threadId` / `projectId` | Explicit intended binding or explicit absence; never inferred from page content. |
| `provenance` | Actor, trusted client, document/origin binding, transformation chain, and artifact lineage. |
| failure / absence | Typed reason when content or a field is absent, rejected, unavailable, or failed. |

The envelope MUST NOT contain secrets, browser storage, cookies, password
fields, form values, hidden DOM state, extension storage, authentication
headers, or ambient browser state. A changed document or origin invalidates the
capture and requires a new user initiation. Raw browser content MUST NOT be
copied into ordinary logs.

Browser-local tab identifiers are ephemeral correlation aids and MUST NOT
become durable account identity or cross-session ownership. Truncation and
omitted material MUST be explicit.

## Default Extraction Boundary

### Allowed by default after an explicit grant

- normalized source URL, origin, document title, and capture timestamp;
- user-selected text;
- bounded visible text from the active top-level document;
- visible semantic structure needed to preserve headings, lists, links, tables,
  and code blocks;
- canonical and public metadata already exposed by the rendered document;
- content length, hash, truncation, and extractor provenance; and
- a screenshot or document artifact only through a separately visible,
  capture-specific authorization.

### Excluded by default

- hidden, collapsed, offscreen-only, script, style, comment, or application
  state not visibly presented to the user;
- cross-origin iframe content;
- cookies, local/session storage, IndexedDB, cache, service-worker state, auth
  headers, tokens, and browser profile data;
- password, payment, autofill, or other sensitive form fields;
- typed but unsubmitted form content;
- browser history, bookmarks, downloads, open-tab inventory, or clipboard;
- accessibility or devtools data beyond the approved visible extraction;
- background pages and unrelated extension pages; and
- whole-document capture when selection or bounded visible extraction satisfies
  the request.

An implementation MUST NOT infer a broader capture mode merely because the host
can technically access it.

Screenshot capture is not text extraction. PDF or binary capture is not DOM
capture. Each source mode requires its own user action, provenance, validation,
and retention disclosure. This contract does not automatically authorize OCR,
downloads, binary ingestion, raw DOM serialization, or page JavaScript
execution beyond the bounded extractor contract.

## Credential and Secret Boundary

For the current private side-panel client, the local API key and remote
`Authorization: Bearer` session may exist only in the trusted extension context
defined by ADR-051. Future content scripts, page renderers, remote page
processes, injected scripts, page bridges, and extraction adapters MUST NOT
receive either credential class.

- Extractors MUST NOT call Guardian.
- The trusted client or host MUST use an allowlisted, typed, correlated
  transport schema.
- Guardian MUST reject unsolicited envelopes, unknown capture requests,
  mismatched user/thread/project correlation, stale document bindings, origin
  mismatch, and unapproved retention.
- Credential storage MUST remain in an explicitly trusted client boundary and
  follow ADR-051 or a later accepted credential contract.
- Credentials MUST NOT appear in the Browser Context Envelope, logs, durable
  browser-context records, page messages, renderer IPC payloads, model context,
  telemetry, or error text.
- Page content MUST NOT select an auth mode, Guardian origin, account, thread,
  project, storage target, or capability.

## Attachment, Persistence, Identity, and Memory

These are separate operations:

- **Capture** produces a bounded envelope from one authorized observation.
- **Attachment** makes an accepted envelope available to one identified
  authored turn and one request attempt. The default retention class is
  ephemeral; it does not automatically become a thread document, enter semantic
  retrieval, enter browser history, enter memory, or survive the applicable
  request/session policy.
- **Durable persistence** is a distinct Guardian-owned write requiring explicit
  user authorization, a named destination such as a thread, project, document,
  media asset, or artifact, provenance and relationship lineage, retention,
  ownership checks, export/restore, deletion, and correction behavior. Saved
  records preserve source URL, origin, title, capture time, source kind,
  content hash, extractor version, truncation, and omitted-material status.
- **Chat-backed Browser Episode persistence** is the narrower future rule in
  ADR-070. A clearly labeled Ambient Browser Turn may authorize a normal
  durable user turn and the bounded Semantic Page Payload needed to preserve
  what the interaction addressed. It does not authorize whole-page/raw-DOM
  persistence, Browser Recall, or identity/memory mutation. The current v1
  Browser Host attachment remains ephemeral and not_persisted.
- **Identity or memory mutation** is outside this contract and requires the
  governing identity/memory write contract, separate consent, and separate
  proof. Capture or persistence does not mutate IDDB, Identity Mirror, persona
  ownership, personal facts, or durable traits; browsing behavior is not a
  durable personality trait.

Attachment does not imply durable persistence. Persistence does not imply
identity truth, memory truth, retrieval truth, project truth, endorsement, or
permission for reuse. Thread or project identifiers bind intended use; they do
not transfer ownership from the user or establish factual accuracy.

## Failure Vocabulary and State Separation

A future implementation MUST canonicalize its runtime vocabulary before code
lands. The following conceptual failure meanings are the minimum required
coverage:

- `permission_denied`
- `permission_revoked`
- `unsupported_scheme`
- `protected_page`
- `tab_unavailable`
- `document_changed`
- `origin_mismatch`
- `capture_failed`
- `payload_too_large`
- `context_rejected`
- `user_cancelled`
- `attachment_failed`
- `persistence_failed`

Permission, capture, attachment, and persistence are independent state
dimensions. A future schema must represent at least:

- permission: not requested, requested, granted, denied, or revoked;
- capture: idle, active, succeeded, failed, or cancelled;
- attachment: unattached, active, attached, rejected, or failed; and
- persistence: ephemeral, requested, persisted, rejected, or failed.

These phrases are conceptual semantics, not new inline runtime tokens. Before
they appear across code, tests, APIs, logs, or UI, a future implementation must
create or extend the bounded canonical token registries.

Permission denial or capture failure MUST NOT break ordinary chat, alter
Guardian connectivity, or imply authentication loss. Protected and ambiguous
surfaces fail closed. Failure MUST NOT silently retry with a wider permission,
different capture mode, whole-document fallback, screenshot fallback, or
another origin. Retry remains bound to the same user-selected page and
authority scope unless a new user initiation creates a new capture. Partial or
truncated content MUST NOT be presented as complete. Raw page content MUST NOT
be placed in logs or error messages.

## Protected-Page Policy

Protected, privileged, ambiguous, or unsupported pages fail closed without
capture. At minimum this includes:

- browser-internal and settings schemes such as `chrome:`, `edge:`, `about:`,
  and equivalent host-private pages;
- extension stores, browser account pages, devtools, and unrelated extension
  pages;
- the trusted client's own authentication and credential-management surfaces;
- pages whose active origin or document no longer matches the grant;
- unsupported schemes, unavailable tabs/documents, and inaccessible protected
  documents;
- cross-origin frames not independently and explicitly authorized; and
- `file:` access unless a later explicit policy permits it; and
- PDFs, binary, canvas-only, sandboxed, or embedded documents unless a later
  accepted,
  source-specific contract and permission explicitly covers them.

The UI may identify the category and safe recovery step. It MUST NOT expose
captured content, probe for a broader grant, or imply that disabling browser
protections is the normal remedy. Eligibility comes from explicit
browser/runtime capability and policy; the system MUST NOT guess page
sensitivity from prose, brand identity, or speculative content classification.

## Browser Host Neutrality

This contract is valid for a Chrome extension, Tauri host, Electron host,
Chromium-based host, another accepted browser host, or a split trusted
client/renderer design. It deliberately does not choose among them.

Any candidate must prove:

- renderer and trusted-host isolation;
- least-privilege observation brokerage;
- secret-free extraction and transport;
- document/origin binding;
- crash, partition, retry, cancellation, and replay behavior;
- upgrade and protocol compatibility; and
- packaging, signing, recovery, and security ownership.

Those proofs inform the later Browser Host topology and repository-boundary ADR;
this document cannot substitute for that decision.

## Browser action boundary

This contract grants no authority to navigate, click, type, submit, upload,
download, dismiss, accept, purchase, authenticate, install, execute script,
modify page state, change browser settings, manage tabs, or invoke an external
service.

Any future browser-action contract must be separate and normative. It must
define typed commands, explicit capability grants, origin and document binding,
user confirmation rules, identity, idempotency, retry and replay handling,
cancellation, deadlines, receipts, attribution, audit fields, protected-page
rules, provider/model limits, and command-bus mediation. Prompt text and page
content can never create action authority.

## Observability and Data Minimization

Safe observability may record:

- capture request ID and context ID;
- source origin, subject to minimization and retention policy;
- capture mode and source kind;
- coarse permission, capture, attachment, and persistence outcomes;
- trusted client, adapter, schema, and extractor versions;
- payload byte counts, truncation, latency, and typed failure meaning;
- attachment destination type;
- whether user initiation and explicit persistence authorization were present.

Future operator truth must distinguish:

- Browser Client reachable;
- Guardian backend reachable;
- Guardian connectivity permission granted;
- Page observation permission granted;
- capture started and capture completed;
- context validated;
- context attached to a request attempt;
- context persisted as a durable artifact; and
- capture or attachment degraded versus failed.

Observability MUST NOT record:

- raw page content, selections, screenshots, document bodies, or model context;
- full URLs with sensitive paths, fragments, or query strings;
- cookies, credentials, tokens, auth headers, form values, clipboard, storage,
  or browsing history;
- hidden prompt material or page instructions;
- page-derived identity inferences or sensitive-trait profiles; or
- cross-site behavior assembled into user profiling or analytics.

Operational metrics must be content-free by default, access-controlled, and
retained only as long as their stated operational purpose requires.

## Required Future Proof Surfaces

Before any implementation or product claim, the applicable task must prove:

1. exact source, build, packaging, and generated-output ownership;
2. renderer/content-script isolation from credentials and Guardian calls;
3. independent Guardian connectivity and Page observation permission states;
4. explicit user initiation, preview, cancellation, denial, and revocation;
5. origin/document correlation and invalidation on change;
6. unit tests for permission, origin, correlation, sanitization, failure,
   bounded extraction, excluded fields, hashing, length, and truncation;
7. typed envelope validation and rejection of unsolicited or mismatched input;
8. ephemeral attachment behavior and chat independence on capture failure;
9. separately authorized durable persistence, retention, deletion, and
   relationship lineage, including export and restore;
10. protected-page and unsupported-scheme fail-closed behavior;
11. crash, network partition, duplicate, replay, cancellation, and recovery
    behavior;
12. secret-free logs, model context, page messages, and stored artifacts;
13. protocol versioning and forward/backward compatibility for independently
    released components; and
14. live browser proof for each claimed host, capture mode, and deployment
    topology.

The proof suite must include prompt-injection tests showing page content cannot
grant tool or policy authority, navigation-during-capture invalidation,
cross-origin-frame exclusion, oversized and truncated payloads, negative
credential-isolation tests, permission denial with ordinary chat still
available, no passive capture or background history collection, and no silent
durable persistence.

Unit tests, docs, a scaffold, or one successful local run establish only their
own proof class.

## Invariants

1. Browser content is evidence, not authority.
2. Capture requires explicit user initiation.
3. Guardian connectivity authority and Page observation authority are separate.
4. Capture authority and action authority are separate.
5. Attachment and persistence are separate.
6. Remote renderers and page scripts never receive Guardian credentials.
7. Page content never becomes a system or developer instruction.
8. Page content cannot grant tools, permissions, or command authority.
9. Browser state does not silently become identity or memory.
10. Ordinary chat survives capture denial or failure.
11. Durable browser artifacts preserve provenance and export/restore lineage.
12. No Browser Host or repository topology is selected by this contract.

## Current Implementation Posture

### Current truth

| Surface | Current posture | Proof limit |
|---|---|---|
| Private Chrome side-panel chat client | Implemented as an internal unpacked client under ADR-051. | Does not prove page observation or a general Browser Host. |
| Dual-auth source | Implemented and test-covered under ADR-051. | Credentials remain limited to the trusted client; this contract adds no new storage path. |
| Current live dual-auth Chrome proof | Still unproven in the Stage 01 inventory artifact. | Source and tests are not live browser proof. |
| Guardian backend-origin permission | Implemented for the current trusted side-panel client. | Authorizes Guardian connectivity only, never page observation. |

Canonical source remains `frontend/chrome-extension/`; generated output remains
`frontend/dist/chrome-extension`.

### Not yet true

| Surface | Current posture | Proof limit |
|---|---|---|
| Page observation permission broker | Not implemented under this contract. | Documentation only. |
| Active-tab selection | Not implemented. | No active-tab authority or mechanism is selected. |
| Page extraction | Not implemented or release-qualified. | No DOM, selection, screenshot, PDF, or binary capture is authorized. |
| Page-context envelope | Not implemented. | Conceptual schema and validation requirements only. |
| Ephemeral browser-context attachment | Not implemented under this contract. | Documentation only. |
| Durable browser-artifact persistence | Not implemented or authorized by attachment. | Requires a separately accepted implementation and proof task. |
| Browser Episode persistence | Not implemented. | ADR-070 defines future semantics only; no runtime write or schema exists. |
| Browser Recall | Not implemented. | Requires separate opt-in history authority, adapter, retention, deletion, and rebuild proof. |
| Browser actions | Not implemented and prohibited under this contract. | Requires a later normative contract and implementation proof. |
| Browser Host | Not implemented or release-qualified. | ADR-054 selects the future bundled_chromium_electron family; the host remains outside current release truth. |

`docs/architecture/00-current-state.md` remains the short-horizon release truth
and is not changed by this contract.

## Non-Goals

- Implementing page capture, content scripts, extraction, attachment,
  persistence, a Browser Host, or browser actions.
- Changing the current side-panel manifest, adding Chrome permissions, using an
  active-tab API, or changing authentication,
  storage, transport, build, packaging, or release status.
- Selecting Chrome, Tauri, Electron, Chromium, another host, or a repository
  topology.
- Adding DOM extraction, screenshots, PDF ingestion, or importing tabs, cookies,
  passwords, bookmarks, history, sessions, profiles, downloads, autofill,
  documents, or Atlas state.
- Defining autonomous browsing, continuous monitoring, background capture,
  accessibility scraping, or web-wide history.
- Adding command-bus tokens, runtime status tokens, routes, migrations, events,
  schemas, workers, provider behavior, identity writes, or memory writes.
- Widening beta, support, privacy, security, compatibility, or release claims.

## ADR Impact

- ADR-051 remains the accepted governing contract for the current private
  Chrome side-panel client's dual-auth and credential boundary.
- ADR-021 remains the proposed architecture boundary that separates search,
  reading, extraction, browser automation, and service-connector modes and
  treats remote content as untrusted data.
- ADR-004 continues to govern retrieval policy as control-plane authority.
- ADR-003 remains relevant to keeping user/message identity distinct from
  request and capture correlation.
- ADR-005 remains relevant to backend-owned account and identity boundaries.
- ADR-054 governs Browser Host technology, repository topology, protocol
  ownership, signing, and release ownership.
- ADR-070 governs chat-backed Browser Episode evidence, Browser Recall
  authority, continuity, retention, deletion, provenance, and export/restore
  boundaries. It narrows the durable-evidence interpretation of this contract
  without changing the current ephemeral attachment wire contract.

This contract remains host-neutral and does not by itself authorize Browser
Episode or Browser Recall implementation.

## Exit Criteria

This documentation task is complete only when:

1. the actor, trust-zone, authority, credential, capture, attachment,
   persistence, identity, memory, and action boundaries are explicit;
2. Guardian connectivity and page observation are separate permission domains;
3. the envelope, extraction limits, lifecycle, failures, protected pages,
   observability, invariants, and future proof surfaces are documented;
4. provenance, retention, identity, memory, and export/restore rules are
   explicit;
5. prompt-injection and credential boundaries are structural and explicit;
6. current implementation posture is labeled without release inflation;
7. the Architecture KB, validity matrix, and Browser Campaign route to this
   contract;
8. the Browser Campaign records the accepted Stage 01 inventory evidence and
   leaves Stage 03 as the next architecture decision;
9. documentation validation and scoped diff checks pass; and
10. only the four task-authorized documentation files are committed.

## Governing and Related Sources

- [`00-current-state.md`](./00-current-state.md)
- [`ADR-051`](./adr/051-chrome-side-panel-dual-auth-client-contract.md)
- [`ADR-021`](./adr/021-web-agent-boundary-and-retrieval-contract.md)
- [`ADR-004`](./adr/004-retrieval-policy-as-control-plane.md)
- [`chrome-side-panel-client.md`](./chrome-side-panel-client.md)
- [`web-agent-spec.md`](./web-agent-spec.md)
- [`runtime-protocol-token-contract.md`](./runtime-protocol-token-contract.md)
- [`account-export-restore-contract.md`](./account-export-restore-contract.md)
- [Stage 01 Browser extension inventory proof](./proofs/2026-07-30-codexify-browser-extension-repository-inventory.md)
- Companion contract: docs/architecture/browser-episodic-context-and-recall-contract.md
- Governing decision: docs/architecture/adr/070-browser-episodic-context-and-recall.md
- [`CODEXIFY_BROWSER_CAMPAIGN.md`](../Campaign/CODEXIFY_BROWSER_CAMPAIGN.md)
