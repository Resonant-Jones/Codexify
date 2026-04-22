import * as React from "react";
import ContextMenu, { type ContextMenuItem } from "@/components/menus/ContextMenu";
import MediaGrid from "@/components/media/MediaGrid";
import TileShell from "@/components/surface/TileShell";
import { useMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";
import {
  getMobilePressSurfaceStyle,
  getMobileTapTargetStyle,
} from "@/components/persona/layout/mobileInteractionContract";
import { useRenderableMediaSrc } from "@/hooks/useRenderableMediaSrc";
import { usePressFeedback } from "@/hooks/usePressFeedback";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import {
  getDashboardGalleryBadgeStyle,
  getDashboardGalleryTileActiveStyle,
} from "./galleryInteractionContract";
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
  activeItemSrc?: string | null;
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

function DashboardGalleryImageTile({
  item,
  alt,
  provenance,
  provenanceClass,
  activeItemSrc,
  isPhoneShell,
  onOpenPreview,
  onOpenContextMenu,
}: {
  item: DashboardGalleryItem;
  alt: string;
  provenance: string;
  provenanceClass: string;
  activeItemSrc?: string | null;
  isPhoneShell: boolean;
  onOpenPreview: (item: DashboardGalleryItem) => void;
  onOpenContextMenu: (event: React.MouseEvent<HTMLButtonElement>) => void;
}) {
  const pressFeedback = usePressFeedback({ enabled: isPhoneShell });
  const {
    className: pressFeedbackClassName,
    style: pressFeedbackStyle,
    ...pressFeedbackProps
  } = pressFeedback.getPressFeedbackProps({
    className: "dashboardGalleryTilePressSurface",
  });
  const renderableSrc = useRenderableMediaSrc(item.src);
  const [hasLoadError, setHasLoadError] = React.useState(false);
  const normalizedSrc = React.useMemo(() => normalizeMediaUrl(item.src), [item.src]);

  React.useEffect(() => {
    setHasLoadError(false);
  }, [renderableSrc.src]);

  const showImage =
    renderableSrc.status === "ready" &&
    !!renderableSrc.src &&
    !hasLoadError;
  const isActiveItem = Boolean(
    isPhoneShell && activeItemSrc && normalizedSrc === activeItemSrc
  );

  const handleOpenPreview = React.useCallback(() => {
    pressFeedback.releasePressed();
    onOpenPreview(item);
  }, [item, onOpenPreview, pressFeedback]);

  const handleContextMenu = React.useCallback(
    (event: React.MouseEvent<HTMLButtonElement>) => {
      pressFeedback.releasePressed();
      onOpenContextMenu(event);
    },
    [onOpenContextMenu, pressFeedback]
  );

  return (
    <TileShell
      as="button"
      type="button"
      sizeVariant={isPhoneShell ? undefined : "dashboard-image"}
      className={`${pressFeedbackClassName ?? ""} codexifyMediaTile dashboardGalleryTile cursor-pointer ${
        isPhoneShell ? "dashboardGalleryTile--mobile" : ""
      }`.trim()}
      style={{
        ...pressFeedbackStyle,
        padding: 0,
        ...(isPhoneShell
          ? {
              width: "100%",
              minWidth: 0,
              height: "auto",
              aspectRatio: "4 / 3",
              flex: "0 0 auto",
            }
          : {}),
        ...getMobileTapTargetStyle(isPhoneShell),
        ...getMobilePressSurfaceStyle(
          isPhoneShell,
          pressFeedback.prefersReducedMotion
        ),
        ...getDashboardGalleryTileActiveStyle(isPhoneShell, isActiveItem),
      }}
      {...pressFeedbackProps}
      data-state={isActiveItem ? "active" : undefined}
      onClick={handleOpenPreview}
      onContextMenu={handleContextMenu}
      aria-label={alt}
    >
      {showImage ? (
        <img
          className="codexifyMediaTileMedia"
          src={renderableSrc.src}
          alt={alt}
          loading="lazy"
          onError={() => setHasLoadError(true)}
        />
      ) : (
        <div className="codexifyMediaTileFallback" aria-hidden="true">
          <span className="codexifyMediaTileFallbackLabel">
            {renderableSrc.status === "loading" ? "Loading image" : "Image unavailable"}
          </span>
        </div>
      )}
      <span
        className={`dashboardGalleryBadge ${provenanceClass}`}
        aria-hidden="true"
        style={getDashboardGalleryBadgeStyle(
          provenance === "Generated" ? "generated" : "uploaded"
        )}
      >
        {provenance}
      </span>
    </TileShell>
  );
}

export default function DashboardGallery({
  items,
  onOpenPreview,
  onAddToThread,
  activeItemSrc,
}: DashboardGalleryProps) {
  const mobileShellProfile = useMobileShellProfile();
  const isPhoneShell = mobileShellProfile.active;
  const [menu, setMenu] = React.useState<{
    x: number;
    y: number;
    item: DashboardGalleryItem;
    resolvedSrc: string;
    alt: string;
  } | null>(null);

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
    <div
      className="dashboardGalleryRoot"
      style={{ gap: "var(--shell-gap)" }}
      data-gallery-layout={isPhoneShell ? "mobile_stack" : "desktop_grid"}
      data-testid="dashboard-gallery"
    >
      {isPhoneShell ? (
        <div className="flex flex-col gap-[var(--shell-gap)]">
          {items.map((item, index) => {
            const resolvedSrc = normalizeMediaUrl(item.src);
            const alt = item.prompt || "Gallery image";
            const key = `${item.id ?? "dashboard"}:${item.src}:${index}`;
            const provenance = provenanceLabel(item);
            const provenanceClass =
              provenance === "Generated"
                ? "dashboardGalleryBadge--generated"
                : "dashboardGalleryBadge--uploaded";
            return (
              <DashboardGalleryImageTile
                key={key}
                item={item}
                alt={alt}
                provenance={provenance}
                provenanceClass={provenanceClass}
                activeItemSrc={activeItemSrc}
                isPhoneShell={isPhoneShell}
                onOpenPreview={onOpenPreview}
                onOpenContextMenu={(event) => {
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
              />
            );
          })}
        </div>
      ) : (
        <MediaGrid className="codexifyMediaGrid--dashboard-image">
          {items.map((item, index) => {
            const resolvedSrc = normalizeMediaUrl(item.src);
            const alt = item.prompt || "Gallery image";
            const key = `${item.id ?? "dashboard"}:${item.src}:${index}`;
            const provenance = provenanceLabel(item);
            const provenanceClass =
              provenance === "Generated"
                ? "dashboardGalleryBadge--generated"
                : "dashboardGalleryBadge--uploaded";
            return (
              <DashboardGalleryImageTile
                key={key}
                item={item}
                alt={alt}
                provenance={provenance}
                provenanceClass={provenanceClass}
                activeItemSrc={activeItemSrc}
                isPhoneShell={isPhoneShell}
                onOpenPreview={onOpenPreview}
                onOpenContextMenu={(event) => {
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
              />
            );
          })}
        </MediaGrid>
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
