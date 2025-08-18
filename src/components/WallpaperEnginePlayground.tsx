

import React, { useEffect, useState } from "react";
import { SaveControl } from "../ui/SaveControl";
import { useTriggerAction } from "../hooks/useTriggerAction";

/**
 * Wallpaper Engine Glass Workspace (playground)
 * Floating side panel with tabs (no sublabels) + desktop-only tooltips.
 * Safe for Canvas: no remote assets on boot, minimal effects, inline styles, ErrorBoundary.
 */

// ---------------- Error Boundary ----------------
class ErrorBoundary extends React.Component<any, { err: any }>{
  constructor(props: any){ super(props); this.state = { err: null }; }
  static getDerivedStateFromError(err: any){ return { err }; }
  render(){
    if (this.state.err) {
      return (
        <div style={{fontFamily:"ui-sans-serif,system-ui",padding:16}}>
          <h2 style={{fontWeight:700,marginBottom:8}}>UI crashed</h2>
          <pre style={{whiteSpace:"pre-wrap",background:"#111",color:"#eee",padding:12,borderRadius:8}}>
            {String(this.state.err && (this.state.err as any).message ? (this.state.err as any).message : this.state.err)}
          </pre>
        </div>
      );
    }
    return this.props.children as any;
  }
}

// ---------------- Helpers & tests ----------------
function computeBgStyle(mode: string, solidColor: string, gradient: string, imageUrl: string){
  if (mode === "solid") return { background: solidColor } as React.CSSProperties;
  if (mode === "gradient") return { background: gradient } as React.CSSProperties;
  if (mode === "image" && imageUrl) return { backgroundImage: `url(${imageUrl})`, backgroundSize: "cover", backgroundPosition: "center" } as React.CSSProperties;
  return { background: solidColor } as React.CSSProperties;
}
function runSelfTests(){
  const solid = computeBgStyle("solid", "#000", "", "");
  const grad = computeBgStyle("gradient", "#000", "linear-gradient(#000,#111)", "");
  const img  = computeBgStyle("image", "#000", "", "https://example.com/x.jpg");
  if ((solid as any).background !== "#000") throw new Error("solid style test failed");
  if (!String((grad as any).background).includes("linear-gradient")) throw new Error("gradient style test failed");
  if (!String((img as any).backgroundImage).includes("url(")) throw new Error("image style test failed");
  const fallback = computeBgStyle("image", "#123", "", "");
  if ((fallback as any).background !== "#123") throw new Error("image fallback test failed");
  console.log("[WallpaperEngine tests] passed");
}

// ---------------- Icons ----------------
function BurgerIcon({ className = "" }:{ className?: string }){
  const bar: React.CSSProperties = { height: 2, background: "currentColor", marginBottom: 4, borderRadius: 2 };
  return (
    <div className={className} aria-hidden>
      <div style={bar} />
      <div style={bar} />
      <div style={{ ...bar, marginBottom: 0 }} />
    </div>
  );
}

// ---------------- Tooltip (desktop only) ----------------
function usePointerFine(){
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq: any = (window as any).matchMedia && (window as any).matchMedia("(pointer: fine)");
    const update = () => setFine(mq && mq.matches ? true : false);
    update();
    if (mq && mq.addEventListener) mq.addEventListener("change", update);
    return () => { if (mq && mq.removeEventListener) mq.removeEventListener("change", update); };
  }, []);
  return fine;
}
function Tooltip({ label, enabled, children }:{ label: string; enabled: boolean; children: React.ReactNode }){
  const [show, setShow] = useState(false);
  return (
    <div
      onMouseEnter={() => enabled && setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => enabled && setShow(true)}
      onBlur={() => setShow(false)}
      style={{ position: "relative", display: "inline-block" }}
    >
      {children}
      {enabled && show && (
        <div style={{ position: "absolute", top: -30, left: "50%", transform: "translateX(-50%)", background: "rgba(0,0,0,0.85)", color: "#fff", fontSize: 10, padding: "4px 6px", borderRadius: 6, whiteSpace: "nowrap", pointerEvents: "none" }}>
          {label}
        </div>
      )}
    </div>
  );
}

