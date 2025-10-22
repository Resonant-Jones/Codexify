import React, { useContext, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import PreviewTile from "@/components/ui/PreviewTile";
import { Button } from "@/components/ui/button";
import { ProjectContext } from "@/components/layout/ProjectContext";

export function DocChip({
  label,
  onClick,
  active = false,
  variant = "default",
  className = "",
}: {
  label: string;
  onClick?: () => void;
  active?: boolean;
  variant?: "default" | "dock";
  className?: string;
}) {
  const isDark = typeof window !== "undefined"
    ? document.documentElement.classList.contains("dark")
    : false;
  const ink = isDark ? "#ffffff" : "#000000";
  // Prefer simple, widely supported fallbacks so chips render consistently
  // across browsers; avoid color-mix to prevent invalid background results.
  const backPlate = typeof window !== "undefined"
    ? (getComputedStyle(document.documentElement).getPropertyValue("--chip-bg").trim() || "var(--chip-bg, var(--panel-bg))")
    : "var(--chip-bg, var(--panel-bg))";
  const paperBg = typeof window !== "undefined"
    ? (getComputedStyle(document.documentElement).getPropertyValue("--panel-bg").trim() || "var(--panel-bg)")
    : "var(--panel-bg)";

  // Base outer shell (beveled plate)
  const outer = "group w-full rounded-2xl border p-[3px] text-left appearance-none transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-white/10";
  const ring = active ? "ring-1" : "";

  // Inner face (paper) — default keeps your original shadows; dock trims padding/weight
  const innerBase = "rounded-xl border text-sm shadow-[0_0_18px_rgba(0,0,0,0.12),0_8px_18px_rgba(0,0,0,0.18),0_2px_6px_rgba(0,0,0,0.12),inset_0_1px_0_rgba(255,255,255,0.28),inset_0_-1px_0_rgba(0,0,0,0.08)] group-hover:shadow-[0_0_24px_rgba(0,0,0,0.14),0_12px_24px_rgba(0,0,0,0.22),0_4px_12px_rgba(0,0,0,0.16),inset_0_1px_0_rgba(255,255,255,0.30),inset_0_-1px_0_rgba(0,0,0,0.10)] group-active:shadow-[0_0_14px_rgba(0,0,0,0.12),0_6px_16px_rgba(0,0,0,0.18),0_2px_6px_rgba(0,0,0,0.14),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(0,0,0,0.08)]";
  const innerPadding = variant === "dock" ? "px-3 py-1.5" : "px-3 py-2";
  const innerRadius  = variant === "dock" ? "rounded-xl" : "rounded-xl"; // same radius, different density
  const innerClasses = [innerBase, innerPadding, innerRadius].join(" ");

  return (
    <button
      onClick={onClick}
      className={[outer, ring, className].join(" ")}
      style={{ background: backPlate, borderColor: "var(--panel-bezel)" }}
    >
      <div
        className={innerClasses}
        style={{ background: paperBg, borderColor: "var(--panel-bezel)", color: ink }}
      >
        <span className="workspace-ink truncate">{label}</span>
      </div>
    </button>
  );
}

// Convenience alias for top dock chips without changing other files:
export const DockChip = (props: Omit<Parameters<typeof DocChip>[0], "variant">) => (
  <DocChip {...props} variant="dock" />
);

export default function WorkspacePane({
  bare = false,
  activeDoc,
  onOpenInThread,
}: {
  bare?: boolean;
  activeDoc?: string | null;
  onOpenInThread?: (doc: string) => void;
}) {
  const { projectId } = useContext(ProjectContext);

  const isDark = typeof window !== "undefined"
    ? document.documentElement.classList.contains("dark")
    : false;
  const ink = isDark ? "#ffffff" : "#000000";
  const backPlate = isDark
    ? "color-mix(in oklab, var(--panel-bg) 88%, white 12%)"
    : "color-mix(in oklab, #ffffff 85%, black 15%)"; // slightly darker than paper to form the occlusion ring
  const paperBg = isDark
    ? "color-mix(in oklab, var(--panel-bg) 86%, black 14%)"
    : "color-mix(in oklab, var(--panel-bg) 64%, white 36%)"; // bright paper like the Workspace/Settings look

  const tone = isDark ? "panel" : "sheet";

  const docsAll = ["Covenant.pdf", "Roadmap.md", "Vision.txt", "Design.sketch"];
  const docs = useMemo(() => {
    if (!projectId) return docsAll;
    if (projectId == "p1") return ["Covenant.pdf", "Roadmap.md"];
    if (projectId == "p2") return ["Vision.txt", "Design.sketch"];
    return docsAll;
  }, [projectId]);

  const currentDoc = activeDoc ?? null;
  const headerTitle = currentDoc ? `Workspace · ${currentDoc}` : "Workspace";

  const content = (
    <div className="flex h-full min-h-0 flex-col p-4" style={{ color: ink }}>
      <style>{`
        :root:not(.dark) .workspace-ink { color: #000 !important; }
        .dark .workspace-ink { color: #fff !important; }
      `}</style>
      <div className="mb-2 flex items-center justify-between text-sm font-semibold opacity-90">
        <span className="truncate">{headerTitle}</span>
        {currentDoc && onOpenInThread && (
          <Button
            size="sm"
            className="rounded-[var(--tile-radius,19px)] px-3"
            onClick={() => onOpenInThread(currentDoc)}
          >
            Open in Thread
          </Button>
        )}
      </div>

      <div className="rounded-2xl border border-[var(--panel-border)] bg-[color-mix(in oklab,var(--panel-bg) 94%,transparent)] p-4 text-sm leading-relaxed shadow-inner">
        {currentDoc ? (
          <div>
            <div className="text-xs uppercase tracking-wide opacity-70">Now Reading</div>
            <div className="mt-1 text-base font-semibold">{currentDoc}</div>
            <p className="mt-2 text-xs opacity-70">
              Jot notes or draft an outline here before looping your Guardian in.
            </p>
          </div>
        ) : (
          <div className="text-xs opacity-70">
            Select a document from the Documents view to load it into the workspace.
          </div>
        )}
      </div>

      <div className="pt-4">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide opacity-70">
          Docs
        </div>
        {/* Documents */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {docs.map((d) => (
            <PreviewTile key={d} tone="panel" className="cursor-pointer transition-transform duration-150 ease-[cubic-bezier(.2,.7,.2,1)] hover:-translate-y-0.5 active:translate-y-0">
              <div className="min-h-[112px]">
                <div className="rounded-[10px] aspect-[4/3]" style={{ background: "var(--panel-bg)" }} />
                <div className="mt-2 text-sm font-medium truncate">{d}</div>
                <div className="text-xs opacity-70 truncate">&nbsp;</div>
              </div>
            </PreviewTile>
          ))}
        </div>
      </div>

      <div className="flex-1" />
    </div>
  );

  if (bare) {
    return content;
  }

  return (
    <Card
      className="h-full min-h-0 w-[340px] shrink-0 overflow-hidden rounded-2xl border shadow-sm !text-black dark:!text-white"
      style={{
        background: "var(--panel-bg)",
        borderColor: "var(--panel-border)",
        color: ink,
      }}
    >
      <CardContent className="h-full min-h-0 p-0">
        {content}
      </CardContent>
    </Card>
  );
}
