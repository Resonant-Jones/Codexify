# Image Gallery + Image Generation Validation (Task 003)

This playbook validates the deterministic loop for:
- `GET /api/media/images`
- `POST /api/media/generate/image`

The contract baseline is:
- Gallery payload shape uses `images` plus `count`.
- Generation payload shape uses `id`, `src_url`, `prompt`, `model`, `created_at`.

## Prerequisites
- Docker daemon is available.
- `GUARDIAN_API_KEY` is exported.
- `LLM_PROVIDER` is exported (`local`, `openai`, or `groq`).
- Provider key is exported when using cloud backends (`OPENAI_API_KEY` or `GROQ_API_KEY`).

## Deterministic Steps
1. Start required services.
```bash
docker compose up -d db redis backend
```

2. Capture gallery baseline.
```bash
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/media/images?limit=20"
```
Pass criteria:
- HTTP 200.
- JSON contains `images` array.
- Each returned object includes `id`, `src_url`, `source_tag`, `created_at`.

3. Generate one image with deterministic payload.
```bash
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"audit test image","model":"dall-e-3","project_id":1,"thread_id":1,"user_id":"default"}' \
  "http://localhost:8888/api/media/generate/image"
```
Pass criteria:
- HTTP 200.
- JSON contains non-null `id`, `src_url`, `prompt`, `model`, `created_at`.

4. Refresh gallery and verify the generated id appears under `source_tag="generated"`.
```bash
curl -sS -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/media/images?limit=20"
```
Pass criteria:
- Generated id appears in the refreshed `images` array.
- Generated count does not regress.

5. Verify `/media` fetchability.
```bash
curl -sS -o /tmp/image_validation_probe.bin "$GEN_SRC"
```
Pass criteria:
- Download succeeds and file size is greater than zero bytes.

## Automation Command
Run from repository root:

```bash
bash scripts/validate_image_gallery.sh
```

Script guarantees:
- explicit pass/fail exit code,
- contract checks against `images` list payload,
- canonical generation-field checks,
- media fetch probe for runtime accessibility.
