# Scout #815 hosted continuity proof — October 4, 2026

Scope: authenticated Scout Simulator continuity against `https://preview.codexify.space`, backed by the preserved VaultNode runtime. The live loop and server-side logout denial are proven. This is branch/runtime qualification, not a supported Beta, TestFlight, App Store or physical-device continuity claim. #816–#818 are deferred.

## Lineage and artifacts

- Client branch: `feature/scout-ios-remote-session` in the `44dc/Codexify` checkout.
- Original goal checkpoint: `558438525dcaea4da48547218ce25913f73a2915`; ancestry remains intact.
- Edge amendment starting client: `8245a02df12fa1815969b161d023be4ad63b82c0`.
- Latest live-proof slice starting client: `76d33fae34ffa7e3fd866e2121251282f8fa1925`.
- Current signed application source: `fab00177b66b38b97e1f8149edf43bea23b1c1d4`. Documentation closeout commits are reported separately.
- Backend branch: `codex/scout-account-handoff-815` in the separately reviewable `scout-account-handoff/Codexify` worktree. Edge amendment starts at `d5d258d840e5b561af4fbe39ece0cb066f0e6941`; serving transport/ADR commit is `5836ed986e4cc6175b5184fe6b5d2fb23a989ed1`.
- Proof Simulator: `077E052A-54E0-41F5-BF47-F7BAED94599C`, “Scout continuity proof 2026-09-30,” iOS 26.5. Bundle: `ai.resonantconstructs.codexify.scout`. Final install launched PID 49987 without uninstall, profile reset or Keychain removal.
- Canonical project/scheme: `mobile/scout-ios/CodexifyScout.xcodeproj` / `Codexify Scout`. Simulator signing is ad hoc; this does not qualify distribution signing.
- VaultNode artifact: `/Volumes/Dev_SSD/Codexify-scout815-auth/5836ed986-edge`. Existing image: `sha256:579c15b3b31b74ac3feef814ced96af8595c4a3f289f0b955ef8bbf6b0a61291`.

No reset, rebase, merge, branch deletion, push, issue mutation or history reconstruction occurred. The final documentation commits must leave both worktrees clean.

## Authentication and connection authority

`connection = endpoint/transport + explicit authentication mode`.

Hosted Codexify is the convenience/default lane. A public native OAuth client and S256 PKCE admit Cloudflare Access through ASWebAuthenticationSession. That ingress grant is separate from Guardian identity. The existing Guardian browser account login offers Continue to Scout, which prepares a single-use, origin-bound, 60-second S256 handoff. Exchange revalidates the canonical browser account and live parent session, then issues an independent exact-purpose `account_session` for the same canonical user. Browser session bytes are never returned to Scout.

Scout sends Access in Authorization and the existing canonical account credential in `X-Guardian-Account-Session`. For the explicitly qualified preview composition, Guardian recognizes edge-consumed Authorization only after exact-host/private-preview signed Access validation using its fixed issuer/audience. Missing Authorization alone grants no trust. Access is neither reconstructed nor moved to another origin header. ADR-092's approved amendment changes transport only, not credential purpose, principal or account authority. Conflicting, invalid or absent account selectors fail closed without key, guest, operator, cookie or anonymous fallback.

Personal nodes remain independent HTTPS endpoints with an explicitly supported auth mode: Guardian account Bearer where supported, or explicitly selected local API key. Connecting to one's own node does not require a paid hosted account. Tailscale is transport, not identity. Separate Access/account/key records are isolated by profile UUID and canonical origin; profile serialization is non-secret metadata. Redirects cannot receive credentials, changing connections clears volatile projections, and Guardian/Vault remains durable authority. Personal-node continuity was not newly exercised live in this proof.

## Nine-stage native sign-in

Public attempt `d0d1f7bd-7ba3-4710-9b0a-49ccad8a4938` passed every native stage, directly observed in Scout Settings and corroborated by the operator's “All nine passed” report:

| Stage | Observed result |
| --- | --- |
| Hosted ingress credential available | Passed |
| Guardian web login launched | Passed; bounded backend browser arrival HTTP 200 |
| Guardian account login confirmed | Passed; canonical account login HTTP 200 |
| Handoff callback received | Passed in ASWebAuthenticationSession |
| Callback state validated | Passed locally |
| Handoff exchange accepted | Passed, HTTP 200 |
| Fresh native account session issued | Passed; fixed issuance observation checked |
| Session stored for this profile and origin | Passed; validated Keychain save/readback |
| Protected Guardian read with account header | Passed, HTTP 200 and decoded thread list |

