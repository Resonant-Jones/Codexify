# Chat History Disappearance Boundary Proof (2026-09-03)

## Result

**PROVEN — `data_present_api_filter_mismatch`**

The vanished conversation history is present in the canonical PostgreSQL
database used by the running private-preview Guardian backend. The current
authenticated account owns 66 active threads: 63 Anthropic-origin threads and
3 native Codexify threads. An unfiltered authenticated thread-list request
returns all 66.

The live Guardian sidebar instead requests project 4. That project belongs to
the current account but contains zero threads, so Guardian correctly returns an
empty page and the frontend renders zero thread rows. All 66 current-account
threads point to projects 1 or 3, both still owned by the legacy `local`
principal and therefore omitted from the current account's `/api/projects`
response.

No canonical chat row is proven lost. No runtime database-target drift is
present. The first causal boundary is the disagreement between thread ownership
and project ownership, combined with the persisted project-scoped sidebar
request.

## Scope and preservation

- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `main`
- Pre-proof HEAD: `bc4a334915e90d66380471d8222b7fd702253f08`
- A scheduled documentation automation committed
  `79f92f2a2e42c09b4a7add7f823177fe954ed724` while the proof was running and
  advanced `main`. Its changes to `00-current-state.md` and the architecture
  README were re-read before staging; they do not change this incident
  classification.
- Evidence date: 2026-09-03 (America/New_York)
- Only this proof artifact was created.
- SQL was aggregate/read-only. Message content and thread titles were not
  selected. Project names were reduced to the bounded classes `general-name`,
  `imports-name`, or `other-name`.
- Account identifiers below are non-reversible proof labels formed as
  `account:` plus the first 12 hexadecimal characters of SHA-256. Email
  addresses, tokens, cookies, session identifiers, passwords, and API keys are
  not recorded.
- No import, restore, migration, ownership rewrite, row edit, authentication
  reset, container recreation, alternate-volume mount, or volume mutation was
  performed.
- A pre-existing unrelated staged deletion of the 2026-09-03 development log
  was preserved and excluded from this task.

## Current-truth and historical anchor

The required architecture pre-read establishes PostgreSQL `chat_threads` and
`chat_messages` as canonical conversation state, `user_id` as the ownership
boundary, and `origin_system` as provenance rather than ownership. The account
export/restore contract forbids silent ownership reassignment.

The 2026-08-19 Anthropic runtime proof recorded 63 Anthropic-origin threads and
784 messages under `user_id=local`. That proof used the fresh disposable
Compose project `codexify_anthropic_import_proof_r2_20260819` and explicitly
tore its volumes down after proof. It is therefore a count/provenance anchor,
not evidence that today's private-preview stack should mount that proof volume.

Today's private-preview database contains a 63-thread/784-message Anthropic
population under the current account label. The exact identity of every row
cannot be compared with the disposed proof database because the historical
receipt did not preserve row IDs; this proof therefore claims count and
provenance continuity, not a byte-for-byte row identity comparison.

## Running PostgreSQL authority

The repository-owned private-preview lifecycle resolves the base and overlay
Compose files with project name `codexify_private_preview`. Live labels,
container inspection, a credential-redacted backend target read, and the
resolved Compose model agree:

| Field | Live value |
|---|---|
| Compose project | `codexify_private_preview` |
| PostgreSQL service | `db` |
| PostgreSQL container | `codexify_private_preview-db-1` |
| Image | `postgres:15` |
| Database | `Codexify` |
| Backend database host/port | `db:5432` |
| Backend URL scheme | `postgresql` |
| Mounted volume | `codexify_private_preview_pg_data` |
| Host mount source | `/var/lib/docker/volumes/codexify_private_preview_pg_data/_data` |
| Container destination | `/var/lib/postgresql/data` |
| Mount mode | read/write (inspection only; no writes performed) |
| Database container created | `2026-09-02T10:38:58.527297259Z` |
| Backend container created | `2026-09-02T16:52:15.872508543Z` |
| Active volume created | `2026-07-30T12:21:49Z` |

The resolved Compose model mounts logical volume `pg_data` at
`/var/lib/postgresql/data`, and Docker resolves that logical volume to
`codexify_private_preview_pg_data` for this project. The backend depends on
`db`. This matches the running target; there is no active database or volume
drift.

