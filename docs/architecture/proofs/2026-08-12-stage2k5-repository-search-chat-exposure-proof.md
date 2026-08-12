# Stage 2K.5 Repository Search Ordinary-Chat Exposure Proof

## Date

2026-08-12

## Verdict

PASS — bounded repository search is exposed only in the supported local single-user ordinary-chat lane after Guardian resolves thread-owned binding authority.

## Diagnostic Outcome

REPOSITORY_SEARCH_CHAT_EXPOSURE_ESTABLISHED

## Base Commit

`18b8640703237482f47f2681d0d33f3753a8e561`, verified `origin/main` at task start.

## Branch/Worktree

- Branch: `codex/stage2k5-repository-search-chat-exposure`
- Worktree: `/private/tmp/codexify-stage2k5-repository-search-chat-exposure`

## Governing ADRs

ADR-065 is primary; ADR-005, ADR-020, ADR-024, ADR-061, and the existing bounded provider-tool contracts remain preserved.

## ADR Impact

Aligned with existing ADRs. No ADR, authority contract, auth/session module, Command Bus core, provider adapter, schema, or migration changed.

## Stage 2K.1 Prerequisite

`tests/core/test_repository_authority.py` passed; ownership, one-active-binding cardinality, exact Git root, and stale/ambiguous failure behavior remain unchanged.

## Stage 2K.2 Prerequisite

`tests/core/test_repository_discovery.py` passed; discovery remains non-authorizing.

## Stage 2K.3 Prerequisite

`tests/core/test_repository_import.py` and `tests/routes/test_project_repository_import.py` passed; import remains explicit and is not invoked by chat.

## Stage 2K.4 Prerequisite

The 34-test Stage 2K.4 search core, route, and manifest suite passed; `op::repository.search` remains GET/read/read_only/safe/no-approval.

## Current Truth Before

Automatic ordinary-chat exposure was health-only; ChatCompletionTask held account/thread identity but no Project, root, binding, or queued request credential.

## Ordinary Chat Boundary

Repository search requires no Hosted Room invocation, positive thread ID, task account, and exact base origin `api:chat.complete`; other origins remain suppressed.

## Current-Thread Project Resolution

The new resolver loads only the exact current thread, checks its owner against the task account, and returns frozen context containing only positive `project_id`.

## RepositoryBinding Eligibility Proof

It opens one non-committing SQLAlchemy session and calls Stage 2K.1 with task account plus thread Project. Missing, stale, ambiguous, or cross-account authority returns no context.

## Local Single-User Auth Transport Boundary

Eligibility requires non-preview local auth, disabled multi-user mode, canonical single-user task identity, and one currently accepted local Guardian API key.

## Remote/Multi-User Deferral

Remote/multi-user ordinary-chat repository search remains intentionally fail-closed because the queued ChatCompletionTask does not carry an accepted delegated user credential for authenticated loopback replay. Stage 2K.5 does not invent one.

## Hosted Room Suppression

Any populated `hosted_room_invocation` suppresses repository search for both owner and guest paths.

## Command Identity

The only projected command is existing `op::repository.search`, alias `route::GET::/api/projects/{project_id}/repository/search`, operation ID `repository.search`.

## Model Tool Projection

The fixed model schema exposes required `q` and optional `limit` only, using Stage 2K.4 imported limits of 256 characters and 20 results.

## Project-ID Non-Exposure

No Project ID, binding ID, canonical root, repository root, cwd, mount, account field, or credential appears in schema, provider tools/messages, toolExposure, payload summary, result, or trace.

## Guardian-Side Argument Hydration

Guardian rejects every key except q/limit, then injects the freshly derived Project ID only into InvokeArguments path parameters with query q/limit, empty headers, and no body.

## Pre-Dispatch Authority Revalidation

Before dispatch, Guardian requires the private advertised context, rechecks transport, re-resolves thread/Project/binding, and requires the same Project ID; loss uses existing `tool_command_blocked`.

## Thread-Move Fail-Closed Proof

Mocked execution and disposable Postgres coverage move a thread from a bound Project to a repository-less Project; no old or new Project is silently searched.

## Binding-Staleness Fail-Closed Proof

The disposable Postgres proof moves the fixture worktree; the existing binding resolver rejects it and capability resolution returns no context.

## Command Bus Delegation

Repository search alone uses system actor request/tool-turn identity with `delegated_by=task.user_id` and `auth_subject=task.user_id`; existing actor validation accepts the bounded delegation.

