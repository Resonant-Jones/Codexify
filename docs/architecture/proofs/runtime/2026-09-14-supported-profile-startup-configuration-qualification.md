# Supported-Profile Startup Configuration Qualification

## Verdict

`PASS — TEST_PROCESS_SETTINGS_DRIFT`

The two failing retrieval-startup tests select `v1-local-core-web-mcp` after
the process has imported the module that creates the shared core `Settings`
object. Their environment mutation does not update that already-created
object. The supported-profile contract, a fresh settings instance, a clean
process initialized with the contract environment, and the canonical Compose
render all agree.

This is a configuration-boundary qualification, not live runtime proof. It
does not change fail-closed supported-profile validation or assert that a
container was started successfully.

## Qualification identity

| Item | Value |
| --- | --- |
| Audited `origin/main` and `HEAD` | `aa1951306077e176e953fc39c9412ce93e47dd66` |
| Branch | `codex/qualify-golden-supported-retrieval-startup` |
| Worktree | `/Volumes/Dev_SSD/codex-worktrees/qualify-golden-supported-retrieval-startup` |
| Interpreter | `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` |
| Python | `3.12.13` |
| Initial tracked state | clean |

`git fetch origin` was repeated immediately before recording this receipt;
`origin/main` remained the audited SHA.

## Authoritative provider contract

`config/supported_profiles/v1-local-core-web-mcp.yaml` is the governing
provider contract.

| Key | Required value |
| --- | --- |
| `LLM_PROVIDER` | `local` |
| `ALLOW_CLOUD_PROVIDERS` | `false` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `true` |
| `CODEXIFY_EGRESS_ALLOWLIST` | empty |
| `LOCAL_RUNTIME_PRESET` | `whooshd-mlx` |
| `LOCAL_BASE_URL` | `http://host.docker.internal:8000/v1` |
| `LOCAL_API_KEY` | `local` |
| `LOCAL_COMPAT_FIRST` | `true` |
| `LOCAL_PROVIDER_DISPLAY_NAME` | `Whoosh'd` |
| `LOCAL_PROVIDER_VENDOR` | `whooshd` |

`guardian/guardian_api.py` obtains the shared settings object at lifespan
startup and calls `_refresh_supported_profile_state` before the built-in-help
or retrieval assertions run. That function intentionally raises
`RuntimeError` whenever the manifest/runtime comparison is invalid.

## Fresh failure reproduction

Both tests were run in separate clean Python processes from this worktree.

| Command | Result |
| --- | --- |
| `pytest -vv -s tests/routes/test_builtin_help_startup.py::test_startup_seeds_builtin_help_and_retrieval_can_find_it` | `1 failed, 8 warnings in 11.59s` |
| `pytest -vv -s tests/golden/test_supported_beta_golden_tasks.py::test_golden_supported_retrieval_path` | `1 failed, 8 warnings in 8.18s` |

The signatures were identical:

```text
exception_type: builtins.RuntimeError
startup_phase: application_lifespan
guardian/guardian_api.py:_app_lifespan_body -> _refresh_supported_profile_state

supported profile drift:
LOCAL_RUNTIME_PRESET expected 'whooshd-mlx' but found '';
LOCAL_BASE_URL expected 'http://host.docker.internal:8000/v1'
  but found 'http://127.0.0.1:8000/v1';
LOCAL_COMPAT_FIRST expected True but found False;
LOCAL_PROVIDER_DISPLAY_NAME expected "Whoosh'd" but found '';
LOCAL_PROVIDER_VENDOR expected 'whooshd' but found ''
```

The receipt boundary reported `application_lifespan`; no built-in-help or
retrieval assertion executed before the fail-closed profile comparison.

## Independent supported-profile contract proof

The following exact focused suite passed:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v \
  tests/core/test_supported_profile.py \
  tests/core/test_supported_profile_provider.py \
  tests/core/test_supported_profile_startup.py \
  tests/test_whooshd_smoke_env_contract.py

