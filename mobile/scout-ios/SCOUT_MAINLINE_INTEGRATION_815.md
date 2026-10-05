# Scout #815 mainline client integration receipt

## Lineage and scope

- Integration branch: `codex/scout-client-integration-815`.
- Base: current `main`, `e992d8e2b836167e87e4f3c9343ec596cf15f566`.
- Source evidence: `feature/scout-ios-remote-session`,
  `fa1329ce742bfdb9cc6d94880c4206f6d11109e0`.
- Backend dependency: the separate `codex/scout-backend-integration-815` PR.
  Its historical source is `codex/scout-account-handoff-815` at
  `68d6c061f786f680f198f7328d40753b096625db`.

The integration starts from current main and copies only the Scout client,
tracked application project, focused tests and directly relevant architecture
documents. Neither historical branch is merged. Historical provider/model-path
detours, execution credentials, coding workers, migrations and deployment
configuration are excluded. Current-main health-response validation and existing
Swift tests are retained. The README's governed document-node content hash is
refreshed for its two Scout entry changes; authority/freshness metadata and graph
relationships are unchanged. The containing commit and PR bind this receipt to the
integration tree; the source live-proof packet retains its original revisions.

## Preserved behavior and authority

`connection = endpoint/transport + explicit authentication mode`.
Guardian/Vault owns accounts and persisted threads, messages, tasks and documents.
Scout presents subordinate, connection-scoped state. Source branches and test
receipts supply evidence, not runtime authority or deployment approval.

- Explicit `localAPIKey` and `remoteSession` share one request-selection seam.
  Missing or invalid remote authority never falls back to a key or anonymous use.
- Hosted Access admission and canonical Guardian account identity remain separate.
  Access uses the existing public native OAuth/S256 browser flow. Guardian's
  explicitly confirmed, origin-bound S256 handoff issues an independent canonical
  `account_session`; the browser credential is never exported.
- Hosted requests put Access in Authorization and the account session in
  `X-Guardian-Account-Session`. ADR-092 permits edge-consumed Authorization only
  after the backend verifies the fixed hosted signed Access assertion. Personal
  nodes retain Guardian Bearer where supported. Tailscale remains transport.
- Access, account and key material remain in isolated profile/origin Keychain
  records. Configuration serializes non-secret metadata only. Wrong-origin
  dispatch, discovery and redirects refuse credentials; changing connections
  cancels pending sign-in and clears volatile account/thread projections.
- Restoration, expiry, reauthentication and logout are explicit. Only a marked
  account-lane failure invalidates account state; an unrelated operator 401 does
  not. Logout requests canonical revocation and removes local usable authority.
- Sending a message and requesting completion remain separate. Task acceptance
  is distinct from terminal completion. A completed task publishes a successful
  persisted-message read into observable conversation state; failure/cancellation
  does not fabricate output. Stale/overlapping reads and foreground refresh retain
  the selected profile/origin/thread identity.

These changes preserve ADR-051, ADR-091/092 and current-main task-event ownership
contracts. The separately reviewable backend PR carries ADR-092's scoped hosted
transport amendment. No new credential class, account ownership or release promise
is introduced. `00-current-state.md` remains the release gate.

## Fresh integration qualification

Executed from the client integration worktree on October 4, 2026:

```sh
CLANG_MODULE_CACHE_PATH=/tmp/scout815-main-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout815-main-module-cache \
swift test --package-path mobile/scout-ios \
  --scratch-path /tmp/scout815-main-swift-build \
  --cache-path /tmp/scout815-main-spm-cache --disable-sandbox
```

Result: **66 tests passed, zero failures**, including the complete existing suite
and the Access, handoff, account lifecycle, authentication boundary, qualification,
conversation refresh and ingress tests. Log: `/tmp/scout815-main-swift-tests.log`.

```sh
CLANG_MODULE_CACHE_PATH=/tmp/scout815-main-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout815-main-module-cache \
xcodebuild -project mobile/scout-ios/CodexifyScout.xcodeproj \
  -scheme 'Codexify Scout' -sdk iphonesimulator \
  -destination 'id=077E052A-54E0-41F5-BF47-F7BAED94599C' \
  -derivedDataPath /tmp/scout815-main-signed-derived-data \
  DEVELOPMENT_TEAM=5Q888BY3YZ \
  'OTHER_SWIFT_FLAGS=$(inherited) -disable-sandbox' build
```

Result: **BUILD SUCCEEDED** for the tracked shared scheme and existing proof
Simulator. `codesign` confirms an ad hoc Simulator signature on the built app.
Log: `/tmp/scout815-main-signed-build.log`. Task-specific writable caches and
`-disable-sandbox` accommodate the managed host environment. This is build/signing
proof; the new integration bundle was not live-authenticated or distribution signed.

The companion backend integration independently passes 749 backend/architecture
tests (259 core Scout/identity tests, 59 additional auth/logging regressions and
431 architecture contracts), 60 frontend tests and a production frontend build;
its receipt records those commands. Client pre-commit checks pass.
The complete client architecture-contract suite also passes **431 tests** after
refreshing the README's governed hash. XML/log:
`/tmp/scout815-client-architecture-results.xml` and
`/tmp/scout815-client-architecture-tests.log`. Existing unrelated broken-link
warnings in the architecture index remain warnings; no unrelated cleanup is included.
CI and review must qualify each exact PR head before either integration is merged.

## Historical live evidence and remaining gaps

[The original live packet](SCOUT_LIVE_CONTINUITY_2026-10-04.md) records the exact
source/build/runtime revisions: nine sign-in stages, protected read, existing
messages, thread create/rename, two persisted completion turns, task-event receipt,
foreground/resume, document browsing, logout and denied protected replay. Its
source/runtime evidence is not relabeled as a new integration live run.

Non-blocking evidence gaps remain explicit: personal-node live continuity, the
final physical iPhone continuity loop and deliberate failed/cancelled live tasks.
Those paths retain only the proof levels recorded in the historical packet and
focused tests. No Beta, TestFlight or App Store readiness is asserted.

Both integration PRs must reach main before #813 current truth is advanced and
#816 starts. The #818 App Intents/system-integration contract slice is downstream
of that merge gate. No App Intents work is included here.
