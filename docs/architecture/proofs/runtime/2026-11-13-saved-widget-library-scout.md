# Saved Widget Library and Scout implementation proof — 2026-11-13

Scope: explicit Guardian save, account-wide paginated listing, direct Library
launch, immutable version selection, Save as new, and Save new version.
ADR-102's 2026-11-13 clarification permits direct launch without a transcript
attachment. Existing account ownership, eligibility, accepted-completion
provenance, sandbox containment, and immutable revisions remain authoritative.

## Validation

- 177 backend tests passed: saved-widget promotion and revision storage against
  a disposable PostgreSQL 16 database, plus Scout transport admission.
- 84 web tests passed: Library navigation, explicit launch and dismissal,
  original marker coordinates, explicit version-base submission, and existing
  generative UI rendering.
- Web production Vite build passed. Existing chunk-size and React test-act
  warnings remain; neither was represented as release qualification.
- Scout: 169 SwiftPM tests passed and signed generic-iOS Xcode build succeeded.
- Earlier web test startup failures were environmental: read-only Vite cache,
  missing root dependency link, and an unhydrated LFS corpus. The isolated test
  container used temporary writable caches, existing dependency volumes, and
  hydrated tracked fixtures. Final tests passed.
- No production database mutation was used for automated tests. The disposable
  PostgreSQL container was task-specific and was stopped/removed after validation.

Commands (from the relevant checkout):
```
TEST_DATABASE_URL=<disposable-local-postgres> CODEXIFY_DISABLE_DOTENV=1 python -m pytest -q tests/routes/test_saved_widget_promotion.py tests/db/test_saved_widget_revision_store.py tests/identity/test_scout_account_transport.py
vitest run --config vitest.config.ts components/library/SavedWidgets.test.tsx components/library/LibraryView.test.tsx features/chat/components/__tests__/GenerativeUI.test.tsx
VITE_GENERATIVE_UI=true vite build --outDir /tmp/widget-library-build
swift test --package-path mobile/scout-ios
xcodebuild -project mobile/scout-ios/CodexifyScout.xcodeproj -scheme 'Codexify Scout' -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath /private/tmp/scout-library-build build
```

## Behavior and boundaries

The listing returns metadata only, scoped to the authenticated account and active
records, with bounded pages. Raw widget source is fetched only on explicit
launch, from an authorized immutable revision. Metadata selection does not run
code. Closing the launch surface removes the renderer.

Promotion and version appending accept only canonical source coordinates.
Invalid or unaccepted Guardian artifacts remain ineligible. A new version
requires the selected base revision; stale writes conflict. Save as new is a
separate explicit promotion and preserves the existing widget. This is not a
clone-from-stored-source endpoint.

The web and Scout clients expose earlier revisions for launch. No source-bearing
AI edit turn, automatic KB binding, implicit conversation access, source export,
deletion UI, or model-controlled save capability is added. Account-wide widgets
do not invent project/thread placements. These are bounded client/deployment
proofs, not general Beta or distribution qualification.

## Deployment observation

- Server/web implementation: `bab1b05d7`, cherry-picked into the serving checkout
  as `fe9bb0612`. The backend restarted healthy; `/ping` returned 200, and an
  unauthenticated `/api/saved-widgets` read returned 401.
- The authenticated hosted web Library displayed the active Saved widgets view
  and an empty list without an API error after reload.
- Scout implementation: `bd3e75c74`. Installation succeeded on ScoutNode iPhone
  and the physical iPad mini. Launching ScoutNode from Xcode tooling was denied
  because the phone was locked; the user was asked to unlock and perform the
  save/reopen check. Device Hub cannot inject taps into its mirrored phone view.
- Existing unrelated Xcode signing/workspace changes and the serving checkout's
  untracked Compose override were preserved. No push or merge was performed.

Live cross-client save/reopen verification awaits the user's chosen widget.
Installation, an empty authenticated list, and automated tests do not prove that
the phone save/reopen interaction has passed.

