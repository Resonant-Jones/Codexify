import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
} from "./personaStudioStore";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import PersonaPreviewPanel from "./PersonaPreviewPanel";

const RAIL_TABS = ["Preview", "Profiles", "Diagnostics"] as const;
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
  profiles: PersonaProfileDraft[];
  selectedProfileId: string;
  onSelectProfile: (profileId: string) => void;
  selectedProfile: PersonaProfileDraft | null;
  config: PersonaConfig | null;
  isDirty: boolean;
  hasSavedVersion: boolean;
}

export default function PersonaStudioRail({
  profiles,
  selectedProfileId,
  onSelectProfile,
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
        ) : activeTab === "Profiles" ? (
          <div
            className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto rounded-[var(--card-radius)] border px-3 py-3"
            data-state="active"
            style={{
              borderColor: "var(--panel-border)",
              background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
            }}
          >
            {profiles.map((profile) => (
              <button
                key={profile.id}
                type="button"
                onClick={() => onSelectProfile(profile.id)}
                className={`w-full rounded-xl p-3 text-left transition-colors ${
                  profile.id === selectedProfileId
                    ? "border-2"
                    : "border border-transparent hover:border-[var(--panel-border)]"
                }`}
                style={{
                  background:
                    profile.id === selectedProfileId
                      ? "color-mix(in srgb, var(--accent) 10%, var(--panel-bg))"
                      : "transparent",
                  borderColor:
                    profile.id === selectedProfileId
                      ? "var(--accent)"
                      : "transparent",
                }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{profile.name}</span>
                  {profile.isDefault && (
                    <Badge
                      variant="outline"
                      className="px-1.5 py-0.5 text-[10px]"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      Default
                    </Badge>
                  )}
                </div>
                <p
                  className="mt-1 line-clamp-2 text-xs"
                  style={{ color: "var(--muted)" }}
                >
                  {profile.description}
                </p>
              </button>
            ))}
          </div>
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
