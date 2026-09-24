# Account activation and invitation terrain

**Inspection date:** 2026-09-17
**Execution lane:** Architecture-Impact
**Mutation posture:** Documentation-only inspection. This report records repository and bounded runtime evidence; it changes no runtime contract.

## 1. Baseline and evidence boundary

The repository was inspected at the actual local working tree, not published GitHub state.

| Git fact | Observed value |
|---|---|
| git status --short | D docs/DEV_LOG/2026-09-17/Dev Log - 2026-09-17.md; M frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx; M frontend/src/components/persona/layout/__tests__/GuardianChatWithSidebar.stability.test.tsx; M frontend/src/features/chat/GuardianChat.tsx; M frontend/src/features/chat/__tests__/GuardianChat.session-shortcuts.test.tsx |
| branch | main |
| HEAD | 7b8af61e6e2312b6853a6ac5666e7ffc070337c9 |
| origin/main | 4a09140b98858630088265912528698166b0cec6 |
| merge-base | 4a09140b98858630088265912528698166b0cec6 |

Local main is three commits ahead of origin/main (`7b8af61e6`, `b5561c492`, `a072634fb`) and is not behind it. The current-state document had previously reported two commits ahead; that statement is stale relative to this inspected baseline. Working-tree dirty files are unrelated to this task and were preserved.

An earlier inspection of the same path (`docs/architecture/inspections/2026-09-17-account-activation-invitation-terrain.md`, written earlier today) is fully replaced by this document. That earlier draft concluded `REQUIRES_MULTI_SLICE_FOUNDATION` before the activation subsystem had landed in the working tree. Since then the activation domain (model, migration, service, redemption route, dedicated UI page, and operator CLI) has been implemented in this checkout; this report is the first inspection to record that fact and to revise the viability classification accordingly.

Evidence was limited to repository files, migrations, tests, non-secret configuration key names, and git history. No container, account, database, mailbox, credential, provider, environment, or external Google configuration was accessed or modified.

The repository's documented documentation validation target is `make docs` (Makefile). It was run after drafting. The python scripts it depends on were not invokable from this environment (`python` not on PATH), so validators exited without producing their checks; this is an environmental validation failure, not runtime proof, and was not repaired in this documentation-only task.

Relevant additional paths include `guardian/guardian_api.py`, `guardian/server/codexify_api.py`, `guardian/connectors/gsuite.py`, `guardian/integrations/google_drive.py`, `guardian/cli/tester_account_activation.py`, `guardian/account_activation/{tokens,service}.py`, `backend/alembic.ini`, `docker-compose.tester.yml`, `docker-compose.private-preview.yml`, `.env.example`, `.env.tester.example`, and `config/supported_profiles/v1-friends-family-web.yaml`.

## 2. Current runtime/profile topology

The supported reality remains local Docker Compose core operation with local provider policy; the friends-and-family/private-preview lane is a separately gated overlay, not a release proof.

| Surface | Documented project / profile | Provisioning tool | Activation tool | Evidence |
|---|---|---|---|---|
| Older private preview | `codexify_private_preview`; `v1-whooshd-deepseek-web` | `guardian.cli.private_preview_provision` | (none — operator supplies password via getpass) | `docs/Ops/private-browser-preview.md`, `docker-compose.private-preview.yml` |
| Stabilized tester / friends-and-family | `codexify_tester`; `v1-friends-family-web` | `guardian.cli.tester_account_provision` | `guardian.cli.tester_account_activation` (issue/revoke) | `docs/Ops/friends-family-tester-runtime.md`, `docker-compose.tester.yml`, `config/supported_profiles/v1-friends-family-web.yaml` |

`docker-compose.tester.yml` declares `CODEXIFY_SUPPORTED_PROFILE=${CODEXIFY_SUPPORTED_PROFILE:-v1-friends-family-web}` and gates the `auth`, `hosted_rooms`, `hosted_room_guest`, `direct_messages`, and `share` route posture. It does NOT load the `user_profile` route group (which carries the frontend `/profile` surface), `collaboration`, `connectors`, or `google_connect`. The tester runbook names the tester provisioner as the operator boundary for creating accounts.

The friends-and-family profile is the only one that simultaneously enables the `auth` route group (which now contains the activation redeem path) and supports a built-in operator CLI for issuance. The runtime proof of which profile is actually deployed is **RUNTIME_UNVERIFIED** from this environment (no Docker socket available), but the configuration surfaces are consistent: the friends-and-family tester profile is the documented and default deployment for the account-activation flow.

## 3. Canonical auth/account model

Guardian is the canonical account, credential, session, and role authority. ADR-005 requires explicit account identity in multi-user mode and makes runtime mode bootstrap/configuration rather than account authority (`docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md`). The remote-account/profile contract assigns canonical identity and session authority to Guardian (`docs/architecture/remote-account-access-and-user-profile-contract.md`).

Canonical `User` table — `guardian/db/models.py`:

| Property | Current implementation |
|---|---|
| id | required string primary key |
| username | required unique string |
| email | nullable unique string |
| password_hash | required non-null string (bcrypt) |
| role | required `admin` or `guest`, default `guest` |
| lifecycle state | absent: no `pending`, `active`, `disabled`, `activation`, or credential-version field |
| is_active flag | absent on `users`; `is_active` exists on several derived tables but is not a User lifecycle column |

