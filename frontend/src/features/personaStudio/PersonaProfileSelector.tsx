import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import type { PersonaProfileDraft } from "./personaStudioStore";

export interface PersonaProfileSelectorProps {
  profiles: PersonaProfileDraft[];
  selectedProfileId: string;
  onSelectProfile: (profileId: string) => void;
  selectedProfile: PersonaProfileDraft | null;
  isDirty: boolean;
  hasSavedVersion: boolean;
  onSave: () => void;
  onSaveAsNew: () => void;
  onReset: () => void;
  onResetAll: () => void;
}

export default function PersonaProfileSelector({
  profiles,
  selectedProfileId,
  onSelectProfile,
  selectedProfile,
  isDirty,
  hasSavedVersion,
  onSave,
  onSaveAsNew,
  onReset,
  onResetAll,
}: PersonaProfileSelectorProps) {
  const [open, setOpen] = React.useState(false);

  const handleSelectProfile = (profileId: string) => {
    onSelectProfile(profileId);
    setOpen(false);
  };

  const profileName = selectedProfile?.name ?? "No profile selected";

  return (
    <div
      className="flex flex-wrap items-center gap-1.5 rounded-[var(--tile-radius)] border px-3 py-2"
      data-testid="persona-studio-profile-selector"
      style={{
        borderColor: "var(--panel-border)",
        background: "color-mix(in srgb, var(--panel-bg) 93%, transparent)",
      }}
    >
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          className="inline-flex items-center gap-1.5 rounded-[var(--tile-radius)] border px-2.5 py-1 text-xs font-medium transition-colors hover:border-[var(--accent)]"
          style={{
            background: "transparent",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
          data-testid="persona-studio-profile-selector-trigger"
          title="Select Persona Studio profile"
        >
          <span className="max-w-[180px] truncate">{profileName}</span>
          <svg
            className="h-3 w-3 shrink-0"
            style={{ color: "var(--muted)" }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          className="z-50 min-w-[240px] overflow-hidden rounded-[var(--card-radius)] border p-1"
          style={{
            background: "color-mix(in srgb, var(--panel-bg) 98%, transparent)",
            borderColor: "var(--panel-border)",
            boxShadow: "0 12px 40px color-mix(in srgb, var(--bg) 55%, transparent)",
          }}
          data-testid="persona-studio-profile-selector-dropdown"
        >
          <div
            className="max-h-[220px] overflow-y-auto"
            data-testid="persona-studio-profile-selector-list"
          >
            {profiles.map((profile) => (
              <DropdownMenuItem
                key={profile.id}
                onClick={() => handleSelectProfile(profile.id)}
                className="flex items-center gap-2 rounded-[var(--tile-radius)] px-3 py-2 text-sm cursor-pointer"
                style={{
                  background:
                    profile.id === selectedProfileId
                      ? "color-mix(in srgb, var(--accent) 10%, transparent)"
                      : "transparent",
                  color: "var(--text)",
                }}
                data-testid={`persona-studio-profile-option-${profile.id}`}
              >
                <span className="flex-1 truncate">{profile.name}</span>
                <span className="shrink-0 text-xs" style={{ color: "var(--muted)" }}>
                  {profile.isDefault ? "Default" : "Custom"}
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      <div className="h-5 w-px shrink-0" style={{ background: "var(--panel-border)" }} />

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onSave}
        disabled={!isDirty}
        className="h-7 text-xs"
        data-testid="persona-studio-action-save"
      >
        Save profile
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onSaveAsNew}
        disabled={!selectedProfile}
        className="h-7 text-xs"
        data-testid="persona-studio-action-save-as-new"
      >
        Save as new profile
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onReset}
        disabled={!isDirty}
        className="h-7 text-xs"
        data-testid="persona-studio-action-reset"
      >
        Reset profile changes
      </Button>

      <div className="ml-auto">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onResetAll}
          className="h-7 text-xs"
          style={{ color: "var(--muted)" }}
          data-testid="persona-studio-action-reset-all"
          title="Reset all local Persona Studio data"
        >
          Reset local Studio data
        </Button>
      </div>
    </div>
  );
}
