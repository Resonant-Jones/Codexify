import * as React from "react";
import { createProject, deleteProject } from "@/api";
import { useState } from "react";
import PreviewTile from "@/components/ui/PreviewTile";
import DocumentPreviewTile from "@/components/ui/DocumentPreviewTile";
import { ExtColors, GalleryItem } from "@/types/ui";
import ComboDashboardCard from "./ComboDashboardCard";

export default function DashboardView({
  extColors,
  gallery,
  onImagePrompt,
  workspaceOpen,
}: {
  extColors: ExtColors;
  gallery: GalleryItem[];
  onImagePrompt: (p: string) => void;
  workspaceOpen?: boolean;
}) {
  // Handlers for card actions
  const handleCreateProject = React.useCallback(async () => {
    const name = prompt("Project name:");
    if (name) {
      try {
        await createProject(name);
        alert(`Project "${name}" created.`);
      } catch (e) {
        console.error(e);
        alert("Failed to create project.");
      }
    }
  }, []);

  const handleCreateThread = React.useCallback(() => {
    alert("New Thread functionality is not yet implemented.");
  }, []);
  // Helpers
  const ext = (name: string) => (name.includes(".") ? name.split(".").pop()!.toLowerCase() : "");
  const readableOn = (hex: string) => {
    let h = hex.replace("#", "");
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    const r = parseInt(h.substring(0, 2), 16) / 255;
    const g = parseInt(h.substring(2, 4), 16) / 255;
    const b = parseInt(h.substring(4, 6), 16) / 255;
    const srgb = [r, g, b].map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
    const L = 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
    return L > 0.5 ? "#111111" : "#ffffff";
  };
  const colorFor = (name: string) =>
    extColors[ext(name) as keyof typeof extColors] || "#6366f1";

  // Demo lists (replace with real data when wired)
  const recentDocs = ["Covenant.pdf", "Roadmap.md", "Vision.txt", "Design.sketch"];
  const pinned = "Sovereign AI Principles,Health & Wellness,Novel Outline,Meeting Prep".split(",");

  return (
    <section className="w-full h-full min-h-0 flex flex-col overflow-hidden">
      {/* Main grid fills the remaining height */}
      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 items-stretch gap-[var(--gutter)]">
        {/* Column 1: two equal-height STACKED cards (Pinned / Recent) */}
        <ComboDashboardCard 
          pinned={pinned} 
          recentDocs={recentDocs} 
          onCreateProject={handleCreateProject}
          onCreateThread={handleCreateThread}
        />

        {/* Column 2: Gallery card - always visible */}
        <div className="glass-surface rounded-2xl p-[3px] h-full min-h-0">
          <div
            className="rounded-xl border shadow-sm h-full flex flex-col"
            style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
          >
            <div className="px-4 pt-3 pb-2 shrink-0 flex items-center justify-between">
              <div className="text-lg font-semibold">Gallery</div>
              <button className="text-sm opacity-80 hover:opacity-100">See all</button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-4 pt-0">
              <div className="grid gap-5 justify-start" style={{ gridTemplateColumns: "repeat(auto-fill, 112px)" }}>
                {gallery.map((item, i) => (
                  <PreviewTile
                    key={i}
                    layer="flat"
                    square
                    bezel="simple"
                    elevation="md"
                    bevel="soft"
                    onClick={() => onImagePrompt(item.prompt)}
                    style={{ background: "var(--panel-bg)" }}
                    className="cursor-pointer w-[112px]"
                  >
                    <img src={item.src} alt={item.prompt || "Gallery image"} />
                  </PreviewTile>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
