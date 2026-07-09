# Guardian Codex Runner Bridge Local Auth Override Contract

> Classification: architecture contract
> Status: governance contract for opt-in bridge proof profile
> Scope: docker-compose.codex-runner-bridge.yml only

Last updated: 2026-07-09

Source anchors:
- docker-compose.codex-runner-bridge.yml
- docker-compose.yml
- docs/architecture/00-current-state.md
- docs/architecture/config-and-ops.md
- docs/architecture/guardian-codex-runner-preflight-bridge-contract.md
- docs/architecture/guardian-codex-runner-command-bus-live-orchestration-proof.md
- guardian/core/dependencies.py
- guardian/core/public_exposure.py

## 1. Purpose

This contract documents and governs the local-auth runtime override that was introduced through the opt-in Guardian Codex Runner bridge compose profile (`docker-compose.codex-runner-bridge.yml`).

The override was needed so the opt-in bridge proof profile works with local `.env` files that carry remote-auth or multi-user defaults. It forces local auth and disables OAuth/multi-user triggers when the bridge proof profile is active.

This contract normalizes that variance into explicit governance — it does not add new bridge capability, change runtime code, or widen release claims.

## 2. Status

Status: governance contract only.

This contract does not:

- add a new bridge capability
- run live orchestration
- change runtime code
- widen release claims
- set production auth policy

This contract does not add UI support. No UI panel is implied by this contract.

Required boundary label:

```
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

Required authority block:

```yaml
authority:
  guardian_operational: false
  plan_execution_allowed: false
  pi_loop_invocation_allowed: false
  codexify_ingestion_allowed: false
  durable_mutation_allowed: false
  provider_execution_allowed: false
  patch_application_allowed: false
  dispatch_allowed: false
  merge_allowed: false