Supported login identifiers are username, or a normalized `User.email` when the input contains an `@`. Password verification is bcrypt via `guardian/core/passwords.py`. The legacy `guardian/Users/users.py` SQLite/plain-password shape is not imported by the Guardian route path and must not be revived as identity authority.

`register_user` (`POST /auth/register`, `guardian/routes/auth.py`) creates the User from a chosen username and password and runs the account-observability attribution side-effect. In private-preview exposure it returns `404 Not Found` (preview users are provisioned, not self-registered). `login_user` resolves by username or email, issues a session via `issue_session_token` + `session_store.store`, and stores the token in Redis at `session:<token>` with TTL `DEFAULT_SESSION_TTL_SECONDS` (24h). `logout_user` revokes only the presented session token.

`activate_user` (`POST /auth/activate`, `guardian/routes/auth.py`) is the redemption endpoint for the new activation capability. Its request model is `AuthActivateRequest{token, password}` with `model_config = ConfigDict(extra="forbid")`. Successful redemption creates the User with `id == username == email == recipient_email`, bcrypts the recipient-supplied password, and returns `{ok, user_id, username}` without issuing a session — the recipient still authenticates through `/auth/login` (this is intentional and matches the UI: `ActivateAccountPage` links to `/login` after success).

## 4. Operator provisioning paths

Two CLI provisioners exist; both predate the activation flow and remain the operator password-custody boundary for environments that have not yet moved to activation issuance.

| Tool | Intended runtime | Gates / role | Account / reset behavior | Password custody | Current posture |
|---|---|---|---|---|---|
| `guardian.cli.private_preview_provision` | older `codexify_private_preview` | requires private-preview exposure; allowlisted normalized email determines permitted role | creates email-as-id User, or overwrites hash and role of existing User | `getpass` entry and confirmation; operator supplies durable password | legacy/superseded for stabilized tester; still a distinct documented private-preview path |
| `guardian.cli.tester_account_provision` | stabilized `codexify_tester` / friends-and-family | requires `v1-friends-family-web` and `remote/local_safe` posture; role is `admin` or `guest` | creates email-as-id User, or overwrites hash and role of existing User | `getpass` entry and confirmation; operator supplies durable password | intended current tester tool; live deployment remains `RUNTIME_UNVERIFIED` |
| `guardian.cli.tester_account_activation` | same as above | gated by `runtime_posture_error()` from `tester_account_provision` | does NOT create a User at issuance; creates a `AccountActivationCapability` and prints the activation URL once | operator has no durable recipient password; recipient chooses password at redemption | intended current activation tool; redemption path is wired end-to-end; issuance path requires operator-side trust (no automated delivery) |

Both older provisioners reset an existing account credential as part of reprovisioning. They predate the activation capability and should be treated as the operator fallback path for environments where activation is not yet enabled.

The activation issuance CLI (`guardian/cli/tester_account_activation.py`) is fully implemented:
- `issue --email --role --actor-user-id --base-url --expires-in-hours` → calls `issue_activation`, prints `Activation ID`, `Expires at`, and `Activation URL` once.
- `revoke --activation-id --actor-user-id` → calls `revoke_activation`, prints `Revoked activation` and `Revoked at`.
- Activation URL is `{base_url}/activate#token={raw_token}` — the raw bearer is transported in a URL fragment so the server never logs it.
- Posture gate (`runtime_posture_error`) rejects non-tester profiles; this is the only existing runtime guard against accidental issuance in the wrong environment.

## 5. Invite-system inventory

The repository contains distinct invitation domains; they must not be conflated.

| Domain | Runtime state | Authority granted | Relationship to account activation |
|---|---|---|---|
| Account activation capability | **CURRENT — wired this morning** | creates canonical User with recipient-chosen password on redemption | **this is the activation flow itself** |
| Account-observability acquisition invite | Current | first-touch guest attribution only | unsafe unchanged |
| Hosted Room invite | Current | room guest participation / session | not a Guardian User/password invitation |
| ThreadSpace membership invitation | persistence mapping only | intended existing-account membership lifecycle | no bearer redemption implementation |
| Contacts / Circles / Spaces invite architecture | ADR-044 Proposed only | future collaboration concept | no runtime authority |
| Password reset / change / email verification | **Gap** | none | separate capability, not yet implemented |

