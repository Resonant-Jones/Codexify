# Scout remote-session progress and hosted qualification

Date: 2026-10-04 (America/New_York; historical checkpoints retain their original dates).
Status: hosted #815 continuity and revocation denial proven; see [the live closeout](SCOUT_LIVE_CONTINUITY_2026-10-04.md). Historical incomplete checkpoints below are superseded by that evidence. No release promotion or downstream task execution is implied.

## Lineage and scope

Starting branch: `feature/scout-ios-remote-session`.
Starting HEAD: `558438525dcaea4da48547218ce25913f73a2915`.
Starting working tree: clean. The tracked #822 checkpoint equals HEAD.
No local commits were discarded, rewritten, rebased, or replaced. No merge or push occurred.
Client repair commit: `b704291b3` (`Publish Scout persisted messages after task completion`).
The ending documentation commit is reported in the chat closeout.

The initial September 30 slice changes only the Scout client and its directly relevant documentation.
Guardian, frontend, Tailscale, Whoosh'd, providers, and database state were not modified. The separately approved Cloudflare Managed OAuth setting was applied on October 1, as recorded below.

## Authentication trace and evidence classes

**Native Access admission, October 2:** Operator-supplied Device Hub evidence at
16:51:45 UTC displays `Native request reached Guardian's account gate (HTTP 401,
Cloudflare Ray a4453689ff3df8ae-MIA)`. The installed classifier requires the
canonical Guardian account failure marker for this message. This qualifies the
simulator's native ingress admission, not a Guardian account session or protected
authenticated read. No further registration, BIC or Access policy work is needed
for this checkpoint. The serving account extractor was re-read at the pinned
`f83fe5da326871d1948ba79d90831be1402375ec` revision: Bearer precedes `gc_session`,
and no native account handoff exists. The concrete next contract/deployment
decision is in [the account handoff proposal](SCOUT_ACCOUNT_HANDOFF_DECISION.md).
It is not an approval or deployed implementation.

**Scout sign-in diagnostics, October 2:** Starting HEAD for this slice was
`b5cb07df6433274e51e768f93752807eedaf8cbc`; branch and #822 ancestry were
verified. Remote Server status no longer attempts to load a local API key.
Settings now offers a profile-scoped Keychain ingress check, with refresh using
the existing registered public client and fixed issuer/resource. No new client,
secret, access policy, or Guardian credential is introduced. Qualification checks
the canonical `X-Guardian-Auth-Failure: ACCOUNT_SESSION_INVALID` marker before
the edge challenge; status alone never establishes account authentication.

Complete SwiftPM suite: 41 tests, zero failures, using the task-local caches and
`--disable-sandbox` command documented below. Generic simulator build passed.
An unsigned installed bundle could not read Keychain. A second simulator build
using the existing development team (`DEVELOPMENT_TEAM=5Q888BY3YZ`, normal
signing enabled, destination the existing proof simulator) passed and was
installed without reset/uninstall. It launched with PID 87863. Device Hub then
showed `No ingress credential is stored for this connection`, rather than the
Keychain-read error. This proves Keychain-query access and missing credential
for the selected simulator profile; it does not identify why an earlier browser
sign-in did not retain a credential. The misleading API-key warning was visibly
absent in remote mode. The system-browser flow was reopened in this corrected
build and awaits the operator. Callback, refresh, native admission, Guardian
handoff, and the complete continuity loop remain unproven.

**Observed live, September 30:** Opening `https://preview.codexify.space` in the Codex browser redirects to the `resonant-constructs.cloudflareaccess.com` Access login. Its heading is `Log in to Codexify Private Preview`; Google and `Send login code` are offered. This establishes an Access application in front of the hostname, beyond ordinary Tunnel ingress. No credentials or codes were entered by the agent.

**Observed browser UI, October 1:** After the operator completed sign-in in Chrome, `/login` displayed `Your workspace is ready` and reported an active session. Continuing opened `/chat`; the sidebar displayed existing threads, and opening an existing thread rendered a four-message conversation. This proves an accessible browser workspace and rendered existing conversation, not a captured protected API response, deployed credential-purpose enforcement, native credential handoff, or Scout continuity. The agent did not inspect browser session storage, cookies, or tokens, and did not send a message or request inference. Serving Vault lineage was subsequently identified below.

**Credentialless ingress discovery, October 1:** Requests from the approved host lane with `Accept: application/json` to preview's `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server` returned HTTP 302 with a `Cloudflare-Access` challenge advertising a `resource_metadata` URL. Reading those exact advertised `/.well-known/cloudflare-access-protected-resource/...` URLs returned HTTP 200 JSON: `protected=true`, team domain `resonant-constructs.cloudflareaccess.com`, and the sole advertised authentication method `cloudflared`. No authorization or token endpoint was supplied by the preview resource metadata. The team domain's standard `/.well-known/oauth-authorization-server` returned issuer, authorization/token/revocation endpoints under that same team origin, authorization-code and refresh-token grants, unauthenticated public-client support (`none`), and PKCE `S256`. Team-wide OAuth capability does not prove that the preview application enables it or permits an iOS callback/client.

