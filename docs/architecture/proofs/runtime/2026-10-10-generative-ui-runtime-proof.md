# Generative UI runtime proof

Date: 2026-10-10
Contract: `docs/architecture/generative-ui-contract.md`
Upstream reference: `CopilotKit/OpenIntelligentUI` @ `f6e4388b26a64b9a0714943b08a1ce622b924eec`

Scope of this proof: the generative UI **rendering, interaction, containment,
and restore** path in a real browser. It does not claim a live provider turn.

## Harness

The proof mounts the real `ChatBubble` component with canonical message content
containing four messages: a sandboxed calculator, a native bar chart, a
malformed artifact, and ordinary prose.

- Harness entry: `frontend/src/generative-ui-harness.tsx`
- Harness build: `frontend/vite.harness.config.ts` (proof-only, separate config,
  PWA disabled, `VITE_GENERATIVE_UI` forced on)

The harness exists because jsdom does not execute iframe `srcdoc`. Every
containment and interaction claim below is therefore real-browser evidence, not
a unit-test proxy.

## Containment (real browser, Chrome)

Probed from the host document against the live iframe:

| Probe | Result |
| --- | --- |
| `iframe.sandbox` | `allow-scripts` — only |
| `iframe.contentDocument` | `null` — opaque origin blocks the parent |
| `frame.contentWindow.localStorage` | throws `SecurityError` |
| CSP present in `srcdoc` | yes, injected ahead of generated content |
| CSP remote origin | none |

Enforced CSP as built by `buildSandboxDocument`:

```text
default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';
img-src data: blob:; connect-src 'none'; form-action 'none';
base-uri 'none'; frame-src 'none'
```

No `frame-src`, `connect-src`, or CDN entry. Upstream permits four public CDN
origins; Codexify permits none and ships no importmap.

### Containment finding: `eval` is unavailable

The first calculator implementation evaluated its expression with
`new Function(...)`. Under this CSP the calculator silently rendered `Error`
instead of a result. `script-src 'unsafe-inline'` does not imply
`'unsafe-eval'`, so the `Function` constructor is blocked.

This is correct and intended behavior, not a defect. It was confirmed by
replacing the evaluator with a recursive-descent parser, after which the same
controls computed correctly. Generated UI **cannot** use `eval`, `new Function`,
or string-compiled code. This is recorded as a known limitation.

## Interactive calculator (real interaction)

Clicked `1`, `2`, `+`, `3`, `0`, `=` through Chrome DevTools, targeting the
frame's own elements.

- After `1`: display showed `1`.
- After the full sequence `12 + 30 =`: display showed **`42`**.

The frame's document title read `ready:bridge-present`, proving the host
bridge object was injected and available to generated code.

## Structured visualization

The native `chart.bar` artifact rendered as host SVG (not in a frame) with five
bars and a legend: Mon 42, Tue 68, Wed 51, Thu 87, Fri 63. No third-party
charting dependency was involved.

## Transcript integrity

- A malformed marker (`<!-- cfy-ui:@@@not-a-valid-payload@@@ -->`) rendered
  **no** artifact and leaked **no** marker syntax; the surrounding prose
  rendered normally on both sides.
- An ordinary message rendered with `code` and **bold** intact.
- Prose, headings, and fenced code blocks surrounding a valid artifact were
  unaffected.

## Responsive presentation

Measured at an emulated 390×844 viewport:

| Measure | Value |
| --- | --- |
| Viewport width | 390 |
| Document scroll width | 390 — **no horizontal overflow** |
| Iframe width | 350, within viewport |
| Chart SVG width | 320, within viewport |

## Host bridge (real browser)

The calculator exposes an "Ask Guardian to explain" control that calls
`window.cfyUI.sendPrompt(...)`. A host listener on `cfy:composer:prefill` was
installed before the click.

Result after clicking:

```json
{"prefillEventsReceived":["Explain that 12 + 30 = 42"],"transcriptUnchanged":true}
```

The request reached the host and was routed to the existing composer prefill
seam. Critically, **no message was sent**: the transcript contains no trace of
the requested text. A sandbox can request a turn but cannot cause one. This is
the runtime proof of the no-silent-action-execution invariant.

## Restore after reload

The harness was reloaded with cache bypassed. The calculator and chart were
rebuilt from canonical message content and became interactive again, with no
regeneration call, no extra message, and no duplicate artifact. Automated
coverage additionally asserts that two mounts of the same content produce an
identical frame document apart from the per-mount session nonce.

## Automated coverage

| Suite | Result |
| --- | --- |
| `frontend/src/features/chat/components/__tests__/GenerativeUI.test.tsx` | 32 passed |
| `frontend/src/features/chat` + `lib/documentContext` (regression) | 523 passed / 43 files |
| `guardian/tests/test_chat_attachments.py` | 5 passed |
| Backend inference-path subset | 6 passed |
| `tsc --noEmit` | clean |

## What this proof does not establish

- **No live provider turn.** The artifacts were injected as canonical message
  content by the harness. Whether a specific local or hosted model reliably
  emits a valid `cfy-ui` marker on demand is unproven and depends on model
  behavior and any prompting added later.
- **No end-to-end Guardian round trip.** The backend side is proven by unit
  tests over `render_content_for_inference`, not by a live queued worker turn.
- **Lint unverified.** `eslint` could not run in this environment:
  `eslint-plugin-react` is declared in `frontend/src/package.json` but is absent
  from the shared installed tree. This is a pre-existing environment gap, not a
  regression from this work.
- **`table.rows` is registered but not exercised in the browser.** It is
  covered only by registry unit assertions.

## Reproduction

```bash
cd frontend
./node_modules/.bin/vite build --config vite.harness.config.ts
cd .harness-dist && python3 -m http.server 4177
# open http://localhost:4177/generative-ui-harness.html
```