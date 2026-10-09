# Scout #816 starter: scoped thread entities and actions

Date: 2026-10-05. Status: branch implementation/test/build evidence;
not live Siri/Shortcuts qualification or release support.

## Starting authority

Base main: `54cc3359cc13991a5906f07595e84ff334f58df7`, after bounded
backend [#851](https://github.com/Resonant-Jones/Codexify/pull/851) and
client [#852](https://github.com/Resonant-Jones/Codexify/pull/852) merges.
Historical source branches remain evidence only. The separate prepared
[#818 contract PR #853](https://github.com/Resonant-Jones/Codexify/pull/853)
is CI-green at `469e426d9577cc849bc624558d9e195c7afedc91` and remains unmerged.
This starter follows its bounded system-integration contract and existing
ADR-051/091/092 authority; it introduces no new principal, credential class,
server route, account, access policy, migration or ownership semantics.

## Implemented slice

- `ScoutThreadEntity` contains only a scoped lookup ID, thread title and node name.
  Its namespace binds profile UUID, canonical HTTPS origin, encoded base path,
  explicit auth mode and canonical account subject (when using `remoteSession`).
  Local/operator scope never invents an account from a key. Credentials never
  contribute to entity IDs or enter display properties.
- `ScoutThreadEntityQuery` re-resolves current protected server data through
  `ScoutGuardianThreadsProbe`. Wrong-scope IDs fail before dispatch. Suggestions
  are empty; this slice performs no background indexing or automatic donations.
- `ListScoutThreadsIntent` reads the selected node's current thread-list page.
  Missing pagination metadata is treated as potentially incomplete. Entity lookup
  explicitly reports a missing reference on a partial page as unavailable from
  the current page; it does not claim deletion or a complete catalog.
- `CreateScoutThreadIntent` confirms the title and selected node/endpoint, then
  calls `ScoutCreateThreadProbe`. It requires a canonical positive returned ID
  and synchronous 200/201 response. HTTP 202 cannot become a creation claim.
  Unknown outcomes are not automatically retried. Creating a thread neither
  sends a message nor requests Guardian completion.
- Both intents require local device authentication. This OS gate never replaces
  Guardian authorization. Loss/change of profile or credentials invalidates
  suspended confirmation and delayed results. A dispatched write may have
  succeeded; stale-result errors say to check Scout before retrying.
- `ScoutThreadActions` imports no App Intents and contains no HTTP/auth
  implementation. It loads the existing selected profile and Keychain records,
  pins the captured canonical account session through the shared request auth
  seam, and delegates to the existing probes. Default SwiftUI service behavior
  is unchanged. Hosted Access and Guardian account identity remain separate;
  personal-node Bearer/local-key selection retains existing semantics.
- Two `AppShortcutsProvider` entries expose explicit list/create actions.
  Xcode's synchronized Scout source group includes the files. SwiftPM includes
  the actual entity/query/intent types so tests exercise the adapter mapping.

## Qualification

- Full SwiftPM suite: 82 tests, zero failures, including 10 new tests of actual
  intent/query adapters with synthetic URLProtocol transport. Coverage includes
  protected read/create mapping; scoped IDs; missing/deleted/partial lookups;
  confirmation cancellation; profile/auth changes; stale responses; canonical
  returned IDs; remote Bearer without key fallback; 202 and uncertain writes.
- Canonical signed Simulator build and strict codesign verification pass.
  The built app includes `Metadata.appintents` action/shortcut extraction.
- Task-specific writable caches and `--disable-sandbox` were used for SwiftPM;
  the Xcode build uses `-disable-sandbox`. A compatibility-only deprecated
  confirmation API remains for the existing iOS 17/macOS 13 deployment floor;
  iOS 18/macOS 15 and newer use Apple's current confirmation API.
- Logs: `/tmp/scout816-swift-tests.log`, `/tmp/scout816-signed-build.log`.
- No backend/browser code changed in this slice. The combined merged #815
  matrix remains separately recorded in the mainline integration receipts.

Commands, from the repository root:

```sh
CLANG_MODULE_CACHE_PATH=/tmp/scout816-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout816-module-cache \
swift test --package-path mobile/scout-ios \
  --scratch-path /tmp/scout816-swift-build \
  --cache-path /tmp/scout816-spm-cache --disable-sandbox

CLANG_MODULE_CACHE_PATH=/tmp/scout816-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout816-module-cache \
xcodebuild -project mobile/scout-ios/CodexifyScout.xcodeproj \
  -scheme 'Codexify Scout' -sdk iphonesimulator \
  -destination id=077E052A-54E0-41F5-BF47-F7BAED94599C \
  -derivedDataPath /tmp/scout816-signed-derived-data \
  DEVELOPMENT_TEAM=5Q888BY3YZ \
  'OTHER_SWIFT_FLAGS=$(inherited) -disable-sandbox' build

codesign --verify --strict \
  '/tmp/scout816-signed-derived-data/Build/Products/Debug-iphonesimulator/Codexify Scout.app'
```

## Remaining #816 work

#816 remains open. Actual Shortcuts/Siri display, confirmation and invocation
have not been exercised; extracted metadata/builds are not that proof. No new
live hosted/personal/device continuity is claimed. Additional open-thread routing,
send/completion, document/artifact and qualified task entities/actions remain
future #816 slices. The first query resolves only the existing thread-list page;
full pagination remains a deliberate limitation to address before broad discovery.
Task cancellation, indexing, onscreen annotations, donations, notifications and
custom Siri snippets remain deferred. #817 has not begun. This work does not
widen Beta/TestFlight/App Store or distribution readiness.
