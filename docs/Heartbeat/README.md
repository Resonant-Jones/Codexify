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

## Schedule manifest

A declarative JSON manifest at `config/heartbeat/heartbeat.schedule.example.json`
describes the intended heartbeat schedule without implementing it.

- **Schema version:** `heartbeat.schedule.v1`
- **Example schedule:** `daily-local-heartbeat` — manual-only, `enabled: false`
  (no scheduler is active), publication off, review gate on
- **Inputs documented:** `DATE`, `DEV_BLOG_SOURCE`, `INSIGHT_SOURCE`, `FORCE`
- **Review inputs:** `STRICT`
- **Artifact families:** heartbeat report, beta sentinel (md + json),
  dev blog, daily insight

The manifest is validated by `tests/scripts/test_schedule_manifest.py`
(16 tests, no network or external dependencies).

Like everything else in this directory, the manifest is a **specification**,
not an active schedule.  Activation is `manual_only` — the only way to
run the heartbeat today is via `make heartbeat` from the repo root.

### Activation modes

| Mode | Meaning |
|---|---|
| `manual_only` | No scheduler is activated. All runs are manual via `make heartbeat`. **This is the current state.** |
| `local_scheduler_ready` | Manifest validated; a local scheduler (cron, launchd, systemd timer) may be wired in a later task. |
| `future_codexify_cron_ready` | Reserved for a future Codexify-integrated cron or command-bus scheduler. Not implemented. |

**Future scheduling must pass through heartbeat review before publication.**
Any automated pipeline added later must run the review gate (`make heartbeat-review STRICT=1`)
and require `passed` status before proceeding to deployment, email, Substack,
or website publishing.

**Publication targets remain disabled and empty** (`enabled: false`, `targets: []`)
in this task.  No external publishing is wired.

## Reviewing a heartbeat run

The `review_heartbeat_run.py` script validates a heartbeat report without
running the orchestrator.  It checks that the report exists, the title
matches, artifacts are present on disk, no failures are recorded, and no
secret-like values leaked into the report.

**The review command is a safety gate** — it should be run before any
scheduling, deployment, or publication step is added in later tasks.
Passing review confirms that a given heartbeat run is complete and
artifact-intact, but does **not** by itself approve release readiness.

The review command does **not** run the heartbeat orchestrator, publish
externally, or modify any file on disk.

### How to run

```bash
# Makefile (recommended)
make heartbeat-review DATE=2026-05-14
make heartbeat-review DATE=2026-05-14 STRICT=1
make heartbeat-review   # defaults to today

# pnpm
pnpm heartbeat:review -- --date 2026-05-14 --strict

# Direct
python scripts/content/review_heartbeat_run.py --date 2026-05-14
python scripts/content/review_heartbeat_run.py --date 2026-05-14 --strict --json
```

Richer argument handling (date defaulting, strict gating) is best done
through the Makefile target.

### Review statuses

| Status | Meaning |
|---|---|
| `passed` | Report exists, all steps passed, artifacts present, no secrets detected |
| `warning` | Report exists but has issues (failed steps, missing artifacts, title mismatch, secrets) |
| `failed` | Report not found, or `--strict` mode with any issue |

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--date YYYY-MM-DD` | no | Date of the heartbeat run. Defaults to today. |
| `--heartbeat-dir PATH` | no | Directory containing heartbeat reports (default: `docs/Heartbeat/generated`) |
| `--json` | no | Output machine-readable JSON instead of Markdown-ish text |
| `--strict` | no | Treat warnings as failures; skipped or non-passed steps become review failures |

### What it checks

- Heartbeat report exists for the given date
- Report title matches `Heartbeat Orchestrator — YYYY-MM-DD`
- Run summary table is present
- No steps have `failed` status
- Artifacts listed in the report exist on disk
- Report contains no obvious secret-like values (`api_key=`, `token=`,
  `password=`, `secret=`, `oauth`, `cookie`, `Authorization: Bearer`,
  `sk-`, GitHub tokens, JWT, private keys)