Cloudflare's [Managed OAuth documentation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/) describes an opt-in application setting, authorization-code discovery for non-browser clients, and allowed HTTPS redirect URIs. The observed 302 and `cloudflared` advertisement suggest the preview application has not exposed that managed flow; this is an inference awaiting control-plane inspection, not confirmed configuration. Any ingress token must remain distinct from Guardian's account token. No Access setting was changed or client registered.

**Read-only control-plane confirmation, October 1:** Following operator dashboard sign-in, the `Codexify Private Preview` self-hosted Access application was inspected. Its destination is `preview.codexify.space`, with no path restriction; one Allow policy is attached (`Allow exact private-preview operators`). Its login methods are Google and One-time PIN, application session duration is 24 hours, and Cloudflare One Client authentication is off. Cookie settings show HTTP Only on, binding cookie off, and SameSite Lax. Managed OAuth is **off**, confirming the earlier ingress inference. Its inactive options display localhost and loopback clients on, no listed allowed redirect URI, grant duration inherited from application session duration, and a default 15-minute access-token lifetime. The live dashboard explicitly permits exact custom-scheme redirect URIs, unlike the narrower redirect wording in the linked prose documentation. No policy rule identities, secrets, browser cookies, or credential values were copied; no setting was saved.

**Approved Access change applied, October 1:** After explicit operator approval, Managed OAuth was enabled for `Codexify Private Preview`. Reopening its settings confirmed the exact allowed redirect `ai.resonantconstructs.codexify.scout://access-callback`, localhost and loopback clients off, a 24-hour grant, and a 15-minute access token. Existing Google/One-time PIN methods and Allow policy remain configured. No native client has been registered; saved settings are not native admission proof.

**Native discovery blocker after saving:** Default Python HTTP requests from both the approved local host lane and VaultNode to preview's standard protected-resource and authorization-server metadata paths returned Cloudflare HTTP 403, Error 1010, `browser_signature_banned`, rather than OAuth metadata. The VaultNode observations were at `2026-10-01T20:54:39Z`, with Ray IDs `a43e5d1ddda55c03` and `a43e5d1e2af7df44`. Dashboard inspection confirmed Browser Integrity Check on for the domain. Automatic approval review rejected a proposed retry with a changed Scout user-agent as an attempt to evade the browser-signature restriction; no such retry occurred. No browser impersonation or indirect bypass was used.

**Prepared rule before deployment, October 1:** An unsaved configuration-rule form named `Scout native API and OAuth discovery` sets only Browser Integrity Check off for the following filter. It has not been deployed or saved. Cloudflare Access and Guardian authorization are not changed by this proposed rule, but it reduces a browser-header heuristic on these paths and requires separate explicit approval before deployment.

```text
(http.host eq "preview.codexify.space" and (starts_with(http.request.uri.path, "/api/") or http.request.uri.path eq "/.well-known/oauth-protected-resource" or http.request.uri.path eq "/.well-known/oauth-authorization-server" or starts_with(http.request.uri.path, "/.well-known/cloudflare-access-protected-resource/")))
```

**Approved scoped BIC exception deployed, October 2:** The operator approved BIC-only skipping on the exact filter above, with matching-request logging enabled and other protections retained. Chrome's restart cleared the unsaved configuration form. To meet the explicit logging requirement, the exception was deployed as a custom security rule with action `Skip`, rather than a configuration-setting override. Rule `57dd83039e3c40109a7daf4846f0bb0e`, named `Scout native API and OAuth discovery`, was reopened after deployment: Active, the exact hostname/path expression, Log matching requests on, Browser Integrity Check selected, and every other skip checkbox off. No remaining custom rules, managed rules, rate limiting, Super Bot Fight Mode, Zone Lockdown, User Agent Blocking, Hotlink Protection, or Security Level was skipped. No configuration override was saved. Neither Scout nor the default Python User-Agent was changed.

**Unchanged native discovery after deployment:** Credentialless requests using the same default Python HTTP stack and `Accept: application/json` reached successful discovery, rather than Error 1010. At `2026-10-02T12:51:31Z`, `/.well-known/oauth-protected-resource` returned HTTP 200 JSON, Ray `a443d6c8eabaa576-MIA`, resource `https://preview.codexify.space`, and authorization server `https://resonant-constructs.cloudflareaccess.com`. `/.well-known/oauth-authorization-server` returned HTTP 200 JSON, Ray `a443d6cbbd445d0c-MIA`, with the same issuer, code/refresh grants, public-client authentication method `none`, PKCE `S256`, and advertised `/cdn-cgi/access/oauth/authorization`, `/token`, `/revoke`, and `/registration` endpoints on that team origin. No cookies, tokens, or credentials were sent or recorded. This qualifies the BIC discovery blocker as resolved; it does not prove native admission or Guardian authentication.

