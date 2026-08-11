# Private-preview frontend server-secret isolation proof

Date: 2026-08-11

## 1. Scope

This architecture-impact task repairs a Compose boundary defect: the private-preview
`frontend` service inherited the server runtime env file, exposing server-only
credentials (`DEEPSEEK_API_KEY`, `GUARDIAN_API_KEY`, `GUARDIAN_SESSION_SECRET`,
`GUARDIAN_JWT_SECRET`) to the browser-facing container.

## 2. Workflow classification

- Execution lane: architecture-impact
- Task kind: Compose overlay boundary repair
- Evidence posture: static configuration proof, deterministic regression test, canonical static gate

## 3. ADR impact

Classification: Aligned with existing ADR(s)

Governing ADRs:
- ADR-039 Operator / User Access Boundary
- ADR-040 Network Profile Topology Resolution Contract
- ADR-052 Whoosh'd Gemma and Approved DeepSeek Startup Profile
- ADR-039 Capability-Oriented Mesh Architecture (capability-mesh record at `docs/architecture/adr/039-capability-oriented-mesh-architecture.md`)

Reason: This task repairs enforcement of an already-established credential and browser/server
authority boundary. It does not introduce a new topology or provider contract.

## 4. Previous blocking proof and commit

Previous proof: [2026-08-11-private-preview-profile-static-gate-proof.md](2026-08-11-private-preview-profile-static-gate-proof.md)
Previous proof commit: `caa7ba9a9102b32e2702b5889248d332768f8531`

The previous proof reached `NEXT_PROOF_NEEDED` because the fully reconciled durable
`.env.private-preview` exposed the Compose boundary defect: the resolved `frontend`
service received the server-only `DEEPSEEK_API_KEY` field.

## 5. Task branch and pre-task HEAD

- Task branch: `codex/publish-codexify-private-preview`
- Pre-task HEAD: `caa7ba9a9102b32e2702b5889248d332768f8531`

## 6. Source-cause confirmation

Confirmed in repository state:

- `/docker-compose.yml` line 988: `frontend` has `env_file: ${CODEXIFY_RUNTIME_ENV_FILE:-.env}`
- `/docker-compose.private-preview.yml` line 62: `frontend` resets `ports: !reset []` but does not reset `env_file`
- The private-preview runtime resolves `CODEXIFY_RUNTIME_ENV_FILE` to `.env.private-preview`
- Therefore server-only fields in `.env.private-preview` enter the resolved frontend container environment

Source cause confirmed: **PASS**

## 7. Compose overlay change

Modified `docker-compose.private-preview.yml` frontend service:

```yaml
frontend:
  ports: !reset []
  env_file: !reset []
  environment:
    VITE_GUARDIAN_API_BASE: ""
    VITE_GUARDIAN_AUTH_MODE: "remote"
    VITE_GUARDIAN_API_KEY: ""
    VITE_GUARDIAN_DEV_API_KEY: ""
    VITE_PRIVATE_PREVIEW: "true"
    VITE_PREVIEW_FEEDBACK_EMAIL: "${CODEXIFY_PREVIEW_FEEDBACK_EMAIL:-}"
```

Adds `env_file: !reset []` using the existing Compose reset idiom already used for ports.

Base `docker-compose.yml` unchanged. Backend and worker-chat continue receiving `.env.private-preview`.

## 8. Regression-test change

Modified `tests/ops/test_private_preview_contract.py`:

- Added `SENTINEL_ENV_CONTENT` with inert test literals for `DEEPSEEK_API_KEY`, `GUARDIAN_API_KEY`, `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`
- Extended `_render_compose()` to accept an optional `runtime_env_file` parameter that sets `CODEXIFY_RUNTIME_ENV_FILE`
- Added new test `test_private_preview_frontend_env_file_isolation_prevents_server_credential_leak()` that creates a temporary inert env file, renders the full Compose configuration with it, and proves:
  1. backend receives the inert `DEEPSEEK_API_KEY`
  2. worker-chat receives the inert `DEEPSEEK_API_KEY`
  3. frontend does not contain `DEEPSEEK_API_KEY`
  4. frontend does not contain `GUARDIAN_API_KEY`
  5. frontend does not contain `GUARDIAN_SESSION_SECRET`
  6. frontend does not contain `GUARDIAN_JWT_SECRET`
  7. frontend `VITE_GUARDIAN_API_KEY` equals `""`
  8. frontend `VITE_GUARDIAN_DEV_API_KEY` equals `""`