The new account activation capability row is the most important delta from the prior inspection. Evidence:
- `guardian/account_activation/tokens.py` — `secrets.token_urlsafe(32)` (256-bit) bearer primitives, bounded length validation, SHA-256 digest, audit action enum.
- `guardian/account_activation/service.py` — `issue_activation`, `redeem_activation`, `revoke_activation`, error hierarchy (`ActivationAuthorizationError`, `ActivationConflictError`, `ActivationNotFoundError`, `ActivationStateError`, `ActivationUnavailableError`), Postgres `pg_advisory_xact_lock` serialization per recipient email.
- `guardian/db/models.py` — `AccountActivationCapability` (PK `activation_id` 36-char, `token_digest` 64-char, `recipient_email` 255-char, `intended_role` constrained to `admin`/`guest`, `created_by_user_id` FK to `users.id` RESTRICT, `created_at`, `expires_at`, `consumed_at`, `revoked_at`, `resulting_user_id` FK to `users.id` RESTRICT; CHECK constraints for expiry ordering, consumption XOR, and the `NOT (consumed AND revoked)` terminal-state exclusion; UNIQUE on `token_digest`; composite index on `recipient_email, consumed_at, revoked_at, expires_at`).
- `guardian/db/migrations/versions/a8d4c2f6b1e9_add_account_activation_capabilities.py` (down_revision `7e5a5fccf253`, dated 2026-09-17) — full DDL with the same CHECK constraints.
- `guardian/routes/auth.py` — `POST /auth/activate` and `POST /api/auth/activate` mounted in `guardian/guardian_api.py` under the `CODEXIFY_ENABLE_AUTH_ROUTES` flag, included in the friends-and-family profile route posture.
- `frontend/src/pages/login/ActivateAccountPage.tsx` — token captured from `#token=…` fragment, fragment cleared via `history.replaceState`, password + confirmation form, single POST to `/auth/activate`, generic public-failure messaging for invalid/expired/revoked states; routed in `frontend/src/App.tsx` at `/activate`.
- `guardian/cli/tester_account_activation.py` — `issue` and `revoke` subcommands gated by the friends-and-family runtime posture check.

Hosted-room invitations, ThreadSpace membership, and the account-observability acquisition invite remain distinct and unchanged; they do not carry activation authority.

## 6. Account-observability invite semantics

Unchanged from the prior inspection. The account-observability system is acquisition attribution, not authentication.

| Required question | Current answer |
|---|---|
| Token entropy | `secrets.token_urlsafe(32)` — 256 bits of source entropy |
| Raw-token persistence/visibility | returned only at creation; only SHA-256 digest is persisted |
| Expiration | optional `expires_at` checked dynamically; expired is unavailable, not a persisted status |
| Disable / revoke | explicit `disabled` and `revoked` status transitions |
| Single-use resolution | no; a valid link may resolve repeatedly and reuses/creates first-touch guest attribution |
| Recipient-email bound | no |
| User / account bound | no, aside from attribution after separate registration |
| Successful resolution grants | no authenticated account or account creation; guest attribution/cookie bootstrap only |
| Registration behavior | best-effort attribution after ordinary User registration; no account invitation redemption |
| Retention | analytics retention under observability policy, not credential-lifecycle retention |
| Audit | create/disable/revoke write audit events; public resolve does not write a resolution audit record |
| Frontend bootstrap | present, attribution-only: `frontend/src/main.tsx` invokes the fragment resolver, which clears `#invite` before POSTing to the observability resolve route; it creates no account session or credential authority |

Evidence: `guardian/account_observability/tokens.py`, `guardian/account_observability/contracts.py`, `guardian/account_observability/invites.py`, `guardian/routes/account_observability.py`, `guardian/db/models.py` (account-observability table block ~L6488-L6729), `frontend/src/main.tsx`, `frontend/src/lib/inviteAttribution.ts`, ADR-049, the admin-account-observability contract.

**Can `AccountObservabilityInviteLink` safely serve as an account-activation/password-setup token without changing its meaning? No.** Hashing a random bearer is only one primitive. The implemented link is multi-resolution, purpose-unbound, recipient-unbound, account-unbound, creates guest acquisition attribution rather than a canonical account, and has no consumption/credential setup/session-revocation semantics. Reuse unchanged would silently turn analytics attribution into authentication authority, violating ADR-049 and the activation invariants. The new `AccountActivationCapability` table is the correct place for activation; it inherits only the cryptographic and bounded-public-failure patterns, not the semantics.

## 7. Account activation / password-reset inventory

The activation redemption flow is now implemented end-to-end. Password reset, password change, and email verification are not.

| Capability | State | Evidence |
|---|---|---|
| `AccountActivationCapability` model | **Current** | `guardian/db/models.py` (table definition, CHECK constraints, FK, unique constraint, index) |
| Migration creating the table | **Current** | `guardian/db/migrations/versions/a8d4c2f6b1e9_add_account_activation_capabilities.py` (down_revision `7e5a5fccf253`, dated 2026-09-17) |
| Service: `issue_activation`, `redeem_activation`, `revoke_activation` | **Current** | `guardian/account_activation/service.py` |
| Token primitives: 256-bit `secrets.token_urlsafe`, SHA-256 digest, bounded validation | **Current** | `guardian/account_activation/tokens.py` |
| Operator CLI: `tester_account_activation issue|revoke` | **Current** | `guardian/cli/tester_account_activation.py` |
| Operator HTTP issuance route | **Gap** | `guardian/routes/` has no `/admin/activations/issue` or `/auth/activate/issue`; only `/auth/activate` redemption is wired |
| Public redemption route: `POST /auth/activate` and `/api/auth/activate` | **Current** | `guardian/routes/auth.py` (lines 282-309), mounted in `guardian/guardian_api.py` under `CODEXIFY_ENABLE_AUTH_ROUTES` |
| Activation frontend page: `/activate` | **Current** | `frontend/src/pages/login/ActivateAccountPage.tsx`, routed in `App.tsx` |
| Tests covering activation redemption, issuance, revoke, expiry | **Partial** | `guardian/cli/tester_account_activation.py` has command-line wiring but no dedicated test file (e.g., `tests/auth/test_account_activation_service.py`, `tests/cli/test_tester_account_activation.py`) is present; `tests/auth/test_tester_account_provision.py` exists but covers provisioning, not activation |
| Automated outbound mail for activation | **Gap** | confirmed below in §10 |
| Password-reset route, password-change route, password-mutation route | **Gap** | no `/auth/password/*` endpoint; `register_user` and the two operator CLIs are the only credential-creation paths |
| Email verification, recipient-email change, reissue / resend UX | **Gap** | no schema or route |
| Session revocation on credential mutation | **Gap** | no user-session index, credential epoch, or revoke-all operation exists |

