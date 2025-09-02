import * as React from "react";
import PreviewTile from "@/components/ui/PreviewTile";
import { FileText } from "lucide-react";

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
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const R = srgb(r), G = srgb(g), B = srgb(b);
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

export default function DocumentPreviewTile({ file, onClick, className }: Props) {
  const extColors = React.useMemo(readExtColors, []);
  const ext = (file.ext || getExt(file.name) || "").toLowerCase();
  const bannerColor = extColors[ext] || "#6B7280"; // fallback gray
  const onColor = contrastRatio(bannerColor, "#ffffff") >= 4.5 ? "#ffffff" : "#111827";
  const mergedClass = ["w-[112px]", className].filter(Boolean).join(" ");
  return (
    <PreviewTile className={mergedClass} square bezel="simple" tone="panel" layer="flat" elevation="md" bevel="soft" onClick={onClick}>
      <div className="relative w-full h-full">
        {file.thumb ? (
          <img src={file.thumb} alt={file.name} className="absolute inset-0 w-full h-full object-cover block" />
        ) : (
          <>
            <div className="absolute inset-0" style={{ background: "var(--chip-bg)" }} />
            <div className="absolute inset-0 grid place-items-center">
              <FileText className="h-7 w-7" style={{ color: bannerColor }} />
            </div>
          </>
        )}
        <div className="absolute inset-x-0 bottom-0" style={{ background: bannerColor, color: onColor }}>
          <div className="px-2 flex items-center h-11 text-xs">
            <div className="truncate flex-1" title={file.name}>{file.name}</div>
            {ext && <div className="ml-2 font-semibold uppercase opacity-90">.{ext}</div>}
          </div>
        </div>
      </div>
    </PreviewTile>
  );
}
