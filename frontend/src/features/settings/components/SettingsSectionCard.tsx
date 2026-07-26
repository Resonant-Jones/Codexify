import type {
  CSSProperties,
  ComponentPropsWithoutRef,
  PropsWithChildren,
} from "react";

import { cn } from "@/lib/utils";

type SettingsSectionCardProps = PropsWithChildren<
  Omit<ComponentPropsWithoutRef<"section">, "children" | "className" | "style"> & {
    className?: string;
    "data-testid"?: string;
    style?: CSSProperties;
    variant?: "card" | "canvas";
  }
>;

export default function SettingsSectionCard({
  children,
  className,
  style,
  "data-testid": dataTestId,
  variant = "card",
  ...rest
}: SettingsSectionCardProps) {
  const isCanvas = variant === "canvas";

  return (
    <section
      data-testid={dataTestId}
      data-variant={variant}
      className={cn("space-y-4 rounded-[var(--tile-radius)] border", className)}
      style={{
        borderColor: isCanvas
          ? "transparent"
          : "color-mix(in srgb, var(--panel-border) 84%, transparent)",
        background: isCanvas
          ? "transparent"
          : "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
        padding: "calc(var(--card-pad) + var(--board-edge))",
        boxShadow: isCanvas
          ? "none"
          : "inset 0 1px 0 rgba(255,255,255,0.04), inset 0 -1px 0 rgba(0,0,0,0.12)",
        ...style,
      }}
      {...rest}
    >
      {children}
    </section>
  );
}