**Access still enforced on the API:** At `2026-10-02T12:53:26Z`, credentialless `GET /api/chat/threads` using that same stack returned HTTP 401, Ray `a443d99b8b0bdfba-MIA`, server Cloudflare, and a Bearer OAuth challenge reporting missing/invalid Access token, with resource metadata at `/.well-known/cloudflare-access-protected-resource/api/chat/threads`. The next boundary is Cloudflare Access admission. Guardian authentication has not yet been reached by this request.

**Exact next external action:** Automatic approval review rejected a POST to the advertised registration endpoint because registering a public OAuth client is a separate persistent access change from enabling Managed OAuth. No registration request was executed and no client was created. The proposed request registers only `client_name=Codexify Scout`, the exact approved callback, `token_endpoint_auth_method=none`, `grant_types=[authorization_code, refresh_token]`, and `response_types=[code]`. Explicit operator approval for that registration is pending. Registration grants no account session and does not relax Access policy. After approval, register the public client and continue the system-browser PKCE flow; all Access admission, Guardian handoff, client implementation, and live continuity proof remain open.

**Single public client registration approved and completed, October 2:** The operator explicitly approved the registration POST and minimum configuration for one native/public Scout iOS client, no secret, the existing exact callback, and PKCE authorization. The advertised team registration endpoint returned HTTP 201 at `2026-10-02T13:56:04Z`, Ray `a44435558d09a4d0-MIA`. Returned public metadata: client ID `53bc5fc5-aba1-4b4e-8541-30772ce12c20`, name `Codexify Scout iOS`, callback `ai.resonantconstructs.codexify.scout://access-callback`, grants authorization-code/refresh, response code, token endpoint authentication `none`. No client secret or registration access token was returned. Only one registration POST was executed. No additional client, policy, or identity mapping was created.

**Native ingress implementation slice:** Scout now has an ASWebAuthenticationSession flow using that public client. It generates fresh cryptographic state/verifier and requires PKCE S256, validates the exact callback and a single matching state/code, consumes each attempt once, and exchanges the code through the fixed discovered team token endpoint. It never prints callback/code/token material. Ingress credentials are stored only in a separate Keychain service, scoped by profile UUID and canonical HTTPS origin, with WhenUnlockedThisDeviceOnly accessibility and synchronization off. Token exchange, ingress qualification and revocation use ephemeral URLSession without cookie or credential storage; all redirects are refused. A profile change cancels/supersedes an in-flight sign-in. Only the explicitly configured hosted remote-session profile may use this client; personal nodes are not silently redirected to hosted ingress.

Settings exposes `Use hosted Codexify`, `Authorize hosted ingress`, and `Revoke hosted ingress` under remote mode. The saved connection identity must match the draft before authorization can start. This is ingress setup, not Guardian account login: the shared #822 remote request policy continues failing before dispatch until an actual Guardian session exists, and no API key is mixed or substituted. The post-exchange read displays HTTP status and a bounded non-secret Cloudflare Ray ID, distinguishes an Access metadata challenge, and does not label other statuses as authenticated Guardian identity. Revocation is claimed only after a successful revocation response; failed revocation preserves the stored credential for retry. Refresh/restoration and Guardian session lifecycle remain unfinished.

**Validation and exact human boundary for this slice:** Complete SwiftPM suite passed 35 tests with zero failures (eight additional OAuth tests). Tests cover RFC PKCE challenge generation, resource/callback binding, state mismatch/duplicate/error/replay rejection, profile/origin scoping, unsupported/wrong-origin URLs, token response validation, continued #822 fail-closed behavior, and redirect refusal. The canonical simulator Xcode project build succeeded. The dedicated `077E052A-54E0-41F5-BF47-F7BAED94599C` simulator booted; the build installed and launched (PID `61193` for the initial slice; final diagnostic build relaunched as PID `62150`). Simulator UI binding was unavailable through both bundle ID and full application path. A Finder navigation attempt did not locate a usable Simulator window. No callback, token exchange, Access-admitted native request, Guardian account session, or native continuity is claimed as live proof. The operator must complete the intended browser sign-in in the installed app; credentials/codes must stay in that UI.

**Physical iPhone installation, October 2:** The operator reported that simulator OAuth approval could not complete the phone/Bluetooth step and explicitly requested installation on the USB-connected iPhone. Xcode identified ScoutNode as an iPhone 16 Pro; Scout was not previously installed. The unchanged client at `7bc556b492261a69b2a0d408ad2c037e2a40588a` built successfully for the connected device using automatic development signing, a command-line team override, and `-allowProvisioningUpdates`. Xcode obtained the development profile for the existing Scout bundle identifier; no project signing settings were edited. DerivedData was isolated at `/tmp/scout-iphone-derived-data`. `xcrun devicectl device install app` succeeded for `ai.resonantconstructs.codexify.scout`; `device process launch` also succeeded. No credentials or session material were collected. Build/install/launch qualify device deployment only. Interactive native sign-in is now pending on the physical phone; callback, token exchange, Access admission, Guardian account-session handoff, and live continuity remain unproven.

