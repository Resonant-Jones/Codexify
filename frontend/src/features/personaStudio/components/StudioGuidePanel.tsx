import * as React from "react";
import { Badge } from "@/components/ui/badge";
import type { PersonaConfig } from "../personaStudioStore";
import { analyzeStudioGuideDraft } from "../lib/studioGuideRules";

export default function StudioGuidePanel({
  config,
}: {
  config: PersonaConfig | null;
}) {
  const cards = React.useMemo(() => analyzeStudioGuideDraft(config), [config]);

  const hasDraft = Boolean(config);

  return (
    <aside
      className="flex min-h-0 flex-1 flex-col gap-[var(--shell-gap)] rounded-[var(--card-radius)] border p-[var(--card-pad)]"
      data-testid="persona-studio-guide-panel"
      role="complementary"
      aria-label="Persona Studio guide"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
        borderColor: "var(--panel-border)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), inset 0 -1px 0 rgba(0,0,0,0.16)",
      }}
    >
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Studio Guide
            </h3>
            <p className="text-sm leading-6 text-[var(--text)]">
              Deterministic draft linting for the unsaved persona config. No chat, no memory, no autosave.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge
              variant="outline"
              className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {hasDraft ? "Draft aware" : "No draft selected"}
            </Badge>
            <Badge
              variant="outline"
              className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {cards.length ? `${cards.length} signals` : "No obvious drift"}
            </Badge>
          </div>
        </div>
        <p className="text-sm leading-6 text-[var(--muted)]">
          The panel only reads the current unsaved draft state and surfaces sparse guidance when the prompt or identity feels under-specified.
        </p>
      </div>

      <div className="min-h-0 space-y-[var(--shell-gap)] overflow-y-auto pr-1">
        {cards.length > 0 ? (
          cards.map((card) => (
            <article
              key={card.id}
              data-testid="persona-studio-guide-card"
              className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
              style={{
                borderColor: "var(--panel-border)",
                background: "var(--chip-bg)",
              }}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-[var(--text)]">{card.title}</h4>
                  <p className="text-sm leading-6 text-[var(--muted)]">{card.summary}</p>
                </div>
                <Badge
                  variant="outline"
                  className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                  style={{ borderColor: "var(--panel-border)" }}
                >
                  {card.severity}
                </Badge>
              </div>

              <div className="mt-3 space-y-2">
                <p className="text-sm leading-6 text-[var(--text)]">
                  <span className="font-semibold">Suggested edit:</span> {card.suggestion}
                </p>
                {card.question ? (
                  <p className="text-sm leading-6 text-[var(--muted)]">
                    <span className="font-semibold">Question:</span> {card.question}
                  </p>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  {card.evidence.map((item) => (
                    <Badge
                      key={`${card.id}-${item}`}
                      variant="outline"
                      className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      {item}
                    </Badge>
                  ))}
                </div>
              </div>
            </article>
          ))
        ) : (
          <div
            data-testid="persona-studio-guide-empty"
            className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
            }}
          >
            <p className="text-sm font-semibold text-[var(--text)]">
              No obvious draft lint detected.
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              The current draft already carries enough role, tone, and constraint signal for the bounded guide.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
