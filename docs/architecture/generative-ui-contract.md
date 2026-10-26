# Generative UI Contract

Purpose: Define the normative contract for rendering model-authored interactive
interfaces inside ordinary Codexify chat, including the artifact channel,
rendering authority, sandbox containment, host bridge, persistence association,
and security invariants.

Last updated: 2026-10-10

Source anchors:

- `docs/architecture/00-current-state.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/adr/003-message-identity-vs-request-identity.md`
- `docs/architecture/adr/077-sandbox-execution-authority-and-provider-boundary.md`
- `frontend/src/lib/documentContext.ts`
- `guardian/core/chat_attachments.py`
- `guardian/workers/chat_worker.py`
- upstream `CopilotKit/OpenIntelligentUI` @ `f6e4388b26a64b9a0714943b08a1ce622b924eec`

## Scope

- The artifact channel, renderer selection, sandbox containment, host bridge,
  and durability association for interactive UI inside ordinary chat.
- This contract does **not** change provider routing, Guardian authority,
  completion acceptance, turn-lock semantics, or the task lifecycle.
- This contract creates no new backend subsystem, table, route, or identity.

### Relationship to the Saved Widget contract

The [Saved Widget Contract](./saved-widget-contract.md) and
[ADR-102](./adr/102-saved-widget-identity-and-revision-boundary.md) propose a
later, separate architecture for promoting eligible generated UI into durable,
account-owned, revisioned resources that can be invoked from any thread.

That proposal is **not** part of this contract, and nothing in it changes the
artifact channel, the renderer, the sandbox, the bridge, the artifact envelope,
or the wire format described here. The statement above — that this contract
creates no new backend subsystem, table, route, or identity — remains true of
*this* contract; the Saved Widget proposal is a distinct document with a
distinct status, and it is **Proposed**, not accepted.

A saved widget is rendered through the existing renderer and the existing
sandbox frame, so the containment, bridge, and provider-hygiene rules in this
document continue to govern it unchanged. A saved widget's *identity* is a
resource identity and is not a message, request, or attempt identity, so
ADR-003 continues to hold for both. See the Saved Widget contract for the
classification, ownership, revision, invocation, and editing boundaries.

## Upstream reference and pinned revision

