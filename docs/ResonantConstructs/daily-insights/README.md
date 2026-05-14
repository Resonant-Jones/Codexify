# Daily Insights

The Daily Insight generator creates dated Resonant Constructs daily insight
Markdown artifacts from one or more local Markdown source files.

## What It Does

`scripts/content/generate_resonant_daily_insight.py` takes local Markdown
sources and produces a single dated insight page.  The generated page
contains:

- **title**: a custom title or the default `Daily Insight — YYYY-MM-DD`
- **date**: the target date
- **source paths**: which files contributed
- **generated timestamp**: when the artifact was created
- **signal**: a concise deterministic extraction from source headings and
  opening paragraphs (no LLM, no external API)
- **source excerpts**: the source material preserved without rewriting the
  author's voice
- **reflection**: a templated, conservative reflection section

The generator is deterministic and repo-local.  It does not call an LLM,
web service, network API, or external publisher.

## How to Run Manually

From the repository root:

```bash
# Basic invocation with one source
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-14 \
  --source path/to/source.md \
  --force

# With multiple sources
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-14 \
  --source path/to/source1.md \
  --source path/to/source2.md \
  --force

# Custom title
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-14 \
  --source path/to/source.md \
  --title "Field Coherence Observations" \
  --force

# Dry run (validates and prints summary, no files written)
python scripts/content/generate_resonant_daily_insight.py \
  --date 2026-05-14 \
  --source path/to/source.md \
  --dry-run
```

### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--date YYYY-MM-DD` | yes | Target date for the insight |
| `--source PATH` | yes | Path to a Markdown source (repeatable) |
| `--output-dir PATH` | no | Output directory (default: `docs/ResonantConstructs/daily-insights/generated`) |
| `--title TEXT` | no | Custom title (default: `Daily Insight — YYYY-MM-DD`) |
| `--dry-run` | no | Validate inputs, print target path and summary, do not write |
| `--force` | no | Overwrite existing output file |

## Where Generated Entries Go

Generated insight pages are written to:

```
docs/ResonantConstructs/daily-insights/generated/YYYY-MM-DD.md
```

Each file is a self-contained Markdown page with YAML frontmatter.

## What Is Deferred

The following are **intentionally deferred** to later tasks and are not part
of this generator:

- Scheduling / cron automation
- Deployment to a website or hosting environment
- Email publication or newsletter distribution
- Substack or external platform sync
- Codexify website ingestion integration
- External content sourcing

## What Generated Insights Are

Generated daily insights are **local-source artifacts**, not external
announcements.  They reflect the content of source files in the repository at
generation time.  They do not:

- Invent claims, metrics, or customer statements
- Make release promises or product status declarations
- Use model-generated text
- Rewrite the author's voice

The signal section is a deterministic extraction (headings and opening
paragraphs).  The reflection section is a templated block that acknowledges
the artifact's provenance.
