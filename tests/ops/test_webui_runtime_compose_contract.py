from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.webui-runtime.yml"
DOCKERFILE_PATH = ROOT / "frontend" / "Dockerfile.webui"
DOCKERIGNORE_PATH = ROOT / "frontend" / ".dockerignore"
FRONTEND_PACKAGE_PATH = ROOT / "frontend" / "package.json"
FRONTEND_LOCKFILE_PATH = ROOT / "frontend" / "pnpm-lock.yaml"


def test_webui_runtime_compose_contract_includes_frontend_and_runtime_images() -> None:
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert COMPOSE_PATH.is_file()
    assert "extends:" in text
    assert "service: db" in text
    assert "service: neo4j" in text
    assert "service: redis" in text
    assert "file: docker-compose.runtime.yml" in text
    assert "service: backend" in text
    assert "service: migrator" in text
    assert "service: worker-document-embed" in text
    assert "service: worker-chat-embed" in text
    assert "service: worker-warmup" in text
    assert "frontend:" in text
    assert "build:" in text
    assert "context: ./frontend" in text
    assert "dockerfile: Dockerfile.webui" in text
    assert "ports:" in text
    assert "3000:80" in text
    assert (
        "image: ${CODEXIFY_WEBUI_IMAGE_REGISTRY:-ghcr.io/resonant-jones}/codexify-webui:${CODEXIFY_WEBUI_IMAGE_TAG:-local-beta}"
        in text
    )
    assert "condition: service_healthy" in text


def test_webui_frontend_bundle_builds_static_assets_and_same_origin_proxy() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    dockerignore = DOCKERIGNORE_PATH.read_text(encoding="utf-8")
    frontend_package = FRONTEND_PACKAGE_PATH.read_text(encoding="utf-8")
    frontend_lockfile = FRONTEND_LOCKFILE_PATH.read_text(encoding="utf-8")

    assert DOCKERFILE_PATH.is_file()
    assert DOCKERIGNORE_PATH.is_file()
    assert FRONTEND_PACKAGE_PATH.is_file()
    assert FRONTEND_LOCKFILE_PATH.is_file()
    assert '"@tailwindcss/postcss": "^4.1.14"' in frontend_package
    assert '"@heroicons/react": "2.2.0"' in frontend_package
    assert "'@heroicons/react':" in frontend_lockfile
    assert "'@tailwindcss/postcss':" in frontend_lockfile
    assert "VITE_WEBUI_COMPOSE_BUNDLE=1" in dockerfile
    assert "COPY package.json ./package.json" in dockerfile
    assert "COPY pnpm-lock.yaml ./pnpm-lock.yaml" in dockerfile
    assert "RUN pnpm install --include=dev" in dockerfile
    assert "ln -s ../node_modules ./src/node_modules" in dockerfile
    assert "RUN pnpm run build" in dockerfile
    assert "COPY --from=builder /app/src/dist /usr/share/nginx/html" in dockerfile
    assert "client_max_body_size 100m" in dockerfile
    assert "location ^~ /api/ws/" in dockerfile
    assert "location ^~ /api/collab/ws/" in dockerfile
    assert "location ^~ /api/events" in dockerfile
    assert "location ^~ /api/" in dockerfile
    assert "location ^~ /health" in dockerfile
    assert "location ^~ /media/" in dockerfile
    assert "location = /docs" in dockerfile
    assert "location / {" in dockerfile
    assert "try_files $uri $uri/ /index.html;" in dockerfile
    assert "!Dockerfile.webui" in dockerignore
    assert "!package.json" in dockerignore
    assert "!pnpm-lock.yaml" in dockerignore
