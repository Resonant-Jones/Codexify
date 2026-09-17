# Account activation and invitation terrain

**Inspection date:** 2026-09-17
**Execution lane:** Architecture-Impact
**Mutation posture:** Documentation-only inspection. This report records repository and bounded runtime evidence; it changes no runtime contract.

## 1. Baseline and evidence boundary

The repository was inspected at the actual local working tree, not published GitHub state.

| Git fact | Observed value |
|---|---|
| git status --short | D docs/DEV_LOG/2026-09-17/Dev Log - 2026-09-17.md; M frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx; M frontend/src/features/chat/GuardianChat.tsx |
| branch | main |
| HEAD | 7b8af61e6e2312b6853a6ac5666e7ffc070337c9 |
| origin/main | 4a09140b98858630088265912528698166b0cec6 |
| merge-base | 4a09140b98858630088265912528698166b0cec6 |

Local main is three commits ahead of origin/main and is not behind it: 7b8af61e6, b5561c492, and a072634fb are local-only commits. The current-state document says two commits ahead; that statement is stale relative to this inspected baseline. Existing staged and unstaged changes are unrelated and were preserved.

Evidence was limited to repository files, migrations, tests, non-secret configuration key names, and bounded Docker status commands. The focused current tests inspected include tests/auth/test_auth_flow.py, tests/auth/test_private_preview_access.py, tests/auth/test_tester_account_provision.py, tests/routes/test_auth_invite_attribution.py, tests/account_observability/test_invite_service.py, tests/routes/test_account_observability_invites.py, tests/db/test_account_observability_migration.py, and tests/migration/test_account_observability_compatibility_normalization.py. Docker was unavailable through the local socket during inspection, so no running tester/private-preview instance was proven. No containers, database, account, mailbox, credential, provider, environment, or external Google configuration were changed or accessed.

The repository's canonical documentation validation target is make docs (Makefile:L99-L101). It was run after drafting and did not execute its validators because the environment has no python executable on PATH: it exited 2 after invoking python scripts/validate_docs.py. The Makefile also emitted pre-existing duplicate-target warnings for canonical-audit-live-proof-receipt. This is an environmental validation failure, not runtime proof and not repaired in this documentation-only task.

The source hierarchy used was the Axis source manifest and repository protocol: current-state document for release truth; accepted ADRs/contracts for governing intent; then current code, migrations, and tests for implementation truth. Relevant additional paths include guardian/guardian_api.py, guardian/connectors/google.py, guardian/connections/google_drive/, guardian/Users/users.py, guardian/identity.py, docker-compose.tester.yml, docker-compose.private-preview.yml, docker-compose.whooshd-deepseek.yml, scripts/ops/codexify_tester.sh, and .env.example.

## 2. Current runtime/profile topology

The current supported reality remains local Docker Compose core operation with local provider policy; the separately gated friends-and-family/private-preview lane is not a release proof. The current-state document explicitly says there is no current-tip Compose or live provider/runtime proof: docs/architecture/00-current-state.md:L24-L71.

There are two documented isolated profiles:

| Surface | Documented project/profile | Provisioning tool | Evidence and present conclusion |
|---|---|---|---|
| Older private preview | codexify_private_preview; v1-whooshd-deepseek-web | guardian.cli.private_preview_provision | docs/Ops/private-browser-preview.md and docker-compose.private-preview.yml |
| Stabilized tester/friends-and-family | codexify_tester; base tester configuration declares v1-friends-family-web | guardian.cli.tester_account_provision | docs/Ops/friends-family-tester-runtime.md; docker-compose.tester.yml |

The tester lifecycle combines the tester and Whoosh’d/DeepSeek overlays through scripts/ops/codexify_tester.sh. The latter overlay sets v1-whooshd-deepseek-web, while the tester runbook/provisioner names v1-friends-family-web. This is a real configuration/documentation seam, not evidence that either effective runtime is currently running. Bounded Docker inspection could not connect to the local daemon; therefore the deployed profile is **RUNTIME_UNVERIFIED**.

The intended current account-provisioning path for the stabilized tester environment is guardian.cli.tester_account_provision: its own module documentation declares that it supersedes the old private-preview operator workflow. The exact effective deployed profile remains **RUNTIME_UNVERIFIED** until a read-only healthy-runtime inspection is available.

