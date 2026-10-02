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

Account reads require an exact `AgentRun.run_id`, a surviving canonical
`ChatThread` owned by that account, and consistent run/deployment/thread links.
Deployment metadata corroborates ownership: nonempty string account and
coding task IDs plus an exact integer source thread ID. Metadata cannot grant
ownership, and boolean/float/string thread-ID aliases are rejected.

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
