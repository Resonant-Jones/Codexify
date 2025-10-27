---
version: 1.0  
author: Codex (Resonant Constructs)  
created: 2025-10-27  
category: maintenance  
type: archival  
status: active  
---

## PCX_LEGACY_001 – Legacy Archival Protocol
**Purpose:** Safely move deprecated or obsolete modules into `archive/legacy` to preserve development history without impacting runtime execution or CI/CD workflows.

**Rules:**
1. Verify the target file is unused via import search:
   ```bash
   grep -r "media_db" guardian --include="*.py"
   ```
   Proceed only if no active imports are found.
2. Move deprecated modules to the archive:
   ```bash
   mkdir -p archive/legacy
   git mv guardian/core/media_db.py archive/legacy/media_db.py
   git commit -m "chore: archive unused media_db.py after ORM migration"
   ```
3. Add deprecation notice to the file header:
   ```python
   # DEPRECATED: Archived on 2025-10-27
   # Superseded by ORM models in guardian/db/models.py and Alembic revision 9373693cc12e.
   ```
4. Exclude archived modules from CI:
   - Add `archive/legacy/` to `.flake8` exclude list.
   - Add `archive/legacy/` to `.pytestignore`.
5. Document all archival actions in this system ledger with the superseding revision or feature.
6. Never import from `archive/legacy` in runtime or tests.

**Verification:**
Run:
```bash
pytest --ignore=archive/legacy
```
Expected output:
✅ No import or linting references to archived modules detected.

---

## Archival Execution Log

### 2025-10-27: media_db.py Archival
**Status:** ✅ COMPLETE
**Executor:** Code Health Maintainer (Claude)
**Superseded By:**
- ORM Models: `guardian/db/models.py` (UploadedImage, GeneratedImage, UploadedDocument, GeneratedDocument, TTSOutput)
- Alembic Migration: `9373693cc12e_add_media_and_tts_tables.py`
- Storage Layer: `guardian/core/storage.py`
- REST API: `guardian/routes/media.py`

**Actions Taken:**
1. ✅ Verified zero active imports (`grep -r "from.*media_db import"` returned no results)
2. ✅ Created `archive/legacy/` directory structure
3. ✅ Moved file with git history preservation: `git mv guardian/core/media_db.py archive/legacy/media_db.py`
4. ✅ Added deprecation notice to archived file header (lines 2-12)
5. ✅ Updated `pytest.ini` to ignore archive: `--ignore=archive/legacy`
6. ✅ Updated `pyproject.toml` black/isort exclusions to skip `archive/`
7. ✅ Updated `guardian/db/SETUP_GUIDE.md` to use new ORM examples instead of deprecated media_db

**Validation:**
```bash
# No imports found
grep -r "from.*media_db import" guardian --include="*.py"
# Result: (empty)

# Pytest configured to skip
pytest --ignore=archive/legacy
# Result: Tests run without touching archive
```

**Git Commit:**
```bash
git add archive/legacy/media_db.py
git add pytest.ini pyproject.toml guardian/db/SETUP_GUIDE.md memory-bank/systemPatterns.md
git commit -m "chore: archive media_db.py after ORM migration (PCX_LEGACY_001)"
```

---