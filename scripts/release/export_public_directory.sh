#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/Public-Directory"
SOURCE_BUNDLE_DIR="${ROOT_DIR}/Codexify-Beta"

rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"

copy_file() {
  local src="$1"
  local dst="$2"
  if [[ -f "${src}" ]]; then
    mkdir -p "$(dirname "${dst}")"
    cp "${src}" "${dst}"
  fi
}

mkdir -p \
  "${TARGET_DIR}/docs/public/release-notes" \
  "${TARGET_DIR}/docs/public/install" \
  "${TARGET_DIR}/docs/public/security" \
  "${TARGET_DIR}/releases/Codexify-Beta" \
  "${TARGET_DIR}/docker" \
  "${TARGET_DIR}/dist"

copy_file "${ROOT_DIR}/LICENSE" "${TARGET_DIR}/LICENSE"
copy_file "${SOURCE_BUNDLE_DIR}/README.md" "${TARGET_DIR}/releases/Codexify-Beta/README.md"
copy_file "${SOURCE_BUNDLE_DIR}/AUTHORIZATION.md" "${TARGET_DIR}/releases/Codexify-Beta/AUTHORIZATION.md"
copy_file "${SOURCE_BUNDLE_DIR}/.env.example" "${TARGET_DIR}/releases/Codexify-Beta/.env.example"
copy_file "${SOURCE_BUNDLE_DIR}/docker-compose.yml" "${TARGET_DIR}/releases/Codexify-Beta/docker-compose.yml"

cat >"${TARGET_DIR}/README.md" <<'EOF'
# Codexify Core

This repository is the public snapshot for Codexify.

It is not the private Source Vault. It contains the curated files that are safe
to publish: the public handoff bundle, public docs, contribution guidance, and
security guidance.

Start here:

- Read `releases/Codexify-Beta/README.md` for the current handoff bundle.
- Read `docs/public/install/README.md` for the public install path.
- Read `docs/public/security/README.md` for the public security policy.

If you need the full development tree, internal notes, or unreleased work, that
stays in the private repository.
EOF

cat >"${TARGET_DIR}/SECURITY.md" <<'EOF'
# Security Policy

Codexify's public Publishing Portal is release-oriented. Do not report security
issues in public issues.

Use GitHub Security Advisories or a private maintainer contact channel for
responsible disclosure.

Do not commit secrets, credentials, personal data, or local runtime exports.
If something sensitive is discovered in a release artifact, rotate it and
remove the artifact from future public bundles.
EOF

cat >"${TARGET_DIR}/CONTRIBUTING.md" <<'EOF'
# Contributing

Public contributions are welcome through pull requests.

- Create a branch for your change.
- Open a PR against `main`.
- Keep changes focused and release-safe.
- Expect the maintainers to keep merge authority.

This portal is curated and release-oriented. It is not a live development firehose.
EOF

cat >"${TARGET_DIR}/.gitignore" <<'EOF'
.env
.env.*
!.env.example
!.env.template
dist/
node_modules/
*.log
.DS_Store
EOF

cat >"${TARGET_DIR}/.env.example" <<'EOF'
# Copy this file to `.env` before starting the public handoff bundle.
# Keep the values local-only and never commit your real `.env`.

ENV=development
LOG_LEVEL=INFO
DEBUG=true
PORT=8888
AI_BACKEND=ollama

POSTGRES_USER=codexify
POSTGRES_PASSWORD=codexify
POSTGRES_DB=Codexify

NEO4J_USER=neo4j
NEO4J_PASS=codexify-local-dev

GUARDIAN_AUTH_MODE=local
GUARDIAN_API_KEY=replace-with-long-random-value
GUARDIAN_SESSION_SECRET=replace-with-long-random-secret
GUARDIAN_JWT_SECRET=
GUARDIAN_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
GUARDIAN_CSP_POLICY=default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;
GUARDIAN_ENABLE_RATE_LIMITING=1
GUARDIAN_RATE_LIMITS=100/minute,1000/hour
GUARDIAN_ENABLE_SECURITY_HEADERS=1

LLM_PROVIDER=local
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_LOCAL_ONLY_MODE=true
CODEXIFY_BETA_CORE_ONLY=false
CODEXIFY_POLICY_MODE=enforce
CODEXIFY_CONFIG_SOURCE=legacy
CODEXIFY_SINGLE_USER_ID=local
CODEXIFY_EGRESS_ALLOWLIST=

LOCAL_BASE_URL=http://host.docker.internal:11434
LOCAL_DOCKER_FALLBACK_BASE_URL=http://host.docker.internal:11434
LOCAL_API_KEY=local
LOCAL_CHAT_MODEL=library2/ministral-3:8b
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
LOCAL_EMBEDDINGS_REQUIRED=0
LOCAL_COMPAT_FIRST=0
LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK=0
VAULTNODE_BASE_URL=http://host.docker.internal:11434

EMBEDDER_PROVIDER=local
EMBEDDING_BACKEND=local
CODEXIFY_EMBEDDINGS_BACKEND=local
CODEXIFY_VECTOR_STORE=chroma
CODEXIFY_CHROMA_PATH=./.chroma
CODEXIFY_COLLECTION=codexify_vault_supported

HF_HUB_OFFLINE=0
TRANSFORMERS_OFFLINE=0
EMBED_MODEL_ID=BAAI/bge-large-en-v1.5
EMBED_MODEL_REVISION=
HF_TOKEN=

OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-5.1
OPENAI_EMBED_MODEL=text-embedding-3-small
ANTHROPIC_API_KEY=
ANTHROPIC_CHAT_MODEL=claude-4-5-sonnet-latest
GEMINI_API_KEY=
GEMINI_CHAT_MODEL=gemini-1.5-flash
GROQ_API_KEY=
GROQ_BASE_URL=
MINIMAX_API_KEY=
MINIMAX_API_BASE=
MINIMAX_MODEL=
MINIMAX_TIMEOUT_SECONDS=60
NOTION_API_KEY=
DISCORD_BOT_TOKEN=
GITHUB_TOKEN=
GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY=
EOF

cat >"${TARGET_DIR}/docs/public/README.md" <<'EOF'
# Public Documentation

This folder holds the public-safe documentation for the Publishing Portal.

The private Source Vault may contain deeper architectural notes, internal run
books, and unreleased implementation details. Those stay out of this repo.
EOF

cat >"${TARGET_DIR}/docs/public/install/README.md" <<'EOF'
# Install

This folder explains the public install path for Codexify.

The current public handoff bundle lives in `releases/Codexify-Beta/`.
EOF

cat >"${TARGET_DIR}/docs/public/security/README.md" <<'EOF'
# Security

This folder holds public security guidance for the Publishing Portal.

Keep secrets local, rotate credentials when necessary, and use private channels
for vulnerability disclosure.
EOF

cat >"${TARGET_DIR}/docs/public/release-notes/README.md" <<'EOF'
# Release Notes

Stable public releases should be recorded here.

Use this folder for the curated release surface only, not for day-to-day private
development chatter.
EOF

cat >"${TARGET_DIR}/docker/README.md" <<'EOF'
# Docker

Docker-facing public release artifacts live here.

The current beta handoff bundle is stored under `releases/Codexify-Beta/`.
EOF

cat >"${TARGET_DIR}/dist/README.md" <<'EOF'
# Dist

Generated release archives can live here.

This folder is meant for release outputs, not source-of-truth code.
EOF

echo "Exported public portal tree to: ${TARGET_DIR}"
