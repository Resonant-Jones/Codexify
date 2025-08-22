import { FileText } from "lucide-react";

function ext(name: string) {
  const m = name.match(/\.([^.]+)$/);
  return m ? m[1].toLowerCase() : "";
}

export function DocumentTile({ name, color }: { name: string; color: string }) {
  return (
    <div className="relative aspect-square rounded-2xl overflow-hidden border shadow-sm" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)" }}>
      <div className="grid h-full place-items-center">
        <FileText className="h-8 w-8" style={{ color }} />
      </div>
      <div className="absolute inset-x-0 bottom-0">
        <div className="px-2 py-1 text-xs text-center" style={{ background: "rgba(0,0,0,0.35)", color: "#fff" }}>
          {name}
        </div>
      </div>
    </div>
  );
}

export { ext };

export default DocumentTile;

