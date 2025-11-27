import { FolderOpen } from "lucide-react";
import TileShell from "@/components/surface/TileShell";

export function ProjectTile({ name, color = "var(--text)" }: { name: string; color?: string }) {
  return (
    <TileShell
      className="relative h-full w-full pointer-events-auto"
      style={{ background: "var(--panel-bg)" }}
    >
      <div className="grid h-full place-items-center">
        <FolderOpen className="h-8 w-8" style={{ color }} />
      </div>
      <div className="absolute inset-x-0 bottom-0">
        <div className="rounded-[var(--card-radius)] border px-4 py-3 text-left transition-colors" style={{ background: "rgba(0,0,0,0.35)", color: "#fff" }}>
          {name}
        </div>
      </div>
    </TileShell>
  );
}

export default ProjectTile;
