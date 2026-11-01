"""Qualification registry projection and validation tooling.

`docs/qualification/registry.json` is the dashboard-facing projection of
Codexify qualification status. The directory contract in
`docs/qualification/README.md` requires that projection to be derived from
repository evidence rather than hand-maintained: a rubric defines what must be
proven, a run receipt records what was actually attempted, and the registry
summarizes the current state of those runs.

This package provides:

* `generate_registry.py` — project rubrics and run receipts into
  `registry.json`, with a `--check` mode that fails on drift.
* `validate_registry.py` — enforce the JSON Schema plus the invariants the
  schema cannot express (evidence resolves, receipts exist, PASS carries a
  tested commit).
* `lib/` — the shared parsing, freshness, and matching primitives.

Nothing here mutates runtime state, contacts a provider, or claims
qualification. The registry summarizes evidence; it never manufactures it.
"""
