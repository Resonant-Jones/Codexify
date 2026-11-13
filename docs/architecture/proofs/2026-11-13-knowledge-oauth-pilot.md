# Knowledge OAuth pilot: local implementation receipt

## Scope and authority

Local implementation only, based on the GitHub/Notion read pilot at `8f731fabc`.
Not merged or deployed. This does not promote Beta or Private Preview qualification,
change imported-history permissions, or enable Preview worker dispatch. ADR-075 and
the Connections control-plane contract remain the boundaries: setup owns encrypted
credentials and explicit scope; adapters own bounded reads; Command Bus owns execution
policy. Accepted ADR-112 is integrated separately on main; its accepted-chat custody
prerequisite was initially a separate local branch. The later integration section
below records its deliberate combination without enabling Preview dispatch.

The authoritative account is the authenticated existing account-session dependency,
not an OAuth provider username, callback argument, email alias, or worker payload.
State is opaque and hashed in the database, expires in ten minutes, and binds account,
provider, generation, callback and an HttpOnly browser nonce. GitHub also uses PKCE.
Callbacks consume state once; stale callback/refresh responses cannot overwrite a
new connection or resurrect a disconnected one. A refresh crash fails closed and
requires reconnect rather than replaying a possibly consumed rotating refresh token.

## User-facing path

With the opt-in enabled and provider setup present: Connections → Notion or GitHub
Knowledge → Connect → provider consent → return → status. Notion uses its page-picker
and a read-content-only registration. GitHub uses a GitHub App user OAuth token,
not a classic OAuth app's broad `repo` scope. Its installation must grant Issues and
Pull requests read permission with no write permissions; the account must then
explicitly select at most twenty accessible repositories in Codexify. Discovery
never grants repositories. Installation/repository lists are capped at one hundred
items and report incompleteness; there is no automatic pagination authority expansion.

The existing read adapters consume these account-owned credentials and refresh when
an expiring credential needs rotation. Notion remains page search/read. GitHub remains
issue and pull-request search/body read, not code, diff, comment, sync or write access.
Guardian's existing opt-in local-single-account restrictions remain in force.

Disconnect is **local credential removal and pending-flow invalidation**, not a claim
that provider-side authorization or installation has been revoked. Old manual tokens
are removed atomically when OAuth begins/disconnects, so disabling the feature cannot
resurrect them. Other accounts are untouched. Future deliberate manual reconfiguration
with OAuth disabled is a separate action, not credential resurrection.

## External setup required, not performed

- Provision a Notion OAuth integration with read-content capability only and suitable
  installation audience. Register exact callback
  `https://<same-origin-host>/api/connect/notion/oauth/callback`.
- Provision a GitHub App, not OAuth App, with Issues and Pull requests read and no
  write permissions; choose selected repository installations. Register exact callback
  `https://<same-origin-host>/api/connect/github-knowledge/oauth/callback`.
- Set server-only `CODEXIFY_NOTION_OAUTH_CLIENT_ID`, `_CLIENT_SECRET`, `_REDIRECT_URI`;
  `CODEXIFY_GITHUB_APP_OAUTH_CLIENT_ID`, `_CLIENT_SECRET`, `_REDIRECT_URI`;
  optional `CODEXIFY_GITHUB_APP_SLUG` supplies the installation link.
- Supply a stable dedicated `GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY` through existing
  secret management, not source or browser storage. The existing encryption helper
  has legacy fallback key sources; a dedicated persistent key is preferred.
- Apply reviewed migration `d8a90bf32107` after pilot migration `c13f0713a901` in an
  authorized deployment. The separate custody branch has a sibling migration after
  `ab71d5ce9604`. The integrated candidate now sequences GitHub after custody:
  `ab71d5ce9604 → c7e4a1b9d602 → c13f0713a901 → d8a90bf32107`.
  Original branches are preserved; no migration has run against serving data.
- Enable `CODEXIFY_ENABLE_KNOWLEDGE_OAUTH` plus the existing provider route flags.
  Default remains off. No real `.env` or provider credentials were changed.
- Browser setup must use the same origin as the registered callback. Cross-origin
  desktop/custom-scheme authorization is not proven or claimed by this pilot.
- Configure proxies/access logs to omit callback query strings (codes/state), including
  upstream ingress logs. App responses never reflect them and use no-store,
  no-referrer and restrictive CSP. No external logging configuration was changed.

No Marketplace listing is required by the implementation; provider registration and
consent eligibility must be verified for the chosen distribution audience. Notion's
OAuth token response does not certify the configured read-only capability, so that
provider registration is an explicit operator review prerequisite.

## Evidence and limits

Focused provider protocol tests use mocked HTTP with fixed hosts, disabled redirects,
bounded responses and safe errors. Lifecycle tests use actual disposable SQLite for
single-use state, account/provider/browser mismatch, expiry, callback supersession,
refresh fencing, repository-generation fencing, deletion and flag-off legacy safety.
SQLite is not PostgreSQL concurrent locking proof. Migration roundtrip was tested
locally; no live migration or database was touched.

