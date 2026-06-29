import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import type { PersonaProfileDraft } from "./personaStudioStore";

export type PersonaStudioActionTone = "utility" | "primary" | "secondary" | "reset";

type PersonaStudioActionMaterialOptions = {
  open?: boolean;
};

const PERSONA_STUDIO_ACTION_CHIP_STYLES = `
.persona-studio-action-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-height: 28px;
  padding: 0.34rem 0.75rem;
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-micro);
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 94%, transparent),
      color-mix(in oklab, var(--chip-bg) 90%, transparent)
    );
  color: var(--text);
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--text) 12%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--panel-bg) 74%, transparent),
    0 1px 2px color-mix(in oklab, var(--panel-bg) 16%, transparent);
  transition:
    transform 140ms ease,
    border-color 160ms ease,
    background 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease,
    opacity 160ms ease;
}

.persona-studio-action-chip:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: color-mix(in oklab, var(--panel-border) 72%, var(--accent-weak));
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 92%, transparent),
      color-mix(in oklab, var(--chip-bg) 88%, transparent)
    );
}

.persona-studio-action-chip:active:not(:disabled) {
  transform: translateY(1px);
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 90%, transparent),
      color-mix(in oklab, var(--chip-bg) 86%, transparent)
    );
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--text) 10%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--panel-bg) 82%, transparent),
    0 0 0 1px color-mix(in oklab, var(--panel-border) 54%, transparent);
}

.persona-studio-action-chip:focus-visible {
  outline: 2px solid color-mix(in oklab, var(--accent-strong) 72%, transparent);
  outline-offset: 2px;
}

.persona-studio-action-chip:disabled {
  color: var(--text-subtle);
  cursor: not-allowed;
  border-color: color-mix(in oklab, var(--panel-border) 78%, var(--chip-border) 22%);
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 96%, transparent),
      color-mix(in oklab, var(--chip-bg) 94%, transparent)
    );
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--text-subtle) 8%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--panel-bg) 82%, transparent),
    0 1px 1px color-mix(in oklab, var(--panel-bg) 10%, transparent);
}

.persona-studio-action-chip--utility {
  border-color: color-mix(in oklab, var(--chip-border) 80%, var(--panel-border) 20%);
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 92%, var(--chip-bg) 8%),
      color-mix(in oklab, var(--chip-bg) 90%, var(--panel-bg) 10%)
    );
}

.persona-studio-action-chip--utility[data-persona-studio-action-open="true"] {
  border-color: color-mix(in oklab, var(--accent-strong) 26%, var(--panel-border));
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 88%, var(--accent-weak) 12%),
      color-mix(in oklab, var(--chip-bg) 88%, var(--panel-bg) 12%)
    );
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--text) 16%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--panel-bg) 70%, transparent),
    0 2px 4px color-mix(in oklab, var(--accent-strong) 10%, transparent);
}

.persona-studio-action-chip--primary {
  border-color: color-mix(in oklab, var(--accent-strong) 26%, var(--panel-border));
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 88%, var(--accent-weak) 12%),
      color-mix(in oklab, var(--chip-bg) 86%, var(--accent-strong) 14%)
    );
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--text) 16%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--accent-strong) 12%, transparent),
    0 2px 6px color-mix(in oklab, var(--accent-strong) 12%, transparent);
}

.persona-studio-action-chip--secondary {
  border-color: color-mix(in oklab, var(--panel-border) 82%, var(--chip-border) 18%);
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 93%, var(--chip-bg) 7%),
      color-mix(in oklab, var(--chip-bg) 91%, var(--panel-bg) 9%)
    );
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--text) 12%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--panel-bg) 76%, transparent),
    0 1px 3px color-mix(in oklab, var(--panel-bg) 12%, transparent);
}

.persona-studio-action-chip--reset {
  color: color-mix(in oklab, var(--text) 84%, var(--danger-text) 16%);
  border-color: color-mix(in oklab, var(--danger-border) 38%, var(--panel-border) 62%);
  background:
    linear-gradient(
      180deg,
      color-mix(in oklab, var(--panel-bg) 94%, var(--danger-surface) 6%),
      color-mix(in oklab, var(--chip-bg) 92%, var(--danger-surface) 8%)
    );
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--danger-text) 10%, transparent),
    inset 0 -1px 0 color-mix(in oklab, var(--panel-bg) 80%, transparent),
    0 1px 3px color-mix(in oklab, var(--panel-bg) 12%, transparent);
}

.persona-studio-action-chip--reset:hover:not(:disabled) {
  border-color: color-mix(in oklab, var(--danger-border) 50%, var(--panel-border) 50%);
}

.persona-studio-action-chip__chevron {
  color: var(--muted);
  font-size: 0.68rem;
  line-height: 1;
  letter-spacing: 0.02em;
}
`;

