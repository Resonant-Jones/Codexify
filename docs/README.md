# Docs Map

Codexify docs now follow 3 human-facing parent concepts:

- `docs/reference/`: living reference material for the product, architecture, infrastructure, security, plugins, prompts, and operator workflows
- `docs/work/`: campaigns, tasks, plans, reports, and investigations
- `docs/archive/`: retained but non-canonical mirrors, superseded docs, and scratch material

Generated run output no longer lives under `docs/`. Machine-produced audit and campaign artifacts live under `artifacts/`.

## Start Here

- Running or operating Codexify: `docs/reference/operator/README.md`
- Understanding the current system: `docs/reference/architecture/README.md`
- Product and platform docs: `docs/reference/product/README.md`
- Active and historical execution records: `docs/work/README.md`

## Where Should This Doc Live?

- Put stable, re-usable source-of-truth material in `docs/reference/`.
- Put campaigns, tasks, plans, reports, and investigations in `docs/work/`.
- Put mirrors, duplicates, and uncertain historical material in `docs/archive/`.
- Put generated JSON, prompts, run manifests, and machine logs in `artifacts/`.

## Canonical vs Archive vs Artifact

- Canonical docs are the default place to link from README files and runbooks.
- Archive docs are retained for context, but should not be the first destination for new links.
- Artifact paths are output locations for automation and should not be treated as hand-maintained documentation.
