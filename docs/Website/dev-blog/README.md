# Daily Dev Blog Ingestion

This directory defines the first-pass repo-local ingestion seam for Codexify’s
daily dev blog website content.

The ingestion script:

- reads a Markdown source file from the repo
- validates that the source exists, is non-empty, and looks like Markdown
- writes a dated website-ready Markdown page to
  `docs/Website/dev-blog/generated/YYYY-MM-DD.md`
- preserves the source body verbatim under a small metadata block

## Manual Run

From the repository root:

```bash
python scripts/content/ingest_daily_dev_blog.py \
  --date 2026-05-13 \
  --source docs/Website/dev-blog/README.md \
  --output-dir docs/Website/dev-blog/generated \
  --force
```

Use `--dry-run` to validate inputs and print the target path without writing
files.

Use `--force` when you want to overwrite an existing generated page.

## Output

Generated entries are written to:

```text
docs/Website/dev-blog/generated/YYYY-MM-DD.md
```

Each page includes:

- title
- date
- source path
- generated timestamp
- the original source Markdown content

## Deferred Work

This task only covers ingestion and documentation.

Deferred to later tasks:

- scheduling
- email publication
- Substack publishing
- deployment automation
- Resonant Constructs daily insight logic
