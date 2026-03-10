import * as React from "react";
import { createPortal } from "react-dom";

export type ContextMenuItem = {
  label: string;
  onSelect: () => void | Promise<void>;
  destructive?: boolean;
  disabled?: boolean;
};

type ContextMenuProps = {
  open: boolean;
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
  ariaLabel?: string;
};

export function ContextMenu({
  open,
  x,
  y,
  items,
  onClose,
  ariaLabel = "Context menu",
}: ContextMenuProps) {
  React.useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onClose();
    };
    const onPointerDown = () => onClose();
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("resize", onClose);
    window.addEventListener("scroll", onClose, true);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("resize", onClose);
      window.removeEventListener("scroll", onClose, true);
    };
  }, [onClose, open]);

  if (!open || items.length === 0 || typeof document === "undefined") return null;

  return createPortal(
    <div
      role="menu"
      aria-label={ariaLabel}
      className="fixed z-[2000] min-w-[180px] overflow-hidden border py-1"
      style={{
        left: x,
        top: y,
        background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        borderColor: "var(--panel-border)",
        borderRadius: "calc(var(--tile-radius) - 6px)",
        boxShadow:
          "0 18px 42px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.08)",
        backdropFilter: "blur(18px)",
      }}
      onPointerDown={(event) => event.stopPropagation()}
    >
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          role="menuitem"
          disabled={item.disabled}
          className="block w-full px-3 py-2 text-left text-sm transition-colors hover:bg-white/8 disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            color: item.destructive ? "var(--danger, #ef4444)" : "var(--text)",
          }}
          onClick={() => {
            onClose();
            void item.onSelect();
          }}
        >
          {item.label}
        </button>
      ))}
    </div>,
    document.body
  );
}

export default ContextMenu;
