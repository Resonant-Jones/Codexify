Codex prompt — Hotfix Workspace tiles (revert to LayeredCard structure)

Goal: Fix broken Workspace tiles by removing PreviewTile usage in Workspace and restoring the original LayeredCard 2-layer surface (bezel + 3px rim + inner surface) with sane heights. Leave the Threads/Projects sidebar chips as-is.

Guardrails
 • Do not change components/ui/LayeredCard.tsx.
 • Do not change the sidebar chips (desktop/mobile) in AppShell.tsx.
 • Keep page rim 6px, inter-card gap 12px, inner rim 3px.
 • Respect tokens: --panel-bg, --chip-bg, --panel-border, --text, --elevation-shadow-front.

1) Edit src/components/layout/WorkspacePane.tsx

Task: Replace any PreviewTile usage (projects or docs) with the explicit LayeredCard pattern below. Also ensure the grids and spacing are correct.
 • Imports at top:

import LayeredCard from "@/components/ui/LayeredCard";
import { CardContent } from "@/components/ui/card";

Remove import PreviewTile ... from this file (only this file).

 • Projects grid: ensure container uses a proper grid:

{/*Projects*/}
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
  {projects.map((p) => (
    <LayeredCard
      key={p.id}
      tone="panel"
      className="cursor-pointer transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 active:translate-y-0"
    >
      <CardContent className="p-[3px]">
        <button
          type="button"
          onClick={() => onOpenProject(p.id)}
          className="block w-full text-left rounded-xl border px-3 py-2.5"
          style={{
            background: "var(--chip-bg)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            boxShadow: "var(--elevation-shadow-front)"
          }}
        >
          <div className="flex items-center gap-2">
            {/* optional icon/color swatch */}
            <div className="h-4 w-4 rounded-full opacity-80" style={{ background: p.color ?? "var(--panel-border)" }} />
            <span className="font-medium">{p.name}</span>
          </div>
        </button>
      </CardContent>
    </LayeredCard>
  ))}
</div>

 • Documents grid: same structure, with thumbnail sizing and a real min height so nothing collapses:

{/*Documents*/}
<div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
  {docs.map((d) => (
    <LayeredCard
      key={d.id}
      tone="panel"
      className="cursor-pointer transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 active:translate-y-0"
    >
      <CardContent className="p-[3px]">
        <button
          type="button"
          onClick={() => onOpenDoc(d.id)}
          className="block w-full text-left rounded-xl border px-3 py-2.5"
          style={{
            background: "var(--chip-bg)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            boxShadow: "var(--elevation-shadow-front)"
          }}
        >
          {d.thumb ? (
            <img
              src={d.thumb}
              alt={d.title}
              className="block w-full rounded-[10px] aspect-[4/3] object-cover"
              style={{ display: "block", background: "var(--panel-bg)" }}
            />
          ) : (
            <div className="rounded-[10px] aspect-[4/3]" style={{ background: "var(--panel-bg)" }} />
          )}

          <div className="mt-2 text-sm font-medium truncate">{d.title}</div>
          <div className="text-xs opacity-70 truncate">{d.subtitle ?? d.updatedAt ?? ""}</div>
        </button>
      </CardContent>
    </LayeredCard>
  ))}
</div>

 • Remove any wrappers adding overflow-hidden to the grid containers that could clip the tiles.

2) Tokens sanity (only if needed)

If tiles still look like skinny lines, define a safe --chip-bg fallback (skip if already defined in your theme):
 • In your theme/tokens file (where :root and .dark tokens live), ensure:

:root {
  /*slightly lighter than panel in light mode */
  --chip-bg: var(--sheet-bg, #fff);
}
.dark {
  /* slightly lighter than panel in dark mode for lift*/
  --chip-bg: color-mix(in oklab, var(--panel-bg) 90%, white 10%);
}

Don’t touch this if --chip-bg already exists and looks correct elsewhere.

3) Do NOT modify sidebar chips
 • Leave the Threads/Projects chips in AppShell.tsx exactly as they are now (they were looking right).
 • This hotfix only targets WorkspacePane.tsx.

4) Acceptance
 • Workspace project tiles: chunky, elevated, hover-lift; text readable.
 • Workspace document tiles: thumbnail 4:3 (rounded), title + meta; no collapse.
 • Sidebar chips remain unchanged and good-looking.
 • No “React already declared” errors; no PreviewTile import remains in WorkspacePane.tsx.

When finished, print a one-paragraph summary of what you changed and where.
