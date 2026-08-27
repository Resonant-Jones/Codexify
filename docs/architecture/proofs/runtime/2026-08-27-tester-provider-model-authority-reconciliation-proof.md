# Tester provider/model authority reconciliation proof

**Result:** `TESTER_PROVIDER_MODEL_AUTHORITY_RECONCILED`

**ADR impact:** Aligned with ADR-074 and the existing ADR-052 dual-provider
Tester posture; no ADR change.

## Scope and proof window

This task corrected only the two previously proven provider/profile values in
the active Tester operator environment. It did not activate the Tester stack,
start a service, run initialization, invoke a model, exercise authentication or
chat, or mutate storage. The bounded proof window began at
`2026-08-27T18:05:25Z` and ended after the static validation and documentation
checks recorded below.

The first causal blocker from the predecessor task was the exact provider and
supported-profile drift. The local Qwen selection was already correct and was
preserved.

## Prerequisite and proof-task checkout

The required predecessor was verified before any environment edit:

```text
git cat-file -e 44de4274e292aa1622b9f20040953aaab8a4c590^{commit}: PASS
git merge-base --is-ancestor 44de4274e292aa1622b9f20040953aaab8a4c590 HEAD: PASS
```

The proof-task checkout was:

```text
root: /Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: 44de4274e292aa1622b9f20040953aaab8a4c590
status: clean; ahead 7 of origin/codex/diagnose-tester-fresh-chroma-failure
```

`docs/architecture/00-current-state.md` and the unrelated Watchdog worker
remained unchanged.

## Canonical Tester authority resolution

The lifecycle chain was read from the active source without invoking it:

```text
make tester-up
  -> bash scripts/ops/codexify_tester.sh up
  -> Compose project: codexify_tester
  -> env file: /Volumes/Dev_SSD/Codexify-main/.env.tester
  -> Compose files:
     docker-compose.yml
     docker-compose.tester.yml
     docker-compose.whooshd-deepseek.yml
```

The script resolves `REPO_ROOT` to `/Volumes/Dev_SSD/Codexify-main` through the
installed Tester LaunchAgent configuration, and then deterministically derives
`TESTER_ENV_FILE=$REPO_ROOT/.env.tester`. A separate ignored `.env.tester`
exists in this proof worktree, but it is not referenced by the installed
LaunchAgent or the active source root; the canonical activation therefore has
one deterministic authority. The active file is ignored by the source
repository (`.gitignore:13`), is not tracked, and was never staged.

For clarity, the unrelated worktree copy is mode `0644` and contains the stale
`v1-friends-family-web`/`local`/`gemma-4-12b-it-qat-4bit` posture. It was not
read as the active authority, edited, staged, or used for any Compose render.
The installed LaunchAgent's explicit `CODEXIFY_TESTER_REPO_ROOT` is the
precedence anchor for the real Tester runtime.

The active source repository identity was:

```text
remote: https://github.com/Resonant-Jones/Codexify.git
branch: main
HEAD: 1c597042e314a9a409ddd384225a2cbb723f7528
status: main...origin/main [ahead 3, behind 18]
pre-existing dirty paths: deleted 2026-08-26 daily log, modified
2026-08-25 image-retention proof, untracked 2026-08-27 Google Drive proof
```

Those source-repository paths were preserved. The active environment metadata
was `owner=chriscastillo`, `group=staff`, `mode=0600` before the edit and remains
`owner=chriscastillo`, `group=staff`, `mode=0600` afterward. The file contents
were never printed wholesale; only the non-secret authority fields below were
read.

## Pre-change authority snapshot

The pre-change values were:

