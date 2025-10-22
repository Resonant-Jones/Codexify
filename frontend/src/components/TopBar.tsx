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
        borderBottom: "1px solid rgba(0,0,0,.08)",
        position: "sticky",
        top: 0,
        background: "rgba(255,255,255,.85)",
        backdropFilter: "saturate(150%) blur(8px)",
        zIndex: 100,
      }}
    >
      {/* “menu pill dock” vibe: hex + wordmark can drop in later */}
      <div style={{ fontWeight: 700, letterSpacing: "-.02em" }}>Codexify</div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
        <StatusDot ok={connected} />
        <span style={{ fontSize: 13, color: "rgba(0,0,0,.6)" }}>
          {connected ? "Live" : "Reconnecting…"}
        </span>
      </div>
    </header>
  );
}
