type FlowBuilderStage = {
  id: string;
  label: string;
  description: string;
  chip: string;
};

type FlowBuilderGraphCanvasProps = {
  modeLabel: string;
  selectedStage: FlowBuilderStage;
  selectedStageIndex: number;
  stages: FlowBuilderStage[];
};

type FlowNode = {
  label: string;
  note: string;
  active?: boolean;
  compact?: boolean;
  x: string;
  y: string;
};

function NodeCard({ node }: { node: FlowNode }) {
  return (
    <div
      className={[
        "absolute -translate-x-1/2 -translate-y-1/2 rounded-[var(--tile-radius,19px)] border px-4 py-3 text-left backdrop-blur-sm",
        node.active ? "shadow-[0_24px_42px_rgba(0,0,0,0.3)]" : "shadow-[0_10px_24px_rgba(0,0,0,0.16)]",
        node.compact ? "min-w-[180px]" : "min-w-[240px]",
      ].join(" ")}
      style={{
        left: node.x,
        top: node.y,
        borderColor: node.active ? "var(--accent)" : "var(--panel-border)",
        background: node.active
          ? "color-mix(in oklab, var(--accent) 15%, var(--panel-bg))"
          : "color-mix(in oklab, var(--panel-bg) 90%, transparent)",
      }}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{
            backgroundColor: node.active ? "var(--accent-strong)" : "var(--accent-weak)",
            boxShadow: node.active ? "0 0 0 6px color-mix(in oklab, var(--accent) 12%, transparent)" : "none",
          }}
        />
        <div className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
          {node.active ? "Seeded state" : "Derived node"}
        </div>
      </div>
      <div className="mt-2 text-sm font-semibold tracking-[-0.02em]">{node.label}</div>
      <div className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
        {node.note}
      </div>
    </div>
  );
}

export default function FlowBuilderGraphCanvas({
  modeLabel,
  selectedStage,
  selectedStageIndex,
  stages,
}: FlowBuilderGraphCanvasProps) {
  const previousStage = stages[Math.max(0, selectedStageIndex - 1)] ?? selectedStage;
  const nextStage = stages[Math.min(stages.length - 1, selectedStageIndex + 1)] ?? selectedStage;
  const reviewStage = stages[stages.length - 1] ?? selectedStage;

  const nodes: FlowNode[] = [
    {
      label: selectedStage.label,
      note: selectedStage.description,
      active: true,
      x: "50%",
      y: "24%",
    },
    {
      label: previousStage.label,
      note: "The upstream choice that feeds the current seed.",
      compact: true,
      x: "28%",
      y: "43%",
    },
    {
      label: nextStage.label,
      note: "The next visible step in the draft chain.",
      compact: true,
      x: "72%",
      y: "43%",
    },
    {
      label: "Validation Gate",
      note: "Keep the unresolved edges visible before anything is treated as final.",
      compact: true,
      x: "38%",
      y: "68%",
    },
    {
      label: reviewStage.label,
      note: "This remains a draft surface for inspection and review.",
      compact: true,
      x: "62%",
      y: "68%",
    },
  ];

  return (
    <section
      data-testid="flow-builder-graph-canvas"
      className="relative flex min-h-[560px] flex-col overflow-hidden rounded-[var(--tile-radius,19px)] border"
      style={{
        borderColor: "var(--panel-border)",
        background:
          "linear-gradient(180deg, color-mix(in oklab, var(--panel-bg) 92%, transparent), color-mix(in oklab, var(--panel-bg) 84%, transparent))",
        boxShadow: "inset 0 1px 0 color-mix(in oklab, white 6%, transparent)",
      }}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, color-mix(in oklab, var(--muted) 28%, transparent) 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 50% 15%, color-mix(in oklab, var(--accent) 10%, transparent), transparent 44%), radial-gradient(circle at 50% 78%, color-mix(in oklab, var(--accent) 14%, transparent), transparent 40%)",
        }}
      />

      <div className="relative z-10 border-b border-[var(--panel-border)] p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="text-[11px] uppercase tracking-[0.24em]" style={{ color: "var(--muted)" }}>
            Graph canvas
          </div>
          <span
            className="rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.2em]"
            style={{
              borderColor: "var(--chip-border)",
              background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
              color: "var(--muted)",
            }}
          >
            {modeLabel}
          </span>
        </div>
        <div className="mt-2 max-w-2xl space-y-2">
          <h2 className="text-lg font-semibold tracking-[-0.02em] sm:text-xl">
            Seeded from {selectedStage.label}
          </h2>
          <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
            The graph is a drafting surface, not an execution surface. It keeps the current stage,
            its neighbors, and the review boundary legible in one view.
          </p>
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden px-4 py-6 sm:px-6 sm:py-8">
        <svg
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 1000 720"
          preserveAspectRatio="none"
        >
          <g stroke="color-mix(in oklab, var(--accent-weak) 45%, transparent)" strokeWidth="2">
            <path d="M500 164 L500 278" />
            <path d="M500 278 L278 314" />
            <path d="M500 278 L722 314" />
            <path d="M278 314 L386 486" />
            <path d="M722 314 L614 486" />
            <path d="M500 278 L500 540" strokeDasharray="8 10" />
          </g>
          <g fill="color-mix(in oklab, var(--accent) 70%, transparent)">
            <circle cx="500" cy="164" r="7" />
            <circle cx="500" cy="278" r="7" />
            <circle cx="278" cy="314" r="6" />
            <circle cx="722" cy="314" r="6" />
            <circle cx="386" cy="486" r="6" />
            <circle cx="614" cy="486" r="6" />
          </g>
        </svg>

        {nodes.map((node, index) => (
          <NodeCard key={`${node.label}-${index}`} node={node} />
        ))}

        <div
          className="absolute bottom-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--tile-radius,19px)] border px-4 py-3 backdrop-blur-sm"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in oklab, var(--panel-bg) 88%, transparent)",
          }}
        >
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
              Current seed
            </div>
            <div className="mt-1 text-sm font-medium">{selectedStage.label}</div>
          </div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Stage {selectedStageIndex + 1}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Draft only
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
