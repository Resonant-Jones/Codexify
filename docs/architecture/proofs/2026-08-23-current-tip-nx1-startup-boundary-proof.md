# 2026-08-23 Current-Tip NX-1 Startup Boundary Proof

## Final classification

`BLOCKED — current-tip supported runtime fails configuration coherence`

This is a fresh supported-Compose observation of the exact current-main
revision below. It clears the historical MemoryStore startup boundary again:
the actual backend-container import succeeded, emitted
`guardian_api_import_ok`, did not create `guardian/memory/store.db`, and did
not emit `sqlite3.OperationalError` or `attempt to write a readonly database`.

The first material blocker is later in application startup. Uvicorn reaches
its lifespan, then configuration coherence raises `LLMConfigError` because the
resolved Compose/template configuration does not meet the active supported
profile's local-gateway contract. No repair was attempted.

## Audited revision and proof isolation

| Item | Result |
|---|---|
| Audited `origin/main` | `7aae1807492313d4cf10eb7876c3ebde92408819` |
| PR #740 merge | `72611a879b4f9a5aaba0e051fb21839fe71697fb` |
| PR #740 ancestry | `git merge-base --is-ancestor` exit `0` |
| Proof worktree | `/Volumes/Dev_SSD/Codexify-proof-nx1-7aae1807` |
| Initial state | detached `HEAD == origin/main`; no tracked or staged changes |
| Remote movement after pinning | none; final fetched `origin/main` remained `7aae1807492313d4cf10eb7876c3ebde92408819` |
| Compose project | `codexify-nx1-7aae1807` |

The proof worktree remained pinned throughout. The `.env` used for the run was
ignored and proof-local; it is not part of this commit.

## Focused pre-Docker gates

Both gates used the repository virtual-environment interpreter because the
plain `python` command is unavailable on this host.

```text
$ /Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/venv/bin/python \
    -m pytest -v tests/core/test_memory_store_startup_boundary.py
collected 5 items
tests/core/test_memory_store_startup_boundary.py .....
5 passed, 1 warning in 4.64s

$ /Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/venv/bin/python \
    -m pytest -v tests/core/test_config_coherence.py
collected 16 items
tests/core/test_config_coherence.py ................
16 passed, 1 warning in 0.11s
```

The five startup-boundary checks passed:

- `test_import_seam_does_not_create_legacy_sqlite_store_db[guardian.core.dependencies]`;
- `test_import_seam_does_not_create_legacy_sqlite_store_db[guardian.connectors.google]`;
- `test_import_seam_does_not_create_legacy_sqlite_store_db[guardian.guardian_api]`,
  including probe-owned media storage initialization;
- `test_isolated_import_probe_fails_when_target_import_fails`; and
- `test_explicit_memory_store_construction_still_works`.

The green configuration unit suite is focused unit evidence only; it does not
replace runtime proof under the resolved Compose environment.

## Isolated runtime environment and rendered posture

The proof environment was created exactly from the canonical template:

```text
cp .env.example .env
chmod 600 .env
```

It was not sourced into the host shell. There were **no proof-local
substitutions**. Compose rendered successfully with exit `0`. It emitted only
non-fatal interpolation warnings that `LOCAL_CHAT_MODEL` was unset and
defaulted blank; that key is not enforced by this supported-profile contract,
and the value was not filled in to alter the proof.

The safe resolved backend posture was:

```text
CODEXIFY_CONFIG_SOURCE='core'
CODEXIFY_SUPPORTED_PROFILE='v1-local-core-web-mcp'
LLM_PROVIDER='local'
ALLOW_CLOUD_PROVIDERS='false'
CODEXIFY_LOCAL_ONLY_MODE=true
CODEXIFY_EGRESS_ALLOWLIST=''
LOCAL_RUNTIME_PRESET=''
LOCAL_BASE_URL='http://localhost:8000/v1'
LOCAL_COMPAT_FIRST=false
LOCAL_PROVIDER_DISPLAY_NAME=''
LOCAL_PROVIDER_VENDOR=''
```

