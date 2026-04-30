import { ChevronDown, ChevronUp, Move } from "lucide-react";

import {
  type FlowDraftNode,
  type FlowDraftSelection,
  type FlowDraftValidationSummary,
} from "../model/flowDraft";

type FlowBuilderGraphCanvasProps = {
  currentSelection: FlowDraftSelection;
  graphVisibleNodes: FlowDraftNode[];
  modeLabel: string;
  onMoveNode: (nodeId: string, direction: "up" | "down") => void;
  onSelectNode: (nodeId: string) => void;
  validationSummary: FlowDraftValidationSummary;
};

type GraphPosition = {
  left: string;
  top: string;
  x: number;
  y: number;
};

const GRAPH_POSITIONS: GraphPosition[] = [
  { left: "50%", top: "18%", x: 500, y: 130 },
  { left: "27%", top: "34%", x: 270, y: 250 },
  { left: "73%", top: "34%", x: 730, y: 250 },
  { left: "34%", top: "56%", x: 340, y: 400 },
  { left: "50%", top: "62%", x: 500, y: 450 },
  { left: "66%", top: "56%", x: 660, y: 400 },
  { left: "50%", top: "80%", x: 500, y: 570 },
];

function getNodeFieldPreview(node: FlowDraftNode): string {
  const entries = Object.entries(node.fields);
  if (entries.length === 0) {
    return node.summary;
  }

  return entries
    .slice(0, 2)
    .map(([field, value]) => `${field}: ${value}`)
    .join(" · ");
}

function NodeCard({
  node,
  active,
  position,
  onMoveNode,
  onSelectNode,
}: {
  active: boolean;
  node: FlowDraftNode;
  onMoveNode: (nodeId: string, direction: "up" | "down") => void;
  onSelectNode: (nodeId: string) => void;
  position: GraphPosition;
}) {
  return (
    <div
      data-testid={`flow-builder-graph-node-${node.id}`}
      role="button"
      tabIndex={0}
      aria-pressed={active}
      onClick={() => onSelectNode(node.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelectNode(node.id);
        }
      }}
      className={[
        "absolute -translate-x-1/2 -translate-y-1/2 rounded-[var(--tile-radius,19px)] border px-4 py-3 text-left backdrop-blur-sm transition",
        active ? "shadow-[0_24px_42px_rgba(0,0,0,0.3)]" : "shadow-[0_10px_24px_rgba(0,0,0,0.16)]",
        node.kind === "validation" ? "min-w-[210px]" : "min-w-[240px]",
      ].join(" ")}
      style={{
        left: position.left,
        top: position.top,
        borderColor: active ? "var(--accent)" : "var(--panel-border)",
        background: active
          ? "color-mix(in oklab, var(--accent) 15%, var(--panel-bg))"
          : "color-mix(in oklab, var(--panel-bg) 90%, transparent)",
      }}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{
            backgroundColor: active ? "var(--accent-strong)" : "var(--accent-weak)",
            boxShadow: active ? "0 0 0 6px color-mix(in oklab, var(--accent) 12%, transparent)" : "none",
          }}
        />
        <div className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
          {node.kind}
        </div>
      </div>
      <div className="mt-2 text-sm font-semibold tracking-[-0.02em]">{node.label}</div>
      <div className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
        {node.summary}
      </div>
      <div className="mt-2 text-xs leading-5" style={{ color: "var(--muted)" }}>
        {getNodeFieldPreview(node)}
      </div>

      {active ? (
        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            data-testid={`flow-builder-node-move-up-${node.id}`}
            onClick={(event) => {
              event.stopPropagation();
              onMoveNode(node.id, "up");
            }}
            className="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] transition hover:-translate-y-[1px]"
            style={{
              borderColor: "var(--panel-border)",
              background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
            }}
          >
            <ChevronUp className="h-3.5 w-3.5" />
            Up
          </button>
          <button
            type="button"
            data-testid={`flow-builder-node-move-down-${node.id}`}
            onClick={(event) => {
              event.stopPropagation();
              onMoveNode(node.id, "down");
            }}
            className="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] transition hover:-translate-y-[1px]"
            style={{
              borderColor: "var(--panel-border)",
              background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
            }}
          >
            <ChevronDown className="h-3.5 w-3.5" />
            Down
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default function FlowBuilderGraphCanvas({
  currentSelection,
  graphVisibleNodes,
  modeLabel,
  onMoveNode,
  onSelectNode,
  validationSummary,
}: FlowBuilderGraphCanvasProps) {
  const positions = graphVisibleNodes.map((_, index) => GRAPH_POSITIONS[index] ?? GRAPH_POSITIONS[GRAPH_POSITIONS.length - 1]);

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
          <span
            className="rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.2em]"
            style={{
              borderColor: "var(--chip-border)",
              background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
              color: "var(--muted)",
            }}
          >
            Validation {validationSummary.label}
          </span>
        </div>
        <div className="mt-2 max-w-2xl space-y-2">
          <h2 className="text-lg font-semibold tracking-[-0.02em] sm:text-xl">
            Seeded from {currentSelection.stage.label}
          </h2>
          <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
            The graph is a drafting surface, not an execution surface. It keeps the current stage,
            its neighboring structure, and the review boundary legible in one view.
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
            {graphVisibleNodes.slice(0, -1).map((node, index) => {
              const from = positions[index];
              const to = positions[index + 1] ?? positions[index];
              return <line key={`${node.id}-edge`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} />;
            })}
          </g>
          <g fill="color-mix(in oklab, var(--accent) 70%, transparent)">
            {positions.map((position, index) => (
              <circle key={`${index}-${position.x}-${position.y}`} cx={position.x} cy={position.y} r="6" />
            ))}
          </g>
        </svg>

        {graphVisibleNodes.map((node, index) => (
          <NodeCard
            key={node.id}
            active={node.id === currentSelection.nodeId}
            node={node}
            onMoveNode={onMoveNode}
            onSelectNode={onSelectNode}
            position={positions[index] ?? GRAPH_POSITIONS[GRAPH_POSITIONS.length - 1]}
          />
        ))}

        <div
          data-testid="flow-builder-draft-order"
          className="absolute bottom-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--tile-radius,19px)] border px-4 py-3 backdrop-blur-sm"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in oklab, var(--panel-bg) 88%, transparent)",
          }}
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
              <Move className="h-3.5 w-3.5" />
              Draft order
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-sm">
              {graphVisibleNodes.map((node, index) => (
                <span
                  key={node.id}
                  data-testid={`flow-builder-draft-order-item-${node.id}`}
                  className="rounded-full border px-2.5 py-1"
                  style={{
                    borderColor: node.id === currentSelection.nodeId ? "var(--accent)" : "var(--panel-border)",
                    background:
                      node.id === currentSelection.nodeId
                        ? "color-mix(in oklab, var(--accent) 14%, var(--panel-bg))"
                        : "color-mix(in oklab, var(--chip-bg) 86%, transparent)",
                  }}
                >
                  {index + 1}. {node.label}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              {currentSelection.stage.label}
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              Draft only
            </span>
            <span className="rounded-full border px-2 py-1" style={{ borderColor: "var(--panel-border)" }}>
              {validationSummary.label}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
