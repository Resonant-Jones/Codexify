# Local OpenAI Export Corpus Workspace

This directory is for local-only OpenAI export work: symlinks, manifests,
diagnostic outputs, scraper outputs, and short-lived archaeology artifacts.

Raw OpenAI export payloads must never be committed. Do not copy private export
contents into tracked source files, docs, tests, or fixtures.

The real local export currently lives at:

```text
/Users/resonant_jones/Keep/OpenAI-export
```

Create a repo-local symlink when Codexify needs to inspect the live corpus:

```bash
ln -s /Users/resonant_jones/Keep/OpenAI-export local_exports/openai/OpenAI-export
```

Run a non-mutating diagnostic scan with:

```bash
codexify import:openai --path local_exports/openai/OpenAI-export --diagnose
```

Run the task prompt scraper with:

```bash
codexify export-scraper:tasks --path local_exports/openai/OpenAI-export --out export_scraper
```

If the installed `codexify` entrypoint is unavailable in a development shell,
use the repo-module equivalent:

```bash
python -m scripts.chatgpt_import.cli_migrate import:openai \
  --path local_exports/openai/OpenAI-export \
  --diagnose

python -m scripts.chatgpt_import.cli_migrate export-scraper:tasks \
  --path local_exports/openai/OpenAI-export \
  --out export_scraper
```

## Manifest Awareness

The uploaded `export_manifest.json` indicates the current export corpus
contains:

- `chat.html`
- `conversation_asset_file_names.json`
- `conversations-000.json` through `conversations-050.json`
- many `file-*.dat` assets
- sharded and non-sharded file mapping metadata

Treat the manifest as an index into the export corpus. It should guide
diagnostics and importer development, but raw payloads remain local-only.
