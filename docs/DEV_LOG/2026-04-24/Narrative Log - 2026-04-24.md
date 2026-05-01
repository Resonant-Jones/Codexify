## Dev Log - 2026-04-24

### Summary
Project knowledge boundary hardening day.

The work was about making project-local knowledge visible without collapsing it into the assistant-wide Settings lane. Project documents now have a routed place in the shell, and the UI tells the truth about scope: project-local working docs live in their own lane, while System Docs remain the constitutional overlay in Settings.

That matters because the system is now clearer about what belongs to a project and what belongs to the assistant. The feature is still honest about its limits. It reuses existing document storage and does not claim to change global retrieval policy.

### What I completed

#### Project Knowledge Base entry point
- Added a dedicated `Project Knowledge Base` card in the sidebar projects tab.
- The card exposes an explicit `Open Project Knowledge Base` action instead of treating project docs as an implicit side effect of being in a project.
- The sidebar now dispatches `cfy:project-kb:open` with project context, including `projectId` and `projectName`.
- `AppShell` listens for that event, loads the project context, and routes the workspace into the dashboard view.
- Tests now cover the sidebar-to-dashboard handoff so the route is not just visual.

#### Project document lane
- The dashboard now renders a real project-local document surface with loading, empty, and error states.
- It loads project-scoped documents through the existing `/media/documents?project_id=...` path.
- It uploads through `/api/media/upload/document` with `project_id` and `tag=uploaded`.
- The surface states plainly that it uses existing project document storage and does not change global behavior or retrieval policy.
- Demo-state coverage now checks the empty state, populated state, and upload-refresh flow.

### Important outcome
Project Knowledge Base is no longer just a phrase in settings copy. It now has a visible door in the shell, a routed project context, and a document flow that stays scoped to the project.

The stronger shift is boundary clarity. The system now separates project-local working docs from assistant-wide overlays in a way the UI can enforce and the rest of the shell can trust.

### Commits
- `994d0ed1f` - `add project knowledge base surface entry`
- `a65efc2dc` - `wire project knowledge base document surface`

### Notes
- Validation in this pass is still component-test-level; there was no live browser/runtime proof.
- The work reuses existing project document storage and API paths rather than introducing a new backend contract.
- The boundary language in the UI matters here because it prevents the surface from overstating what it does.

### Next likely moves
- Open the shell in the browser and verify the sidebar-to-dashboard handoff with real project state.
- Exercise the upload flow against a live backend and confirm the project document list refreshes cleanly.
- Check whether the project KB panel needs copy or spacing adjustments once seen in the real shell.
- Decide whether this lane needs a follow-up architecture note or can stay presentation-only for now.

### Closing thought
The important change is not that there is another document bucket. It is that project-local knowledge now has a visible, routable place to live without blurring into system-level truth.

## Narrative Log - 2026-04-24

This was a boundary day. The work was not about adding a flashy new surface so much as making the shell follow a distinction that already needed to be real: project-local knowledge belongs in the project lane, and System Docs belong in the assistant-wide lane.

The first correction was at the edge of the sidebar. Project Knowledge Base stopped being a soft concept and became an explicit entry point with its own action. That action carries project context through `cfy:project-kb:open`, and `AppShell` catches it and routes into the dashboard with the right project already attached. The practical effect is small but important: the user lands in the right place with the right scope instead of being dropped into a generic dashboard and forced to infer intent.

The second correction was inside the dashboard itself. The project knowledge panel became an operational surface instead of a label. It loads project-scoped documents from the existing document API, shows loading and empty states, and uploads back through the same storage path with the project id attached. The panel also says what it is not: it does not alter global behavior or retrieval policy. That line matters because it keeps the feature honest. It is a project-local working lane, not a hidden policy change.

What changed underneath the surface is clarity. The shell can now carry project-local knowledge without pretending it is system-level truth, and that makes the rest of the product easier to trust. The next useful step is live verification, because the structure is now clear enough to test in the real shell.


::inbox-item{title="Project KB surface wired" summary="Needs browser verification and live upload proof."}