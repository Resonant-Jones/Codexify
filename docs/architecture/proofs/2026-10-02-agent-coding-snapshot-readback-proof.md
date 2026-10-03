# Agent/Coding Snapshot Readback: Adopted Destination Proof

## Frozen lineage and authority

- Date: 2026-10-02.
- Lane: architecture-impact; bounded prerequisite adoption and proof.
- Task: user-supplied **Adopt and Qualify Agent/Coding Snapshot Readback**.
- Destination baseline: `590e9ac9f11b4a5f7fa8b153ee0a76074eff04ff`, the
  clean approved PR #848 lineage. GitHub's open PR head and protected checkout
  both matched this SHA before editing.
- Frozen implementation source: `39a0d4867b245fa40fffa141a82b7ba08eb4dd8c`.
- Accepted matrix source: `3cc1aed8808467cf22169ba38ad98e92e4351450`;
  original accepted matrix blob: `1134e623a782e4aa3d7534fc40492ae235ee0188`.
- Adopted reader commit: `a352c088a0d9fd68edabf28ae53dbbf40f80595d`.
- Branch: `codex/adopt-agent-coding-snapshot-readback`.
- Worktree: `/Volumes/Dev_SSD/offload/codex/worktrees/adopt-agent-coding-snapshot-readback/Codexify-main`.
- Evidence: mounted actual routers/dependencies, real signed/stored account
  sessions, and disposable PostgreSQL resource authority. Session mapping
  uses isolated memory Redis; event access is a forbidden spy.
- Release/public-ingress posture: **HOLD**. No deployed ingress, browser,
  provider execution, full Guardian startup, or supported-Compose proof.

The [accepted matrix](../task-event-ingress-matrix.md) keeps agent/coding
`MOVE` to dedicated snapshots and public dedicated agent SSE quarantined.
Generic public task SSE is chat-only, but its runtime correction and #848's
three credential P2 repairs are outside this adoption task.

The adoption used a reviewed four-file patch from the approved destination
baseline to the frozen implementation source, not a complete cherry-pick.
All four adopted file contents equal the source blobs. Source ancestors
changed no corresponding runtime files between `590e9ac9` and `aab4edf9`.
The amended source branch tip `ae07ea30` and its eight unrelated file
differences were excluded. The reader commit contains the same runtime/test
bytes exercised by the fresh run below. Subsequent follow-through is docs only.

## Selected file and hunk scope

| File | Adopted scope |
| --- | --- |
| [AgentStore](../../../guardian/agents/store.py) | Account-specific durable run/deployment/thread lookup; owner-authorized thread list; account snapshots use that authority instead of memory/internal projection. |
| [Agent routes](../../../guardian/routes/agent_orchestration.py) | Resolved account string for snapshots and three thread-list URLs; public/remote/preview dedicated-SSE denial before lookup/Redis; execute docstring directs polling to `/coding`. |
| [Adjacent route tests](../../../guardian/tests/routes/test_agent_orchestration_events.py) | Memory-only account reads denied; internal bounded projection remains distinct from account authority. Existing local stream and execution/control tests retained. |
| [PostgreSQL tests](../../../tests/integration/test_agent_coding_snapshot_readback_postgres.py) | Disposable PostgreSQL fixture and 71 mounted-router authority/denial cases, without auth dependency overrides. |
| Matrix, architecture README, this proof | Accepted policy retained; destination evidence and discovery pointer updated. Missing investigation/packet documents remain explicit frozen-source references, outside this seven-file allowlist. |

No generic-task authorization, credential-boundary, guest invitation, schema,
migration, queue, worker, frontend, cancellation, intake, or execution policy
was changed. No new authority mapping, credential purpose, route, protocol
token, or ADR was introduced. Local snapshot readers deliberately require
durable authority; local legacy SSE generation and credential behavior remain
unchanged and unqualified as public ingress.

## Qualified authority and fresh results

The adopted snapshot implementation required an exact `AgentRun.run_id`, a
surviving canonical `ChatThread` owned by that account, consistent
run/deployment/thread links, and typed deployment metadata. Its test set did
not construct an operator-created deployment with metadata deliberately
matching an account coding run. The statement that metadata could not grant
ownership was therefore not proven against that actor-controlled shape; the
follow-up below records the discovered limitation and the durable correction.

