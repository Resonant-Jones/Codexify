# Private-preview runtime startup local origin proof

Date: 2026-08-11

## 1. Scope

This architecture-impact task was to start the complete `codexify_private_preview`
Compose project from the durable checkout using the canonical private-preview
configuration, then prove the running local origin and running frontend credential
boundary.

## 2. Workflow classification

- Execution lane: architecture-impact
- Task kind: runtime startup and live credential-isolation proof
- Evidence posture: static preflight + live startup attempt + build-failure diagnosis

## 3. ADR impact

Classification: Aligned with existing ADR(s)

Governing ADRs:
- ADR-039 Operator / User Access Boundary
- ADR-040 Network Profile Topology Resolution Contract
- ADR-052 Whoosh'd Gemma and Approved DeepSeek Startup Profile
- ADR-061 Capability-Oriented Mesh Architecture

Reason: This task was to instantiate the already-defined private-preview runtime
topology and prove its live authority and credential boundaries. It does not
alter accepted architecture.

## 4. Previous blocking proof and commit

Previous proof: [2026-08-11-private-preview-live-local-origin-proof.md](2026-08-11-private-preview-live-local-origin-proof.md)
Previous proof commit: `a38ba7759bae9d4c5df1724af8a748027da4994a`

The previous proof stopped at NEXT_PROOF_NEEDED because no `codexify_private_preview`
Compose project was running.

## 5. Durable checkout branch and pre-task HEAD

- Branch: `codex/stage2j-r5f-r2-live-replay`
- Pre-task HEAD: `a38ba7759bae9d4c5df1724af8a748027da4994a`
- `git diff --check`: clean
- Pre-existing untracked: `.worktrees/render-relay-codexify/` (unrelated)

## 6. Durable environment isolation baseline

- `.env.private-preview` exists: **PASS**
- Mode: **600** (PASS)
- Ignored by `.gitignore:13:.env.*`: **PASS**
- Not tracked: **PASS**
- Contents not inspected: **PASS**

## 7. Tester project baseline

Captured 11 `codexify_tester` container identities before any mutation:

```
38fd7032d55a codexify_tester-frontend-1
4f26fb6d9d04 codexify_tester-redis-1
573979b1cac4 codexify_tester-neo4j-1
5a8a647bfdf7 codexify_tester-worker-chat-embed-1
5ab9f6407ccf codexify_tester-worker-warmup-1
707c2c95f113 codexify_tester-backend-1
8fdcb63c55bc codexify_tester-worker-chat-1
9a2794906893 codexify_tester-tailscale-codexify-test-1
b37dd1a7c744 codexify_tester-db-1
cd4c56bedcc4 codexify_tester-worker-document-embed-1
e0602ec3f73a codexify_tester-worker-account-import-1
```

No `codexify_private_preview` containers existed (stopped or running): **PASS**

## 8. Whoosh'd preflight result

- Whoosh'd endpoint reachable at `http://127.0.0.1:8000/v1/models`: **PASS**
- Required `gemma-4-12b-it-qat-4bit` model present: **PASS**

## 9. Static pre-start validator result

```
static configuration proof: PASS
published ports: private-preview-origin 127.0.0.1:8081 -> 8080
```

**PASS**

## 10. Resolved Compose isolation result

Rendered via `docker compose config --format json` (temp file, mode 600, deleted after parsing):

- All required services present (backend, worker-chat, frontend, private-preview-origin, db, redis): **PASS**
- frontend DEEPSEEK_API_KEY absent: **PASS**
- frontend GUARDIAN_API_KEY absent: **PASS**
- frontend GUARDIAN_SESSION_SECRET absent: **PASS**
- frontend GUARDIAN_JWT_SECRET absent: **PASS**
- frontend VITE_GUARDIAN_API_KEY empty: **PASS**
- frontend VITE_GUARDIAN_DEV_API_KEY empty: **PASS**
- backend DEEPSEEK_API_KEY present: **PASS**
- worker-chat DEEPSEEK_API_KEY present: **PASS**
- Sole host-published port: `127.0.0.1:8081 -> private-preview-origin:8080`: **PASS**
- No forbidden host publications: **PASS**

## 11. Canonical startup command

Executed from `/Volumes/Dev_SSD/Codexify-main`:

```
docker compose -p codexify_private_preview --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  up -d --build
```

Exit code: **1**

Elapsed: ~28 seconds (failed during build)

## 12. Startup result and duration

**FAILED** — build-stage failure in the shared `builder` Dockerfile stage.

A second attempt without `--build` also failed with the same error (elapsed ~14 seconds),
confirming the builder stage must execute for the required runtime image.

## 13. Preview-critical steady-state result

**Not reached.** No containers were created. The build failure in the shared
`builder` stage blocked all services including backend, worker-chat, frontend,
private-preview-origin, db, and redis.

## 14. One-shot initialization/migration result

**Not reached.** No PostgreSQL or Redis containers were created.

## 15. Compose working-directory ownership result

