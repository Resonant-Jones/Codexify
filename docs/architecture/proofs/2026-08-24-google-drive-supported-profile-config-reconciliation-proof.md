# Google Drive Supported-Profile Configuration Reconciliation Proof

Proof date: 2026-08-24

## Outcome

**BLOCKED — BACKEND STARTUP**

The three supported-profile configuration mismatches from the prior Google
Drive qualification receipt were reconciled in the authorized ignored local
environment file. Compose resolution and the bounded configuration-coherence
probe both passed with zero supported-profile mismatches. The Compose-managed
backend nevertheless exited with code 3 before binding HTTP, so this task
stopped before route checks and before all Google activity.

This receipt establishes that the original supported-profile mismatch is no
longer the blocking boundary. It does not establish a healthy backend or a
Google Drive / Docs live qualification.

## Source identity

- Worktree: `/private/tmp/codexify-google-drive-knowledge`
- Branch: `codex/implement-google-drive-knowledge-connection`
- HEAD before task: `62ffc307dc8337ed25e5791648337d8b5b8b7031`
- Canonical implementation ancestry (`c3e5c87dfe8236ce903ff86dd41b5c7cfb43d610`): pass
- OAuth configuration-readiness ancestry (`362e748d35aa628856bdaa730ae3b594598f2b2f`): pass
- Prior live-blocker receipt ancestry (`62ffc307dc8337ed25e5791648337d8b5b8b7031`): pass
- Tracked worktree before this proof artifact: clean.

## Prior blocker

The preceding live-qualification attempt reached FastAPI lifespan and then
exited with code 3. Its bounded configuration probe reported `LLMConfigError`
and exactly these supported-profile mismatches:

- `ALLOW_CLOUD_PROVIDERS`
- `CODEXIFY_LOCAL_ONLY_MODE`
- `LOCAL_BASE_URL`

No OAuth, provider API, or Command Bus Google operation was attempted in that
prior receipt.

## Local configuration reconciliation

Only the three task-authorized, non-secret local semantic values were changed:

| Key | Pre-repair | Final required value | Occurrences after repair |
| --- | --- | --- | --- |
| `ALLOW_CLOUD_PROVIDERS` | `true` | `false` | 1 |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` | `true` | 1 |
| `LOCAL_BASE_URL` | host-local endpoint | `http://host.docker.internal:8000/v1` | 1 |

The ignored local environment file remains mode 600, Git-ignored, untracked,
and unstaged. No Google OAuth value, Guardian API credential, database
credential, or other secret was printed or included in this receipt.

Structural checks after the edit confirmed that the five required Google
runtime fields remain present, nonempty, and single-occurrence. The Google
callback remains the task-required local callback URI. The required existing
local-provider fields also remained semantically compatible with the active
profile, including local provider selection, empty egress allowlist,
`whooshd-mlx` runtime preset, local API placeholder, compatibility-first mode,
and the Whoosh'd provider identity.

## Compose resolution and coherence

The following Compose validation passed:

```text
docker compose --env-file .env config --quiet
```

The bounded resolved backend inspection reported:

```text
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_LOCAL_ONLY_MODE=true
LOCAL_BASE_URL=http://host.docker.internal:8000/v1
```

The same bounded backend diagnostic used for the original blocker then
reported:

```text
CONFIG_COHERENCE=pass
SUPPORTED_PROFILE_MISMATCH_COUNT=0
```

## Backend startup result

The existing local dependencies were inspected first. Postgres, Redis, and
Neo4j were healthy; the prior graph bootstrap and model preparation remained
complete. The supported Compose backend restart was then run:

```text
docker compose up -d backend
```

Compose performed its ordinary dependency ordering, including idempotent
graph bootstrap and migration containers, which both exited 0. The backend
then initialized database readiness, migration-version verification, default
seeding, route registration, and local embedder construction. It exited with
code 3 before an HTTP listener became available.

Bounded backend logs showed the same two redacted error events after embedder
initialization. Their exception message and class were suppressed by the
runtime log filter, so this proof does not assign an unsupported root cause.
The first observable failing boundary is therefore the Compose-managed backend
process after configuration coherence and shared-service initialization.

A disposable direct lifespan probe, using the same Compose backend service
configuration but no network listener, completed its lifespan successfully.
That confirms the three profile fields are no longer the immediate failure;
it does not override the observed failure of the actual Compose-managed
backend service.

## Reachability and route readiness

| Required surface | Result |
| --- | --- |
| Backend service remains running | blocked: exited 3 |
| FastAPI lifespan in Compose-managed service | blocked before usable HTTP |
| `GET /health` | no HTTP response; connection refused |
| `GET /health/chat` | not reached |
| `GET /api/health/llm` | not reached |
| `GET /api/connections` | not reached |
| Canonical `google_drive` projection | not inspected live |
| Google Drive provider router | not inspected live |
| `/api/connect/google-drive/callback` | not inspected live |
| Command Bus control surface | not inspected live |

## Qualification boundary

OAuth was not initiated.

Google APIs were not called.

Google content was not read.

Command Bus Google operations were not invoked.

No Google authorization state, provider content, or Google command-run
evidence was created by this task.

## Scope and architecture boundaries

- ADR impact: aligned with ADR-071, ADR-072, and ADR-073; no ADR changed.
- The supported profile remains local-only and cloud execution remains
  disabled.
- Connections remained projection-only and Command Bus authority was neither
  bypassed nor exercised.
- No implementation, test, migration, protocol-token, or checked-in
  configuration file changed. The only runtime edit was the authorized,
  ignored local environment file.
- Release classification and `00-current-state.md` remain unchanged.

## Validation

| Check | Result |
| --- | --- |
| Required commit ancestry | pass |
| Local environment containment | pass |
| Three-value reconciliation and duplicate check | pass |
| Required Google configuration structural preservation | pass |
| Compose configuration resolution | pass |
| Configuration coherence | pass; zero mismatches |
| Dependency/one-shot initialization | pass |
| Compose-managed backend startup | blocked: exit 3 |
| HTTP and route readiness | not reached |
| Documentation validation | pass |
| Diff hygiene | pass |

## Next gate

Diagnose the post-coherence Compose-managed backend exit in a separately scoped
task. Once the backend stays up and the required route surfaces respond, resume
Google Drive / Docs live qualification at the OAuth gate, then prove provider
search/read, Command Bus execution, zero-write behavior, disconnect/reconnect,
and final connected state.