## Credential Non-Persistence

The local key occurs only in the ephemeral `execute_invoke` inbound X-API-Key header. Tests prove absence from task serialization, tools, schema, arguments, provenance, idempotency, continuation, summary, result, and trace.

## Command Bus Invocation Proof

One mocked DeepSeek decision dispatched exactly one repository search with Guardian path Project 42, q `_prepare_chat_tool_exposure`, limit 5, empty InvokeArguments headers, no body, and ephemeral loopback transport auth.

## Tool Result Reinjection

The bounded Command Bus result was reinjected through the existing continuation seam; the second model attempt received no Project identity or absolute root and returned the final answer.

## One-Command Limit Proof

The existing second-tool-decision `tool_turn_limit_reached` behavior remains unchanged; one Command Bus invocation remains the maximum.

## Existing Health Regression

Existing health exposure and one-command execution tests pass unchanged, and repository eligibility failure leaves health available.

## DeepSeek Exposure Proof

Eligible DeepSeek receives health then repository search only when local transport and current thread/binding authority pass.

## Whoosh'd Exposure Proof

Only the existing eligible exact Whoosh'd target receives health then repository search; qualification logic is unchanged.

## Unsupported Provider Suppression

OpenAI, Groq, and non-Whoosh'd local providers gain no automatic tool.

## Manual Tool Bypass Denial

Manually supplied repository.search is removed before dispatch; unrelated explicit tools stay unchanged without repository context.

## Database Read-Only Proof

The disposable Postgres proof records Project, binding, thread, ORM state, and row counts before/after resolution and proves no changes.

## Repository Mutation Denial

Capability resolution invokes only Stage 2K.1 validation; it does not read search internals, mutate Git, or mutate a repository.

## Model Authority Isolation

Source and behavior checks found no cwd, nearest-Git, worktree environment, discovery, legacy fs.search, direct repository search, or provider-selected Project/root authority path.

## Worker Parity

`guardian/workers/chat_worker.py` remains unchanged and consumes the same preparation dict; private context stays in memory and is excluded by the existing serialization allowlist.

## Alembic Head Result

Before and after this no-schema slice, the sole Alembic head is `6e2b9c4a7d1f`.

## Core Test Results

`tests/core/test_repository_chat_capability.py` plus `tests/core/test_chat_tool_exposure.py` — 75 passed.

## Postgres Integration Result

`tests/integration/test_repository_chat_capability_postgres.py` — 1 passed against a dedicated loopback-only disposable PostgreSQL 15 container and unique database; both were removed.

## Stage 2K.1 Regression Results

Stage 2K.1 authority plus Stage 2K.2 discovery regression set — 71 passed.

## Stage 2K.2 Regression Results

The Stage 2K.2 discovery portion of that 71-test regression set passed.

## Stage 2K.3 Regression Results

Stage 2K.3 import plus Project account-scope set — 41 passed.

## Stage 2K.4 Regression Results

Stage 2K.4 search set — 34 passed.

## Command Bus Regression Results

Manifest, invoke, and tool-turn observability regressions — 34 passed.

## Architecture Test Results

`pytest -v tests/architecture` passed after this receipt was added.

## Docs Validation

`python3 scripts/validate_docs.py` and `make docs PYTHON=python3` passed, including diagram freshness.

## What Was Proven

On the supported local single-user ordinary-chat path, Codexify now advertises op::repository.search only when the authenticated current thread resolves one owned Project with one valid active RepositoryBinding; the model supplies only q/limit, Guardian revalidates and injects Project identity at dispatch time, Command Bus executes the existing bounded read-only search, and no repository root or Project authority is model-controlled.

## What Was Not Proven

- No remote multi-user or private-preview ordinary-chat repository-search execution was enabled.
- No delegated session/JWT transport or browser/session credential queueing was created.
- No Hosted Room repository-search exposure, live provider repository search, or supported-runtime replay was performed.
- No second repository command, file-read-by-path command, repository write, or multi-command repository loop exists.
- No repository mutation, Workspace authority change, provider inference, or supported-runtime restart occurred.

## Documentation Follow-Through

This receipt is the authorized documentation follow-through; governing ADR and authority/auth contracts remain unchanged.

## Final File Scope

Exactly seven files: resolver, exposure policy, completion seam, two focused core tests, disposable Postgres proof, and this receipt.

## Commit

Pending final architecture, documentation, and cached-diff validation.
