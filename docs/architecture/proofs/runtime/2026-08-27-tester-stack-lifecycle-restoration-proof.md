# Tester stack lifecycle restoration proof

**Result:** `TESTER_PROVIDER_MODEL_AUTHORITY_DRIFT`

**ADR impact:** Aligned with ADR-074, ADR-052, and the existing Tester
lifecycle/operator contracts; no ADR change.

## Scope and stop condition

This task was authorized to restore the existing isolated `codexify_tester`
runtime to a healthy, idle, non-inference baseline. The canonical lifecycle
authority and preserved durable volumes were resolved, but the pre-activation
authority gate failed. The task therefore stopped before the one permitted
activation. No service was started, recreated, or repaired.

The bounded read-only preflight window was:

```text
PROOF_WINDOW_START_UTC=2026-08-27T17:37:07Z
PROOF_WINDOW_END_UTC=2026-08-27T17:37:08Z
```

The first causal blocker was:

```text
TESTER_PROVIDER_MODEL_AUTHORITY_DRIFT
```

The machine-local `.env.tester` currently selects `LLM_PROVIDER=deepseek` and
`CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web`. This restoration requires
the unchanged Tester authority `LLM_PROVIDER=local` and the
`v1-whooshd-deepseek-web` dual-provider profile. The local model literal is
`qwen3.8-27b-4bit`, but the provider/profile drift makes activation unsafe and
is explicitly outside this task's write boundary.

## Repository and prerequisite gate

Codexify task checkout:

```text
root: /Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: 758dbe4b1d6a28f62ba15a307ecd233707e29016
status: clean; ahead 6 of origin/codex/diagnose-tester-fresh-chroma-failure
```

The required predecessor was verified before preflight:

```text
git cat-file -e 758dbe4b1d6a28f62ba15a307ecd233707e29016^{commit}: PASS
git merge-base --is-ancestor 758dbe4b1d6a28f62ba15a307ecd233707e29016 HEAD: PASS
```

The unrelated Watchdog worker and `docs/architecture/00-current-state.md`
were not changed.

## Lifecycle authority and runtime distinction

The canonical control surface is:

```text
make tester-up
  -> bash scripts/ops/codexify_tester.sh up
  -> desired-up marker: ~/Library/Application Support/Codexify/tester/enabled
  -> Compose project: codexify_tester
  -> env: /Volumes/Dev_SSD/Codexify-main/.env.tester
  -> Compose files:
     docker-compose.yml
     docker-compose.tester.yml
     docker-compose.whooshd-deepseek.yml
```

The installed per-user LaunchAgent
`com.resonant.codexify-tester` points at the same lifecycle script and source
root. The marker was absent before this proof (`desired_state=disabled`).

The two local runtimes remain distinct:

| Runtime | Project/container | Profile | Backend port |
| --- | --- | --- | --- |
| Tester (target) | `codexify_tester` / `codexify_tester-backend-1` | `v1-whooshd-deepseek-web` | `127.0.0.1:8889` |
| Standard Compose (not target) | `codexify` / `codexify-backend-1` | `v1-local-core-web-mcp` | `127.0.0.1:8888` |

The standard stack was inspected only to prevent substitution. It was not
started, stopped, reconfigured, or used as Tester evidence.

## Active source and pre-restoration state

The configured Tester source root is `/Volumes/Dev_SSD/Codexify-main`.
Read-only source identity was:

```text
remote: https://github.com/Resonant-Jones/Codexify.git
branch: main
HEAD: 1c597042e314a9a409ddd384225a2cbb723f7528
status: main...origin/main [ahead 3, behind 18]
pre-existing dirty paths: one deleted daily log, one modified proof, one
untracked Google Drive proof
```

Those paths were preserved. `.env.tester` exists with mode `0600`; its
contents were read only for the non-secret authority keys below and were not
printed wholesale, changed, staged, or committed.

No `codexify_tester` containers or project network were present. The Docker
image `codexify-backend-runtime:latest` was available locally (image ID
`afaca31e244e`). Existing Tester-owned volumes were present and preserved:

```text
codexify_tester_pg_data
codexify_tester_neo4j_data
codexify_tester_codexify_cli_home
codexify_tester_codexify_tailscale_test_state
codexify_tester_hf_cache
codexify_tester_frontend_pnpm_store
codexify_tester_corepack_cache
```

The canonical PostgreSQL volume `codexify_tester_pg_data` was created
2026-07-25, is labeled for Compose project `codexify_tester`, and remains
untouched. No volume deletion, recreation, pruning, snapshot restore, or
manual data operation occurred.

## Authority gate

The effective non-secret values read from the existing operator environment
were:

| Setting | Observed value | Required for this task |
| --- | --- | --- |
| `CODEXIFY_SUPPORTED_PROFILE` | `v1-friends-family-web` | `v1-whooshd-deepseek-web` |
| `LLM_PROVIDER` | `deepseek` | `local` |
| `LOCAL_CHAT_MODEL` | `qwen3.8-27b-4bit` | `qwen3.8-27b-4bit` |
| `LOCAL_PROVIDER_VENDOR` | unset | existing Whoosh'd posture |
| `LOCAL_BASE_URL` | unset | existing Whoosh'd endpoint |
| `ALLOW_CLOUD_PROVIDERS` | `true` | existing Tester posture |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` | existing Tester posture |
| `CODEXIFY_EGRESS_ALLOWLIST` | `deepseek` | `deepseek` |
| `GUARDIAN_AUTH_MODE` | `remote` | existing Tester auth posture |

The provider and supported-profile values fail the required exact Tester
authority. No environment or Compose value was normalized or substituted.

## Cold-start dependency graph (not executed)

The current lifecycle script's `up` operation would set the marker and invoke
one `compose up -d` for `backend`, `frontend`, `worker-chat`,
`worker-chat-embed`, `worker-document-embed`, `worker-warmup`,
`worker-account-import`, and `tailscale-codexify-test`. The rendered Compose
graph identifies these required dependencies:

- `backend` requires healthy `db` and successful `graph-init`, `migrator`, and
  `model-prep`;
- `graph-init` requires healthy `neo4j`;
- `migrator` requires healthy `db`;
- `worker-chat` requires healthy `backend` and `redis`, plus successful
  `model-prep`;
- the remaining workers require the canonical backend/Redis/model-prep
  dependencies as defined by the active render.

This graph was inspected read-only. It was not invoked because the authority
gate failed first.

## Activation and execution boundary

No lifecycle mutation was performed:

```text
TESTER_STACK_ACTIVATION_ATTEMPTS=0
MIGRATOR_INVOCATIONS_DURING_TESTER_RESTORATION=0
SEED_INVOCATIONS_DURING_TESTER_RESTORATION=0
MODEL_PREP_INVOCATIONS_DURING_TESTER_RESTORATION=0
GRAPH_INIT_INVOCATIONS_DURING_TESTER_RESTORATION=0
```

No `make tester-up`, Compose `up`, `docker start`, or one-shot command was
issued. Consequently there is no post-restoration backend, Postgres, Redis,
worker, queue, or port-health claim. The Whoosh'd prerequisite was not
re-probed after the authority blocker, and no Whoosh'd lifecycle action
occurred.

No authenticated chat activity or inference occurred:

```text
AUTHENTICATED_SESSIONS_DURING_TESTER_RESTORATION=0
PROOF_THREADS_CREATED=0
USER_MESSAGES_CREATED=0
COMPLETION_REQUESTS_SUBMITTED=0
MODEL_INVOCATIONS_DURING_TESTER_RESTORATION=0
DEEPSEEK_REQUESTS_DURING_TESTER_RESTORATION=0
WATCHDOG_ACTIVITY_DURING_TESTER_RESTORATION=0
GITHUB_IO_DURING_TESTER_RESTORATION=0
POSTGRES_MUTATIONS_DURING_TESTER_RESTORATION=0
REDIS_MUTATIONS_DURING_TESTER_RESTORATION=0
CHROMA_MUTATIONS_DURING_TESTER_RESTORATION=0
```

No application source, `.env.tester`, supported profile, Compose definition,
migration, seed implementation, provider/model configuration, Qwen
registry/artifact, Whoosh'd plist/source, Watchdog file, or release-truth file
was changed.

## Validation

Read-only checks performed:

```text
git status --short --branch
git rev-parse HEAD
git branch --show-current
git cat-file -e 758dbe4b1d6a28f62ba15a307ecd233707e29016^{commit}
git merge-base --is-ancestor 758dbe4b1d6a28f62ba15a307ecd233707e29016 HEAD
git -C /Volumes/Dev_SSD/Codexify-main status --short --branch --untracked-files=all
git -C /Volumes/Dev_SSD/Codexify-main rev-parse HEAD
git -C /Volumes/Dev_SSD/Codexify-main remote -v
git -C /Volumes/Dev_SSD/Codexify-main check-ignore -v .env.tester
bash scripts/ops/codexify_tester.sh status
docker compose --project-name codexify_tester ... config --format json
docker ps -a --filter label=com.docker.compose.project=codexify_tester
docker volume inspect codexify_tester_pg_data ...
docker network ls --filter name=codexify_tester
python3 scripts/validate_docs.py
git diff --check
```

The canonical status command returned `tester_status=degraded` with the
desired-up marker disabled, all required services missing, and both `8889`
health endpoints unreachable. The authority read independently returned the
provider/profile drift recorded above. Docs validation and `git diff --check`
passed after this artifact was created.

## Deferred next slice

Do not activate the stack until an operator-authorized configuration task
restores the existing `.env.tester` authority to the exact Tester posture
without changing the Qwen model selection. Then rerun this restoration task
from its preflight, with exactly one `make tester-up` activation and no
repair-and-retry after any startup failure. Only after a healthy idle Tester
baseline is proven may the blocked authenticated ordinary Qwen completion task
be rerun.

`docs/architecture/00-current-state.md` remained unchanged. This blocked
receipt does not widen current-main supported-Compose or Beta release claims.
