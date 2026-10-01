# Scout remote-session goal: bounded progress and hosted prerequisite

Date: 2026-10-01 (America/New_York; validation below performed September 30)
Status: incomplete; #815 cannot close.

## Lineage and scope

Starting branch: `feature/scout-ios-remote-session`.
Starting HEAD: `558438525dcaea4da48547218ce25913f73a2915`.
Starting working tree: clean. The tracked #822 checkpoint equals HEAD.
No local commits were discarded, rewritten, rebased, or replaced. No merge or push occurred.
Client repair commit: `b704291b3` (`Publish Scout persisted messages after task completion`).
The ending documentation commit is reported in the chat closeout.

This slice changes only the Scout client and its directly relevant documentation.
Guardian, frontend, Cloudflare, Tailscale, Whoosh'd, providers, and database state were not modified.

## Authentication trace and evidence classes

**Observed live, September 30:** Opening `https://preview.codexify.space` in the Codex browser redirects to the `resonant-constructs.cloudflareaccess.com` Access login. Its heading is `Log in to Codexify Private Preview`; Google and `Send login code` are offered. This establishes an Access application in front of the hostname, beyond ordinary Tunnel ingress. No credentials or codes were entered by the agent.

**Observed browser UI, October 1:** After the operator completed sign-in in Chrome, `/login` displayed `Your workspace is ready` and reported an active session. Continuing opened `/chat`; the sidebar displayed existing threads, and opening an existing thread rendered a four-message conversation. This proves an accessible browser workspace and rendered existing conversation, not a captured protected API response, deployed credential-purpose enforcement, native credential handoff, or Scout continuity. The agent did not inspect browser session storage, cookies, or tokens, and did not send a message or request inference. Running Vault lineage remains unverified.

**Credentialless ingress discovery, October 1:** Requests from the approved host lane with `Accept: application/json` to preview's `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server` returned HTTP 302 with a `Cloudflare-Access` challenge advertising a `resource_metadata` URL. Reading those exact advertised `/.well-known/cloudflare-access-protected-resource/...` URLs returned HTTP 200 JSON: `protected=true`, team domain `resonant-constructs.cloudflareaccess.com`, and the sole advertised authentication method `cloudflared`. No authorization or token endpoint was supplied by the preview resource metadata. The team domain's standard `/.well-known/oauth-authorization-server` returned issuer, authorization/token/revocation endpoints under that same team origin, authorization-code and refresh-token grants, unauthenticated public-client support (`none`), and PKCE `S256`. Team-wide OAuth capability does not prove that the preview application enables it or permits an iOS callback/client.

Cloudflare's [Managed OAuth documentation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/) describes an opt-in application setting, authorization-code discovery for non-browser clients, and allowed HTTPS redirect URIs. The observed 302 and `cloudflared` advertisement suggest the preview application has not exposed that managed flow; this is an inference awaiting control-plane inspection, not confirmed configuration. Any ingress token must remain distinct from Guardian's account token. No Access setting was changed or client registered.

**Read-only control-plane confirmation, October 1:** Following operator dashboard sign-in, the `Codexify Private Preview` self-hosted Access application was inspected. Its destination is `preview.codexify.space`, with no path restriction; one Allow policy is attached (`Allow exact private-preview operators`). Its login methods are Google and One-time PIN, application session duration is 24 hours, and Cloudflare One Client authentication is off. Cookie settings show HTTP Only on, binding cookie off, and SameSite Lax. Managed OAuth is **off**, confirming the earlier ingress inference. Its inactive options display localhost and loopback clients on, no listed allowed redirect URI, grant duration inherited from application session duration, and a default 15-minute access-token lifetime. The live dashboard explicitly permits exact custom-scheme redirect URIs, unlike the narrower redirect wording in the linked prose documentation. No policy rule identities, secrets, browser cookies, or credential values were copied; no setting was saved.

**Serving source identification, October 1:** Existing SSH access to VaultNode permitted read-only Docker inspection. The private-preview backend and frontend containers mount `/Volumes/Dev_SSD/Codexify-main/guardian` and `frontend`, respectively; their Nginx origin mounts that tree's `docker/private-preview/nginx.conf`. The mounted checkout HEAD is `f83fe5da326871d1948ba79d90831be1402375ec`. The inspected auth source files and Nginx configuration have no working-tree modifications. The unrelated `/Users/chriscastillo/Codexify` checkout is not the serving source and was not used as deployed auth truth. Backend image identity is `sha256:7ae26800d2090c735cb313ef7f9da72d584d68d2b548e82d378f5ebc89fcf8ce`; mounted files, rather than image tag or another checkout's HEAD, establish this source evidence.

