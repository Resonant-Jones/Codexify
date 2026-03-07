import React from "react";
import clsx from "clsx";
import { createPortal } from "react-dom";

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
  contextMenuItems?: Array<{
    label: string;
    onSelect: () => void | Promise<void>;
    destructive?: boolean;
  }>;
  contextMenuLabel?: string;
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
  contextMenuItems,
  contextMenuLabel,
  className,
  style,
  children,
  ...rest
}: TileShellProps<T>) {
  const Component = (as || "div") as React.ElementType;
  const onContextMenuProp = (rest as { onContextMenu?: (event: React.MouseEvent) => void }).onContextMenu;
  const [menuPosition, setMenuPosition] = React.useState<{ x: number; y: number } | null>(null);
  const menuRef = React.useRef<HTMLDivElement | null>(null);
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
  const actionableMenuItems = React.useMemo(
    () => (contextMenuItems ?? []).filter((item) => typeof item?.label === "string"),
    [contextMenuItems]
  );

  React.useEffect(() => {
    if (!menuPosition || typeof window === "undefined") return;

    const closeMenu = () => setMenuPosition(null);
    const handlePointerDown = (event: PointerEvent) => {
      if (menuRef.current?.contains(event.target as Node)) return;
      closeMenu();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
    };
  }, [menuPosition]);

  const handleContextMenu = React.useCallback(
    (event: React.MouseEvent) => {
      if (typeof onContextMenuProp === "function") {
        onContextMenuProp(event);
      }
      if (event.defaultPrevented || actionableMenuItems.length === 0) return;
      event.preventDefault();
      event.stopPropagation();
      setMenuPosition({ x: event.clientX, y: event.clientY });
    },
    [actionableMenuItems.length, onContextMenuProp]
  );

  return (
    <>
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
        onContextMenu={handleContextMenu}
      >
        {children}
      </Component>
      {menuPosition && typeof document !== "undefined"
        ? createPortal(
            <div
              ref={menuRef}
              role="menu"
              aria-label={contextMenuLabel ?? "Asset actions"}
              className="fixed z-[2000] min-w-[168px] overflow-hidden border"
              style={{
                left: menuPosition.x,
                top: menuPosition.y,
                background:
                  "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
                borderColor: "var(--panel-border)",
                borderRadius: "calc(var(--tile-radius) - 6px)",
                boxShadow:
                  "0 18px 42px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.08)",
                backdropFilter: "blur(18px)",
              }}
            >
              <div className="py-1">
                {actionableMenuItems.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    role="menuitem"
                    className="block w-full px-3 py-2 text-left text-sm transition-colors hover:bg-white/8"
                    style={{
                      color: item.destructive
                        ? "var(--danger, #ef4444)"
                        : "var(--text)",
                    }}
                    onClick={() => {
                      setMenuPosition(null);
                      void item.onSelect();
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>,
            document.body
          )
        : null}
    </>
  );
}

export default TileShell;
