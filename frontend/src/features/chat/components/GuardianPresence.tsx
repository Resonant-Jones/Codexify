import type { CSSProperties } from "react";

import type { RuntimeVisualState } from "@/shared/runtimeVisualState";

type PresenceState = RuntimeVisualState["key"] | "idle";

type GuardianPresenceProps = {
  guardianName?: string;
  visualState?: RuntimeVisualState | null;
  size?: "sm" | "md";
};

const STATE_COLORS: Record<
  PresenceState,
  Pick<CSSProperties, "background" | "borderColor" | "color">
> = {
  idle: {
    background: "var(--panel-bg)",
    borderColor: "var(--panel-border)",
    color: "var(--muted)",
  },
  queued: {
    background: "var(--info-surface, var(--accent-weak))",
    borderColor: "var(--accent)",
    color: "var(--info-text, var(--accent))",
  },
  starting: {
    background: "var(--info-surface, var(--accent-weak))",
    borderColor: "var(--accent)",
    color: "var(--info-text, var(--accent))",
  },
  warming: {
    background: "var(--accent-weak)",
    borderColor: "var(--accent)",
    color: "var(--accent)",
  },
  delayed: {
    background: "var(--accent-weak)",
    borderColor: "var(--accent)",
    color: "var(--accent)",
  },
  generating: {
    background: "var(--accent-strong)",
    borderColor: "var(--accent-strong)",
    color: "var(--text-on-accent, var(--text))",
  },
  complete: {
    background: "var(--accent)",
    borderColor: "var(--accent)",
    color: "var(--text-on-accent, var(--text))",
  },
  error: {
    background: "var(--danger-surface, var(--accent-weak))",
    borderColor: "var(--danger-border, var(--accent))",
    color: "var(--danger-text, var(--text))",
  },
};

export function GuardianPresence({
  guardianName,
  visualState,
  size = "sm",
}: GuardianPresenceProps) {
  const name = guardianName?.trim() ?? "";
  const initial = Array.from(name)[0]?.toLocaleUpperCase() || "G";
  const state: PresenceState = visualState?.key ?? "idle";
  const dimension =
    size === "md"
      ? "calc(var(--card-pad) * 3)"
      : "calc(var(--card-pad) * 2)";

  return (
    <div
      aria-hidden="true"
      data-testid="guardian-presence"
      data-presence-state={state}
      className="inline-flex shrink-0 items-center justify-center rounded-full border text-xs font-semibold"
      style={{
        ...STATE_COLORS[state],
        width: dimension,
        height: dimension,
      }}
    >
      {initial}
    </div>
  );
}

export default GuardianPresence;