```

## 3. Scope

This contract governs only the local-auth override values in `docker-compose.codex-runner-bridge.yml`.

It covers:

- why the override exists
- which compose values are accepted
- how the override preserves local-only posture
- how to interpret the override's auth boundary

It does not implement or approve:

- new API route
- frontend panel
- UI trigger
- new write flags
- runtime code changes
- bridge command behavior changes
- default docker-compose.yml changes
- production auth policy
- remote deployment support

## 4. Triggering Evidence

The live orchestration proof (`guardian-codex-runner-command-bus-live-orchestration-proof.md`) was initially blocked by auth errors:

```
Remote mode requires session/JWT auth; X-API-Key is local-only
Multi-user mode requires an authenticated session/JWT subject
```

The local `.env` file contained `GUARDIAN_AUTH_MODE=remote` and OAuth redirects which triggered remote/multi-user auth posture. The whooshd-smoke override set local-only provider posture but did not override auth mode. The bridge compose override needed to force local auth so the command-bus bridge proofs could execute.

The fix was adding explicit `GUARDIAN_AUTH_MODE=local`, clearing OAuth triggers, and setting `CODEXIFY_MULTI_USER_ENABLED=false` in `docker-compose.codex-runner-bridge.yml`. After this change, both the validate and orchestrate live proofs passed.

## 5. Current Truth

What is true now:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- The Guardian Codex Runner bridge is internal and preflight-only.
- Both bridge preflight commands are live-proven with all authority locks false.
- The bridge compose override forces local auth for local proof execution.
- This contract documents that override — it does not change any runtime behavior.

## 6. Why the Override Exists

The bridge compose profile (`docker-compose.codex-runner-bridge.yml`) is an opt-in development/proof profile. It is not the default supported runtime path.

The whooshd-smoke override handles provider posture (LLM_PROVIDER=local, ALLOW_CLOUD_PROVIDERS=false). But `.env` files in local development environments may contain remote-auth defaults that the provider-layer override doesn't address:

- `GUARDIAN_AUTH_MODE=remote` — enables session/JWT auth, rejects X-API-Key
- `GOOGLE_OAUTH_REDIRECT=...` — triggers multi-user mode detection
- `CODEXIFY_MULTI_USER_ENABLED` — may be set explicitly or derived

Without the auth override, local command-bus proof invocation fails even though the rest of the bridge stack (mount, module invocation, adapter) is correctly configured.

The bridge override therefore includes minimal auth-env values to keep the backend in local-apikey-auth mode when the bridge proof profile is active.

## 7. Override Ownership

The override belongs exclusively to `docker-compose.codex-runner-bridge.yml`.

- The default `docker-compose.yml` remains untouched.
- The whooshd-smoke override remains untouched.
- No runtime code was modified.
- The backend auth layer (`guardian/core/dependencies.py`) remains unchanged.
- The command-bus layer remains unchanged.
- The bridge adapter remains unchanged.

## 8. Accepted Compose Values

The following values in `docker-compose.codex-runner-bridge.yml` are explicitly governed by this contract:

```yaml
GUARDIAN_AUTH_MODE: "local"
CODEXIFY_MULTI_USER_ENABLED: "false"
GOOGLE_OAUTH_REDIRECT: ""
GOOGLE_OAUTH_CLIENT_ID: ""
GOOGLE_OAUTH_CLIENT_SECRET: ""
GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY: ""
```

| Value | Purpose | Type |
|---|---|---|
| `GUARDIAN_AUTH_MODE=local` | Force local X-API-Key auth | Hard-coded |
| `CODEXIFY_MULTI_USER_ENABLED=false` | Disable multi-user mode | Hard-coded |
| `GOOGLE_OAUTH_REDIRECT=""` | Disable OAuth redirect detection | Hard-coded |
| `GOOGLE_OAUTH_CLIENT_ID=""` | Clear OAuth client ID | Hard-coded |
| `GOOGLE_OAUTH_CLIENT_SECRET=""` | Clear OAuth client secret | Hard-coded |
| `GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY=""` | Clear OAuth token encryption key | Hard-coded |

All auth-related values are hard-coded (not variable-substituted) to prevent `.env` leakage.

These values co-exist with the module invocation and mount configuration already present in the override.

## 9. Local-Only Posture

The bridge compose profile must preserve local-only posture:

- `GUARDIAN_AUTH_MODE=local` — only local API-key auth is accepted
- `CODEXIFY_MULTI_USER_ENABLED=false` — single-user mode
- OAuth redirect and credentials cleared — prevents multi-user detection
- The override is never applied by default — explicit `-f` flag required
- The default `docker-compose.yml` is not modified

This override is a proof-profile runtime condition, not a general production auth policy.

## 10. Auth Boundary Interpretation

The local-auth values in the bridge override must be interpreted narrowly:

- They enable local command-bus proof execution only.
- They do NOT set production auth policy.
- They do NOT imply that `GUARDIAN_AUTH_MODE=local` is the recommended production posture.
- They do NOT imply that OAuth should be disabled in production.
- They do NOT change the backend's auth code path — the same code runs, different env values.
- They do NOT add a second competing auth mechanism.

## 11. What This Contract Establishes

This contract establishes that:

- PR #491 introduced a compose override auth/posture change needed for local bridge proof execution
- the override is explicitly governed and documented
- the override belongs only to `docker-compose.codex-runner-bridge.yml`
- the override preserves local-only posture
- the override is opt-in (never applied by default)
- the override does not modify default `docker-compose.yml`
- the override does not change any runtime code

## 12. What This Contract Does Not Establish

This contract does not establish:

- production auth policy guidance
- recommendation for or against remote auth in production
- UI support for auth configuration
- remote deployment support
- release support expansion
- Pi Loop invocation authorization
- plan execution authorization
- provider execution authorization
- Codexify ingestion authorization
- source mutation authorization

## 13. Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| Bridge proof auth blocked | `.env` sets GUARDIAN_AUTH_MODE not covered by override | Verify override values are hard-coded, not variable-substituted |
| Bridge override unintentionally applied | Compose `-f` flags used in default startup | Document that override is opt-in; do not add it to default compose chain |
| OAuth redirect re-triggers multi-user mode | New `.env` vars not cleared in override | Add new OAuth env names to the override if they appear in `.env` |
| Production auth policy confused | Bridge override mistaken for production guidance | This contract explicitly states the override is proof-profile only |

## 14. Operator Review Checklist

When using the bridge compose profile for local proof execution:

- [ ] Bridge override applied via explicit `-f docker-compose.codex-runner-bridge.yml`
- [ ] Default `docker-compose.yml` not modified
- [ ] `GUARDIAN_AUTH_MODE=local` active
- [ ] `CODEXIFY_MULTI_USER_ENABLED=false`
- [ ] OAuth redirect and credentials cleared
- [ ] Module invocation active (`CODEXRUN_INVOCATION_MODE=module`)
- [ ] Codex Runner mounted read-only
- [ ] PYTHONPATH includes Codex Runner src

## 15. Future Changes

If future `.env` changes introduce new auth-related environment variables that would trigger remote or multi-user mode, the bridge override should be updated to clear those variables as well. Any such update must:

- stay within `docker-compose.codex-runner-bridge.yml`
- preserve local-only posture
- not modify default `docker-compose.yml`
- be documented in this contract's Accepted Compose Values section

## 16. Forbidden Interpretations

Do not interpret this contract as meaning:

- production auth policy has changed
- `GUARDIAN_AUTH_MODE=local` is the recommended production posture
- OAuth should be disabled in production
- the bridge override is the default supported path
- UI support for auth configuration is implied
- remote deployment is supported
- release claims have widened
- Pi Loop invocation is authorized
- plan execution is authorized
- source mutation is authorized
- Codexify ingestion is authorized
- provider execution is authorized

## 17. Bottom Line

This contract governs the local-auth override values in `docker-compose.codex-runner-bridge.yml`.

The override exists so the opt-in bridge proof profile works with local `.env` files that carry remote-auth defaults. It forces local API-key auth, disables OAuth triggers, and suppresses multi-user mode when the bridge proof profile is active.

The override is opt-in, local-only, and proof-profile scoped. It does not change production auth policy, runtime code, default compose posture, or any bridge authority boundaries.

Both bridge preflight commands remain live-proven with all authority locks false.