- Strengthened `test_private_preview_compose_keeps_browser_secrets_empty` to also assert absence of `GUARDIAN_API_KEY`, `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`

## 9. Static-validator change

Modified `scripts/private_preview_validate.sh`:

Strengthened the frontend-secret assertion region from checking only `DEEPSEEK_API_KEY` to checking all four server-only fields: `DEEPSEEK_API_KEY`, `GUARDIAN_API_KEY`, `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`.

Uses field-presence checks only. Does not print values. Failure classification:
```
frontend must not receive server-only credential field: <FIELD_NAME>
```

## 10. Durable environment preservation result

- `/Volumes/Dev_SSD/Codexify-main/.env.private-preview`: mode `600`, ignored by `.gitignore:13:.env.*`, untracked
- No modification to durable environment
- **PASS**

## 11. Backend DeepSeek credential-presence result

Resolved Compose configuration shows `DEEPSEEK_API_KEY` present and non-empty in `backend` service environment.
- **PASS**

## 12. Worker-chat DeepSeek credential-presence result

Resolved Compose configuration shows `DEEPSEEK_API_KEY` present and non-empty in `worker-chat` service environment.
- **PASS**

## 13. Frontend DEEPSEEK_API_KEY isolation result

Resolved Compose configuration shows `DEEPSEEK_API_KEY` absent from `frontend` service environment.
- **PASS**

## 14. Frontend Guardian server-secret isolation result

Resolved Compose configuration shows `GUARDIAN_API_KEY`, `GUARDIAN_SESSION_SECRET`, and `GUARDIAN_JWT_SECRET` absent from `frontend` service environment.
- **PASS**

## 15. Vite Guardian-key isolation result

Resolved Compose configuration shows `VITE_GUARDIAN_API_KEY=""` and `VITE_GUARDIAN_DEV_API_KEY=""` in `frontend` service environment.
- **PASS**

## 16. Published-port isolation result

Resolved Compose configuration shows sole published application port: `127.0.0.1:8081 -> 8080` on `private-preview-origin`.
- **PASS**

## 17. Canonical static validator result

```
static configuration proof: PASS
published ports: private-preview-origin 127.0.0.1:8081 -> 8080
```

Command:
```bash
CODEXIFY_RUNTIME_ENV_FILE=/Volumes/Dev_SSD/Codexify-main/.env.private-preview \
PRIVATE_PREVIEW_ENV_FILE=/Volumes/Dev_SSD/Codexify-main/.env.private-preview \
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
  bash scripts/private_preview_validate.sh static
```

The `CODEXIFY_RUNTIME_ENV_FILE` environment override was required to resolve the relative
path in the durable `.env.private-preview` against the task checkout's project directory.
This override does not modify the durable file and does not change the semantic check.

The previously blocked gate now passes.
- **PASS**

## 18. Focused preview test result

```
tests/auth/test_private_preview_access.py ...                            [ 27%]
tests/ops/test_private_preview_contract.py ......                        [ 81%]
tests/ops/test_private_preview_origin_recovery_contract.py ..            [100%]

======================== 11 passed, 2 warnings in 1.82s ========================
```

- Total passed: 11
- Total failed: 0
- **PASS**

## 19. Warning summary

2 non-failing warnings from pytest (pre-existing, not related to this change).

## 20. Cloudflare untouched confirmation

Cloudflare: untouched. No Tunnel, Access, DNS, or publication mutation occurred.

## 21. DNS untouched confirmation