The redemption path is sufficient for the activation-only slice described in §22: operator issues a capability via CLI, prints the URL once, transports it out of band, recipient redeems at `/activate`, then logs in via `/login`. The two remaining runtime gaps for that slice are (a) operator HTTP issuance for environments without shell access to the backend host, and (b) outbound mail — both are deferred per §19.

No smaller existing Codexify-native mechanism could have satisfied this. Hosted-room exchange is room-scoped; account-observability links are attribution-scoped; `OAuthConnection` is connector credential state. The new `AccountActivationCapability` is the right place and is already created.

## 8. Session and password lifecycle

Guardian issues an HMAC-signed session payload with subject, expiry, and nonce. Default session expiry is 24 hours (`DEFAULT_SESSION_TTL_SECONDS`). The raw session token is stored in Redis at `session:<token>` with the same TTL. Revocation removes only that exact raw token.

HTTP bearer/cookie session resolution is implemented in `guardian/core/auth_dependencies.py` and `guardian/core/dependencies.py`. Request identity selection uses valid session identity in multi-user mode and refuses header identity in private-preview mode. Preview access also requires normalized allowlist membership and role.

There is no user-to-session index, credential epoch, session generation/version, or revoke-all-by-user operation. Therefore:

- **Activation redemption does NOT issue a session.** It creates the User and returns `{ok, user_id, username}`; the recipient then authenticates via `/auth/login`. This is intentional and avoids an undocumented auto-login posture.
- **Password change / reset does not exist.** When it is added, it must either include a credential-epoch check during session resolution, or introduce a durable user-session index that allows `revoke_all_for_user(user_id)`. The former requires a per-user counter column and migration; the latter requires a new session-key scheme and migration. Both have export/restore and downgrade implications.
- **Provisioning CLI overwrites are silent with respect to live sessions.** The two operator provisioners reset a User's password hash without revoking existing sessions. This is a real bug surface if the operator uses these in production. It should be called out in operator runbooks.

The safe default for a future password-change slice is an account-level credential/session epoch checked during session resolution, with a documented downgrade posture and a one-time migration backfill.

## 9. Frontend auth/profile seams

| Surface | Current behavior | Activation / recovery suitability |
|---|---|---|
| `LoginPage` (`frontend/src/pages/login/LoginPage.tsx`) | username/email-form identifier plus password; remote-aware labels; generic error surface | re-entry point after activation; not activation itself |
| `RegisterPage` (`frontend/src/pages/login/RegisterPage.tsx`) | username/password direct public registration; unavailable when `VITE_PRIVATE_PREVIEW === "true"` | incompatible with recipient-bound invite requirement as written |
| `ActivateAccountPage` (`frontend/src/pages/login/ActivateAccountPage.tsx`) | hash-fragment token capture, fragment cleared via `history.replaceState`, password + confirmation, single POST to `/auth/activate`, generic public failure messaging | the Codexify-native activation surface — already wired |
| `UserProfilePage` (`frontend/src/pages/userProfile/UserProfilePage.tsx`) | display name, avatar URL, timezone metadata only | appropriate future authenticated security subsection, but no current password controls |
| `authState`, `useAuth` | session token in sessionStorage, bearer authentication, clears local state on 401/logout | seam for forced local logout after credential change |
| `App.tsx` | explicit login, register, profile, and activate paths | already routes `/activate` to `ActivateAccountPage` |

Evidence: `frontend/src/pages/login/LoginPage.tsx`, `RegisterPage.tsx`, `ActivateAccountPage.tsx`, `userProfile/UserProfilePage.tsx`, `lib/authState.ts`, `lib/api.ts`, `components/auth/useAuth.ts`, `App.tsx`.

The activation surface is already a dedicated unauthenticated route at `/activate`, reads the bearer from a URL fragment (so the token never reaches the server in the request path), and shows public-generic invalid/expired/unavailable messaging. A future authenticated password-change control belongs in a `Profile` security subsection, not in persona/settings metadata. A successful password change/reset should locally clear the caller session and direct reauthentication if server-side revoke-all is adopted.

The tester profile does NOT load the `user_profile` route group, so the future Profile-security surface is not reachable in the tester runtime; that is correct for the current friends-and-family slice but will need to be re-evaluated when a hosted/private runtime reaches that feature.

## 10. Google Workspace and outbound-mail inventory

