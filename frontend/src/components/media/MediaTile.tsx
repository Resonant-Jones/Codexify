/**
 * MediaTile.tsx
 *
 * Reusable media tile component for displaying images in a grid.
 * Used by both Dashboard and Gallery for consistent styling.
 */
import React from "react";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import TileShell, { type TileShellSizeVariant } from "@/components/surface/TileShell";
import "./media.css";

type MediaTileProps = {
  id: string;
  src: string;
  alt?: string;
  onOpen?: () => void;
  sizeVariant?: TileShellSizeVariant;
};

export function MediaTile({
  id,
  src,
  alt,
  onOpen,
  sizeVariant = "gallery-image",
}: MediaTileProps) {
  const resolvedSrc = React.useMemo(() => normalizeMediaUrl(src), [src]);
  const [hasLoadError, setHasLoadError] = React.useState(false);

  React.useEffect(() => {
    setHasLoadError(false);
  }, [resolvedSrc]);

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
      aria-label={alt ?? `Open media ${id}`}
      style={{ padding: 0 }}
    >
      {content}
    </TileShell>
  );
}

export default MediaTile;
