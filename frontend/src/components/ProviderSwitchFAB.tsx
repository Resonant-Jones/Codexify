import React, { useEffect, useMemo, useRef, useState } from "react";
import { GuardianAPI } from "../lib/guardianApi";
import { usePreferredProvider } from "../hooks/usePreferredProvider";

export const ProviderSwitchFAB: React.FC = () => {
  const { provider, setProvider } = usePreferredProvider();
  const [open, setOpen] = useState(false);
  const [caps, setCaps] = useState<{ chat: string[]; embeddings: string[] }>({ chat: [], embeddings: [] });
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    GuardianAPI.capabilities().then(setCaps).catch(() => setCaps({ chat: [], embeddings: [] }));
  }, []);

  // close on esc
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // close when clicking outside the panel
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!panelRef.current) return;
      if (!panelRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const options = useMemo(() => ["", ...caps.chat], [caps.chat]); // "" = default

  return (
    <>
      {/* FAB */}
      <button
        aria-label="Choose model provider"
        onClick={() => setOpen((v) => !v)}
        style={{
          position: "fixed",
          right: 16,
          bottom: 16,
          borderRadius: 999,
          padding: "10px 14px",
          border: "1px solid rgba(0,0,0,0.12)",
          background: "rgba(255,255,255,0.8)",
          backdropFilter: "blur(8px)",
          boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
          cursor: "pointer",
          fontSize: 14,
          zIndex: 1000,
        }}
      >
        ⚙︎ Provider{provider ? `: ${provider}` : ": default"}
      </button>

      {/* Panel */}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Switch provider"
          ref={panelRef}
          style={{
            position: "fixed",
            right: 16,
            bottom: 64,
            width: 280,
            borderRadius: 12,
            border: "1px solid rgba(0,0,0,0.12)",
            background: "rgba(255,255,255,0.9)",
            backdropFilter: "blur(10px)",
            boxShadow: "0 16px 48px rgba(0,0,0,0.18)",
            padding: 12,
            display: "grid",
            gap: 10,
            zIndex: 1000,
          }}
        >
          <div style={{ fontWeight: 600 }}>Model Provider</div>
          <select
            value={provider ?? ""}
            onChange={(e) => setProvider(e.target.value || null)}
            style={{
              width: "100%",
              padding: "6px 8px",
              borderRadius: 8,
              border: "1px solid #d0d7de",
              background: "white",
            }}
          >
            {options.map((p) => (
              <option key={p || "__default"} value={p}>
                {p || "default (server-configured)"}
              </option>
            ))}
          </select>

          <div style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
            <button
              onClick={() => setProvider(null)}
              style={{
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid #d0d7de",
                background: "white",
                cursor: "pointer",
              }}
            >
              Reset to default
            </button>
            <button
              onClick={() => setOpen(false)}
              style={{
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid #d0d7de",
                background: "white",
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>

          <small style={{ opacity: 0.7 }}>
            Default is whatever your backend advertises via <code>GUARDIAN_PROVIDER</code>, unless the request overrides it.
          </small>
        </div>
      )}
    </>
  );
};

export default ProviderSwitchFAB;