**Runtime qualification and unavailable origin, October 2 at 15:02 UTC:** Device Hub now exposes the dedicated simulator's Scout accessibility tree. Its current Settings status is `System-browser authorization did not finish. Retry sign-in; no Guardian account session was created.` The operator separately reported `http 530 no session was issued`, without a device or Ray ID. In the current client, a protected-probe HTTP status is displayed only after callback validation, HTTP-200 PKCE exchange, credential validation, and Keychain storage; the operator report therefore supports that sequence on the reporting device, but is not direct callback/Access/Guardian proof. The conflicting device observations remain unresolved; no credential was extracted.

A fresh credentialless `/api/chat/threads` read returned Cloudflare HTTP 401 with its missing/invalid Access-token challenge, Ray `a44495f2eb6d7088-MIA`; discovery returned 200, Ray `a44495f34982afde-MIA`. These are edge checks, not authenticated origin reads. Read-only SSH inspection of VaultNode at `2026-10-02T15:02:20Z` found Docker context `desktop-linux`, zero running or stopped containers, and an empty Compose project list. The original serving tree remains at `f83fe5da326871d1948ba79d90831be1402375ec`. The lifecycle desired-up marker is absent, the existing preview env file is present (contents not read), and preserved volumes `codexify_private_preview_chroma` and `codexify_private_preview_pg_data` are listed. Loopback `/health` on port 8081 cannot connect (HTTP 000). The deployment is explicitly disabled; it was not restarted or reconstructed. Operator authorization to restore the existing deployment is requested, with a stop before migration or additional identity/access changes. Cloudflare HTTP 530 alone does not identify the exact origin error, and native Access admission remains unqualified.

**Recovery preflight, October 2 at 15:04 UTC:** A second read-only VaultNode check confirmed the same disabled marker, empty container inventory, and unreachable loopback origin. The existing two-file private-preview Compose configuration passes `config --quiet`; configuration values and credentials were not printed. The canonical lifecycle `up` command invokes Compose startup, whose `migrator` runs `alembic upgrade heads` and `seed_defaults.py`. Therefore ordinary full startup is not authorized by restoration approval that excludes migrations. The next recovery gate is operator-approved database-only startup against the preserved PostgreSQL volume, followed by read-only comparison of stored Alembic revision(s) with the serving source/image revisions. Do not run a migration or suppress the startup migration gate to obtain a green application. No recovery mutation, new identity/access configuration, or migration was executed in this preflight.

**Approved bounded database restoration, October 2:** The operator authorized overriding the disabled preview state only for preserved-database startup, read-only schema/runtime inspection, and conditional minimum application restoration without migration/seeding. Before startup, an ephemeral read-only, network-disabled PostgreSQL 15 container verified `PG_VERSION=15` and a nonempty `global/pg_control` on the existing `codexify_private_preview_pg_data` volume. A delayed image inventory completed with PostgreSQL 15 present; earlier claims that all images were absent were incomplete observations. Public pull attempts failed at the SSH registry Keychain boundary and did not replace an image; no credential or Keychain change was made.

The existing Compose database service started with `--no-deps --no-build --pull never`, a task-local override declaring the existing volume external, direct `postgres` entrypoint under the `postgres` user (no initdb/bootstrap entrypoint), and `default_transaction_read_only=on`. The full-preview enabled marker remains absent. The inspected container is running/healthy, restart count zero, and mounts the preserved volume at `/var/lib/postgresql/data`. Read-only SQL reports stored Alembic revision `c9f3e2a7b601`, 121 public tables, and the expected users/projects/thread/message/document/outbox tables. This is schema evidence, not authenticated Scout or record-content proof.

The intended serving source remains `f83fe5da326871d1948ba79d90831be1402375ec`; static migration-graph inspection finds one head, `a7b9c4d2e6f1`, directly descending from the stored revision. The stored revision was introduced in source commit `4106053b96e3080ba296b54a7da60cf61eb20b8e`; a database revision alone does not identify the exact previously running application commit. Read-only catalog checks confirm both new coding-credential tables are absent and the stored revision remains unchanged. The missing backend image is `codexify-backend-runtime:latest`, so restoring that intended source also requires an image build. No build was executed.

The pending migration `a7b9c4d2e6f1_add_coding_execution_credentials.py` creates `coding_execution_credentials` and `coding_execution_credential_leases`, with constraints and indexes; it does not provision an actual credential. Its downgrade drops those tables/indexes and would lose rows subsequently written there. Canonical startup runs `alembic upgrade heads` followed by `seed_defaults.py`; backend startup independently runs that seeder, and Guardian lifespan also seeds global system documents in the vector store. The default-project seeder may create/promote account defaults. Thus mutation-free restoration of this intended runtime is not qualified. No migration, seed, image build, application stack, or ingress/access change was executed. The new operator decision must separately address the pinned backend build, the single migration and backup/rollback gate, and startup seed mutations, or authorize qualification of a schema-compatible non-seeding recovery path. Scout #815 remains incomplete.

