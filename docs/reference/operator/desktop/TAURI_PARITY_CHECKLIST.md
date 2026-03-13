# Tauri Parity Checklist (macOS-first)

Purpose: validate desktop parity against current end-user WebUI flows before local bundle sign-off.

## Preconditions

- Guardian backend is running and reachable (default: `http://127.0.0.1:8888`).
- Desktop shell can reach frontend dev/build assets.
- Desktop Connection settings are configured in-app:
  - Backend Base URL
  - Share Public Base URL
  - API key saved in secure keychain (local auth mode)

## Runtime Verification

- [ ] App boots without auth gate lockout when backend URL + API key are valid.
- [ ] `Guardian`, `Dashboard`, `Documents`, `Gallery`, `Settings` tabs all render.
- [ ] Theme + basic shell state persist after relaunch.

## Flow Verification

### Guardian

- [ ] Create/select thread and send message.
- [ ] Completion returns successfully.
- [ ] Event stream updates continue without manual refresh.

### Dashboard

- [ ] New thread creation from dashboard works.
- [ ] Workspace drawer opens/closes without visual/layout regressions.

### Documents

- [ ] Upload document succeeds.
- [ ] Uploaded document appears in list.
- [ ] Open in workspace works.
- [ ] Open in thread works.

### Gallery

- [ ] Upload image succeeds and renders.
- [ ] Context actions (delete/generate prompt) still function.
- [ ] No broken media URL behavior in desktop runtime.

### Share

- [ ] Share link creation succeeds.
- [ ] Copied URL is web-valid (not `tauri://...`).
- [ ] Shared URL resolves from browser using configured public share base.

### Settings / Connection

- [ ] Connection settings save successfully.
- [ ] Connection test passes against `/ping`.
- [ ] API key save/clear works through secure keychain commands.
- [ ] Export action opens external URL in desktop-safe path.

## Failure/Recovery Checks

- [ ] Invalid backend URL produces actionable error.
- [ ] Correcting backend URL recovers without app restart.
- [ ] Invalid API key fails auth predictably; updating key recovers.

## Local Release Gate

- [ ] `pnpm --dir frontend/src build` succeeds.
- [ ] `cargo check` succeeds in `src-tauri`.
- [ ] `make desktop-dev` launches app shell against external backend.
- [ ] `make desktop-build` produces local desktop bundle.

## Out of Scope for This Gate

- CI artifact signing/notarization
- Store packaging/distribution
- Embedded backend process management