The fixed native observation was “Access admitted / Authorization edge-consumed.” Runtime correlation became unavailable after the ten-minute process-local receipt lifetime; this does not negate the local exchange/issuance/storage/read evidence, and no complete correlated backend event trail is claimed. Safe backend logs independently retain browser arrival and successful canonical login for this attempt. Diagnostics contain only fixed stages, classifications, HTTP status and public attempt IDs.

Expired ingress was renewed through Check stored ingress using the existing refresh grant. Renewals reached Guardian's independent account gate at HTTP 401. They created no new OAuth client or account authority. A later delayed attempt `bf77e198-783d-4ec2-a82c-b9bc7699b99d` received its callback but stopped before exchange with the former `invalidCallback` classification. The browser interval exceeded an ingress-grant lifetime; the exchange builder checks that captured grant before callback state, so this result is consistent with expiry but does not independently expose its exact cause. The misleading generic classifier was corrected at `fab00177b`: the typed ingress-expiry error now reports `credentialExpired` and asks for existing-grant renewal/fresh sign-in. Invalid callbacks remain rejected; no state/PKCE or admission check changes.

## Actual app continuity

| #815 step | Proof |
| --- | --- |
| 1. Launch Scout | Canonical signed app installed and launched on the existing proof Simulator |
| 2. Use hosted connection | Existing hosted remote-session profile retained; no local-key substitution |
| 3. Canonical account authentication | All nine native stages above |
| 4. Protected read | Decoded account-owned thread read HTTP 200; later Check account session loaded 50 threads |
| 5. Display thread list | Authenticated list visibly loaded in Guardian tab |
| 6. Existing persisted messages | Opened an existing account thread; persisted user/Guardian roles loaded, without recording its content |
| 7. Create thread | Created proof thread ID 76 |
| 8. Rename | Renamed to `Scout #815 native continuity 2026-10-04`; read-only database verification matches |
| 9. Send message | Send acknowledged; first user row persisted before any completion attempt existed |
| 10. Distinct response action | Request Guardian response invoked separately from Send on both proof turns |
| 11. Request completion | Both requests accepted as tasks; acceptance was not labeled completion |
| 12. Capture task identity | Public task IDs and durable request/turn bindings below |
| 13. Observe task events | Actual account-authorized task stream loaded; final run visibly included `task.completed` |
| 14. Truthful terminal states | Completed live; failed/cancelled behavior unit-tested without synthesizing assistant output, not deliberately forced live |
| 15. Publish persisted output | Both terminal reads updated the actual visible thread with persisted Guardian replies |
| 16. Foreground/resume | Home backgrounded Scout; launch without termination resumed the same process/selected proof thread. Final source `5c9ad3cba` resumed PID 47100; GET `/api/chat/76/messages` returned 200 after the checkpoint |
| 17. Documents/artifacts | Protected global document list loaded ten available rows; opening an account-owned document loaded metadata and content. No document names/content were recorded or mutated |
| 18. Logout and denial | Canonical logout HTTP 200 followed by protected replay HTTP 401; subsequent local account check failed before dispatch because no session remained |

The known refresh defect was fixed at `b704291b3`: thread and task views share observable conversation state, and terminal completion assigns fetched persisted messages rather than discarding them. Selection/profile/origin/revision guards reject stale reads. The live replies prove the visible update, beyond a “Messages refreshed” label.

The task view initially displayed Connecting after a finished stream. Commit `716b405dd` retains terminal task truth while showing Stream ended after stream closure. The final completion run observed both “Stream ended” and “Task completed. Messages refreshed,” then the persisted reply in the thread.

## Durable proof rows and accepted identities

Read-only repeatable-read SQL verified thread 76, four messages and two completion attempts. Only synthetic markers and public identifiers are documented.

| Turn | Accepted task | Request / turn binding | Persisted result |
| --- | --- | --- | --- |
| First | `0058f121-59f4-4483-8693-4571816287e5` | `req_a0d215ecf3384e02bf77929e6b25b99e` / `7f641d95-eca9-4821-be87-0147bd8023c2` | User 911; assistant 912, `SCOUT_815_OK` |
| Final completion build | `9727f0cc-20e4-43a5-bd51-d4d589aa4f0a` | `req_c0d9f61515124af9be2a31ad122c7bed` / `9c2f8d00-2381-4cd0-af0b-30281b9abdee` | User 913; assistant 914, `SCOUT_815_FINAL_OK` |

