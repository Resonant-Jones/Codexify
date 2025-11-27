import React from "react";

export type MenuItem = { label: string; onClick: () => void };

export function ContextMenu({ x, y, items, onClose }: { x: number; y: number; items: MenuItem[]; onClose: () => void }) {
  React.useEffect(() => {
    const close = () => onClose();
    window.addEventListener("click", close);
    window.addEventListener("contextmenu", close);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("contextmenu", close);
    };
  }, [onClose]);
  return (
    <div
      className="fixed z-[1600] min-w-[160px] rounded-lg border shadow-lg"
      style={{ left: x, top: y, background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
      role="menu"
    >
      <ul className="py-1">
        {items.map((it, idx) => (
          <li key={idx}>
            <button
              type="button"
              className="w-full text-left px-3 py-1.5 hover:bg-white/5"
              onClick={() => { it.onClick(); onClose(); }}
              role="menuitem"
            >
              {it.label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ContextMenu;
