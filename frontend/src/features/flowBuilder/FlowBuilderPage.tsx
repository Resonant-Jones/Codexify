import React, { useCallback, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import Textarea from "@/components/ui/textarea";

import FlowBuilderChatDock from "./components/FlowBuilderChatDock";
import FlowBuilderGraphCanvas from "./components/FlowBuilderGraphCanvas";
import FlowBuilderParameterRail from "./components/FlowBuilderParameterRail";
import {
  getCurrentNodeSelection,
  getGraphVisibleNodes,
  getOrderedStageProgress,
  getSupportChatContextSummary,
  getValidationSummary,
  useFlowDraftState,
} from "./hooks/useFlowDraftState";
import {
  DEFAULT_FLOW_BUILDER_MODE,
  getFlowBuilderPath,
  hasFlowBuilderModeQuery,
  parseFlowBuilderMode,
  type FlowBuilderMode,
} from "./flowBuilderRoute";
import type { FlowDraftContent, FlowDraftStageId } from "./model/flowDraft";

const FLOW_BUILDER_LAST_MODE_STORAGE_KEY = "cfy.flowBuilder.mode";

type FlowBuilderPageProps = {
  onReturnToGuardian?: () => void;
};

function isFlowBuilderPathname(pathname: string): boolean {
  return pathname.startsWith("/flow-builder");
}

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
  if (!isFlowBuilderPathname(window.location.pathname)) return;

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
        "rounded-[var(--tile-radius,19px)] border px-4 py-3 text-left transition",
        active ? "shadow-[0_16px_30px_rgba(0,0,0,0.22)]" : "hover:-translate-y-[1px]",
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
        Source mode
      </div>
      <div className="mt-1 text-sm font-semibold tracking-[-0.02em]">{label}</div>
      <p className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
        {description}
      </p>
    </button>
  );
}