**Backup-first forward recovery and observed concurrent restoration, October 2:** The operator approved a verified backup, pinned runtime build, the single forward migration, and only qualified idempotent seeding. This chat created `/Volumes/Dev_SSD/Codexify-private-preview-backups/scout815-20261002-forward-recovery` outside Git, directory mode 0700/files 0600, containing a custom-format database archive, cluster-role backup, and non-content table fingerprints. Verification completed at `2026-10-02T15:30:54Z`: restore into a network-disabled disposable tmpfs PostgreSQL container succeeded; all 121 public-table row counts/content fingerprints and Alembic revision matched; the source remained unchanged after backup. The verification copy was stopped and was never substituted for production. Archive size is 2,156,911 bytes, SHA-256 `c23b76aa77a550f5b506b545cd9c81d8dae668109baf2217011902b03eaa2d5f`; the role backup SHA-256 is `1b85a961e30164e56b6daf0f87731eafa5fc9f732b385cde4ed6ba51d87346f3`. Backup contents, roles/passwords, and record content were not printed or copied into this repository.

The pinned image-build attempt used tracked files from `f83fe5da326871d1948ba79d90831be1402375ec` as its build context, excluding untracked runtime secrets. An initial archive attempt lacked git-lfs in its task PATH; the corrected attempt reached dependency installation. While that build was still live, current Docker state changed outside this chat's actions: the full preview services appeared, the source remained clean at the intended revision, the enabled marker became present, and the database advanced to `a7b9c4d2e6f1`. This chat interrupted its own duplicate build (exit 130) to avoid retagging over the active runtime. No migration or seed was executed by this chat. The observed running image is `sha256:0f842ac1f9f8fec04af74b253f831aeb872644cbfbb58b839fd25eea37756649`. Its origin/build attribution was not inferred from its `latest` tag.

Read-only validation of that image with startup overridden and network disabled reports migration head `a7b9c4d2e6f1`. Hashes of its target migration, ORM models, project seeder, backend startup script, Guardian auth routes, and auth dependencies match the corresponding clean pinned source files. The restored database reports that head and both new coding-credential tables. Fingerprints of every pre-existing table match the verified backup except `alembic_version`, the expected changed revision row. This is preservation evidence for all baseline public-table contents, not an attribution claim about the other recovery actor's commands or a new production rollback test.

Project seed preflight reports six canonical accounts, six existing structural General projects, zero promotions/creations, and zero duplicate conflicts; the seeder's existing-General branch preserves those rows. Source inspection identifies global system-document seeding as a projection into stable `system-doc:` vector ids under `system_docs:global`, rather than canonical SQL content replacement. Actual seed invocation by the concurrent recovery was not observed by this chat. The existing Tunnel LaunchAgent is loaded/running; no Tunnel/Access/BIC/OAuth configuration was changed here. Loopback `/health` returns 200 and anonymous `/api/chat/threads` returns Guardian JSON 401. An initial bounded health read timed out, then the repeated read succeeded. Hosted credentialless `/api/chat/threads` still returns Cloudflare OAuth-challenge 401, Ray `a444d1ff8b67de30-MIA`, preserving ingress enforcement.

The origin recovery prerequisite is now supported by current runtime evidence. Operator retry of native `Authorize hosted ingress` is pending to replace the prior 530 with an attributable native callback/exchange/API result. No authenticated native Access admission, Guardian account-session handoff, protected account read, or #815 continuity loop is claimed yet. The existing registered client and PKCE implementation were not repeated or changed.

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

The source trace establishes two authentication boundaries. It does not establish that current VaultNode serves the inspected main commit or that every deployed validator enforces ADR-092. Access application settings were subsequently inspected above; live native admission, renewal, and logout remain unproven.

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

Before a hosted native implementation can be qualified, establish the operator-approved Access admission mechanism for native API requests and the canonical Guardian browser-to-native handoff. Managed OAuth is now enabled with the approved exact callback and lifetimes above. The approved logged BIC-only rule is deployed, and unchanged native discovery now returns HTTP 200. The account-owned API still requires Cloudflare Access admission. The separately approved public PKCE client is now registered and its native ingress flow implemented. Interactive sign-in on the installed physical iPhone is the exact pending human action. Continue Managed OAuth/system-browser qualification afterward and establish ingress credential presentation compatible with Guardian account authentication. If implementation requires a new ownership/authorization decision or weakening Access, stop for that decision instead of changing Guardian opportunistically. Do not distribute a shared service token or copy browser cookies/tokens through chat or terminal.

Once those prerequisites are established, resume `remoteSession`, Keychain-only per-profile credential isolation, hosted/personal profile UI, restoration/logout/expiry/reauthentication and route-specific invalid-session handling. Then run the real account-owned thread → message → completion → task events → persisted-output loop, documents/artifacts, resume, and revoked-session denial in Scout.

No authenticated live Scout behaviors were proven. The new ingress tests do not establish a Guardian remote session. Account-session lifecycle tests and the full #815 live proof remain open. #816/#817 were not started. No issue was mutated, closed, or promoted. No new ADR is introduced by this client projection repair; existing Guardian authority and endpoint/auth separation remain governing.


