import React, { useContext, useMemo } from "react";
import { ProjectContext } from "@/components/layout/ProjectContext";
import PreviewTile from "@/components/ui/PreviewTile";

function getExt(name: string): string {
  const m = name.match(/\.([^.]+)$/);
  return m ? m[1].toLowerCase() : "";
}
function readExtColors(): Record<string, string> {
  if (typeof window === "undefined") return { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
  try {
    const raw = localStorage.getItem("cfy.extColors");
    return raw ? JSON.parse(raw) : { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
  } catch {
    return { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
  }
}

export default function DocumentsView({ docs, projectId: projectIdProp }: { docs: Array<{ name: string; project?: string }>; projectId?: string }) {
  const { projectId: ctxProject } = useContext(ProjectContext);
  const projectId = projectIdProp ?? ctxProject ?? undefined;
  const visible = useMemo(() => (projectId ? docs.filter((d) => (d as any).project === projectId) : docs), [docs, projectId]);
  return (
    <div className="h-full px-4 pt-3 pb-2 space-y-2">
      <div className="text-lg font-semibold" style={{ color: "var(--text)" }}>Documents</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {visible.map((d) => (
          <PreviewTile key={d.name} tone="panel">
            <div className="space-y-2">
              <div className="rounded-[10px] aspect-[4/3]" style={{ background: "var(--panel-bg)" }} />
              <div className="text-sm font-medium truncate">{d.name}</div>
              <div className="text-xs opacity-70 truncate">{getExt(d.name).toUpperCase()}</div>
            </div>
          </PreviewTile>
        ))}
      </div>
    </div>
  );
}
