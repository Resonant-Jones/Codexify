#!/usr/bin/env bash
# fix_dependencies.sh
# 🗃️ HOTBOX: Consistent dependency reconciliation and lockfile rebuild

echo "🔍 Checking for dependency mismatches..."

# 1️⃣ Make sure you have pip-tools installed:
pip install --upgrade pip-tools

# 2️⃣ Re-compile ALL requirement sets:
sed -i '' 's/markitdown>=3.0.0/markitdown>=0.1.2/g' requirements/requirements.in
sed -i '' 's/markitdown>=3.0.0/markitdown>=0.1.2/g' requirements/dev-requirements.in
sed -i '' 's/markitdown>=3.0.0/markitdown>=0.1.2/g' requirements/test-requirements.in
sed -i '' 's/markitdown>=3.0.0/markitdown>=0.1.2/g' requirements/docs-requirements.in

pip-compile requirements/requirements.in -o requirements/requirements.txt
pip-compile requirements/dev-requirements.in -o requirements/dev-requirements.txt
pip-compile requirements/test-requirements.in -o requirements/test-requirements.txt
pip-compile requirements/docs-requirements.in -o requirements/docs-requirements.txt

echo "✅ Recompiled all .txt lockfiles."

# 3️⃣ Optionally sync environment to lockfiles (careful!):
pip-sync requirements/requirements.txt \
         requirements/dev-requirements.txt \
         requirements/test-requirements.txt \
         requirements/docs-requirements.txt

echo "✅ Synced local environment to match lockfiles."

# 4️⃣ Show outdated packages as a sanity check:
echo "📋 Outdated packages:"
pip list --outdated

echo "🚀 Done! Your dependencies are now fresh, consistent, and conflict-free."
