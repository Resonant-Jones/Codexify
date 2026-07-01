# Frontend Typecheck Ledger

This document preserves the frontend TypeScript baseline for the mechanical triage pass. It is a durable snapshot, not a fix log.

The current checkout in this workspace validates at 158 frontend TypeScript errors, which matches the archived repaired baseline from commit `45e54111a266804df5de7b97e64d9fb4c1a04a57`.

## Validation command

Run from `frontend/src`:

```bash
node ../../node_modules/.pnpm/typescript@5.9.3/node_modules/typescript/bin/tsc --noEmit -p tsconfig.app.json
```

## Baseline

- Before triage: 199 errors
- Repaired baseline: 158 errors
- Live validated count in this checkout: 158 errors
- Triage commit: `45e54111a266804df5de7b97e64d9fb4c1a04a57`
- Scope of the triage pass: mechanical-only cleanup, no behavior changes

## Remaining Clusters

| Area | Count | Representative files | Remaining shape |
| --- | ---: | --- | --- |
| `commandCenter` | 32 | `components/persona/layout/AppShell.tsx`, `features/commandCenter/components/CommandCenterShell.tsx`, `features/commandCenter/components/TraceWorkbench.tsx`, `features/commandCenter/HeartbeatStatusPanel.tsx`, `features/commandCenter/commandCenterRunAggregation.ts` | prop/type drift, missing exports, unused symbols, callback return mismatches |
| `chat` | 27 | `features/chat/GuardianChat.tsx`, `features/chat/components/GuardianThreadApprovalRail.tsx`, `features/chat/hooks/useInferenceRequestState.ts`, `features/chat/useChat.ts`, `features/chat/components/ChatBubble.tsx` | request-state union drift, nullability, prop mismatch, completion-state shape drift |
| `persona/layout` | 24 | `components/persona/layout/AppShell.tsx`, `components/persona/layout/GuardianChatWithSidebar.tsx` | token names missing, event type mismatch, drawer config shape drift, unused symbols |
| `personaStudio` | 20 | `features/personaStudio/components/PersonaVoicePanel.tsx`, `features/personaStudio/PersonaStudioPage.tsx`, `features/personaStudio/components/StudioGuidePanel.tsx`, `features/personaStudio/PersonaPreviewPanel.tsx`, `features/personaStudio/components/DiagnosticsPanel.tsx` | variant and prop shape drift, unused imports, config typing mismatches |
| `sidebar` | 12 | `components/sidebar/useProjectsCache.ts`, `components/sidebar/ProjectList.tsx`, `components/sidebar/SidebarRoot.tsx`, `components/sidebar/ThreadList.tsx`, `components/sidebar/useSidebarThreads.ts` | `Project[]` vs `SidebarProjectRecord` mismatch, prop shape drift, duplicate or unused imports |
| `settings` | 8 | `features/settings/components/PersonalFactsPanel.tsx`, `features/settings/SettingsView.tsx`, `features/settings/api/persona.ts` | option and shape mismatches, local prop typing drift |
| `flowBuilder` | 7 | `features/flowBuilder/components/FlowBuilderGraphCanvas.tsx`, `features/flowBuilder/FlowBuilderPage.tsx`, `features/flowBuilder/hooks/useFlowDraftState.ts`, `features/flowBuilder/model/flowDraft.ts`, `features/flowBuilder/components/FlowBuilderParameterRail.tsx` | stage/node selection shape drift, export mismatch, node-field typing drift |
| `ui` | 6 | `components/ui/PreviewTile.tsx`, `components/ui/dropdown-menu.tsx` | invalid prop names passed to shared primitives |
| `workspace` | 6 | `features/workspace/components/WorkspaceInspectorPanel.tsx`, `features/workspace/components/WorkspaceShelfPanel.tsx`, `features/workspace/WorkspacePane.tsx` | config and prop shape drift |
| `dashboard` | 3 | `components/dashboard/DashboardView.tsx` | union narrowing and index-signature issues |
| `modals` | 3 | `components/modals/ImageGenModal.tsx`, `components/modals/ChatGPTImportModal.tsx` | unused locals and variant prop mismatch |
| `contracts` | 2 | `contracts/runtimeTokens.ts`, `contracts/slashCommands.ts` | return-path and assertion-shape issues |
| `hooks` | 2 | `hooks/useRenderableMediaSrc.ts`, `hooks/useRuntimeHealth.ts` | local hook typing drift |
| `shared` | 2 | `shared/runtimeVisualState.ts` | impossible comparison and union-overlap issues |
| `lib` | 1 | `lib/api.ts` | response JSON shape narrowing |
| `App.tsx` | 1 | `App.tsx` | remaining control-flow or type-narrowing issue |
| `documents` | 1 | `components/documents/DocumentsView.tsx` | ext-color indexing issue |
| `SessionRail` | 1 | `components/SessionRail/SessionRail.tsx` | unused import cleanup |
| `types` | 1 | `types/rag.ts` | missing export in RAG types |

## Error Shape Summary

- `TS2322`: 52
- `TS6133`: 46
- `TS2345`: 15
- `TS2339`: 9
- `TS18047`: 9
- `TS2769`: 7
- `TS2724`: 3
- `TS2551`: 3
- `TS7053`: 2
- `TS2304`: 2
- `TS6196`: 2
- `TS2367`: 2
- `TS2366`: 1
- `TS2352`: 1
- `TS7016`: 1
- `TS2677`: 1
- `TS2459`: 1
- `TS2305`: 1

## Known Limitations

- An offline `pnpm`/store repair issue affected the earlier validation pass, so the compiler was run against the locally repaired frontend toolchain rather than a clean dependency reinstall.
- `git diff --check` against `frontend/src/tsconfig.app.json` is still affected by the repository's Git LFS clean filter; the same check passes when that file is excluded.
- The remaining 158 errors are intentionally unresolved. They are preserved here as the baseline for the next scoped fix pass.

## Notes

- Do not rely on `/private/tmp/frontend-typecheck-current.log` as the source of truth. This file is the durable baseline.
- Keep future fix passes narrow and cluster-based so behavior changes stay explicit.
