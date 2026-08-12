# MLX Linux ARM64 dependency lock proof

Date: 2026-08-11

## 1. Scope

This architecture-impact task repaired the MLX dependency declarations and
generated lock so the Linux ARM64 Python 3.11 Docker builder can install the MLX
family without losing the Darwin Metal backend.

## 2. Workflow classification

- Execution lane: architecture-impact
- Task kind: dependency-lock repair
- Evidence posture: compatibility probe + lock edit + Docker build proof + contract test

## 3. ADR impact

Classification: Aligned with existing ADR(s)

Governing ADRs:
- ADR-052 Whoosh'd Gemma and Approved DeepSeek Startup Profile
- ADR-061 Capability-Oriented Mesh Architecture

Reason: This task repaired the dependency contract required to instantiate the
already accepted private-preview topology. It does not alter model identity,
provider routing, account authority, or ingress topology.

## 4. Previous blocking proof and commit

Previous proof: [2026-08-11-private-preview-runtime-startup-local-origin-proof.md](2026-08-11-private-preview-runtime-startup-local-origin-proof.md)
Previous proof commit: `e832a51b8b751df61f0667d8818ecc8a30380399`

That proof stopped at NEXT_PROOF_NEEDED because the shared Docker builder stage
failed with `mlx==0.29.3` not found on PyPI.

## 5. Task branch and pre-task HEAD

- Branch: `codex/stage2j-r5f-r2-live-replay`
- Pre-task HEAD: `dd4769dc6ae3d5c4cb7c62e72d209008b566645c`
- `git diff --check`: clean

## 6. Existing MLX-family lock inventory

Pre-repair state:

| File | Package | Version |
|------|---------|---------|
| `requirements/ai.in` | `mlx` | unpinned |
| `requirements/ai.in` | `mlx-lm` | unpinned |
| `requirements/ai.in` | `mlx-vlm` | unpinned |
| `requirements/all.txt` | `mlx` | 0.29.3 |
| `requirements/all.txt` | `mlx-lm` | 0.28.3 |
| `requirements/all.txt` | `mlx-metal` | 0.29.3 |
| `requirements/all.txt` | `mlx-vlm` | 0.3.4 |

`mlx-cpu` was absent from both files.

## 7. Current-version Linux ARM64 compatibility proof

```
docker run --rm --platform linux/arm64 python:3.11.14-slim \
  pip download --only-binary=:all: --no-deps "mlx==0.29.3"
```

Result: **FAIL** — `mlx==0.29.3` not found on PyPI (only 0.30.0+ available).

Exact error: `ERROR: Could not find a version that satisfies the requirement mlx==0.29.3 (from versions: 0.30.0, 0.30.1, ... 0.32.0)`

## 8. MLX 0.30.0 candidate compatibility proof

```
docker run --rm --platform linux/arm64 python:3.11.14-slim \
  pip download --only-binary=:all: "mlx[cpu]==0.30.0"
```

Result: **PASS** — `mlx-0.30.0-cp311-cp311-manylinux_2_35_aarch64.whl` and
`mlx_cpu-0.30.0-py3-none-manylinux_2_35_aarch64.whl` downloaded successfully.

## 9. mlx-lm compatibility result

```
docker run --rm --platform linux/arm64 python:3.11.14-slim \
  pip download --only-binary=:all: \
    "mlx[cpu]==0.30.0" "mlx-lm==0.28.3" "mlx-vlm==0.3.4"
```

Result: **PASS** — all three packages and their transitive dependencies resolve
together without version conflicts.

## 10. mlx-vlm compatibility result

**PASS** — included in the same resolution above. No upgrade required.

## 11. Canonical input change

`requirements/ai.in`: Replaced the single unqualified `mlx` declaration with two
platform-qualified declarations:

```diff
-mlx
+mlx==0.30.0; sys_platform == "darwin"
+mlx[cpu]==0.30.0; sys_platform == "linux"
```

`mlx-lm` and `mlx-vlm` remain unpinned in the input file.

## 12. Generated-lock platform contract

`requirements/all.txt` changes limited to three MLX-family packages:

| Change | Before | After |
|--------|--------|-------|
| `mlx` | `mlx==0.29.3` | `mlx==0.30.0` |
| `mlx-metal` | `mlx-metal==0.29.3` | `mlx-metal==0.30.0; sys_platform == "darwin"` |
| `mlx-cpu` | absent | `mlx-cpu==0.30.0; sys_platform == "linux"` |

Platform semantics:
- Darwin: `mlx=0.30.0` + `mlx-metal=0.30.0` (Metal backend)
- Linux: `mlx=0.30.0` + `mlx-cpu=0.30.0` (CPU backend)
- No platform receives both backends
- `mlx-metal` is gated behind `sys_platform == "darwin"`
- `mlx-cpu` is gated behind `sys_platform == "linux"`

## 13. Unrelated dependency preservation result

- `mlx-lm==0.28.3`: **unchanged**
- `mlx-vlm==0.3.4`: **unchanged**
- No other package versions modified: **PASS**

## 14. Regression-test result

`tests/ops/test_mlx_platform_dependency_contract.py` — **10 tests, 0 failures**