There is no callable Codexify runtime path that sends email. No Gmail API sender, SMTP transport, generic mailer, transactional-email service, message send route, or tested outbound-message capability was found in current runtime code or configuration.

| Category | Evidence-backed state |
|---|---|
| Architecture / docs | ADR-047 is accepted; its provider capability/routing contract and implementation targets remain Proposed/inspection material |
| Placeholder / legacy | `guardian/pulse_secretary.py` contains mocked Gmail-shaped data only |
| Drive-only integration | present: `guardian/connectors/gsuite.py` is read-only GSheet; `guardian/integrations/google_drive.py` is Drive/Docs; `guardian/server/codexify_api.py` exposes OAuth status only |
| Reusable OAuth plumbing | present: encrypted `OAuthConnection` storage and Google OAuth callback/connect seams |
| Gmail API capability | absent |
| SMTP capability | absent |
| Tested outbound-message capability | absent |
| Live proof | absent |
| External Google Cloud / Workspace configuration | **EXTERNAL_CONFIGURATION_UNVERIFIED** |

The dedicated Drive OAuth/service implementation uses Drive/Docs read-only scopes and read operations (`google.oauth2.credentials`, `google.oauth2.service_account`, `googleapiclient.discovery`, scope `https://www.googleapis.com/auth/drive.file` in `guardian/integrations/google_drive.py`). `OAuthConnection` encrypts connection tokens at rest but is not a mail provider adapter. `.env.example` declares Google connector/OAuth and encryption key names (`GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT`, `GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY`) but no Gmail, SMTP, sender, or transactional-mail configuration names.

ADR-047 governs a broad user-owned Codexify Email architecture (provider adapters, routing identity, sync, drafts, approval, send, reconciliation). It explicitly does not prove an Email runtime or provider connectivity. The provider contract says initial consequential send/draft/alias operations are disabled and raw provider APIs are not ambient authority. The implementation-target inspection independently finds no runtime path, adapter, credential broker, mailbox model, or sending.

A narrowly governed Guardian transactional-security transport for activation mail would not require building the full user-mail product/domain. It could have a fixed system sender identity, a single account-security template class, recipient/purpose-bounded inputs, redacted audit, delivery-attempt/result separation, and no mailbox/sync/draft/user-send authority. That is distinct from a parallel user-mail authority. **However**, ADR-047 does not explicitly classify such system security notifications. It is scoped around agent/user correspondence and provider-routed mailbox behavior; it cannot be treated as an automatic approval or exemption for activation mail. A new ADR or explicit accepted amendment is required before that transport becomes runtime truth.

A likely Google implementation would need a Gmail sending authority such as `gmail.send` and a sender identity authorized by Workspace policy; any send-as alias, service-account delegation, OAuth consent, API enablement, quota, audit, egress, and retention treatment are **EXTERNAL_CONFIGURATION_UNVERIFIED**. The repository cannot prove the existence, approval, custody, policy permission, or operational readiness of any Google Workspace sender. No live mailbox was accessed or tested.

## 11. Migration / persistence terrain

The Alembic configuration is `backend/alembic.ini` with `script_location = %(here)s/../guardian/db/migrations` — migrations live at `guardian/db/migrations/versions/`. The latest canonical head after this morning's commit is `a8d4c2f6b1e9` (down_revision `7e5a5fccf253`), which creates `account_activation_capabilities`.

The working tree contains multiple parallel migration DAGs (baseline schema files and isolated test fixtures); the canonical Codexify lineage containing the account-observability tables and the activation table passes through `b2c3d4e5f6a7` (account-observability foundation), `9d4c2a7e1b6f` (historical↔canonical normalization, fail-closed for unknown/mixed shapes), and now `a8d4c2f6b1e9` (activation capabilities).

The relevant users / credential history:
- `f2b3c4d5e6f7` creates `users`.
- `f2b3c4d5e6f9` backfills and makes `password_hash` non-null.
- `e5f6a7b8c9d0` adds constrained roles.
- `c1a2b3c4d5e6` adds optional unique email.

The activation capability is now part of that lineage. Its constraints are tight enough to make runtime safety explicit:
- `intended_role IN ('admin', 'guest')` — operators cannot fabricate a new role token.
- `expires_at > created_at` — sanity check.
- `((consumed_at IS NULL AND resulting_user_id IS NULL) OR (consumed_at IS NOT NULL AND resulting_user_id IS NOT NULL))` — consumption XOR.
- `NOT (consumed_at IS NOT NULL AND revoked_at IS NOT NULL)` — terminal-state exclusion.
- `UNIQUE (token_digest)` — digest collisions are detected, not silently allowed.

The downgrade of `a8d4c2f6b1e9` is the table drop, which is appropriate for a capability not yet containing issued rows. Once activations are issued and consumed, downgrade semantics should be reviewed.

Delivery outcomes must remain separate from activation state. The current CLI fallback is: operator creates a capability, prints the URL exactly once, transports out of band. A failed out-of-band delivery must leave a recoverable pending capability that can be revoked/reissued or re-displayed via re-running the CLI; it must not make the account unrecoverable.

## 12. Architecture conflicts and dangerous reuse candidates

