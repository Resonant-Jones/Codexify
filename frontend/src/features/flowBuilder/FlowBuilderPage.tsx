import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  DEFAULT_FLOW_BUILDER_MODE,
  getFlowBuilderPath,
  hasFlowBuilderModeQuery,
  parseFlowBuilderMode,
  type FlowBuilderMode,
} from "./flowBuilderRoute";

const FLOW_BUILDER_LAST_MODE_STORAGE_KEY = "cfy.flowBuilder.mode";

function readPersistedFlowBuilderMode(): FlowBuilderMode | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(FLOW_BUILDER_LAST_MODE_STORAGE_KEY);
    return raw === "expertise" || raw === "process" ? raw : null;
  } catch {
    return null;
  }
}

function persistFlowBuilderMode(mode: FlowBuilderMode): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(FLOW_BUILDER_LAST_MODE_STORAGE_KEY, mode);
  } catch {
    // Keep the route authoritative even if local storage is unavailable.
  }
}

function resolveInitialFlowBuilderMode(): FlowBuilderMode {
  if (typeof window === "undefined") return DEFAULT_FLOW_BUILDER_MODE;

  const routeMode = parseFlowBuilderMode(window.location.search);
  if (routeMode) {
    return routeMode;
  }

  if (hasFlowBuilderModeQuery(window.location.search)) {
    return DEFAULT_FLOW_BUILDER_MODE;
  }

  const storedMode = readPersistedFlowBuilderMode();
  return storedMode ?? DEFAULT_FLOW_BUILDER_MODE;
}

function canonicalizeFlowBuilderLocation(nextMode: FlowBuilderMode): void {
  if (typeof window === "undefined") return;

  const nextPath = getFlowBuilderPath(nextMode);
  const currentPath = `${window.location.pathname}${window.location.search}`;
  if (currentPath === nextPath) {
    return;
  }

  window.history.replaceState({}, "", nextPath);
}

function ModeButton({
  active,
  description,
  label,
  onClick,
  testId,
}: {
  active: boolean;
  description: string;
  label: string;
  onClick: () => void;
  testId: string;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      aria-pressed={active}
      onClick={onClick}
      className={[
        "rounded-[20px] border px-4 py-4 text-left transition",
        active ? "shadow-lg" : "hover:-translate-y-[1px]",
      ].join(" ")}
      style={{
        borderColor: active ? "var(--accent)" : "var(--panel-border)",
        background: active
          ? "color-mix(in oklab, var(--accent) 14%, var(--panel-bg))"
          : "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        color: "var(--text)",
      }}
    >
      <div className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
        {active ? "Selected" : "Available"}
      </div>
      <div className="mt-2 text-lg font-semibold tracking-[-0.02em]">
        {label}
      </div>
      <p className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
        {description}
      </p>
    </button>
  );
}

export default function FlowBuilderPage() {
  const [mode, setModeState] = useState<FlowBuilderMode>(() =>
    resolveInitialFlowBuilderMode()
  );

  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncFromLocation = () => {
      const routeMode = parseFlowBuilderMode(window.location.search);
      const hasModeQuery = hasFlowBuilderModeQuery(window.location.search);
      const nextMode = routeMode
        ?? (hasModeQuery
          ? DEFAULT_FLOW_BUILDER_MODE
          : readPersistedFlowBuilderMode() ?? DEFAULT_FLOW_BUILDER_MODE);

      setModeState((current) => (current === nextMode ? current : nextMode));
      persistFlowBuilderMode(nextMode);
      canonicalizeFlowBuilderLocation(nextMode);
    };

    syncFromLocation();
    window.addEventListener("popstate", syncFromLocation);

    return () => {
      window.removeEventListener("popstate", syncFromLocation);
    };
  }, []);

  useEffect(() => {
    persistFlowBuilderMode(mode);
  }, [mode]);

  const currentRoute = useMemo(() => {
    if (typeof window === "undefined") {
      return getFlowBuilderPath(mode);
    }

    return `${window.location.pathname}${window.location.search}`;
  }, [mode]);

  const handleSelectMode = useCallback(
    (nextMode: FlowBuilderMode) => {
      setModeState(nextMode);
      persistFlowBuilderMode(nextMode);

      if (typeof window === "undefined") return;

      const nextPath = getFlowBuilderPath(nextMode);
      const currentPath = `${window.location.pathname}${window.location.search}`;
      if (currentPath !== nextPath) {
        window.history.pushState({}, "", nextPath);
      }
    },
    []
  );

  return (
    <div
      data-testid="flow-builder-page"
      data-flow-builder-mode={mode}
      className="flex h-full min-h-0 w-full flex-col gap-5 overflow-auto p-[var(--card-pad)]"
    >
      <div
        className="rounded-[24px] border p-5 sm:p-6"
        style={{
          borderColor: "var(--panel-border)",
          background:
            "linear-gradient(160deg, color-mix(in oklab, var(--panel-bg) 92%, transparent), color-mix(in oklab, var(--panel-bg) 84%, transparent))",
        }}
      >
        <div
          className="inline-flex items-center rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.24em]"
          style={{
            borderColor: "var(--chip-border)",
            background: "color-mix(in oklab, var(--chip-bg) 90%, transparent)",
            color: "var(--muted)",
          }}
        >
          Spec first
        </div>
        <div className="mt-4 max-w-3xl space-y-3">
          <h1 className="text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">
            Flow Builder
          </h1>
          <p className="max-w-2xl text-sm leading-6 sm:text-[15px]" style={{ color: "var(--muted)" }}>
            This entry seam is for shaping workflow structure before execution.
            The job here is to make the plan explicit, inspectable, and
            validated, not to pretend the runnable path already exists.
          </p>
        </div>

        <div className="mt-5 rounded-[20px] border px-4 py-4" style={{ borderColor: "var(--panel-border)" }}>
          <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
            Current route
          </div>
          <code
            data-testid="flow-builder-route"
            className="mt-2 block rounded-[14px] border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--panel-border)",
              background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
              color: "var(--text)",
            }}
          >
            {currentRoute}
          </code>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ModeButton
          active={mode === "expertise"}
          description="Start from the outcome, constraints, and vocabulary. We surface missing steps, assumptions, and validation gates before anything can become runnable."
          label="Build from expertise"
          onClick={() => handleSelectMode("expertise")}
          testId="flow-builder-mode-expertise"
        />
        <ModeButton
          active={mode === "process"}
          description="Start from the steps you already know. We normalize the sequence into a draft spec and mark the gaps before execution is allowed."
          label="Build from process"
          onClick={() => handleSelectMode("process")}
          testId="flow-builder-mode-process"
        />
      </div>

      <div
        className="rounded-[20px] border p-4 sm:p-5"
        style={{
          borderColor: "var(--panel-border)",
          background:
            "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        }}
      >
        <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
          Pre-execution contract
        </div>
        <ul className="mt-3 grid gap-2 text-sm leading-6" style={{ color: "var(--text)" }}>
          <li>Interview the intent before draft structure hardens.</li>
          <li>Normalize the plan into explicit steps and named gaps.</li>
          <li>Validate the flow before any runnable execution path is exposed.</li>
        </ul>
      </div>
    </div>
  );
}