Other persistent volumes exist, including `codexify_pg_data`,
`codexify-audit_pg_data`, and `codexify_tester_pg_data`. None is mounted by the
private-preview database. They were listed and inspected only for Docker
metadata; they were not attached, mounted, started, copied, or read for data.
Because the active expected volume contains the missing history, none is a
recovery candidate for this incident.

At proof time the database and backend were healthy. An unrelated coding worker
was restarting; it is not on the thread-list read path and was not changed.

## Canonical row presence

The required read-only queries were run inside
`codexify_private_preview-db-1` against its configured database.

### Totals

| Query | Count |
|---|---:|
| `SELECT COUNT(*) FROM chat_threads` | 68 |
| `SELECT COUNT(*) FROM chat_messages` | 792 |

### Ownership and provenance

| Thread owner | `origin_system` | Threads | Messages on those threads |
|---|---|---:|---:|
| `account:a34e2a285020` | `anthropic` | 63 | 784 |
| `account:a34e2a285020` | `codexify` | 3 | 4 |
| `account:4addacfd4ec9` | `codexify` | 2 | 4 |

There are no `local`-owned chat threads in the active database and no
`origin_system IS NULL` threads. Current native-origin semantics use the
canonical value `codexify`, so no substitution was necessary.

### Archive and time bounds

| Thread owner | Active | Archived |
|---|---:|---:|
| `account:a34e2a285020` | 66 | 0 |
| `account:4addacfd4ec9` | 2 | 0 |

| Bound | UTC value |
|---|---|
| Oldest thread | `2026-09-02 10:30:22.242755+00` |
| Newest thread | `2026-09-02 16:56:23.749592+00` |
| Most recent update | `2026-09-02 16:56:23.782069+00` |

The prior 63-thread Anthropic count exists, now under
`account:a34e2a285020`; 5 native Codexify threads also exist across two account
owners. Absence from the UI is therefore not canonical absence.

## Project ownership mismatch

The project/thread join exposes the decisive ownership split:

| Project | Project owner | System role | Bounded name class | Attached threads | Cross-owner threads |
|---:|---|---|---|---:|---:|
| 1 | `local` | `general` | `general-name` | 4 | 4 |
| 2 | `account:4addacfd4ec9` | `<NULL>` | `other-name` | 1 | 0 |
| 3 | `local` | `<NULL>` | `imports-name` | 63 | 63 |
| 4 | `account:a34e2a285020` | `<NULL>` | `other-name` | 0 | 0 |

The current account's three native threads point to project 1. Its 63
Anthropic threads point to project 3. Project ownership never moved with thread
ownership: all 66 are cross-owner project links. The current account can list
only project 4, which contains no threads.

## Current request/account scope

Private-preview `get_request_user_scope()` derives `user_id`, `subject_id`, and
`account_id` from the approved authenticated principal and enables multi-user
enforcement. `_scope_query_user_id()` then forces thread-list reads to the
authenticated account and rejects a mismatched requested `user_id`.

The current browser/account posture was correlated to
`account:a34e2a285020` without recording the raw account identifier:

- all 13 current durable account-import jobs, including the most recent job at
  `2026-09-03 02:04:51.347983+00`, have that owner label;
- a 120-second proof-only session for that same approved principal was used for
  one bounded, read-only API comparison and immediately revoked;
- no existing browser credential or session store was read or changed.

## Authenticated API proof

Using the current account scope through the repository-owned private-preview
origin:

| Request | HTTP | Returned threads | Owner distribution | Origin distribution |
|---|---:|---:|---|---|
| `GET /api/chat/threads?limit=200` | 200 | 66 | `account:a34e2a285020=66` | `anthropic=63`, `codexify=3` |
| `GET /api/projects` | 200 | n/a | one visible project: ID 4 | no `general` system-role project visible |

The unfiltered thread response reported `limit=200`, `offset=0`,
`next_offset=66`, `has_more=false`, with 66 active and 0 archived threads. It
contained no caller-supplied project, origin, archive, or user filter.

The live signed-in Guardian page was then opened at `/chat`. Its actual browser
requests, observed at the private-preview Nginx origin, were:

