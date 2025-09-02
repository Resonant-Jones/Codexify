Codex prompt — Unify Preview Tiles (projects, threads, docs, gallery)

You are editing a Vite + React + TS app with Tailwind + shadcn/ui.

Guardrails (don’t break)
 • Do not edit components/ui/LayeredCard.tsx internals.
 • Keep page rim 6px, inter-card gap 12px, inner rim 3px.
 • Respect tokens: --panel-bg, --chip-bg, --panel-border, --text, --elevation-shadow-front.
 • Avoid duplicate imports and duplicate exports (fix the “React already declared” and “no default export” issues as you go).

1) Add a reusable PreviewTile

Create src/components/ui/PreviewTile.tsx:

import * as React from "react";
import LayeredCard from "@/components/ui/LayeredCard";
import { CardContent } from "@/components/ui/card";

type PreviewTileProps = React.PropsWithChildren<{
  active?: boolean;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
  tone?: "chat" | "panel" | "neutral";
}>;

export default function PreviewTile({
  active,
  className,
  style,
  onClick,
  tone,
  children,
}: PreviewTileProps) {
  return (
    <LayeredCard
      tone={tone}
      className={className}
      style={active ? ({ boxShadow: "inset 0 0 0 2px var(--accent-strong)" } as React.CSSProperties) : undefined}
      onClick={onClick}
    >
      <CardContent className="p-[3px]">
        <div
          className="rounded-xl border min-h-[88px] px-3 py-2.5 shadow-sm"
          style={{
            background: "var(--chip-bg)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            boxShadow: "var(--elevation-shadow-front)",
            ...style,
          }}
        >
          {children}
        </div>
      </CardContent>
    </LayeredCard>
  );
}

This gives every “preview” a visible surface, proper min height, the 3px rim, and your front elevation.

2) Projects & Threads (sidebar, desktop + mobile)

In src/components/layout/AppShell.tsx inside GuardianChat:
 • Import once at top:

import PreviewTile from "@/components/ui/PreviewTile";

 • Replace the Projects list items’ inner button wrapper with PreviewTile. Example:

<li key="loose">
  <PreviewTile tone={chatTone} onClick={() => { setProjectId(null); setSidebarTab("threads"); }}>
    <div className="flex items-center gap-2">
      <FolderOpen className="h-4 w-4 opacity-80" />
      <span>Loose threads</span>
    </div>
  </PreviewTile>
</li>
{projects.filter(p => p.id !== "loose").map(p => (
  <li key={p.id}>
    <PreviewTile tone={chatTone} active={projectId === p.id} onClick={() => { setProjectId(p.id); setSidebarTab("threads"); }}>
      <div className="flex items-center gap-2">
        <FolderOpen className="h-4 w-4 opacity-80" />
        <span>{p.name}</span>
      </div>
    </PreviewTile>
  </li>
))}

 • Replace the Threads list items similarly (both desktop and mobile sheet):

<li key={t.id}>
  <PreviewTile tone={chatTone} active={t.id === activeId} onClick={() => { setActiveId(t.id); /* close sheet on mobile branch */ }}>
    <div className="flex items-center justify-between gap-3 min-w-0">
      <div className="min-w-0">
        <div className="font-medium truncate">{t.title}</div>
        <div className="text-xs opacity-70 truncate">{t.lastMessage || " "}</div>
      </div>
      {t.unread > 0 && (
        <span
          className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-2 text-xs font-semibold"
          style={{ background: "var(--accent-strong)", color: "#fff" }}
        >
          {t.unread}
        </span>
      )}
    </div>
  </PreviewTile>
</li>

Remove any leftover inner <button> wrappers so the tile’s height doesn’t collapse.

3) Workspace document previews

In src/components/layout/WorkspacePane.tsx (where project/doc previews render):
 • Import PreviewTile.
 • Wrap each project and document preview in PreviewTile. For documents with thumbnails/images:

<PreviewTile tone="panel" onClick={() => openDoc(d.id)}>
  <div className="space-y-2">
    {d.thumb ? (
      <img
        src={d.thumb}
        alt={d.title}
        className="block w-full rounded-[10px] aspect-[4/3] object-cover"
        style={{ background: "var(--panel-bg)" }}
      />
    ) : null}
    <div className="text-sm font-medium truncate">{d.title}</div>
    <div className="text-xs opacity-70 truncate">{d.subtitle || d.updatedAt}</div>
  </div>
</PreviewTile>

4) Documents page

In src/components/documents/DocumentsView.tsx:
 • Import PreviewTile.
 • Ensure the grid uses tiles, not naked buttons/divs. Example:

<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
  {docs.map(d => (
    <PreviewTile key={d.id} tone="panel" onClick={() => openDoc(d.id)}>
      {/* same inner content pattern as above */}
    </PreviewTile>
  ))}
</div>

5) Gallery page + export fix

In src/components/gallery/GalleryView.tsx:
 • Fix duplicate imports (there was a “React already declared” error). Keep only:

import React, { useContext, useMemo } from "react";
import { ProjectContext } from "@/components/layout/ProjectContext"; // or from AppShell if that’s correct in your repo

 • Ensure a default export (we had “No matching export for import default” before). At bottom:

export default GalleryView;

 • Use PreviewTile for each image:

<PreviewTile tone="panel">
  <button type="button" className="block w-full rounded-[10px] overflow-hidden">
    <img
      src={item.src}
      alt={item.prompt}
      className="block w-full aspect-square object-cover"
      style={{ display: "block" }}
    />
  </button>
</PreviewTile>

6) Token sanity (so tiles don’t look like lines)

If not already defined, ensure --chip-bg exists for both modes (e.g., in :root / .dark token sets). It should be slightly lighter than --panel-bg in dark mode, and var(--sheet-bg) or pure white in light mode.

Do not change LayeredCard; we’re only standardizing the inner surface.

7) Acceptance
 • Projects tab shows chunky chip tiles (Loose + others).
 • Threads list shows the same chunky tiles (desktop and mobile).
 • Workspace, Documents, Gallery all show real tiles (no skinny lines).
 • No duplicate React/import/export errors.
 • Light/dark keeps the same spacing, rims, shadows.

When done, print a short summary of files changed and confirm all four preview zones render with the same tile look.

⸻