## 3. Canonical auth/account model

Guardian is the canonical account, credential, session, and role authority. ADR-005 requires explicit account identity in multi-user mode and makes runtime mode bootstrap/configuration rather than account authority: docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md:L18-L106. The remote-account/profile contract likewise assigns canonical identity and session authority to Guardian: docs/architecture/remote-account-access-and-user-profile-contract.md:L28-L84.

The canonical User table is guardian.db.models.User:

| Property | Current implementation |
|---|---|
| id | required string primary key |
| username | required unique string |
| email | nullable unique string |
| password_hash | required non-null string |
| role | required admin or guest, default guest |
| lifecycle state | absent: no pending, active, disabled, activation, or credential-version field |

Evidence: guardian/db/models.py:L134-L153. The schema check permits only admin and guest. Canonical registration creates User.id and User.username from the submitted username and does not establish a recipient email; email is optional but is a secondary login lookup when the submitted identifier contains an at-sign: guardian/routes/auth.py:L53-L82 and L151-L222.

Supported login identifiers are username, or a normalized User.email when the username-form input contains an at-sign. Password verification is bcrypt through guardian/core/passwords.py:L1-L21. The legacy guardian/Users/users.py SQLite/plain-password shape is not imported by the Guardian route path and must not be revived as identity authority.

Registration accepts username and password, hashes the password, creates a guest User, and returns registration success without issuing a session. Private-preview exposure returns not found for registration. Login verifies the password, checks preview allowlist/role when applicable, persists a preview role correction if needed, issues a session, and returns token, user id, and expiry. Logout revokes only the presented session token. Evidence: guardian/routes/auth.py:L84-L222 and L224-L310.

## 4. Operator provisioning paths

Both existing provisioners require an operator to choose a password interactively. Neither is an activation flow.

| Tool | Intended runtime/profile | Gates and role | Account/reset behavior | Password custody | Current posture |
|---|---|---|---|---|---|
| guardian.cli.private_preview_provision | older codexify_private_preview | requires private-preview exposure; allowlisted normalized email determines permitted role | creates email-as-id/username User, or overwrites hash and role of existing User | getpass entry and confirmation; operator supplies durable password | legacy/superseded for stabilized tester, still a distinct intentionally documented private-preview path |
| guardian.cli.tester_account_provision | stabilized codexify_tester / friends-and-family | requires v1-friends-family-web and remote/local_safe posture; role is admin or guest | creates email-as-id/username User, or overwrites hash and role of existing User | getpass entry and confirmation; operator supplies durable password | intended current tester tool, but live deployment/profile remains RUNTIME_UNVERIFIED |

Evidence: guardian/cli/private_preview_provision.py:L1-L170; guardian/cli/tester_account_provision.py:L1-L214; docs/Ops/private-browser-preview.md; docs/Ops/friends-family-tester-runtime.md.

Both paths reset an existing account credential as part of reprovisioning. Neither has an activation record, recipient-bound capability, one-time redemption, outbound delivery, audit trail for credential setup, or revoke-all-session behavior. They satisfy neither the operator-password-custody goal nor a password-recovery lifecycle.

## 5. Invite-system inventory

The repository contains distinct invitation domains; they must not be conflated.

| Domain | Runtime state | Authority granted | Relationship to account activation |
|---|---|---|---|
| Account-observability acquisition invite | implemented internally | first-touch guest attribution only | unsafe unchanged |
| Hosted Room invite | implemented | room guest participation/session | not a Guardian User/password invitation |
| ThreadSpace membership invitation | persistence mapping only | intended existing-account membership lifecycle | no bearer redemption implementation |
| Contacts/Circles/Spaces invite architecture | ADR-044 Proposed only | future collaboration concept | no runtime authority |
| Account activation/password setup | absent | none | required new purpose-specific capability |

Hosted-room invitations use a separate pending/accepted/revoked/expired lifecycle and one-time exchange into a room-scoped guest session. Evidence: guardian/db/models.py:L1422-L1494; guardian/routes/hosted_rooms.py:L909-L1048; guardian/routes/hosted_room_guest.py:L315-L410. It cannot be repurposed as a canonical account invitation without changing both subject and authority.