Proves:
1. `mlx==0.29.3` absent from lock
2. `mlx-metal==0.29.3` absent from lock
3. Darwin MLX 0.30.0 declared in input
4. Linux MLX CPU 0.30.0 declared in input
5. Linux-qualified mlx-cpu in lock
6. Darwin-qualified mlx-metal in lock
7. mlx-metal not installable under Linux marker
8. mlx-cpu not installable under Darwin marker
9. mlx-lm version unchanged
10. mlx-vlm version unchanged

## 15. Complete-lock dry-run result

```
docker run --rm --platform linux/arm64 -v $PWD:/repo:ro python:3.11.14-slim \
  pip install --dry-run -r /repo/requirements/all.txt
```

Result: **PASS** — all packages resolve. Key evidence: `Ignoring mlx-metal:
markers 'sys_platform == "darwin"' don't match your environment` proves platform
isolation is active and correct.

## 16. Shared builder build result

```
docker build --progress=plain -f backend/Dockerfile --target builder \
  -t codexify-backend-builder:mlx-lock-proof .
```

Result: **PASS** — built successfully in ~182 seconds.

## 17. Runtime image build result

```
docker build --progress=plain -f backend/Dockerfile --target runtime \
  -t codexify-backend-runtime:mlx-lock-proof .
```

Result: **PASS** — built successfully in ~92 seconds (reused builder cache).

## 18. Runtime import-smoke result

```python
import fastapi; import uvicorn; import psycopg; import redis
```

Result: `backend runtime imports: PASS`

## 19. Linux MLX CPU import/backend result

```python
import mlx
```

Result: `linux mlx import: PASS`

MLX 0.30.0 CPU backend is importable inside the Linux ARM64 container.

## 20. Private-preview static validator result

```
static configuration proof: PASS
published ports: private-preview-origin 127.0.0.1:8081 -> 8080
```

**PASS**

## 21. Focused preview contract result

```
tests/auth/test_private_preview_access.py ...              [ 14%]
tests/ops/test_private_preview_contract.py ......           [ 42%]
tests/ops/test_private_preview_origin_recovery_contract.py .. [ 52%]
tests/ops/test_mlx_platform_dependency_contract.py .......... [100%]

21 passed in 13.94s
```

- Passed: **21**
- Failed: **0**
- Warnings: **0**

## 22. codexify_private_preview not-started confirmation

`codexify_private_preview` was never started during this task. The runtime remains intentionally stopped pending the next startup task. **PASS**

## 23. Tester untouched confirmation

`codexify_tester` project was not modified in any way. **PASS**

## 24. Whoosh'd untouched confirmation

**Whoosh'd: untouched.**

## 25. Cloudflare untouched confirmation

**Cloudflare: untouched.**

## 26. DNS untouched confirmation

**DNS: untouched.**

## 27. Cloudflare Access untouched confirmation

**Cloudflare Access: untouched.**

## 28. Render untouched confirmation

**Render: untouched.**

## 29. Tailscale untouched confirmation

**Tailscale: untouched.**

## 30. cloudflared untouched confirmation

**cloudflared: untouched.**

## 31. What this proves

- `mlx==0.29.3` was genuinely unavailable on Linux ARM64 Python 3.11 (not a
  transient error).
- `mlx[cpu]==0.30.0` resolves and installs on the Linux ARM64 Docker build
  platform.
- Existing `mlx-lm==0.28.3` and `mlx-vlm==0.3.4` remain compatible with MLX 0.30.0.
- The platform-qualified lock correctly gates `mlx-metal` to Darwin and
  `mlx-cpu` to Linux.
- The complete requirements lock resolves in a dry-run on Linux ARM64.
- The shared Docker builder stage (previously blocked) now builds successfully.
- The backend runtime image builds successfully.
- Backend runtime import smoke passes.
- Linux MLX CPU backend is importable inside the container.
- The regression test enforces all platform-contract invariants deterministically.

## 32. What this does not prove

- The private-preview project starts successfully (purposefully deferred).
- Live frontend credential isolation.
- Live local origin reachability.
- Live chat/LLM health.
- Cloudflare/public-preview publication health.
- Whoosh'd inference inside Docker (MLX is installed for dependency surface, not
  for in-container inference — Whoosh'd remains the host runtime).

## 33. Final classification

**PASS**

## 34. Exact next gate

Resume the private-preview runtime startup from `/Volumes/Dev_SSD/Codexify-main`:

```
docker compose -p codexify_private_preview --env-file .env.private-preview \
  -f docker-compose.yml -f docker-compose.private-preview.yml \
  up -d --build
```

Then prove:
1. Preview-critical services reach steady state
2. Project working directory is `/Volumes/Dev_SSD/Codexify-main`
3. Running frontend server-secret isolation
4. Backend and worker-chat DeepSeek authority
5. Sole private-preview publication at `127.0.0.1:8081`
6. Canonical reachability validation
7. `/`, `/health`, `/health/chat`, `/api/health/llm`
8. `codexify_tester` untouched
9. Cloudflare, DNS, Access, Render, Tailscale, cloudflared untouched
