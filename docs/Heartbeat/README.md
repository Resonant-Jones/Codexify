# Heartbeat Orchestrator

## What it is

`scripts/content/run_heartbeat_orchestrator.py` is a deterministic, repo-local
orchestration script that runs the three existing heartbeat scripts in one
command and emits a single dated Markdown report.

The orchestrator is a thin runner — it invokes the child scripts as
subprocesses and aggregates their results. It does **not** duplicate their
implementation logic.

## Which scripts it runs

| Step | Script | Purpose |
|------|--------|---------|
| Beta Release Sentinel | `scripts/release/beta_release_sentinel.py` | Generates beta readiness evidence artifacts |
| Daily Dev Blog Ingestion | `scripts/content/ingest_daily_dev_blog.py` | Ingests a dev blog Markdown source into the website content tree |
| Resonant Constructs Daily Insight | `scripts/content/generate_resonant_daily_insight.py` | Generates a daily insight from local Markdown sources |

Each step can be independently skipped via a `--skip-*` flag.

## How to run

### Makefile (recommended)

```bash
# Full run with all sources
make heartbeat DATE=2026-05-14 \
  DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md \
  INSIGHT_SOURCE="docs/ResonantConstructs/daily-insights/README.md docs/ResonantConstructs/README.md" \
  FORCE=1

# Defaults to today; skips dev-blog and insight unless sources provided
make heartbeat

# Today, with only the dev blog (insight skipped automatically)
make heartbeat DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md FORCE=1

# Today, with only insight sources (dev blog skipped automatically)
make heartbeat INSIGHT_SOURCE="docs/ResonantConstructs/daily-insights/README.md" FORCE=1
```

**Makefile variable behavior:**

| Variable | Default | Effect |
|---|---|---|
| `DATE` | today (`date +%Y-%m-%d`) | Passed as `--date` |
| `DEV_BLOG_SOURCE` | *(empty)* | If set, passed as `--dev-blog-source`; otherwise `--skip-dev-blog` |
| `INSIGHT_SOURCE` | *(empty)* | If set, each word passed as `--insight-source`; otherwise `--skip-daily-insight` |
| `FORCE` | *(unset)* | If `FORCE=1`, passes `--force`; otherwise omitted |

Beta Release Sentinel is **always** run (no skip variable).

The Makefile target is the recommended interface for daily use because it
handles date defaulting, conditional `--skip-*` flags, and `--force` gating.

### pnpm / npm

```bash
pnpm heartbeat -- --date 2026-05-14 --dev-blog-source docs/Website/dev-blog/README.md --insight-source docs/ResonantConstructs/daily-insights/README.md --force
```

Note: The `--` separator is required so pnpm forwards arguments to the Python
script.  Richer argument handling (date defaults, conditional skip flags) is
best done through the Makefile target.

### Direct Python invocation

From the repo root:

```bash
# Full run
python scripts/content/run_heartbeat_orchestrator.py \
  --date 2026-05-13 \
  --dev-blog-source docs/Website/dev-blog/README.md \
  --insight-source docs/ResonantConstructs/daily-insights/README.md \
  --force

# Skip specific steps
python scripts/content/run_heartbeat_orchestrator.py \
  --date 2026-05-13 \
  --dev-blog-source docs/Website/dev-blog/README.md \
  --insight-source docs/ResonantConstructs/daily-insights/README.md \
  --skip-beta-sentinel \
  --force

# Dry run (prints planned commands, writes nothing)
python scripts/content/run_heartbeat_orchestrator.py \
  --date 2026-05-13 \
  --dev-blog-source docs/Website/dev-blog/README.md \
  --insight-source docs/ResonantConstructs/daily-insights/README.md \
  --dry-run

# Custom output directory
python scripts/content/run_heartbeat_orchestrator.py \
  --date 2026-05-13 \
  --dev-blog-source docs/Website/dev-blog/README.md \
  --insight-source docs/ResonantConstructs/daily-insights/README.md \
  --output-dir /tmp/heartbeat-out \
  --force
```

## Arguments

| Argument | Required | Description |
|---|---|---|
| `--date YYYY-MM-DD` | yes | Date for the heartbeat run |
| `--dev-blog-source PATH` | yes (unless `--skip-dev-blog`) | Path to the Daily Dev Blog Markdown source file |
| `--insight-source PATH` | yes unless `--skip-daily-insight` | Path to a Resonant Constructs insight source file (repeatable) |
| `--output-dir PATH` | no | Output directory for the heartbeat report (default: `docs/Heartbeat/generated`) |
| `--dry-run` | no | Print planned commands and target path without executing or writing |
| `--force` | no | Overwrite existing heartbeat report if present |
| `--skip-beta-sentinel` | no | Skip the Beta Release Sentinel step |
| `--skip-dev-blog` | no | Skip the Daily Dev Blog ingestion step |
| `--skip-daily-insight` | no | Skip the Resonant Constructs Daily Insight step |

## Where generated heartbeat reports go

```
docs/Heartbeat/generated/YYYY-MM-DD-heartbeat.md
```

## How `--dry-run`, `--force`, and skip flags work

- **`--dry-run`**: Prints all planned subprocess commands and the target report
  path. Does **not** execute any child script and does **not** write any files.
- **`--force`**: Allows overwriting an existing heartbeat report for the same
  date. Without `--force`, the orchestrator fails with a clear error if the
  report already exists.
- **`--force` is forwarded** to the Daily Dev Blog and Daily Insight scripts
  (which support it). The Beta Release Sentinel does **not** receive `--force`
  because it does not support that flag.
- **Skip flags** (`--skip-beta-sentinel`, `--skip-dev-blog`,
  `--skip-daily-insight`): Omit the corresponding step entirely. Skipped steps
  are recorded in the heartbeat report with status `skipped`.
- When a `--skip-*` flag is used, the corresponding required source argument
  becomes optional.

## Report contents

Each heartbeat report includes:

- Title: `Heartbeat Orchestrator — YYYY-MM-DD`
- Date and generated timestamp
- Repo status summary (branch, head, worktree cleanliness)
- Run summary table (step name, status, artifacts, notes)
- Generated artifact paths
- Skipped steps
- Warnings
- Failures (with sanitized, bounded captured output)
- Next suggested manual action

Run statuses are limited to three values: `passed`, `failed`, and `skipped`.

## What's deferred

The following are **not** included in this first pass and are deferred to
later tasks:

- Cron scheduling
- Deployment automation
- Email distribution
- Substack publishing
- Codexify website publishing
- External automation
- Command-bus integration
- Runtime worker integration
- Any modification to the child scripts' implementations (unless a minimal
  compatibility fix is required)

## Important caveats

- **Heartbeat reports are local operational artifacts**, not release approval
  by themselves. They capture what happened during a local run of the three
  heartbeat scripts on a given date.
- The orchestrator does **not** publish externally. All output is written to
  the local filesystem.
- The orchestrator does **not** modify runtime, queue, worker, provider,
  retrieval, identity, cron, command bus, or release-gating behavior.
- Captured child script output is sanitized to remove obvious secret-like
  values (API keys, tokens, passwords, private keys).
