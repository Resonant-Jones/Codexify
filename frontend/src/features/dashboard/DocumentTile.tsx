import { FileText } from "lucide-react";
import FrameCard from "@/components/surface/FrameCard";

function ext(name: string) {
  const m = name.match(/\.([^.]+)$/);
  return m ? m[1].toLowerCase() : "";
}

export function DocumentTile({
  name,
  color,
  onClick,
  className = "",
}: {
  name: string;
  color: string;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <FrameCard
      hoverPop
      className={`relative aspect-square ${className}`}
      ariaLabel={name}
      onClick={onClick}
      style={{ "--doc-caption-bg": "var(--caption-bg)" } as any}
    >
      <div className="grid h-full place-items-center">
        <FileText className="h-8 w-8" style={{ color }} />
      </div>

      {/* caption ribbon */}
      <div className="absolute inset-x-0 bottom-0">
        <div
          className="px-2 py-1 text-xs text-center"
          style={{ background: "var(--doc-caption-bg)", color: "#fff" }}
        >
          {name}
        </div>
      </div>
    </FrameCard>
  );
}

export { ext };

export default DocumentTile;
