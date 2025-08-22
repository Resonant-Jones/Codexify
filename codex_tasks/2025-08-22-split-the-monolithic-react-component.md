Task: Split the monolithic React component in
  src/components/persona/layout/AppShell.tsx
into well-scoped files, wire them up, and remove dead code — WITHOUT changing the UI behavior.

Authoritative design rules (must honor exactly):

- “Glass” (refractive) lives BEHIND the Dashboard panel and the Workspace panel only.
  Guardian Chat stays opaque.
- DO NOT frost or blur the global wallpaper; keep the wallpaper high-definition.
- Header should have no visible “white bar” seam; no visual segmentation line across the app.
- No system theme toggle in the main UI. Theme controls live only in Settings.
- Keep existing wallpaper/gradient logic, CSS variables, and accessibility contrast.
- Preserve & reuse existing components if present:
  - ReactiveGlassCard (refractive material) for Dashboard and Workspace surfaces
  - PersonaProvider
  - TagSelector
- Do not introduce UI we cannot see yet (e.g., no RightRail etc).
- Keep Vite alias: `@` → `src/`.

Scope & Permissions:

- You MAY delete/rename files in `src/` to match the new structure,
  EXCEPT do not delete: PersonaProvider, TagSelector, existing UI primitives.
- Update imports to use `@/...`.
- If a previous shim `src/AppShell.tsx` exists, remove it; the real entry remains at
  `src/components/persona/layout/AppShell.tsx`.

Split plan (create these files; move code 1:1 from the monolith):

- src/components/controls/SegmentedThemeControl.tsx         (from SegmentedThemeControl)
- src/components/controls/ContrastChip.tsx                  (from ContrastChip)
- src/features/chat/components/Composer.tsx                 (from Composer)
- src/features/chat/components/Sidebar.tsx                  (from Sidebar)
- src/features/chat/components/ChatBubble.tsx               (from ChatBubble)
- src/features/chat/GuardianChat.tsx                        (wrapper that composes the 3 above)
- src/features/workspace/WorkspacePane.tsx                  (from WorkspacePane)
- src/features/dashboard/DocumentTile.tsx                   (from DocumentTile)
- src/features/dashboard/DashboardView.tsx                  (from DashboardView)
- src/features/settings/SettingsView.tsx                    (from SettingsView)
- src/types/ui.ts                                           (move shared types:
  ThemeMode, Message, Thread, ExtColors, GalleryItem)
- src/components/surface/ReactiveGlassCard.tsx              (reuse existing if present; otherwise create
  and use it as the *container* for Dashboard + Workspace panels only)

Then, refactor src/components/persona/layout/AppShell.tsx to:

- import and compose the above components.
- Keep the theme controller logic, wallpaper/gradient logic, and css var injection (—accent, —panel-bg, etc).
- Remove any header/top-nav “Separator” that creates a visible seam. No hairline border across the page.
- Ensure the Settings view is the only place that can change theme; remove any other theme toggle bindings.

CSS / tokens (index.css):

- Ensure the following CSS variables exist (or add them if missing) and are not overridden globally with blur:
  :root {
    --accent: #6B7280;
    --accent-weak: #7c8491;
    --accent-strong: #5b6575;
    --panel-bg: #f3f4f6;
    --panel-border: #e5e7eb;
    --chip-bg: #e5e7eb;
    --text: #111827;
    --muted: #374151;
  }
  .dark {
    --panel-bg: #202020;
    --panel-border: #3f3f3f;
    --chip-bg: #2f2f2f;
    --text: #ffffff;
    --muted: rgba(255,255,255,0.88);
  }
- Provide a utility class used ONLY by Dashboard and Workspace containers:
  .glass-surface {
    backdrop-filter: blur(12px) saturate(120%);
    -webkit-backdrop-filter: blur(12px) saturate(120%);
    box-shadow: inset 0 1px rgba(255,255,255,0.18),
                inset 0 -1px rgba(0,0,0,0.25),
                0 10px 22px rgba(0,0,0,0.25);
    background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)),
                rgba(255,255,255,0.06);
  }
- Do NOT apply any blur/frost to <body> or the page background.

Wiring specifics:

- AppShell should render:
  - Top nav with brand + navigation buttons (Dashboard, Guardian, Settings) but no visible seam below it.
  - When `view === "dashboard"`: wrap the dashboard card in <ReactiveGlassCard className="glass-surface">.
  - When `view === "dashboard"`: WorkspacePane sits to the right, also inside <ReactiveGlassCard className="glass-surface">.
  - When `view === "guardian"`: GuardianChat remains fully opaque (no glass classes).
  - When `view === "settings"`: SettingsView uses the SegmentedThemeControl inside, not in the header.
- Keep `localStorage` keys as-is (cfy.*).
- Keep the prefill prompt flow for “open chat with prompt” from the Dashboard gallery.

TypeScript / build:

- Update imports to new paths; create simple barrel files where helpful (e.g., features/chat/components/index.ts).
- No changes to Vite alias or tsconfig needed beyond fixing imports.
- Ensure `src/main.tsx` (or your entry) still renders <AppShell />.

Acceptance checklist (must pass locally):

- `pnpm -C ./src typecheck` — no TS errors.
- `pnpm -C ./src dev` — app renders exactly as before.
- Guardian Chat is opaque; Dashboard + Workspace show the refractive glass.
- No visible header seam; wallpaper remains high-def.
- No theme toggle in the main top bar; only in Settings.

Finally:

- Remove any now-unused components that were inlined into the monolith (but keep PersonaProvider and TagSelector).
- Stage and commit with message:
  "ui: split AppShell monolith into modules; apply glass only to dashboard/workspace; keep chat opaque"
