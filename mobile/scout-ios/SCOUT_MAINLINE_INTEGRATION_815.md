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

## PR review follow-up

Repeated Use hosted Codexify selection preserves the saved profile UUID, keeping
its origin-scoped Keychain records recoverable. Switching to a personal origin
does not send hosted credentials there; returning to hosted can recover the same
credential scope. The hosted preset is available from Endpoint Profile even on
a new/local draft.

HTTPS scheme case and surrounding whitespace are normalized consistently with
profile validation before origin checks, including credential-bearing dispatch.
Origin, port and forbidden URL-component checks remain fail closed. Message
refresh status now renders beside cached messages, so an expired session or
failed foreground reread cannot silently present stale data as refreshed.
Connection testing loads a personal API key using the captured endpoint that the
request will test, so a draft edit before the asynchronous action runs cannot
pair another node's key with the previous endpoint.
Foreground and terminal conversation refresh use the same ephemeral,
cookie-free, no-redirect authenticated session as other Scout services. The
redirect regression now exercises that configured session's actual delegate.

The personal-node local API-key lane remains first-class. Personal account Bearer
transport and isolation tests are retained, but Scout does not yet provision a
personal-node account session. Settings explains that limitation and disables new
selection of remote account mode for a personal endpoint; imported/stored remote
profiles still fail closed without their canonical session. This is a native
provisioning gap, not a claim that Tailscale or endpoint transport decides identity.
No alternate login or API-key fallback is added.

After these review repairs, the complete SwiftPM suite passes **69 tests, zero
failures** and the signed proof-Simulator build again reports **BUILD SUCCEEDED**.
The commands above are unchanged. Logs: `/tmp/scout815-review-swift-tests.log` and
`/tmp/scout815-review-signed-build.log`. These are isolated tests/build proof;
the historical live packet is unchanged.

## Final boundary review repairs

Personal HTTPS endpoints retain their configured base paths during protected
requests and logout. Origin extraction no longer rejects those valid profiles;
hosted ingress authorization and native sign-in still require the qualified
preview root endpoint. Preview base paths do not acquire hosted credentials.

A marked account-session rejection deletes only the account token selected by
that request. Compare-and-delete serializes with Keychain save/load/delete across
store instances, so a delayed rejection of session A cannot remove replacement
session B or advance the view generation. The hosted selector is the account
header, never the Access Bearer; personal nodes retain canonical account Bearer.

Settings observes account-store generations and compares a process-local token
fingerprint with its displayed authority. External deletion or replacement clears
stale qualification and restores actual local status. Active browser operations
retain their controller; each operation rechecks authority when it ends. Own
sign-in/logout changes preserve their qualification/status. Fingerprints are
neither persisted nor displayed. Settings lifecycle behavior is code/build proof,
not a new live UI qualification.

The complete SwiftPM suite passes **72 tests, zero failures**, including personal
base-path transport, rejected-versus-replacement session deletion, and independent
hosted account selector regressions. Log: `/tmp/scout815-boundary-swift-tests.log`.
The signed Simulator build succeeds and its bundle passes strict codesign
verification. Log: `/tmp/scout815-boundary-signed-build.log`. No historical live
packet, source branch or external authentication configuration changed.

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

## Verified combined mainline — 2026-10-05

Backend PR #851 merged as `5b879e8179c34b592006fc2bfacfedd282bb0d2b`; client
PR #852 merged as `54cc3359cc13991a5906f07595e84ff334f58df7`. Both exact integration
heads are ancestors of that mainline commit. Neither historical source branch
was merged wholesale, changed or deleted. All reported review threads were
resolved after fixes. Final-head automated review hit the account usage limit;
local final-diff inspection is recorded in each PR. Both PRs' CI is green; one
same-head frontend retry passed after an unchanged cancellation timing test failed.

The combined checkout freshly passes **774 backend/architecture tests**, **72
SwiftPM tests**, **61 focused browser tests**, the frontend production build and
the signed Simulator build with strict codesign verification. Exact commands are
the matrix above with the added supported-profile, beta-quarantine and WebSocket
order regressions, the CI FastAPI/Starlette overlay and the test virtual environment
on PATH. Logs/XML: `/tmp/scout815-merged-backend-tests.log`,
`/tmp/scout815-merged-backend-results.xml`, `/tmp/scout815-merged-swift-tests.log`,
`/tmp/scout815-merged-browser-tests.log`, `/tmp/scout815-merged-browser-build.log`,
and `/tmp/scout815-merged-signed-build.log`. The checkout's exact tracked frontend
LFS configuration was hydrated before browser validation; temporary dependency
symlinks were removed. This is combined source/test/build proof, not a new live loop.

#813 now marks #815 complete on main; #815's stale backend publication note is
corrected. The historical live packet and its non-blocking gaps remain unchanged.
#818's bounded system-integration contract can now precede beginning #816 from
the merged Scout service layer; neither is promoted to a proven system surface.