ThreadSpaceMembershipInvitation records intended existing-user membership state, but its model documentation says it is only persistence mapping and creates no route, service, redemption, or authentication behavior: guardian/db/models.py:L303-L450. ADR-044 is explicitly Proposed and is scoped to future Contacts/Circles/Spaces collaboration, not accepted authentication truth: docs/architecture/adr/044-invite-lifecycle-and-storage-model.md:L1-L15.

## 6. Account-observability invite semantics

The account-observability system is an acquisition-attribution subsystem governed by accepted ADR-049 and the accepted observability contract, not authentication.

| Required question | Current answer |
|---|---|
| Token entropy | secrets.token_urlsafe(32): 256 bits of source entropy |
| Raw-token persistence/visibility | returned only by creation; only SHA-256 digest is persisted |
| Expiration | optional expires_at checked dynamically; expired is unavailable, not a persisted status |
| Disable/revoke | explicit disabled and revoked status transitions |
| Single-use resolution | no; valid link may resolve repeatedly and reuses/creates first-touch guest attribution |
| Recipient-email bound | no |
| User/account bound | no, aside from attribution association after separate registration |
| Successful resolution grants | no authenticated account or account creation; guest attribution/cookie bootstrap only |
| Registration behavior | best-effort attribution after ordinary User registration; no account invitation redemption |
| Retention | analytics data is retained under observability policy, not a credential-lifecycle retention policy |
| Audit | create/disable/revoke record audit/event evidence; public resolve does not itself write a resolution audit record |
| Frontend bootstrap | present, but attribution-only: frontend/src/main.tsx invokes the fragment resolver, which clears #invite before POSTing it to the observability resolve route; it creates no account session or credential authority |

Evidence: guardian/account_observability/tokens.py:L1-L61; guardian/account_observability/contracts.py:L1-L62; guardian/account_observability/invites.py:L1-L357; guardian/routes/account_observability.py:L1-L287; guardian/db/models.py:L6488-L6729; frontend/src/main.tsx:L16-L145; frontend/src/lib/inviteAttribution.ts:L1-L68; frontend/src/lib/inviteAttribution.test.ts; tests/account_observability/test_invite_service.py; tests/routes/test_account_observability_invites.py; docs/architecture/adr/ADR-049-admin-account-observability-and-invite-attribution.md:L24-L117; docs/architecture/admin-account-observability-contract.md:L31-L172.

**Can AccountObservabilityInviteLink safely serve as an account-activation/password-setup token without changing its meaning? No.** Hashing a random bearer token is only one primitive. The implemented link is multi-resolution, purpose-unbound, recipient-unbound, account-unbound, creates guest acquisition attribution rather than a canonical account, and has no consumption/credential setup/session-revocation semantics. Reuse unchanged would silently turn analytics attribution into authentication authority, violating ADR-049 and this task's invariants. A future implementation may reuse narrowly scoped cryptographic and generic-public-failure patterns, but not the table, route, or authority semantics.

## 7. Account activation/password-reset inventory

Repository-wide inspection found no canonical pending-account model, activation token, password-reset token, email-verification token, one-time credential setup record, first-login password-change flag, account-status field, password-change route, password-reset route, or session-generation/version mechanism.

There is no smaller existing Codexify-native credential mechanism that meets the required goal. The hosted-room exchange is deliberately room-scoped; account-observability links are deliberately attribution-scoped; OAuthConnection is connector credential state, not account credential state: guardian/db/models.py:L2451-L2500.

The only discovered runtime password/account-creation paths are:
- ordinary registration, which creates a hash from the caller's submitted password;
- private-preview provisioning, which creates or overwrites a hash from an operator-entered password;
- tester provisioning, which creates or overwrites a hash from an operator-entered password.
- local default-user bootstrap, which creates only the local seed User when absent and hashes either the non-secret configuration input or an unpredictable generated value; it does not reset an existing User credential (guardian/core/user_manager.py:L1-L88).

No reset or change route exists anywhere in Guardian routes or the frontend account/profile seams.

## 8. Session and password lifecycle

