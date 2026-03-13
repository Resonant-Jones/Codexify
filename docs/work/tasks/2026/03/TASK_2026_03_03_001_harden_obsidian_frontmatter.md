# TASK-2026-03-03-001: Harden Obsidian Frontmatter Parsing (Beta Core)

## Metadata

- Task-ID: TASK-2026-03-03-001
- Campaign-ID: CAMPAIGN_BETA1_CORE_STABILITY
- Branch: codex/explain-ingestobsidian-flag-error
- Repo root: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Owner: resonant_jones
- Risk: LOW
- Commit mode: two-phase

## Objective

Obsidian ingestion no longer fails on malformed or pseudo-frontmatter; malformed YAML is treated as plain content, ingest continues deterministically, and zero documents are dropped.

## Status

DONE

## What Changed

- Hardened frontmatter parsing in `guardian/cli/ingest_cli.py`.
- Wrapped YAML parse in defensive `try/except`.
- On parse failure, parser now returns:
  - `frontmatter: {}`
  - `content: <full original file text>`
- Added deterministic warning logging once per affected file:
  - `frontmatter_parse_failed:<file_path>`
- Preserved ingest schema and vector store behavior.
- No API surface changes.

## Verification

- Direct ingest run used real vault path:
  - `/Users/resonant_jones/Library/Mobile Documents/iCloud~md~obsidian/Documents/Axis_Node`
- Command:
  - `python -m guardian.cli.ingest_cli ingest-obsidian "$OBSIDIAN_DIR"`
- Result:
  - `{"ingested": 471, "dir": "/Users/resonant_jones/Library/Mobile Documents/iCloud~md~obsidian/Documents/Axis_Node"}`
- Exit code:
  - `0`
- Expected warning logs observed for malformed frontmatter files.
- No YAML traceback occurred.

## Commands Run

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
python -m compileall guardian/cli/ingest_cli.py
source .venv/bin/activate
export LOCAL_EMBED_MODEL="/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/models/bge-large-en-v1.5"
export CODEXIFY_EMBEDDINGS_BACKEND=local
export OBSIDIAN_DIR="/Users/resonant_jones/Library/Mobile Documents/iCloud~md~obsidian/Documents/Axis_Node"
python -m guardian.cli.ingest_cli ingest-obsidian "$OBSIDIAN_DIR"
```

## Scope Check

- git status clean before start: yes
- only allowed files modified: yes

## Commit Info

- Commit mode: two-phase
- Commit A hash: `b0ffe43c`
- Commit B hash: recorded in campaign mapping update commit

## Notes

- `guardian/ingestion` path does not exist in this repository; implementation was applied in `guardian/cli/ingest_cli.py`.