// ---------------- Floating Side Panel ----------------
function FloatingSidePanel({ open, onClose, useEffects, activeTab, setActiveTab }:{ open: boolean; onClose: ()=>void; useEffects: boolean; activeTab: string; setActiveTab: (t:string)=>void; }){
  const glassBg = useEffects ? "rgba(0,0,0,0.30)" : "rgba(0,0,0,0.45)";
  const base: React.CSSProperties = {
    position: "fixed",
    top: 20,
    bottom: 20,
    left: 12,
    width: 360,
    borderRadius: 16,
    color: "#fff",
    zIndex: 51,
    display: "flex",
    flexDirection: "column",
    transition: "transform 180ms ease-out, opacity 180ms ease-out",
    background: glassBg,
    backdropFilter: useEffects ? "blur(14px)" : "none",
    boxShadow: "0 20px 50px rgba(0,0,0,0.35)",
    overflow: "hidden"
  };
  const style = open ? { ...base, transform: "translateX(0)", opacity: 1 } : { ...base, transform: "translateX(-110%)", opacity: 0 };

  const tabStyle = (t: string): React.CSSProperties => ({
    padding: "8px 10px",
    borderRadius: 10,
    background: activeTab === t ? "rgba(255,255,255,0.12)" : "transparent",
    border: activeTab === t ? "1px solid rgba(255,255,255,0.25)" : "1px solid transparent",
    fontSize: 12,
    cursor: "pointer",
    color: "#fff"
  });

  const boundaryTop: React.CSSProperties = { height: 30, background: "linear-gradient(180deg, rgba(0,0,0,0.45), rgba(0,0,0,0))", position: "relative", zIndex: 2 };
  const boundaryBottom: React.CSSProperties = { height: 30, background: "linear-gradient(0deg, rgba(0,0,0,0.45), rgba(0,0,0,0))", position: "relative", zIndex: 2 };
  const scrollWrap: React.CSSProperties = { position: "relative", flex: 1, overflow: "auto", padding: "8px 12px", zIndex: 1 };
  const inner: React.CSSProperties = { paddingTop: 20, paddingBottom: 20 };

  const isPointerFine = usePointerFine();

  return (
    <div style={style} onKeyDown={(e)=>{ if ((e as any).key === "Escape") onClose(); }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 12, borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
        <div style={{ fontWeight: 700 }}>Workspace</div>
        <button onClick={onClose} title="Close" style={{ color: "#fff", background: "transparent", border: 0, fontSize: 18 }}>×</button>
      </div>

      {/* Tabs Row (no sublabels) with desktop-only tooltips */}
      <div style={{ display: "flex", gap: 8, padding: 12, borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
        {(["Guardian","Codex","Library","Settings"]).map((tab) => (
          <Tooltip key={tab} label={tab} enabled={isPointerFine}>
            <button onClick={()=>setActiveTab(tab)} style={tabStyle(tab)}>{tab}</button>
          </Tooltip>
        ))}
      </div>

      {/* Sections with boundaries and scroll-under effect */}
      <div style={boundaryTop} />
      <div style={scrollWrap}>
        <div style={inner}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>— Projects —</div>
          <ul style={{ display: "grid", gap: 8, fontSize: 14 }}>
            {["Guardian Backend","Codexify","PulseOS","Persona: Axis","Memory Graph","UI Shell"].map((p) => (
              <li key={p} style={{ padding: "8px 10px", borderRadius: 10, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>{p}</li>
            ))}
          </ul>

          <div style={{ height: 24 }} />

          <div style={{ fontWeight: 700, marginBottom: 8 }}>— Conversations —</div>
          <ul style={{ display: "grid", gap: 8, fontSize: 14 }}>
            {["Initial","Brainstorming","Deep Research","Design Sync","User Interview"].map((c) => (
              <li key={c} style={{ padding: "8px 10px", borderRadius: 10, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>{c}</li>
            ))}
          </ul>
        </div>
      </div>
      <div style={boundaryBottom} />
    </div>
  );
}

// ---------------- Main Component ----------------
export default function WallpaperEnginePlayground(){
  const [dark, setDark] = useState(false);
  const [useEffects, setUseEffects] = useState(false);
  const [mode, setMode] = useState("solid"); // solid | gradient | image
  const [solidColor, setSolidColor] = useState("#0b1020");
  const [gradient, setGradient] = useState("linear-gradient(135deg,#0f172a 0%,#1e293b 55%,#020617 100%)");
  const [imageUrl, setImageUrl] = useState("");

  const [panelOpen, setPanelOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("Guardian");
  const [composerText, setComposerText] = useState("");

  const { trigger } = useTriggerAction();

  useEffect(() => { try { runSelfTests(); } catch (e) { console.error(e); } }, []);

  // Edge hover trigger
  useEffect(() => {
    let timer: any = null;
    const onMove = (e: MouseEvent) => {
      if (panelOpen) return;
      if ((e as any).clientX <= 6) {
        if (!timer) timer = setTimeout(() => setPanelOpen(true), 180);
      } else if (timer) { clearTimeout(timer); timer = null; }
    };
    window.addEventListener("mousemove", onMove);
    return () => { window.removeEventListener("mousemove", onMove); if (timer) clearTimeout(timer); };
  }, [panelOpen]);

  // Swipe gestures
  useEffect(() => {
    let startX: number | null = null;
    const onTouchStart = (e: TouchEvent) => { const t = e.touches[0]; startX = t && (t as any).clientX; };
    const onTouchMove = (e: TouchEvent) => {
      if (startX == null) return;
      const x = (e.touches[0] as any).clientX;
      const dx = x - startX;
      if (!panelOpen && startX < 24 && dx > 30) { setPanelOpen(true); startX = null; }
      if (panelOpen && dx < -40) { setPanelOpen(false); startX = null; }
    };
    const onTouchEnd = () => { startX = null; };
    window.addEventListener("touchstart", onTouchStart as any, { passive: true } as any);
    window.addEventListener("touchmove", onTouchMove as any, { passive: true } as any);
    window.addEventListener("touchend", onTouchEnd as any);
    return () => {
      window.removeEventListener("touchstart", onTouchStart as any);
      window.removeEventListener("touchmove", onTouchMove as any);
      window.removeEventListener("touchend", onTouchEnd as any);
    };
  }, [panelOpen]);

  const style = computeBgStyle(mode, solidColor, gradient, imageUrl);
  const glass = useEffects ? "rgba(0,0,0,0.30)" : "rgba(0,0,0,0.45)";
  const textColor = { color: "#fff" } as React.CSSProperties;

  return (
    <ErrorBoundary>
      <div className={dark ? "dark" : ""}>
        <div style={{ ...style, height: "100vh", width: "100vw", position: "relative", overflow: "hidden" }}>
          {/* Scrim */}
          {panelOpen && (
            <div onClick={() => setPanelOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.25)", zIndex: 49 }} />
          )}

          {/* Floating Side Panel */}
          <FloatingSidePanel open={panelOpen} onClose={() => setPanelOpen(false)} useEffects={useEffects} activeTab={activeTab} setActiveTab={setActiveTab} />

          {/* Edge sensor */}
          <div onMouseEnter={() => setPanelOpen(true)} style={{ position: "fixed", left: 0, top: 0, bottom: 0, width: 4, zIndex: 50 }} />

          {/* Top bar */}
          <div style={{ position: "fixed", insetInline: 24, top: 16, zIndex: 30 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, background: glass }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, ...textColor }}>
                <button title="Menu" onClick={()=>setPanelOpen(v=>!v)} style={{ display: "grid", placeContent: "center", width: 36, height: 36, borderRadius: 10, background: "transparent", color: "#fff", border: 0 }}>
                  <BurgerIcon />
                </button>
                <div style={{ fontSize: 14, fontWeight: 600 }}>ThreadSpace</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, ...textColor }}>
                {/* Save + Pins */}
                <SaveControl
                  projectSlug={"codexify"}
                  payload={{ markdown: composerText || "(empty capture)", threadId: "thread-1", turnIndex: 0 }}
                />

                <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={useEffects} onChange={(e) => setUseEffects(e.target.checked)} /> Glass
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={dark} onChange={(e) => setDark(e.target.checked)} /> Dark
                </label>
                <select value={mode} onChange={(e) => setMode((e.target as any).value)} style={{ background: "rgba(255,255,255,0.2)", color: "#fff", borderRadius: 8, padding: "6px 8px", border: 0 }}>
                  <option value="solid">Solid</option>
                  <option value="gradient">Gradient</option>
                  <option value="image">Image</option>
                </select>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div style={{ position: "fixed", right: 24, top: 72, zIndex: 30, padding: 12, borderRadius: 12, background: glass, color: "#fff", minWidth: 280 }}>
            {mode === "solid" && (
              <div>
                <div style={{ marginBottom: 6, fontSize: 12, opacity: 0.9 }}>Color</div>
                <input type="color" value={solidColor} onChange={(e) => setSolidColor((e.target as any).value)} style={{ width: "100%", height: 40, background: "transparent", border: 0, padding: 0 }} />
              </div>
            )}
            {mode === "gradient" && (
              <div>
                <div style={{ marginBottom: 6, fontSize: 12, opacity: 0.9 }}>Gradient CSS</div>
                <input value={gradient} onChange={(e) => setGradient((e.target as any).value)} style={{ width: "100%", borderRadius: 8, padding: "8px 10px", background: "rgba(255,255,255,0.15)", color: "#fff", border: 0 }} />
              </div>
            )}
            {mode === "image" && (
              <div>
                <div style={{ marginBottom: 6, fontSize: 12, opacity: 0.9 }}>Image URL (≤1920px)</div>
                <input value={imageUrl} onChange={(e) => setImageUrl((e.target as any).value)} placeholder="https://..." style={{ width: "100%", borderRadius: 8, padding: "8px 10px", background: "rgba(255,255,255,0.15)", color: "#fff", border: 0 }} />
              </div>
            )}
          </div>

          {/* Composer */}
          <div style={{ position: "fixed", left: 0, right: 0, bottom: 24, paddingInline: 16, display: "grid", gridTemplateColumns: "1fr 56px", gap: 8 }}>
            <div style={{ borderRadius: 12, padding: "14px 16px", color: "#fff", background: useEffects ? "rgba(15,23,42,0.7)" : "rgba(0,0,0,0.7)" }}>
              <input
                placeholder="Ask a question..."
                value={composerText}
                onChange={(e) => setComposerText((e.target as HTMLInputElement).value)}
                style={{ width: "100%", background: "transparent", border: 0, outline: "none", color: "#fff" }}
              />
            </div>
            <button
              style={{ display: "grid", placeContent: "center", borderRadius: 12, background: "rgba(99,102,241,0.9)", color: "#fff", border: 0 }}
              onClick={() => {
                trigger("save_markdown", {
                  markdown: composerText || "(empty capture)",
                  threadId: "thread-1",
                  turnIndex: 0
                });
                setComposerText("");
              }}
            >✓</button>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}