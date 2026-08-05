# Tester Backend Exit-3 Startup Diagnosis

Proof date: 2026-08-05

Runtime window: 2026-08-05 ~17:05-17:40 EDT

## Outcome

`hold`

The root cause is a code defect: the Pydantic `Settings` model in
`guardian/core/config.py` uses `model_config = SettingsConfigDict(extra="ignore")`
(line 80-81), which silently discards environment variables that are not
explicitly defined as model fields.  The supported-profile runtime validation
(`_validate_supported_profile_contract`) reads these fields via
`supported_profile_actual_provider_contract`, which uses `getattr(settings, ...)`
against the Pydantic model.  Because `extra="ignore"` drops them, the profile
validator sees empty defaults instead of the actual `.env` values and raises
`LLMConfigError`.

This is a real implementation defect.  Per the proof failure policy, this task
stops, classifies as `hold`, and documents the smallest follow-up implementation
task.  No production code was modified (`.env` edits were reverted).

## Root cause

`guardian/core/config.py` line 80:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
```

`extra="ignore"` tells Pydantic to silently discard any environment variable
that does not match a declared field.  The following profile-contract fields
are in `.env` and required by the supported profile but are **not** declared
in the `Settings` model:

| Env var | Profile expected value | Pydantic sees |
|---|---|---|
| `LOCAL_RUNTIME_PRESET` | `whooshd-mlx` | `""` (discarded) |
| `LOCAL_COMPAT_FIRST` | `true` | `False` (default) |
| `LOCAL_PROVIDER_DISPLAY_NAME` | `Whoosh'd` | `None` |
| `LOCAL_PROVIDER_VENDOR` | `whooshd` | `None` |

The function `supported_profile_actual_provider_contract` in
`guardian/core/supported_profile.py` uses `getattr(settings, key, "")` to
read these values.  Because Pydantic dropped them, every `getattr` returns
the default (empty string, `False`, or `None`).

The profile-runtime validator in `guardian/core/config.py` line 1133
(`_validate_supported_profile_contract`) compares the profile's expected
values against the Pydantic model's actual values.  The mismatches cause
`LLMConfigError` to be raised during the ASGI lifespan
(`GuardianApi.app_lifespan`, `guardian/guardian_api.py` line 615), which
re-raises, terminates uvicorn, and exits the container with code 3.

The error is fully redacted by the Guardian structured logger
(`guardian/utils/log_safety.py`), so the operator sees only
`log_event=<redacted> chars=…` and `ERROR:` lines with no actionable detail.

## Unredacted exception

Captured by running the backend on the host with a reduced environment where
the missing fields were not set:

```
LLMConfigError: supported profile requires blessed local gateway contract:
  LOCAL_RUNTIME_PRESET expected 'whooshd-mlx' but found ''
  LOCAL_BASE_URL expected 'http://host.docker.internal:8000/v1' but found 'http://localhost:8000/v1'
```

(The `LOCAL_BASE_URL` mismatch on the host was a test-only condition; in
Docker Compose the value matches the profile.)

## Why the tester backend worked previously (21-hour uptime)

The `_validate_supported_profile_contract` function was introduced on this
branch (between the prior mainline merge and the current HEAD).  The tester
backend was started before the branch was checked out or was running an
image that predates the validation code.  A restart after the branch was
present triggers the new validation path.

## Smallest follow-up implementation task

### Primary fix

Add the four missing profile-contract fields to the `Settings` model in
`guardian/core/config.py`:

```python
LOCAL_RUNTIME_PRESET: str = Field(default="")
LOCAL_COMPAT_FIRST: bool = Field(default=False)
LOCAL_PROVIDER_DISPLAY_NAME: str | None = Field(default=None)
LOCAL_PROVIDER_VENDOR: str | None = Field(default=None)
```

These fields should read from the environment with the same names (Pydantic
does this by default) so that `supported_profile_actual_provider_contract`
sees the actual values instead of silent defaults.

### Secondary review

Consider whether `extra="ignore"` is the correct posture for a system whose
operator relies on environment variables to satisfy supported-profile
contracts.  `extra="allow"` would preserve unknown fields, but `extra="ignore"`
was likely chosen to prevent accidental configuration drift.  A narrower
fix is adding the explicit fields as above.

### Validation

- Unit test: `_validate_supported_profile_contract` passes when all four
  fields are present in the environment and match the profile.
- Integration test: backend starts healthy with `CODEXIFY_CONFIG_SOURCE=core`.
- Regression test: backend exits cleanly without `LLMConfigError` when
  profile-contract fields are missing (graceful degradation, not crash).

## Service state at diagnosis