## October 2: canonical account handoff implementation checkpoint

The operator approved the alternate hosted account header only as transport of
Guardian's existing canonical account session, with no new credential authority.
The backend patch is isolated from the older Scout issuer in a worktree based on
serving revision f83fe5da326871d1948ba79d90831be1402375ec. It has not yet been deployed.

Scout now implements browser handoff, profile/origin-scoped account restoration,
protected thread qualification, explicit logout, typed expiry/invalid-session
handling and the shared hosted/personal credential selector. Local API keys also
use profile/origin slots; legacy global material is preserved without adoption.
All credential-bearing shared services reject redirects and clear account state
only on the canonical invalid-account marker. Account changes reset volatile views.

Validation: the complete SwiftPM suite passes 50 tests; the canonical signed
simulator Xcode project builds successfully in the host lane with isolated /tmp
caches and -disable-sandbox. The managed build cannot reach CoreSimulator, so that
attempt does not establish build or launch proof. The new signed build is not yet
installed. Backend handoff/transport/app-mount/strict-purpose/operator tests passed 57
tests after aligning core dependencies with the serving image. Frontend login tests passed 13 tests
and Vite build passed. These are source/test/build layers, not live account proof.

The previously observed native ingress admission remains the current live
checkpoint. Guardian handoff, protected read, complete continuity and logout denial
must still be executed through the actual app before #815 can close.


## October 2: bounded auth deployment and native launch

Backend Git revision: 465497b0c.
Scout Git revision: 899ad8ff2.
Both were committed separately without merge, rebase or push.

The preview patch image was built on the exact already qualified base image
sha256:0f842ac1f9f8fec04af74b253f831aeb872644cbfbb58b839fd25eea37756649.
Serving patch image:
sha256:c85760cf456e9a09a12983642a1fd6f4f1817903acb86ea3b3791134a84673d5.
Hash and Python syntax qualification ran in an isolated image container with no
network, production mounts, application lifespan or database startup. Compose
configuration validation passed without printing environment values.

Only preview backend/frontend were recreated with --no-deps --no-build --pull
never. Reviewed auth files are read-only specific-file mounts; the main checkout,
workers and concurrent codexify_chat_proof_f091_20261002 stack were preserved.
The frontend override was corrected to use its existing shell entrypoint after
an initial duplicate-shell command exited without serving. The corrected frontend
serves /login. Preview origin is 127.0.0.1:8081: /health and /login return 200;
unadmitted /api/auth/scout/exchange returns 401. Serving Guardian and LoginPage
hashes match the committed patch. DB remains at a7b9c4d2e6f1; this deployment ran
no migration, database reset or replacement operation. No Access/OAuth/BIC change.

The signed Scout build was installed on the existing proof simulator with data
and Keychain preserved, then launched (PID 3678). Device Hub displays the new
account-session-required message. These are deployment/launch checks, not an
account-authenticated read. Device Hub inspection works but input attempts return
noWindowsAvailable. The operator has been asked to use Settings → Check stored
ingress → Sign in to Guardian and confirm Continue to Scout in the existing web
account flow. Guardian handoff and the full #815 loop remain unproven pending that
secure UI action. No credential values were captured.


## October 2: independent native session amendment, deployment held

The operator amended the handoff to require a fresh exact-purpose account_session
for the same canonical User.id, with independent nonce/expiry/store/revocation.
The separately reviewed backend source now implements this; the browser's token
is retained only server-side for one-time grant revalidation and is not returned
to Scout. Origin is checked in atomic grant consumption. The alternate account
transport invokes the existing strict validator before every scoped handler,
including logout. Conflicting account transports fail closed without fallback.

68 backend tests and 13 login-page tests pass; Vite build passes. Native response
fields and the Swift credential class are unchanged. Revised deployment has not
run: the current entrypoint and lifespan unconditionally execute seed/bootstrap
operations, and no existing no-seed startup switch was found. The amended approval
forbids seeding. A concrete bounded startup-guard proposal is required before
restarting. No new seed/migration or external access change ran for this amendment.
The currently served first patch still follows the earlier token-transfer design;
hold account sign-in until the amended independent-session revision is deployed.
The full authenticated #815 loop remains unproven, and #816–#818 remain downstream.

## October 2: approved no-seed deployment verified

The startup guard was separately approved, implemented and tested. Source commits
6c6adaa74 and dcd8c2b73 retain default behavior when the flag is absent and suppress
only the seven identified seed/bootstrap/replay hooks when enabled. The latter
uses a static marker that survives safe logging. The integrated backend suite
passes 70 tests and guarded original-source rollback passes both modes. Prior
frontend qualification remains 13 tests/build; Swift bytes did not change.