Guardian issues an HMAC-signed session payload with subject, expiry, and nonce; default session expiry is 24 hours. The raw session token is stored in Redis under a session-prefixed key with TTL. Revocation removes only that exact raw token. Evidence: guardian/core/auth.py:L1-L194 and guardian/core/session_store.py:L1-L122.

HTTP bearer/cookie session resolution is implemented in guardian/core/auth_dependencies.py:L1-L154. Request identity selection uses valid session identity in multi-user mode and refuses header identity in private-preview mode: guardian/core/dependencies.py:L219-L238 and L382-L518. Preview access also requires normalized allowlist membership and role: guardian/core/preview_access.py:L1-L156.

There is no user-to-session index, credential epoch, session generation/version, or revoke-all-by-user operation. Therefore changing a password currently cannot revoke existing sessions because no password-change/reset operation exists; provisioning resets similarly do not explicitly revoke existing sessions. A future password change/reset must choose and document explicit invalidation. The safe default is an account-level credential/session epoch checked during session resolution, or a durable user-session index allowing revoke-all, with migration and restore implications.

## 9. Frontend auth/profile seams

The smallest existing frontend seams are already separated:

| Surface | Current behavior | Activation/recovery suitability |
|---|---|---|
| LoginPage | username/email-form identifier plus password; remote-aware labels; generic error surface | re-entry point after activation, not activation itself |
| RegisterPage | username/password direct public registration; unavailable in private preview | incompatible with recipient-bound invite requirement as written |
| UserProfilePage | display name, avatar, timezone, accent metadata only | appropriate future authenticated security subsection, but no current password controls |
| authState and useAuth | session token in sessionStorage, bearer authentication, clears local state on 401/logout | seam for forced local logout after credential change |
| App | explicit login, register, and profile paths | smallest route seam for a dedicated unauthenticated activation page |

Evidence: frontend/src/pages/login/LoginPage.tsx; frontend/src/pages/login/RegisterPage.tsx; frontend/src/pages/userProfile/UserProfilePage.tsx; frontend/src/lib/authState.ts; frontend/src/lib/api.ts; frontend/src/hooks/useAuth.ts; frontend/src/App.tsx; relevant tests under frontend/src/pages/login/, frontend/src/pages/userProfile/, frontend/src/lib/, and frontend/src/App.test.tsx.

The Codexify-native activation surface should be a dedicated unauthenticated route, such as /activate, rather than overload Login, Register, or metadata-only Profile. It should read capability material from a URL fragment rather than server-visible query string where feasible, display public-generic invalid/expired/unavailable messaging, and submit password setup once. A later authenticated password-change control belongs in a Profile security subsection, not persona/settings metadata. A successful password change/reset should locally clear the caller session and direct reauthentication if server-side revoke-all is adopted.

## 10. Google Workspace and outbound-mail inventory

There is no callable Codexify runtime path that sends email. No Gmail API sender, SMTP transport, generic mailer, transactional-email service, message send route, or tested outbound-message capability was found in current runtime code or configuration.

| Category | Evidence-backed state |
|---|---|
| Architecture/docs | ADR-047 is accepted; its provider capability/routing contract and implementation targets remain Proposed/inspection material |
| Placeholder/legacy | guardian/pulse_secretary.py contains mocked Gmail-shaped data only |
| Drive-only integration | present: generic Google connector and Google Drive OAuth/service paths |
| Reusable OAuth plumbing | present: encrypted OAuthConnection storage and Google OAuth callback/connect seams |
| Gmail API capability | absent |
| SMTP capability | absent |
| Tested outbound message capability | absent |
| Live proof | absent |
| External Google Cloud/Workspace configuration | EXTERNAL_CONFIGURATION_UNVERIFIED |

The generic connector requests Drive plus OpenID/profile/email identity scopes, not Gmail send scope: guardian/connectors/google.py:L1-L212. The dedicated Drive OAuth/service implementation uses Drive/Docs read-only scopes and read operations: guardian/connections/google_drive/oauth.py and guardian/connections/google_drive/service.py. OAuthConnection encrypts connection tokens at rest, but is not a mail provider adapter: guardian/db/models.py:L2451-L2500. .env.example declares Google connector/OAuth and encryption key names, but no Gmail, SMTP, sender, or transactional-mail configuration names.

