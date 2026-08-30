# ADR-076: Archive Before Delete and Built-In Project Roles

**Status:** Accepted

**Date:** 2026-08-30

## Context

Projects are durable ownership and grouping boundaries for conversations and
documents. The existing implementation identified the `General` default by its
display name and allowed Project deletion to eject threads before the delete
operation had been proven valid. That made presentation text carry structural
authority and left no reversible lifecycle gate before permanent removal.

`General` and `Imports` have structural responsibilities that must survive a
rename. Ordinary Projects still need a usable deletion path, but permanent
removal must be deliberate and must not begin by mutating contained threads.

## Decision

Projects gain two durable lifecycle fields:

- `system_role`, nullable for ordinary Projects and constrained to `general` or
  `imports` for built-in containers;
- `archived_at`, nullable for active Projects and populated for archived
  ordinary Projects.

At most one non-null role may exist per owning user and role. Migration
backfill assigns roles only to the existing exact canonical `General` and
`Imports` rows. It preserves Project IDs and all existing membership and does
not infer roles from provider, import, thread, or document metadata.

The Project name remains editable presentation. Renaming a built-in Project
does not change its role, and default-Project resolution uses `system_role`
before retaining a name-based compatibility fallback for pre-migration data.

Built-in Projects may be renamed but may not be archived, restored, or
deleted. Ordinary Projects follow this lifecycle:

```text
active -> archived -> active
           |
           -> permanently deleted
```

Permanent deletion is accepted only for an archived ordinary Project. Both
the HTTP route and core persistence layer enforce this rule. Thread ejection
to the canonical General Project and Project deletion occur in one database
transaction after lifecycle validation, so a rejected deletion has no
containment side effect.

The frontend exposes lifecycle actions from each Project tile. Active ordinary
Projects offer rename and archive; archived ordinary Projects offer rename,
restore, and delete; built-in Projects offer rename only. Archived Projects
remain visible. If the selected Project is archived, the UI returns to the
canonical General Project while preserving the archived row for later restore
or deletion.

## Consequences

Project structural identity is no longer coupled to a mutable label. Archive
is a reversible state and the required safety gate for deletion. Consumers of
the Project list must preserve `system_role` and `archived_at` through API and
cache normalization.

Deletion still moves contained threads to General; it does not delete those
threads. Backups are an operational concern and are not guaranteed by this
lifecycle contract.

## Rejected alternatives

- **Keep name-based built-in identity.** Rejected because rename would alter
  structural authority.
- **Allow immediate deletion.** Rejected because it has no reversible intent
  boundary and can begin containment mutation before validation.
- **Hide archived Projects.** Rejected because users need a reachable restore
  and permanent-delete surface.
- **Infer built-in roles from provenance.** Rejected because presentation and
  import metadata are not Project authority.

## Proof and release boundary

Focused core, route, cache, and sidebar tests prove lifecycle enforcement and
per-tile actions at the code path. The migration is inspected through the
single Alembic head. No production migration or live Compose qualification is
performed by this task. `docs/architecture/00-current-state.md` remains
unchanged and authoritative for release truth.