The independent native-session amendment is now deployed. Preview serves image
sha256:f9e7f5ff1e69d03a4f626bdbf99ff6ba032687f7f374517ed1f05a565a99a158
from dcd8c2b7347632dc196f2181094bc4a1425c4785 on the qualified pinned base.
Only preview backend/frontend were recreated. The approved direct Uvicorn command
and CODEXIFY_SKIP_STARTUP_SEEDING=1 are active; the suppression receipt appears
once. Reviewed Guardian/LoginPage bytes match the serving mounts. Origin health
and login return 200, anonymous thread reads and unadmitted exchange return 401.

Preserved schema remains a7b9c4d2e6f1. Before/after schema fingerprint, all ten
recorded table counts/row fingerprints and preserved service identities/configs
are unchanged, including existing workers and the separate chat-proof stack.
No migration, seed, import replay, database replacement or external access change
ran. Rollback retains the pinned prior image and original API source with the same
tested no-seed guard/direct command for this qualification window.

Device Hub displays “Sign in to Guardian for this connection. No account session
is stored; no request was sent.” Its coordinate input still reports
noWindowsAvailable. The operator is asked to open Settings in the existing proof
simulator, complete Sign in to Guardian / Continue in Scout, and report only the
resulting status. Ingress may be renewed through its existing authorization flow
if expired. Independent native session issuance, protected authenticated read,
logout/revocation denial and full continuity still require live app proof.
#815 cannot close yet; #816–#818 remain deferred.

## October 3 — bounded authentication qualification

Settings now shows nine safe stages for one connection-scoped sign-in attempt:
ingress availability, browser launch, Guardian account confirmation, callback
receipt, state validation, exchange acceptance, independent native issuance,
Keychain save/readback for the correct profile/origin, and a protected account
thread read. A public random attempt UUID correlates native/browser/backend
observations without exporting state, code, verifier, cookies or session bytes.
First observed failure and first unqualified stage remain distinct. Missing
runtime evidence does not declare authentication failure. Profile changes clear
the receipt; checking an older session cannot qualify a new attempt's issuance.

The bounded backend receipt is process-local, capped at 128 attempts with a fixed
ten-minute lifetime, hosted-admission gated and devoid of account identity.
Canonical validators confirm browser account authority. Scout automatically
checks the native account-owned read after verified issuance and Keychain
readback. The backend work remains independently reviewable on
`codex/scout-account-handoff-815`; its contract is
`docs/Ops/scout-auth-qualification-2026-10-03.md` in that checkout.

This instrumentation changes no account provisioning, password, role, approval,
database schema/data, Cloudflare policy, BIC or OAuth registration. Canonical
Guardian authority, personal Bearer sessions, local API-key mode, profile/origin
isolation and the no-fallback boundary are retained. Authenticated native proof
and the complete #815 continuity/logout loop still require live qualification.

Source qualification for this slice: **57 SwiftPM tests pass**, canonical signed
proof-simulator **BUILD SUCCEEDED**, **78 integrated backend tests pass**, and
**16 LoginPage tests plus Vite build pass**. The managed-shell simulator build
failed to connect to CoreSimulator; the same canonical project built in the
host lane. The existing origin proxy also needs a bounded query/referrer-free
logging override before sign-in because its default logs include the request
URI. Routing and ingress/access policy remain unchanged. Installation/deployment
and operator-authenticated continuity are separate remaining proof gates.

The authentication qualification source is committed as `3f6d1cdcd`; its signed
build is installed and launched in the existing proof Simulator, preserving app
configuration and Keychain. Device Hub Settings exposes all nine stage rows,
initially Waiting/pending. The corresponding backend/browser slice `f231ef3cf`
is deployed on VaultNode with the bounded safe origin logger. Serving bytes,
health, no-seed posture, anonymous denial and synthetic query redaction are
verified. Schema and ten preserved table fingerprints match before/after;
eighteen other services are unchanged. The operator was asked for one Guardian
sign-in. Protected native read, full #815 continuity and logout are still pending.
No account provisioning, password, role, approval or Cloudflare change occurred.

The first native qualification stopped before browser launch because the stored
ingress grant had expired. A generic catch incorrectly replaced the specific
availability result with `transportFailure`. Scout now distinguishes missing and
expired credentials, classifies Keychain read failure separately, and preserves
the first observed failure until an actual successful recovery. Two additional
tests cover the expiry boundary and failure/recovery evidence: **59 SwiftPM tests
pass**, and the canonical signed simulator **BUILD SUCCEEDED**. No backend or
authentication authority changes are needed for this diagnostic correction.

The existing Check stored ingress action renewed the stored grant and reached
Guardian's account gate (HTTP 401, Cloudflare Ray `a44fd999ca5b67cf-MIA`). This
qualifies renewed Access admission only. Guardian sign-in, fresh native issuance,
protected account read, continuity and logout remain pending.

The subsequent guarded pre-browser request passed ingress availability but
returned HTTP 400. Scout's bounded allowlist maps only fixed server messages;
the live result is `nativeAdmissionRejected`. A corresponding backend-only
response header distinguishes missing/ambiguous/unsupported Authorization from
conflicting selectors without exposing values or changing admission checks.
Scout accepts only those fixed enum values, never arbitrary response text.
The complete client suite passes **61 tests**; the backend integration suite
passes **83 tests**. No new sign-in submission occurred during these preflights.