ADR-047 governs a broad user-owned Codexify Email architecture, including provider adapters, routing identity, sync, drafts, approval, send, and reconciliation. It explicitly does not prove an Email runtime or provider connectivity: docs/architecture/adr/047-codexify-email-routing-identity-mailbox-governance-provider-adapter-contract.md:L1-L194. The provider contract says initial consequential send/draft/alias operations are disabled and raw provider APIs are not ambient authority: docs/architecture/codexify-email-provider-capability-routing-contract.md:L1-L193. The implementation-target inspection independently finds no runtime path, adapter, credential broker, mailbox model, or sending: docs/architecture/inspections/codexify-email-implementation-targets.md:L1-L185.

A narrowly governed Guardian transactional-security transport would not require building the full user-mail product/domain. It could have a fixed system sender identity, fixed account-security template class, recipient/purpose-bounded inputs, redacted audit, delivery attempt/result separation, and no mailbox/sync/draft/user-send authority. That is distinct from a parallel user-mail authority. However, ADR-047 does not explicitly classify such system security notifications. It is scoped around agent/user correspondence and provider-routed mailbox behavior; it cannot be treated as an automatic approval or exemption for activation mail. A new ADR or explicit amendment is required before that transport becomes runtime truth.

A likely Google implementation would need a Gmail sending authority such as gmail.send and a sender identity authorized by Workspace policy; any send-as alias, service-account delegation, OAuth consent, API enablement, quota, audit, egress, and retention treatment are **EXTERNAL_CONFIGURATION_UNVERIFIED**. The repository cannot prove the existence, approval, custody, policy permission, or operational readiness of any Google Workspace sender. No live mailbox was accessed or tested.

## 11. Migration/persistence terrain

The Alembic head is 7e5a5fccf253, as reported by the repository backend Alembic configuration. The initial User schema and credential history includes:
- f2b3c4d5e6f7 creates users;
- f2b3c4d5e6f9 backfills and makes password_hash non-null;
- e5f6a7b8c9d0 adds constrained roles;
- c1a2b3c4d5e6 adds optional unique email.

The account-observability lineage is materially compatibility-sensitive:
- b2c3d4e5f6a7 introduced historical account-observability tables;
- 9d4c2a7e1b6f recognizes historical/canonical/mixed shapes, normalizes only the known historical schema, and deliberately fails unsafe/mixed cases;
- tests/migration/test_account_observability_compatibility_normalization.py proves canonical no-op, historical normalization, failure-before-DDL for mixed/unrecognized shapes, and non-reversible downgrade behavior;
- tests/db/test_account_observability_migration.py covers upgrade lineage.

Evidence: backend/alembic/versions/f2b3c4d5e6f7_initial_schema.py; backend/alembic/versions/f2b3c4d5e6f9_add_password_hash_to_users.py; backend/alembic/versions/e5f6a7b8c9d0_add_user_role.py; backend/alembic/versions/c1a2b3c4d5e6_add_optional_user_email.py; backend/alembic/versions/b2c3d4e5f6a7_add_account_observability_tables.py; backend/alembic/versions/9d4c2a7e1b6f_normalize_account_observability_compatibility.py.

Every safe activation option requires new persistence and therefore a new Alembic revision; no existing migration may be edited. The minimum durable concept is a purpose-specific activation capability record containing a one-way token digest, intended normalized recipient email, intended canonical role token, expiry, lifecycle/consumed/revoked timestamps, creator/audit correlation, and optionally a pending canonical account linkage. If credential changes must revoke all existing sessions, the smallest robust design also needs a durable credential/session epoch or a durable user-session index. Both introduce export/restore, downgrade, and existing-instance transition obligations.

Delivery outcomes must be separate from activation state. A failed email delivery must leave a recoverable pending capability that can be revoked/reissued or displayed exactly once for authorized out-of-band delivery; it must not make the account unrecoverable.

## 12. Architecture conflicts and dangerous reuse candidates

