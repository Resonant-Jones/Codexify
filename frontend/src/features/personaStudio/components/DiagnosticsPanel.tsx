import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
} from "../personaStudioStore";

function buildDebugLog(
  profile: PersonaProfileDraft | null,
  config: PersonaConfig | null
): string[] {
  if (!profile || !config) {
    return [
      "[PersonaStudio] Initialized local draft store",
      "[PersonaStudio] Waiting for profile selection",
      "[Config] No profile selected",
    ];
  }

  return [
    "[PersonaStudio] Initialized local draft store",
    `[PersonaStudio] Selected profile: ${profile.id}`,
    `[PersonaStudio] Profile loaded: ${profile.name}`,
    `[Config] Model: ${config.model.provider}/${config.model.model}`,
    `[Config] Temperature: ${config.model.temperature}`,
    `[Config] Voice: ${config.voice.enabled ? config.voice.provider : "disabled"}`,
    `[Config] Retrieval: ${config.retrieval.enabled ? config.retrieval.mode : "disabled"}`,
  ];
}

export default function DiagnosticsPanel({
  profile,
  config,
  isDirty,
  hasSavedVersion,
}: {
  profile: PersonaProfileDraft | null;
  config: PersonaConfig | null;
  isDirty: boolean;
  hasSavedVersion: boolean;
}) {
  const debugLog = React.useMemo(() => buildDebugLog(profile, config), [profile, config]);

  const saveStatusLabel = isDirty
    ? "Unsaved Draft"
    : hasSavedVersion
      ? "Saved Locally"
      : "Seed Draft";

  const saveStatusTone = isDirty ? "warning" : hasSavedVersion ? "saved" : "seed";

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Diagnostics</h3>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span style={{ color: "var(--muted)" }}>Save Status</span>
            <Badge
              variant="outline"
              className="text-xs"
              style={{
                borderColor:
                  saveStatusTone === "saved"
                    ? "rgba(34, 197, 94, 0.35)"
                    : saveStatusTone === "warning"
                      ? "rgba(234, 179, 8, 0.35)"
                      : "var(--panel-border)",
                background:
                  saveStatusTone === "saved"
                    ? "rgba(34, 197, 94, 0.12)"
                    : saveStatusTone === "warning"
                      ? "rgba(234, 179, 8, 0.12)"
                      : "transparent",
              }}
            >
              {saveStatusLabel}
            </Badge>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-2">
        <h4 className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
          Effective Config
        </h4>
        <div
          className="overflow-auto rounded-lg border p-3 text-xs font-mono"
          style={{
            background: "rgba(0,0,0,0.12)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            maxHeight: "200px",
          }}
        >
          {config ? (
            <pre className="whitespace-pre-wrap">{JSON.stringify(config, null, 2)}</pre>
          ) : (
            <span style={{ color: "var(--muted)" }}>No profile selected</span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
          Debug Log
        </h4>
        <div
          className="overflow-auto rounded-lg border p-3 text-xs font-mono"
          style={{
            background: "rgba(0,0,0,0.12)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            maxHeight: "150px",
          }}
        >
          {debugLog.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