**Not reached.** No `codexify_private_preview` project was started.

## 16. Tester project preservation result

Post-attempt comparison of `codexify_tester` container identities to Phase 7 baseline:

```
tester project mutation: NONE
tester container identity preservation: PASS
```

All 11 tester containers unchanged.

## 17. Running frontend DEEPSEEK_API_KEY isolation result

**Not reached.** No frontend container was created.

## 18. Running frontend Guardian secret-isolation result

**Not reached.**

## 19. Running Vite Guardian-key isolation result

**Not reached.**

## 20. Backend DeepSeek authority result

**Not reached.** No backend container was created.

## 21. Worker-chat DeepSeek authority result

**Not reached.**

## 22. Live host-port isolation result

**Not reached.** No private-preview containers running.

## 23. Canonical reachability validator result

**Not reached.** The validator was run post-build-failure:

```
static configuration proof: PASS
curl: (7) Failed to connect to 127.0.0.1 port 8081
```

Static configuration passes; reachability fails (no runtime).

## 24. Root reachability result

**Not reached.**

## 25. Health result

**Not reached.**

## 26. Chat-health result

**Not reached.**

## 27. LLM-health result

**Not reached.**

## 28. Focused preview contract-test result

Tests were run independently (they do not require a running runtime):

```
tests/auth/test_private_preview_access.py ...              [ 27%]
tests/ops/test_private_preview_contract.py ......           [ 81%]
tests/ops/test_private_preview_origin_recovery_contract.py .. [100%]

11 passed in 7.21s
```

- Passed: **11**
- Failed: **0**
- Non-failing warnings: **0**

## 29. Warning summary

None.

## 30. Durable environment preservation result

Post-attempt checks:

- `.env.private-preview` mode: **600** (PASS)
- Ignored by `.gitignore:13:.env.*`: **PASS**
- Not tracked: **PASS**
- Contents not inspected: **PASS**

## 31. Repository/source preservation result

- `git status --short`: only `.worktrees/` untracked (pre-existing, unrelated)
- No source, Compose, test, or script files modified: **PASS**
- `git diff --check`: clean: **PASS**

## 32. Cloudflare untouched confirmation

**Cloudflare: untouched.**

## 33. DNS untouched confirmation

**DNS: untouched.**

## 34. Cloudflare Access untouched confirmation

**Cloudflare Access: untouched.**

## 35. Render untouched confirmation

**Render: untouched.**

## 36. Tailscale untouched confirmation

**Tailscale: untouched.**

## 37. cloudflared untouched confirmation

**cloudflared: untouched.**

## 38. Secret/exposure review

No secrets were printed, hashed, fingerprinted, or exposed. The `.env.private-preview`
file was never read. No container environment variables were inspected. No credential
values appear in this proof artifact.

## 39. What this proves

- Whoosh'd host dependency is healthy (reachable, Gemma model present): **PASS**
- Canonical static validator passes: **PASS**
- Resolved Compose configuration is correct (credential isolation, port bindings): **PASS**
- Focused private-preview contract tests pass (11/11): **PASS**
- `codexify_tester` project remains completely untouched: **PASS**
- `.env.private-preview` remains mode 600, ignored, untracked: **PASS**
- No source files were modified: **PASS**
- No infrastructure was touched: **PASS**

## 40. What this does not prove

- `codexify_private_preview` Compose project can start from the current durable checkout.
- Live frontend credential isolation.
- Live local origin reachability.
- Live chat/LLM health.
- Cloudflare/public-preview publication health.

The build failure prevents all runtime proof.

## 41. Final classification

**NEXT_PROOF_NEEDED**

## 42. Exact next gate

**Repair the `mlx==0.29.3` dependency pin in `requirements/all.txt` before
re-attempting private-preview startup.**

The exact failing runtime seam:

> `mlx==0.29.3` is no longer available on PyPI. Only versions 0.30.0+ are
> available. The `requirements/all.txt` file (line within the 15KB file) pins
> `mlx==0.29.3`. The shared Dockerfile `builder` stage uses this file during
> `pip install -r`, which fails for all build targets (`runtime`,
> `worker-coding-runtime`, `tts-runtime`). No Docker image can be built, so
> no container can start.

The failing seam is in the Docker build stage (`backend/Dockerfile` line 13-30,
`builder` target) because `requirements/all.txt` contains the unresolvable
`mlx==0.29.3` pin. This blocks ALL private-preview services, not just
non-preview-critical ones.

Recommended next atomic task:

A source-repair Architecture-Impact task to update `requirements/all.txt`:

1. Replace `mlx==0.29.3` with the latest available `mlx` version compatible
   with the project's dependency constraints (likely `mlx>=0.30.0`).
2. Rebuild the `codexify-backend-runtime:latest` image to confirm the fix.
3. Do not modify any other source, Compose, environment, test, script, or ADR file.
4. Do not start the private-preview project (that remains the next task after
   this dependency repair).

After the `mlx` pin is repaired and the Docker image builds successfully, resume
this runtime startup task.
