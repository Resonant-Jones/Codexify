import { FolderOpen } from "lucide-react";

export function ProjectTile({ name, color = "var(--text)" }: { name: string; color?: string }) {
  return (
    <div className="relative h-full w-full rounded-[var(--card-radius)] border overflow-hidden pointer-events-auto" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)" }}>
      <div className="grid h-full place-items-center">
        <FolderOpen className="h-8 w-8" style={{ color }} />
      </div>
      <div className="absolute inset-x-0 bottom-0">
        <div className="rounded-[var(--card-radius)] border px-4 py-3 text-left transition-colors" style={{ background: "rgba(0,0,0,0.35)", color: "#fff" }}>
          {name}
        </div>
      </div>
    </div>
  );
}

export default ProjectTile;
