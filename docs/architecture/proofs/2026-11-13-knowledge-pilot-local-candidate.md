# GitHub / Notion Knowledge pilot: isolated local candidate

Date: 2026-11-13. Branch base: `a01a3400549596692930eb54544d3af7501d2d55`.
This continues the [preflight receipt](2026-11-13-github-notion-pilot-preflight.md).
**Not deployed, not live-provider-qualified, not Private Preview support.**

## Implemented scope

- Added a separate GitHub Knowledge read adapter, distinct from legacy sync.
  It supports bounded issue/PR phrase search within one explicitly granted
  repository, and selected issue/PR body reads. It does **not** read repository
  files, comments, diffs, or attachments, write, sync, ingest, or create memory.
- Added encrypted account-owned GitHub credentials with an explicit list of
  one to twenty allowed repositories, configure / validate / status / disconnect
  routes, and Command Bus-discoverable read routes. Token permissions alone do
  not grant an unlisted repository. No environment fallback serves credentials
  to arbitrary accounts.
- Added migration `c13f0713a901` after `ab71d5ce9604`. It creates only
  `github_knowledge_credentials`; it does not alter existing data. No live
  migration was run. Any future merge must reconcile concurrent migration heads.
- Added opt-in ordinary Guardian tool projection/invocation for validated
  Notion/GitHub connections on the existing **local single-account DeepSeek
  tool lane only**. The authenticated task account owns credential resolution;
  model arguments cannot select account, token, headers, or transport.
- Invocation rechecks eligibility and connection validation. Existing accepted-
  attempt checkpoint and Command Bus policy remain in the path. Caller-supplied
  knowledge tool IDs are stripped. Disconnect removes the local credential;
  later calls fail before contacting a provider.

## Deliberate deployment and product boundaries

`CODEXIFY_ENABLE_KNOWLEDGE_CHAT_PILOT` defaults off. GitHub routes additionally
require `CODEXIFY_ENABLE_GITHUB_KNOWLEDGE_ROUTES`, default off. Neither flag was
set on the host. Existing supported profiles keep new routes quarantined; no
profile file changed.

The existing scoped local HTTP transport rejects Private Preview, remote auth,
multi-user mode, and a task account different from the configured local owner.
This change deliberately reuses that restriction. It does not forward an admin
credential as another user's identity, invent an `X-User-Id` authority bridge,
or weaken any existing guard. The next Preview stage needs a reviewed
worker-to-Command-Bus account-custody transport and its own qualification.

The pilot is an API/developer candidate. A GitHub Knowledge catalog/setup UI is
**not** implemented; the existing GitHub sync UI must not be presented as this
connection. Notion retains its existing setup surface. The current bounded
chat loop permits one tool operation, not search-then-read iteration in one
turn. OpenAI and Whoosh'd advertisement are unchanged.

No actual credentials were configured. The inspected VaultNode root `.env`
fields remained empty. No provider requests, production database changes,
Docker actions, pushes, merges, or deployments occurred.

## Security review and fixes

- Fixed direct and whole-request validation error paths that could echo secret
  inputs: setup-route validation errors now return bounded classifications.
- Validation uses its credential snapshot and row locks; replacement resets
  validation. Both configure and validation take row locks to avoid ORM
  stale-field races. PostgreSQL concurrent execution has not been live-tested.
- GitHub fixed-host GET-only transport refuses redirects, malformed identities,
  ungranted repositories and search-scope injection. Errors do not return raw
  provider responses or credentials. Results preserve canonical source links.
- Notion's prerequisite bounded traversal fix remains included. Read results
  mark incomplete coverage rather than claiming exhaustive content.
- Knowledge result instructions explicitly classify external content as
  evidence, never authority. This is defense-in-depth, not a claim of immunity
  to model prompt injection.
- Revocation means local disconnect blocking **subsequent** reads; it neither
  revokes the upstream PAT/integration token nor cancels an in-flight request.

## Contracts and authoritative state

Aligned with ADR-071 (projection versus execution), ADR-075 (bounded Knowledge
reads with provenance and no implicit persistence), and ADR-024 (connected is
not consulted). Credential/grant rows own scope; provider results are external
evidence; the authenticated account configures/disconnects; the accepted task
and unchanged local transport guards govern invocation. No new ADR or release
claim is asserted. No canonical release-truth/qualification document is advanced.

## Validation

Run from this isolated worktree using the existing Python environment and
`PYTHONPATH=.`; no production datastore is used:

```
python -m pytest tests/connections \
  tests/core/test_knowledge_tool_execution.py \
  tests/core/test_chat_tool_exposure.py \
  tests/core/test_chat_completion_service_tool_loop.py \
  tests/migration/test_github_knowledge_credentials.py -q --disable-warnings
```

**Result: 259 tests passed.** Scoped Ruff and `git diff --check` passed.
Central-file Ruff: 110 baseline diagnostics, 110 current, no new diagnostics
(comparison by file, rule, and message against the preceding commit).

Coverage includes synthetic provider/Command Bus continuation, source reinjection,
flat argument hydration, account/transport override rejection, invalid credentials,
replacement/disconnect, read-only provider scope, and migration upgrade/downgrade
on disposable SQLite with PostgreSQL DDL compilation. This is code/test proof,
not live DeepSeek, live GitHub/Notion, browser, or PostgreSQL race qualification.

A broad Ruff pass on existing central files reports preexisting lint findings;
those unrelated findings are not repaired in this slice. New/changed connector
modules and new tests receive a separate scoped lint pass. Final counts and
commit are in the task closeout.
