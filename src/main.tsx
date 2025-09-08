import "./index.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { configureGC } from "@/dcw-services/gc";
// Tailwind base/utilities and app entry

declare global {
  interface Window {
    __GC_ENV__?: any;
  }
}

// Wire the API client to the backend using Vite envs
const API_BASE = import.meta.env.VITE_GUARDIAN_API_BASE ?? "http://127.0.0.1:8000";
const API_KEY  = import.meta.env.VITE_GUARDIAN_API_KEY ?? "";


configureGC({ base: API_BASE, token: API_KEY });

// ---- env diagnostics (safe to keep)
try {
  // Make a snapshot you can inspect via `window.__GC_ENV__` in the browser console
  (window as any).__GC_ENV__ = {
    mode: import.meta.env.MODE,
    base: import.meta.env.VITE_GUARDIAN_API_BASE ?? null,
    keyPresent: !!import.meta.env.VITE_GUARDIAN_API_KEY,
    // Also surface GUARDIAN_/GC_ keys if present (vite.config.ts envPrefix covers them)
    guardianKeyPresent: !!(import.meta.env as any).GUARDIAN_API_KEY,
    gcKeyPresent:       !!(import.meta.env as any).GC_API_KEY,
  };
  // One-time console breadcrumb
  // (Do not log secrets; only booleans for keys)
  console.info('[gc] env snapshot', {
    mode: (window as any).__GC_ENV__?.mode,
    base: (window as any).__GC_ENV__?.base,
    keyPresent: (window as any).__GC_ENV__?.keyPresent,
    guardianKeyPresent: (window as any).__GC_ENV__?.guardianKeyPresent,
    gcKeyPresent: (window as any).__GC_ENV__?.gcKeyPresent,
  });
} catch (err) {
  console.warn('[gc] env snapshot failed', err);
}
// ---- end env diagnostics

if (!API_KEY) {
  // This will cause 401s from the backend; mask the value if present
  console.warn("[gc] VITE_GUARDIAN_API_KEY is empty; backend calls will be unauthorized.");
} else {
  const masked = String(API_KEY);
  console.info("[gc] Backend configured:", { base: API_BASE, key: `${masked.slice(0,4)}…${masked.slice(-4)}` });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
