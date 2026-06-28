import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import type { PersonaProfileDraft } from "./personaStudioStore";

/**
 * Persona Studio-local action material.
 *
 * This is a deliberately small, Persona Studio-only "micro-Aqua" pressed-glass
 * chip treatment. It is intentionally quieter than the navigation pill material
 * (`.glass-pill` / `.pill-tab[data-state="active"]`): nav pills stay the
 * strongest luminous/glass moment, while these action controls become compact
 * pressed-glass chips that hint at the same optical material through rim,
 * depth, gentle sheen, and tactile state.
 *
 * Boundary contract:
 * - Local to Persona Studio only. Does not modify the shared Button component,
 *   global styles, AppShell, or any navigation material.
 * - Token-only: every value derives from existing Codexify UI tokens
 *   (`var(--...)`) via `color-mix`. No inline hex, arbitrary Tailwind colors,
 *   hardcoded rgba, arbitrary radii, arbitrary shadows, or new CSS variables.
 *   The inset depth/sheen shadows reuse the same token-derived `color-mix`
 *   pattern already present in Persona Studio files.
 * - States (hover/active/focus-visible/disabled) are token-compliant and keep
 *   focus visible via an `outline` that does not collide with the chip's
 *   box-shadow depth.
 */
export type PersonaStudioActionMaterialTier =
  | "selector"
  | "primary"
  | "secondary"
  | "reset";

const PERSONA_STUDIO_ACTION_CHIP_CSS = `
.ps-action-chip{
  border-radius:var(--radius-micro);
  border:1px solid color-mix(in oklab, var(--panel-border) 85%, transparent);
  background:var(--chip-bg);
  box-shadow:
    inset 0 1px 0 color-mix(in oklab, var(--panel-bezel) 55%, transparent),
    inset 0 -1px 1px color-mix(in oklab, var(--bg) 38%, transparent);
  transition:background .18s ease, border-color .18s ease, box-shadow .18s ease, transform .1s ease;
}
.ps-action-chip:hover{
  background:color-mix(in oklab, var(--surface-hover) 60%, var(--chip-bg));
  border-color:var(--panel-border);
}
.ps-action-chip:active{
  transform:translateY(1px);
  box-shadow:inset 0 1px 2px color-mix(in oklab, var(--bg) 52%, transparent);
}
.ps-action-chip:focus-visible{
  outline:2px solid var(--accent-weak);
  outline-offset:1px;
}
.ps-action-chip:disabled{
  box-shadow:inset 0 1px 0 color-mix(in oklab, var(--panel-bezel) 24%, transparent);
}

/* Tier 1 — Utility / selector chip: compact inline pill, text-first. */
.ps-action-chip[data-ps-material="selector"]{
  background:color-mix(in oklab, var(--chip-bg) 80%, var(--panel-bg));
}
.ps-action-chip[data-ps-material="selector"]:hover{
  background:color-mix(in oklab, var(--surface-hover) 55%, var(--chip-bg));
}

/* Tier 2 — Primary action chip: restrained accent presence, quieter than nav pills. */
.ps-action-chip[data-ps-material="primary"]{
  border-color:color-mix(in oklab, var(--accent-weak) 42%, var(--panel-border));
  background:color-mix(in oklab, var(--accent-weak) 20%, var(--chip-bg));
}
.ps-action-chip[data-ps-material="primary"]:hover{
  background:color-mix(in oklab, var(--accent-weak) 34%, var(--chip-bg));
  border-color:color-mix(in oklab, var(--accent-weak) 60%, var(--panel-border));
}
.ps-action-chip[data-ps-material="primary"]:disabled{
  background:color-mix(in oklab, var(--panel-bg) 30%, var(--chip-bg));
  border-color:color-mix(in oklab, var(--panel-border) 70%, transparent);
}

/* Tier 3 — Secondary action chip: polished but quieter than primary. */
.ps-action-chip[data-ps-material="secondary"]{
  background:color-mix(in oklab, var(--panel-bg) 30%, var(--chip-bg));
}

/* Tier 4 — Reset / danger chip: quiet and muted, never alarm red.
   No warm/reset token exists in the allowed canon, so this stays token-muted;
   richer reset material needs a future token task. */
.ps-action-chip[data-ps-material="reset"]{
  border-color:color-mix(in oklab, var(--panel-border) 95%, transparent);
  background:color-mix(in oklab, var(--chip-bg) 70%, transparent);
  color:var(--muted);
}
.ps-action-chip[data-ps-material="reset"]:hover{
  background:color-mix(in oklab, var(--surface-hover) 50%, var(--chip-bg));
  border-color:var(--panel-border);
}
`;

/**
 * Returns the Persona Studio-local action chip material attributes for a given
 * tier. The caller keeps its own sizing/utility className and interactive props;
 * this only contributes the material marker class (`ps-action-chip`), the
 * `data-ps-material` tier used by the scoped styles above and by tests, and an
 * explicit tier label.
 */
export function personaStudioActionChip(
  tier: PersonaStudioActionMaterialTier,
  className?: string
): {
  className: string;
  "data-ps-material": PersonaStudioActionMaterialTier;
  "data-ps-action-tier": PersonaStudioActionMaterialTier;
} {
  return {
    className: ["ps-action-chip", className].filter(Boolean).join(" "),
    "data-ps-material": tier,
    "data-ps-action-tier": tier,
  };
}

function PersonaStudioActionChipStyles() {
  return <style data-ps-action-chip-styles>{PERSONA_STUDIO_ACTION_CHIP_CSS}</style>;
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
 * module editor. The selected-profile control is a small inline Button —
 * it must remain visually secondary to the module editor and never grow
 * into a square/tile shape.
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
  const [open, setOpen] = React.useState(false);

  const handleSelectProfile = (profileId: string) => {
    onSelectProfile(profileId);
    setOpen(false);
  };

  const profileName = selectedProfile?.name ?? "No profile selected";

  return (
    <div
      className="flex flex-wrap items-center gap-1"
      data-testid="persona-studio-profile-selector"
    >
      <PersonaStudioActionChipStyles />
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            data-testid="persona-studio-profile-selector-trigger"
            title={`Profile: ${profileName} — click to switch`}
            aria-label={`Profile: ${profileName}`}
            className="ps-action-chip h-6 gap-1 px-2 text-xs"
            data-ps-material="selector"
            data-ps-action-tier="selector"
          >
            <span
              data-testid="persona-studio-profile-selector-trigger-name"
              className="max-w-[180px] truncate"
            >
              {profileName}
            </span>
            <span
              aria-hidden="true"
              className="text-[10px] leading-none"
              style={{ color: "var(--muted)" }}
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
        className="ps-action-chip h-6 text-xs px-2"
        data-testid="persona-studio-action-save"
        data-ps-material="primary"
        data-ps-action-tier="primary"
      >
        Save profile
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onSaveAsNew}
        disabled={!selectedProfile}
        className="ps-action-chip h-6 text-xs px-2"
        data-testid="persona-studio-action-save-as-new"
        data-ps-material="secondary"
        data-ps-action-tier="secondary"
      >
        Save as new profile
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onReset}
        disabled={!isDirty}
        className="ps-action-chip h-6 text-xs px-2"
        data-testid="persona-studio-action-reset"
        data-ps-material="reset"
        data-ps-action-tier="reset"
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
        className="ps-action-chip h-6 text-xs px-2"
        title="Reset all local Persona Studio data"
        data-testid="persona-studio-action-reset-all"
        data-ps-material="reset"
        data-ps-action-tier="reset"
      >
        Reset local Studio data
      </Button>
    </div>
  );
}