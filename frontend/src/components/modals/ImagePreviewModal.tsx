import * as React from "react";
import { useRenderableMediaSrc } from "@/hooks/useRenderableMediaSrc";

type ImagePreviewModalProps = {
  open: boolean;
  src?: string;
  alt?: string;
  onOpenChange: (open: boolean) => void;
};

export function ImagePreviewModal({
  open,
  src,
  alt = "Preview image",
  onOpenChange,
}: ImagePreviewModalProps) {
  const renderableSrc = useRenderableMediaSrc(src);
  const [hasLoadError, setHasLoadError] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onOpenChange(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpenChange, open]);

  React.useEffect(() => {
    setHasLoadError(false);
  }, [renderableSrc.src]);

  if (!open || !src) return null;

  return (
    <div
      className="fixed inset-0 z-[1400] flex items-center justify-center p-4"
      onClick={() => onOpenChange(false)}
      aria-hidden={false}
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={alt}
        className="relative z-[1401] w-full max-w-[92vw] max-h-[92vh] overflow-hidden border"
        style={{
          borderColor: "var(--panel-border)",
          borderRadius: "var(--tile-radius)",
          boxShadow:
            "var(--panel-elevated-shadow, 0 18px 42px rgba(0,0,0,0.28), 0 8px 20px rgba(0,0,0,0.18))",
          background: "color-mix(in oklab, var(--panel-bg) 92%, transparent)",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-3 py-2" style={{ borderColor: "var(--panel-border)" }}>
          <div className="truncate text-xs opacity-75">{alt}</div>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-[var(--tile-radius)] px-2 py-1 text-xs opacity-75 hover:opacity-100"
            aria-label="Close image preview"
          >
            Close
          </button>
        </div>
        <div className="flex max-h-[calc(92vh-44px)] items-center justify-center p-3">
          {renderableSrc.status === "ready" &&
          !!renderableSrc.src &&
          !hasLoadError ? (
            <img
              src={renderableSrc.src}
              alt={alt}
              className="max-h-[calc(92vh-68px)] w-auto max-w-full object-contain"
              onError={() => setHasLoadError(true)}
            />
          ) : (
            <div className="flex min-h-[200px] w-full items-center justify-center text-sm opacity-75">
              {renderableSrc.status === "loading" ? "Loading image" : "Image unavailable"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImagePreviewModal;