The reference implementation is
[`CopilotKit/OpenIntelligentUI`](https://github.com/CopilotKit/OpenIntelligentUI),
pinned at revision `f6e4388b26a64b9a0714943b08a1ce622b924eec` (2026-10-09),
MIT licensed.

Upstream's reusable content is:

| Upstream concern | Codexify disposition |
| --- | --- |
| `generateSandboxedUi` ordered fields (`initialHeight`, `placeholderMessages`, `css`, `html`, `jsFunctions`, `jsExpressions`) | Adapted into the artifact envelope below. Not adopted as a LangGraph/CopilotKit tool. |
| Isolated sandbox iframe with progressive preview | Adapted. Rendered via `srcdoc` rather than the Websandbox CDN runtime. |
| `sendPrompt` / `openLink` host bridge functions | `sendPrompt` adapted. `openLink` **deliberately not implemented**. |
| Native component registry | Adapted as a Codexify-owned registry. |
| Next.js `/api/copilotkit` runtime route | **Not adopted.** Codexify's Guardian chat runtime stays authoritative. |
| LangGraph / `BoundedMemorySaver` process-memory checkpoint | **Not adopted.** Codexify's canonical Postgres persistence stays authoritative. |

Upstream itself documents that its checkpoint store is process memory and that
restarting or scaling can lose or split conversation state
(`docs/architecture.md`). Codexify must not inherit that weakness.

## Artifact channel

A generative UI artifact travels as a **structured marker inside canonical
assistant message content**, following the existing `cfy-`-prefixed marker
convention already used for `cfy-media` and `cfy-doc-tile`.

```text
<!-- cfy-ui:<base64url(JSON artifact)> -->
```

The base64url alphabet (`A-Za-z0-9_-`) excludes `>`, which is what makes an
HTML-comment-delimited regex safe. This is the same property
`documentContext.ts` already relies on.

Rationale, with the alternatives it rejects:

- **Chosen — in-content marker.** Codexify already proves this channel end to
  end for document-context tiles, including mid-stream rendering and
  restore-after-reload (`frontend/src/lib/documentContext.ts`,
  `GuardianChat.document-context.test.tsx`). The artifact is therefore owned by
  the canonical message and thread by construction: it needs **no new storage,
  no migration, no new read route, and no new authorization surface**. Content
  is already authorized by `require_thread_read_access` before it is ever
  returned by `GET /chat/{thread_id}/messages`.
- **Rejected — new JSONB column on `chat_messages`.** Storage/domain expansion
  must be earned. `extra_meta` already exists and already round-trips, but the
  artifact must also render *while streaming*, and the streaming draft carries
  content only (`ChatView.tsx` constructs the draft bubble from three
  primitives). A typed slot cannot render mid-stream.
- **Rejected — separate artifact table.** Reintroduces a second ownership
  model beside canonical messages, with duplicate-message and orphan risk that
  ADR-003 explicitly exists to prevent.

### Artifact envelope

```ts
type GenerativeUiArtifact =
  | { version: 1; kind: "native"; component: string; props: Record<string, unknown>; layout?: "compact" | "wide" }
  | {
      version: 1;
      kind: "sandbox";
      title?: string;
      html: string;
      css?: string;
      js?: string;
      initialHeight?: number;
      layout?: "compact" | "wide";
    };
```

Unknown `version` or unknown `kind` is **rejected at parse time**, not rendered.

### Responsive artifact sizing

`layout` is an optional width hint. `compact` (default) retains the existing
34rem artifact bound. `wide` uses the available Codexify chat lane; it cannot
request an arbitrary pixel width or extend outside the conversation viewport.
Unknown layout tokens fail validation. Native charts/tables and sandbox frames
share this same hint.

The isolated sandbox measures its body after scripts initialize and again when
content changes. A `ResizeObserver` and a DOM observer schedule bounded height
updates over the existing `resize` bridge. `initialHeight` sets first paint
height only. The host still clamps every request to 80-640px; taller interfaces
scroll inside the frame. No new host actions, credentials, or permissions are
introduced by measurement or width hints.

### Wire encoding

Two encodings are accepted, and their alphabets are disjoint: base64url uses
only `A-Za-z0-9_-`, so a payload containing `%` cannot be base64url. The
parser uses that to choose deterministically.

- **percent-encoded JSON** — the model-facing format taught by the system
  prompt. Models emit base64 unreliably by hand; percent-encoding JSON is a
  mechanical transform they get right far more often. Excludes `>`, so it stays
  safe inside an HTML comment.
- **base64url** — the canonical programmatic form used by
  `serializeUiArtifact`.

### Marker parsing rules

A marker is delimited by its terminator, not by the first `>`:

```text
complete marker      /<!--\s*cfy-ui:.*?-->/gis   (DOTALL)
unterminated marker  /<!--\s*cfy-ui:[^\n]*$/gm
```

Delimiting on `-->` matters. The `cfy-media` convention stops at `>`, which
leaks raw syntax into the transcript whenever a model emits an *unencoded*
payload containing HTML, because `<p>` supplies a `>` before the terminator. A
payload that genuinely contains `-->` still ends early and then fails
validation, which is fail-safe.

The unterminated pattern strips to the end of its **own line**, not the end of
the message. The contract requires the marker to sit on its own line, so this
removes a half-streamed payload while leaving prose on later lines intact.

Every marker is removed from display text whether or not it validates. The
invariant under all malformed model output: **marker syntax never reaches the
transcript, and anything that does render has passed full validation.**

### Cross-boundary marker agreement

The renderer and the inference strip are separate implementations in two
languages that must agree on what a marker is. When they diverged, the renderer
matched on `-->` while the strip still stopped at `>`, and an unencoded artifact
containing HTML leaked its HTML/JS into every subsequent provider turn for that
thread — invisible in both suites, because each only tested its own side.

Both sides therefore read one shared corpus,
`docs/architecture/generative-ui-marker-corpus.json`, which is the regression
mechanism. The corpus distinguishes `parses` (a **codec**-level property: the
envelope passes structural validation) from *renders*. An envelope naming an
unregistered component parses but displays nothing, because the registry
rejects it at render time; conflating those two layers produced a misleading
assertion while the shared corpus was being written.

## Model emission contract

The model learns the format from a feature-gated block appended to the Guardian
system prompt (`guardian/cognition/generative_ui_prompt.py`), enabled by
`GUARDIAN_GENERATIVE_UI` and **default off**.

This rides the ordinary system prompt rather than the tool-exposure rail on
purpose. `guardian/tools/chat_exposure.py` advertises tools only to DeepSeek or
to a local Whoosh'd provider with eligible capability, so a tool-based emission
channel would silently fail for most user-selected providers and would breach
the local-first, user-selected-provider invariant.

The block describes the real sandbox limits (no network, no import map, no
`eval`, only `sendPrompt` and `resize`) so the model does not write code that
silently fails at runtime. A test asserts the documented worked examples decode
to the shapes they claim, and that the stated limits have not drifted from what
the frame enforces.

Assembly is proven, not assumed: the block is appended to the scratchpad and
therefore passes through prompt budgeting and truncation. Tests assert it is
absent when disabled, present when enabled, still present at a tight token cap,
and that enabling is purely additive — removing the block reproduces the
disabled prompt exactly. Without this, the block could be silently truncated
away while every isolated unit test still passed.

**Unproven:** whether a given local or hosted model reliably emits a valid
marker on request. That requires a live provider turn and has not been
observed.

## Rendering authority

`ChatBubble` renders artifacts above assistant prose, in the slot already used
by document-context tiles and attachment tiles. Precedence is:

1. `native` artifact → Codexify-registered trusted React component.
2. `sandbox` artifact → isolated `srcdoc` iframe.
3. Neither → ordinary markdown text, unchanged.

A registered native component executes **first-party Codexify code** with
validated props. A sandbox artifact executes **model-authored untrusted code**
under containment. Only registered components may be rendered as native;
there is no arbitrary component resolution.

## Sandbox containment

Sandbox artifacts are untrusted. The containment boundary is the iframe
`sandbox` attribute plus a document-level CSP — and, since the navigation
repair below, a **trusted outer wrapper** that keeps the network policy
in force across navigation.

```html
<!-- app page -->
<iframe sandbox="allow-scripts" srcdoc="<trusted wrapper document>" />
```

```html
<!-- trusted wrapper document, built by Codexify -->
<iframe id="cfy-ui-inner" sandbox="allow-scripts" srcdoc="<generated document>" />
```

- `allow-scripts` **only**, on **both** frames. Notably absent:
  `allow-same-origin`, `allow-forms`, `allow-popups`, `allow-top-navigation`,
  `allow-modals`, `allow-downloads`.
- Without `allow-same-origin` each frame runs in an opaque origin. The wrapper
  therefore has no same-origin access to host `storage`, cookies, `document`,
  or any host API, and the generated document has no same-origin access to
  the wrapper either. This matches upstream's documented posture ("The sandbox
  has no same-origin access to storage or host APIs").
- The generated document is built by Codexify, which injects a restrictive CSP
  **before** any generated content:

  ```text
  default-src 'none';
  script-src 'unsafe-inline';
  style-src 'unsafe-inline';
  img-src data: blob:;
  connect-src 'none';
  form-action 'none';
  base-uri 'none';
  frame-src 'none'
  ```

### The trusted wrapper, and why the boundary needs it

The generated document's CSP governs **that document**. A same-frame
navigation replaces it with a document that declares no policy, and that
replacement could then issue network requests. That escape was reproduced in a
real browser; see
[the navigation-containment proof](./proofs/runtime/2026-10-26-generative-ui-navigation-containment-proof.md).

The repair is a **trusted outer wrapper document**, built by Codexify, that
carries:

```text
default-src 'none';
frame-src 'none';
script-src 'unsafe-inline';
style-src 'unsafe-inline';
img-src data: blob:;
connect-src 'none';
form-action 'none';
base-uri 'none'
```

`frame-src 'none'` is the load-bearing directive. It governs which URLs may
be loaded into **child frames**. A child loaded from `about:srcdoc` is
permitted, so the generated frame still loads; a child navigated to any real
URL is blocked **before the request is made**. The network boundary therefore
survives navigation, because the navigation never happens.

The wrapper's `frame-src` is scoped to the wrapper document. It is
deliberately **not** applied to the Codexify app document, so other legitimate
workspace iframe surfaces are unaffected.

The wrapper contains no generated source. It embeds the generated document in a
nested sandboxed `srcdoc` frame and relays bridge messages. Generated content
can never reach the wrapper's CSP or its relay logic, because it lives in a
separate, opaque-origin document.

### Deliberate tightening versus upstream

Upstream's sandbox CSP allows `script-src`/`connect-src` to four public CDNs and
ships an importmap. **Codexify does not.** Generated UI receives **no network
access at all**, consistent with the objective's security invariant against
unrestricted network access and with ADR-077's deny-by-default network posture.
Codexify therefore ships **no CDN importmap**; generated code may not fetch
remote modules, fonts, tiles, or APIs.

This is a deliberate, recorded divergence from upstream, not an oversight.

Note also that `src-tauri/tauri.conf.json` declares `"csp": null`. The iframe
`sandbox` attribute is therefore the load-bearing containment boundary and must
not be weakened.

## Host bridge

The sandbox may not call host APIs directly. It may only send **validated**
messages over `postMessage`, each of which Codexify authorizes explicitly.

The bridge now has **two hops**, and each hop validates independently.

1. **Generated frame → trusted wrapper.** The generated document's own bridge
   script posts to its parent, which is the wrapper. The wrapper accepts the
   message only when all of the following hold:
   1. `event.source === innerFrame.contentWindow` (source binding).
   2. `event.origin === "null"` (the opaque origin of the sandboxed frame).
   3. `event.data.channel === "cfy-ui"` and `event.data.session === <nonce>`,
      where the nonce is minted per mount (session binding).
   4. `event.data.action` is in the allowed set.
   5. The action payload validates against its schema and bounds.

   The wrapper then relays **only** the two approved actions to the host. It
   never forwards a message it did not validate, never forwards an unknown
   action, and never forwards a message from any frame other than the exact
   nested frame.

2. **Trusted wrapper → Codexify host.** The host re-validates the relayed
   message rather than trusting the wrapper:
   1. `event.source === wrapperFrame.contentWindow` (source binding).
   2. `event.origin === "null"` (the opaque origin of the sandboxed wrapper).
   3. `event.data.channel === "cfy-ui"` and `event.data.session === <nonce>`.
   4. `event.data.action` is in the allowed set.
   5. The action payload validates against its schema and bounds.

   A message posted **directly** by the nested generated frame has a different
   `event.source` and is rejected here, even when it knows the session token.
   The host therefore never treats generated code as an authority, and the
   wrapper never becomes a second control plane: it is a relay with no
   capability of its own.

| Action | Payload | Effect |
| --- | --- | --- |
| `resize` | `{ height: number }` | Sets frame height, clamped to a bounded range. |
| `send_prompt` | `{ text: string }` | Routes a bounded, requested prompt into the **existing** composer prefill seam (`cfy:composer:prefill`). |

`send_prompt` deliberately does **not** send. It hands the requested text to
the composer, and the user reviews it and presses send. This is the whole
point: a sandbox can *request* a turn but can never cause one, which is what
makes the invariant against silent action execution and permission escalation
provable rather than aspirational. The request then travels the same authorized
composer path a human turn would, including existing busy-state rejection.

Explicitly **not** implemented in this slice:

- `openLink` — denied. Upstream gates it behind
  `NEXT_PUBLIC_OPEN_LINK_ALLOWED_ORIGINS`; Codexify has no equivalent operator
  configuration, so the capability is absent rather than half-guarded.
- Direct send. Upstream submits the prompt itself; Codexify requires a human
  to press send.

Any unrecognized action, malformed payload, oversized text, or failed
validation is **ignored**, never partially applied.

## Durability and identity

- The artifact is part of the canonical assistant message's own content. It is
  therefore owned by that message and that thread, under the existing
  account/project/thread authorization boundary.
- Restoring after navigation, reload, or reconnect replays the stored content.
  The artifact is never regenerated and no message is duplicated.
- ADR-003 is preserved: the artifact rides message identity. A retry or replay
  that reuses the same message content restores the same artifact; it does not
  create a second artifact identity, and an artifact is never bound to request
  or attempt identity.
- Code blocks, plain prose, and document tiles around the artifact are
  unaffected.

## Provider hygiene

Generated UI source is **not** sent back to the model. Before inference,
Guardian strips `cfy-ui` markers from message content, mirroring the existing
`cfy-media` strip in `chat_completion_service.py`. This keeps a multi-kilobyte
base64 blob out of every subsequent provider turn in the thread and keeps
untrusted script out of the prompt.

## Feature gate

Rendering is gated. With the gate off, artifacts are neither rendered nor
executed; the marker is stripped from display and the message renders as
ordinary text. The gate is a build-time `import.meta.env.VITE_GENERATIVE_UI`
check following the existing `VITE_PRIVATE_PREVIEW` pattern, default **off**.

Emission is gated separately by `GUARDIAN_GENERATIVE_UI`, also default **off**.
The two flags are independent: enabling emission without rendering would
produce markers that degrade to text, and enabling rendering without emission
yields a renderer no model will use. Enable both to turn the feature on.

Per `00-current-state.md`, the release gate is `HOLD` and this surface is not
Beta Supported. Implementation presence does not promote it.

## Security invariants

1. Generated UI is untrusted and is never granted Guardian credentials, host
   filesystem access, Tauri native capabilities, privileged APIs, or network
   access.
2. Only registered native components may execute as first-party code; an
   unknown component id degrades to text rather than resolving dynamically.
3. The sandbox frame runs in an opaque origin with `allow-scripts` only.
4. Every bridge message is source-bound, session-bound, origin-checked, and
   schema-validated. Unknown or malformed messages are ignored.
5. The bridge exposes exactly one host capability in this slice (`send_prompt`)
   and it only prefills the composer. It cannot cause a turn.
6. Generated UI source is stripped before provider inference.
7. A render-time failure inside an artifact is caught by a dedicated error
   boundary and degrades to an inline notice. It never blanks the transcript.
8. No release, provider, or inference configuration claim changes.

## Known limitations

- No `openLink` capability.
- No direct send from generated UI; a human always presses send.
- **No `eval` or `new Function`.** The CSP grants `script-src 'unsafe-inline'`
  but deliberately not `'unsafe-eval'`, so string-compiled code is blocked.
  Confirmed in a real browser: an `eval`-based expression evaluator silently
  failed, while a recursive-descent parser computed correctly. Generated code
  that depends on dynamic compilation will not work.
- No network access inside generated UI, including map tiles or remote fonts.
  Upstream allows four public CDNs; Codexify ships no importmap.
- No cross-artifact control synchronization; each artifact is an independent
  snapshot, matching upstream's documented behavior.
- The native registry is intentionally small (`chart.bar`, `table.rows`);
  unknown components degrade to text rather than resolving dynamically.
- The gate is build-time only, not operator-configurable at runtime.
- The artifact payload rides message content, so a large HTML/CSS/JS artifact
  enlarges the stored message row. It is stripped from provider inference, but
  it is still persisted. If artifacts grow large enough to matter, a dedicated
  content-addressed artifact table is the next step — deliberately not taken
  here, because the artifact must also render mid-stream.
- A partial (mid-stream) marker fails validation and renders nothing until the
  payload is complete. This is the intended fail-safe behavior.
- A partial marker is also **stripped from display**, not merely ignored. A
  half-received marker has no closing `-->`, so it would otherwise be shown to
  the user as raw text until the reply finished. The unterminated-marker pattern
  is `<!--\s*cfy-ui:[^>]*$`; `[^>]*` is safe because neither wire encoding can
  contain `>`, so only a genuinely unterminated trailing marker is stripped and
  prose that merely mentions the prefix is left alone.