Frontend tests cover OAuth choice, generations, popup handling, explicit repository
selection, disconnected/pending/reconnect state and interruption behavior. No live
provider consent, real browser callback, PostgreSQL concurrency, server deployment or
full release qualification has been performed. An existing TypeScript compiler was subsequently located. App typecheck has 166
baseline diagnostics and root tsconfig has three baseline diagnostics; comparison
after removing one introduced unused import was identical. No dependency installation
was attempted. Refresh failures require reconnect.
Expired/consumed flow row retention is not yet a production maintenance policy.

## Primary protocol sources checked

- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app
- https://developers.notion.com/guides/authorization/overview

GitHub's current documentation supports S256 PKCE and `offline_access` for rotating
user tokens; that parameter is not repository authorization. Permissions come from
the GitHub App registration, installation and user's intersected access.

## Validation commands/results

- `PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest tests/connections tests/core/test_supported_profile.py -q --disable-warnings`: **231 passed**.
- Frontend `vitest run` for `KnowledgeOAuthSetup`, `ConnectionsCatalog` and
  `MinimaxOAuth` test files: **31 passed**. Existing `SettingsPanelDock.tsx`
  duplicate-style warning remains unrelated and unchanged.
- Scoped Ruff checks and `git diff --check`: passed. A whole-file Ruff pass on
  `guardian_api.py` still reports the same 91 baseline findings as the unchanged
  pilot branch; no global lint pass is claimed.
- `PATH=/Volumes/Dev_SSD/Codexify-main/.venv/bin:$PATH make docs`: passed.
  The first invocation lacked `python` on PATH; rerun used the existing venv.
- Independent source security review identified and verified fixes for browser
  origin enforcement, legacy credential resurrection, pending-flow disconnect
  visibility and bounded refresh errors. No remaining blocking source finding.

Read-only is this pilot's explicit grant, not an irreversible product-wide model.
Future write or selected-content offline sync would require distinct explicit
capabilities, scope selection and conflict policy; this task adds none of them.

## Integrated local candidate and stronger proof

The preserved original OAuth branch was integrated in a separate worktree on
current authoritative main `663d14990`, after custody prerequisite `a757531a5`.
The only cherry-pick conflict was the two appended Connections-contract sections;
both were retained. The old 'transport decision pending' sentence now correctly
refers to implementation and qualification of accepted ADR-112. No worker dispatch
was enabled by this integration.

Migration order is now one head:
`ab71d5ce9604 → c7e4a1b9d602 → c13f0713a901 → d8a90bf32107`.
The earlier GitHub migration test's stale parent/head assertions were updated to
this integrated lineage. Original worktrees and commits remain unchanged.

- Integrated focused backend suites: **302 passed**, 15 opt-in PostgreSQL tests
  skipped in the ordinary run, before adding the separate nine-case custody proof.
- Integrated frontend three focused suites: **31 passed**.
- **24 actual PostgreSQL 16.15 tests passed** separately: nine custody
  trigger/migration cases plus fifteen OAuth concurrency cases. Actual migrations
  `c7 → c13 → d8` and reverse downgrade ran against minimal baseline tables.
  This is not a replay of the entire historical Alembic migration graph.
- Concurrent state consumers produced exactly one winner; concurrent refresh claims
  produced exactly one winner. Callback/disconnect, refresh/disconnect, first-row
  creation and scope-change fences were exercised. Six immutable accepted-work
  mutations failed with SQLSTATE 23514; terminal/checkpoint updates remained allowed.
- Both proof clusters were newly created under unique temporary directories using
  existing Postgres.app binaries, Unix sockets only, no TCP listener and 32MB shared
  buffers. Each was stopped and absence of its postmaster PID verified. No Docker,
  production schema, user data, credentials or Preview volumes were used.
- A simulated Notion route bridge now proves callback → encrypted credential →
  source-bearing read → denial for another account → denial after disconnect.
  The external provider is mocked; this is not live provider consent evidence.

Configured tunnel hostname `preview.codexify.space` is verified in the private
Preview Cloudflare tunnel configuration and its installed LaunchAgent reference.
Thus the exact registration targets are:

- `https://preview.codexify.space/api/connect/notion/oauth/callback`
- `https://preview.codexify.space/api/connect/github-knowledge/oauth/callback`

These callback paths are implemented in the local candidate, **not deployed live**.
No OAuth application credentials or verified provider registrations were found in
the inspected configuration. An existing GitHub PAT is not a GitHub App OAuth
registration and was neither exposed nor used. Registration/consent/secret setup,
actual ingress callback delivery and Preview worker bridge qualification remain
separate blockers.

Final ordinary integrated run including both opt-in PostgreSQL test modules:
**302 passed, 24 skipped** (the same 24 passed separately against actual PostgreSQL).
A second independent source review confirmed preserved account handoff/checkpoints,
continued Preview invocation quarantine, and the single integrated migration head.
