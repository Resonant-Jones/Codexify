# scripts/setup-envs.sh
set -euo pipefail

ROOT="$(pwd)"
backend_env_dev=".env.development"
backend_env_prod=".env.production"
frontend_env_dev=".env.development"
frontend_env_prod=".env.production"

# generate a strong dev key (64 hex bytes)
DEV_KEY="$(python - <<'PY'
import secrets; print(secrets.token_hex(32))
PY
)"

cat > "$backend_env_dev" <<EOF
# FastAPI (development)
GUARDIAN_ENV=development
GUARDIAN_DB_PATH=${ROOT}/guardian/guardian.dev.db
GUARDIAN_API_KEY=${DEV_KEY}
GUARDIAN_ALLOWED_ORIGINS=http://localhost:5173
EOF

cat > "$backend_env_prod" <<'EOF'
# FastAPI (production) — set real values in your host/secret manager
GUARDIAN_ENV=production
GUARDIAN_DB_PATH=/var/lib/guardian/guardian.prod.db
GUARDIAN_API_KEY=REPLACE_WITH_STRONG_RANDOM
GUARDIAN_ALLOWED_ORIGINS=https://your-frontend-domain.tld
EOF

# Frontend (Vite) envs live at the project root of the Vite app.
# If your Vite app runs from this repo root (where vite.config.ts lives), keep them here.
cat > "$frontend_env_dev" <<EOF
# Vite (development)
VITE_GUARDIAN_API_BASE=http://127.0.0.1:8000
VITE_GUARDIAN_API_KEY=${DEV_KEY}
EOF

cat > "$frontend_env_prod" <<'EOF'
# Vite (production)
VITE_GUARDIAN_API_BASE=https://api.yourdomain.tld
VITE_GUARDIAN_API_KEY=demo-or-staging-key-if-you-must
EOF

# .gitignore hygiene
awk 'BEGIN{seen=0} {if($0 ~ /guardian\.guardian\.db|guardian\/guardian\..*\.db|\.env\.local/){seen=1} print} END{if(!seen){print "guardian/guardian.db"; print "guardian/guardian.*.db"; print ".env.local"}}' .gitignore > .gitignore.new || true
mv .gitignore.new .gitignore

echo "--------------------------------------------------"
echo "Created:"
printf "  %s\n  %s\n  %s\n  %s\n" "$backend_env_dev" "$backend_env_prod" "$frontend_env_dev" "$frontend_env_prod"
echo "Dev API key (copied to dev backend & frontend):"
echo "  $DEV_KEY"
echo "Updated .gitignore with DB patterns and .env.local"
echo "--------------------------------------------------"
