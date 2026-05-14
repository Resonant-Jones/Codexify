# Resonant Constructs

This directory contains the Resonant Constructs content area — a local,
deterministic content pipeline focused on structured thinking, daily
observation, and long-form exploration.  Everything in this area is
generated from local source material; nothing is piped to external
publishing surfaces yet.

## Sub-areas

- [daily-insights/](./daily-insights/) — Daily insight generation from
  local Markdown source files.

## Principles

1. **Deterministic.**  Given the same inputs, the same output is
   produced every time.
2. **Repo-local.**  All generation runs within the repository using
   only local files and standard Python tooling.
3. **Source-grounded.**  Every artifact cites its exact source files.
   No claims are invented and no external models or APIs are called.
4. **Deferred publishing.**  Scheduling, deployment, email, Substack,
   and website ingestion are out of scope for the initial generator.
   This directory is a content *source* area, not a publication
   pipeline.

## Status

- **Daily Insight generator:** implemented (first pass).  See
  [daily-insights/README.md](./daily-insights/README.md) for usage.
- **Scheduling / deployment / publishing:** deferred to later tasks.
