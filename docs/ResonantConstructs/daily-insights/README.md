# Daily Insight Generator

## What it is

`scripts/content/generate_resonant_daily_insight.py` is a deterministic,
repo-local generator that takes one or more local Markdown source files
and produces a dated Resonant Constructs daily insight Markdown artifact.

The generator:

- Reads only local Markdown source files
- Extracts a concise "signal" from headings and first non-empty paragraphs
- Preserves source excerpts without rewriting the author's voice
- Appends a templated, conservative reflection section
- Does **not** call an LLM, web service, network API, or external publisher
- Does **not** invent claims, metrics, customer statements, release promises, or product status

## How to run

From the repo root:

```bash
# Basic invocation
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-13 \
  --source path/to/source.md

# Multiple sources
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-13 \
  --source docs/ResonantConstructs/daily-insights/README.md \
  --source docs/ResonantConstructs/README.md

# Custom title and output directory
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-13 \
  --source path/to/source.md \
  --title "My Custom Insight" \
  --output-dir /tmp/insights

# Dry run (prints what would happen, does not write)
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-13 \
  --source path/to/source.md \
  --dry-run

# Overwrite existing output
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-13 \
  --source path/to/source.md \
  --force
```

## Arguments

| Argument | Required | Description |
|---|---|---|
| `--date YYYY-MM-DD` | yes | Date for the insight |
| `--source PATH` | yes | Path to a local Markdown source file (repeatable) |
| `--output-dir PATH` | no | Output directory (default: `docs/ResonantConstructs/daily-insights/generated`) |
| `--title TEXT` | no | Custom title (default: `Daily Insight — YYYY-MM-DD`) |
| `--dry-run` | no | Print target path and source summary without writing |
| `--force` | no | Overwrite existing output file |

## Where generated entries go

Generated insight artifacts are written to:

```
docs/ResonantConstructs/daily-insights/generated/YYYY-MM-DD.md
```

## What's deferred

The following are **not** included in this first pass and are deferred to
later tasks:

- Scheduling / cron
- Deployment automation
- Email distribution
- Substack publishing
- Codexify website ingestion
- External publication pipelines
- LLM-based enrichment
