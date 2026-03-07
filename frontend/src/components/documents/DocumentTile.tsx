import * as React from "react";
import clsx from "clsx";
import { BookOpen, FileText } from "lucide-react";
import TileShell from "@/components/surface/TileShell";
import { ExtColors } from "@/types/ui";

export type DocumentFile = {
  name: string;
  ext?: string;
  thumb?: string;
  embeddingStatus?: string;
  embeddingError?: string;
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

const STATUS_STYLES: Record<
  string,
  { label: string; background: string; color: string; border: string }
> = {
  pending: {
    label: "Pending",
    background: "#e2e8f0",
    color: "#1f2937",
    border: "rgba(15, 23, 42, 0.15)",
  },
  processing: {
    label: "Processing",
    background: "#fde047",
    color: "#713f12",
    border: "rgba(113, 63, 18, 0.25)",
  },
  ready: {
    label: "Ready",
    background: "#bbf7d0",
    color: "#14532d",
    border: "rgba(20, 83, 45, 0.2)",
  },
  failed: {
    label: "Failed",
    background: "#fecaca",
    color: "#7f1d1d",
    border: "rgba(127, 29, 29, 0.25)",
  },
};

function resolveStatusLabel(raw?: string) {
  if (!raw) return null;
  const key = raw.trim().toLowerCase();
  if (!key) return null;
  const config = STATUS_STYLES[key];
  if (config) return config;
  const label = key.charAt(0).toUpperCase() + key.slice(1);
  return {
    label,
    background: "#e5e7eb",
    color: "#111827",
    border: "rgba(15, 23, 42, 0.15)",
  };
}

function resolveErrorHint(raw?: string) {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const lower = trimmed.toLowerCase();
  if (lower.includes("parsed_text_missing")) return "No text";
  if (lower.includes("no_chunks")) return "No chunks";
  if (lower.includes("timeout")) return "Timeout";
  if (lower.includes("redis") || lower.includes("queue")) return "Queue error";
  const cleaned = trimmed.replace(/[_-]+/g, " ").trim();
  if (!cleaned) return null;
  if (cleaned.length > 18) return `${cleaned.slice(0, 18).trimEnd()}...`;
  return cleaned;
}

function readExtColors(): Record<string, string> {
  const defaults: ExtColors = {
    pdf: "#ef4444",
    md: "#6366f1",
    txt: "#06b6d4",
    sketch: "#f59e0b",
    doc: "#0ea5e9",
    docx: "#2563eb",
    jpeg: "#d946ef",
    png: "#06b6d4",
    codex: "#22c55e",
  };
  if (typeof window === "undefined") return defaults;
  try {
    const raw = localStorage.getItem("cfy.extColors");
    const parsed = raw ? JSON.parse(raw) : {};
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

export default function DocumentTile({ file, onClick, className }: Props) {
  const extColors = React.useMemo(readExtColors, []);
  const fileName = file?.name || "Untitled";
  const ext = (file?.ext || getExt(fileName) || "").toLowerCase();
  const bannerColor = extColors[ext] || "#6B7280"; // fallback gray
  const onColor = contrastRatio(bannerColor, "#ffffff") >= 4.5 ? "#ffffff" : "#111827";
  const Icon = ext === "codex" ? BookOpen : FileText;
  const status = resolveStatusLabel(file?.embeddingStatus);
  const statusKey = file?.embeddingStatus?.trim().toLowerCase();
  const errorHint = statusKey === "failed" ? resolveErrorHint(file?.embeddingError) : null;
  const statusLabel = status
    ? `${status.label}${errorHint ? ` - ${errorHint}` : ""}`
    : null;

  const content = (
    <div className="relative flex h-full w-full flex-col">
      {file?.thumb ? (
        <img src={file.thumb} alt={fileName} className="absolute inset-0 h-full w-full object-cover" />
      ) : (
        <div className="absolute inset-0 grid place-items-center">
          <Icon className="h-7 w-7" style={{ color: bannerColor }} />
        </div>
      )}
      {status && (
        <span
          className="absolute right-2 top-2 z-10 max-w-[120px] truncate rounded-full border px-2 py-0.5 text-[10px] font-semibold"
          style={{
            background: status.background,
            color: status.color,
            borderColor: status.border,
          }}
        >
          {statusLabel}
        </span>
      )}
      <div className="mt-auto">
        <div className="flex h-11 items-center px-2 text-xs" style={{ background: bannerColor, color: onColor }}>
          <div className="flex-1 truncate" title={fileName}>
            {fileName}
          </div>
          {ext && <div className="ml-2 font-semibold uppercase opacity-90">.{ext}</div>}
        </div>
      </div>
    </div>
  );

  const baseClasses = clsx("shrink-0", className);

  if (onClick) {
    return (
      <TileShell
        as="button"
        type="button"
        sizeVariant="document"
        className={clsx(
          baseClasses,
          "cursor-pointer text-left transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] focus-visible:ring-offset-2"
        )}
        style={{ padding: 0 }}
        onClick={onClick}
        aria-label={fileName}
      >
        {content}
      </TileShell>
    );
  }

  return (
    <TileShell
      sizeVariant="document"
      className={baseClasses}
      style={{ padding: 0 }}
      aria-label={fileName}
    >
      {content}
    </TileShell>
  );
}

export { getExt };
