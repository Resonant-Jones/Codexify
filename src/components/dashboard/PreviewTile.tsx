// src/components/dashboard/PreviewTile.tsx
export function PreviewTile({ children, onClick, className = "" }) {
  return (
    <div
      onClick={onClick}
      className={`aspect-square rounded-[var(--tile-radius,1rem)] overflow-hidden border ${className}`}
      style={{ borderColor: "var(--panel-border)" }}
    >
      {children}
    </div>
  );
}