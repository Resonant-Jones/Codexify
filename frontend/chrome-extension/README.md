# Codexify Side Panel

Private, unpacked Manifest V3 client for a deliberately narrow Codexify chat experience in Chrome's native side panel.

This is an internal operator client. It is not a Chrome Web Store package, is not automatically updated, and is not part of Codexify's supported beta release surface.

## Build

From the repository root:

```bash
cd frontend
pnpm build:chrome-extension
```

The clean extension build is written to:

```text
frontend/dist/chrome-extension
```

The normal frontend build output is not used or overwritten.

## Load the unpacked extension

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Choose `frontend/dist/chrome-extension`.
5. Open Chrome's Extensions menu and pin **Codexify Side Panel**.
6. Click the Codexify toolbar action. Chrome opens the native side panel.

The first launch should show the connection form, not the chat shell.

## First private connection

1. Enter the base URL of an already-running Codexify backend, including its scheme and port when applicable. Enter the origin/base URL, not a `/chat/<id>` page URL and not an `/api` route.
2. Select one authentication method:
   - **Local API key** for a same-device/local-auth runtime, then enter that runtime's Guardian API key.
   - **Remote session** for a Tailscale/private-LAN runtime configured with remote auth, then enter a provisioned Codexify username and password.
3. Select **Save and connect** or **Sign in and connect**.
4. Review Chrome's host-access prompt. It must name only the configured backend origin.
5. Grant access. Remote mode exchanges the username/password through the existing `/api/auth/login` route, and the client then verifies authenticated thread access.

Local API keys are stored in this extension's `chrome.storage.local`, never `chrome.storage.sync`, and are not rendered back into the UI after connection. Remote passwords are never stored. Remote session tokens are stored in `chrome.storage.session`, which clears on browser restart and when the extension is disabled, reloaded, or updated. Extension storage is not application-level encrypted; anyone with control of the Chrome profile or host machine should be treated as able to inspect an active credential.

The two modes are mutually exclusive. Local mode sends only `X-API-Key`; remote mode sends only `Authorization: Bearer <session>`. Tailscale provides private transport but does not replace Codexify login.

Use loopback HTTP only for same-device local operation. Prefer private HTTPS for remote or overlay-network access.

## Rebuild and reload

After changing extension source:

1. Run `cd frontend && pnpm build:chrome-extension` again.
2. Return to `chrome://extensions`.
3. Select the reload icon on **Codexify Side Panel**.
4. Close and reopen the Codexify side panel.

Reloading an unpacked extension clears `chrome.storage.session`, so a remote connection must sign in again after each rebuild/reload. The saved backend URL and selected remote auth mode remain available.

The build removes stale files from `frontend/dist/chrome-extension` before emitting the new artifacts.

## Disconnect and clear credentials

1. Open the thread switcher.
2. Select **Disconnect**.

Disconnect best-effort revokes a remote session, removes the persistent profile/local key and session-scoped token, clears side-panel chat state, and asks Chrome to remove the origin permission granted for that backend. Local clearing still completes if the remote runtime is unavailable.

Removing the extension also clears its local and session-scoped storage data.

## Markdown rendering

Assistant messages are rendered as safe Markdown using the same `react-markdown` + `remark-gfm` stack as the main Codexify frontend.

Supported features: paragraphs, soft and explicit line breaks, headings, bold, italics, strikethrough, ordered and unordered lists (including nested lists), inline code, fenced code blocks, blockquotes, links, horizontal rules, and GFM tables.

Raw HTML is intentionally disabled — the renderer does not execute scripts, event handlers, embedded iframes, or arbitrary HTML supplied by the model. Unsafe link protocols (`javascript:`, `data:`, etc.) are stripped. Safe external links open in a new tab with `rel="noopener noreferrer"`.

User-authored messages remain literal and are not reinterpreted as Markdown.

## Known MVP limitations

- One extension-local connection profile only.
- Remote sessions require a new login after Chrome restart or extension disable/reload/update; there is no refresh-token or silent-renewal flow.
- Manual unpacked installation and manual rebuild/reload only.
- The side panel observes task lifecycle events but renders only persisted assistant messages as final output; it does not fabricate token streaming.
- Closing or reloading the side panel preserves the configured connection and selected thread, but does not persist an active task-event subscription. Reopen the selected thread to read any reply that completed while the panel was closed.
- No page awareness, selected-text capture, content scripts, screenshots, tab control, browser automation, context menus, uploads, voice, provider/model selection, persona editing, or command-bus UI.
- No full Codexify `AppShell`, workspace navigation, documents, gallery, settings application, or secondary inspector panels.
- Backend availability, exposure, TLS, authentication, provider readiness, queue health, and worker execution remain operator responsibilities.
- The private Tailscale/session mode does not establish public remote-access, cloud-provider, or release-support claims.

## Manual smoke proof

For a live proof, use an already-healthy backend and verify in order:

1. The toolbar action opens the side panel.
2. The host prompt is limited to the configured origin.
3. The selected authentication mode succeeds without the other credential header being sent.
4. Existing threads and persisted messages load.
5. **New Chat** creates a backend thread.
6. Sending persists the user message before completion acceptance.
7. **Completion accepted** remains pending until task-terminal evidence arrives.
8. The completed assistant reply is re-read from the backend transcript.
9. Closing and reopening the side panel restores the connection and selected thread within the same Chrome session.
10. Disconnect returns to the connection form and clears the credential.