| Fresh destination evidence | Observed result |
| --- | --- |
| Owner admission at five read URLs | HTTP 200; exact durable run/thread returned through real account credentials. |
| Account B and forged `X-User-Id` | Existence-hiding HTTP 404 for account A's snapshots and thread lists. |
| Missing, operator token/key, guest, mixed guest-selector credentials | HTTP 401 or canonical mixed HTTP 400 before PostgreSQL resource lookup. |
| Unknown run and queue/coding/attempt correlation IDs | HTTP 404; no alias authority. |
| Missing/empty/conflicting metadata, null thread, operator-only shape, mismatched lineage | Individual reads denied; owned-thread lists omit ineligible runs. |
| Actual thread deletion/current owner change | HTTP 404; real PostgreSQL foreign-key deletion and current canonical owner exercised. |
| Memory-only authority and database failure | No successful account read or event fallback. Memory reads 404; simulated database failure returns generic 500 with no run disclosure. |
| Public dedicated SSE: owned and unknown runs | HTTP 404 under remote, public allowlist, private preview, and unknown-mode fail-closed posture; zero database lookups and zero event reads. |
| Stored coding result | Existing path-bounded projection preserved. |
| Local legacy SSE | Existing terminal-event framing test passed; local generator code is unchanged. This is focused legacy preservation, not public streaming qualification. |

Unknown or foreign threads return 404; an owned thread with no eligible runs
returns an empty list. Threadless/operator-created shapes gain no account
read entitlement by implication. Internal no-account store projection remains
available to internal callers; HTTP callers cannot select it through an empty
or omitted account value.

## Fresh destination validation

Run from the adopted worktree root, using the validated repository interpreter:

```bash
AGENT_SNAPSHOT_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:59642/agent_snapshot_proof \
PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v \
  tests/integration/test_agent_coding_snapshot_readback_postgres.py \
  guardian/tests/routes/test_agent_orchestration_events.py \
  tests/identity/test_operator_route_auth_migration.py \
  tests/identity/test_account_purpose_strict_migration.py
```

Result: **121 passed, 34 warnings, 13.04 seconds**: 71 PostgreSQL cases,
18 adjacent route cases, 17 operator migration cases, and 15 account-purpose
cases. All required suites were rerun here; historical source results were
not used to substitute for destination execution. The local log is
`/private/tmp/agent-snapshot-adoption-qualification.log`; it is supporting
execution output, not a portable repository authority. The observed port is
an ephemeral allocation, not application configuration.

The dedicated `postgres:15` container
`codexify-agent-snapshot-adoption-proof-20261002` uses loopback-only publication
and tmpfs data. Its fixture accepts only the named `agent_snapshot_proof`
database and creates/drops unique schemas using existing ORM tables and their
foreign-key closure. It never uses application `DATABASE_URL`. This is not a
full schema/migration qualification. The post-run schema count was zero. This task's container was removed by its
recorded container ID; a filtered container inventory confirmed its absence.
No shared database or volume was modified.

The new PostgreSQL test file passes Ruff. Whole-file Ruff retains exactly
five pre-existing findings compared with `590e9ac9`: duplicate
`store_coding_result`, one unnecessary f-string, and unused `subprocess`,
`CodingAgentResult`, and `CodingExecutionTask` imports. The comparison
normalizes shifted line references in diagnostic text; no new finding exists.
No unrelated lint repair was adopted.

`python3 scripts/validate_docs.py` passed. All 40 local Markdown links and
the six complete matrix rows passed validation. The accepted consumer,
surface, identifier, principal lane, authority, and disposition cells match
`3cc1aed88`; only destination evidence/metadata and frozen-source references
were reconciled. The local legacy SSE generator is byte-identical to
`590e9ac9`. Diff checks passed; verify staged scope before closeout. All four
adopted runtime/test blobs remain equal to `a352c088a` and the frozen source.
The protected PR #848, original matrix, snapshot source, acceptance-plan,
and primary checkout refs/status were unchanged in the post-run comparison.
GitHub also retained the approved open PR head. Simplify advanced outside this
task from `2f01c44b` to `3da09443`, with concurrent status changes; all three
initially pending file contents still matched their SHA-256 hashes. No write,
stage, checkout, stash, reset, or cleanup was performed in Simplify, and no
concurrent change was restored or overwritten.

## Historical provenance and limits

The original source proof is preserved at
`39a0d4867b245fa40fffa141a82b7ba08eb4dd8c:docs/architecture/proofs/2026-10-02-agent-coding-snapshot-readback-proof.md`.
It recorded an earlier 121-test result on the source branch; its results and
ephemeral port are historical. The ingress investigation is at that commit's
`docs/architecture/proofs/2026-10-02-agent-coding-ingress-contract-investigation.md`.
The acceptance packet is at
`3cc1aed8808467cf22169ba38ad98e92e4351450:docs/architecture/pr848-ingress-acceptance-and-integration-plan.md`.
Use `git show <commit>:<path>` for those frozen local source records; this
task does not imply that source commits have been published remotely.

[ADR-020](../adr/020-guardian-mediated-coding-agent-execution-contract.md)
retains Guardian intake and lineage ownership.
[ADR-091](../adr/091-durable-chat-completion-attempt-authority.md) and
[ADR-092](../adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md)
remain unchanged, as does [current release truth](../00-current-state.md).
This proof qualifies only the adopted snapshot-reader prerequisite. PR #848
remains at its protected reviewed SHA and HOLD. No push, merge, deployment,
generic-SSE P1 repair, or credential P2 repair is performed here.

