import * as React from "react";

import { Badge } from "@/components/ui/badge";

type FlowBuilderLane = "expertise" | "process";

type FlowBuilderLaneCard = {
  id: FlowBuilderLane;
  title: string;
  lead: string;
  detail: string;
  signals: string[];
};

const FLOW_BUILDER_LANES: FlowBuilderLaneCard[] = [
  {
    id: "expertise",
    title: "Build from expertise",
    lead: "Start with what the subject-matter expert already knows, then shape the flow around that knowledge.",
    detail:
      "Use this lane when the work starts from domain judgment, policy, or lived operational context. The goal is to capture intent, boundaries, and the desired outcome before any sequence is defined.",
    signals: ["Domain knowledge", "Guardrails", "Desired outcome"],
  },
  {
    id: "process",
    title: "Build from process",
    lead: "Start with the current workflow, then turn the known steps into a spec that can be reasoned about.",
    detail:
      "Use this lane when the work starts from an existing procedure, handoff chain, or repeatable operating path. The goal is to capture the observed order of operations before any runtime implementation exists.",
    signals: ["Workflow steps", "Inputs and outputs", "Decision points"],
  },
];

function FlowBuilderLaneButton({
  lane,
  active,
  onSelect,
}: {
  lane: FlowBuilderLaneCard;
  active: boolean;
  onSelect: (lane: FlowBuilderLane) => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      data-state={active ? "active" : "inactive"}
      data-testid={`flow-builder-lane-${lane.id}`}
      className="flex h-full min-h-[220px] flex-col justify-between rounded-3xl border p-5 text-left transition-[transform,border-color,box-shadow,background-color] duration-200 hover:-translate-y-0.5"
      style={{
        borderColor: active ? "color-mix(in oklab, var(--accent) 42%, var(--panel-border))" : "var(--panel-border)",
        background: active
          ? "color-mix(in oklab, var(--accent-weak) 14%, var(--panel-bg))"
          : "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        boxShadow: active
          ? "0 18px 42px color-mix(in oklab, var(--accent) 14%, transparent)"
          : "none",
      }}
      onClick={() => onSelect(lane.id)}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="px-2 py-1 text-[10px] uppercase tracking-[0.18em]">
            {active ? "Selected" : "Entry lane"}
          </Badge>
          <Badge variant="outline" className="px-2 py-1 text-[10px] uppercase tracking-[0.18em]">
            Pre-execution
          </Badge>
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-semibold tracking-[-0.02em]">{lane.title}</h2>
          <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
            {lane.lead}
          </p>
        </div>
      </div>

      <div className="space-y-4 pt-5">
        <p className="text-sm leading-6">{lane.detail}</p>
        <div className="flex flex-wrap gap-2">
          {lane.signals.map((signal) => (
            <span
              key={signal}
              className="rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.14em]"
              style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
            >
              {signal}
            </span>
          ))}
        </div>
      </div>
    </button>
  );
}

export default function FlowBuilderPage() {
  const [activeLane, setActiveLane] = React.useState<FlowBuilderLane>("expertise");
  const selectedLane =
    FLOW_BUILDER_LANES.find((lane) => lane.id === activeLane) ?? FLOW_BUILDER_LANES[0];

  return (
    <section
      data-testid="flow-builder-page"
      className="flex h-full min-h-0 flex-col gap-5 p-[var(--card-pad)]"
      style={{
        color: "var(--text)",
      }}
    >
      <header className="space-y-4 rounded-[28px] border p-5 sm:p-6" style={{ borderColor: "var(--panel-border)", background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)" }}>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="px-2 py-1 text-[10px] uppercase tracking-[0.2em]">
            Pre-execution spec
          </Badge>
          <Badge variant="outline" className="px-2 py-1 text-[10px] uppercase tracking-[0.2em]">
            Non-runtime
          </Badge>
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-[-0.03em] sm:text-3xl">
            Flow Builder
          </h1>
          <p className="max-w-2xl text-sm leading-6 sm:text-[15px]" style={{ color: "var(--muted)" }}>
            Choose the elicitation lane before anything is built. This surface is for
            pre-execution specification work only, so the page stays explicit about intent,
            ownership, and structure without implying any compile or execute path.
          </p>
        </div>
        <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
          No compile or execute path is wired in this seam.
        </p>
      </header>

      <div
        className="grid min-h-0 flex-1 gap-4 lg:grid-cols-2"
        role="group"
        aria-label="Flow builder entry lanes"
      >
        {FLOW_BUILDER_LANES.map((lane) => (
          <FlowBuilderLaneButton
            key={lane.id}
            lane={lane}
            active={lane.id === activeLane}
            onSelect={setActiveLane}
          />
        ))}
      </div>

      <aside
        className="rounded-[28px] border p-5 sm:p-6"
        aria-live="polite"
        data-testid="flow-builder-selection-summary"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
            Selected lane
          </span>
          <Badge variant="outline" className="px-2 py-1 text-[10px] uppercase tracking-[0.18em]">
            {selectedLane.title}
          </Badge>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-6">
          {selectedLane.detail}
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--panel-border)" }}>
            <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
              What we capture
            </div>
            <p className="mt-2 text-sm leading-6">Intent, shape, and the scope of the flow.</p>
          </div>
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--panel-border)" }}>
            <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
              What we do not claim
            </div>
            <p className="mt-2 text-sm leading-6">No runtime compile or execution support yet.</p>
          </div>
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--panel-border)" }}>
            <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: "var(--muted)" }}>
              Next spec fields
            </div>
            <p className="mt-2 text-sm leading-6">Inputs, outputs, constraints, and failure modes.</p>
          </div>
        </div>
      </aside>
    </section>
  );
}