Assistant row 912 SHA-256: `b71ca1f1be4adf054f245d62cbb3eca9d06b197349b87187e79426b2603ac4fd`.
Assistant row 914 SHA-256: `855f8bf901ed44515924050c2e0fbcb801d3d3d27ab74ac1e1e2f31600a539ba`.
The final completion/foreground/document run used `5c9ad3cba72c76cfeeb56ea0bc2a4dfc541d7462`; subsequent source changes touch only bounded logout-result and ingress-expiry diagnostics.

## Logout proof and final diagnostic check

At `2026-10-04T20:55:20Z`, Scout's account read succeeded immediately before logout. The app prepared the canonical request, removed the local account Keychain record, sent POST `/api/auth/logout` (200), then reused those already prepared bytes only in memory for GET `/api/chat/threads` (401). Safe query/referrer-free origin logs independently confirm that sequence. No credential was exported, saved again or used as fallback.

The subsequent local check reported: “Sign in to Guardian for this connection. No account session is stored; no request was sent.” This qualifies local removal and fail-before-dispatch separately from remote denial.

The first proof classifier additionally required a general account-invalidation marker and underreported the actual denial. Commit `dad8a4803` restricts this causal post-logout check to the exact protected URL, HTTP 401 and the fixed qualified Access-admission observation. It does not relax the general session-invalidation policy or reinterpret unrelated operator failures. Source `fab00177b` includes that correction and the explicit delayed-ingress diagnostic. A final native check of the corrected logout display is pending Mac unlock; the already observed server denial remains proven.

## Preserved runtime and data

The bounded deployment changes only four read-only backend mount sources. Existing image, direct Python/Uvicorn startup and `CODEXIFY_SKIP_STARTUP_SEEDING=1` remain active. Final read-only audit finds backend healthy, schema `a7b9c4d2e6f1` unchanged, and serving hashes equal the deployed source:

- Route, both package mounts: `424bd8f3eff1aed8f06bae5d24cbd00df30bce38570e987eeb2b87e1eff864ec`.
- Account transport, both mounts: `206d3df4cd8aca3a5043fc09818a9d648a51f0dd00a1a723c67d4a84127c832a`.

After excluding the newly created proof thread/messages, all 75 pre-existing threads and 878 pre-existing messages retain their recorded row fingerprints. Project, system-document/link, imprint, provider/runtime and sync-job counts/fingerprints match the deployment checkpoint; user count remains seven. Ordinary approved login/logout presence and the new proof conversation are app lifecycle writes, not seed/provisioning or schema operations.

All 29 other services matched immediately after deployment. During final observation, two services in the separate `codexify_chat_branch_proof_896387ad2` stack changed only start time at approximately 21:13 UTC; their IDs/images/config hashes match. This task issued no restart for that stack. The remaining 27 match entirely. This is a concurrent runtime observation, not attribution of an external restart cause.

No further Cloudflare Access, OAuth registration, BIC, DNS, Tunnel, database migration, seed, account provisioning, ownership or auth-policy change occurred in this amendment/live-proof slice. Earlier separately approved recovery is historical and was not repeated.

## Validation actually executed

- Complete SwiftPM: **66 tests passed, zero failures**, including credential selection/isolation, expiry, logout, wrong-origin refusal, qualification, persisted refresh, stale-selection protection and failed/cancelled task handling.
- Canonical signed Simulator: **BUILD SUCCEEDED**, installed/launched with profile and Keychain retained.
- Integrated backend: **100 tests passed** across qualification, transport, handoff, mounted routes, no-seed startup, strict-purpose migration and operator-route auth.
- LoginPage: **16 tests passed**; Vite production build passed.
- Task-scoped diff checks and applicable commit hooks passed. Backend mypy has five pre-existing errors in three untouched files; only that hook was skipped for the scoped backend source commit. No repository-wide clean mypy claim is made.
- New documentation links resolve and diff checks pass. Six pre-existing unresolved links in the architecture index were verified against starting content and left outside this scope; no clean repository-wide link claim is made.

Final Swift command (repo root):

