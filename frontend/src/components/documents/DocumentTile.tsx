import * as React from "react";
import clsx from "clsx";
import { BookOpen, FileText } from "lucide-react";
import TileShell from "@/components/surface/TileShell";
import {
  deleteAsset,
  downloadAsset,
  notifyAssetActionError,
  resolveAssetDownloadUrl,
} from "@/lib/assetActions";
import { ExtColors } from "@/types/ui";

export type DocumentFile = {
  id?: string;
  name: string;
  ext?: string;
  thumb?: string;
  src_url?: string;
  srcUrl?: string;
  src?: string;
  url?: string;
  type?: "file" | "codex_entry";
  embeddingStatus?: string;
  embeddingError?: string;
};

type Props = {
  file: DocumentFile;
  onClick?: () => void;
  onDeleted?: (file: DocumentFile) => void;
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

function splitDocumentLabel(name: string, providedExt?: string) {
  const normalizedName = name.trim() || "Untitled";
  const normalizedExt = (providedExt || getExt(normalizedName) || "")
    .replace(/^\./, "")
    .toLowerCase();

  if (!normalizedExt) {
    return { baseName: normalizedName, extLabel: "" };
  }

  const suffix = `.${normalizedExt}`;
  const baseName = normalizedName.toLowerCase().endsWith(suffix)
    ? normalizedName.slice(0, normalizedName.length - suffix.length)
    : normalizedName;

  return {
    baseName: baseName || normalizedName,
    extLabel: normalizedExt,
  };
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

export default function DocumentTile({ file, onClick, onDeleted, className }: Props) {
  const extColors = React.useMemo(readExtColors, []);
  const fileName = file?.name || "Untitled";
  const ext = (file?.ext || getExt(fileName) || "").toLowerCase();
  const { baseName, extLabel } = React.useMemo(
    () => splitDocumentLabel(fileName, ext),
    [ext, fileName]
  );
  const fileType = file?.type === "codex_entry" ? "codex_entry" : "file";
  const bannerColor = extColors[ext] || "#6B7280"; // fallback gray
  const onColor = contrastRatio(bannerColor, "#ffffff") >= 4.5 ? "#ffffff" : "#111827";
  const Icon = ext === "codex" ? BookOpen : FileText;
  const status = resolveStatusLabel(file?.embeddingStatus);
  const statusKey = file?.embeddingStatus?.trim().toLowerCase();
  const errorHint = statusKey === "failed" ? resolveErrorHint(file?.embeddingError) : null;
  const statusLabel = status
    ? `${status.label}${errorHint ? ` - ${errorHint}` : ""}`
    : null;
  const [isDeleted, setIsDeleted] = React.useState(false);
  const downloadUrl = React.useMemo(
    () =>
      resolveAssetDownloadUrl(
        file?.src_url || file?.srcUrl || file?.src || file?.url
      ),
    [file]
  );
  const canDownload = fileType !== "codex_entry" && !!downloadUrl;
  const canDelete =
    fileType !== "codex_entry" &&
    typeof file?.id === "string" &&
    file.id.trim().length > 0;

  const emitDeletedEvent = React.useCallback(() => {
    if (typeof window === "undefined") return;
    const title = fileName.replace(/\.[^./\\]+$/, "") || fileName;
    try {
      window.dispatchEvent(
        new CustomEvent("cfy:documents:delete", {
          detail: {
            doc: {
              id: file.id,
              name: fileName,
              title,
              ext: ext || getExt(fileName),
              type: "file",
              src_url: file?.src_url || file?.srcUrl || file?.src || file?.url,
            },
          },
        })
      );
    } catch {
      // Ignore event transport failures.
    }
  }, [ext, file.id, file?.src, file?.srcUrl, file?.src_url, file?.url, fileName]);

  const handleDownload = React.useCallback(async () => {
    if (!canDownload) return;
    try {
      await downloadAsset({ url: downloadUrl, filename: fileName });
    } catch {
      notifyAssetActionError("download", "document");
    }
  }, [canDownload, downloadUrl, fileName]);

  const handleDelete = React.useCallback(async () => {
    if (!canDelete) return;
    if (typeof window !== "undefined") {
      const confirmed = window.confirm(`Delete "${fileName}"? This removes it from your asset views.`);
      if (!confirmed) return;
    }
    try {
      await deleteAsset({ kind: "document", id: file.id! });
      setIsDeleted(true);
      emitDeletedEvent();
      onDeleted?.(file);
    } catch {
      notifyAssetActionError("delete", "document");
    }
  }, [canDelete, emitDeletedEvent, file, file.id, fileName, onDeleted]);

  const contextMenuItems = React.useMemo(
    () => [
      ...(canDownload
        ? [{ label: "Download", onSelect: handleDownload }]
        : []),
      ...(canDelete
        ? [{ label: "Delete", onSelect: handleDelete, destructive: true }]
        : []),
    ],
    [canDelete, canDownload, handleDelete, handleDownload]
  );

  if (isDeleted) return null;

  const content = (
    <div className="relative flex h-full w-full flex-col" data-slot="document-tile">
      {file?.thumb ? (
        <>
          <img src={file.thumb} alt={fileName} className="absolute inset-0 h-full w-full object-cover" />
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-gradient-to-b from-black/5 via-transparent to-black/25"
          />
        </>
      ) : (
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            background: `linear-gradient(180deg, color-mix(in oklab, ${bannerColor} 14%, var(--panel-bg, #111827)) 0%, color-mix(in oklab, ${bannerColor} 5%, var(--panel-bg, #111827)) 100%)`,
          }}
        />
      )}
      <div className="relative flex min-h-0 flex-1 flex-col px-3 pt-3 pb-2">
        {status && (
          <div
            className="codexifyDocumentTileStatusWrap flex min-h-0 justify-center pb-2"
            data-slot="document-tile-status-wrap"
          >
            <span
              className="codexifyDocumentTileStatus inline-flex max-w-full items-center justify-center truncate rounded-full border px-2.5 py-1 text-[10px] font-semibold shadow-sm"
              data-slot="document-tile-status"
              title={statusLabel ?? undefined}
              style={{
                background: status.background,
                color: status.color,
                borderColor: status.border,
              }}
            >
              {statusLabel}
            </span>
          </div>
        )}
        <div
          className="codexifyDocumentTileBody flex min-h-0 flex-1 items-center justify-center"
          data-slot="document-tile-body"
        >
          <div
            className="flex h-12 w-12 items-center justify-center border"
            style={{
              borderRadius: "calc(var(--tile-radius) - 6px)",
              background: "color-mix(in oklab, var(--panel-bg, #111827) 80%, white 20%)",
              borderColor:
                "color-mix(in oklab, var(--panel-border, rgba(255,255,255,0.12)) 72%, transparent)",
            }}
          >
            <Icon className="h-7 w-7 shrink-0" style={{ color: bannerColor }} />
          </div>
        </div>
      </div>
      <div className="mt-auto">
        <div
          className="codexifyDocumentTileFooter flex min-h-[54px] flex-col items-center justify-center gap-1 px-3 py-2 text-center"
          data-slot="document-tile-footer"
          style={{ background: bannerColor, color: onColor }}
        >
          <div
            className="codexifyDocumentTileName max-w-full text-[11px] font-semibold leading-[1.1]"
            data-slot="document-tile-name"
            style={{ overflowWrap: "anywhere" }}
            title={fileName}
          >
            {baseName}
          </div>
          {extLabel && (
            <div
              className="codexifyDocumentTileExtension text-[10px] font-semibold uppercase tracking-[0.18em] opacity-90"
              data-slot="document-tile-extension"
            >
              .{extLabel}
            </div>
          )}
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
        contextMenuItems={contextMenuItems}
        contextMenuLabel={`${fileName} actions`}
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
      contextMenuItems={contextMenuItems}
      contextMenuLabel={`${fileName} actions`}
      style={{ padding: 0 }}
      aria-label={fileName}
    >
      {content}
    </TileShell>
  );
}

export { getExt };
