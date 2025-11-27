import { FolderOpen } from "lucide-react";

export function ProjectTile({
  name,
  color = "var(--text)",
  onClick,
}: {
  name: string;
  color?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="relative aspect-square rounded-2xl overflow-hidden border shadow-md cursor-pointer"
      style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)" }}
    >
      <div className="grid h-full place-items-center">
        <FolderOpen className="h-8 w-8" style={{ color }} />
      </div>
      <div className="absolute inset-x-0 bottom-0">
        <div
          className="px-2 py-1 text-xs text-center"
          style={{ background: "rgba(0,0,0,0.35)", color: "#fff" }}
        >
          {name}
        </div>
      </div>
    </div>
  );
}

export default ProjectTile;
