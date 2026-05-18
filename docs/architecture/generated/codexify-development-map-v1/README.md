# Codexify Development Map v1 Generated Artifacts

## Source

- Source map document: `/docs/architecture/codexify-development-map-v1.md`

## Generated artifacts

- `01-current-codexify-system-map.mmd`
- `01-current-codexify-system-map.svg`
- `02-core-chat-interoperation-flow.mmd`
- `02-core-chat-interoperation-flow.svg`
- `03-data-and-dependency-spine.mmd`
- `03-data-and-dependency-spine.svg`
- `04-ui-architecture-map.mmd`
- `04-ui-architecture-map.svg`

## Rendering status

- `01-current-codexify-system-map`: `.mmd` extracted and `.svg` rendered.
- `02-core-chat-interoperation-flow`: `.mmd` extracted and `.svg` rendered.
- `03-data-and-dependency-spine`: `.mmd` extracted and `.svg` rendered.
- `04-ui-architecture-map`: `.mmd` extracted and `.svg` rendered.

## Mermaid compatibility notes

- Source compatibility repair applied in `/docs/architecture/codexify-development-map-v1.md` and synced into generated `.mmd` files.
- Flowchart label line breaks were normalized from escaped `\n` to `<br/>` for broader preview compatibility.
- Sequence diagram note text was split into shorter `Note over ...` lines to reduce parser fragility in VS Code Mermaid preview.
- Architecture meaning, node relationships, status labels, and release-promise caveats were preserved.

## Renderer command used

- `npm exec --yes @mermaid-js/mermaid-cli -- -i docs/architecture/generated/codexify-development-map-v1/<diagram>.mmd -o docs/architecture/generated/codexify-development-map-v1/<diagram>.svg`

## Canonical truth notes

- Generated artifacts are convenience outputs and do not override `/docs/architecture/00-current-state.md`.
- `/docs/architecture/codexify-development-map-v1.md` remains the canonical editable source document for this map.
