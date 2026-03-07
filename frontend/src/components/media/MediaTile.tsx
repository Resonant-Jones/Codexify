/**
 * MediaTile.tsx
 *
 * Reusable media tile component for displaying images in a grid.
 * Used by both Dashboard and Gallery for consistent styling.
 */
import React from "react";
import {
  deleteAsset,
  downloadAsset,
  notifyAssetActionError,
} from "@/lib/assetActions";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import TileShell, { type TileShellSizeVariant } from "@/components/surface/TileShell";
import "./media.css";

type MediaTileProps = {
  id: string;
  assetId?: string;
  src: string;
  alt?: string;
  onOpen?: () => void;
  onDeleted?: () => void;
  sizeVariant?: TileShellSizeVariant;
};

export function MediaTile({
  id,
  assetId,
  src,
  alt,
  onOpen,
  onDeleted,
  sizeVariant = "gallery-image",
}: MediaTileProps) {
  const resolvedSrc = React.useMemo(() => normalizeMediaUrl(src), [src]);
  const [hasLoadError, setHasLoadError] = React.useState(false);
  const [isDeleted, setIsDeleted] = React.useState(false);

  React.useEffect(() => {
    setHasLoadError(false);
  }, [resolvedSrc]);

  const canDownload = !!resolvedSrc;
  const canDelete = typeof assetId === "string" && assetId.trim().length > 0;

  const handleDownload = React.useCallback(async () => {
    if (!canDownload) return;
    try {
      await downloadAsset({ url: resolvedSrc, filename: alt || `${id}.png` });
    } catch {
      notifyAssetActionError("download", "image");
    }
  }, [alt, canDownload, id, resolvedSrc]);

  const handleDelete = React.useCallback(async () => {
    if (!canDelete) return;
    if (typeof window !== "undefined") {
      const confirmed = window.confirm(`Delete "${alt || "image"}"? This removes it from your asset views.`);
      if (!confirmed) return;
    }
    try {
      await deleteAsset({ kind: "image", id: assetId! });
      setIsDeleted(true);
      onDeleted?.();
    } catch {
      notifyAssetActionError("delete", "image");
    }
  }, [alt, assetId, canDelete, onDeleted]);

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

  const showImage = !!resolvedSrc && !hasLoadError;
  const content = showImage ? (
    <img
      className="codexifyMediaTileMedia"
      src={resolvedSrc}
      alt={alt ?? ""}
      loading="lazy"
      onError={() => setHasLoadError(true)}
    />
  ) : (
    <div className="codexifyMediaTileFallback" aria-hidden="true">
      <span className="codexifyMediaTileFallbackLabel">Image unavailable</span>
    </div>
  );

  if (onOpen) {
    return (
      <TileShell
        as="button"
        type="button"
        sizeVariant={sizeVariant}
        className="codexifyMediaTile"
        contextMenuItems={contextMenuItems}
        contextMenuLabel={`${alt ?? `Media ${id}`} actions`}
        onClick={onOpen}
        aria-label={alt ?? `Open media ${id}`}
        style={{ padding: 0 }}
      >
        {content}
      </TileShell>
    );
  }

  return (
    <TileShell
      sizeVariant={sizeVariant}
      className="codexifyMediaTile"
      contextMenuItems={contextMenuItems}
      contextMenuLabel={`${alt ?? `Media ${id}`} actions`}
      aria-label={alt ?? `Open media ${id}`}
      style={{ padding: 0 }}
    >
      {content}
    </TileShell>
  );
}

export default MediaTile;
