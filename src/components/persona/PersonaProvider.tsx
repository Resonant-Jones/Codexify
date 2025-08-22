import React, { createContext, useState, useEffect, useRef, useContext } from "react";

interface PersonaContextProps {
  ready: boolean;
  activePersonaId: string;
  setActivePersonaId: (id: string) => void;
  memoryTags: string[];
  setMemoryTags: (tags: string[]) => void;
  recentTags: string[];
  setRecentTags: (tags: string[]) => void;
  debugMode: boolean;
  setDebugMode: (enabled: boolean) => void;
  addMemoryTag?: (tag: string) => void;
  removeMemoryTag?: (tag: string) => void;
  clearMemoryTags?: () => void;
  pushRecentTag?: (tag: string) => void;
}

const NS = "cfy.persona.";
const KEYS = {
  version: NS + "version",
  activePersonaId: NS + "activeId",
  memoryTags: NS + "memoryTags",
  recentTags: NS + "recentTags",
  debugMode: NS + "debug",
};
const LEGACY = {
  activePersonaId: "activePersonaId",
  memoryTags: "memoryTags",
  recentTags: "recentTags",
  debugMode: "debugMode",
};
const CURRENT_VERSION = "1";

function safeParseArray(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function readBool(raw: string | null, fallback: boolean): boolean {
  if (raw == null) return fallback;
  return raw === "true" || raw === "1";
}

export const PersonaContext = createContext<PersonaContextProps>({
  ready: false,
  activePersonaId: "default",
  setActivePersonaId: () => {},
  memoryTags: [],
  setMemoryTags: () => {},
  recentTags: [],
  setRecentTags: () => {},
  debugMode: false,
  setDebugMode: () => {},
  addMemoryTag: () => {},
  removeMemoryTag: () => {},
  clearMemoryTags: () => {},
  pushRecentTag: () => {},
});

export function usePersona() {
  const ctx = useContext(PersonaContext);
  if (!ctx.ready) throw new Error("usePersona must be used within <PersonaProvider>");
  return ctx;
}

export const PersonaProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activePersonaId, setActivePersonaId] = useState("default");
  const [memoryTags, setMemoryTagsState] = useState<string[]>([]);
  const [recentTags, setRecentTagsState] = useState<string[]>([]);
  const [debugMode, setDebugMode] = useState(false);
  const hydrated = useRef(false);

  const arraysEqual = (a: string[], b: string[]) => a.length === b.length && a.every((v, i) => v === b[i]);
  const norm = (s: string) => s.trim().replace(/\s+/g, " ").slice(0, 64);
  const normalizeMemory = (arr: string[]) => Array.from(new Set(arr.map(norm))).filter(Boolean).slice(0, 200);
  const normalizeRecent = (arr: string[]) => Array.from(new Set(arr.map(norm))).filter(Boolean).slice(0, 50);

  const dev = typeof process !== "undefined" && process.env && process.env.NODE_ENV !== "production";
  const devWarnNormalization = (kind: string, input: string[], output: string[]) => {
    if (!dev) return;
    if (arraysEqual(input, output)) return;
    const dropped = input.filter((x) => !output.includes(x)).slice(0, 5);
    const added = output.filter((x) => !input.includes(x)).slice(0, 5);
    const sampleIn = input.slice(0, 8);
    const sampleOut = output.slice(0, 8);
    // eslint-disable-next-line no-console
    console.warn(`[Persona] normalized ${kind}`, { inCount: input.length, outCount: output.length, dropped, added, sampleIn, sampleOut });
  };

  const setMemoryTagsNormalized = (tags: string[]) => {
    const out = normalizeMemory(tags);
    devWarnNormalization("memoryTags", tags, out);
    setMemoryTagsState(out);
  };
  const setRecentTagsNormalized = (tags: string[]) => {
    const out = normalizeRecent(tags);
    devWarnNormalization("recentTags", tags, out);
    setRecentTagsState(out);
  };

  const addMemoryTag = (tag: string) => {
    const t = norm(tag);
    if (!t) return;
    setMemoryTagsState((prev) => {
      const next = Array.from(new Set([...prev, t]));
      return next.slice(0, 200);
    });
  };

  const removeMemoryTag = (tag: string) => {
    const t = norm(tag);
    setMemoryTagsState((prev) => prev.filter((x) => x !== t));
  };

  const clearMemoryTags = () => setMemoryTagsState([]);

  const pushRecentTag = (tag: string) => {
    const t = norm(tag);
    if (!t) return;
    setRecentTagsState((prev) => {
      const next = [t, ...prev.filter((x) => x !== t)];
      return next.slice(0, 50);
    });
  };

  useEffect(() => {
    if (typeof window === "undefined") {
      hydrated.current = true;
      return;
    }
    const v = localStorage.getItem(KEYS.version);

    let nextId = localStorage.getItem(KEYS.activePersonaId) || null;
    let nextMem = safeParseArray(localStorage.getItem(KEYS.memoryTags));
    let nextRecent = safeParseArray(localStorage.getItem(KEYS.recentTags));
    let nextDebugRaw = localStorage.getItem(KEYS.debugMode);

    if (!v) {
      const legacyId = localStorage.getItem(LEGACY.activePersonaId);
      const legacyMem = safeParseArray(localStorage.getItem(LEGACY.memoryTags));
      const legacyRecent = safeParseArray(localStorage.getItem(LEGACY.recentTags));
      const legacyDebug = localStorage.getItem(LEGACY.debugMode);
      if (legacyId) nextId = legacyId;
      if (legacyMem.length) nextMem = legacyMem;
      if (legacyRecent.length) nextRecent = legacyRecent;
      if (legacyDebug != null) nextDebugRaw = legacyDebug;
    }

    if (nextId) setActivePersonaId(nextId);
    const normMem = normalizeMemory(nextMem);
    const normRecent = normalizeRecent(nextRecent);
    if (normMem.length) setMemoryTagsState(normMem);
    if (normRecent.length) setRecentTagsState(normRecent);
    setDebugMode(readBool(nextDebugRaw, false));

    try { localStorage.setItem(KEYS.version, CURRENT_VERSION); } catch {}
    hydrated.current = true;
  }, []);

  useEffect(() => {
    if (!hydrated.current || typeof window === "undefined") return;
    try {
      const mem = normalizeMemory(memoryTags);
      const rec = normalizeRecent(recentTags);
      if (!arraysEqual(mem, memoryTags)) {
        setMemoryTagsState(mem);
        return;
      }
      if (!arraysEqual(rec, recentTags)) {
        setRecentTagsState(rec);
        return;
      }
      localStorage.setItem(KEYS.activePersonaId, activePersonaId);
      localStorage.setItem(KEYS.memoryTags, JSON.stringify(mem));
      localStorage.setItem(KEYS.recentTags, JSON.stringify(rec));
      localStorage.setItem(KEYS.debugMode, debugMode ? "true" : "false");
    } catch {}
  }, [activePersonaId, memoryTags, recentTags, debugMode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (!e.key) return;
      if (e.key === KEYS.activePersonaId && typeof e.newValue === "string") setActivePersonaId(e.newValue);
      else if (e.key === KEYS.memoryTags) {
        const raw = safeParseArray(e.newValue);
        const normed = normalizeMemory(raw);
        devWarnNormalization("memoryTags(storage)", raw, normed);
        setMemoryTagsState(normed);
      } else if (e.key === KEYS.recentTags) {
        const raw = safeParseArray(e.newValue);
        const normed = normalizeRecent(raw);
        devWarnNormalization("recentTags(storage)", raw, normed);
        setRecentTagsState(normed);
      } else if (e.key === KEYS.debugMode) setDebugMode(readBool(e.newValue, false));
      else if (e.key === LEGACY.activePersonaId && typeof e.newValue === "string") setActivePersonaId(e.newValue);
      else if (e.key === LEGACY.memoryTags) {
        const raw = safeParseArray(e.newValue);
        const normed = normalizeMemory(raw);
        devWarnNormalization("memoryTags(legacy)", raw, normed);
        setMemoryTagsState(normed);
      } else if (e.key === LEGACY.recentTags) {
        const raw = safeParseArray(e.newValue);
        const normed = normalizeRecent(raw);
        devWarnNormalization("recentTags(legacy)", raw, normed);
        setRecentTagsState(normed);
      } else if (e.key === LEGACY.debugMode) setDebugMode(readBool(e.newValue, false));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <PersonaContext.Provider
      value={{
        ready: true,
        activePersonaId,
        setActivePersonaId,
        memoryTags,
        setMemoryTags: setMemoryTagsNormalized,
        recentTags,
        setRecentTags: setRecentTagsNormalized,
        debugMode,
        setDebugMode,
        addMemoryTag,
        removeMemoryTag,
        clearMemoryTags,
        pushRecentTag,
      }}
    >
      {children}
    </PersonaContext.Provider>
  );
};