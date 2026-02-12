# Auth Boundary Decision

Date: 2026-02-11  
Status: accepted

## Decision

1. Static browser API keys are local-only.
2. In remote mode, protected routes must not accept `X-API-Key`.
3. Remote mode requires a session/JWT token:
   - `Authorization: Bearer <token>`, or
   - `gc_session` cookie.

## Scope

This boundary applies to route dependencies using
`guardian/core/dependencies.py::verify_api_key`.

## Mode Contract

- `GUARDIAN_AUTH_MODE=local`
  - Local development behavior.
  - Static API keys remain valid for protected routes.
- `GUARDIAN_AUTH_MODE=remote`
  - Static API keys are rejected.
  - Caller must provide a valid session/JWT token.
  - Server must provide a signing/verification secret via:
    - `GUARDIAN_SESSION_SECRET` (preferred), or
    - `GUARDIAN_JWT_SECRET`, or
    - `GUARDIAN_API_KEY` (compatibility fallback).

## Rationale

`VITE_GUARDIAN_API_KEY` is distributed to browsers at build/runtime.
That is acceptable only for localhost/local-trust workflows.
For remote deployments, static shared keys in browser clients are not an
acceptable trust boundary and must be replaced by per-user session/JWT auth.

## Operational Notes

1. Do not set `VITE_GUARDIAN_API_KEY` in remote deployments.
2. Set `GUARDIAN_AUTH_MODE=remote` for any non-local deployment.
3. Ensure session/JWT token issuance is wired before enabling remote mode.

