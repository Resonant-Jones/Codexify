import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { normalizeWorkspaceMediaUrl, type WorkspaceImageRecord } from "../workspaceSelection";

export const WORKSPACE_IMAGE_ZOOM_MIN = 50;
export const WORKSPACE_IMAGE_ZOOM_MAX = 400;
export const WORKSPACE_IMAGE_ZOOM_STEP = 25;

export function clampWorkspaceImageZoom(zoom: number): number {
  return Math.min(WORKSPACE_IMAGE_ZOOM_MAX, Math.max(WORKSPACE_IMAGE_ZOOM_MIN, zoom));
}

type ZoomControlsProps = {
  zoom: number;
  onZoomChange: (zoom: number) => void;
  onExpand?: () => void;
  canExpand?: boolean;
  expandButtonRef?: React.Ref<HTMLButtonElement>;
};

export function WorkspaceImageZoomControls({
  zoom,
  onZoomChange,
  onExpand,
  canExpand = true,
  expandButtonRef,
}: ZoomControlsProps) {
  const buttonClassName =
    "inline-flex min-h-9 items-center justify-center rounded-md border px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-45";
  const buttonStyle = {
    borderColor: "var(--panel-border)",
    background: "var(--panel-bg)",
    color: "var(--text)",
  };

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2" aria-label="Image zoom controls">
      <button
        className={buttonClassName}
        style={buttonStyle}
        type="button"
        aria-label="Zoom out"
        disabled={zoom <= WORKSPACE_IMAGE_ZOOM_MIN}
        onClick={() => onZoomChange(clampWorkspaceImageZoom(zoom - WORKSPACE_IMAGE_ZOOM_STEP))}
      >
        Zoom out
      </button>
      <output
        className="min-w-12 text-center text-xs font-semibold tabular-nums"
        aria-live="polite"
        aria-label="Current zoom"
        data-testid="workspace-image-zoom"
        style={{ color: "var(--text)" }}
      >
        {zoom}%
      </output>
      <button
        className={buttonClassName}
        style={buttonStyle}
        type="button"
        aria-label="Zoom in"
        disabled={zoom >= WORKSPACE_IMAGE_ZOOM_MAX}
        onClick={() => onZoomChange(clampWorkspaceImageZoom(zoom + WORKSPACE_IMAGE_ZOOM_STEP))}
      >
        Zoom in
      </button>
      <button
        className={buttonClassName}
        style={buttonStyle}
        type="button"
        aria-label="Reset / Fit"
        disabled={zoom === 100}
        onClick={() => onZoomChange(100)}
      >
        Reset / Fit
      </button>
      {onExpand && (
        <button
          ref={expandButtonRef}
          className={buttonClassName}
          style={buttonStyle}
          type="button"
          aria-label="Expand image"
          disabled={!canExpand}
          onClick={onExpand}
        >
          Expand
        </button>
      )}
    </div>
  );
}

type ViewportSize = {
  width: number;
  height: number;
};

type NaturalSize = {
  width: number;
  height: number;
};

export function useWorkspaceImageSizing(zoom: number) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [viewportSize, setViewportSize] = useState<ViewportSize>({
    width: 0,
    height: 0,
  });
  const [naturalSize, setNaturalSize] = useState<NaturalSize | null>(null);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const measure = () => {
      const rect = viewport.getBoundingClientRect();
      setViewportSize((current) =>
        current.width === rect.width && current.height === rect.height
          ? current
          : { width: rect.width, height: rect.height }
      );
    };

    measure();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    observer?.observe(viewport);
    window.addEventListener("resize", measure);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  const fitScale =
    naturalSize && viewportSize.width > 0 && viewportSize.height > 0
      ? Math.min(
          1,
          viewportSize.width / naturalSize.width,
          viewportSize.height / naturalSize.height
        )
      : 1;
  const zoomScale = (clampWorkspaceImageZoom(zoom) / 100) * fitScale;
  const imageSize = naturalSize
    ? {
        width: Math.max(1, naturalSize.width * zoomScale),
        height: Math.max(1, naturalSize.height * zoomScale),
      }
    : null;

  const onImageLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
    const image = event.currentTarget;
    setNaturalSize({ width: image.naturalWidth, height: image.naturalHeight });
  };

  const canvasStyle: React.CSSProperties = {
    width: imageSize ? `${Math.max(viewportSize.width, imageSize.width)}px` : "100%",
    height: imageSize ? `${Math.max(viewportSize.height, imageSize.height)}px` : "100%",
    minWidth: "100%",
    minHeight: "100%",
    display: "grid",
    placeItems: "center",
  };

  const imageStyle: React.CSSProperties = imageSize
    ? {
        width: `${imageSize.width}px`,
        height: `${imageSize.height}px`,
        maxWidth: "none",
        maxHeight: "none",
        objectFit: "contain",
      }
    : { maxWidth: "100%", maxHeight: "100%", objectFit: "contain" };

  return { viewportRef, canvasStyle, imageStyle, onImageLoad };
}

