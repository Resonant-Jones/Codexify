# Obsidian Ingest Proof

## Scope
This proof validates the existing CLI Obsidian ingest path against a minimal
fixture vault and proves that the ingested content is retrievable through the
current MemoryOS retrieval path. It does not expose connectors, change profiles,
or activate sync semantics.

## Fixture Vault
Location: `tests/fixtures/obsidian_vault`

Included notes:
- `Plain Note.md` (no frontmatter)
- `Frontmatter Note.md` (YAML frontmatter with title/tags)
- `Tagged Metadata.md` (frontmatter tags/metadata that should survive ingest)
- `Distinctive Retrieval.md` (unique text for retrieval assertion)

## Commands Run
- `pytest -v tests/obsidian/test_ingest_cli.py tests/obsidian/test_ingest_retrieval_proof.py`
- `pytest -v tests`
- `make docs`

## What Was Proven
- Markdown files in a local vault directory are discovered for ingest.
- YAML frontmatter is parsed safely and merged into ingest metadata.
- Metadata packaging preserves `path`, `title`, and `tags` (with tag
  normalization) for ingested notes.
- Content originating from the fixture vault can be retrieved through
  `MemoryOSRetriever` using a minimal vector-store seam.

## What Was Not Proven
- Real embedding backends (FAISS/Chroma) indexing and persistence.
- Retrieval through any API or connector routes.
- End-to-end ingest via a running service or Dockerized environment.
- Sync semantics, federation, or profile changes.

## Hardening Changes
- Added tag normalization to keep ingest metadata consistent.
- Extracted a reusable `_build_obsidian_items` helper from CLI-only logic to
  make ingest packaging testable and repeatable.

## Verdict
The current architecture still supports "local vault as source of truth +
derived local index" at the ingest-packaging and retrieval layer, but the
proof remains limited to a minimal vector-store seam. Real backend indexing
and API-level retrieval are still unverified.
