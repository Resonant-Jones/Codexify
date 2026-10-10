# Runbook: verify generative UI in a live Codexify chat

Purpose: close the last open requirement in
`docs/architecture/proofs/runtime/2026-10-10-generative-ui-runtime-proof.md` —
proving that a **real** Codexify chat, with a real provider, produces an
interactive UI.

Everything else is already proven. This covers only the model-emission step.

## What is already proven (do not re-test)

Rendering, sandbox containment, host-bridge authorization, streaming, and
restore-after-reload are proven in a real browser. See the runtime proof.

## Prerequisites

- A working Codexify dev stack (backend, Postgres, gateway).
- Your chosen inference provider already configured and working. Generative UI
  is provider-neutral, but reliability of *emission* varies by model.

## 1. Enable both flags

Two independent flags, both default off. Edit your root `.env`:

```dotenv
GUARDIAN_GENERATIVE_UI=true
VITE_GENERATIVE_UI=true
```

`GUARDIAN_GENERATIVE_UI` is read by the backend process.
`VITE_GENERATIVE_UI` is build-time, so the frontend dev server must be
**restarted** after setting it. Vite reads env from `frontend/` with prefix
`VITE_` (`frontend/src/vite.config.ts:45-47`), so `frontend/.env.local` also
works if you prefer not to use the root file.

Both values are documented in `.env.example`.

## 2. Ask for something interactive

Send a request that genuinely warrants a tool, not prose:

> Give me a working calculator I can use right here in the chat. Then show a bar
> chart of thread volume: Mon 42, Tue 68, Wed 51.

## 3. Confirm what happened

Check in order:

1. **An artifact rendered.** A calculator with working buttons, and a bar chart.
   Click the calculator controls — they must compute.
2. **The marker is in the stored message.** View source on the assistant
   message. You should see a line beginning `<!-- cfy-ui:` near the end.
3. **Restore works.** Reload the app, reopen the thread. Both artifacts must
   reappear and be interactive, with no duplicate message.
4. **The artifact never leaked into the prompt.** On the next turn, nothing in
   the model's context should contain the generated HTML/JS.

## 4. Report back

Paste **the raw assistant message text** (view source), and note:

- Which provider and model produced it.
- Whether the artifact rendered, and whether it was interactive.
- Whether a second attempt was needed.

That is enough to record the outcome either way. A failure is a useful result:
it tells us the emission contract needs a tool-call channel rather than prompt
guidance, which is a real finding, not a bug to hide.

## If the marker is missing but an artifact rendered

Check the gate actually took effect: `VITE_GENERATIVE_UI` is build-time, and a
stale dev server silently keeps the old value.

## If nothing renders and no marker appears

Most likely the model chose prose. That is allowed behavior — the guidance asks
it to prefer prose for ordinary answers. Rephrase to demand an interactive tool.