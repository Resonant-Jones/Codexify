import * as React from "react";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
} from "./personaStudioStore";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import PersonaPreviewPanel from "./PersonaPreviewPanel";

const RAIL_TABS = ["Preview", "Diagnostics"] as const;
type RailTab = (typeof RAIL_TABS)[number];

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      data-state={active ? "active" : "inactive"}
      className="pill-tab min-w-0 flex-1 px-3 py-2.5 text-[0.92rem]"
    >
      {children}
    </button>
  );
}

export interface PersonaStudioRailProps {
  selectedProfile: PersonaProfileDraft | null;
  config: PersonaConfig | null;
  isDirty: boolean;
  hasSavedVersion: boolean;
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
        className="glass-pill flex w-full items-stretch gap-1.5 overflow-x-auto px-1"
        data-testid="persona-studio-rail-tabs"
        style={
          {
            "--pill-active-text": "var(--text-on-accent)",
            "--pill-font": "0.92rem",
            width: "100%",
            justifyContent: "stretch",
          } as React.CSSProperties
        }
      >
        {RAIL_TABS.map((tab) => (
          <TabButton
            key={tab}
            active={activeTab === tab}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </TabButton>
        ))}
      </div>

      <div className="flex min-h-0 flex-1 flex-col" data-testid={`persona-studio-rail-${activeTab.toLowerCase()}-panel`}>
        {activeTab === "Preview" ? (
          <PersonaPreviewPanel profile={selectedProfile} />
        ) : (
          <div
            role="complementary"
            aria-label="Persona Studio diagnostics"
            data-state="active"
            className="relative flex min-h-0 flex-1 flex-col"
          >
            <DiagnosticsPanel
              profile={selectedProfile}
              config={config}
              isDirty={isDirty}
              hasSavedVersion={hasSavedVersion}
            />
          </div>
        )}
      </div>
    </div>
  );
}
