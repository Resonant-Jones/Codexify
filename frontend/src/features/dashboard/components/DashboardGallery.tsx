import * as React from "react";
import ContextMenu, { type ContextMenuItem } from "@/components/menus/ContextMenu";
import MediaGrid from "@/components/media/MediaGrid";
import TileShell from "@/components/surface/TileShell";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import "@/components/media/media.css";
import "./DashboardGallery.css";

export type DashboardGalleryItem = {
  id?: string;
  src: string;
  prompt?: string;
  tag?: string;
  source_tag?: string;
  source?: string;
  mock?: boolean;
};

type DashboardGalleryProps = {
  items: DashboardGalleryItem[];
  onOpenPreview: (item: DashboardGalleryItem) => void;
  onAddToThread?: (item: DashboardGalleryItem) => void;
};

function emitToast(message: string): void {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message } }));
  } catch {
    // Ignore toast transport failures.
  }
}

function deriveFilename(item: DashboardGalleryItem, fallback = "image"): string {
  const promptPart = String(item.prompt || "").trim().replace(/[^a-z0-9-_]+/gi, "-");
  const idPart = String(item.id || "").trim().replace(/[^a-z0-9-_]+/gi, "-");
  const base = promptPart || idPart || fallback;
  return `${base}.png`;
}

function triggerDownload(url: string, filename: string): void {
  if (typeof window === "undefined") return;
  try {
    const parsed = new URL(url, window.location.href);
    const isCrossOrigin = parsed.origin !== window.location.origin;
    if (isCrossOrigin) {
      window.open(parsed.toString(), "_blank", "noopener,noreferrer");
      return;
    }
    const anchor = document.createElement("a");
    anchor.href = parsed.toString();
    anchor.download = filename;
    anchor.rel = "noopener noreferrer";
    anchor.target = "_blank";
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  } catch {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export default function DashboardGallery({
  items,
  onOpenPreview,
  onAddToThread,
}: DashboardGalleryProps) {
  const INITIAL_VISIBLE = 4;
  const [menu, setMenu] = React.useState<{
    x: number;
    y: number;
    item: DashboardGalleryItem;
    resolvedSrc: string;
    alt: string;
  } | null>(null);
  const [showAll, setShowAll] = React.useState(false);

  const hasOverflow = items.length > INITIAL_VISIBLE;
  const visibleItems = showAll ? items : items.slice(0, INITIAL_VISIBLE);

  React.useEffect(() => {
    if (items.length <= INITIAL_VISIBLE) {
      setShowAll(false);
    }
  }, [items.length]);

  const provenanceLabel = React.useCallback(
    (item: DashboardGalleryItem): "Uploaded" | "Generated" => {
      const source = String(
        item?.source_tag ?? item?.tag ?? item?.source ?? ""
      )
        .trim()
        .toLowerCase();
      if (source.includes("gen")) return "Generated";
      if (source.includes("upload")) return "Uploaded";
      // In current data flow generated images are explicitly tagged; untagged defaults to uploaded.
      return "Uploaded";
    },
    []
  );

  const handleCopyLink = React.useCallback(async (url: string) => {
    if (typeof navigator?.clipboard?.writeText === "function") {
      try {
        await navigator.clipboard.writeText(url);
        emitToast("Image link copied");
        return;
      } catch {
        // Fall through to no-op toast below.
      }
    }
    emitToast("Unable to copy link");
  }, []);

  const buildMenuItems = React.useCallback(
    (entry: NonNullable<typeof menu>): ContextMenuItem[] => {
      const items: ContextMenuItem[] = [
        {
          label: "Add to Thread",
          onSelect: () => {
            if (onAddToThread) {
              onAddToThread(entry.item);
              return;
            }
            // TODO: Hook into a dedicated image->thread attachment flow when available.
            emitToast("Add to Thread is not yet available in this view");
          },
        },
        {
          label: "Download",
          onSelect: () => {
            triggerDownload(
              entry.resolvedSrc,
              deriveFilename(entry.item, "dashboard-image")
            );
          },
        },
      ];

      if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
        items.push({
          label: "Share",
          onSelect: async () => {
            try {
              await navigator.share({
                title: entry.alt,
                text: entry.alt,
                url: entry.resolvedSrc,
              });
            } catch {
              // Ignore cancelled shares.
            }
          },
        });
      } else {
        items.push({
          label: "Copy link",
          onSelect: async () => {
            await handleCopyLink(entry.resolvedSrc);
          },
        });
      }

      return items;
    },
    [handleCopyLink, onAddToThread]
  );

  return (
    <div className="dashboardGalleryRoot">
      <MediaGrid className="codexifyMediaGrid--dashboard-image">
        {visibleItems.map((item, index) => {
          const resolvedSrc = normalizeMediaUrl(item.src);
          const alt = item.prompt || "Gallery image";
          const key = `${item.id ?? "dashboard"}:${item.src}:${index}`;
          const provenance = provenanceLabel(item);
          const provenanceClass =
            provenance === "Generated"
              ? "dashboardGalleryBadge--generated"
              : "dashboardGalleryBadge--uploaded";
          return (
            <TileShell
              key={key}
              as="button"
              type="button"
              sizeVariant="dashboard-image"
              className="codexifyMediaTile dashboardGalleryTile cursor-pointer"
              style={{ padding: 0 }}
              onClick={() => onOpenPreview(item)}
              onContextMenu={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setMenu({
                  x: event.clientX,
                  y: event.clientY,
                  item,
                  resolvedSrc,
                  alt,
                });
              }}
              aria-label={alt}
            >
              <img
                className="codexifyMediaTileMedia"
                src={resolvedSrc}
                alt={alt}
                loading="lazy"
              />
              <span
                className={`dashboardGalleryBadge ${provenanceClass}`}
                aria-hidden="true"
              >
                {provenance}
              </span>
            </TileShell>
          );
        })}
      </MediaGrid>
      {hasOverflow && (
        <button
          type="button"
          className="dashboardGalleryShowMore"
          onClick={() => setShowAll((prev) => !prev)}
        >
          {showAll
            ? "Show fewer images"
            : `Show ${items.length - INITIAL_VISIBLE} more image${
                items.length - INITIAL_VISIBLE === 1 ? "" : "s"
              }`}
        </button>
      )}
      <ContextMenu
        open={!!menu}
        x={menu?.x ?? 0}
        y={menu?.y ?? 0}
        items={menu ? buildMenuItems(menu) : []}
        onClose={() => setMenu(null)}
        ariaLabel="Dashboard image actions"
      />
    </div>
  );
}
