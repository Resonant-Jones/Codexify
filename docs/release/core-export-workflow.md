# Core Export Workflow

## Purpose

This document defines the local-only `Publishing_Portal/Core/` source-mirror
workflow. It syncs the active Codexify core source from the parent repo into the
sibling `Publishing_Portal/` repo for public-facing packaging and review.

This is a **source mirror**, not a release, snapshot, or curated handoff bundle.
The existing public portal snapshot workflow
([`public-portal-snapshot-workflow.md`](./public-portal-snapshot-workflow.md))
remains the path for curated public-snapshot publication.

## Directory Layout

```text
projectCodexify/
├── Codexify/             # Active source repo (source of truth)
└── Publishing_Portal/    # Independent public-facing repo
    └── Core/             # Generated core source mirror (this workflow)
```

## Rules

1. **`Publishing_Portal/` is an independent Git repo** with its own `.git`
   history. It must not be tracked by the parent Codexify repo.
   The parent `.gitignore` enforces this.

2. **`Publishing_Portal/Core/` is generated output.** It is not a source-of-truth
   editing location. The source of truth remains `projectCodexify/Codexify/`.

3. **The sync workflow is local only.** It does not publish remotely, does not
   run `git push`, and does not prove release readiness.

4. **The sync workflow is safe to rerun.** It deletes and replaces the `Core/`
   mirror without touching the portal repo's `.git` directory.

## How to Run

### Default sync

```bash
# From projectCodexify/Codexify/
bash scripts/release/sync_core_export.sh
```

This copies the core source into `../Publishing_Portal/Core/`.

### Dry run

```bash
bash scripts/release/sync_core_export.sh --dry-run
```

Prints what would be copied without modifying the target.

### Sync with automatic commit in the portal repo

```bash
bash scripts/release/sync_core_export.sh --commit
```

After a successful sync, stages `Core/` inside the `Publishing_Portal` repo and
commits with the message `Refresh Codexify core mirror`. Does not push.

### Custom target

```bash
bash scripts/release/sync_core_export.sh --target /path/to/custom/Core
```

Overrides the default target path.

### Manual commit from inside the portal repo

If you run the sync without `--commit`, you can manually commit from inside the
portal repo:

```bash
cd ../Publishing_Portal
git add Core/
git commit -m "Refresh Codexify core mirror"
```

## What Gets Included

The sync copies the following source roots and files when they are present in the
parent Codexify repo:

| Category | Paths |
|---|---|
| Source directories | `guardian/`, `frontend/`, `src-tauri/`, `config/`, `scripts/`, `tests/` |
| Root config files | `docker-compose.yml`, `Dockerfile`, `Makefile`, `package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `alembic.ini` |
| Env templates | `.env.example`, `.env.template` |
| Top-level docs | `README.md`, `AUTHORIZATION.md` |
| Curated docs | `docs/architecture/`, `docs/release/`, `docs/dev/`, `docs/tasks/`, `docs/Campaign/` |

## What Gets Excluded

At minimum, the following are excluded from the sync:

- `.git/` — the portal owns its own Git history
- `.env`, `.env.*` (except `.env.example` and `.env.template`)
- `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, and other build/cache dirs
- `dist/`, `build/`, `coverage/`
- `*.log`, `*.db`, `*.sqlite`
- `tmp/`, `scratch/`
- `Publishing_Portal/`, `Codexify-Beta/`, `releases/Codexify-Beta/`
- `docs/Marketing/generated/`
- `docs/audits/daily/`, `docs/audits/latest.json`, `docs/audits/latest.md`

## Manifest

After each sync, the script writes `CORE_EXPORT_MANIFEST.json` into the
`Core/` directory. The manifest records:

| Field | Description |
|---|---|
| `export_kind` | Always `codexify_core_source_mirror` |
| `generated_at` | UTC timestamp of the sync |
| `source_branch` | Git branch of the parent repo at sync time |
| `source_commit` | Full commit SHA of the parent repo |
| `source_repo_path` | Absolute path to the parent Codexify repo |
| `target_path` | Absolute path to the mirror target |
| `source_dirty` | Whether the parent repo had uncommitted changes |
| `included_roots` | Array of all paths that were synced |
| `excluded_patterns` | Array of all exclusion patterns applied |
| `do_not_edit_notice` | Reminder that `Core/` is generated output |

## What This Workflow Does Not Do

- Does not publish remotely. There is no `git push`.
- Does not prove release readiness. Use the existing supported-path live-proof
  workflows and `config-and-ops.md` beta-readiness checklist for that.
- Does not replace the curated public-portal snapshot workflow. That workflow
  (`public-portal-snapshot-workflow.md`) handles handoff bundles, public
  READMEs, and curated release artifacts. This workflow is a raw source mirror.
- Does not run as part of CI or any automated pipeline. It is a local-only
  script that must be run intentionally.

## Validation

The script performs these checks before syncing:

1. Confirms it is run from the Codexify repo root by checking for
   `guardian/`, `frontend/`, `docker-compose.yml`, and `.git/`.
2. Confirms the portal repo exists by checking for `../Publishing_Portal/.git`
   (or the parent of a custom `--target`).
3. Confirms `rsync` is available on the system.
