import clsx from "clsx";

const STATUS_STYLES = {
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
} as const;

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

function resolveStatusPresentation(raw?: string, embeddingError?: string) {
  if (!raw) return null;
  const key = raw.trim().toLowerCase();
  if (!key) return null;

  const config = STATUS_STYLES[key as keyof typeof STATUS_STYLES];
  const baseLabel = config?.label ?? key.charAt(0).toUpperCase() + key.slice(1);
  const errorHint = key === "failed" ? resolveErrorHint(embeddingError) : null;
  const label = errorHint ? `${baseLabel} - ${errorHint}` : baseLabel;
  const title = label;

  return {
    label,
    title,
    background: config?.background ?? "#e5e7eb",
    color: config?.color ?? "#111827",
    border: config?.border ?? "rgba(15, 23, 42, 0.15)",
  };
}

export function DocumentEmbeddingStatusBadge({
  status,
  embeddingError,
  className,
}: {
  status?: string;
  embeddingError?: string;
  className?: string;
}) {
  const presentation = resolveStatusPresentation(status, embeddingError);
  if (!presentation) return null;

  return (
    <span
      className={clsx(
        "inline-flex max-w-full items-center justify-center truncate rounded-full border px-2.5 py-1 text-[10px] font-semibold shadow-sm",
        className
      )}
      data-slot="document-tile-status"
      title={presentation.title}
      style={{
        background: presentation.background,
        color: presentation.color,
        borderColor: presentation.border,
      }}
    >
      {presentation.label}
    </span>
  );
}