| Setting | Active env value | Effective Tester contract |
| --- | --- | --- |
| `CODEXIFY_SUPPORTED_PROFILE` | `v1-friends-family-web` | `v1-whooshd-deepseek-web` |
| `LLM_PROVIDER` | `deepseek` | `local` |
| `LOCAL_CHAT_MODEL` | `qwen3.8-27b-4bit` | `qwen3.8-27b-4bit` |
| `LOCAL_PROVIDER_VENDOR` | unset in env; supplied by overlay | `whooshd` |
| `LOCAL_BASE_URL` | unset in env; supplied by overlay | `http://host.docker.internal:8000/v1` |
| `ALLOW_CLOUD_PROVIDERS` | `true` | `true` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` | `false` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `deepseek` | `deepseek` |
| `DEEPSEEK_CHAT_MODEL` | `deepseek-v4-flash` | `deepseek-v4-flash` |

The Whoosh’d vendor and endpoint are explicit values in the final
`docker-compose.whooshd-deepseek.yml` overlay, so their effective pre-change
values were already correct even though the ignored env file did not repeat
them. The two identical pre-existing DeepSeek env assignments were not changed
or used to override the local authority; the target authority keys each had one
assignment.

The target assignment counts before editing were exactly one each for
`LLM_PROVIDER`, `CODEXIFY_SUPPORTED_PROFILE`, and `LOCAL_CHAT_MODEL`.

## Bounded-drift decision and exact edit

The supported profile authority exists at:

```text
/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-whooshd-deepseek-web.yaml
```

It parses successfully and declares the accepted provider contract: local
Whoosh’d, `qwen3.8-27b-4bit`, `ALLOW_CLOUD_PROVIDERS=true`,
`CODEXIFY_LOCAL_ONLY_MODE=false`, the `deepseek` egress allowlist, and
`deepseek-v4-flash` for the explicit cloud lane. No other contract-bearing
value was materially wrong; the overlay supplies the vendor/base URL values
and the Qwen model was already exact.

Only these two existing assignments were changed in
`/Volumes/Dev_SSD/Codexify-main/.env.tester`:

```text
LLM_PROVIDER: deepseek -> local
CODEXIFY_SUPPORTED_PROFILE: v1-friends-family-web -> v1-whooshd-deepseek-web
```

No target authority key was appended or duplicated. Comments, ordering, secrets, storage
settings, authentication settings, and all other values were preserved.

## Post-change authority snapshot

The post-change secret-safe read was:

| Setting | Post-change value |
| --- | --- |
| `CODEXIFY_SUPPORTED_PROFILE` | `v1-whooshd-deepseek-web` |
| `LLM_PROVIDER` | `local` |
| `LOCAL_CHAT_MODEL` | `qwen3.8-27b-4bit` |
| `LOCAL_PROVIDER_VENDOR` | unset in env; effective overlay `whooshd` |
| `LOCAL_BASE_URL` | unset in env; effective overlay `http://host.docker.internal:8000/v1` |
| `ALLOW_CLOUD_PROVIDERS` | `true` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `deepseek` |
| `DEEPSEEK_CHAT_MODEL` | `deepseek-v4-flash` |

The exact semantic comparison was therefore:

```text
LLM_PROVIDER: deepseek -> local
CODEXIFY_SUPPORTED_PROFILE: v1-friends-family-web -> v1-whooshd-deepseek-web
LOCAL_CHAT_MODEL: qwen3.8-27b-4bit -> qwen3.8-27b-4bit
```

Post-edit assignment counts remained exactly one for each target key:

```text
LLM_PROVIDER=1
CODEXIFY_SUPPORTED_PROFILE=1
LOCAL_CHAT_MODEL=1
```

## Static Tester configuration proof

The active Compose files and corrected env file were rendered with
`docker compose config --format json` and `docker compose config --quiet`; no
container lifecycle command was used. Both commands exited successfully. The
safe resolved fields were:

```text
project: codexify_tester
backend image: codexify-backend-runtime:latest
backend host binding: 127.0.0.1:8889 -> 8888/tcp
backend profile: v1-whooshd-deepseek-web
backend provider: local
backend local model: qwen3.8-27b-4bit
backend local vendor: whooshd
backend local base URL: http://host.docker.internal:8000/v1
backend cloud enabled: true
backend local-only mode: false
backend egress allowlist: deepseek
backend DeepSeek model: deepseek-v4-flash
worker-chat provider: local
worker-chat local model: qwen3.8-27b-4bit
worker-chat local vendor: whooshd
worker-chat DeepSeek model: deepseek-v4-flash
```