The final signed client build is installed and launched in the existing proof
Simulator. Public attempt `f559214a-652f-4557-ad99-d6d5f8f5bae7` passed stage 1
but stopped before browser launch at stage 2: `nativeAuthorizationMissing`,
HTTP 400. The deployed backend diagnostic confirms its existing signed Access
checks passed and no Authorization header reached Guardian. Scout supplies that
header; the observation does not identify the individual upstream remover.
ADR-092's current opaque-Bearer requirement correctly fails closed. A bounded
transport amendment is prepared in the backend checkout's
`docs/Ops/scout-edge-consumed-access-proposal-2026-10-03.md`; it awaits separate
approval and is not implemented. Current canonical account authority is unchanged.
Authenticated native read, complete #815 continuity and logout remain unproven.

## October 4 — approved edge-consumed Access composition

The operator approved the ADR-092 hosted transport amendment. Guardian recognizes
absent origin Authorization only after mandatory signed Access admission at the
independently qualified exact-host/private-preview composition. Any forwarded
Authorization remains single opaque Access Bearer. This does not infer trust from
absence or move Access credential bytes to another header. Canonical account
session validation remains independent; no identity or credential class changes.

Settings now reports “Access admitted / Authorization edge-consumed” from the
fixed server observation after a successful, exact-origin/path/attempt receipt.
The missing-header failure remains valid for historical pre-amendment evidence.
Personal-node Bearer behavior, profile isolation and explicit local mode remain
unchanged. The backend work/ADR remain separately reviewable in the attached
account-handoff checkout. **62 SwiftPM tests, 100 backend tests, 16 browser tests,
Vite build and signed Simulator build pass**. Live deployment/install/sign-in,
protected read and complete continuity/logout remain separate proof gates.

The approved implementation is committed as client `ae6855b721dbbe0f0fff6148285a9a7bcd1d7341`
and separately reviewable backend/ADR `5836ed986e4cc6175b5184fe6b5d2fb23a989ed1`.
The backend amendment is deployed on VaultNode as two read-only source overlays
at both package locations, retaining the existing image, direct Uvicorn command,
disabled startup seeding and safe origin logging. Runtime hashes match; health
is 200 and anonymous account read is 401. Schema and all ten preserved table
fingerprints are unchanged; all 29 other running services are unchanged.
No Cloudflare, account, database or migration operation ran.

The signed client update is installed and launched in the same proof Simulator,
preserving its profile and Keychain. Device Hub displays the updated app but
coordinate input returns `noWindowsAvailable`; the operator has been asked to
check stored ingress, perform one Guardian sign-in and return to Scout.
Installation/deployment do not establish account issuance, protected read or
the full #815 loop. Current source inspection confirms successful terminal
completion assigns persisted messages to observable conversation state and
guards selection/connection/revision; its live behavior remains to be proven.
#816–#818 remain deferred.

## October 4 — authenticated continuity and revocation proof

Public attempt `d0d1f7bd-7ba3-4710-9b0a-49ccad8a4938` passed all nine native
authentication stages and a decoded protected account thread read. The operator
corroborated all nine stages. The fixed admitted state is Access admitted /
Authorization edge-consumed; Guardian account authority remains independent.
The bounded runtime receipt expired, so a complete correlated backend trail is
not claimed. Native callback/exchange/issuance/Keychain/read evidence is retained.

The real app loaded existing threads/messages, created and renamed proof thread
76, sent two synthetic user messages through distinct Send/Request actions,
observed accepted tasks and successful task streams, and actually displayed both
persisted Guardian replies. Read-only SQL confirms messages 911–914 and both
request/task/turn bindings. Foreground/resume preserved the selected thread;
protected document inventory and an account-owned document's metadata/content
loaded. Canonical logout returned 200, its in-memory protected replay returned
401, and a subsequent local account check failed before dispatch with no stored
session. No credentials or existing document content were captured.

Latest client corrections report Stream ended honestly (`716b405dd`), qualify
post-logout denial without requiring an unrelated general invalidation marker
(`5c9ad3cba`, `dad8a4803`), and distinguish captured ingress expiry during a long
browser handoff (`fab00177b`). The complete SwiftPM suite now passes **66 tests**;
the canonical signed proof-Simulator build/install/launch passes. Existing backend
**100 tests**, LoginPage **16 tests** and Vite build remain qualified; their bytes
did not change in the latest Swift-only corrections.

The [live proof packet](SCOUT_LIVE_CONTINUITY_2026-10-04.md) records exact source
revisions, all 18 #815 steps, preserved data/runtime evidence and remaining proof
limits. Final corrected logout UI verification awaits Mac unlock. Personal-node
isolation and failed/cancelled behavior are unit-tested, not newly forced live.
No Beta, TestFlight, App Store or final physical-device continuity is claimed.
