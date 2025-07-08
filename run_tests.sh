

#!/bin/bash
# Sovereign ThreadSpace Test Runner
set -e

echo "🔍 Setting PYTHONPATH to project root..."
export PYTHONPATH=$(pwd)

echo "✅ Running all Guardian plugin and system tests..."
pytest guardian/ --asyncio-mode=strict -v --tb=short