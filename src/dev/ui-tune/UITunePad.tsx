import React from "react";

/**
 * UITunePad – dev-only UI playground ("tune rack").
 *
 * - Self-contained: renders fine without external CSS.
 * - Also sets CSS variables on the sandbox root so optional
 *   `ui-tune.dev.css` can enhance visuals when present.
 * - Saves/loads a small set of variables to localStorage.
 */

// --- Types & Presets ---------------------------------------------------------

type Vars = {
  radius: number;       // px
  blur: number;         // px
  depth: number;        // 0..1.5
  panelOpacity: number; // 0..1
  glassOpacity: number; // 0..1
  borderAlpha: number;  // 0..1
  accent: string;       // css color
};

type Preset = { name: string; vars: Partial<Vars> };

const DEFAULTS: Vars = {
  radius: 19,
  blur: 10,
  depth: 1,
  panelOpacity: 0.78,
  glassOpacity: 0.60,
  borderAlpha: 0.10,
  accent: "#6D6AFE",
};

const PRESETS: Preset[] = [
  { name: "SoftGlass", vars: { radius: 19, blur: 10, depth: 1, panelOpacity: 0.78, glassOpacity: 0.60, borderAlpha: 0.10, accent: "#6D6AFE" }},
  { name: "GuardianChrome", vars: { radius: 19, blur: 12, depth: 1.25, panelOpacity: 0.72, glassOpacity: 0.56, borderAlpha: 0.14, accent: "#9b87f5" }},
  { name: "MatteLow", vars: { radius: 19, blur: 6, depth: 0.75, panelOpacity: 0.90, glassOpacity: 0.82, borderAlpha: 0.06, accent: "#22b3a6" }},
];

const STORAGE_KEY = "uiTuneVars:v1";

