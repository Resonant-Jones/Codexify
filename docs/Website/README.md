# Website Content Area

This directory holds repo-local Markdown content intended for the Codexify
website pipeline.

The current first-pass seam is the daily dev blog ingestion flow:

- source Markdown is collected from a repo-local file
- the ingestion script writes a website-ready dated page
- generated pages live under `docs/Website/dev-blog/generated/`

This area is intentionally narrow for now. It covers content shaping only and
does not include deployment, scheduling, email publication, Substack sync, or
other automation paths.

## Structure

- `dev-blog/`: daily dev blog source notes and the ingestion README
- `dev-blog/generated/`: dated generated website pages created by the
  ingestion script

## Boundary

The website content tree is a derived output layer. It should reflect the source
Markdown without rewriting the author’s voice or inventing new claims.
