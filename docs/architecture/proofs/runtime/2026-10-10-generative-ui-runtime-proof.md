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

## Live model emission: attempted and blocked

The one requirement this proof does not satisfy is "a real Codexify chat
produces an interactive UI". Two routes were attempted and both are blocked by
the environment, not by the implementation.

**Route 1 — configured model via the agent shell.** A prompt-emission test was
assembled and attempted against the models reachable from this session
(`minimax/MiniMax-M3.1-Flash-Preview`, `MiniMax-M3`, `MiniMax-M2.7`) using the
verbatim output of `build_generative_ui_guidance_block()` as the system prompt.
The call returned `401 {"code":401,"message":"token is required"}`. A provider
block exists in the runtime config, but no credential is exposed to the agent
shell, and retrieving one is not appropriate.

**Route 2 — local model.** Ollama is installed at `/opt/homebrew/bin/ollama`
but is not serving, and `~/.ollama` is empty (0 B): no models are present. A
local model would require a multi-GB download, which is the user's call.

**Route 3 — full Codexify stack.** Requires Docker, Postgres, Neo4j, a gateway,
and provider credentials. Nothing was running: ports 8888, 8001, and 5432 are
all closed.

Consequently the emission contract is proven only up to the model boundary: the
guidance block is assembled into the real system prompt, survives prompt
budgeting, and its worked examples decode to the shapes they claim — but no
model has been observed emitting a valid marker. Treat model-emission
reliability as **unproven working theory**.

## Automated coverage

| Suite | Result |
| --- | --- |
| `frontend/src/features/chat/components/__tests__/GenerativeUI.test.tsx` | 64 passed |
| `frontend/src/features/chat` + `lib/documentContext` (regression) | 555 passed / 43 files |
| `guardian/tests/test_chat_attachments.py` | 11 passed |
| `guardian/tests/test_generative_ui_prompt.py` | 8 passed |
| Backend inference-path subset | 9 passed |
| `tsc --noEmit` | clean |

Both the frontend parser and the Guardian inference strip read the same
`docs/architecture/generative-ui-marker-corpus.json`. That shared fixture is a
regression mechanism: the two are separate implementations in two languages,
and they previously diverged in a way that leaked generated HTML/JS into the
model prompt while both suites stayed green.

Native components render into the **host** document rather than the sandbox, so
their escaping is proven rather than assumed: markup injected through a chart
title, a series label, a table title, or a table cell survives only as inert
text, and hostile prop magnitudes are clamped by the registry rather than by the
model.

## Re-verification after parser changes

Containment and interaction were re-proved in Chrome after the marker-parsing
changes, so the evidence above matches the current code rather than an earlier
revision:

- `sandbox="allow-scripts"`, `contentDocument` null, frame `localStorage`
  blocked with `SecurityError`, deny-all CSP with no remote origin.
- Marker syntax absent from the rendered page; malformed-artifact prose intact.
- Calculator again computed `12 + 30 = 42` through real clicks.

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
- **`table.rows` is exercised in jsdom only.** It is covered by registry,
  rendering, degradation, and escaping tests, but was not driven interactively
  in the browser harness the way `chart.bar` and the calculator were.
- **A pre-existing backend test fails independently of this work.**
  `test_metacog_prompt.py` references `MetacognitionEngine.build_summary_prompt`,
  which exists nowhere in the codebase at base or HEAD; the test file is
  byte-identical to the base commit. Not a regression here.
- `ChatView.loop-guards.test.tsx` is a pre-existing scroll-dependent flake: it
  fails intermittently in a full run and passes 3/3 in isolation.

## Reproduction

```bash
cd frontend
./node_modules/.bin/vite build --config vite.harness.config.ts
cd .harness-dist && python3 -m http.server 4177
# open http://localhost:4177/generative-ui-harness.html
```