| Service | State |
|---|---|
| `codexify-db-1` | healthy |
| `codexify-redis-1` | healthy |
| `codexify-worker-coding-1` | healthy (readiness `ready`) |
| `codexify-frontend-1` | up, HTTP 200 |
| `codexify-backend-1` | exit 3 during startup |
| `codexify_tester-backend-1` | exit 3 during startup (same root cause) |

## Configuration-source comparison

The tester uses `.env.tester` with profile `v1-friends-family-web`.
The main stack uses `.env` with profile `v1-local-core-web-mcp`.

Both profiles trigger the same validation path.  The `v1-friends-family-web`
profile does not have a `provider_contract` section, so its validation is a
no-op.  However, the main profile `v1-local-core-web-mcp` **does** have a
`provider_contract`, and its validation fails for the reasons above.

The tester backend additionally fails because its `LLM_PROVIDER` is `deepseek`
(set in `docker-compose.tester.yml` for the `worker-chat` service, but the
`backend` service inherits the default `LLM_PROVIDER=local` from the
shared `local_llm` Compose anchor).

## Redaction override method

Guardian log redaction could not be disabled through environment variables
(the `SafeLogFilter` in `guardian/utils/log_safety.py` is always active).
The unredacted error was captured by running the backend on the host where
the `assert_config_coherence` failure propagated to the Python interpreter
before the Guardian logger suppressed the message.

## Exact commands run

```text
# Tester lifecycle
bash scripts/ops/codexify_tester.sh down
bash scripts/ops/codexify_tester.sh up     # migrator failed, exit 1

# Backend startup attempts (all exited with code 3)
docker compose up -d --no-deps backend
docker run ... codexify-backend-runtime:latest python -c "..."

# Host-side diagnosis (captured the unredacted error)
.venv/bin/python -c "
os.environ['CODEXIFY_CONFIG_SOURCE'] = 'core'
os.environ['LLM_PROVIDER'] = 'local'
...
from guardian.core.config import get_settings, assert_config_coherence, ConfigCoherenceError
try:
    assert_config_coherence(get_settings())
except ConfigCoherenceError as e:
    print(f'COHERENCE_FAIL: {e}')
"
# Output: LOCAL_RUNTIME_PRESET expected 'whooshd-mlx' but found ''
#         LOCAL_BASE_URL expected '...' but found '...'

# Environment restoration
git checkout -- .env  (reverted to original value)

# Docker cleanup
docker rm -f codexify-backend-1 codexify_tester-backend-1 ...
```

## Warnings

- The `.env` file was temporarily edited during diagnosis (`LOCAL_BASE_URL`
  changed, `CODEXIFY_CONFIG_SOURCE` and `CODEXIFY_EGRESS_ALLOWLIST` added).
  All edits were reverted after the root cause was identified.
- The tester `migrator` failed with exit 1 during `make tester-up` — a
  separate pre-existing issue not investigated here.
- The Guardian `SafeLogFilter` cannot be bypassed through environment
  variables, making operator diagnosis of startup failures unnecessarily
  difficult.  This is a separate design concern, not a bug.

## Failures

1. **Code defect (blocker):** `Settings.model_config.extra="ignore"` drops
   `LOCAL_RUNTIME_PRESET`, `LOCAL_COMPAT_FIRST`, `LOCAL_PROVIDER_DISPLAY_NAME`,
   and `LOCAL_PROVIDER_VENDOR` from the Pydantic model, causing the
   supported-profile runtime validator to raise `LLMConfigError` and the
   backend to exit with code 3.

2. **Operational blindness:** Guardian log redaction prevents the operator
   from seeing the actual configuration coherence error in the Docker logs.

## Documentation follow-through

`docs/architecture/00-current-state.md` is unchanged (outcome not `go`).

## Validation results

| Check | Result |
|---|---|
| `git diff --check` (proof doc only) | pass |
| Secret scan of proof receipt and git diff | pass |
| `python3 scripts/validate_docs.py` | pass |
| `.env` restored to original state | confirmed |
| Unredacted exception captured | confirmed |
| Root cause traced to specific line of code | confirmed |

## What Axis should add to his KB

1. `Settings.model_config.extra="ignore"` in `guardian/core/config.py` is the
   root cause of the backend exit-3 failure.  Four profile-contract fields
   are silently discarded by Pydantic.  The fix is adding explicit field
   declarations to the model.

2. Guardian log redaction (`SafeLogFilter`) is always active and has no
   environment-variable off switch.  When diagnosing backend startup
   failures, run the config check on the host where Python tracebacks
   are not intercepted by the Guardian logger.

3. The `_validate_supported_profile_contract` function was introduced
   recently (this branch) and is the gate that triggers the exit.  The
   tester stack had been running since before this code was active, which
   is why it survived 21 hours until restart.

## Secret-handling statement

No raw API key, credential, token, or private path is included in this
receipt.  The `.env.tester` contents were inspected for key names only;
credential values were not retained, printed, or committed.
