import * as React from "react";
import { Badge } from "@/components/ui/badge";
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

  const handleProfileAction = (action: () => void) => {
    action();
    setOpen(false);
  };

  const profileName = selectedProfile?.name ?? "No profile selected";

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid="persona-studio-profile-selector"
    >
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          className="inline-flex items-center gap-2 rounded-[var(--tile-radius)] border px-4 py-2 text-sm font-medium transition-colors hover:border-[var(--accent)]"
          style={{
            background: "color-mix(in srgb, var(--panel-bg) 93%, transparent)",
            borderColor: "var(--panel-border)",
            color: "var(--text)",
          }}
          data-testid="persona-studio-profile-selector-trigger"
        >
          <span className="text-xs uppercase tracking-[0.12em]" style={{ color: "var(--muted)" }}>
            Profile
          </span>
          <span className="max-w-[240px] truncate">{profileName}</span>
          <svg
            className="h-3.5 w-3.5 shrink-0"
            style={{ color: "var(--muted)" }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          className="z-50 min-w-[260px] overflow-hidden rounded-[var(--card-radius)] border p-1"
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
          <div
            className="my-1 border-t"
            style={{ borderColor: "var(--panel-border)" }}
          />
          <div className="space-y-0.5 px-1">
            <button
              type="button"
              disabled={!isDirty}
              onClick={() => handleProfileAction(onSave)}
              className="w-full rounded-[var(--tile-radius)] px-3 py-1.5 text-left text-sm transition-colors hover:bg-[var(--accent-weak)]/20 disabled:opacity-50"
              style={{ color: "var(--text)" }}
              data-testid="persona-studio-action-save"
            >
              Save profile
            </button>
            <button
              type="button"
              disabled={!selectedProfile}
              onClick={() => handleProfileAction(onSaveAsNew)}
              className="w-full rounded-[var(--tile-radius)] px-3 py-1.5 text-left text-sm transition-colors hover:bg-[var(--accent-weak)]/20 disabled:opacity-50"
              style={{ color: "var(--text)" }}
              data-testid="persona-studio-action-save-as-new"
            >
              Save as new profile
            </button>
            <button
              type="button"
              disabled={!isDirty}
              onClick={() => handleProfileAction(onReset)}
              className="w-full rounded-[var(--tile-radius)] px-3 py-1.5 text-left text-sm transition-colors hover:bg-[var(--accent-weak)]/20 disabled:opacity-50"
              style={{ color: "var(--text)" }}
              data-testid="persona-studio-action-reset"
            >
              Reset profile changes
            </button>
          </div>
          <div
            className="my-1 border-t"
            style={{ borderColor: "var(--panel-border)" }}
          />
          <div className="px-1">
            <button
              type="button"
              onClick={() => handleProfileAction(onResetAll)}
              className="w-full rounded-[var(--tile-radius)] px-3 py-1.5 text-left text-xs transition-colors hover:bg-[var(--danger-weak)]/20"
              style={{ color: "var(--muted)" }}
              data-testid="persona-studio-action-reset-all"
              title="Reset all local Persona Studio data"
            >
              Reset local Studio data
            </button>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
