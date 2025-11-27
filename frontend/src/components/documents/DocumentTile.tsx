import * as React from "react";
import clsx from "clsx";
import { FileText } from "lucide-react";
import TileShell from "@/components/surface/TileShell";

export type DocumentFile = {
  name: string;
  ext?: string;
  thumb?: string;
};

type Props = {
  file: DocumentFile;
  onClick?: () => void;
  className?: string;
};

function hexToRgb(hex: string) {
  const n = hex.replace("#", "");
  const v = n.length === 3 ? n.split("").map((c) => c + c).join("") : n;
  const num = parseInt(v, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

function relativeLuminance(hex: string) {
  const { r, g, b } = hexToRgb(hex);
  const srgb = (c: number) => {
    const channel = c / 255;
    return channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
  };
  const R = srgb(r);
  const G = srgb(g);
  const B = srgb(b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function contrastRatio(a: string, b: string) {
  const L1 = relativeLuminance(a);
  const L2 = relativeLuminance(b);
  const [hi, lo] = L1 >= L2 ? [L1, L2] : [L2, L1];
  return (hi + 0.05) / (lo + 0.05);
}

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

export default function DocumentTile({ file, onClick, className }: Props) {
  const extColors = React.useMemo(readExtColors, []);
  const ext = (file.ext || getExt(file.name) || "").toLowerCase();
  const bannerColor = extColors[ext] || "#6B7280"; // fallback gray
  const onColor = contrastRatio(bannerColor, "#ffffff") >= 4.5 ? "#ffffff" : "#111827";

  const content = (
    <div className="relative flex aspect-[3/4] w-full flex-col">
      {file.thumb ? (
        <img src={file.thumb} alt={file.name} className="absolute inset-0 h-full w-full object-cover" />
      ) : (
        <div className="absolute inset-0 grid place-items-center">
          <FileText className="h-7 w-7" style={{ color: bannerColor }} />
        </div>
      )}
      <div className="mt-auto">
        <div className="flex h-11 items-center px-2 text-xs" style={{ background: bannerColor, color: onColor }}>
          <div className="flex-1 truncate" title={file.name}>
            {file.name}
          </div>
          {ext && <div className="ml-2 font-semibold uppercase opacity-90">.{ext}</div>}
        </div>
      </div>
    </div>
  );

  const baseClasses = clsx("aspect-square w-[125px]", className);

  if (onClick) {
    return (
      <TileShell
        as="button"
        type="button"
        className={clsx(
          baseClasses,
          "cursor-pointer text-left transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
        )}
        style={{ padding: 0 }}
        onClick={onClick}
        aria-label={file.name}
      >
        {content}
      </TileShell>
    );
  }

  return (
    <TileShell className={baseClasses} style={{ padding: 0 }} aria-label={file.name}>
      {content}
    </TileShell>
  );
}

export { getExt };
