# Scout #816 live Apple system-surface qualification

Date: 2026-10-05. Status: **IN PROGRESS — authenticated read/write not yet qualified**.

## Revision and runtime

Operator explicitly approved normal merges of #853 and #854. Both are merged:

- #853 contract: `57f29e19c27e309b64852269d594f0cfb4f1dc40`.
- #854 starter: `a9be208471c6d84b44a3d915cfa45e23c9d1bf01` (merged main).
- Both source heads/branches were preserved. This proof branch starts at that
  exact merged main, `codex/scout-shortcuts-live-816`.
- Canonical signed Xcode Simulator build from merged main succeeded; strict
  codesign verification passed. That bundle was installed without resetting
  the proof Simulator's stored profile or Keychain.
- Proof device: `Scout continuity proof 2026-09-30`, iOS 26.5,
  UUID `077E052A-54E0-41F5-BF47-F7BAED94599C`.
- Build log: `/tmp/scout816-live-signed-build.log`.
- UI operated through Device Hub / native CUA, not an in-process intent harness.

## Actual observations so far

1. Apple's Shortcuts app opens on the proof Simulator.
2. In a new shortcut's Search Actions catalog, searching `Scout` displays
   `Codexify Scout` and `List Scout threads`.
3. Adding the read action creates an actual Shortcuts action with its
   `Show When Run` option. Running it executes and displays the native error:
   `The protected thread read failed. Check the selected connection in Scout.`
   This proves discoverability/invocation/error presentation, not a successful
   Vault read or entity display.
4. Scout's Server page reports that hosted ingress requires renewal. The existing
   `Check stored ingress` action renews the stored grant and qualifies native
   admission at Guardian's independent account gate: HTTP 401,
   Cloudflare Ray `a45cb217fe0a96db-MIA`.
5. The separate `Check account session` returns HTTP 401 and explicitly leaves
   account-session protected read unqualified. No key/guest/browser fallback
   was selected and no write intent was attempted.
6. Scout's canonical Guardian `ASWebAuthenticationSession` was opened. Its
   ordinary `preview.codexify.space` sign-in consent was continued. Authentication
   entry is handed to the operator; no browser URLs, passwords, codes, cookies,
   tokens or callback parameters were captured in this packet.

The native Shortcuts error and Scout status were captured as non-secret UI
screenshots/accessibility observations in this task. Credential-entry/callback
screens are excluded from proof capture.

## Required live checks remaining

- [ ] Thread entity display in the actual Apple system surface.
- [ ] Read action returns and displays real authorized Vault-backed thread state.
- [ ] Create action presents title/node/endpoint confirmation before dispatch.
- [ ] Confirmed creation executes through existing Scout services.
- [ ] Returned canonical thread exists in Vault and re-resolves via entity query.
- [ ] Cancelling confirmation produces no write.
- [ ] Profile/account/auth change invalidates a pending action before dispatch.
- [ ] Capture completed system-surface proof without authentication material.

The entity query remains limited to the existing thread-list page. A partial page
must not be described as the entire thread universe or used by itself to prove
that a thread does not exist. The current 82-test fixture suite and metadata
extraction remain separate from these live acceptance checks. No new send,
completion, document or task intents are being added. #816 stays open; #817
remains deferred. No Siri invocation or release/distribution readiness is claimed.
