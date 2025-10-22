export function StatusDot({ ok }: { ok: boolean }) {
  const color = ok ? "#10b981" : "#f59e0b"; // green / amber
  const title = ok ? "Connected" : "Reconnecting…";
  return (
    <span
      title={title}
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: 999,
        backgroundColor: color,
        boxShadow: `0 0 0 2px ${ok ? "rgba(16,185,129,.25)" : "rgba(245,158,11,.25)"}`,
      }}
    />
  );
}
