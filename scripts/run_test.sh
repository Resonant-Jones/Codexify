# run_tests.sh
#!/bin/bash

echo "🔁 Cleaning old logs..."
rm -f test_logs.txt

echo "🧪 Running pytest with verbose output..."
pytest -v > test_logs.txt

echo "✅ Done. Logs saved to test_logs.txt"
