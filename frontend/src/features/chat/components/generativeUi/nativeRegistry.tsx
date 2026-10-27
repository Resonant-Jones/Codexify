/**
 * Registered native generative UI components.
 *
 * Only components listed here may render as first-party Codexify code. An
 * artifact naming any other component id is not resolved dynamically; it
 * degrades to ordinary assistant text.
 *
 * Registered components are trusted and run in the host React tree, so their
 * props are treated as untrusted input and normalized before render.
 *
 * Contract: docs/architecture/generative-ui-contract.md
 */
import React from "react";

export type NativeUiComponentProps = Record<string, unknown>;

export type NativeUiComponent = React.ComponentType<NativeUiComponentProps>;

export type NativeUiEntry = {
  component: NativeUiComponent;
  /** Container styling shared by every registered component. */
  className: string;
};

// The OpenUI parser and runtime are only needed when a valid native artifact
// selects this component. Do not charge ordinary chat for its initial bundle.
const LazyOpenUiNative = React.lazy(async () => {
  const { OpenUiNative } = await import("./openuiNative");
  return { default: OpenUiNative };
});

const OpenUiNativeEntry: NativeUiComponent = (props) => (
  <React.Suspense fallback={null}>
    <LazyOpenUiNative {...props} />
  </React.Suspense>
);

const PANEL_STYLE: React.CSSProperties = {
  border: "1px solid color-mix(in srgb, var(--panel-border, rgba(127,127,127,0.35)) 80%, transparent)",
  borderRadius: "0.75rem",
  background: "color-mix(in srgb, var(--panel-sheet, var(--panel-bg, #fff)) 92%, transparent)",
  color: "var(--text)",
  padding: "0.875rem",
  maxWidth: "100%",
  overflow: "hidden",
};

const TITLE_STYLE: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 600,
  marginBottom: "0.625rem",
  color: "var(--text)",
  overflowWrap: "anywhere",
};

function str(value: unknown, max = 120): string {
  return typeof value === "string" ? value.slice(0, max) : "";
}

function num(value: unknown, fallback: number): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function titleOf(props: NativeUiComponentProps): React.ReactNode {
  const title = str(props.title, 200);
  if (!title) return null;
  return <div style={TITLE_STYLE}>{title}</div>;
}

type BarDatum = { label: string; value: number };

function readSeries(props: NativeUiComponentProps): BarDatum[] {
  const raw = Array.isArray(props.series) ? props.series : [];
  return raw
    .slice(0, 24)
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const row = entry as Record<string, unknown>;
      const label = str(row.label, 60);
      const value = num(row.value, Number.NaN);
      if (!label || !Number.isFinite(value)) return null;
      return { label, value };
    })
    .filter((entry): entry is BarDatum => entry !== null);
}