```sh
CLANG_MODULE_CACHE_PATH=/tmp/scout-goal-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout-goal-module-cache \
swift test --package-path mobile/scout-ios \
  --scratch-path /tmp/scout-goal-swift-build \
  --cache-path /tmp/scout-goal-spm-cache --disable-sandbox
```

Final Simulator command (authorized host lane; managed CoreSimulator access is unavailable):

```sh
CLANG_MODULE_CACHE_PATH=/tmp/scout-goal-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout-goal-module-cache \
xcodebuild -project mobile/scout-ios/CodexifyScout.xcodeproj \
  -scheme 'Codexify Scout' -sdk iphonesimulator \
  -destination 'id=077E052A-54E0-41F5-BF47-F7BAED94599C' \
  -derivedDataPath /tmp/scout-goal-signed-derived-data \
  DEVELOPMENT_TEAM=5Q888BY3YZ \
  'OTHER_SWIFT_FLAGS=$(inherited) -disable-sandbox' build
```

Local logs: `/tmp/scout-final-expiry-swift-tests.log`, `/tmp/scout-final-expiry-signed-build.log`, `/tmp/scout-edge-backend-results.xml`, `/tmp/scout-edge-browser-tests.log`, `/tmp/scout-edge-browser-build.log`. They are local ephemeral validation evidence, not tracked secrets or release artifacts. Backend/browser exact commands and runtime deployment details remain in the separately reviewed qualification document.

## Changes, limits and next task

The client changes the shared request-authentication selector, profile/origin Keychain stores, Access OAuth/PKCE, canonical account handoff, safe nine-stage diagnostics, shared observable conversation refresh and truthful task/Settings UI. Neighboring existing tests cover those seams. Backend/browser work stays separately reviewable: scoped account transport, one-time canonical handoff, LoginPage Continue to Scout, non-secret qualification and the approved no-seed startup guard. ADR-092 carries the approved transport decision; no additional ADR is needed for the UI/proof corrections.

Physical-device installation was previously qualified, but this final authenticated loop ran on the Simulator. Personal-node live sign-in, cross-node switching, deliberate failed/cancelled production tasks, distribution signing, general federation/sync/offline inference and release support are unproven here. The ten-minute runtime receipt is bounded correlation evidence, not durable identity or execution authority.

#815 has sufficient live evidence to close after the final diagnostic checkpoint and clean documentation commits. The issue itself is not mutated. The next logical Scout task is #816 App Entities/App Intents, subject to deliberate user selection; #816–#818 are not started.

## Reviewable client commits since the original checkpoint

```text
b704291b3 Publish Scout persisted messages after task completion
b8c56656b Record Scout hosted authentication prerequisite and continuity proof
6b6aedeec Record authenticated browser and native ingress discovery
345f59e00 Identify serving Guardian auth and preview Access configuration
3a46e3493 Record approved Scout OAuth and native discovery blocker
bd0becc19 Qualify scoped Scout ingress discovery after BIC exception
7bc556b49 Add Scout native PKCE ingress qualification flow
bf21ebdf0 Record physical iPhone deployment for OAuth qualification
88e104f2b Record OAuth report and disabled hosted origin
aa7bb4834 Bound hosted recovery before automatic migration
d524be1fa Record preserved database restoration and schema boundary
b5cb07df6 Verify recovery backup and restored preview state
dfce40b2d Qualify stored Scout ingress and correct remote auth diagnostics
f1515aa39 Record native Scout admission and bounded account handoff decision
899ad8ff2 Implement scoped canonical Scout remote account sessions
7c0343d9f Record Scout account handoff deployment checkpoint
bd98e07a9 Document independent native session amendment and no-seed boundary
c7a36c265 Record deployed Scout native-session and no-seed qualification
3f6d1cdcd Expose staged Scout authentication qualification
5bfcb099b Record installed Scout authentication diagnostics
3f6cd5570 Classify Scout ingress availability before Guardian sign-in
07da312dc Expose bounded Scout native admission classifications
8245a02df Record Scout native Authorization mismatch checkpoint
ae6855b72 Qualify edge-consumed hosted admission in Scout diagnostics
76d33fae3 Record installed Scout edge admission checkpoint
716b405dd Report ended Scout event streams accurately
5c9ad3cba Prove hosted Scout revocation with an in-memory denied read
dad8a4803 Recognize qualified hosted replay denial after logout
fab00177b Explain ingress expiry during Scout browser handoff
```
