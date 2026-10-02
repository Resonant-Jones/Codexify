import React, { type ReactNode, useId } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import FrameCard from "@/components/surface/FrameCard";
import codexifyMark from "@/assets/brands/codexify/codexify-mark.svg";
import "./SystemSurface.css";

/** Presentation-only state role; this is not a runtime status token. */
export type SystemSurfaceTone = "neutral" | "success" | "attention" | "error";

export type SystemSurfaceProps = {
  category: string;
  statusLabel: string;
  tone?: SystemSurfaceTone;
  title: ReactNode;
  titleId?: string;
  headingLevel?: "h1" | "h2" | "h3";
  description?: ReactNode;
  metadata?: ReactNode;
  details?: ReactNode;
  actions?: ReactNode;
};

const STATE_ICONS: Record<SystemSurfaceTone, LucideIcon> = {
  neutral: Info,
  success: CheckCircle2,
  attention: AlertTriangle,
  error: AlertCircle,
};

export default function SystemSurface({
  category,
  statusLabel,
  tone = "neutral",
  title,
  titleId,
  headingLevel = "h2",
  description,
  metadata,
  details,
  actions,
}: SystemSurfaceProps) {
  const generatedTitleId = useId();
  const resolvedTitleId = titleId ?? `system-surface-title-${generatedTitleId}`;
  const StateIcon = STATE_ICONS[tone];
  const Heading = headingLevel;

  return (
    <FrameCard
      ariaLabel="Codexify system surface"
      className="codexify-system-surface w-full"
      hoverPop={false}
      liquidBezel={false}
      style={{
        "--tile-blur": "var(--system-surface-blur)",
        "--depth-scale": "1",
      } as React.CSSProperties}
    >
      <div className="codexify-system-surface__content" data-tone={tone}>
        <header className="codexify-system-surface__header">
          <div className="codexify-system-surface__identity">
            <span
              aria-label="Codexify system mark"
              className="codexify-system-surface__mark"
              role="img"
              style={{
                maskImage: `url("${codexifyMark}")`,
                WebkitMaskImage: `url("${codexifyMark}")`,
              }}
            />
            <span className="codexify-system-surface__speaker text-sm font-semibold tracking-wide">
              Codexify
            </span>
          </div>
          {metadata ? (
            <div className="codexify-system-surface__metadata text-xs leading-normal">
              {metadata}
            </div>
          ) : null}
        </header>

        <div className="codexify-system-surface__message">
          <div className="codexify-system-surface__state" data-tone={tone}>
            <span aria-label={statusLabel} role="img">
              <StateIcon
                aria-hidden="true"
                className="codexify-system-surface__state-icon"
              />
            </span>
            <span className="codexify-system-surface__status-label text-xs font-semibold leading-normal">
              {statusLabel}
            </span>
            <span className="codexify-system-surface__category text-xs font-bold leading-normal tracking-wider">
              {category}
            </span>
          </div>

          <div className="codexify-system-surface__copy">
            <Heading
              className="codexify-system-surface__title text-2xl font-semibold leading-tight tracking-tight sm:text-3xl"
              id={resolvedTitleId}
            >
              {title}
            </Heading>
            {description ? (
              <div className="codexify-system-surface__description max-w-prose text-sm leading-6">
                {description}
              </div>
            ) : null}
          </div>
        </div>

        {details ? (
          <div className="codexify-system-surface__details">{details}</div>
        ) : null}
        {actions ? (
          <div className="codexify-system-surface__actions">{actions}</div>
        ) : null}
      </div>
    </FrameCard>
  );
}