// --- Helpers -----------------------------------------------------------------

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function rgba(hexOrCss: string, alpha: number) {
  // crude: pass-through for css colors like rgb()/hsl(); simple hex -> rgba
  if (hexOrCss.startsWith("#")) {
    const h = hexOrCss.replace("#", "");
    const bigint = parseInt(h.length === 3 ? h.split("").map(c => c + c).join("") : h, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return hexOrCss; // trust the caller
}

function shadow(depth: number) {
  // scale a two-layer shadow by depth
  const d1 = clamp(depth, 0, 1.5);
  const o1 = 0.18 * d1; // outer opacity
  const o2 = 0.10 * d1;
  return `0 ${Math.round(14 * d1)}px ${Math.round(34 * d1)}px rgba(0,0,0,${o1}), 0 ${Math.round(4 * d1)}px ${Math.round(12 * d1)}px rgba(0,0,0,${o2})`;
}

// --- Component ---------------------------------------------------------------

export default function UITunePad() {
  const [vars, setVars] = React.useState<Vars>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return { ...DEFAULTS, ...JSON.parse(saved) } as Vars;
    } catch {}
    return DEFAULTS;
  });

  const sandboxRef = React.useRef<HTMLDivElement>(null);

  const setVar = (key: keyof Vars, value: number | string) =>
    setVars(v => ({ ...v, [key]: value } as Vars));

  const applyPreset = (p: Preset) => setVars(v => ({ ...v, ...p.vars } as Vars));

  React.useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(vars));
    // also expose as CSS variables in case the scoped CSS is present
    const el = sandboxRef.current;
    if (el) {
      el.style.setProperty("--card-radius", `${vars.radius}px`);
      el.style.setProperty("--tile-blur", `${vars.blur}px`);
      el.style.setProperty("--depth-scale", String(vars.depth));
      el.style.setProperty("--panel-bg", rgba("#ffffff", vars.panelOpacity));
      el.style.setProperty("--chip-bg", rgba("#ffffff", vars.glassOpacity));
      el.style.setProperty("--panel-border", `rgba(20,23,28,${vars.borderAlpha})`);
      el.style.setProperty("--accent-strong", vars.accent);
    }
  }, [vars]);

  // Inline style fallbacks so it looks good without CSS
  const styles = React.useMemo(() => {
    const tileBg = rgba("#ffffff", vars.glassOpacity);
    const panelBg = rgba("#ffffff", vars.panelOpacity);
    const border = `1px solid rgba(20,23,28,${vars.borderAlpha})`;
    const radius = vars.radius;
    const blur = vars.blur;

    const tileStyle: React.CSSProperties = {
      background: tileBg,
      border: border as any,
      borderRadius: radius,
      boxShadow: shadow(vars.depth),
      backdropFilter: `saturate(140%) blur(${blur}px)`,
      WebkitBackdropFilter: `saturate(140%) blur(${blur}px)`,
    };
    const panelStyle: React.CSSProperties = {
      background: panelBg,
      border: border as any,
      borderRadius: radius,
      boxShadow: `inset 0 2px rgba(255,255,255,.16), inset 0 -2px rgba(0,0,0,.12)`,
      backdropFilter: `saturate(140%) blur(${blur}px)`,
      WebkitBackdropFilter: `saturate(140%) blur(${blur}px)`,
    };
    const badgeStyle: React.CSSProperties = {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "2px 8px",
      minWidth: 20,
      height: 20,
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 600,
      color: "#fff",
      background: vars.accent,
    };
    return { tileStyle, panelStyle, badgeStyle };
  }, [vars]);

  return (
    <div
      ref={sandboxRef}
      className="tune-sandbox"
      style={{
        padding: 16,
        fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto",
        color: "#111418",
        // gradient page bg just for context
        background: "linear-gradient(180deg, #f6f7fb 0%, #eef1f7 100%)",
        minHeight: "100dvh",
      }}
    >
      {/* Control bar */}
      <div style={{ ...styles.panelStyle, padding: 12, marginBottom: 12 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
          <Knob label={`Radius ${vars.radius}px`} min={8} max={28} step={1} value={vars.radius} onChange={v => setVar("radius", v)} />
          <Knob label={`Blur ${vars.blur}px`} min={0} max={24} step={1} value={vars.blur} onChange={v => setVar("blur", v)} />
          <Knob label={`Depth ${vars.depth.toFixed(2)}`} min={0} max={1.5} step={0.05} value={vars.depth} onChange={v => setVar("depth", v)} />
          <Knob label={`Panel ${Math.round(vars.panelOpacity*100)}%`} min={0.2} max={1} step={0.02} value={vars.panelOpacity} onChange={v => setVar("panelOpacity", v)} />
          <Knob label={`Glass ${Math.round(vars.glassOpacity*100)}%`} min={0.2} max={1} step={0.02} value={vars.glassOpacity} onChange={v => setVar("glassOpacity", v)} />
          <Knob label={`Border α ${vars.borderAlpha.toFixed(2)}`} min={0} max={0.3} step={0.01} value={vars.borderAlpha} onChange={v => setVar("borderAlpha", v)} />
          <Color label="Accent" value={vars.accent} onChange={v => setVar("accent", v)} />

          {/* Presets */}
          <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
            {PRESETS.map(p => (
              <button key={p.name} onClick={() => applyPreset(p)} style={{ ...styles.tileStyle, padding: "6px 10px", border: 0 }}>
                {p.name}
              </button>
            ))}
            <button onClick={() => localStorage.removeItem(STORAGE_KEY)} style={{ ...styles.tileStyle, padding: "6px 10px", border: 0 }}>Reset</button>
          </div>
        </div>
      </div>

      {/* Preview grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ ...styles.tileStyle, padding: 12 }}>
            <div style={{ ...styles.panelStyle, padding: 10, marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Design Sync #{i + 1}</div>
                  <div style={{ opacity: .7, fontSize: 12, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Let’s ship the new message bubbles today.</div>
                </div>
                <span style={styles.badgeStyle}>2</span>
              </div>
            </div>
            <div style={{ ...styles.panelStyle, padding: 10 }}>
              <div style={{ fontSize: 12, opacity: .75, marginBottom: 6 }}>Badge</div>
              <span style={styles.badgeStyle}>ALPHA</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Small control primitives ------------------------------------------------

type KnobProps = { label: string; min: number; max: number; step?: number; value: number; onChange: (v: number) => void };
function Knob({ label, min, max, step = 1, value, onChange }: KnobProps) {
  return (
    <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12 }}>
      <span style={{ minWidth: 84, opacity: .75 }}>{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.currentTarget.value))}
      />
    </label>
  );
}

type ColorProps = { label: string; value: string; onChange: (v: string) => void };
function Color({ label, value, onChange }: ColorProps) {
  return (
    <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12 }}>
      <span style={{ opacity: .75 }}>{label}</span>
      <input type="color" value={value} onChange={(e) => onChange(e.currentTarget.value)} />
    </label>
  );
}
