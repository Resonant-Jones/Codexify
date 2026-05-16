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

## Staging a heartbeat outbox

The `stage_heartbeat_outbox.py` script copies heartbeat artifacts into a
flat staging directory and generates templated content drafts for downstream
publication channels (all deferred).

### How to run

```bash
# Makefile (recommended)
make heartbeat-stage DATE=2026-05-14
make heartbeat-stage DATE=2026-05-14 FORCE=1
make heartbeat-stage   # defaults to today

# pnpm
pnpm heartbeat:stage -- --date 2026-05-14 --force

# Direct
python scripts/content/stage_heartbeat_outbox.py --date 2026-05-14 --force
python scripts/content/stage_heartbeat_outbox.py --date 2026-05-14 --dry-run
```

Richer argument handling (date defaulting, force gating) is best done
through the Makefile target.

### What it produces

The staging script copies artifacts from the generated directories into
`docs/Heartbeat/staged/YYYY-MM-DD/` and produces:

| File | Description |
|---|---|
| `*-beta-sentinel.{md,json}` | Beta release sentinel artifacts |
| `*-dev-blog.md` | Daily dev blog draft |
| `*-daily-insight.md` | Resonant Constructs daily insight |
| `release-summary.md` | Templated release summary from heartbeat run |
| `website-update.md` | Templated website update draft |
| `substack-draft.md` | Templated Substack newsletter draft |
| `email-draft.md` | Templated email draft |
| `manifest.json` | Staging manifest (`heartbeat.outbox.v1`) |

All drafts include a visible note that they are local staging artifacts,
not published content.

### Safety gates

- **Review required** — the staging script runs `review_heartbeat_run.py --strict`
  before copying.  If review fails, staging is blocked.
- **--skip-review** bypasses the gate but writes a `_SKIP_REVIEW_WARNING.txt`
  file and adds warnings to the result.
- **Secret scan** — after generating drafts, the script scans all staged
  content for secret-like values.  If detected, the offending draft is removed
  and an error is reported.
- **No network calls** — the script operates entirely on the local filesystem.
- **Publication disabled** — the staging manifest records `publication.enabled: false`
  and `targets: []`.

## Inspecting a staged outbox

The `inspect_heartbeat_outbox.py` script reads a staged outbox directory
and validates its contents without modifying anything.  It is a read-only
safety check — unlike staging, which copies files and generates drafts,
inspection only verifies what was already staged.

### How to run

```bash
# Makefile (recommended)
make heartbeat-outbox DATE=2026-05-14
make heartbeat-outbox DATE=2026-05-14 STRICT=1
make heartbeat-outbox   # defaults to today

# pnpm
pnpm heartbeat:outbox -- --date 2026-05-14 --strict

# Direct
python scripts/content/inspect_heartbeat_outbox.py --date 2026-05-14
python scripts/content/inspect_heartbeat_outbox.py --date 2026-05-14 --strict --json
```

Richer argument handling (date defaulting, strict gating) is best done
through the Makefile target.

### What it checks

| Check | Non-strict | Strict |
|---|---|---|
| Staged directory exists for date | `failed` | `failed` |
| `manifest.json` present and valid JSON | `failed` | `failed` |
| `schema_version` is `heartbeat.outbox.v1` | `failed` | `failed` |
| `date` in manifest matches directory name | `failed` | `failed` |
| `publication.enabled` is `false` | `failed` | `failed` |
| `publication.targets` is `[]` | `failed` | `failed` |
| `review_required` is `true` | `failed` | `failed` |
| `review_status` is present | `failed` | `failed` |
| All `generated_files` exist on disk | `warning` | `failed` |
| No secret-like values in staged content | `warning` | `failed` |
| Review gate was skipped | `warning` | `warning` |

### Inspection statuses

| Status | Meaning |
|---|---|
| `passed` | All checks pass, outbox is clean |
| `warning` | Non-critical issues (skip-review, extra files). Review manually. |
| `failed` | Critical issues (missing manifest, wrong schema, publication enabled, missing files). Do not proceed. |

### Difference from staging

- **Staging** (`make heartbeat-stage`) copies artifacts from generated
  directories and creates drafts. It **modifies** the filesystem.
- **Inspection** (`make heartbeat-outbox`) reads the already-staged outbox
  and validates it. It is **read-only** and does not modify files.

Run inspection after staging to verify the outbox before any further
pipeline step.

## Full pipeline (`make heartbeat-full`)

The `make heartbeat-full` target runs the complete heartbeat pipeline
end-to-end in a single command: generate → review → stage → inspect.
It stops on the first failed step.

### Usage

```bash
# Full run with content sources
make heartbeat-full \
  DEV_BLOG_SOURCE=docs/Website/dev-blog/README.md \
  INSIGHT_SOURCE="docs/ResonantConstructs/daily-insights/README.md docs/ResonantConstructs/README.md" \
  FORCE=1

# Beta-only run (dev-blog and insight auto-skipped when sources not provided)
make heartbeat-full

# Strict run (warnings treated as failures in review and inspection)
make heartbeat-full STRICT=1

# Custom date
make heartbeat-full DATE=2026-05-14 FORCE=1
```

### What it runs

| Step | Target | What happens |
|---|---|---|
| 1. Generate | `make heartbeat` | Runs Beta Release Sentinel, Daily Dev Blog, Resonant Daily Insight |
| 2. Review | `make heartbeat-review` | Validates the heartbeat report (strict when `STRICT=1`) |
| 3. Stage | `make heartbeat-stage` | Copies artifacts + generates drafts to `docs/Heartbeat/staged/` |
| 4. Inspect | `make heartbeat-outbox` | Validates the staged outbox (strict when `STRICT=1`) |

### Pass-through variables

| Variable | Passed to |
|---|---|
| `DATE` | All four child targets |
| `DEV_BLOG_SOURCE` | `heartbeat` |
| `INSIGHT_SOURCE` | `heartbeat` |
| `FORCE=1` | `heartbeat`, `heartbeat-stage` |
| `STRICT=1` | `heartbeat-review`, `heartbeat-outbox` |

### Caveats

- **Staging requires strict review to pass.** If review fails (e.g., because
  a lane was skipped and `STRICT=1`), staging is blocked and the pipeline
  stops.
- This is the **recommended manual operator command** for running the full
  heartbeat flow.
- **Agent Command Center wiring is deferred** to a separate
  architecture-impact task.  The `heartbeat-full` command creates the
  operator seam that a future ACC task can invoke through a governed path.
- **This does not schedule or publish anything.**  All steps are manual
  and local.

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
