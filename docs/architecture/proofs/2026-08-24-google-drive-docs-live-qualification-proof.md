# Google Drive / Docs Live Qualification Proof

Proof date: 2026-08-24

## Outcome

**BLOCKED — RUNTIME STARTUP**

The qualifying backend did not become reachable. The dependency services,
migration, graph bootstrap, and embedding-model preparation completed, but the
`backend` service exited with code 3 during the FastAPI lifespan before any
health or authenticated route could be reached. The task therefore stopped
before Google OAuth, provider calls, persistence inspection, Command Bus
invocation, frontend inspection, disconnect, or reconnect.

This is a runtime-startup gate failure, not a conclusion about the Google
Drive / Docs implementation or Google Cloud configuration.

## Source identity

- Worktree: `/private/tmp/codexify-google-drive-knowledge`
- Branch: `codex/implement-google-drive-knowledge-connection`
- HEAD before proof: `362e748d35aa628856bdaa730ae3b594598f2b2f`
- Canonical implementation ancestry (`c3e5c87dfe8236ce903ff86dd41b5c7cfb43d610`): pass
- OAuth configuration-readiness ancestry (`362e748d35aa628856bdaa730ae3b594598f2b2f`): pass
- Working tree before the proof artifact was created: clean.

The local OAuth configuration remained structurally contained before startup:
the local environment file was ignored, untracked, mode 600, and the five
required values were present exactly once without their values being printed.
The configured callback matched the task-required local callback URI.

## Runtime startup attempt

The supported local Compose sequence was used without removing the pre-existing
`worker-watchdog-review` orphan container:

```text
docker compose config --quiet
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d graph-init model-prep backend frontend
```

Results:

| Surface | Result |
| --- | --- |
| Compose configuration | pass |
| Postgres | healthy |
| Redis | healthy |
| Neo4j | healthy |
| Migrator | exit 0 |
| Graph bootstrap | exit 0 |
| Embedding-model preparation | exit 0 |
| Backend | exit 3 during FastAPI lifespan |
| Frontend | not started; waiting on backend health |

The backend completed database readiness, migration-version verification,
default seeding, route registration, and Uvicorn process startup. It then
emitted two Guardian-redacted error events and exited before binding a usable
HTTP surface. The bounded Docker state at the stop point reported
`codexify-backend-1` as `Exited (3)`; no health endpoint could be probed.

## First failing boundary and reproduction

The first failing boundary is the active supported-profile runtime validation
inside backend startup. A disposable, dependency-free backend diagnostic
reproduced the failure without printing any configuration values:

```text
docker compose run --rm --no-deps backend -c '<config coherence probe>'
```

Observed result:

```text
CONFIG_COHERENCE=fail exception_class=LLMConfigError
```

A second bounded diagnostic emitted only mismatch field names:

```text
SUPPORTED_PROFILE_MISMATCH_FIELDS=ALLOW_CLOUD_PROVIDERS,CODEXIFY_LOCAL_ONLY_MODE,LOCAL_BASE_URL
```

Expected result: the active supported-profile contract is satisfied and the
backend remains reachable so that the required health, Connections, Google
provider-specific, and Command Bus routes can be checked.

The application log filter redacted the fatal event text, so no more detailed
message was copied into this receipt. The diagnostics above establish the
reproducible exception class and the three non-secret contract fields without
exposing local environment values.

No implementation or configuration repair was made. The appropriate next
step is a separately scoped reconciliation of the active supported-profile
runtime configuration, followed by a fresh startup gate before attempting
this live qualification again.

## Downstream qualification status

None of the following were attempted because the backend startup gate failed:

- Connections projection before or after authorization;
- Google OAuth start, consent, or callback;
- persisted Google authorization or historical generic-Google reconciliation;
- Google Drive search, Google Docs read, Shared Drive qualification, or proof
  document selection;
- Command Bus search or read execution;
- user-scope, zero-write, content-ingestion, memory, vector, graph, or sync
  persistence checks;
- frontend configured-state or browser-storage checks;
- disconnect, missing-authorization behavior, reconnect, or final usable
  connection state.

Accordingly, no Google content was read, created, changed, imported, or
persisted by this task. No Google authorization interaction was initiated, and
no browser consent action was requested.

## Authority and release boundaries

- ADR impact: aligned with ADR-071, ADR-072, and ADR-075; no new ADR and no
  decision change.
- Connections remains a read-only projection and did not become an execution
  owner.
- Command Bus authority was not bypassed; its route was not reachable.
- OAuth credentials remain local and server-owned; no credential material was
  emitted into this proof or staged for Git.
- No implementation, test, configuration, migration, or protocol-token file
  changed.
- No release classification or `00-current-state.md` claim changed.

## Validation

| Check | Result |
| --- | --- |
| Qualifying implementation ancestry | pass |
| Configuration-readiness ancestry | pass |
| Compose configuration | pass |
| Dependency startup and migration | pass |
| Backend startup | blocked: exit 3 |
| Route availability | not reached |
| Live OAuth and provider qualification | not reached |
| Documentation validation | pass |
| Proof sensitive-material scan | pass; no values present |
| Git diff check | pass |

## Documentation follow-through

This blocker receipt is the only tracked file changed. The Connections
control-plane document remains unchanged because no live provider
qualification was completed.

## Remaining operator work

1. Reconcile the active supported-profile runtime contract at the three
   reported fields, without treating this receipt as authorization to change
   source or local configuration.
2. Restart the backend and repeat the runtime-startup gate from a clean state.
3. Only after that gate passes, perform the live Google OAuth, read-only
   provider, Command Bus, zero-write, disconnect, and reconnect qualification.
4. Google production OAuth verification/security assessment remains separate
   future operator work.
5. Shared Drive live qualification remains unattempted and requires an already
   authorized harmless fixture when the ordinary live qualification can run.
