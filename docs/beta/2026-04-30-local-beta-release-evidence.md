# 2026-04-30 Local Beta Release Evidence

This note records the GHCR pullability state for the local-beta runtime images and the fallback validation path for the webUI bundle.

## Registry Pull Checks

- Clean shell baseline: `docker logout ghcr.io`
- Runtime image pull: `docker pull ghcr.io/resonant-jones/codexify-runtime:local-beta`
  - Result: successful anonymous pull
- WebUI image pull: `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta`
  - Result: successful anonymous pull

## Interpretation

- `ghcr.io/resonant-jones/codexify-runtime:local-beta` is publicly pullable from a clean shell.
- `ghcr.io/resonant-jones/codexify-webui:local-beta` is publicly pullable from a clean shell.
- The low-friction webUI beta bundle path is now restored for anonymous pull from the registry.

## Fallback Validation Path

- The local bundle validation script remains the supported local-build fallback:
  - `bash scripts/verification/check_webui_runtime_bundle.sh`
- That script validates the Compose bundle and local frontend build, but it does not prove registry pullability.
This is the release evidence artifact for the patched private beta handoff.

It records the local beta GHCR distribution evidence for both supported entry paths:

- macOS desktop shell on Mac
- universal webUI Docker bundle for browser-only testers

Both paths use the same local backend runtime.

## Release Metadata

| Item | Value |
|---|---|
| Release date | 2026-04-30 |
| Upload hotfix commit | `0a331733f7b446aa52bc1b8b59dafa90c4117f2c` |
| webUI bundle commit | `36ba946b5fa57d1a02822401cd59bc76c7ff3726` |
| Runtime image tag | `ghcr.io/resonant-jones/codexify-runtime:local-beta` |
| webUI image tag | `ghcr.io/resonant-jones/codexify-webui:local-beta` |
| Runtime digest | `sha256:12b3990f5f7971df289e082d027f51b5345f6d9edbfd1a762dc0125651494b4d` |
| webUI digest recorded for beta handoff | `sha256:dd2d65761d592e1a87c9f72260091761fdf52fdc49ed202cd5932f728fa5a1b0` |

## Tester Path Distinction

### macOS Desktop Path

- This is the Tauri shell path for Mac testers.
- It is the desktop client surface, not the backend runtime.
- The desktop path still uses the same local backend runtime as the webUI bundle.
- Desktop testers should keep using `~/Codexify/.env` as the editable runtime config source.

### WebUI Docker Path

- This is the browser-only path for Linux, Windows, or Mac testers who want the web surface.
- It is served from the standalone webUI Docker bundle.
- It uses the same local backend runtime as the desktop path.
- The bundle listens on `http://localhost:3000`.

## Validation Commands Run

### Registry and Compose

```bash
docker pull ghcr.io/resonant-jones/codexify-runtime:local-beta
docker pull ghcr.io/resonant-jones/codexify-webui:local-beta
docker compose -f docker-compose.runtime.yml config
docker compose -f docker-compose.webui-runtime.yml config
```

### Packaged Runtime Checks

```bash
bash scripts/verification/check_compiled_runtime_image.sh ghcr.io/resonant-jones/codexify-runtime:local-beta
bash scripts/verification/check_webui_runtime_bundle.sh
docker compose -f docker-compose.webui-runtime.yml up -d
docker compose -f docker-compose.webui-runtime.yml ps
```

### Live Health Checks

```bash
curl -s http://localhost:8888/health | jq
curl -s http://localhost:8888/health/chat | jq
curl -s http://localhost:8888/api/health/llm | jq
curl -I http://localhost:3000
```

### Media Upload Proof

```bash
API_KEY="$(sed -n 's/^GUARDIAN_API_KEY=//p' .env | head -n1)"

curl -sS -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/codexify-beta-release-evidence.txt;type=text/plain" \
  http://127.0.0.1:8888/api/media/upload/document

curl -sS -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/codexify-beta-release-evidence.png;type=image/png" \
  -F "thread_id=1" \
  http://127.0.0.1:8888/api/media/upload/image

curl -sS -H "X-API-Key: ${API_KEY}" \
  http://127.0.0.1:8888/api/media/documents/1e0c1351-922f-4a0b-b577-2d9219185f44

curl -sS -H "X-API-Key: ${API_KEY}" \
  -D /tmp/codexify-beta-release-evidence-image.headers \
  -o /tmp/codexify-beta-release-evidence-fetched.png \
  http://127.0.0.1:8888/api/media/images/fe1e6659-f0c1-4938-bda4-cb794ae3e152
```