1. Treating `AccountObservabilityInviteLink` as authentication would convert acquisition attribution into account authority, violate ADR-049, and omit recipient binding and non-replayability. The new `AccountActivationCapability` is the correct place; reuse the cryptographic pattern, not the meaning.
2. Treating ADR-044 as implemented authority would promote a Proposed collaboration design into identity behavior without runtime proof.
3. Reusing `HostedRoomInvite` would bind a password flow to room guest/session authority rather than canonical User authority.
4. Continuing operator-selected durable passwords through provisioners contradicts the desired operator-custody boundary. They remain acceptable as a fallback for environments where activation is not yet enabled.
5. Creating a second user database, frontend identity truth, or provider-owned account record would violate ADR-005 and the remote-account contract.
6. Treating Cloudflare Access or Tailscale as Guardian account authority would confuse an outer network boundary with canonical credentials and roles.
7. Treating generic Google Drive OAuth or `OAuthConnection` as Gmail sending proof would create unsupported provider authority.
8. Persisting raw bearer material, plaintext temporary passwords, or a reversible password copy would violate credential-custody invariants.
9. Treating email-delivery success as activation success would collapse transport state into identity/credential state.
10. Resetting a password without account-wide session invalidation would leave an undocumented live-session posture. This applies to the provisioners as well as any future change/reset endpoint.
11. Auto-issuing a session at activation redemption would silently extend the activation token's authority past user creation and would couple bearer and session lifecycles; the current explicit "redemption creates User, recipient re-authenticates via /auth/login" posture is correct.

## 13. Current / Partial / Proposed / Gap matrix

| Capability | State | Evidence |
|---|---|---|
| Canonical Guardian User and bcrypt credential hash | Current | `guardian/db/models.py`, `guardian/routes/auth.py` |
| Username/email-form login and single-session logout | Current | `guardian/routes/auth.py`, `guardian/core/session_store.py` |
| Private-preview / tester operator provisioning | Current, parallel historical paths | `guardian/cli/private_preview_provision.py`, `guardian/cli/tester_account_provision.py` |
| Account-observability attribution invite | Current, internal-only | ADR-049; observability contract; `guardian/account_observability/` |
| Room guest invitation | Current | `guardian/routes/hosted_rooms.py`, `guardian/routes/hosted_room_guest.py` |
| ThreadSpace membership invite runtime | Partial: model only | `guardian/db/models.py` |
| Account activation capability model + migration | Current | `guardian/db/models.py` `AccountActivationCapability`, `guardian/db/migrations/versions/a8d4c2f6b1e9_add_account_activation_capabilities.py` |
| Activation service (issue/redeem/revoke) | Current | `guardian/account_activation/service.py` |
| Activation redemption HTTP route (`POST /auth/activate`) | Current | `guardian/routes/auth.py` |
| Activation frontend page (`/activate`) | Current | `frontend/src/pages/login/ActivateAccountPage.tsx`, routed in `App.tsx` |
| Activation issuance CLI (`tester_account_activation`) | Current | `guardian/cli/tester_account_activation.py` |
| Activation issuance HTTP route | Gap | no `/admin/activations/issue` or equivalent route handler |
| Activation tests (service, route, CLI, migration, redemption, expiry, revoke) | Gap | no dedicated test file present |
| Password setup / reset / change | Gap | auth route and frontend inventory |
| Authenticated password mutation UX | Gap | `UserProfilePage` is metadata-only and quarantined in tester profile |
| Revoke-all sessions on credential mutation | Gap | session_store inventory |
| Transactional security email transport | Gap | Google/Email inventory |
| Codexify Email product / provider adapter | Proposed architecture, no runtime | ADR-047 and Email contracts |
| Collaboration invite lifecycle | Proposed architecture | ADR-044 |
| Friends/family effective running profile | Gap: `RUNTIME_UNVERIFIED` | Docker socket unavailable in this environment |

## 14. Minimal safe implementation options

The prior inspection enumerated Options A–D for the activation capability. The activation flow itself is now implemented as Option A in production-shaped form:

| Option | Description | Status |
|---|---|---|
| A | Pending activation record creates the canonical User only on redemption | **Selected and implemented in the working tree** |
| B | Canonical User exists before activation with explicit pending state | not used — would have required changing the User lifecycle schema |
| C | Canonical User exists with unknowable generated hash, separate capability sets real password | not used — would have left a dormant canonical account |
| D | Smaller existing Codexify-native mechanism | none qualified |

The implementation honors every invariant identified for Option A in the prior inspection: recipient-bound, role-bound, purpose-bound (`account_activation`), expiring, single-use through `with_for_update()` + `consumed_at`, generic public failures (`activation_unavailable`), digest-only persistence, audit, revocation, advisory-lock serialization per recipient email, and recipient re-authentication after redemption rather than auto-login.

## 15. Recommended Codexify-native path

The activation capability is in place; the operator boundary is the CLI `guardian.cli.tester_account_activation`. Use it:

