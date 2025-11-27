# Title
Make all datetimes timezone-aware (UTC) and fix the commit hook scope

# Context
The pre-commit hook blocks commits when it finds `datetime.utcnow()` in live source.
Current ripgrep output shows occurrences in live code and in test/demo/patch files.
We need to migrate live code to timezone-aware datetimes and narrow the hook so it
ignores tests, scripts, demos, archives, docs, and patch files.

# What to change (precise)
1) In ALL Python source under these live paths:
   - guardian/**/*.py
   - guardian_backend_api_main/guardian/**/*.py
   - (EXCLUDE any 'archive/**', 'demo/**', 'tests/**', 'scripts/**', and files ending in .md, .patch)
   Replace every usage of a naive UTC datetime with an aware one:
   - `datetime.utcnow()`                 -> `datetime.now(timezone.utc)`
   - `datetime.datetime.utcnow()`        -> `datetime.datetime.now(datetime.timezone.utc)`
   - Any `... = datetime.utcnow().isoformat()` -> `... = datetime.now(timezone.utc).isoformat()`
   - Any arithmetic like `datetime.utcnow() - X` -> `datetime.now(timezone.utc) - X`
   - Any assignments like `self.start_time = datetime.utcnow()` -> `self.start_time = datetime.now(timezone.utc)`

   Import rules (match the file’s existing style):
   - If the file has `from datetime import datetime` (maybe also timedelta):
       * Change it to include timezone: `from datetime import datetime, timezone` (and keep timedelta if present).
       * Use `datetime.now(timezone.utc)`.
   - If the file has `import datetime` or `import datetime as dt`:
       * Use module style consistently:
         `datetime.datetime.now(datetime.timezone.utc)` or `dt.datetime.now(dt.timezone.utc)`.
       * Do NOT introduce a second conflicting import style.
   - If a file currently mixes `import datetime` and `from datetime import ...`, normalize to the *existing majority style* in that file.
   - Do not change behavior other than timezone awareness.

   Edge cases:
   - Keep existing `timedelta` imports intact.
   - If a variable (e.g., `self.start_time`) is later used in subtraction, ensure its initialization is updated to an aware datetime too.
   - If a file already uses aware datetimes, do nothing there.

2) Update the local Git hook `.git/hooks/pre-commit` to only scan live source.
   Replace its content with this exact script (and ensure it remains executable):

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail

   # Only check tracked Python source files that are NOT tests, scripts, demos, archives, docs, or patches
   files=$(git ls-files '*.py' \
     ':!:tests/**' ':!:test_*.py' ':!:**/tests/**' \
     ':!:scripts/**' ':!:demo/**' ':!:archive/**' \
     ':!:**/*.md' ':!:**/*.patch' ':!:**/.egg-info/**')

   if [ -z "$files" ]; then
     exit 0
   fi

   if rg -n --no-heading 'datetime(\.datetime)?\.utcnow$begin:math:text$$end:math:text$' $files; then
     echo "❌ Found datetime.utcnow() in source. Use datetime.now(UTC)."
     echo "   If this is only in tests/scripts, commit with --no-verify."
     exit 1
   fi

   exit 0
