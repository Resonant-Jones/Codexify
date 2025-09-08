/**
 * ProviderBadge.tsx
 *
 * Lightweight, icon-only provider badge for use inside the Composer / AppShell.
 *
 * Goal:
 * - Render a compact icon representing the current provider (or a generic icon when none).
 * - Keep styling minimal so this can be placed inline (e.g. at the end of a composer toolbar)
 * - Export a small ConnectorBar utility component that renders an array of connector icons
 *   (useful for the bottom-edge connector strip you described).
 *
 * Notes / rationale (important):
 * - The original component rendered a full textual badge. That is useful in some places
 *   but too heavy for the Composer. We want an unobtrusive icon that still provides affordance
 *   and a tooltip. Clicking the icon should be handled by the parent (so we keep this component
 *   presentation-only and easy to compose).
 * - Keep CSS inline to avoid depending on global styles; this file is small and self-contained.
 * - Provide clear comments so future contributors understand the intent and tradeoffs.
 */

import React from "react";
import { usePreferredProvider } from "../hooks/usePreferredProvider";

export type ProviderBadgeProps = {
  /** optional click handler (open provider picker, etc) */
  onClick?: (ev: React.MouseEvent<HTMLButtonElement>) => void;
  /** size in px for the icon */
  size?: number;
  /** optional className passthrough */
  className?: string;
};

// small mapping for provider -> color / label (extend as needed)
const PROVIDER_META: Record<string, { label: string; color: string }> = {
  openai: { label: "OpenAI", color: "#7b61ff" },
  anthropic: { label: "Anthropic", color: "#ff7b7b" },
  local: { label: "Local", color: "#3ddc84" },
  default: { label: "default", color: "#999" },
};

/**
 * Simple icon-only provider badge.
 * Keeps visual noise low inside the Composer while preserving affordance.
 */
export const ProviderBadge: React.FC<ProviderBadgeProps> = ({
  onClick,
  size = 18,
  className,
}) => {
  const { provider } = usePreferredProvider();
  const meta = PROVIDER_META[provider || "default"] || PROVIDER_META.default;

  return (
    <button
      // keep button semantic but visually minimal
      onClick={onClick}
      title={meta.label}
      aria-label={`Provider: ${meta.label}`}
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size + 8,
        height: size + 8,
        padding: 4,
        borderRadius: 999,
        border: "none",
        background: "transparent",
        cursor: "pointer",
      }}
    >
      {/* icon: little plug / circle with provider color. Keep SVG inline so there's no icon dependency */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <rect x="3" y="3" width="18" height="18" rx="6" fill="rgba(0,0,0,0.12)" />
        <circle cx="12" cy="12" r="5" fill={meta.color} />
        <path d="M12 7v-2" stroke="#fff" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" opacity="0.9" />
      </svg>
    </button>
  );
};

export default ProviderBadge;

/**
 * ConnectorBar
 *
 * Small helper component that renders a horizontal strip of connector icons. The UI you
 * described (icons along the bottom edge like ChatGPT) can be implemented by placing this
 * component fixed to the bottom. This component intentionally does not force a fixed
 * position — that decision stays with the layout layer (AppShell) so it can be styled
 * differently per screen size.
 *
 * Usage:
 * <ConnectorBar connectors={[{id:'openai', label:'OpenAI'},{id:'local',label:'Local'}]} onSelect={...} />
 */
export type Connector = { id: string; label?: string };

export const ConnectorBar: React.FC<{
  connectors: Connector[];
  onSelect?: (id: string) => void;
}> = ({ connectors, onSelect }) => {
  return (
    <div
      // default horizontal layout; parent may override positioning (fixed/bottom/etc)
      style={{
        display: "flex",
        gap: 8,
        alignItems: "center",
        padding: 8,
        background: "transparent",
      }}
    >
      {connectors.map((c) => {
        const meta = PROVIDER_META[c.id] || PROVIDER_META.default;
        return (
          <button
            key={c.id}
            onClick={() => onSelect?.(c.id)}
            title={c.label || c.id}
            aria-label={`Connector ${c.label || c.id}`}
            style={{
              width: 44,
              height: 44,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 12,
              border: "1px solid rgba(0,0,0,0.08)",
              background: "rgba(255,255,255,0.03)",
              cursor: "pointer",
            }}
          >
            <svg width={20} height={20} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
              <circle cx="12" cy="12" r="6" fill={meta.color} />
            </svg>
          </button>
        );
      })}
    </div>
  );
};

export { ConnectorBar };