## Validation Results

### Registry and Compose

- `docker pull ghcr.io/resonant-jones/codexify-runtime:local-beta` succeeded.
- The runtime image pull reported digest `sha256:12b3990f5f7971df289e082d027f51b5345f6d9edbfd1a762dc0125651494b4d`.
- `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta` returned `unauthorized` from this shell.
- `docker compose -f docker-compose.runtime.yml config` succeeded.
- `docker compose -f docker-compose.webui-runtime.yml config` succeeded.

### Packaged Runtime Checks

- `bash scripts/verification/check_compiled_runtime_image.sh ghcr.io/resonant-jones/codexify-runtime:local-beta` passed.
- `bash scripts/verification/check_webui_runtime_bundle.sh` passed.
- The webUI bundle script built the frontend image locally and the daemon reported a local build digest of `sha256:34c5d7c0ccabc0d1fbf65c62cf83673b06e98fc6d30a82f18d6b16a38702492e` for the tag created in this shell.
- `docker compose -f docker-compose.webui-runtime.yml up -d` succeeded.
- `docker compose -f docker-compose.webui-runtime.yml ps` showed the backend and frontend up, with the backend healthy and the frontend publishing port 3000.

### Live Health Checks

- `GET /health` returned `status: ok`.
- `GET /health/chat` returned `status: healthy`, `redis: ok`, and a fresh worker heartbeat.
- `GET /api/health/llm` returned `status: ok` and `status: online`.
- `curl -I http://localhost:3000` was not reachable from this shell namespace during this run.
- `docker compose exec frontend sh -lc 'wget -S -O - http://127.0.0.1'` returned `HTTP/1.1 200 OK` from the frontend container itself.

### Upload Proof

- Document upload through `POST /api/media/upload/document` succeeded.
- The document upload returned id `09bd4942-7f54-4dcc-9939-1456173ca96a`.
- The document response returned `project_id: 1`, `thread_id: null`, `embedding_status: pending`, and `source_tag: uploaded`.
- Document fetch through `GET /api/media/documents/{id}` returned the same backend row, including `content`, `parsed_text`, and matching metadata.
- Image upload through `POST /api/media/upload/image` succeeded when bound to the existing thread context with `thread_id=1`.
- The image upload returned id `88ba3a3f-669f-45c2-934e-c45ffcc7b569`.
- Image fetch through `GET /api/media/images/{id}` returned `200 OK`, `content-type: image/png`, and byte-for-byte matching content against the uploaded file.
- Image upload without `thread_id` returned `422` with `error=thread_id_required` and `message=thread_id is required for image uploads.`
- The rejected missing-thread image upload did not add a new image row; the uploaded-image count stayed unchanged after the rejection path, and no row with filename `missing-thread-20260430.png` appeared in `/api/media/images`.
- These responses came from backend routes backed by the database and storage layer, not browser-only placeholder state.

## Known Inconclusive Validation

- Direct `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta` was unauthorized from this shell, so the registry digest `sha256:dd2d65761d592e1a87c9f72260091761fdf52fdc49ed202cd5932f728fa5a1b0` was not re-pulled here.
- The host-side `curl -I http://localhost:3000` command was not reachable from this shell namespace, so the frontend proof was confirmed via the compose bundle script and an internal container-local HTTP request instead.
- This artifact does not claim cloud hosting, remote multi-user deployment, or a public beta launch.

## Non-Goals

- Do not claim the Tauri shell is required for non-macOS testers.
- Do not collapse the desktop shell, browser webUI, backend runtime, and Compose orchestration into one install story.
- Do not alter runtime semantics, frontend config, or image tags.
- Do not include secrets, local API keys, or private machine paths.
- Do not claim broad beta signoff beyond the evidence recorded here.