1. Treating AccountObservabilityInviteLink as authentication would convert acquisition attribution into account authority, violate ADR-049, and omit recipient binding and non-replayability.
2. Treating ADR-044 as implemented authority would promote a Proposed collaboration design into identity behavior without runtime proof.
3. Reusing HostedRoomInvite would bind a password flow to room guest/session authority rather than canonical User authority.
4. Continuing operator-selected durable passwords through provisioners contradicts the desired operator-custody boundary.
5. Creating a second user database, frontend identity truth, or provider-owned account record would violate ADR-005 and the remote-account contract.
6. Treating Cloudflare Access or Tailscale as Guardian account authority would confuse an outer network boundary with canonical credentials and roles.
7. Treating generic Google Drive OAuth or OAuthConnection as Gmail sending proof would create unsupported provider authority.
8. Persisting raw bearer material, plaintext temporary passwords, or a reversible password copy would violate credential-custody invariants.
9. Treating email-delivery success as activation success would collapse transport state into identity/credential state.
10. Resetting a password without account-wide session invalidation would leave an undocumented live-session posture.

## 13. Current / Partial / Proposed / Gap matrix

| Capability | State | Evidence |
|---|---|---|
| Canonical Guardian User and bcrypt credential hash | Current | guardian/db/models.py:L134-L153; guardian/routes/auth.py |
| Username/email-form login and single-session logout | Current | guardian/routes/auth.py; guardian/core/session_store.py |
| Private-preview/tester operator provisioning | Current, parallel historical paths | guardian/cli/private_preview_provision.py; guardian/cli/tester_account_provision.py |
| Account-observability attribution invite | Current, internal-only | ADR-049; observability contract; guardian/account_observability/ |
| Room guest invitation | Current | guardian/routes/hosted_rooms.py; guardian/routes/hosted_room_guest.py |
| ThreadSpace membership invite runtime | Partial: model only | guardian/db/models.py:L303-L450 |
| Friends/family effective running profile | Gap: RUNTIME_UNVERIFIED | Docker socket unavailable; topology files conflict |
| Pending activation account lifecycle | Gap | User model and route inventory |
| Password setup/reset/change | Gap | auth route and frontend inventory |
| Revoke-all sessions on credential change | Gap | session_store inventory |
| Recipient/purpose-bound one-time activation capability | Gap | invite inventory |
| Transactional security email transport | Gap | Google/Email inventory |
| Codexify Email product/provider adapter | Proposed architecture, no runtime | ADR-047 and Email contracts |
| Collaboration invite lifecycle | Proposed architecture | ADR-044 |

## 14. Minimal safe implementation options

| Option | Description | Fit with current invariants | Cost/risk |
|---|---|---|---|
| A | Store a pending invitation; create canonical User only on redemption | cleanest password ownership; avoids pre-created canonical account | activation record must carry recipient/role truth; identity collision/reissue/recovery rules are needed |
| B | Create canonical User before activation with explicit pending state and no usable password | explicit lifecycle and audit correlation | User.password_hash is non-null today; requires lifecycle/schema/register/login gates and migration across existing users |
| C | Create canonical User with an unknowable generated hash, then separate setup capability sets real password | works with current non-null hash constraint | leaves a canonical but unusable account; requires careful login gates, collision/reissue/recovery, and durable session invalidation |
| D | Reuse an existing native mechanism | none qualifies | no safe smaller mechanism was discovered |

A is the smallest coherent initial design if the product accepts that canonical User creation occurs only on valid one-time redemption. It preserves Guardian as sole durable authority, avoids a fake password, gives a clean operator truth boundary, and localizes lifecycle state to the activation record. The invitation must reserve normalized recipient email and intended role before redemption. On redemption, transactionally validate capability state, create the User with recipient email as canonical account identifier under the chosen account policy, bcrypt the recipient-submitted password, mark consumed, write audit, and reject replay.

B is attractive only if operations need a visible pre-created canonical account before recipient action. It is not the smallest path because it expands User lifecycle semantics and requires changes to all login/register/provisioning/restore interpretations. C is mechanically compatible with password_hash non-nullability, but introduces a dormant canonical account and should not be selected merely to avoid a migration; it still needs a purpose-specific capability, explicit lifecycle, and session posture.

## 15. Recommended Codexify-native path

Use Option A: a Guardian-owned, purpose-specific pending activation capability that creates the canonical User only once a recipient redeems it and chooses a password.

