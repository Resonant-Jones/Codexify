import { Check } from "lucide-react";

type FlowBuilderStage = {
  id: string;
  label: string;
  description: string;
  chip: string;
};

type FlowBuilderParameterRailProps = {
  onSelectStage: (stageId: string) => void;
  selectedStageId: string;
  stages: FlowBuilderStage[];
};

export default function FlowBuilderParameterRail({
  onSelectStage,
  selectedStageId,
  stages,
}: FlowBuilderParameterRailProps) {
  return (
    <aside
      data-testid="flow-builder-parameter-rail"
      className="flex h-full min-h-[560px] flex-col overflow-hidden rounded-[var(--tile-radius,19px)] border"
      style={{
        borderColor: "var(--panel-border)",
        background:
          "linear-gradient(180deg, color-mix(in oklab, var(--panel-bg) 95%, transparent), color-mix(in oklab, var(--panel-bg) 90%, transparent))",
        boxShadow: "inset 0 1px 0 color-mix(in oklab, white 6%, transparent)",
      }}
    >
      <div className="border-b border-[var(--panel-border)] p-4">
        <div className="text-[11px] uppercase tracking-[0.24em]" style={{ color: "var(--muted)" }}>
          Pick your parameters
        </div>
        <p className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
          Choose the stage that should seed the current draft. The selection stays local to this view.
        </p>
      </div>

      <div className="flex-1 space-y-2 p-4">
        {stages.map((stage, index) => {
          const active = stage.id === selectedStageId;

          return (
            <button
              key={stage.id}
              type="button"
              data-testid={`flow-builder-stage-${stage.id}`}
              aria-pressed={active}
              onClick={() => onSelectStage(stage.id)}
              className={[
                "flex w-full items-start gap-3 rounded-[var(--tile-radius,19px)] border px-4 py-4 text-left transition",
                active ? "shadow-[0_14px_32px_rgba(0,0,0,0.22)]" : "hover:-translate-y-[1px]",
              ].join(" ")}
              style={{
                borderColor: active ? "var(--accent)" : "var(--panel-border)",
                background: active
                  ? "color-mix(in oklab, var(--accent) 14%, var(--panel-bg))"
                  : "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
              }}
            >
              <span
                className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold"
                style={{
                  borderColor: active ? "var(--accent-strong)" : "var(--chip-border)",
                  background: active
                    ? "color-mix(in oklab, var(--accent) 24%, transparent)"
                    : "color-mix(in oklab, var(--chip-bg) 90%, transparent)",
                  color: active ? "var(--text)" : "var(--muted)",
                }}
              >
                {active ? <Check className="h-4 w-4" /> : stage.chip}
              </span>

              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold tracking-[-0.02em]">{stage.label}</span>
                  <span
                    className="rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.2em]"
                    style={{
                      borderColor: "var(--chip-border)",
                      background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
                      color: "var(--muted)",
                    }}
                  >
                    {index + 1}
                  </span>
                </span>
                <span className="mt-2 block text-sm leading-6" style={{ color: "var(--muted)" }}>
                  {stage.description}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
