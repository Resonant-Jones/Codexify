import * as React from "react";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
} from "./personaStudioStore";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import PersonaPreviewPanel from "./PersonaPreviewPanel";

const RAIL_TABS = ["Preview", "Diagnostics"] as const;
type RailTab = (typeof RAIL_TABS)[number];

const RAIL_TAB_SLUG: Record<RailTab, string> = {
  Preview: "preview",
  Diagnostics: "diagnostics",
};

export interface PersonaStudioRailProps {
  selectedProfile: PersonaProfileDraft | null;
  config: PersonaConfig | null;
  isDirty: boolean;
  hasSavedVersion: boolean;
}

function tabId(slug: string): string {
  return `persona-studio-rail-tab-${slug}`;
}

function panelId(slug: string): string {
  return `persona-studio-rail-panel-${slug}`;
}

export default function PersonaStudioRail({
  selectedProfile,
  config,
  isDirty,
  hasSavedVersion,
}: PersonaStudioRailProps) {
  const [activeTab, setActiveTab] = React.useState<RailTab>("Preview");

  return (
    <div
      className="flex min-h-0 flex-1 flex-col gap-3"
      data-testid="persona-studio-rail"
    >
      <div
        className="rounded-[var(--card-radius)] p-1"
        role="tablist"
        aria-label="Persona Studio companion rail"
        data-testid="persona-studio-rail-tabs"
        style={{
          background: "color-mix(in srgb, var(--panel-bg) 88%, transparent)",
          border: "1px solid var(--panel-border)",
          boxShadow: "0 2px 12px color-mix(in srgb, var(--bg) 48%, transparent)",
        }}
      >
      <div
        className="glass-pill flex w-full items-stretch gap-1.5 overflow-x-auto"
        style={
          {
            "--pill-active-text": "var(--text-on-accent)",
            "--pill-font": "0.92rem",
            width: "100%",
            justifyContent: "stretch",
          } as React.CSSProperties
        }
      >
        {RAIL_TABS.map((tab) => {
          const slug = RAIL_TAB_SLUG[tab];
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              id={tabId(slug)}
              type="button"
              role="tab"
              aria-selected={isActive ? "true" : "false"}
              aria-controls={panelId(slug)}
              tabIndex={isActive ? 0 : -1}
              data-state={isActive ? "active" : "inactive"}
              data-testid={`persona-studio-rail-tab-${slug}`}
              onClick={() => setActiveTab(tab)}
              className="pill-tab min-w-0 flex-1 px-3 py-2.5 text-[0.92rem]"
            >
              {tab}
            </button>
          );
        })}
      </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {activeTab === "Preview" ? (
          <section
            id={panelId("preview")}
            role="tabpanel"
            aria-labelledby={tabId("preview")}
            data-testid="persona-studio-rail-preview-panel"
            className="flex min-h-0 flex-1 flex-col"
          >
            <PersonaPreviewPanel profile={selectedProfile} />
          </section>
        ) : (
          <section
            id={panelId("diagnostics")}
            role="tabpanel"
            aria-labelledby={tabId("diagnostics")}
            data-testid="persona-studio-rail-diagnostics-panel"
            data-state="active"
            className="relative flex min-h-0 flex-1 flex-col"
          >
            <DiagnosticsPanel
              profile={selectedProfile}
              config={config}
              isDirty={isDirty}
              hasSavedVersion={hasSavedVersion}
            />
          </section>
        )}
      </div>
    </div>
  );
}
