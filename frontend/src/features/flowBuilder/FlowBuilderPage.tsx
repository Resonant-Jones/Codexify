import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import Textarea from "@/components/ui/textarea";

import FlowBuilderChatDock from "./components/FlowBuilderChatDock";
import FlowBuilderGraphCanvas from "./components/FlowBuilderGraphCanvas";
import FlowBuilderParameterRail from "./components/FlowBuilderParameterRail";
import {
  DEFAULT_FLOW_BUILDER_MODE,
  getFlowBuilderPath,
  hasFlowBuilderModeQuery,
  parseFlowBuilderMode,
  type FlowBuilderMode,
} from "./flowBuilderRoute";
import {
  createFlowBuilderExpertiseDraft,
  type FlowBuilderExpertiseDraft,
} from "./flowBuilderDraft";

const FLOW_BUILDER_LAST_MODE_STORAGE_KEY = "cfy.flowBuilder.mode";

type FlowBuilderPageProps = {
  onReturnToGuardian?: () => void;
};

type FlowBuilderStage = {
  id: string;
  label: string;
  description: string;
  chip: string;
};

const FLOW_BUILDER_STAGES: FlowBuilderStage[] = [
  {
    id: "select-source",
    label: "Select Source",
    description: "Choose the input seam that should anchor the first draft.",
    chip: "01",
  },
  {
    id: "define-constraints",
    label: "Define Constraints",
    description: "Set the bounds, limits, and non-negotiables that shape the draft.",
    chip: "02",
  },
  {
    id: "set-outcomes",
    label: "Set Outcomes",
    description: "Name the intended result before the flow starts to harden.",
    chip: "03",
  },
  {
    id: "add-steps",
    label: "Add Steps",
    description: "Lay out the explicit steps that make the plan inspectable.",
    chip: "04",
  },
  {
    id: "insert-conditions",
    label: "Insert Conditions",
    description: "Mark the branch points where the draft needs a choice or guardrail.",
    chip: "05",
  },
  {
    id: "validation-gates",
    label: "Validation Gates",
    description: "Keep the checks visible so unresolved edges stay honest.",
    chip: "06",
  },
  {
    id: "review-validate",
    label: "Review & Validate",
    description: "Shape the handoff into a readable artifact for review.",
    chip: "07",
  },
];

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
  const [mode, setModeState] = useState<FlowBuilderMode>(initialMode);
  const [selectedStageId, setSelectedStageId] = useState<FlowBuilderStage["id"]>(
    initialMode === "expertise" ? "define-constraints" : "select-source"
  );
  const [assistantDockOpen, setAssistantDockOpen] = useState(true);
  const [expertiseDraft, setExpertiseDraft] = useState<FlowBuilderExpertiseDraft | null>(
    () => (initialMode === "expertise" ? createFlowBuilderExpertiseDraft() : null)
  );

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

      setModeState((current) => (current === nextMode ? current : nextMode));
      persistFlowBuilderMode(nextMode);
      if (nextMode === "expertise") {
        setExpertiseDraft((current) => current ?? createFlowBuilderExpertiseDraft());
      }
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

    if (isFlowBuilderPathname(window.location.pathname)) {
      return getFlowBuilderPath(mode);
    }

    return `${window.location.pathname}${window.location.search}`;
  }, [mode]);

  const selectedStageIndex = useMemo(() => {
    const index = FLOW_BUILDER_STAGES.findIndex((stage) => stage.id === selectedStageId);
    return index === -1 ? 0 : index;
  }, [selectedStageId]);

  const selectedStage = FLOW_BUILDER_STAGES[selectedStageIndex] ?? FLOW_BUILDER_STAGES[0];

  const handleSelectMode = useCallback(
    (nextMode: FlowBuilderMode) => {
      setModeState(nextMode);
      persistFlowBuilderMode(nextMode);
      if (nextMode === "expertise") {
        setExpertiseDraft((current) => current ?? createFlowBuilderExpertiseDraft());
      }

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
              active={mode === "process"}
              description="Start from the steps you already know."
              label="Process"
              onClick={() => handleSelectMode("process")}
              testId="flow-builder-mode-process"
            />
            <ModeButton
              active={mode === "expertise"}
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
            stages={FLOW_BUILDER_STAGES}
            selectedStageId={selectedStage.id}
            onSelectStage={setSelectedStageId}
          />

          <FlowBuilderGraphCanvas
            modeLabel={mode === "expertise" ? "Expertise" : "Process"}
            selectedStage={selectedStage}
            selectedStageIndex={selectedStageIndex}
            stages={FLOW_BUILDER_STAGES}
          />

          <FlowBuilderChatDock
            modeLabel={mode === "expertise" ? "Expertise" : "Process"}
            onToggleOpen={() => setAssistantDockOpen((current) => !current)}
            open={assistantDockOpen}
            selectedStage={selectedStage}
          />
        </div>

        {mode === "expertise" && expertiseDraft ? (
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
                {expertiseDraft.title}
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
                <div className="mt-2 text-sm font-medium">{expertiseDraft.runtimeSupport}</div>
              </div>
              <div className="rounded-[16px] border px-3 py-3" style={{ borderColor: "var(--panel-border)" }}>
                <div className="text-[11px] uppercase tracking-[0.2em]" style={{ color: "var(--muted)" }}>
                  Status
                </div>
                <div className="mt-2 text-sm font-medium">{expertiseDraft.status}</div>
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
                  value={expertiseDraft.objective}
                  onChange={(event) =>
                    setExpertiseDraft((current) =>
                      current ? { ...current, objective: event.target.value } : current
                    )
                  }
                />
              </label>

              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Assumptions
                </div>
                <Textarea
                  data-testid="flow-builder-draft-assumptions"
                  className="mt-2 min-h-28"
                  value={expertiseDraft.assumptions}
                  onChange={(event) =>
                    setExpertiseDraft((current) =>
                      current ? { ...current, assumptions: event.target.value } : current
                    )
                  }
                />
              </label>

              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Unknowns
                </div>
                <Textarea
                  data-testid="flow-builder-draft-unknowns"
                  className="mt-2 min-h-28"
                  value={expertiseDraft.unknowns}
                  onChange={(event) =>
                    setExpertiseDraft((current) =>
                      current ? { ...current, unknowns: event.target.value } : current
                    )
                  }
                />
              </label>

              <label className="block">
                <div className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
                  Validation questions
                </div>
                <Textarea
                  data-testid="flow-builder-draft-validation-questions"
                  className="mt-2 min-h-28"
                  value={expertiseDraft.validationQuestions}
                  onChange={(event) =>
                    setExpertiseDraft((current) =>
                      current
                        ? { ...current, validationQuestions: event.target.value }
                        : current
                    )
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