Resume PR #848 under the accepted chat-only P1 plus the three remaining
credential P2 corrections.

## Follow-up — durable account-run provenance

- Follow-up date: 2026-10-03.

### Limitation found at PR #848 starting SHA

At `5fa5ac64a9beec0990a79ba31cf3c6b929268c5c`, an authenticated operator could
create a deployment on an account-owned canonical thread and supply matching
`spec_json.user_id`, `coding_task_id`, and integer `source_thread_id`, then
start a run. Before the correction, an account request to
`GET /api/agents/runs/{run_id}/coding` returned HTTP 200 for that
operator-created run. The red regression is
`test_operator_metadata_spoof_has_no_account_read_entitlement` in the
PostgreSQL snapshot test file; its pre-fix failure output was retained at
`/private/tmp/pr848-agent-run-account-provenance/red-exploit.log` as a local
execution receipt. This corrects the earlier proof's untested assumption; it
does not rewrite the historical 121-case result.

### Persisted origin and authority rule

`AgentRun.account_origin_user_id` is a nullable `String(255)` provenance
column, added by migration `7fcd8ca51401` (`7fcd8ca51401_add_agent_run_account_origin_user_id.py`),
whose parent was the sole migration head `8d41a0c2b7ef`. The migration has no
backfill, default, foreign key, or ownership-lifecycle behavior. Existing rows
remain `NULL` because their metadata cannot establish trusted account-intake
origin.

Only `POST /api/agents/coding/execute` supplies the authenticated
`resolved_user_id` to `AgentStore.create_run`. The store parameter defaults to
`None`; the operator deployment/run route cannot set it, and
`AgentRunStartRequest` rejects an attempted top-level provenance field. An
operator may still put similarly named values in arbitrary deployment
metadata, but those values leave the run column `NULL` and grant no account
read entitlement.

Account snapshot and thread-list reads now require exact equality between the
requesting account and `AgentRun.account_origin_user_id`, in addition to the
existing surviving canonical-thread ownership, run/deployment/thread
consistency, and typed lineage checks. The new field is provenance, not a
replacement owner-of-record relation.

### Follow-up proof

| Evidence | Result |
| --- | --- |
| Red operator-created, metadata-perfect run at starting SHA | Account coding snapshot incorrectly returned HTTP 200 before the fix. |
| Actual authenticated account coding intake, including conflicting body `user_id` and `account_origin_user_id` values | Exact authenticated account ID persisted; owner snapshot and all thread-list routes returned the run; foreign account read returned 404. |
| Actual operator deployment/run with forged user, coding task, source thread, and similarly named origin metadata | Operator deployment and run creation remained successful; persisted origin was `NULL`; exact read and coding snapshot returned 404; all owner thread-list routes omitted the run. An attempted run-body origin field returned 422. |
| Existing thread deletion/owner-change and inconsistent lineage cases | Continued to fail closed under the persisted-origin predicate. |
| Snapshot/quarantine and route regression aggregate | 123 passed, 34 warnings, including the PostgreSQL authority tests, 18 orchestration route tests, and adjacent operator/account-purpose migration tests. |

Migration proof used a disposable PostgreSQL 15 database. Alembic had one
head (`8d41a0c2b7ef`) before the new revision and one head
(`7fcd8ca51401`) afterward. A pre-migration `AgentRun` was inserted before
upgrading; afterward the new column was nullable `VARCHAR(255)` and the row
remained `NULL`. Downgrade removed only the column and retained the row;
re-upgrade restored the column without backfill. The database ran on a
loopback-only, tmpfs-backed disposable container and was not an application
database.

Ruff comparison against the frozen starting SHA found no new diagnostics; the
same five pre-existing findings remain. The modified PostgreSQL test file and
new migration are formatter-clean; the three production files have the same
pre-existing formatter status as the starting SHA.

An additional local run of the broader worker files produced 12 failures and
66 passes. The first failure is an undefined `_fetch_campaign_attempts` test
helper in the unchanged `guardian/tests/workers/test_coding_worker.py`; the
worktree-isolation cases also did not reach their expected terminal state.
Those worker files and implementations are outside this task's authority seam
and were not modified. The scoped snapshot/route/auth aggregate and the
disposable PostgreSQL delegation-delivery contract suite passed separately
(15 passed). This worker-suite result is retained as a known local limitation,
not attributed to account-run provenance.

The exact implementation commit SHA is recorded here after commit and before
publication. This follow-up does not change ADR-020, ADR-091, ADR-092, or
ADR-097; it does not resolve either provenance or batching review threads,
change SSE/queue/event behavior, qualify deployed ingress, or alter HOLD.
