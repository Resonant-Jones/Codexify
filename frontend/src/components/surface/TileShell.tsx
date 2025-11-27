import React from "react";
import clsx from "clsx";

type TileShellProps<T extends React.ElementType = "div"> = {
  as?: T;
  background?: string;
  borderColor?: string;
  shadow?: string;
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
  className,
  style,
  children,
  ...rest
}: TileShellProps<T>) {
  const Component = (as || "div") as React.ElementType;

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
        ...style,
      }}
      {...rest}
    >
      {children}
    </Component>
  );
}

export default TileShell;