- Authorized operator (existing canonical `admin` user) invokes `python -m guardian.cli.tester_account_activation issue --email <recipient> --role <admin|guest> --actor-user-id <admin-user-id> --base-url <https://codexify.test> --expires-in-hours <24>`.
- The CLI prints `Activation ID`, `Expires at`, and `Activation URL` exactly once, then exits.
- The operator transports the activation URL out of band to the recipient.
- Recipient visits `{base_url}/activate#token=<raw>`, chooses a password, submits. The token is read from the URL fragment and never reaches the server log path; the frontend clears the fragment via `history.replaceState`.
- `redeem_activation` transactionally validates the capability, creates the User with `id == username == email == recipient_email`, bcrypts the password, marks `consumed_at`, writes `account_activation_redeemed` audit.
- Recipient is redirected to `/login` and authenticates normally. No auto-login.
- Operator can later `revoke --activation-id <id> --actor-user-id <admin>` any still-unconsumed capability (the redemption path also fails closed against revoked rows).

This preserves expiry, single-use, recipient/purpose binding, Guardian credential authority, and the operator's lack of durable password knowledge. It is aligned in direction with ADR-005, ADR-039's intended operator/user separation, ADR-049's prohibition on using acquisition invites as auth, and the remote-account contract's Guardian authority. It does not settle outbound-email governance. Do not attach activation sending to Codexify Email merely because both use email; decide and govern a narrow Guardian transactional-security transport separately.

The smaller first slice described in §22 does not require Gmail, SMTP, or any operator-side HTTP issuance endpoint — the CLI is the operator boundary.

## 16. Exact implementation file map (for the next atomic Task Spec)

The activation foundation is in place. The next atomic slice is **test coverage plus operator HTTP issuance** — both small, both contained. Do not implement password reset, automated email, or session-revocation semantics in the same slice.

| Area | Authorized files for the next slice |
|---|---|
| Backend tests (new) | `tests/auth/test_account_activation_service.py`; `tests/auth/test_auth_activate_route.py`; `tests/cli/test_tester_account_activation.py`; `tests/db/test_account_activation_models.py`; `tests/migration/test_account_activation_migration.py` |
| Operator HTTP issuance (new) | `guardian/routes/account_activation_admin.py`; `guardian/account_activation/admin_schemas.py`; registered in `guardian/guardian_api.py` behind an admin-only auth flag |
| Activation service touch-ups (only if tests require) | `guardian/account_activation/service.py`; `guardian/account_activation/tokens.py` |
| Frontend operator surface (optional) | `frontend/src/pages/admin/IssueActivationPage.tsx`; admin route group registered in `App.tsx` (defer if CLI is the operator boundary for this slice) |
| Tests for the existing redeem path | add to existing `tests/auth/test_auth_flow.py` if present; otherwise new file under `tests/auth/` |
| Operator / config docs | `docs/Ops/friends-family-tester-runtime.md` (one paragraph on `tester_account_activation issue|revoke`); `.env.example` only if a non-secret key is genuinely introduced (none expected) |
| Architecture / proof artifact | `docs/architecture/proofs/account-activation/<dated-proof-receipt>.md` (new), after the slice ships |

Files NOT authorized for this slice:
- `guardian/account_activation/service.py` (do not add new service-level authority without ADR).
- `guardian/routes/auth.py` (the redemption route is intentionally the only `/auth/activate` endpoint; no `/auth/activate/issue`).
- `frontend/src/pages/login/ActivateAccountPage.tsx` (the recipient surface is intentionally minimal and public-failure-only).
- `guardian/cli/tester_account_provision.py` (do not absorb activation into the provisioning tool — separation of concerns is the point).
- Anything touching Gmail, SMTP, OAuth, or Workspace configuration.
- Anything touching User schema, Alembic, or session store semantics.

## 17. Required tests and runtime proof

The next slice must prove (these become test file names):

1. `tests/auth/test_account_activation_service.py` — `issue_activation` validates role/email and returns raw bearer only once; duplicate-recipient issuance conflicts; expiry in the past raises; non-admin actor rejected.
2. `tests/auth/test_account_activation_service.py` — `redeem_activation` rejects already-consumed, revoked, expired, and malformed bearer with generic `ActivationUnavailableError`; bcrypt hash verification succeeds after redemption while plaintext never reaches persistence/log/audit fixtures.
3. `tests/auth/test_account_activation_service.py` — `revoke_activation` rejects already-consumed, already-revoked, and unknown IDs; admin-only.
4. `tests/auth/test_auth_activate_route.py` — `POST /auth/activate` honors `extra="forbid"`; returns `{ok, user_id, username}` on success; returns `400 activation_unavailable` on any invalid/expired/consumed/revoked bearer; does not issue a session.
5. `tests/cli/test_tester_account_activation.py` — `issue` and `revoke` subcommands gate on `runtime_posture_error`; URL printed exactly once; activation URL fragment carries the raw token.
6. `tests/db/test_account_activation_models.py` — CHECK constraints enforced (intended_role, expiry ordering, consumption XOR, terminal-state exclusion); UNIQUE token_digest; FK `created_by_user_id` and `resulting_user_id` to `users.id`.
7. `tests/migration/test_account_activation_migration.py` — upgrade creates the table with the expected columns/constraints; downgrade drops the table.
8. Existing tests under `tests/auth/test_tester_account_provision.py`, `tests/account_observability/`, `tests/migration/test_account_observability_compatibility_normalization.py` continue to pass.
9. Manual frontend smoke (recorded in a dev log, not asserted in this discovery) — `/activate?ignored#token=…` renders the password form, clears the fragment, and POSTs once.

