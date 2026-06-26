# Zac Report Filename Conventions

**For:** Zac's agent — naming reports consistently  
**Last updated:** 2026-06-26

## Recommended Format

```
YYYY-MM-DD-<lens>-<area>-report.md
```

Keep report names descriptive but short. Prefer repo-relative area names. Use lowercase kebab-case throughout.

## Examples

- `2026-06-26-cartographer-frontend-src-report.md`
- `2026-06-26-cartographer-guardian-routes-report.md`
- `2026-06-26-doc-gardener-architecture-docs-report.md`
- `2026-06-26-ui-naturalist-persona-studio-report.md`
- `2026-06-26-runtime-boundary-auth-report.md`
- `2026-06-26-runtime-boundary-provider-routing-report.md`
- `2026-06-26-dev-experience-local-setup-report.md`
- `2026-06-26-test-cartographer-continuity-tests-report.md`
- `2026-06-26-continuity-museum-six-route-surface-report.md`

## Allowed Lens Slugs

Use exactly one of these slugs in the filename:

| Lens | Slug |
|---|---|
| Cartographer | `cartographer` |
| Doc Gardener | `doc-gardener` |
| UI Naturalist | `ui-naturalist` |
| Runtime Boundary Scout | `runtime-boundary` |
| Dev-Experience Mechanic | `dev-experience` |
| Test Cartographer | `test-cartographer` |
| Continuity Museum Guide | `continuity-museum` |

## Guidance

- Use the date the report was generated, not the date the area was last modified.
- For the area slug, use the most specific repo path or component name that fits (e.g., `frontend-src`, `guardian-routes`, `auth`, `persona-studio`).
- Avoid spaces, underscores, or uppercase in filenames.
- Do not encode secrets, usernames, tokens, or private data in filenames.
- If a report is revised, append a revision marker (e.g., `-v2`) or supersede it with a new dated report and update the index.
