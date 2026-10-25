from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.webui-runtime.yml"
DOCKERFILE_PATH = ROOT / "frontend" / "Dockerfile.webui"
DOCKERIGNORE_PATH = ROOT / "frontend" / "Dockerfile.webui.dockerignore"
APP_PACKAGE_PATH = ROOT / "frontend" / "src" / "package.json"
ROOT_LOCKFILE_PATH = ROOT / "pnpm-lock.yaml"


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
    assert "context: ." in text
    assert "dockerfile: frontend/Dockerfile.webui" in text
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
    app_package = APP_PACKAGE_PATH.read_text(encoding="utf-8")
    root_lockfile = ROOT_LOCKFILE_PATH.read_text(encoding="utf-8")

    assert DOCKERFILE_PATH.is_file()
    assert DOCKERIGNORE_PATH.is_file()
    assert APP_PACKAGE_PATH.is_file()
    assert ROOT_LOCKFILE_PATH.is_file()
    assert '"@tailwindcss/postcss": "^4.1.14"' in app_package
    assert '"@heroicons/react": "2.2.0"' in app_package
    assert "'@heroicons/react':" in root_lockfile
    assert "'@tailwindcss/postcss':" in root_lockfile
    assert "VITE_WEBUI_COMPOSE_BUNDLE=1" in dockerfile
    # The build installs from the canonical root workspace lockfile.
    assert "COPY package.json ./package.json" in dockerfile
    assert "COPY pnpm-lock.yaml pnpm-workspace.yaml ./" in dockerfile
    assert "COPY frontend/src/package.json ./frontend/src/package.json" in dockerfile
    assert "RUN pnpm install --frozen-lockfile" in dockerfile
    # `--include=dev` is not a valid pnpm 9 install option: it makes pnpm
    # reject the whole invocation as an unknown `add` option.
    assert "--include=dev" not in dockerfile
    assert "COPY frontend/src ./frontend/src" in dockerfile
    assert "RUN pnpm --dir frontend/src exec vite build" in dockerfile
    assert "COPY --from=builder /app/frontend/src/dist /usr/share/nginx/html" in dockerfile
    # No frontend-local install root may be reintroduced.
    assert "COPY src ./src" not in dockerfile
    assert "ln -s ../node_modules" not in dockerfile
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
    # The build context is the repository root, so the root .dockerignore (which
    # excludes /frontend) must be overridden by a Dockerfile-scoped ignore file.
    assert "!package.json" in dockerignore
    assert "!pnpm-lock.yaml" in dockerignore
    assert "!pnpm-workspace.yaml" in dockerignore
    assert "!frontend/src/**" in dockerignore
    assert "!frontend/Dockerfile.webui" in dockerignore
