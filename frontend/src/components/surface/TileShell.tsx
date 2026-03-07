import React from "react";
import clsx from "clsx";

export type TileShellSizeVariant =
  | "document"
  | "dashboard-image"
  | "gallery-image";

const TILE_SIZE_BY_VARIANT: Record<TileShellSizeVariant, string> = {
  document: "127px",
  "dashboard-image": "192px",
  "gallery-image": "256px",
};

type TileShellProps<T extends React.ElementType = "div"> = {
  as?: T;
  background?: string;
  borderColor?: string;
  shadow?: string;
  sizeVariant?: TileShellSizeVariant;
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
} & Omit<React.ComponentPropsWithoutRef<T>, "as" | "children" | "className" | "style">;

/**
 * TileShell — shared outer surface for tiles (threads, docs, gallery, projects).
 * Keeps geometry/material tokens centralized via AppShell CSS variables.
 */
export function TileShell<T extends React.ElementType = "div">({
  as,
  background,
  borderColor,
  shadow,
  sizeVariant,
  className,
  style,
  children,
  ...rest
}: TileShellProps<T>) {
  const Component = (as || "div") as React.ElementType;
  const sizeStyles = sizeVariant
    ? ({
        "--tile-size": TILE_SIZE_BY_VARIANT[sizeVariant],
        width: "var(--tile-size)",
        height: "var(--tile-size)",
        minWidth: "var(--tile-size)",
        minHeight: "var(--tile-size)",
        flex: "0 0 var(--tile-size)",
      } as React.CSSProperties)
    : undefined;

  return (
    <Component
      className={clsx("rounded-[var(--tile-radius)] overflow-hidden", className)}
      style={{
        background: background ?? "var(--panel-bg)",
        border: `1px solid ${borderColor ?? "var(--panel-border)"}`,
        boxShadow:
          shadow ??
          "inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -10px 24px rgba(0,0,0,0.18), 0 6px 18px rgba(0,0,0,0.25)",
        borderRadius: "var(--tile-radius)",
        ...sizeStyles,
        ...style,
      }}
      {...rest}
    >
      {children}
    </Component>
  );
}

export default TileShell;
