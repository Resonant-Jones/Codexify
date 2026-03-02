import "./index.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { configureGC } from "./dcw-services/gc";
import { GuardianAPI } from "./lib/guardianApi";
import { resolveAuthStateOnBoot } from "./lib/authState";
import {
  initRuntimeConfig,
  invokeTauriCommand,
  isTauriRuntime,
} from "./lib/runtimeConfig";
import {
  refreshApiBaseUrl,
  setRuntimeApiKey,
} from "./lib/api";

;(window as any).GuardianAPI = GuardianAPI;

declare global {
  interface Window {
    __GC_ENV__?: any;
  }
}

function getComputedStyleVar(name: string, el: Element = document.documentElement) {
  return getComputedStyle(el).getPropertyValue(name).trim();
}

declare global {
  interface Window {
    getComputedStyleVar?: (name: string, el?: Element) => string;
  }
}

if (typeof window !== "undefined") {
  window.getComputedStyleVar = (
    name: string,
    el: Element = document.documentElement
  ) => getComputedStyle(el).getPropertyValue(name).trim();
}

function readDevApiKey(): string {
  if (!import.meta.env.DEV) return "";
  return ((import.meta as any).env.VITE_GUARDIAN_DEV_API_KEY || "").trim();
}

async function hydrateDesktopApiKey(): Promise<void> {
  if (!isTauriRuntime()) return;
  try {
    const value = await invokeTauriCommand<string | null>("desktop_get_api_key");
    setRuntimeApiKey(typeof value === "string" ? value : null);
  } catch (error) {
    console.warn("[desktop-auth] Unable to hydrate API key from secure store", error);
  }
}

function renderApp(): void {
  const rootEl = document.getElementById("root");
  if (!rootEl) {
    console.error("[gc] #root element not found — cannot mount React app.");
    return;
  }

  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

async function bootstrap(): Promise<void> {
  const runtimeConfig = await initRuntimeConfig();
  refreshApiBaseUrl();

  const devApiKey = readDevApiKey();
  configureGC({ base: runtimeConfig.apiBaseUrl, token: devApiKey || undefined });

  await hydrateDesktopApiKey();
  resolveAuthStateOnBoot();

  try {
    (window as any).__GC_ENV__ = {
      mode: import.meta.env.MODE,
      runtimeMode: runtimeConfig.mode,
      base: runtimeConfig.apiBaseUrl,
      backendBase: runtimeConfig.backendBaseUrl,
      sse: runtimeConfig.sseUrl,
      keyPresent: !!devApiKey,
      guardianDevKeyPresent: !!(import.meta.env as any).VITE_GUARDIAN_DEV_API_KEY,
    };
    console.info("[gc] env snapshot", {
      mode: (window as any).__GC_ENV__?.mode,
      runtimeMode: (window as any).__GC_ENV__?.runtimeMode,
      base: (window as any).__GC_ENV__?.base,
      backendBase: (window as any).__GC_ENV__?.backendBase,
      keyPresent: (window as any).__GC_ENV__?.keyPresent,
      guardianDevKeyPresent: (window as any).__GC_ENV__?.guardianDevKeyPresent,
    });
  } catch (err) {
    console.warn("[gc] env snapshot failed", err);
  }

  if (!devApiKey && import.meta.env.DEV) {
    console.info(
      "[gc] Dev API key override disabled. Provide VITE_GUARDIAN_DEV_API_KEY only when needed for local-safe auth."
    );
  } else if (devApiKey) {
    const masked = String(devApiKey);
    console.info("[gc] Backend configured:", {
      base: runtimeConfig.apiBaseUrl,
      key: `${masked.slice(0, 4)}…${masked.slice(-4)}`,
    });
  }

  renderApp();
}

void bootstrap();