The capability should:
- be created only by an authenticated authorized operator endpoint/CLI boundary;
- bind normalized recipient email, canonical role token, purpose account_activation, expiry, and issuance/revocation/consumption audit;
- return the raw activation URL exactly once and persist only a cryptographic digest;
- be single-use through a transactional consume-and-create operation;
- return generic public failures for invalid, expired, revoked, consumed, or mismatched capability;
- create a User and bcrypt password only at successful redemption;
- explicitly not issue a durable account until redemption completes;
- use a documented duplicate-email/reissue/recovery policy;
- retain audit state without persisting password or raw capability material.

The first delivery slice should be transport-optional. The operator can create an activation capability, view its raw URL exactly once, and transport it out of band. That is the smallest secure fallback if automated email remains unavailable: it preserves expiry, single-use, recipient/purpose binding, Guardian credential authority, and the operator's lack of durable password knowledge. The raw URL must not be retrievable later.

This is aligned in direction with ADR-005, ADR-039's intended operator/user separation, ADR-049's prohibition on using acquisition invites as auth, and the remote-account contract's Guardian authority. It does not settle outbound-email governance. Do not attach activation sending to Codexify Email merely because both use email; decide and govern a narrow Guardian transactional-security transport separately.

## 16. Exact implementation file map

The next atomic Task Spec should authorize only the following files, with migration revision identifier assigned at implementation time.

| Area | Exact authorized files |
|---|---|
| Activation domain | guardian/account_activation/contracts.py (new); guardian/account_activation/service.py (new); guardian/account_activation/tokens.py (new); guardian/account_activation/__init__.py (new) |
| Data model | guardian/db/models.py |
| Migration | backend/alembic/versions/<new_revision>_add_account_activation_invitations.py (new only) |
| Route registration and API | guardian/routes/account_activation.py (new); guardian/guardian_api.py |
| Operator creation boundary | guardian/cli/tester_account_provision.py or a new guardian/cli/account_activation_provision.py, selected explicitly by the Task Spec; do not modify both without a stated migration plan |
| Session invalidation foundation | guardian/core/session_store.py; guardian/core/auth.py; guardian/core/auth_dependencies.py, only if the selected slice includes durable credential/session epoch semantics |
| Frontend activation | frontend/src/pages/login/ActivationPage.tsx (new); frontend/src/pages/login/ActivationPage.test.tsx (new); frontend/src/App.tsx; frontend/src/lib/api.ts |
| Account security UI, later slice | frontend/src/pages/userProfile/UserProfilePage.tsx and its tests; not required for first activation-only slice |
| Backend tests | tests/routes/test_auth.py; tests/routes/test_account_activation.py (new); tests/db/test_account_activation_models.py (new); tests/migration/test_account_activation_migration.py (new); tests/core/test_session_store.py |
| Frontend tests | frontend/src/App.test.tsx; frontend/src/lib/authState.test.ts; activation-page test above |
| Operator/config docs | docs/Ops/friends-family-tester-runtime.md; .env.example only if a non-secret key is genuinely introduced |
| Architecture/proof artifact | docs/architecture/proofs/account-activation/<dated-proof-receipt>.md (new), after a future implementation task authorizes it |

Automated delivery is intentionally excluded from this first map. If chosen later, a separate transport-specific Task Spec must name its provider contract, sender authority, configuration keys, secret custody, audit redaction, retry/failed-delivery handling, and external proof boundary.

## 17. Required tests and runtime proof

A future first implementation slice must prove:
1. authorized operator creation validates role/email and returns raw capability only once;
2. database retains a digest but never raw capability/password;
3. redemption accepts only matching recipient/purpose before expiry and creates User only once;
4. replay, expired, revoked, malformed, wrong-recipient, and duplicate-email cases fail closed with public-generic response;
5. role tokens remain canonical and operator-controlled;
6. bcrypt hash verification succeeds after redemption while plaintext never reaches persistence/log/audit fixtures;
7. normal login works after activation, while ordinary registration cannot bypass private-preview policy;
8. audit records issuance, revocation, redemption attempt/result without raw bearer/password;
9. migration upgrades fresh and existing shapes, and downgrade behavior is explicitly safe or deliberately unsupported;
10. any credential epoch/revoke-all implementation invalidates pre-change sessions and preserves expected current session behavior;
11. frontend handles valid, invalid, expired, used, and revoked states without persisting the activation token;
12. a focused live tester proof uses an isolated non-production recipient account only when separately authorized.

