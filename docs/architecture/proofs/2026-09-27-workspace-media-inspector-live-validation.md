# Workspace media Inspector live validation — 2026-09-27

## Identity and verdict

- Observation window: 2026-09-27, 11:47–11:50 EDT.
- Repository root: `/Volumes/Dev_SSD/offload/codex/worktrees/7d94/Codexify-main`.
- Branch: `codex/thread-scoped-delegated-tasks`.
- Evaluated HEAD: `10f996cd21300e92944302273f4a16bca85a8470`.
- Implementation anchor: `10f996cd` (`Enable Workspace media inspection`); ancestry check passed.
- Intended runtime/profile: source-development Docker Compose using the named supported `v1-local-core-web-mcp` profile. No runtime was started from this checkout, so no live profile was validated.
- Canonical local origins from this checkout's Compose configuration: frontend `http://127.0.0.1:5173`; Guardian `http://127.0.0.1:8888`. Both refused connections during this attempt.
- Authenticated account identity, Project ID, Thread ID, saved document ID, and image ID: **none established**. The application could not load or authenticate.

**Overall conclusion: `WORKSPACE_MEDIA_INSPECTOR_LIVE_PROOF_BLOCKED`.** The local runtime configuration stopped Compose before service creation. This is an environment blocker, not an observed media Inspector implementation failure. No live Shelf, document, image, zoom, lightbox, or scope behavior was established.

## Preflight and runtime boundary

From the repository root, `git rev-parse --show-toplevel`, `git branch --show-current`, and `git rev-parse HEAD` returned the root, branch, and HEAD above. `git status --short` was empty. `git merge-base --is-ancestor 10f996cd HEAD` exited 0. No unrelated dirty files were present.

The documented source-development startup command is `docker compose up --build` (`docs/architecture/config-and-ops.md`). The checked-out Compose file maps the frontend to port 5173 and Guardian to port 8888, and requires `GUARDIAN_API_KEY` during interpolation. This worktree has no `.env`, `.env.local`, or `.env.backend.development` file. The required key was not set in the command environment.

Runtime commands and observations:

| Command | Result |
|---|---|
| `docker compose ps` | Exit 1 before listing services: `services.migrator.environment.GUARDIAN_API_KEY` required a value. |
| `docker ps --format '{{.Names}}|{{.Status}}|{{.Ports}}'` | Docker was available. Running containers belonged to private-preview, earlier proof, or partial default projects; no canonical local frontend/backend listener for this checkout was present. Those containers were not used as proof for this HEAD. |
| `lsof -nP -iTCP:8888 -iTCP:5173 -sTCP:LISTEN` | No listener on either canonical local port. |
| `curl -sS -o /dev/null -w 'frontend_http=%{http_code} error=%{errormsg}\n' --max-time 4 http://127.0.0.1:5173/` | Exit 7 with connection refused (`HTTP 000`). |
| `curl -sS -o /dev/null -w 'guardian_http=%{http_code} error=%{errormsg}\n' --max-time 4 http://127.0.0.1:8888/health` | Exit 7 with connection refused (`HTTP 000`). |
| `docker compose up --build` | Exit 1 during Compose interpolation with the same missing `GUARDIAN_API_KEY` requirement; no build or service startup occurred. |

The actual authenticated Codexify application was attempted through the documented startup and both canonical origins. Browser interaction, account selection, media upload, and screenshots could not proceed. No credential was requested, printed, copied from another checkout, or written for this proof. No Compose profile, auth setting, provider policy, account configuration, schema, or production file was changed.

## Required evidence matrix

`BLOCKED` in the mandatory rows means the upstream local runtime was unavailable before an authenticated UI session. It is not a feature failure observation.

| Seam | Result | Evidence |
|---|---|---|
| Authenticated real application load | BLOCKED | Compose interpolation stopped on missing local key; frontend and Guardian origins refused connections. No account session or identity was established. |
| Notes Save through real UI | BLOCKED | No real Workspace or Notes modal could load; no draft was entered or saved. |
| Durable saved document identity | BLOCKED | No Save request ran, so no `GeneratedDocument`, document ID, format, or filename was observed. |
| Real document appears on Shelf | BLOCKED | No authenticated Shelf listing could be requested or rendered. |
| Real document body renders in Inspector | BLOCKED | No persisted document was selected; body, metadata, line breaks, scrolling, and page containment were unobserved. |
| Notes draft survives Save | BLOCKED | No real Save occurred; draft and saved-document separation remains live-unverified. |
| Real image appears on Shelf | BLOCKED | No authenticated image listing or upload occurred; no image ID or linkage was established. |
| Real image renders in Inspector | BLOCKED | No backend-served image was selected or delivered. |
| Inspector zoom | BLOCKED | Default fit, Zoom In, 125%, Zoom Out, Reset/Fit, and keyboard reachability were not exercised against real media. |
| Zoom viewport containment | BLOCKED | No live zoomed image or application page geometry was available. |
| Expanded lightbox | BLOCKED | No real image could be expanded; overlay placement, coverage, Close control, and shell stability were unobserved. |
| Expanded zoom | BLOCKED | No backend-served image was available in the expanded viewer. |
| Escape dismissal | BLOCKED | No live lightbox could be opened. |
| Focus restoration | BLOCKED | No live Escape/Close transition or return focus could be observed. |
| Narrow viewport | BLOCKED | The actual application could not load at desktop or `390×844`; no live screenshots were captured. |
| Thread/scope transition | BLOCKED | No authenticated Project or Chat Thread could be selected; stale-selection behavior was unobserved. |
| Media failure presentation | NOT EXERCISED | Optional real-media failure simulation was not safe or possible without a live record. Focused component tests cover the rendered error states; no canonical media was altered. |

## Supporting evidence and limits

The requested regression command ran from `frontend/src`:

```text
pnpm exec vitest run --config vitest.config.ts \
  features/workspace/__tests__/WorkspaceInspectorPanel.test.tsx \
  features/workspace/__tests__/WorkspaceImageViewerModal.test.tsx \
  features/workspace/__tests__/WorkspaceShelfPanel.test.tsx \
  features/workspace/__tests__/WorkspaceDrawer.test.tsx
```

Result: **4 files passed, 40 tests passed**. `git diff --check` passed. These results retain the earlier focused implementation evidence. The prior desktop and `390×844` browser checks used synthetic records in a temporary component fixture; they do not count as the authenticated real-backend evidence required here.

Read-only inspection at this HEAD found `POST /api/documents/notes` creating a `GeneratedDocument` plus Thread/Project links, `/api/media/document-artifacts` listing records, `/api/media/document-artifacts/{artifact_id}` serving detail content, and `/api/media/images` listing persisted images. These are code-path observations only. No live persistence, media delivery, account ownership, or browser rendering claim follows from them.

Cross-account authorization was outside this task and remains supported only by its existing separate tests; no second account was created or manipulated. This proof does not change `docs/architecture/00-current-state.md`, any ADR, the Workspace contract, or the Beta release posture. It is not full supported-release qualification.

**Next prerequisite:** bring up the intended local Compose runtime with its normal operator-managed configuration for this checkout, then repeat the complete authenticated Notes and image proof on the evaluated implementation. The Workspace media seam is **not yet sufficiently live-proven** to proceed to `Delegated Tasks → Shelf → Inspector` on the strength of this result. No production defect has been identified by this blocked attempt.
