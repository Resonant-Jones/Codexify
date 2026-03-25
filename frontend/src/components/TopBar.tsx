import { useEventStream } from "../hooks/useEventStream";
import { StatusDot } from "./StatusDot";

export function TopBar() {
  const { connected } = useEventStream(); // passive consumer just for status
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 14px",
        borderBottom: "1px solid var(--panel-border)",
        position: "sticky",
        top: 0,
        background: "color-mix(in oklab, var(--panel-bg) 88%, transparent)",
        color: "var(--text)",
        backdropFilter: "saturate(150%) blur(8px)",
        zIndex: 100,
      }}
    >
      {/* “menu pill dock” vibe: hex + wordmark can drop in later */}
      <div style={{ fontWeight: 700, letterSpacing: "-.02em" }}>Codexify</div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
        <StatusDot ok={connected} />
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          {connected ? "Live" : "Reconnecting…"}
        </span>
      </div>
    </header>
  );
}
