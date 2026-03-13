# Security Posture

This document is the canonical runtime security posture for the current Codexify MVP stack.

## Baseline Contract

### 1) Single-user identity is server-derived
- Canonical principal is resolved on the server from `CODEXIFY_SINGLE_USER_ID`.
- Default single-user id is `local` when `CODEXIFY_SINGLE_USER_ID` is unset.
- `X-User-Id` is not trusted by default.
- `X-User-Id` is only honored when `DEBUG=true` or `LOCAL_DEV=true`.

Code references:
- `guardian/core/dependencies.py:get_single_user_id`
- `guardian/core/dependencies.py:get_request_user_id`

### 2) Auth boundary is explicit (`local` vs `remote`)
- `GUARDIAN_AUTH_MODE=local`:
  - static `X-API-Key` auth is allowed for local/trusted workflows.
- `GUARDIAN_AUTH_MODE=remote`:
  - static API key auth is rejected for protected routes.
  - caller must present a session/JWT token (`Authorization: Bearer <token>` or `gc_session` cookie).

See also:
- `docs/reference/security/auth-boundary-decision.md`

Code references:
- `guardian/core/dependencies.py:_auth_mode`
- `guardian/core/dependencies.py:verify_api_key`

### 3) Egress is fail-closed by default
- `CODEXIFY_LOCAL_ONLY_MODE=true` blocks outbound non-local egress.
- To permit outbound traffic, both must be true:
  - `CODEXIFY_LOCAL_ONLY_MODE=false`
  - target present in `CODEXIFY_EGRESS_ALLOWLIST`
- Cloud LLM targets (`openai`, `groq`) additionally require:
  - `ALLOW_CLOUD_PROVIDERS=true`

Current allowlist target names used in code:
- `openai`, `groq`, `elevenlabs`, `federation`, `webhook`

Code references:
- `guardian/core/egress.py`

### 4) Federation is off by default and policy-gated
- Federation master gate defaults to disabled:
  - `GUARDIAN_FEDERATION_ENABLED=false`
- When enabled, signed trust policy enforcement is on by default:
  - `GUARDIAN_FEDERATION_REQUIRE_SIGNED_POLICY=true`
- Policy verification uses:
  - `GUARDIAN_FEDERATION_TRUST_POLICY_JSON`
  - `GUARDIAN_FEDERATION_TRUST_POLICY_SIGNATURE`
  - `GUARDIAN_FEDERATION_POLICY_SIGNING_KEY` (or fallback signing secret)
- Federation session request flow is also subject to egress policy (`federation` target).

Code references:
- `guardian/routes/federation.py`
- `guardian/core/auth.py:verify_federation_trust_policy`

### 5) Plugin loading is centralized
- Runtime plugin loader access is centralized in `guardian/core/plugins.py`.
- Runtime loading is guarded to avoid duplicate initialization when plugins are already loaded.
- Manifest-based plugin discovery is filtered by:
  - duplicate plugin id rejection
  - safe entrypoint scheme (`http`/`https`)

Code references:
- `guardian/core/plugins.py`
- `guardian/system_init.py`
- `guardian/chat/cli/guardianctl.py`
- `guardian/routes/devtools.py`
- `guardian/audio/tts_trigger.py`

### 6) Config coherence is enforced at startup
- Security-relevant overlaps between config systems are checked at startup.
- App startup fails fast when coherence checks fail.

Code references:
- `guardian/core/config.py:assert_config_coherence`
- `guardian/guardian_api.py:app_lifespan`

## Deployment Guidance

### Local development (default-safe)
- `GUARDIAN_AUTH_MODE=local`
- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `ALLOW_CLOUD_PROVIDERS=false`
- `GUARDIAN_FEDERATION_ENABLED=false`

### Hosted/remote deployment
- `GUARDIAN_AUTH_MODE=remote`
- Do not set `VITE_GUARDIAN_API_KEY`
- Configure session/JWT issuance and signing secret(s)
- Keep `CODEXIFY_LOCAL_ONLY_MODE=true` unless outbound integration is explicitly required
- If outbound integration is required, set a minimal `CODEXIFY_EGRESS_ALLOWLIST`
- Enable federation only with a signed trust policy and explicit peer allow rules