No automated runtime test applied to this documentation-only inspection. Static/unit tests cannot prove Google/Workspace authorization, message delivery, sender identity, or live private-preview profile selection.

## 18. External / operator prerequisites

The following facts require operator confirmation or separately authorized live proof and are **EXTERNAL_CONFIGURATION_UNVERIFIED**:

- which tester/private-preview deployment is actually running and its effective profile/mode (Docker socket was unavailable in this environment).
- intended canonical recipient identity policy: whether normalized email is always `User.id`/`username` or only `User.email`. Current `redeem_activation` uses `id == username == email == recipient_email`.
- who is authorized to issue/revoke activation capability and how operator authentication/role is enforced. The CLI calls `_require_admin_operator`, which checks the actor's `User.role == 'admin'`. HTTP issuance would need the same gate plus a session-bound caller.
- retention, recovery, reissue, collision, and audit review policy for pending activation records.
- Google Cloud project, Gmail API enablement, OAuth/service-account design, approved scope, consent screen, sender mailbox, send-as policy, Workspace domain/delegation policy, quotas, audit/retention, and production egress.
- whether a narrowly scoped Guardian transactional-security transport is accepted as a distinct governed domain, or must be folded into/reconcile with ADR-047.
- delivery failure / retry policy and accountable operational owner.

If automated delivery is the only missing prerequisite after the activation capability exists, use the exact-once out-of-band URL fallback described in §15 rather than create, retain, or send a recipient password.

## 19. Deferred mature UX

Deferred deliberately — none implied by the next activation slice:

- full password reset/recovery policy and delivery transport;
- profile security settings and authenticated password change UX;
- multi-device session management, session list, revoke-one/revoke-all UX;
- email verification, recipient-email change, resend/reissue UX, and notification preferences;
- rate limiting, abuse heuristics, advanced operator console workflows, support tooling, and self-service recovery;
- Codexify Email mailbox/sync/draft/send architecture;
- external Google Workspace configuration and live delivery proof;
- Cloudflare / Tailscale changes and broadened preview / release claims;
- a frontend operator console page for activation issuance (the CLI is the operator boundary for this slice).

## 20. ADR impact for implementation

This inspection has no ADR impact and creates no runtime contract.

The activation capability itself appears directionally aligned with accepted ADR-005, accepted ADR-049, and the remote-account contract, while respecting ADR-039 as Proposed rather than accepted authority. It must not treat ADR-044 as implementation authority.

A new ADR, or an explicit accepted amendment, is required **only if** a future implementation introduces:
- durable pending-account policy beyond the activation capability itself,
- new operator authorization boundaries beyond the current `_require_admin_operator` check,
- account-wide session revocation semantics on credential mutation,
- a governed transactional-security email transport.

ADR-047 is not sufficient evidence that system-generated authentication mail is already authorized: it governs a different, user-mail/provider-adapter architecture and leaves this category unresolved.

## 21. Viability classification

The activation capability foundation is in place and exercised end-to-end by the redemption route and the operator CLI. The remaining gap for the smallest safe slice is test coverage and (optionally) an HTTP issuance route for operators without shell access. None of those requires Gmail, SMTP, password reset, or session-revocation architecture. The viability classification is therefore revised upward from the prior inspection's `REQUIRES_MULTI_SLICE_FOUNDATION`.

## 22. Next atomic implementation slice

Authorize **one bounded activation-coverage slice**:

1. Add the test files listed in §17 covering service, route, CLI, models, and migration for `AccountActivationCapability`. No production code changes.
2. Optionally add an operator HTTP issuance route under `/admin/activations/issue` gated by an admin session, calling `issue_activation`, returning the activation URL once in the response body. This is parallel to and does not replace the CLI; both invoke the same service. Skip if the CLI is acceptable as the sole operator boundary for this slice.
3. Update `docs/Ops/friends-family-tester-runtime.md` with a paragraph describing the `tester_account_activation issue|revoke` commands and the recipient flow at `/activate`.
4. Produce a dated proof receipt at `docs/architecture/proofs/account-activation/<dated>.md` summarizing the test results and the recipient flow.

Explicitly excluded from this slice:
- Gmail, SMTP, or any transactional email transport.
- Password reset, password change, or email verification.
- Profile security UX (also quarantined in tester profile).
- Session-revocation / credential-epoch design.
- Changes to `User`, `AccountActivationCapability`, or any existing migration.
- Changes to `register_user`, `login_user`, `logout_user`, or any auth route other than adding the admin issuance route above.
- Broadening private-preview / friends-and-family release claims.

**VIABLE_AS_ONE_BOUNDED_IMPLEMENTATION_SLICE**

The classification is true because the activation domain is already implemented and exercised by the working tree: model, migration, service, redemption route, recipient UI page, and operator CLI are all present. The remaining work for the next slice is test coverage and optional HTTP issuance, neither of which requires external configuration, second identity authority, schema change, or new infrastructure. The earlier `REQUIRES_MULTI_SLICE_FOUNDATION` classification was correct for the pre-implementation state but is no longer accurate for this checkout.