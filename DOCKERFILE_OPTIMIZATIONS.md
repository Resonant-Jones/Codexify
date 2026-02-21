# Dockerfile Production Optimizations

## Summary

I've created two production-optimized Dockerfiles to replace your development versions. These use multi-stage builds to significantly reduce runtime image sizes and improve security.

**Files created:**
- `frontend/Dockerfile.prod` — Optimized React/Vite frontend
- `backend/Dockerfile.prod` — Optimized Python backend

---

## Frontend Optimizations (`frontend/Dockerfile.prod`)

### Changes:
1. **Multi-stage build** (Builder → Runtime)
   - **Builder stage**: Installs dev dependencies, builds Vite bundle to `/app/src/dist`
   - **Runtime stage**: Lightweight Node Alpine + `serve` CLI to serve the static dist folder

2. **Removed dev dependencies** from production image
   - Dev dependencies (Vite, testing tools, etc.) only exist during build
   - Runtime includes only `serve` for static file serving

3. **Better layer caching**
   - `package.json` and `pnpm-lock.yaml` copied separately (cached layer)
   - Source code copied after, so dependency rebuilds only on lock changes

4. **Non-root user**
   - Creates `nodejs:nodejs` user (UID 1001), runs app as non-root for security

5. **Smaller base image**
   - Uses `node:20-alpine` (minimal OS footprint)

6. **Security improvements**
   - User permission restrictions
   - No build tools in runtime image
   - Health check ready (can add to compose)

### Result:
- Old image: `1.45GB` (includes all dev tools, source)
- New image: ~300–400MB (estimated, 70% smaller)

---

## Backend Optimizations (`backend/Dockerfile.prod`)

### Changes:
1. **Multi-stage build** (Builder → Runtime)
   - **Builder stage**: Installs all dependencies, compiles Python wheels to `/tmp/wheels`
   - **Runtime stage**: Minimal Python slim image + wheels installed (no build tools)

2. **Removed build tools from runtime**
   - Builder includes: `build-essential`, `gcc`, `libpq-dev`, `linux-headers`
   - Runtime includes only: `libpq5`, `curl`, `ca-certificates` (runtime deps)

3. **Pre-compiled wheels**
   - Dependencies are built once in builder, wheels cached as layer
   - Runtime install uses `--no-index` (no network calls) against cached wheels
   - Faster builds after first build; consistent reproducibility

4. **Single clean pip install**
   - Removed redundant `apt-get` calls (was called twice in original)
   - Consolidated all system deps into one clean layer

5. **Non-root user**
   - Creates `appuser:appuser`, runs uvicorn as non-root

6. **Proper healthcheck**
   - HTTP ping to `/ping` endpoint with 30s start grace period
   - 10s interval, 5s timeout, 3 retries

7. **Better entrypoint**
   - Cleaner startup sequence with proper error handling
   - Waits for DB, runs migrations, seeds defaults, then starts uvicorn

### Result:
- Old image: `3.92GB` (includes compiler, source, build detritus)
- New image: ~1.2–1.5GB (estimated, 60-70% smaller)

---

## How to Use

### Build production images:
```bash
# Frontend
docker build -f frontend/Dockerfile.prod -t codexify-frontend:prod .

# Backend
docker build -f backend/Dockerfile.prod -t codexify-backend:prod .
```

### Run locally for testing:
```bash
# Frontend (serve on 5173)
docker run -p 5173:5173 codexify-frontend:prod

# Backend (requires .env and DB connectivity)
docker run \
  -e DATABASE_URL="postgresql://codexify:codexify@localhost:5432/Codexify" \
  -p 8888:8888 \
  codexify-backend:prod
```

### Update docker-compose.yml for production:
Replace the `backend:` and `frontend:` service `build.dockerfile` lines:
```yaml
backend:
  build:
    context: .
    dockerfile: backend/Dockerfile.prod  # ← Change this
  # ... rest of config

frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile.prod  # ← Change this
  # ... rest of config
```

---

## Layer Caching Strategy

Both images are optimized for Docker layer caching:

**Frontend layers (in order):**
1. Base image (cached by Docker)
2. Install pnpm, build tools (changed rarely)
3. Copy lockfile (changed on dependency update)
4. Install dependencies (cached if lockfile unchanged)
5. Copy source code (changes frequently during development)
6. Build Vite (runs only if above layers change)
7. Runtime base image (cached)
8. Copy build output (fast copy, no rebuild)

**Backend layers (in order):**
1. Builder base (cached)
2. Install system build tools (changed rarely)
3. Copy requirements files (changed on dependency update)
4. Build wheels (cached if requirements unchanged)
5. Runtime base (cached)
6. Copy wheels (fast install from cache)
7. Copy application code (changes frequently)

---

## Security Improvements

1. **Non-root user execution**
   - Prevents privilege escalation if container is compromised
   - All processes run with minimal permissions

2. **Minimal base images**
   - No unnecessary OS packages or utilities
   - Smaller attack surface

3. **No build tools in runtime**
   - Can't compile malicious code inside running container
   - Reduces supply chain risk

4. **Health checks**
   - Container orchestrators can detect unhealthy instances
   - Automatic recovery in Kubernetes/Swarm

---

## Performance Notes

- **First build**: Slightly slower (downloads and caches wheels)
- **Subsequent builds**: Much faster (uses cached layers)
- **Production runtime**: Same performance as before (identical Python/Node versions)
- **Image pulls**: 60-70% smaller over network

---

## Troubleshooting

If the backend build fails:
- Check that `requirements.txt` exists in root or `backend/` or `requirements/` dir
- Ensure `backend/alembic.ini` exists (or the Dockerfile creates it)
- Verify `guardian/`, `backend/`, `codexify/` dirs exist at root

If frontend build fails:
- Check `src/package.json` and `src/pnpm-lock.yaml` exist
- Ensure `pnpm run build` succeeds locally (Vite compiles to `dist/`)
- Verify Vite output directory is `src/dist` (adjust CMD line if different)

---

## Next Steps

1. ✅ Test builds locally: `docker build -f backend/Dockerfile.prod .`
2. ✅ Verify health checks pass: `docker run --health-cmd='curl -f http://localhost:PORT/' ...`
3. Update `docker-compose.yml` to use `.prod` Dockerfiles for staging/production
4. Optionally: Use both dev (current) and prod (new) Dockerfiles depending on environment
5. Consider Docker Scout scanning: `docker scout cves codexify-backend:prod`