DNS: untouched.

## 22. Cloudflare Access untouched confirmation

Cloudflare Access: untouched.

## 23. Render untouched confirmation

Render: untouched.

## 24. Tailscale untouched confirmation

Tailscale: untouched.

## 25. Services untouched confirmation

No services were started, stopped, or restarted.

## 26. Secret/exposure review

- No real credentials were printed, dumped, or exposed
- The durable `.env.private-preview` was never read for display
- Resolved Compose JSON was inspected via bounded Python field-presence checks only
- The temporary resolved Compose file was deleted after inspection
- Inert test literals (`inert-deepseek-key`, `inert-guardian-key`, `inert-session-secret`, `inert-jwt-secret`) are obviously non-real and are used only in test fixtures
- No credential hashes, fingerprints, or lengths were computed

## 27. What this proves

- The private-preview `frontend` service no longer inherits the server runtime env file
- Backend and worker-chat continue to receive the DeepSeek credential
- The four server-only credential fields are absent from the frontend container environment
- The Vite Guardian-key contract (empty `VITE_GUARDIAN_API_KEY`, `VITE_GUARDIAN_DEV_API_KEY`) is preserved
- The published-port isolation contract (exactly `127.0.0.1:8081 -> 8080`) is preserved
- A deterministic regression test reproduces the actual env-file inheritance seam
- The canonical static validator now passes, including the expanded server-field checks
- The durable `.env.private-preview` was not modified

## 28. What this does not prove

- Runtime behavior (no services were started)
- Live provider execution
- Cloudflare Tunnel or Access behavior
- Public-host reachability
- Authenticated session or preview access
- Frontend Vite dev server startup
- Browser bundle behavior with real credentials
- Full end-to-end private-preview publication

## 29. Final classification

**PASS**

All 23 PASS requirements are satisfied:
1. Base `/docker-compose.yml` is unchanged
2. Private-preview frontend explicitly resets inherited `env_file`
3. Backend still receives `DEEPSEEK_API_KEY`
4. Worker-chat still receives `DEEPSEEK_API_KEY`
5. Frontend does not receive `DEEPSEEK_API_KEY`
6. Frontend does not receive `GUARDIAN_API_KEY`
7. Frontend does not receive `GUARDIAN_SESSION_SECRET`
8. Frontend does not receive `GUARDIAN_JWT_SECRET`
9. `VITE_GUARDIAN_API_KEY` remains empty
10. `VITE_GUARDIAN_DEV_API_KEY` remains empty
11. Private-preview port isolation remains unchanged
12. Deterministic regression coverage proves the runtime-env inheritance seam
13. Canonical static validator passes
14. Focused preview contracts pass
15. Durable `.env.private-preview` remains mode 600, ignored, and untracked
16. Durable `.env.private-preview` is not modified
17. Cloudflare remains untouched
18. DNS remains untouched
19. Cloudflare Access remains untouched
20. Render remains untouched
21. Tailscale remains untouched
22. Services remain untouched
23. No credential exposure occurs

## 30. Exact next gate

Resume the Cloudflare public-preview publication proof.

Before any Cloudflare mutation, the next Architecture-Impact task must first prove
the live local origin:

```bash
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
  bash scripts/private_preview_validate.sh reachability
```

If the runtime is not currently using the repaired Compose source, the next task
must stop rather than publish an older configuration.

Once the repaired runtime and local reachability are proven, continue with:
1. Identify the existing Cloudflare Tunnel
2. Determine local-managed versus remote-managed tunnel posture
3. Verify or attach `preview.codexify.space` to that existing tunnel
4. Preserve the existing Cloudflare Access boundary
5. Prove anonymous traffic cannot bypass Access
6. Prove an approved Access identity can reach Codexify
7. Prove public frontend and health/chat/LLM paths
8. Confirm sensitive routes retain their private-preview policy
9. Leave `codexify.space` and `www.codexify.space` untouched
10. Leave Render and Tailscale untouched
