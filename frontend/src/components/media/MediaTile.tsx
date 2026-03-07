/**
 * MediaTile.tsx
 *
 * Reusable media tile component for displaying images in a grid.
 * Used by both Dashboard and Gallery for consistent styling.
 */
import React from "react";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import "./media.css";

type MediaTileProps = {
  id: string;
  src: string;
  alt?: string;
  onOpen?: () => void;
};

export function MediaTile({ id, src, alt, onOpen }: MediaTileProps) {
  const resolvedSrc = React.useMemo(() => normalizeMediaUrl(src), [src]);
  const [hasLoadError, setHasLoadError] = React.useState(false);

  React.useEffect(() => {
    setHasLoadError(false);
  }, [resolvedSrc]);

  const showImage = !!resolvedSrc && !hasLoadError;

  return (
    <button
      type="button"
      className="codexifyMediaTile"
      onClick={onOpen}
      aria-label={alt ?? `Open media ${id}`}
    >
      {showImage ? (
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
      )}
    </button>
  );
}

export default MediaTile;