The serving `guardian/routes/auth.py` resolves the canonical User from the login identifier, checks its password and private-preview eligibility, and issues `purpose=account_session` with the session store's 24-hour TTL. `/auth/login` and `/api/auth/login` return `token`, `user_id`, and `expires_at`, without setting an account cookie in that handler. Serving `useAuth.ts` and `lib/api.ts` persist the returned credential under `guardian.auth.token` in session storage and attach it as `Authorization: Bearer` in remote mode. `gc_session` is an accepted alternative request credential; it is not the credential transport used by this web login handler. Logout revokes the session mapping and clears browser state. No OAuth callback, native exchange, or account-session refresh endpoint exists in these inspected deployed seams. This establishes serving-source behavior; this run did not capture a new live login request/response or inspect the user's actual stored token.

Container reads produced these source SHA-256 values: `guardian/routes/auth.py` = `cb6c90e194db9394919f8c5f6440521fe58636a48c7be1c5394998e7d4f7abad`; `guardian/core/auth.py` = `c936e59b85f1c78396b98df5f28cc91ef97758c5b1be553f7aaf2b3be1531a83`; `guardian/core/auth_dependencies.py` = `553389a3af018b20cc4f6dc1645ec0568ea01d5161c857a7d58aa65b20f6b639`.

**Next bounded handoff:** A system browser can reuse the hosted Guardian login and canonical User authority, but the current page only returns to the workspace. A native handoff therefore needs a separately reviewable, short-lived, single-use, PKCE-bound code exchange that issues an ordinary Guardian `account_session` for the already authenticated User, rather than exporting the browser's token or converting Access identity into an account. ASWebAuthenticationSession does not promise reuse of Chrome's session storage; the operator may need to sign in again in its system browser. Exact native callback validation and per-profile Keychain isolation remain required. This describes the missing seam, not an implemented or deployed endpoint. Native ingress credential presentation must also be qualified alongside Guardian Bearer before selecting request headers; two distinct tokens cannot occupy the same Authorization field.

**Historical live evidence:** The repository's [2026-09-01 ingress proof](../../docs/architecture/proofs/runtime/2026-09-01-private-preview-cloudflare-ingress-provisioning-proof.md) records Access admission followed by a distinct Guardian email/password login. This is dated evidence, not a current authenticated runtime result.

**Inspected source:** Scout's branch predates ADR-092. Its `guardian/routes/auth.py` calls a purpose-less signer. Current GitHub main was separately inspected at `8665590900fecdfb4c318fdcf813b11fe7119c66`, without integrating that tree:

1. [LoginPage](https://github.com/Resonant-Jones/Codexify/blob/8665590900fecdfb4c318fdcf813b11fe7119c66/frontend/src/pages/login/LoginPage.tsx) submits the Guardian account email/password through `useAuth`.
2. [useAuth](https://github.com/Resonant-Jones/Codexify/blob/8665590900fecdfb4c318fdcf813b11fe7119c66/frontend/src/components/auth/useAuth.ts) calls `/auth/login` through the API client, stores the returned Guardian token in browser session storage, and clears it on logout.
3. [Guardian auth routes](https://github.com/Resonant-Jones/Codexify/blob/8665590900fecdfb4c318fdcf813b11fe7119c66/guardian/routes/auth.py) expose `/api/auth/login` and its `/auth/login` alias. Login resolves the canonical `User`, issues `purpose=account_session`, stores its token-to-user mapping, and returns `token`, `user_id`, and `expires_at`.
4. The inspected session store uses a 24-hour TTL. Guardian accepts its account token through Bearer or `gc_session`; logout revokes the mapping. Expired/revoked credentials require ordinary reauthentication. No renewal, mobile callback, or browser-to-native exchange route was found in the inspected account-auth seams. Server authorization remains decisive; browser token presence is not protected-route proof.
5. [ADR-092](https://github.com/Resonant-Jones/Codexify/blob/8665590900fecdfb4c318fdcf813b11fe7119c66/docs/architecture/adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md) separates `account_session`, `operator_session`, and Hosted Room guest credentials. Scout must use only account credentials in `remoteSession`, never reinterpret an Access token or local key as an account session, and never fall back across lanes.

The source trace establishes two authentication boundaries. It does not establish that current VaultNode serves the inspected main commit or that every deployed validator enforces ADR-092. Current Access policy details, admission expiry, and logout/renewal behavior were not read from its control plane.

**Native handoff limitation:** Apple's [ASWebAuthenticationSession flow](https://developer.apple.com/documentation/authenticationservices/authenticating-a-user-through-a-web-service) requires a website callback to deliver the result to the app. [Cloudflare authorization-cookie documentation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/) explains the separate ingress cookie check. A browser reaching a workspace is therefore insufficient proof that Scout's `URLSession` requests are admitted or possess a Guardian account token. The inspected web flow redirects to `/`, with no existing native handoff. No callback, cookie export, Access bypass, second login authority, or operator-token substitution was invented.

## Completed client repair

- `ScoutConversationState` is a transient observable projection of persisted messages, shared by conversation and task views.
- Successful task completion fetches persisted messages and publishes the result to the conversation instead of discarding it.
- Refresh failure reports the actual read failure and preserves the previous persisted view; it does not report `Messages refreshed.`
- Failed/cancelled tasks neither fetch completion output nor synthesize assistant text.
- Selection is profile ID + endpoint URL + explicit auth mode + thread ID. Changing selection clears messages; late responses and older overlapping reads cannot replace newer or other-node state.
- Foreground/resume refresh retains the selected conversation. Display-only metadata changes preserve connection identity.
- Endpoint/auth changes reset volatile tab views and navigation. This does not implement per-profile credential storage; the existing global local API-key lifecycle remains future work within this goal.
- The task stream view uses a cancellable SwiftUI task.

## Validation actually executed

From the repository root:

```sh
CLANG_MODULE_CACHE_PATH=/tmp/scout-goal-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout-goal-module-cache \
swift test --package-path mobile/scout-ios \
  --scratch-path /tmp/scout-goal-swift-build \
  --cache-path /tmp/scout-goal-spm-cache --disable-sandbox

CLANG_MODULE_CACHE_PATH=/tmp/scout-goal-clang-cache \
SWIFTPM_MODULECACHE_OVERRIDE=/tmp/scout-goal-module-cache \
xcodebuild -project mobile/scout-ios/CodexifyScout.xcodeproj \
  -scheme 'Codexify Scout' -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/scout-goal-derived-data \
  CODE_SIGNING_ALLOWED=NO 'OTHER_SWIFT_FLAGS=$(inherited) -disable-sandbox' build
```

- Complete SwiftPM XCTest suite: **27 tests, zero failures**, including seven conversation regressions and the existing authentication/health tests.
- Canonical generic iOS Simulator build: **BUILD SUCCEEDED**.
- `python3 scripts/validate_docs.py`: passed. Scoped `git diff --check`: passed.
- First SwiftPM attempt without task-local module caches failed due to a managed-shell module-cache write denial. The corrected cache paths passed; user-level configuration/security caches remained unavailable warnings.
- Simulator discovery failed in the restricted shell, then succeeded in the approved host lane.
- Automatic approval review rejected installing over the existing simulator's potentially non-trivial app state. A fresh simulator was created instead; the old app data was preserved.
- Fresh device: `Scout continuity proof 2026-09-30`, iPhone 17, iOS 26.5, UDID `077E052A-54E0-41F5-BF47-F7BAED94599C`.
- Fresh-device boot and install succeeded. `simctl launch` returned `ai.resonantconstructs.codexify.scout: 37137`.
- Native UI inspection was unavailable through the computer-use app binding. Process launch proves no visual shell, authentication, or continuity behavior.

## Remaining prerequisite and next work

Browser admission and workspace access now succeed after operator sign-in. Serving-source lineage and Guardian account issuance behavior are now identified from mounted container source; fresh login-response and native behavior remain unproven. Credentials must remain in the intended secure UI; browser access does not by itself supply native admission or a session handoff.

Before a hosted native implementation can be qualified, establish the operator-approved Access admission mechanism for native API requests and the canonical Guardian browser-to-native handoff. Managed OAuth is now confirmed disabled for this application. Approval has been requested for enabling it with only `ai.resonantconstructs.codexify.scout://access-callback`, localhost/loopback clients disabled, a 24-hour grant, and a 15-minute access token, preserving existing identity-provider and Allow policies. No change has been made. After that exact operator interaction, inspect the exposed application discovery/client registration and qualify ingress credential presentation compatible with Guardian account authentication. If implementation requires a new ownership/authorization decision or weakening Access, stop for that decision instead of changing Guardian opportunistically. Do not distribute a shared service token or copy browser cookies/tokens through chat or terminal.

Once those prerequisites are established, resume `remoteSession`, Keychain-only per-profile credential isolation, hosted/personal profile UI, restoration/logout/expiry/reauthentication and route-specific invalid-session handling. Then run the real account-owned thread → message → completion → task events → persisted-output loop, documents/artifacts, resume, and revoked-session denial in Scout.

No authenticated live Scout behaviors were proven. All remaining requested remote-session tests and the full #815 live proof remain open. #816/#817 were not started. No issue was mutated, closed, or promoted. No new ADR is introduced by this client projection repair; existing Guardian authority and endpoint/auth separation remain governing.