No automated runtime test applied to this documentation-only inspection. Static/unit tests cannot prove Google/Workspace authorization, message delivery, sender identity, or live private-preview profile selection.

## 18. External/operator prerequisites

The following facts require operator confirmation or separately authorized live proof and are **EXTERNAL_CONFIGURATION_UNVERIFIED**:
- which tester/private-preview deployment is actually running and its effective profile/mode;
- intended canonical recipient identity policy: whether normalized email is always User.id/username or only User.email;
- who is authorized to issue/revoke activation capability and how operator authentication/role is enforced;
- retention, recovery, reissue, collision, and audit review policy for pending activation records;
- Google Cloud project, Gmail API enablement, OAuth/service-account design, approved scope, consent screen, sender mailbox, send-as policy, Workspace domain/delegation policy, quotas, audit/retention, and production egress;
- whether a narrowly scoped Guardian transactional-security transport is accepted as a distinct governed domain, or must be folded into/reconcile with ADR-047;
- delivery failure/retry policy and accountable operational owner.

If automated delivery is the only missing prerequisite after the activation capability exists, use the exact-once out-of-band URL fallback described in Section 15 rather than create, retain, or send a recipient password.

## 19. Deferred mature UX

Deferred deliberately:
- full password reset/recovery policy and delivery transport;
- profile security settings and authenticated password change UX;
- multi-device session management, session list, revoke-one/revoke-all UX;
- email verification, recipient-email change, resend/reissue UX, and notification preferences;
- rate limiting, abuse heuristics, advanced operator console workflows, support tooling, and self-service recovery;
- Codexify Email mailbox/sync/draft/send architecture;
- external Google Workspace configuration and live delivery proof;
- Cloudflare/Tailscale changes and broadened preview/release claims.

None of these are implied by the first activation capability slice.

## 20. ADR impact for implementation

This inspection has no ADR impact and creates no runtime contract.

The activation capability itself appears directionally aligned with accepted ADR-005, accepted ADR-049, and the remote-account contract, while respecting ADR-039 as Proposed rather than accepted authority. It must not treat ADR-044 as implementation authority.

A new ADR, or an explicit accepted amendment, is required before account-activation lifecycle and credential-recovery semantics become runtime truth if the implementation introduces durable pending-account policy, new operator authorization boundaries, account-wide session revocation semantics, or a governed transactional-security email transport. ADR-047 is not sufficient evidence that system-generated authentication mail is already authorized: it governs a different, user-mail/provider-adapter architecture and leaves this category unresolved.

## 21. Viability classification

The activation capability can be implemented without first proving Gmail or building Codexify Email because the secure one-time out-of-band URL fallback preserves the required authority and password-custody invariants. However, a complete safe path includes at least two independently governed foundations: (1) purpose-specific activation persistence/redemption with tests and (2) explicit credential/session invalidation policy; transactional email is a further separately governed/externally dependent slice. The first slice should not silently choose the session-revocation or mail-transport architecture.

## 22. Next atomic implementation slice

Authorize one bounded activation-foundation slice only:

Create a Guardian-owned activation-invitation table and service; add an operator-only issuance route/CLI that returns a recipient-bound, role-bound, purpose-bound, expiring raw URL exactly once; add a public one-time redemption route that creates the canonical User from the recipient-selected password; add a dedicated activation page; persist only a digest; audit issuance/revocation/redemption; and support revocation. Use manual out-of-band delivery. Exclude Gmail/SMTP, password reset/change, profile security UX, Cloudflare changes, and broad session-revocation implementation unless the Task Spec explicitly includes a selected durable revocation mechanism.

The implementation Task Spec must make the unresolved account-wide session invalidation posture explicit: either include a minimal durable epoch/index design with its migration and tests, or document that credential mutation is not yet offered beyond first activation. It must not treat session behavior as an incidental detail.

**REQUIRES_MULTI_SLICE_FOUNDATION**