function formatValue(value: number, format: string): string {
  if (format === "percent") return `${Number.isInteger(value) ? value : value.toFixed(1)}%`;
  if (format === "currency") {
    return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  }
  if (format === "compact") {
    return value.toLocaleString("en-US", { notation: "compact", maximumFractionDigits: 1 });
  }
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

const PALETTE = ["#4f7cff", "#22a06b", "#d97706", "#9333ea", "#dc2626", "#0891b2"];

/**
 * `chart.bar` — a structured bar visualization.
 *
 * Renders inline SVG with no third-party charting dependency, so it stays
 * inside the trusted host tree and needs no iframe.
 */
const BarChart: React.FC<NativeUiComponentProps> = (props) => {
  const series = readSeries(props);
  const height = Math.min(Math.max(num(props.height, 180), 80), 480);
  const valueFormat = str(props.valueFormat, 20) || "number";

  if (!series.length) {
    return (
      <div style={PANEL_STYLE} data-testid="generative-ui-native-chart-empty">
        {titleOf(props)}
        <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>No chartable data.</div>
      </div>
    );
  }

  const maxAbs = series.reduce((acc, item) => Math.max(acc, Math.abs(item.value)), 0);
  const hasNegative = series.some((item) => item.value < 0);
  const plotHeight = height - 26;
  const zeroY = hasNegative ? plotHeight / 2 : plotHeight;
  const scale = maxAbs === 0 ? 0 : (hasNegative ? zeroY : plotHeight) / maxAbs;

  return (
    <div style={PANEL_STYLE} data-testid="generative-ui-native-bar-chart">
      {titleOf(props)}
      <svg
        role="img"
        aria-label={str(props.title, 200) || "Bar chart"}
        viewBox={`0 0 320 ${height}`}
        width="100%"
        height={height}
        preserveAspectRatio="xMidYMid meet"
        style={{ display: "block", maxWidth: "100%" }}
      >
        {hasNegative ? (
          <line x1="0" y1={zeroY} x2="320" y2={zeroY} stroke="currentColor" strokeOpacity="0.18" strokeWidth="1" />
        ) : null}
        {series.map((item, index) => {
          const barHeight = Math.max(Math.abs(item.value) * scale, 1);
          const slot = 320 / series.length;
          const width = Math.max(slot * 0.62, 4);
          const x = index * slot + (slot - width) / 2;
          const y = item.value >= 0 ? zeroY - barHeight : zeroY;
          return (
            <g key={`${item.label}-${index}`}>
              <rect
                x={x}
                y={y}
                width={width}
                height={barHeight}
                rx="3"
                fill={PALETTE[index % PALETTE.length]}
              >
                <title>{`${item.label}: ${formatValue(item.value, valueFormat)}`}</title>
              </rect>
              <text
                x={index * slot + slot / 2}
                y={height - 8}
                textAnchor="middle"
                fontSize="9"
                fill="currentColor"
                fillOpacity="0.6"
              >
                {item.label.length > 12 ? `${item.label.slice(0, 11)}…` : item.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ul style={{ listStyle: "none", margin: "0.5rem 0 0", padding: 0, display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
        {series.map((item, index) => (
          <li
            key={`legend-${item.label}-${index}`}
            style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.7rem", color: "var(--muted)" }}
          >
            <span
              aria-hidden="true"
              style={{ width: 8, height: 8, borderRadius: 2, background: PALETTE[index % PALETTE.length] }}
            />
            {item.label}: {formatValue(item.value, valueFormat)}
          </li>
        ))}
      </ul>
    </div>
  );
};

type TableRow = Record<string, string>;

function readTable(props: NativeUiComponentProps): { columns: string[]; rows: TableRow[] } {
  const rawColumns = Array.isArray(props.columns) ? props.columns : [];
  const columns = rawColumns
    .slice(0, 8)
    .map((entry) => {
      if (typeof entry === "string") return entry.slice(0, 60);
      if (entry && typeof entry === "object") return str((entry as Record<string, unknown>).key, 60);
      return "";
    })
    .filter(Boolean);
  const rawRows = Array.isArray(props.rows) ? props.rows : [];
  const rows = rawRows
    .slice(0, 50)
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const out: TableRow = {};
      for (const [key, value] of Object.entries(entry as Record<string, unknown>)) {
        if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
          out[key] = String(value).slice(0, 200);
        }
      }
      return out;
    })
    .filter((entry): entry is TableRow => entry !== null);
  return { columns, rows };
}

/** `table.rows` — a structured data table. */
const DataTable: React.FC<NativeUiComponentProps> = (props) => {
  const { columns, rows } = readTable(props);
  return (
    <div style={PANEL_STYLE} data-testid="generative-ui-native-table">
      {titleOf(props)}
      {columns.length && rows.length ? (
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.75rem" }}>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    scope="col"
                    style={{
                      textAlign: "left",
                      padding: "0.3rem 0.5rem",
                      borderBottom: "1px solid color-mix(in srgb, currentColor 18%, transparent)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {columns.map((column) => (
                    <td key={column} style={{ padding: "0.3rem 0.5rem", verticalAlign: "top" }}>
                      {row[column] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>No tabular data.</div>
      )}
    </div>
  );
};

/**
 * The registry. This map is the complete set of component ids that may execute
 * as first-party code inside chat.
 */
export const NATIVE_UI_REGISTRY: Record<string, NativeUiEntry> = {
  "chart.bar": { component: BarChart, className: "max-w-[min(34rem,100%)]" },
  "table.rows": { component: DataTable, className: "max-w-[min(34rem,100%)]" },
  "openui.program": { component: OpenUiNativeEntry, className: "max-w-[min(34rem,100%)]" },
};

/** Resolve a registered component, or null when the id is not registered. */
export function resolveNativeUiComponent(componentId: string): NativeUiEntry | null {
  const entry = NATIVE_UI_REGISTRY[componentId];
  return entry && typeof entry.component === "function" ? entry : null;
}
