# Image Gallery & Image Generation Validation Playbook (Task 008)

This playbook defines a deterministic validation loop for the `/api/media/images` and `/api/media/generate/image` endpoints so audit teams can confirm gallery integrity without guesswork.

## Prerequisites
- `docker --version` and `docker compose version` return successfully (Docker Engine >= 29, Compose >= v5).
- `.env` or shell exports provide:
  - `GUARDIAN_API_KEY` — service key with gallery + generation scope.
  - `LLM_PROVIDER` — the model backend (`local`, `openai`, or `groq`). Cloud providers require matching API keys and `ALLOW_CLOUD_PROVIDERS=true`.
  - Any provider-specific key (e.g., `OPENAI_API_KEY`, `GROQ_API_KEY`).
- Task 003 (`/media` static asset proxy) is healthy; otherwise `src_url` fetch checks will fail even when metadata is correct.

## Environment Preparation
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
docker compose up -d db redis backend
```
Wait for `backend` logs to show `Application startup complete` or poll `http://localhost:8888/health` until it returns `200`.

## Validation Steps
### 1. Baseline gallery probes
```bash
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/media/images?tag=uploaded&limit=5" | jq '.items'

curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/media/images?tag=generated&limit=5" | jq '.items'
```
**Pass criteria**
- HTTP 200 and JSON with `items` array for each tag.
- Each item includes `id`, `tag`, `src_url`, `created_at`.
- `tag` values align with the requested filter (`uploaded` / `generated`).

**Fail criteria**
- HTTP error, empty array when known fixtures exist, or missing required keys.

### 2. Deterministic generation + gallery refresh
```bash
GEN_PAYLOAD='{"prompt":"audit test image","model":"dall-e-3","project_id":1,"thread_id":1,"user_id":"default"}'
GEN_RESPONSE=$(curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$GEN_PAYLOAD" \
  http://localhost:8888/api/media/generate/image)
```
Capture these fields via `jq` for audit records:
```bash
GEN_ID=$(echo "$GEN_RESPONSE" | jq -r '.id')
GEN_SRC=$(echo "$GEN_RESPONSE" | jq -r '.src_url')
```
Immediately re-query the generated gallery and assert that the new `id` is present:
```bash
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/media/images?tag=generated&limit=5" | jq '.items | map(.id)'
```
**Pass criteria**
- Generation response returns HTTP 200 with non-null `id`, `prompt`, `src_url`, `tag="generated"`.
- Follow-up gallery call contains `GEN_ID` in `items`.

**Fail criteria**
- Generation response omits keys, `tag` ≠ `generated`, or gallery refresh lacks the new `id` within the first page (limit=5) after retrying for ≤10 seconds.

### 3. `/media` fetchability probe (Task 003 dependency)
```bash
curl -sS -o /tmp/image_validation_probe.bin "$GEN_SRC"
```
**Pass criteria**
- Command exits 0 and downloads >0 bytes, proving `/media` proxy reachable in the same runtime.

**Fail criteria**
- Curl exits non-zero, hangs, or downloads zero bytes — indicates Task 003 regression or missing static middleware.

## Automation
Run `./scripts/validate_image_gallery.sh` for a single-shot version with explicit pass/fail output (see script for details). The script will:
1. Verify env vars and provider prerequisites (`LLM_PROVIDER`, `GUARDIAN_API_KEY`).
2. Ensure required services are up (via `docker compose`).
3. Execute the curl probes and generation run with deterministic prompts.
4. Fail fast when `/media` fetch breaks, spotlighting Task 003 as the dependency bottleneck.

Record the console transcript as audit evidence. Stop containers with `docker compose down` when finished.
