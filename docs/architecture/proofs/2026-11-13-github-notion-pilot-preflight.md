# GitHub / Notion read pilots: preflight and bounded Notion follow-through

Date: 2026-11-13. Base: `a01a3400549596692930eb54544d3af7501d2d55`.
Status: **partial implementation, no live connection or Guardian-read qualification**.

## Intended result and ownership

A scoped account connection should allow Guardian to request a useful bounded
read, preserve source identity, and refuse subsequent reads after disconnect.
ADR-071 owns the Connections projection, ADR-075 owns read-only Knowledge
semantics, and ADR-024 distinguishes availability from turn-scoped consultation.
This change belongs in `guardian/connections/notion/`. It does not alter any
accepted authority contract, default profile, schema, or release claim.

## Existing implementation, not a new system

- Notion already has encrypted account-scoped credential storage, configure /
  validate / status / disconnect routes, and search / page-read operations.
- The Notion operations enter the Command Bus manifest as read-only commands.
  That is not proof that ordinary Guardian chat advertises or invokes them.
- Ordinary-chat exposure currently has a fixed allowlist without Notion or
  GitHub knowledge reads (`guardian/tools/chat_exposure.py`).
- GitHub has a legacy issue/PR sync adapter and `/api/connectors` integration.
  This is not an account-scoped Knowledge reader and must not be relabeled as
  one or fed an operator credential as implicit authority for every user.
- Preview's profile is not an authorization to enable these routes. No route
  posture, deployment configuration, or running process was changed.

## Implemented prerequisite repair

The Notion adapter now refuses provider redirects, classifies malformed search
results as a bounded provider failure, caps block traversal at 20 requests, and
rejects missing/repeated pagination cursors. Reads mark `content_truncated`
when block, depth, request, or character limits omit content. Previously depth
and block omissions could be presented as a complete read, and empty paginated
responses were not bounded by the block counter.

Tests also demonstrate that disconnecting another account does not remove the
owner's credential and that the owner's disconnect prevents subsequent search
and read from calling the provider. This is local application disconnect, not
revocation of the integration token at Notion, nor cancellation of an already
in-flight provider request.

## Credential preflight

Only presence of the relevant named keys was reported. The inspected root
VaultNode checkout `.env` and matching local backups have empty `NOTION_API_KEY`
and `GITHUB_TOKEN` fields. No usable credential was imported, printed, copied,
or configured. No remote provider request or production database write occurred.
This is not a claim that no credential exists elsewhere on the machine.

## Remaining work, in dependency order

1. Establish per-account pilot grants and exact scope: initial GitHub repository
   selection and Notion integration-visible pages. Obtain credentials through a
   server-owned path without logging or returning them to the model.
2. Implement the GitHub provider-specific bounded read adapter and credential /
   disconnect seam, separate from legacy sync and without automatic ingestion.
3. Connect eligible pilot operations to ordinary-chat exposure and execution
   with authenticated account custody and rechecks at invocation; a catalog
   entry or connected status is not enough. Preserve Command Bus authority.
4. Qualify source-carrying reads, denial for other accounts, and read-after-
   disconnect refusal against disposable state and then approved live scope.
5. Separately approve deployment posture and perform a controlled rollout.

No automatic provider writes, synchronization, indexing, memory creation,
repository push, merge, or deployment is included. Production data and serving
worktrees remain untouched. This receipt does not close either end-to-end pilot.

## Validation

Using the existing Python environment with `PYTHONPATH=.` directed at the
isolated worktree (not importing the serving checkout):

- Baseline `pytest tests/connections/test_notion_connection.py -q`: 8 passed.
- Changed surface `pytest tests/connections/test_notion_read_bounds.py tests/connections/test_notion_connection.py -q`: 17 passed.
- Broader `pytest tests/connections -q`: 43 passed.
- `ruff check` for the three changed Python files: passed; existing deprecated
  linter-configuration warning remains.
- `git diff --check`: passed.
- Live provider / production / browser / ordinary Guardian chat: not run.
