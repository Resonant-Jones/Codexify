# Scout #816 live Apple system-surface qualification

Date: 2026-10-05. Status: **IN PROGRESS — live read/create/cancel qualified; pending-context invalidation remains live-unverified**.

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

## Actual observations

1. Apple's Shortcuts app opened on the proof Simulator. Its Search Actions
   catalog exposed `Codexify Scout`, `List Scout threads` and
   `Create Scout thread`.
2. Before account sign-in, invoking `List Scout threads` displayed the native
   error `The protected thread read failed. Check the selected connection in
   Scout.` This was an authentication checkpoint only.
3. Scout's Server page initially reported that hosted ingress required renewal.
   The existing `Check stored ingress` action renewed the stored grant and
   qualified native admission at Guardian's independent account gate: HTTP 401,
   Cloudflare Ray `a45cb217fe0a96db-MIA`.
4. The separate `Check account session` first returned HTTP 401 and left the
   account-session protected read unqualified. The operator then completed the
   canonical Guardian sign-in and selected **Continue to Scout**. Scout reported
   all nine authentication stages qualified and a protected Guardian thread
   read succeeded. Non-secret UI evidence showed account login HTTP 200 and the
   qualified hosted state `Access admitted / Authorization edge-consumed`.
5. In Apple's Shortcuts app, `List Scout threads` then returned 50 live entities
   from the current Vault page. After dismissing the Shortcuts result dialog,
   the actual entity rows rendered in the shortcut editor. The query UI stated
   that more threads may be available in Scout; this remains a partial catalog,
   not a complete thread universe.
6. `Create Scout thread` was added with `Show When Run` enabled. Its title prompt
   was followed by the system confirmation naming the title and the
   `Hosted Codexify` endpoint at `https://preview.codexify.space`. Selecting
   **Continue** produced the result `Created thread Scout #816 live entity proof
   2026-10-05 on Hosted Codexify. No message was sent and no Guardian response
   was requested.` A subsequent fresh protected entity query returned that
   title as its first entity.
7. A second distinct title reached the same final confirmation. Selecting
   **Cancel** returned to the Shortcuts editor without a create-success result.
   A subsequent protected query returned the prior successful proof thread at
   the head of the current page, with no cancelled-test title in the observed
   current page. The page remains partial, so this does not establish absence
   outside the returned page.
8. A pending confirmation remained present when the iOS Home screen was opened;
   the system confirmation blocked navigation to Scout Settings while pending.
   The pending action was cancelled without dispatch. Live profile/account/auth
   change invalidation is therefore not claimed. Focused tests exercise
   changed-connection and lost-authentication rejection before write dispatch.

Shortcuts, confirmation, create-result and query-result surfaces were observed
through Device Hub screenshots and accessibility state. Proof notes include only
the task-created neutral titles and non-secret status; unrelated account thread
titles, credential-entry/callback screens, browser URLs, passwords, codes,
cookies, tokens and callback parameters are excluded.

## Live checks

- [x] Thread entity display in the actual Apple system surface.
- [x] Read action returns and displays authorized Vault-backed thread entities.
- [x] Create action presents title/node/endpoint confirmation before dispatch.
- [x] Confirmed creation succeeds through existing Scout services.
- [x] Created thread re-resolves as an entity in a fresh protected query.
- [x] Cancelling the final confirmation produces no create-success result; the
      cancelled title is absent from the subsequent observed current page.
- [ ] Live profile/account/auth change invalidates a pending action before
      dispatch. Focused tests prove changed-connection and lost-authentication
      rejection at the service boundary; the system-surface race remains live
      unverified.
- [x] System-surface screenshots/accessibility observations captured without
      authentication material or unrelated thread titles.

The entity query remains limited to the existing thread-list page. A partial
page must not be described as the entire thread universe or used by itself to
prove that a thread does not exist. No new send, completion, document or task
intents are being added. #816 stays open; #817 remains deferred. No Siri
invocation or release/distribution readiness is claimed.

## Validation

- Focused `ScoutThreadIntentTests`: **10 passed, 0 failed**.
- First default SwiftPM attempt was blocked by managed-cache sandbox
  permissions. Retry used `/tmp/scout-shortcuts-816-swiftpm` with SwiftPM's
  `--disable-sandbox`.
- The earlier full 82-test fixture suite and signed Simulator/codesign result
  remain prior evidence. This turn reran only the focused test filter and did not
  rebuild unchanged source.