The renderer emitted non-fatal warnings that optional `LOCAL_VISION_MODEL` and
`LOCAL_GGUF_MODEL` were unset. Those independent model domains are not required
by the Tester chat provider contract and were not changed. The required
profile/provider/model render passed.

## Lifecycle and execution boundary

The desired-up marker remained absent, no target Tester service was running, and
no process listened on `127.0.0.1:8889` at the pre-edit and post-edit absence
checks. Those checks found only two pre-existing exited Google Drive OAuth
containers carrying the `codexify_tester` label. A later read-only check saw an
out-of-band container named `codexify-strace-capsule-builder-lbk0ba` created at
`2026-08-27T18:07:10Z`, with Compose labels `project=codexify_tester` and
`service=migrator`. Its command is only a long-lived `sleep` loop, it has no
Tester service image/port, and no migration process is running. No command in
this task created or touched that concurrent capsule-builder container; it was
left unchanged and is excluded from the task's lifecycle/invocation counts.

```text
TESTER_STACK_ACTIVATION_ATTEMPTS=0
TESTER_SERVICE_LIFECYCLE_ACTIONS=0
MIGRATOR_INVOCATIONS=0
SEED_INVOCATIONS=0
MODEL_PREP_INVOCATIONS=0
GRAPH_INIT_INVOCATIONS=0
WHOOSHD_LIFECYCLE_ACTIONS=0
MODEL_INVOCATIONS_DURING_TESTER_AUTHORITY_RECONCILIATION=0
AUTHENTICATION_OPERATIONS=0
THREADS_CREATED=0
MESSAGES_CREATED=0
COMPLETION_REQUESTS=0
DEEPSEEK_REQUESTS_DURING_TESTER_AUTHORITY_RECONCILIATION=0
WATCHDOG_ACTIVITY_DURING_TESTER_AUTHORITY_RECONCILIATION=0
POSTGRES_MUTATIONS=0
REDIS_MUTATIONS=0
CHROMA_MUTATIONS=0
NEO4J_MUTATIONS=0
MODEL_ARTIFACT_MUTATIONS=0
```

No `make tester-up`, Compose `up`/`start`, migrator, seed, model-prep,
graph-init, Whoosh’d lifecycle command, authentication request, chat request,
DeepSeek request, Watchdog action, or storage operation was issued. The
canonical Tester volumes and model artifacts were left untouched.

## Validation and documentation

The following read-only or task-checkout validations passed:

```text
git cat-file -e 44de4274e292aa1622b9f20040953aaab8a4c590^{commit}
git merge-base --is-ancestor 44de4274e292aa1622b9f20040953aaab8a4c590 HEAD
bash -n /Volumes/Dev_SSD/Codexify-main/scripts/ops/codexify_tester.sh
docker compose ... config --format json
docker compose ... config --quiet
python3 scripts/validate_docs.py
git diff --check
```

The only task-checkout file added was this proof artifact. The active
`.env.tester` remained outside the proof checkout, ignored, and unstaged;
`docs/architecture/00-current-state.md` remained unchanged.

## Deferred next slice

The next task may perform exactly one canonical `make tester-up` activation
using this corrected authority. That separate lifecycle proof must establish a
healthy idle `codexify_tester` stack, preserved Postgres volume, healthy
Postgres/Redis/backend, fresh `worker-chat` heartbeat, queue depth zero, and
the unchanged `local / qwen3.8-27b-4bit` authority. Do not combine that startup
with an authenticated completion; only after an independently healthy idle
baseline should the one-attempt authenticated Qwen completion proof be rerun.

This proof does not widen release/current-state claims.