type WorkspaceImageViewerModalProps = {
  image: WorkspaceImageRecord | null;
  zoom: number;
  onZoomChange: (zoom: number) => void;
  onClose: () => void;
  returnFocusRef?: React.RefObject<HTMLElement>;
};

export default function WorkspaceImageViewerModal({
  image,
  zoom,
  onZoomChange,
  onClose,
  returnFocusRef,
}: WorkspaceImageViewerModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const [expandedImageFailed, setExpandedImageFailed] = useState(false);
  const source = image ? normalizeWorkspaceMediaUrl(image.src_url) : null;
  const sizing = useWorkspaceImageSizing(zoom);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!image) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable?.length) {
        event.preventDefault();
        dialogRef.current?.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      const restoreTarget = returnFocusRef?.current ?? previousFocus;
      if (restoreTarget?.isConnected) restoreTarget.focus();
    };
  }, [image, returnFocusRef]);

  useEffect(() => {
    setExpandedImageFailed(false);
  }, [image?.id, image?.src_url]);

  if (!image || !source || typeof document === "undefined") return null;

  const name = image.caption || image.filename || image.title || "Image preview";
  const closeStyle = {
    borderColor: "var(--panel-border)",
    background: "var(--panel-bg)",
    color: "var(--text)",
  };

  return createPortal(
    <div
      className="fixed inset-0 flex items-center justify-center bg-black/85 p-3 sm:p-6"
      style={{ zIndex: 10000 }}
      data-testid="workspace-image-lightbox-backdrop"
    >
      <div
        ref={dialogRef}
        className="flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden rounded-lg border bg-[var(--panel-bg)] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-image-lightbox-title"
        tabIndex={-1}
        data-testid="workspace-image-lightbox"
        style={{ borderColor: "var(--panel-border)" }}
      >
        <header
          className="flex flex-none flex-wrap items-center justify-between gap-3 border-b p-3 sm:p-4"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <h2
            id="workspace-image-lightbox-title"
            className="min-w-0 flex-1 truncate text-sm font-semibold"
            style={{ color: "var(--text)" }}
          >
            {name}
          </h2>
          <WorkspaceImageZoomControls zoom={zoom} onZoomChange={onZoomChange} />
          <button
            ref={closeButtonRef}
            className="inline-flex min-h-9 shrink-0 items-center justify-center rounded-md border px-3 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            style={closeStyle}
            type="button"
            aria-label="Close image viewer"
            onClick={onClose}
          >
            Close
          </button>
        </header>

        <div
          ref={sizing.viewportRef}
          className="flex min-h-0 min-w-0 flex-1 overflow-auto bg-neutral-950"
          role="region"
          aria-label="Expanded image viewport"
          data-testid="workspace-image-lightbox-viewport"
        >
          <div style={sizing.canvasStyle}>
            {expandedImageFailed ? (
              <p className="p-6 text-sm text-white" role="alert">
                This image could not be loaded in the expanded viewer.
              </p>
            ) : (
              <img
                src={source}
                alt={name}
                draggable={false}
                onLoad={sizing.onImageLoad}
                onError={() => setExpandedImageFailed(true)}
                style={sizing.imageStyle}
              />
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