export default function FlowBuilderPage({
  onReturnToGuardian,
}: FlowBuilderPageProps = {}) {
  const initialMode = resolveInitialFlowBuilderMode();
  const { actions, draft, view } = useFlowDraftState(initialMode);

  const handleReturnToGuardian = useCallback(() => {
    if (onReturnToGuardian) {
      onReturnToGuardian();
      return;
    }

    if (typeof window === "undefined") return;

    window.history.pushState({}, "", "/chat");
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, [onReturnToGuardian]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncFromLocation = () => {
      if (!isFlowBuilderPathname(window.location.pathname)) {
        return;
      }

      const routeMode = parseFlowBuilderMode(window.location.search);
      const hasModeQuery = hasFlowBuilderModeQuery(window.location.search);
      const nextMode = routeMode
        ?? (hasModeQuery
          ? DEFAULT_FLOW_BUILDER_MODE
          : readPersistedFlowBuilderMode() ?? DEFAULT_FLOW_BUILDER_MODE);

      actions.setMode(nextMode);
      canonicalizeFlowBuilderLocation(nextMode);
    };

    syncFromLocation();
    window.addEventListener("popstate", syncFromLocation);

    return () => {
      window.removeEventListener("popstate", syncFromLocation);
    };
  }, [actions]);

  useEffect(() => {
    persistFlowBuilderMode(view.mode);
    canonicalizeFlowBuilderLocation(view.mode);
  }, [view.mode]);

  const currentRoute = useMemo(() => {
    if (typeof window === "undefined") {
      return getFlowBuilderPath(view.mode);
    }

    if (isFlowBuilderPathname(window.location.pathname)) {
      return getFlowBuilderPath(view.mode);
    }

    return `${window.location.pathname}${window.location.search}`;
  }, [view.mode]);

  const currentSelection = useMemo(
    () => getCurrentNodeSelection(draft, view),
    [draft, view]
  );
  const stageProgress = useMemo(() => getOrderedStageProgress(draft, view), [draft, view]);
  const graphVisibleNodes = useMemo(() => getGraphVisibleNodes(draft), [draft]);
  const validationSummary = useMemo(() => getValidationSummary(draft), [draft]);
  const supportChatContext = useMemo(
    () => getSupportChatContextSummary(draft, view),
    [draft, view]
  );

  const handleSelectMode = useCallback(
    (nextMode: FlowBuilderMode) => {
      actions.setMode(nextMode);

      if (typeof window === "undefined") return;
      if (!isFlowBuilderPathname(window.location.pathname)) return;

      const nextPath = getFlowBuilderPath(nextMode);
      const currentPath = `${window.location.pathname}${window.location.search}`;
      if (currentPath !== nextPath) {
        window.history.pushState({}, "", nextPath);
      }
    },
    [actions]
  );

  const handleSelectStage = useCallback(
    (stageId: FlowDraftStageId) => {
      actions.selectStage(stageId);
    },
    [actions]
  );

  const handleSelectNode = useCallback(
    (nodeId: string) => {
      actions.selectNode(nodeId);
    },
    [actions]
  );

  const handleMoveNode = useCallback(
    (nodeId: string, direction: "up" | "down") => {
      actions.moveNode(nodeId, direction);
    },
    [actions]
  );

  const handleToggleSupportDock = useCallback(() => {
    actions.toggleSupportChatDock();
  }, [actions]);

  const handleDraftFieldChange = useCallback(
    (field: keyof FlowDraftContent, value: string) => {
      actions.updateDraftFields({ [field]: value } as Partial<FlowDraftContent>);
    },
    [actions]
  );

  return (
    <div
      data-testid="flow-builder-page"
      data-flow-builder-mode={view.mode}
      className="flex h-full min-h-0 w-full flex-col gap-5 overflow-auto p-[var(--card-pad)]"
    >
      <div
        className="mx-auto flex w-full max-w-[1680px] flex-1 flex-col overflow-hidden rounded-[var(--tile-radius,19px)] border"
        style={{
          borderColor: "var(--panel-border)",
          background:
            "linear-gradient(180deg, color-mix(in oklab, var(--panel-bg) 96%, transparent), color-mix(in oklab, var(--panel-bg) 88%, transparent))",
          boxShadow:
            "0 24px 60px color-mix(in oklab, black 26%, transparent), inset 0 1px 0 color-mix(in oklab, white 8%, transparent)",
        }}
      >
        <header className="flex flex-col gap-4 border-b border-[var(--panel-border)] p-5 sm:p-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
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
            <div className="max-w-3xl space-y-3">
              <h1 className="text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">
                Flow Builder
              </h1>
              <p className="max-w-2xl text-sm leading-6 sm:text-[15px]" style={{ color: "var(--muted)" }}>
                Authoring, inspection, validation, and draft shaping happen here before anything
                becomes runnable. The builder keeps that boundary visible on purpose.
              </p>
            </div>
            <code
              data-testid="flow-builder-route"
              className="inline-flex max-w-full rounded-[14px] border px-3 py-2 text-xs sm:text-sm"
              style={{
                borderColor: "var(--panel-border)",
                background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
                color: "var(--text)",
              }}
            >
              {currentRoute}
            </code>
          </div>

          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <ModeButton
              active={view.mode === "process"}
              description="Start from the steps you already know."
              label="Process"
              onClick={() => handleSelectMode("process")}
              testId="flow-builder-mode-process"
            />
            <ModeButton
              active={view.mode === "expertise"}
              description="Start from the outcome and constraints."
              label="Expertise"
              onClick={() => handleSelectMode("expertise")}
              testId="flow-builder-mode-expertise"
            />
            <Button
              type="button"
              variant="ghost"
              onClick={handleReturnToGuardian}
              data-testid="flow-builder-return-guardian"
              className="shrink-0 rounded-full px-4"
            >
              Back to Guardian
            </Button>
          </div>
        </header>

        <div className="grid flex-1 gap-4 p-4 sm:p-6 xl:grid-cols-[minmax(240px,280px)_minmax(0,1fr)_minmax(280px,340px)]">
          <FlowBuilderParameterRail
            currentSelection={currentSelection}
            onSelectStage={handleSelectStage}
            stageProgress={stageProgress}
            validationSummary={validationSummary}
          />

          <FlowBuilderGraphCanvas
            currentSelection={currentSelection}
            graphVisibleNodes={graphVisibleNodes}
            modeLabel={view.mode === "expertise" ? "Expertise" : "Process"}
            onMoveNode={handleMoveNode}
            onSelectNode={handleSelectNode}
            validationSummary={validationSummary}
          />

          <FlowBuilderChatDock
            onToggleOpen={handleToggleSupportDock}
            open={view.supportChatOpen}
            supportChatContext={supportChatContext}
            validationSummary={validationSummary}
          />
        </div>

        {view.mode === "expertise" ? (
          <section
            data-testid="flow-builder-draft-spec"
            className="border-t border-[var(--panel-border)] p-4 sm:p-6"
            style={{
              background:
                "linear-gradient(180deg, color-mix(in oklab, var(--panel-bg) 94%, transparent), color-mix(in oklab, var(--panel-bg) 90%, transparent))",
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                Draft specification artifact
              </div>
              <span
                className="rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.2em]"
                style={{
                  borderColor: "var(--chip-border)",
                  background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
                  color: "var(--muted)",
                }}
              >
                Non-runtime
              </span>
              <span
                className="rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.2em]"
                style={{
                  borderColor: "var(--chip-border)",
                  background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
                  color: "var(--muted)",
                }}
              >
                Draft only
              </span>
            </div>

            <div className="mt-3 max-w-2xl space-y-2">
              <h2 className="text-lg font-semibold tracking-[-0.02em]">
                {draft.meta.title}
              </h2>
              <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
                This stub keeps the expertise lane honest: it makes the specification visible and
                editable without claiming compile or execution support.
              </p>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-[16px] border px-3 py-3" style={{ borderColor: "var(--panel-border)" }}>
                <div className="text-[11px] uppercase tracking-[0.2em]" style={{ color: "var(--muted)" }}>
                  Source
                </div>
                <div className="mt-2 text-sm font-medium">Build from expertise</div>
              </div>
              <div className="rounded-[16px] border px-3 py-3" style={{ borderColor: "var(--panel-border)" }}>
                <div className="text-[11px] uppercase tracking-[0.2em]" style={{ color: "var(--muted)" }}>
                  Runtime
                </div>
                <div className="mt-2 text-sm font-medium">{draft.meta.runtimeSupport}</div>
              </div>
              <div className="rounded-[16px] border px-3 py-3" style={{ borderColor: "var(--panel-border)" }}>
                <div className="text-[11px] uppercase tracking-[0.2em]" style={{ color: "var(--muted)" }}>
                  Status
                </div>
                <div className="mt-2 text-sm font-medium">{draft.meta.status}</div>
              </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Objective
                </div>
                <Textarea
                  data-testid="flow-builder-draft-objective"
                  className="mt-2 min-h-28"
                  value={draft.content.objective}
                  onChange={(event) => handleDraftFieldChange("objective", event.target.value)}
                />
              </label>

              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Assumptions
                </div>
                <Textarea
                  data-testid="flow-builder-draft-assumptions"
                  className="mt-2 min-h-28"
                  value={draft.content.assumptions}
                  onChange={(event) => handleDraftFieldChange("assumptions", event.target.value)}
                />
              </label>

              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Unknowns
                </div>
                <Textarea
                  data-testid="flow-builder-draft-unknowns"
                  className="mt-2 min-h-28"
                  value={draft.content.unknowns}
                  onChange={(event) => handleDraftFieldChange("unknowns", event.target.value)}
                />
              </label>

              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Validation questions
                </div>
                <Textarea
                  data-testid="flow-builder-draft-validation-questions"
                  className="mt-2 min-h-28"
                  value={draft.content.validationQuestions}
                  onChange={(event) =>
                    handleDraftFieldChange("validationQuestions", event.target.value)
                  }
                />
              </label>
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
