/**
 * MediaTile.tsx
 *
 * Reusable media tile component for displaying images in a grid.
 * Used by both Dashboard and Gallery for consistent styling.
 */
import React from "react";
import "./media.css";

type MediaTileProps = {
  id: string;
  src: string;
  alt?: string;
  onOpen?: () => void;
};

export function MediaTile({ id, src, alt, onOpen }: MediaTileProps) {
  return (
    <button
      type="button"
      className="codexifyMediaTile"
      onClick={onOpen}
      aria-label={alt ?? `Open media ${id}`}
    >
      <img
        className="codexifyMediaTileMedia"
        src={src}
        alt={alt ?? ""}
        loading="lazy"
      />
    </button>
  );
}

export default MediaTile;
