#!/usr/bin/env sh
set -eu

OUT_FILE="${1:-.env}"

cat >"${OUT_FILE}" <<'EOF'
# Auto-generated for CI only.
# Do not use for local development secrets.

POSTGRES_USER=codexify
POSTGRES_PASSWORD=codexify
POSTGRES_DB=Codexify

GUARDIAN_API_KEY=ci-guardian-key
GUARDIAN_ADMIN_TOKEN=ci-admin-token

GENAI_API_KEY=dummy
NOTION_API_KEY=dummy
ANTHROPIC_API_KEY=dummy
OPENAI_API_KEY=dummy
GEMINI_API_KEY=dummy
GOOGLE_API_KEY=dummy
GROQ_API_KEY=dummy

NEO4J_USER=neo4j
NEO4J_PASS=ci-neo4j-pass

LLM_PROVIDER=local
EMBED_PROVIDER=local
LOCAL_BASE_URL=http://127.0.0.1:11434
LOCAL_CHAT_MODEL=ci-local-model
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
EOF

echo "Wrote CI env file to ${OUT_FILE}"
