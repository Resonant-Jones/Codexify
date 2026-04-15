import type { CSSProperties } from "react";

export type DashboardGalleryBadgeVariant = "uploaded" | "generated";

const DASHBOARD_GALLERY_BADGE = {
  inset: "calc(var(--card-pad) / 2)",
  paddingY: "calc(var(--card-pad) / 6)",
  paddingX: "calc(var(--card-pad) / 2)",
  radius: "999px",
  border: "color-mix(in oklab, var(--panel-border) 85%, transparent)",
  backdropFilter: "blur(8px)",
  uploadedBackground: "color-mix(in oklab, var(--panel-bg) 75%, transparent)",
  uploadedForeground: "color-mix(in oklab, var(--text) 88%, transparent)",
  generatedBackground: "color-mix(in oklab, var(--accent-strong, #3b82f6) 25%, transparent)",
  generatedBorder: "color-mix(in oklab, var(--accent-strong, #3b82f6) 45%, var(--panel-border))",
  generatedForeground: "color-mix(in oklab, var(--text, #f8fafc) 92%, transparent)",
} as const;

const DASHBOARD_GALLERY_ACTIVE_TILE = {
  background: "color-mix(in oklab, var(--accent-weak) 16%, var(--panel-bg) 84%)",
  borderColor: "color-mix(in oklab, var(--accent-strong) 34%, var(--panel-border))",
  boxShadow:
    "0 0 0 1px color-mix(in oklab, var(--accent-strong) 24%, transparent), 0 12px 24px color-mix(in oklab, var(--panel-border) 18%, transparent)",
} as const;

export function getDashboardGalleryBadgeStyle(
  variant: DashboardGalleryBadgeVariant
): CSSProperties {
  return {
    right: DASHBOARD_GALLERY_BADGE.inset,
    bottom: DASHBOARD_GALLERY_BADGE.inset,
    borderRadius: DASHBOARD_GALLERY_BADGE.radius,
    padding: `${DASHBOARD_GALLERY_BADGE.paddingY} ${DASHBOARD_GALLERY_BADGE.paddingX}`,
    borderColor:
      variant === "generated"
        ? DASHBOARD_GALLERY_BADGE.generatedBorder
        : DASHBOARD_GALLERY_BADGE.border,
    background:
      variant === "generated"
        ? DASHBOARD_GALLERY_BADGE.generatedBackground
        : DASHBOARD_GALLERY_BADGE.uploadedBackground,
    color:
      variant === "generated"
        ? DASHBOARD_GALLERY_BADGE.generatedForeground
        : DASHBOARD_GALLERY_BADGE.uploadedForeground,
    backdropFilter: DASHBOARD_GALLERY_BADGE.backdropFilter,
  };
}

export function getDashboardGalleryTileActiveStyle(
  isPhoneShell: boolean,
  isActive: boolean
): CSSProperties {
  if (!isPhoneShell || !isActive) {
    return {};
  }

  return {
    background: DASHBOARD_GALLERY_ACTIVE_TILE.background,
    borderColor: DASHBOARD_GALLERY_ACTIVE_TILE.borderColor,
    boxShadow: DASHBOARD_GALLERY_ACTIVE_TILE.boxShadow,
  };
}