export function getPersonaStudioActionChipClassName(
  tone: PersonaStudioActionTone,
  options: PersonaStudioActionMaterialOptions = {}
) {
  const classes = ["persona-studio-action-chip", `persona-studio-action-chip--${tone}`];
  if (options.open) {
    classes.push("persona-studio-action-chip--open");
  }
  return classes.join(" ");
}

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

/**
 * Compact ownership + action strip rendered directly beneath the active
 * module editor. The selected-profile control stays text-first, compact, and
 * quieter than the nav pills.
 */
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
  void hasSavedVersion;
  const [open, setOpen] = React.useState(false);

  const handleSelectProfile = (profileId: string) => {
    onSelectProfile(profileId);
    setOpen(false);
  };

  const profileName = selectedProfile?.name ?? "No profile selected";

  return (
    <>
      <style>{PERSONA_STUDIO_ACTION_CHIP_STYLES}</style>
      <div
        className="flex flex-wrap items-center gap-1"
        data-testid="persona-studio-profile-selector"
      >
        <DropdownMenu open={open} onOpenChange={setOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              data-testid="persona-studio-profile-selector-trigger"
              data-persona-studio-action-tier="utility"
              data-persona-studio-action-open={open ? "true" : "false"}
              title={`Profile: ${profileName} — click to switch`}
              aria-label={`Profile: ${profileName}`}
              className={`${getPersonaStudioActionChipClassName("utility", { open })} h-6 px-2 text-xs`}
            >
              <span
                data-testid="persona-studio-profile-selector-trigger-name"
                className="max-w-[180px] truncate"
              >
                {profileName}
              </span>
              <span
                aria-hidden="true"
                className="persona-studio-action-chip__chevron"
              >
                ▾
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="z-50 min-w-[240px] overflow-hidden rounded-[var(--card-radius)] border p-1"
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 98%, transparent)",
              borderColor: "var(--panel-border)",
              boxShadow:
                "0 12px 40px color-mix(in srgb, var(--bg) 55%, transparent)",
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
                  <span
                    className="shrink-0 text-xs"
                    style={{ color: "var(--muted)" }}
                  >
                    {profile.isDefault ? "Default" : "Custom"}
                  </span>
                </DropdownMenuItem>
              ))}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <span
          className="mx-0.5 select-none text-xs"
          style={{ color: "var(--muted)" }}
          aria-hidden="true"
        >
          ·
        </span>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onSave}
          disabled={!isDirty}
          data-persona-studio-action-tier="primary"
          className={`${getPersonaStudioActionChipClassName("primary")} h-6 px-3 text-xs`}
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
          data-persona-studio-action-tier="secondary"
          className={`${getPersonaStudioActionChipClassName("secondary")} h-6 px-3 text-xs`}
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
          data-persona-studio-action-tier="reset"
          className={`${getPersonaStudioActionChipClassName("reset")} h-6 px-3 text-xs`}
          data-testid="persona-studio-action-reset"
        >
          Reset profile changes
        </Button>

        <span
          className="mx-1 select-none text-xs"
          style={{ color: "var(--muted)" }}
          aria-hidden="true"
        >
          ·
        </span>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onResetAll}
          className={`${getPersonaStudioActionChipClassName("reset")} h-6 px-3 text-xs`}
          data-persona-studio-action-tier="reset"
          data-testid="persona-studio-action-reset-all"
          title="Reset all local Persona Studio data"
        >
          Reset local Studio data
        </Button>
      </div>
    </>
  );
}
