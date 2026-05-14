# Resonant Constructs Content Area

This directory holds repo-local content related to the **Resonant Constructs**
strand — a body of thinking, observation, and synthesis within the Codexify
repository that is separate from product, engineering, or website content.

## What Is Resonant Constructs

Resonant Constructs is a content strand concerned with:

- **Observation**: noticing patterns in systems, cognition, and design
- **Synthesis**: connecting ideas across domains
- **Reflection**: capturing insights without premature conclusion

It is not a product announcement channel, a release log, or a marketing
surface.  It is a thinking space that operates alongside the engineering and
product work in the repository.

## Structure

- `daily-insights/`: script-driven daily insight generation and generated
  artifacts
- `daily-insights/generated/`: dated generated insight pages created by the
  daily insight generator

## Boundary

Resonant Constructs content is:

- **Derived from local source material only** — no LLM generation, no web
  scraping, no external APIs
- **Deterministic** — the same source produces the same output
- **Conservative** — insights do not invent claims, metrics, customer
  statements, release promises, or product status
- **Separate from the website pipeline** — this content tree is distinct from
  `docs/Website/` and its ingestion paths

This area is intentionally narrow.  Scheduling, deployment, email
publication, Substack sync, and other automation paths are deferred to later
work.
