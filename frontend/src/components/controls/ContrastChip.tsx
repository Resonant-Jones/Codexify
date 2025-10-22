export function ContrastChip({ label, ratio }: { label: string; ratio: number }) {
  const status = ratio >= 7 ? "AAA" : ratio >= 4.5 ? "AA" : "Fail";
  const color = ratio >= 7 ? "#16a34a" : ratio >= 4.5 ? "#f59e0b" : "#ef4444";
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full align-middle"
      style={{ border: "1px solid var(--panel-border)", padding: "1px 4px", lineHeight: 1 }}
      title={`${label}: ${ratio.toFixed(2)}:1 • ${status}`}
      aria-label={`${label} contrast ${ratio.toFixed(2)} to 1, ${status}`}
    >
      <span style={{ width: 5, height: 5, background: color, borderRadius: 9999, display: "inline-block" }} />
      <span className="text-[9px]" style={{ color: "var(--text)" }}>
        {ratio.toFixed(1)}:1
      </span>
    </span>
  );
}

export default ContrastChip;