68 passed, 8 warnings in 8.96s
```

| File | Result |
| --- | --- |
| `tests/core/test_supported_profile.py` | PASS |
| `tests/core/test_supported_profile_provider.py` | PASS |
| `tests/core/test_supported_profile_startup.py` | PASS |
| `tests/test_whooshd_smoke_env_contract.py` | PASS |

This proves the manifest/parser/provider/startup test contract remains
coherent. It is not a live deployment proof.

## Core Settings lifecycle and test timing

`guardian/core/config.py` declares `Settings` with `.env` support, then
constructs `settings = Settings()` at module import. `get_settings()` returns
that same object; it does not rebuild from `os.environ`.

The two failing modules import `guardian.core.config` at module scope before
their test bodies mutate environment values:

| Harness | Import before mutation | Environment mutation | Synchronizes shared settings? |
| --- | --- | --- | --- |
| `test_builtin_help_startup.py` | `config_module` at module import | selects the profile and retrieval test inputs at test start | No |
| `_supported_help_startup_client` in the golden file | `config_module` at module import | selects the profile and retrieval test inputs at helper start | No |

Both subsequently reload `guardian.guardian_api`, but that reload obtains the
existing `get_settings()` singleton. Neither harness assigns the provider
contract fields on that object.

By contrast, `_load_guardian_api` in
`tests/core/test_supported_profile_startup.py` sets every provider-contract
environment variable and then explicitly assigns those values to
`guardian_api.get_settings()` before exercising startup. That synchronization
is a deliberate test-process lifecycle control, not a production authority
change.

## Direct Settings freshness probe

A temporary Python process imported `guardian.core.config`, recorded the
existing singleton, changed only the five mismatched environment fields,
recorded `get_settings()` again, then constructed a new `Settings()`.

| Field | Existing singleton | Same singleton after environment mutation | Fresh `Settings()` after mutation |
| --- | --- | --- | --- |
| `LOCAL_RUNTIME_PRESET` | `""` | `""` | `"whooshd-mlx"` |
| `LOCAL_BASE_URL` | `"http://127.0.0.1:8000/v1"` | same | `"http://host.docker.internal:8000/v1"` |
| `LOCAL_COMPAT_FIRST` | `false` | `false` | `true` |
| `LOCAL_PROVIDER_DISPLAY_NAME` | `null` | `null` | `"Whoosh'd"` |
| `LOCAL_PROVIDER_VENDOR` | `null` | `null` | `"whooshd"` |

The supported-profile adapter normalizes the two `null` values to empty text,
which explains the exact failure receipt. A second clean-process probe set the
complete manifest contract before importing `guardian.core.config`; its
module-level singleton contained all five required values. Therefore the
stale result depends on initialization before test environment mutation, not
on fresh configuration materialization.

## Canonical Compose render

The repository documents `docker compose config --quiet` as the non-mutating
configuration render. Because Compose services reference
`${CODEXIFY_RUNTIME_ENV_FILE:-.env}`, the render used a protected temporary
copy of the tracked `.env.example` through that documented override. The
template was not sourced into the host shell, no repository `.env` was
created, and no container command was run.

The validated render command was equivalent to:

```text
CODEXIFY_RUNTIME_ENV_FILE=<temporary .env.example copy> \
  docker compose --env-file .env.example config --quiet
```

It exited successfully. The only warnings were seven occurrences of an unset
`LOCAL_CHAT_MODEL`; that field is explicitly not enforced by this provider
contract. The JSON render's `backend.environment` was:

| Key | Rendered value | Manifest comparison |
| --- | --- | --- |
| `CODEXIFY_SUPPORTED_PROFILE` | `v1-local-core-web-mcp` | selected profile |
| `LLM_PROVIDER` | `local` | match |
| `ALLOW_CLOUD_PROVIDERS` | `"false"` | match after settings boolean parsing |
| `CODEXIFY_LOCAL_ONLY_MODE` | `"true"` | match after settings boolean parsing |
| `CODEXIFY_EGRESS_ALLOWLIST` | `""` | match |
| `LOCAL_RUNTIME_PRESET` | `whooshd-mlx` | match |
| `LOCAL_BASE_URL` | `http://host.docker.internal:8000/v1` | match |
| `LOCAL_API_KEY` | `local` | match |
| `LOCAL_COMPAT_FIRST` | `"true"` | match after settings boolean parsing |
| `LOCAL_PROVIDER_DISPLAY_NAME` | `Whoosh'd` | match |
| `LOCAL_PROVIDER_VENDOR` | `whooshd` | match |

The current canonical Compose projection therefore matches the manifest for
every required provider-contract field.

## Classification and rejected alternatives

### `TEST_PROCESS_SETTINGS_DRIFT`

All required conditions for this classification hold:

1. The supported-profile/provider/startup suite passed.
2. The canonical Compose render matches the manifest.
3. A fresh settings instance after environment setup matches the manifest.
4. The previously constructed singleton remains at its defaults after the
   same environment mutation.
5. Both failing harnesses omit the synchronization used by the dedicated
   supported-profile startup harness.

### Rejected: `CANONICAL_SUPPORTED_CONFIGURATION_DRIFT`

The rendered canonical backend environment matches all required manifest
values. The historical mismatch cannot be attributed to the current Compose
projection.

### Rejected: `CORE_SETTINGS_LIFECYCLE_DEFECT`

When the supported environment is present before `guardian.core.config` is
imported, the module-level singleton is correct. This qualification found no
evidence that production startup loses a correctly pre-initialized canonical
environment. It does not make a live-runtime availability claim.

### Rejected: `INCONCLUSIVE`

The independent contract suite, direct singleton/fresh probes, test-harness
inspection, and canonical Compose render establish one coherent boundary.

## Smallest next repair boundary

A subsequent test-only task may repair the two affected startup harnesses so
their owned configuration setup establishes the complete supported provider
contract before startup and synchronizes or reconstructs the test-owned
settings lifecycle. It must preserve `_refresh_supported_profile_state` and
its fail-closed behavior, make no production configuration change, and
requalify the dedicated startup and golden retrieval paths.

## ADR impact and exclusions

No ADR impact. This receipt does not alter supported-profile authority,
provider routing, startup behavior, deployment configuration, current-state
truth, or release claims.

No source, test, manifest, environment template, Compose file, runtime code,
container, Chroma volume, Redis, database, Docker resource, or deployment
state was modified. The separate dirty Persona-fixture and Guardian Evidence
worktrees were not entered or changed.