```text
GET /api/projects                                           -> 200
GET /api/chat/threads?limit=50&offset=0&project_id=4       -> 200
GET /api/chat/threads?limit=50&offset=0&project_id=4       -> 200
```

The project-scoped response returned zero threads, and the rendered sidebar
contained zero thread tiles. The browser supplied `limit=50`, `offset=0`, and
`project_id=4`; it supplied no origin, archived, or user filter. The duplicate
GET is a repeated load of the same scope, not evidence of two different
projections.

This comparison locates filtering before frontend presentation: the API returns
zero for the browser's project-scoped request, while the same account's
unfiltered API returns 66. The frontend did not receive 66 rows and then discard
them in this observed path.

## Code-path trace

1. `guardian/core/dependencies.py:get_request_user_scope` maps a private-preview
   principal to one multi-user account scope.
2. `guardian/routes/chat.py:chat_list_threads` forces that account through
   `_scope_query_user_id` and passes optional `project_id` and `origin_system`
   filters to PostgreSQL.
3. `guardian/core/pgdb.py:list_chat_threads` applies exact conjunctions for
   `ct.user_id`, `ct.project_id`, and `ct.origin_system`. It does not apply an
   archive filter.
4. `guardian/routes/projects.py:list_projects` filters projects by their own
   owner before returning them to a multi-user caller. That correctly hides
   legacy-`local` projects 1 and 3 from the current account.
5. `GuardianChatWithSidebar` initializes `selectedProjectId` from the persisted
   `cfy.lastProjectId` browser preference. Its thread loader treats that
   selection as authoritative and sends it as `project_id`.
6. In the observed browser, that persisted selection is project 4. The API
   returns an empty page because project 4 has no threads. The sidebar's later
   archive/project/origin projection receives an empty input.

There is a secondary API robustness hazard: `chat_list_threads` catches an
unexpected database exception and returns a successful empty result. It did not
fire here; the project-4 query is valid and its empty result matches direct SQL.
It is not the causal boundary for this incident.

## Theory disposition

| Theory | Disposition |
|---|---|
| Rows still exist under a different thread owner | Rejected as primary: 66 missing rows already belong to the current account. |
| Thread-list/project filter hides rows | **Proven primary boundary:** live UI requests empty project 4. |
| Frontend receives rows and discards them | Rejected for the observed path: scoped API itself returns zero. |
| Different PostgreSQL database/volume | Rejected: live backend, Compose model, container mount, and expected named volume agree. |
| Rows deleted/lost | Rejected: 68 threads and 792 messages remain, including the 63/784 Anthropic population and five native threads. |
| Other proven boundary | Secondary: thread owners and linked project owners are inconsistent across all 66 current-account history rows. |

## Classification and smallest safe next task

Primary classification: **`data_present_api_filter_mismatch`**.

The first causal boundary is a stale/empty project scope applied by the browser
to rows whose linked projects are invisible under current account ownership.
The underlying durable inconsistency is cross-owner project linkage, not a
missing account-import payload and not a missing PostgreSQL volume.

The smallest safe next task is a separately approved ownership-reconciliation
task that defines and tests the migration contract for legacy `local` General
and Imports projects and their current-account thread links. It must decide the
authoritative account mapping, preserve provenance, be idempotent and auditable,
and prove that no other account gains visibility. A bounded UI hardening task
may separately clear or reject a persisted project selection that is absent
from the authenticated project list, but that would only remove the immediate
empty-scope symptom; it would not repair the cross-owner project invariant.

No repair was performed here.

## ADR impact

`No ADR impact`.

This proof changes no persistence, identity, authority, ownership, project,
thread-list, or frontend semantics. Any ownership reconciliation or UI/API
repair requires its own task and architecture review.

## Documentation follow-through

- `docs/architecture/00-current-state.md`: unchanged.
- Architecture contracts: unchanged.
- ADRs and ADR index: unchanged.
- Release claims: unchanged.
- Implementation documentation: deferred to the separately approved repair.

## Validation record

Required source searches, the repository-owned private-preview Compose
inspection, relevant container/volume inspection, all read-only SQL queries,
the authenticated unfiltered API probe, and the rendered live sidebar request
were completed. Documentation validation, `git diff --check`, and final scoped
Git-state verification are recorded in the task closeout after this artifact is
validated and committed.