The local-only/cloud-off values match the active profile. The five empty or
different gateway-contract values are preserved template/runtime inputs, not
test substitutions.

Before Compose, `test ! -e guardian/memory/store.db` passed.

## Supported Compose execution

The current supported topology was exercised under the isolated project.

| Step | Result |
|---|---|
| `db` | started and healthy |
| `redis` | started and healthy |
| `neo4j` | started and healthy |
| `migrator` | exit `0`; Alembic upgrade and seed defaults completed |
| `model-prep` | exit `0`; an initial cache check/download completed, and an explicit repeat returned `model present` |
| `graph-init` | exit `0`; constraints and seed nodes applied |
| backend-container application import | exit `0`; `guardian_api_import_ok` emitted |

The import used the narrow `--entrypoint python` override because the Compose
backend service already declares `entrypoint: ["python"]`; this avoids an
accidental double interpreter while preserving the service environment.

After the real import and again after the backend-start attempt,
`test ! -e guardian/memory/store.db` passed. The historical readonly SQLite
failure was absent from the import and backend-start evidence.

## Backend startup boundary

`docker compose --env-file .env -p codexify-nx1-7aae1807 up -d backend`
started the dependency-complete backend path. It passed Postgres readiness,
schema verification, default seeding, Guardian API import, and router
registration, then started Uvicorn. It did not become healthy:

```text
backend state: Exited (3)
configured port: 8888
final port result: service "backend" is not running
```

The temporary Compose status showed the expected `0.0.0.0:8888->8888/tcp`
mapping while startup was in progress. There was no serving listener at final
capture because lifespan failed, so no health endpoint request was made.

The direct read-only coherence probe exited `1` with this exact exception
class and sanitized text:

```text
guardian.core.config.LLMConfigError:
supported profile requires blessed local gateway contract:
LOCAL_RUNTIME_PRESET expected 'whooshd-mlx' but found '';
LOCAL_BASE_URL expected 'http://host.docker.internal:8000/v1' but found 'http://localhost:8000/v1';
LOCAL_COMPAT_FIRST expected True but found False;
LOCAL_PROVIDER_DISPLAY_NAME expected "Whoosh'd" but found '';
LOCAL_PROVIDER_VENDOR expected 'whooshd' but found ''
```

The independent read-only profile probe reported:

```text
active_profile=v1-local-core-web-mcp
profile_mismatches=[
  "LOCAL_RUNTIME_PRESET expected 'whooshd-mlx' but found ''",
  "LOCAL_BASE_URL expected 'http://host.docker.internal:8000/v1' but found 'http://localhost:8000/v1'",
  "LOCAL_COMPAT_FIRST expected True but found False",
  "LOCAL_PROVIDER_DISPLAY_NAME expected \"Whoosh'd\" but found ''",
  "LOCAL_PROVIDER_VENDOR expected 'whooshd' but found ''",
]
```

This is a supported-profile mismatch reached through `assert_config_coherence`
in core configuration mode, not a core/legacy disagreement, a provider
credential failure, or a recurrence of the MemoryStore bug.

## Teardown, scope, and next boundary

After evidence capture, only the isolated project was removed with:

```bash
docker compose --env-file .env -p codexify-nx1-7aae1807 down
```

No broad Docker cleanup, code/test/config/profile/Docker edits, legacy SQLite
workarounds, provider or connector changes, Campaign changes, or release
changes occurred. PostgreSQL remains canonical durable application truth;
Redis remains coordination/transport; the lazy legacy MemoryStore remains
non-authoritative. NX-1 remains open.

ADR impact: **No ADR impact.** This receipt records a current-tip runtime
observation only.

Campaign disposition: **NX-1 current-tip configuration blocker proven —
return to Axis for one bounded configuration-contract repair Task Spec.**
