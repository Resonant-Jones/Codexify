/**
 * BetaGate - Reusable beta feature gate UI state
 *
 * A controlled overlay state for features that are intentionally unavailable
 * in the current beta build. Visually replaces or covers unfinished content.
 */

import React from "react";

export interface BetaGateProps {
  /** Title of the gated feature */
  title: string;
  /** Short description of what the feature is */
  description: string;
  /** Optional reason or status note (e.g., "Coming soon", "Under development") */
  statusNote?: string;
  /** Optional className for additional styling */
  className?: string;
}

/**
 * BetaGate - A controlled overlay state for unfinished beta features.
 *
 * Use this to visually block off features that are intentionally unavailable
 * in the current beta build instead of appearing broken or silently incomplete.
 *
 * @example
 * ```tsx
 * <BetaGate
 *   title="Image Generation"
 *   description="Generate images from text prompts using AI"
 *   statusNote="Coming soon"
 * />
 * ```
 */
export function BetaGate({
  title,
  description,
  statusNote,
  className = "",
}: BetaGateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center ${className}`}
      style={{
        background: "var(--surface-soft)",
        borderRadius: "var(--card-radius)",
        border: "1px solid var(--panel-border)",
        minHeight: "200px",
      }}
    >
      {/* Beta pill */}
      <span
        className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide uppercase mb-4"
        style={{
          background: "var(--accent)",
          color: "var(--text-on-accent)",
          opacity: 0.9,
          letterSpacing: "0.05em",
        }}
      >
        Beta
      </span>

      {/* Feature title */}
      <h3
        className="text-lg font-semibold mb-2"
        style={{ color: "var(--text)" }}
      >
        {title}
      </h3>

      {/* Description */}
      <p
        className="text-sm max-w-[280px] mb-3"
        style={{ color: "var(--muted)" }}
      >
        {description}
      </p>

      {/* Status note */}
      {statusNote && (
        <span
          className="text-xs px-3 py-1 rounded-full"
          style={{
            background: "var(--chip-bg)",
            color: "var(--text-subtle)",
            border: "1px solid var(--chip-border)",
          }}
        >
          {statusNote}
        </span>
      )}
    </div>
  );
}

export default BetaGate;
