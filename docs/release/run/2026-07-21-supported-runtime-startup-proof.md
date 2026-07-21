# Supported Compose backend startup proof

- Date: 2026-07-21
- Tested commit: `3998dbae776e4ac1633f20fcea74088dcec84448`
- Runtime profile: local Docker Compose, `v1-local-core-web-mcp`
- Runtime contract: local provider, local-only mode, backend port `8888`
- Execution lane: architecture-impact; bounded startup proof
- ADR impact: **Aligned with existing ADR-005**; no runtime/account contract was changed
- Final outcome: **BLOCKED**

## Blocking result

The supported Compose backend was not restored because two independent
prerequisites fail before a supported full-stack proof can complete:

1. Compose refuses to start `backend` and `worker-chat` because the persisted
   Neo4j service is unhealthy. Its healthcheck reports Bolt authentication
   failures, and `graph-init` therefore remains `Created`.
2. When Neo4j dependency gating is bypassed for diagnosis, the backend fails
   closed during FastAPI lifespan initialization because the untracked local
   `.env` supplies a gateway URL that does not match the active supported
   profile contract.

No repository repair was applied. The observed causes are a local environment
value and persisted local Neo4j authentication/health state, not an evidenced
defect in the authorized repository files. No Neo4j volume reset or credential
mutation was attempted.

## Initial and dependency state

The worktree was clean before this proof and was on `main`, one commit ahead of
`origin/main`. `docker compose config --quiet` passed. The initial Compose
state was:

| Service | State |
| --- | --- |
| `db` | healthy |
| `redis` | healthy |
| `neo4j` | up, unhealthy |
| `migrator` | exited `0` |
| `model-prep` | exited `0` |
| `graph-init` | `Created` |
| `backend` | exited `3` |
| `worker-chat` | `Created` |

Port `8888` was closed before the diagnostic run (`curl` status `000`).

The local `.env` was present and had `GUARDIAN_API_KEY` set; only variable
names and presence were inspected. `GUARDIAN_ENV` and
`CODEXIFY_CONFIG_SOURCE` were unset, so Compose selected its `core` default.
Sourcing the file in zsh also failed on an untracked provider display-name
value containing an apostrophe. Compose's dotenv parser still rendered the
file, but the shell-source defect remains a local prerequisite if operators
need to source it directly.

## Required Compose sequence

The prescribed sequence was executed without destructive cleanup:

```text
docker compose up -d db redis neo4j                         PASS
docker compose run --rm migrator                            PASS; exited 0
docker compose up -d backend worker-chat                    BLOCKED
```

The final command returned:

```text
dependency failed to start: container codexify-neo4j-1 is unhealthy
```

Neo4j logs repeatedly report client authorization failure from its healthcheck;
the latest healthcheck exited `1`. This is classified as an external local
runtime prerequisite: persisted Neo4j auth/health state. The exact credential
state is not recorded in this artifact.

## Backend startup diagnosis

The backend image can import `guardian.guardian_api` successfully, so the
failure is not an import or image-path failure. With Compose dependency gating
bypassed, the exact lifespan failure is:

```text
LLMConfigError: supported profile requires blessed local gateway contract: LOCAL_BASE_URL expected 'http://100.127.148.28:8000/v1' but found 'http://host.docker.internal:8000/v1'
```

Trace and owner:

```text
guardian/guardian_api.py:app_lifespan
  -> assert_config_coherence(settings)
guardian/core/config.py:assert_config_coherence
  -> validate_llm_config
guardian/core/config.py:_validate_supported_profile_contract
  -> guardian/core/supported_profile.py:validate_supported_profile_runtime
```

Classification: **invalid local environment configuration**, not a repository
code defect. The supported profile manifest requires the Tailscale gateway
address above; the untracked local `.env` overrides Compose's fallback with
`host.docker.internal`.

An ephemeral, non-supported diagnostic run with
`LOCAL_BASE_URL=http://100.127.148.28:8000/v1` reached `lifespan=ok`. Its
one-off backend listener on port `8888` returned:

| Probe | Result |
| --- | --- |
| `/healthz` | `200` |
| `/health` | `200` |
| `/health/chat` | `200` |
| `/api/health/llm` | `200` |
| authenticated `/api/threads` | `200` |
| unauthenticated `/api/threads` | `401` |
| post-restart `/health` | `200` |
| post-restart authenticated `/api/threads` | `200` |
| post-restart unauthenticated `/api/threads` | `401` |

This is diagnostic evidence only: it used `docker compose run --no-deps`, an
environment override, and no worker or Neo4j/graph-init completion. It does not
prove supported Compose startup or end-to-end operation.

## Validation

- `docker compose config --quiet` — **PASS**.
- `docker compose run --rm migrator` — **PASS**, migrations and seed completed;
  exited `0`.
- Backend import diagnostic — **PASS**.
- Corrected-environment lifespan diagnostic — **PASS**, `lifespan=ok`.
- `docker compose run --rm --no-deps --entrypoint python backend -m pytest -v tests/core/test_config_coherence.py` — **FAIL**, 13 passed and 2 baseline failures. The core-mode case reaches the same supported-profile URL mismatch; the legacy-mode assertion is incompatible with redacted runtime logging.
- `docker compose run --rm --no-deps --entrypoint python backend -m pytest -q tests/core/test_supported_profile_startup.py tests/test_startup.py tests/ops/test_source_compose_supported_profile_contract.py tests/ops/test_webui_runtime_compose_contract.py` — **FAIL**, 13 passed and 5 failures. Two supported-profile tests reproduce the URL drift. Three ops-contract tests fail only in the backend image because `/app` does not contain repository source paths.
- `.venv/bin/python -m pytest -q tests/ops/test_source_compose_supported_profile_contract.py tests/ops/test_webui_runtime_compose_contract.py` — **PASS**, 3 tests.
- `git diff --check` — **PASS** for this artifact.

The requested `tests/test_supported_runtime_startup.py` was not created: no
authorized repository repair was proven. The requested anchor
`docs/architecture/dev-setup.md` and `server/.env.example` are absent; the
current development setup anchor is `docs/infra/dev-setup.md`.

## Scope and invariants

Only this proof artifact is changed. No files under Compose, Guardian startup
configuration, Documents auth, parsing, embedding, retrieval, provider/chat
semantics, image handling, or tests were modified. No key, token, password,
cookie, private document content, or credential value is recorded here.

The following remain unchanged and unproven only at the supported full-stack
runtime boundary:

- port `8888` remains the Compose backend port;
- supported local-only/provider restrictions remain fail-closed;
- authenticated access is not weakened and unauthenticated access remains
  rejected in the diagnostic run;
- the prior Documents auth proof remains a separate valid blocked proof;
- no runtime claim is inferred from migration success, TCP reachability, or the
  corrected one-off listener.

## Required operator prerequisite

Before rerunning the supported proof, correct the local untracked `.env`
`LOCAL_BASE_URL` to the active profile's required gateway value without
committing it, and resolve the Neo4j authentication/health state. If shell
sourcing is required, quote the provider display-name value containing the
apostrophe. Resetting the Neo4j volume is destructive and requires explicit
operator approval; it was not performed here.

## Final outcome

**BLOCKED** — the supported Compose backend remains down because local
environment and persisted Neo4j prerequisites are not satisfied. No repository
repair or runtime support claim is made.
