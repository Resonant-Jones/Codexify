import "./index.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { configureGC } from "./dcw-services/gc";
import { GuardianAPI } from "./lib/guardianApi";
// Tailwind base/utilities and app entry
;(window as any).GuardianAPI = GuardianAPI;
declare global {
  interface Window {
    __GC_ENV__?: any;
  }
}
// --- runtime helper: read a CSS custom property safely (prevents ReferenceError) ---
function getComputedStyleVar(name: string, el: Element = document.documentElement) {
  return getComputedStyle(el).getPropertyValue(name).trim();
}
declare global {
  interface Window {
    getComputedStyleVar?: (name: string, el?: Element) => string;
  }
}
if (typeof window !== "undefined") {
  window.getComputedStyleVar = (name: string, el: Element = document.documentElement) =>
    getComputedStyle(el).getPropertyValue(name).trim();
}

// Wire the API client to the backend using Vite/Guardian envs (with sensible fallbacks)
// Prefer VITE_* (frontend), then plain GUARDIAN_/GC_* (also exposed via envPrefix in vite.config.ts).
const API_BASE =
  (import.meta as any).env.VITE_GUARDIAN_API_BASE ||
  (import.meta as any).env.GUARDIAN_API_BASE ||
  "/api"; // default to Vite dev proxy

const API_KEY = (import.meta as any).env.VITE_GUARDIAN_API_KEY || "";

configureGC({ base: API_BASE, token: API_KEY });

// ---- env diagnostics (safe to keep)
try {
  // Make a snapshot you can inspect via `window.__GC_ENV__` in the browser console
  (window as any).__GC_ENV__ = {
    mode: import.meta.env.MODE,
    base: API_BASE,
    keyPresent: !!API_KEY,
    guardianKeyPresent: !!(import.meta.env as any).VITE_GUARDIAN_API_KEY,
  };
  console.info('[gc] env snapshot', {
    mode: (window as any).__GC_ENV__?.mode,
    base: (window as any).__GC_ENV__?.base,
    keyPresent: (window as any).__GC_ENV__?.keyPresent,
    guardianKeyPresent: (window as any).__GC_ENV__?.guardianKeyPresent,
  });
} catch (err) {
  console.warn('[gc] env snapshot failed', err);
}
// ---- end env diagnostics

if (!API_KEY) {
  console.warn("[gc] No API key provided; endpoints that require auth will return 401. Set VITE_GUARDIAN_API_KEY.");
} else {
  const masked = String(API_KEY);
  console.info("[gc] Backend configured:", { base: API_BASE, key: `${masked.slice(0,4)}…${masked.slice(-4)}` });
}

const rootEl = document.getElementById("root");
if (!rootEl) {
  console.error("[gc] #root element not found — cannot mount React app.");
} else {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
