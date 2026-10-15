import * as React from "react";

import FrameCard from "@/components/surface/FrameCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

import PersonaVoicePanel from "./components/PersonaVoicePanel";
import PersonaPreviewPanel, {
  personaStudioActionChip,
  PersonaStudioActionChipStyles,
} from "./PersonaPreviewPanel";
import {
  applyPersonaStudioConfiguratorIntent,
  type PersonaStudioConfiguratorChange,
  type PersonaStudioConfiguratorSection,
} from "./lib/personaStudioConfigurator";
import { PERSONA_PROFILE_API_VERSION } from "./personaStudioApi";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
  usePersonaStudioLocalDraftState,
} from "./personaStudioStore";

type AssistantMode = "build" | "test";
type ConfigurationMode = "form" | "manifest" | "effective";
type FormSectionId =
  | "identity"
  | "prompt"
  | "model"
  | "voice"
  | "capabilities"
  | "retrieval"
  | "bindings";

type BuildMessage = {
  id: number;
  request: string;
  changes: PersonaStudioConfiguratorChange[];
  response: string;
};

const CONFIGURATOR_FORM_SECTION: Record<
  PersonaStudioConfiguratorSection,
  FormSectionId
> = {
  prompt: "prompt",
  model: "model",
  voice: "voice",
  capabilities: "capabilities",
  retrieval: "retrieval",
};

const INITIAL_OPEN_SECTIONS: Record<FormSectionId, boolean> = {
  identity: true,
  prompt: true,
  model: false,
  voice: false,
  capabilities: false,
  retrieval: false,
  bindings: false,
};

const WRITABLE_MANIFEST_KEYS = [
  "apiVersion",
  "profileIdentity",
  "identity",
  "prompt",
  "model",
  "voice",
  "capabilities",
  "retrieval",
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${label} must be an object`);
  return value;
}

function assertExactKeys(
  value: Record<string, unknown>,
  allowed: readonly string[],
  label: string
) {
  const unexpected = Object.keys(value).find((key) => !allowed.includes(key));
  if (unexpected) throw new Error(`${label} contains unsupported field: ${unexpected}`);
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== "string") throw new Error(`${label} must be a string`);
  return value;
}

function requireNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${label} must be a finite number`);
  }
  return value;
}

function requireBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${label} must be a boolean`);
  return value;
}

function requireStringArray(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`${label} must be an array of strings`);
  }
  return [...value] as string[];
}

function manifestFromDraft(profile: PersonaProfileDraft) {
  const { config } = profile;
  return {
    apiVersion: PERSONA_PROFILE_API_VERSION,
    profileIdentity: profile.id,
    identity: { ...config.identity },
    prompt: { ...config.prompt },
    model: { ...config.model },
    voice: { ...config.voice },
    capabilities: {
      pinnedTools: [...config.tools.pinnedTools],
      allowedTools: [...config.tools.allowedTools],
      skills: [...config.tools.skills],
      permissions: { ...config.tools.permissions },
    },
    retrieval: { ...config.retrieval },
  };
}

/**
 * JSON is a projection of the local authored draft, not a backdoor to Binding
 * authority. This strict parser makes invalid or authority-bearing JSON remain
 * only in the local text buffer.
 */
function draftFromManifest(
  current: PersonaProfileDraft,
  value: unknown
): PersonaProfileDraft {
  const manifest = requireRecord(value, "Manifest");
  assertExactKeys(manifest, WRITABLE_MANIFEST_KEYS, "Manifest");
  if (manifest.apiVersion !== PERSONA_PROFILE_API_VERSION) {
    throw new Error(`apiVersion must be ${PERSONA_PROFILE_API_VERSION}`);
  }
  if (manifest.profileIdentity !== current.id) {
    throw new Error("profileIdentity must match the selected profile");
  }

  const identity = requireRecord(manifest.identity, "identity");
  assertExactKeys(identity, ["name", "description"], "identity");
  const prompt = requireRecord(manifest.prompt, "prompt");
  assertExactKeys(prompt, ["systemPrompt", "styleNotes", "directives"], "prompt");
  const model = requireRecord(manifest.model, "model");
  assertExactKeys(model, ["provider", "model", "temperature", "topK", "topP", "maxTokens"], "model");
  const voice = requireRecord(manifest.voice, "voice");
  assertExactKeys(voice, ["enabled", "provider", "voicePreset", "speed", "wakeWord", "interruptible"], "voice");
  const capabilities = requireRecord(manifest.capabilities, "capabilities");
  assertExactKeys(capabilities, ["pinnedTools", "allowedTools", "skills", "permissions"], "capabilities");
  const permissions = requireRecord(capabilities.permissions, "capabilities.permissions");
  assertExactKeys(permissions, ["web", "email", "calendar", "cli", "filesystem"], "capabilities.permissions");
  const retrieval = requireRecord(manifest.retrieval, "retrieval");
  assertExactKeys(retrieval, ["enabled", "mode", "topK", "rerank"], "retrieval");

  const config: PersonaConfig = {
    identity: {
      name: requireString(identity.name, "identity.name"),
      description: requireString(identity.description, "identity.description"),
    },
    prompt: {
      systemPrompt: requireString(prompt.systemPrompt, "prompt.systemPrompt"),
      styleNotes: requireString(prompt.styleNotes, "prompt.styleNotes"),
      directives: requireString(prompt.directives, "prompt.directives"),
    },
    model: {
      provider: requireString(model.provider, "model.provider"),
      model: requireString(model.model, "model.model"),
      temperature: requireNumber(model.temperature, "model.temperature"),
      topK: requireNumber(model.topK, "model.topK"),
      topP: requireNumber(model.topP, "model.topP"),
      maxTokens: requireNumber(model.maxTokens, "model.maxTokens"),
    },
    voice: {
      enabled: requireBoolean(voice.enabled, "voice.enabled"),
      provider: requireString(voice.provider, "voice.provider"),
      voicePreset: requireString(voice.voicePreset, "voice.voicePreset"),
      speed: requireNumber(voice.speed, "voice.speed"),
      wakeWord: requireString(voice.wakeWord, "voice.wakeWord"),
      interruptible: requireBoolean(voice.interruptible, "voice.interruptible"),
    },
    tools: {
      pinnedTools: requireStringArray(capabilities.pinnedTools, "capabilities.pinnedTools"),
      allowedTools: requireStringArray(capabilities.allowedTools, "capabilities.allowedTools"),
      skills: requireStringArray(capabilities.skills, "capabilities.skills"),
      permissions: {
        web: requireBoolean(permissions.web, "capabilities.permissions.web"),
        email: requireBoolean(permissions.email, "capabilities.permissions.email"),
        calendar: requireBoolean(permissions.calendar, "capabilities.permissions.calendar"),
        cli: requireBoolean(permissions.cli, "capabilities.permissions.cli"),
        filesystem: requireBoolean(permissions.filesystem, "capabilities.permissions.filesystem"),
      },
    },
    retrieval: {
      enabled: requireBoolean(retrieval.enabled, "retrieval.enabled"),
      mode: requireString(retrieval.mode, "retrieval.mode"),
      topK: requireNumber(retrieval.topK, "retrieval.topK"),
      rerank: requireBoolean(retrieval.rerank, "retrieval.rerank"),
    },
  };

  return {
    ...current,
    name: config.identity.name,
    description: config.identity.description,
    config,
  };
}

function statusFor(isDirty: boolean, savedRevision: number | null) {
  if (savedRevision == null) return "Unsaved draft";
  return isDirty
    ? `Unsaved changes · saved rev ${savedRevision}`
    : `Saved · rev ${savedRevision}`;
}

function FormSection({
  id,
  title,
  summary,
  open,
  highlighted,
  onToggle,
  children,
}: {
  id: FormSectionId;
  title: string;
  summary: string;
  open: boolean;
  highlighted: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  const contentId = `persona-studio-form-section-${id}-content`;
  return (
    <section
      id={`persona-studio-form-section-${id}`}
      data-testid={`persona-studio-form-section-${id}`}
      data-highlighted={highlighted ? "true" : "false"}
      data-open={open ? "true" : "false"}
      className="ps-form-section rounded-[var(--radius-micro)] border"
      style={{
        borderColor: "var(--panel-border)",
        background: highlighted
          ? "color-mix(in oklab, var(--accent-weak) 12%, transparent)"
          : undefined,
      }}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={contentId}
        className="ps-section-toggle flex w-full items-start justify-between gap-[var(--card-pad)] text-left"
      >
        <span>
          <span className="block text-base font-semibold leading-6">{title}</span>
          <span className="mt-1 block text-xs leading-5 text-[var(--muted)]">{summary}</span>
        </span>
        <svg className="mt-1 h-4 w-4 shrink-0 text-[var(--muted)]" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path d={open ? "M3 10l5-5 5 5" : "M3 6l5 5 5-5"} />
        </svg>
      </button>
      {open ? <div id={contentId} className="ps-section-fields">{children}</div> : null}
    </section>
  );
}

function FieldLabel({
  htmlFor,
  children,
  highlighted = false,
}: {
  htmlFor?: string;
  children: React.ReactNode;
  highlighted?: boolean;
}) {
  return (
    <label
      htmlFor={htmlFor}
      data-highlighted={highlighted ? "true" : "false"}
      className="block space-y-1.5 text-xs font-medium text-[var(--muted)]"
      style={{ color: highlighted ? "var(--accent)" : undefined }}
    >
      {children}
    </label>
  );
}

function parseCommaSeparated(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export default function PersonaStudioPage() {
  const {
    profiles,
    selectedProfile,
    savedRevision,
    isDirty,
    hasSavedVersion,
    setSelectedProfileId,
    updateSelectedProfile,
    saveSelectedProfile,
    saveSelectedProfileAsNew,
    resetSelectedProfile,
  } = usePersonaStudioLocalDraftState();
  const [assistantMode, setAssistantMode] = React.useState<AssistantMode>("build");
  const [configurationMode, setConfigurationMode] = React.useState<ConfigurationMode>("form");
  const [openSections, setOpenSections] = React.useState(INITIAL_OPEN_SECTIONS);
  const [highlightedFields, setHighlightedFields] = React.useState<string[]>([]);
  const [buildInput, setBuildInput] = React.useState("");
  const [buildMessages, setBuildMessages] = React.useState<BuildMessage[]>([]);
  const [manifestBuffer, setManifestBuffer] = React.useState("");
  const [manifestError, setManifestError] = React.useState<string | null>(null);
  const messageId = React.useRef(0);
  const highlightTimeout = React.useRef<number | null>(null);
  const selectedProfileIdRef = React.useRef<string | null>(null);

  const manifestProjection = React.useMemo(
    () => (selectedProfile ? JSON.stringify(manifestFromDraft(selectedProfile), null, 2) : ""),
    [selectedProfile]
  );

  React.useEffect(() => {
    const profileId = selectedProfile?.id ?? null;
    if (selectedProfileIdRef.current !== profileId) {
      selectedProfileIdRef.current = profileId;
      setManifestError(null);
      setManifestBuffer(manifestProjection);
    } else if (!manifestError) {
      setManifestBuffer(manifestProjection);
    }
  }, [manifestError, manifestProjection, selectedProfile?.id]);

  React.useEffect(() => () => {
    if (highlightTimeout.current != null) window.clearTimeout(highlightTimeout.current);
  }, []);

  const updateConfig = React.useCallback((updater: (config: PersonaConfig) => PersonaConfig) => {
    updateSelectedProfile((current) => {
      const config = updater(current.config);
      return {
        ...current,
        name: config.identity.name,
        description: config.identity.description,
        config,
      };
    });
  }, [updateSelectedProfile]);

  const fieldIsHighlighted = React.useCallback(
    (field: string) => highlightedFields.includes(field),
    [highlightedFields]
  );
  const sectionIsHighlighted = React.useCallback((section: FormSectionId) => {
    const configuratorSection = (Object.entries(CONFIGURATOR_FORM_SECTION).find(
      ([, formSection]) => formSection === section
    )?.[0] ?? null) as PersonaStudioConfiguratorSection | null;
    return configuratorSection !== null && highlightedFields.some((field) =>
      configuratorSection === "capabilities"
        ? field.startsWith("capabilities.")
        : field.startsWith(`${configuratorSection}.`)
    );
  }, [highlightedFields]);

  const focusChanges = React.useCallback((changes: PersonaStudioConfiguratorChange[]) => {
    const firstSection = changes[0]?.section;
    if (!firstSection) return;
    const formSection = CONFIGURATOR_FORM_SECTION[firstSection];
    setConfigurationMode("form");
    setOpenSections((previous) => ({ ...previous, [formSection]: true }));
    window.setTimeout(() => {
      document.getElementById(`persona-studio-form-section-${formSection}`)?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }, 0);
  }, []);

  const handleBuildSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const request = buildInput.trim();
    if (!request || !selectedProfile) return;
    const result = applyPersonaStudioConfiguratorIntent(selectedProfile, request);
    messageId.current += 1;
    if (result.recognized) {
      updateSelectedProfile(() => result.draft);
      setHighlightedFields(result.changedFieldPaths);
      setOpenSections((previous) => result.sections.reduce(
        (next, section) => ({ ...next, [CONFIGURATOR_FORM_SECTION[section]]: true }),
        previous
      ));
      if (highlightTimeout.current != null) window.clearTimeout(highlightTimeout.current);
      highlightTimeout.current = window.setTimeout(() => setHighlightedFields([]), 2800);
    }
    setBuildMessages((previous) => [...previous, {
      id: messageId.current,
      request,
      changes: result.changes,
      response: result.recognized
        ? `Updated ${result.changes.length} local draft ${result.changes.length === 1 ? "field" : "fields"}. Save remains explicit.`
        : "No supported draft change was recognized. The local draft was left unchanged.",
    }]);
    setBuildInput("");
  };

  const handleManifestChange = (nextBuffer: string) => {
    setManifestBuffer(nextBuffer);
    if (!selectedProfile) return;
    try {
      const nextDraft = draftFromManifest(selectedProfile, JSON.parse(nextBuffer) as unknown);
      updateSelectedProfile(() => nextDraft);
      setManifestError(null);
    } catch (error) {
      setManifestError(error instanceof Error ? error.message : "Manifest is invalid");
    }
  };

  if (!selectedProfile) {
    return <div className="flex h-full items-center justify-center" data-testid="persona-studio-page">No Persona Profile is selected.</div>;
  }

  const { config } = selectedProfile;
  const status = statusFor(isDirty, savedRevision);
  const toggleSection = (section: FormSectionId) => setOpenSections((previous) => ({
    ...previous,
    [section]: !previous[section],
  }));

  return (
    <main className="h-full min-h-0 w-full overflow-y-auto" data-testid="persona-studio-page" data-persona-studio-layout="assistant-configuration">
      <style data-testid="persona-studio-layout-styles">{`
        [data-testid="persona-studio-page"] {
          container: persona-studio / inline-size;
        }
        [data-testid="persona-studio-workspace"] {
          display: grid;
          box-sizing: border-box;
          min-height: 100%;
          grid-template-columns: minmax(0, 1fr);
          grid-auto-rows: minmax(34rem, auto);
          gap: var(--shell-gap);
          padding: var(--shell-gap);
        }
        [data-testid="persona-studio-workspace"] > .fc-root {
          min-width: 0;
          min-height: 0;
        }
        [data-testid="persona-studio-workspace"] .fc-inner > div,
        [data-testid="persona-studio-build-mode"],
        [data-testid="persona-studio-test-mode"] {
          display: flex;
          flex-direction: column;
          flex: 1;
          min-height: 0;
          min-width: 0;
        }
        [data-testid="persona-studio-configuration-viewport"],
        [data-testid="persona-studio-build-transcript"] {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
        }
        [data-testid="persona-studio-workspace"] :is(input, textarea, select) {
          box-sizing: border-box;
          max-width: 100%;
        }
        @container persona-studio (min-width: 900px) {
          [data-testid="persona-studio-workspace"] {
            height: 100%;
            min-height: 0;
            grid-template-columns: minmax(0, 0.75fr) minmax(0, 1.35fr);
            grid-template-rows: minmax(0, 1fr);
          }
          [data-testid="persona-studio-workspace"] > .fc-root {
            grid-row: 1;
          }
        }
      `}</style>
      <style data-testid="persona-studio-hierarchy-styles">{`
        /* Guardian composer geometry, scoped to text entry (including embedded Test). */
        [data-testid="persona-studio-page"] :is(textarea, input[type="text"], input[type="number"], input:not([type])) {
          border-radius: 24px;
          padding: var(--card-pad) var(--shell-gap);
          font-size: 0.875rem;
          font-weight: 400;
          line-height: 1.5;
          color: var(--text);
        }
        [data-testid="persona-studio-page"] :is(input[type="text"], input[type="number"], input:not([type])) {
          height: auto;
          min-height: calc(var(--card-pad) * 3.5);
        }
        [data-testid="persona-studio-page"] .ps-save-row {
          border-block: 1px solid var(--panel-border);
          padding-block: calc(var(--card-pad) / 2);
        }
        [data-testid="persona-studio-page"] .ps-projection-nav {
          border: 1px solid var(--panel-border);
          border-radius: var(--radius-micro);
          background: color-mix(in srgb, var(--chip-bg) 70%, var(--panel-bg));
        }
        [data-testid="persona-studio-page"] .ps-projection-nav .pill-tab {
          font-weight: 600;
        }
        [data-testid="persona-studio-page"] .ps-form-section {
          background: color-mix(in srgb, var(--panel-bg) 92%, var(--text));
        }
        [data-testid="persona-studio-page"] .ps-section-toggle {
          padding: var(--card-pad) var(--shell-gap);
          border-radius: inherit;
        }
        [data-testid="persona-studio-page"] .ps-form-section[data-open="true"] .ps-section-toggle {
          border-bottom: 1px solid var(--panel-border);
          border-bottom-left-radius: 0;
          border-bottom-right-radius: 0;
        }
        [data-testid="persona-studio-page"] .ps-section-fields {
          padding: var(--shell-gap);
        }
        [data-testid="persona-studio-page"] .ps-section-fields > * + * {
          margin-top: var(--shell-gap);
        }
        [data-testid="persona-studio-page"] .ps-section-fields :is(input, textarea, select) {
          font-weight: 400;
        }
      `}</style>
      <PersonaStudioActionChipStyles />
      <h1 className="sr-only">Persona Studio</h1>
      <div
        data-testid="persona-studio-workspace"
        data-layout="assistant-configuration"
      >
        <FrameCard refractiveFallback shimmerMode="subtle" data-testid="persona-studio-assistant-frame" ariaLabel="Studio Assistant">
          <div className="flex min-h-0 flex-1 flex-col gap-4">
            <header className="flex flex-wrap items-start justify-between gap-3 border-b pb-3" style={{ borderColor: "var(--panel-border)" }}>
              <div>
                <h2 className="text-base font-semibold">Studio Assistant</h2>
                <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Deterministic local draft editing and ephemeral preview.</p>
              </div>
              <Badge className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]" style={{ borderColor: "var(--panel-border)" }}>Local only</Badge>
            </header>
            <div className="flex gap-1" role="tablist" aria-label="Studio Assistant mode">
              {(["build", "test"] as const).map((mode) => (
                <button key={mode} type="button" role="tab" aria-selected={assistantMode === mode} onClick={() => setAssistantMode(mode)} className="pill-tab min-w-0 flex-1 px-3 py-2 text-sm capitalize" data-state={assistantMode === mode ? "active" : "inactive"}>{mode}</button>
              ))}
            </div>
            {assistantMode === "build" ? (
              <div className="flex min-h-0 flex-1 flex-col gap-4" data-testid="persona-studio-build-mode">
                <div className="rounded-[var(--tile-radius)] border px-3 py-3 text-sm leading-6" style={{ borderColor: "var(--panel-border)", background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)" }}>
                  <p className="font-medium">Bounded configurator</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">Supports the approved prototype’s typed changes for tone, model, temperature, web/email, voice, and retrieval. It never calls a provider or saves for you.</p>
                </div>
                <div className="min-h-0 flex-1 space-y-3 overflow-y-auto" data-testid="persona-studio-build-transcript" aria-live="polite">
                  {buildMessages.length === 0 ? <p className="text-sm text-[var(--muted)]">Describe a supported change, such as “make this more analytical and use Claude.”</p> : buildMessages.map((message) => (
                    <article key={message.id} className="space-y-3 border-b pb-3 last:border-b-0" style={{ borderColor: "var(--panel-border)" }}>
                      <div className="ml-auto max-w-[92%] rounded-[var(--tile-radius)] border px-3 py-2 text-sm" style={{ borderColor: "var(--panel-border)", background: "color-mix(in oklab, var(--accent) 8%, var(--panel-bg))" }}>{message.request}</div>
                      <div className="rounded-[var(--tile-radius)] border px-3 py-3 text-sm" style={{ borderColor: "var(--panel-border)", background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)" }}>
                        <p>{message.response}</p>
                        {message.changes.length > 0 ? <button type="button" onClick={() => focusChanges(message.changes)} className="mt-2 text-left text-xs font-medium text-[var(--accent)] underline underline-offset-2">{message.changes.map((change) => change.label).join(" · ")}</button> : null}
                      </div>
                    </article>
                  ))}
                </div>
                <form className="space-y-2 border-t pt-3" style={{ borderColor: "var(--panel-border)" }} onSubmit={handleBuildSubmit}>
                  <label className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]" htmlFor="persona-studio-build-input">Describe a draft change</label>
                  <Textarea id="persona-studio-build-input" aria-label="Describe a supported draft change" value={buildInput} onChange={(event) => setBuildInput(event.target.value)} placeholder="e.g. Make this more analytical and use Claude" className="min-h-[88px] resize-y" />
                  <div className="flex justify-end"><Button {...personaStudioActionChip("primary")} type="submit" variant="ghost" disabled={!buildInput.trim()}>Apply locally</Button></div>
                </form>
              </div>
            ) : (
              <div className="flex min-h-0 flex-1 flex-col" data-testid="persona-studio-test-mode">
                <div className="mb-3 rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5 text-[var(--muted)]" style={{ borderColor: "var(--panel-border)" }}>Test is an ephemeral, draft-aware preview. It creates no Guardian thread, provider request, memory write, or saved history.</div>
                <PersonaPreviewPanel profile={selectedProfile} embedded />
              </div>
            )}
          </div>
        </FrameCard>

        <FrameCard refractiveFallback shimmerMode="subtle" data-testid="persona-studio-configuration-frame" ariaLabel="Configuration">
          <div className="flex min-h-0 flex-1 flex-col">
            <header className="ps-configuration-header space-y-[var(--card-pad)] border-b pb-[var(--card-pad)]" style={{ borderColor: "var(--panel-border)" }}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-2xl font-semibold tracking-tight">Configuration</h2>
                  <p className="mt-1 text-xs leading-5 text-[var(--muted)]">One local draft projected as Form, Manifest, or effective inspection.</p>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild><Button {...personaStudioActionChip("selector", "max-w-[15rem] justify-between gap-2")} variant="ghost" type="button" data-testid="persona-studio-profile-selector-trigger"><span className="truncate">{selectedProfile.name}</span><span aria-hidden>⌄</span></Button></DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-64" data-testid="persona-studio-profile-selector-list">
                    <div className="px-2 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Persona Profiles</div>
                    {profiles.map((profile) => <DropdownMenuItem key={profile.id} onClick={() => setSelectedProfileId(profile.id)} className="flex flex-col items-start gap-1"><span>{profile.name}</span><span className="text-xs text-[var(--muted)]">{profile.id === selectedProfile.id ? "Current draft" : profile.description}</span></DropdownMenuItem>)}
                    <div role="separator" className="my-1 h-px bg-[var(--panel-border)]" />
                    <DropdownMenuItem onClick={saveSelectedProfileAsNew} data-testid="persona-studio-action-save-as-new">Duplicate as new</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <div className="ps-save-row flex flex-wrap items-center justify-between gap-[var(--card-pad)]">
                <span className="text-xs font-medium text-[var(--muted)]" data-testid="persona-studio-save-status" data-saved-revision={savedRevision ?? ""}>{status}</span>
                <div className="flex flex-wrap items-center gap-2">
                  <Button {...personaStudioActionChip("reset")} type="button" variant="ghost" size="sm" onClick={resetSelectedProfile} disabled={!hasSavedVersion || !isDirty} data-testid="persona-studio-action-reset">Revert</Button>
                  <Button {...personaStudioActionChip("primary")} type="button" variant="ghost" size="sm" onClick={saveSelectedProfile} disabled={!isDirty} data-testid="persona-studio-action-save">Save</Button>
                </div>
              </div>
              <div className="ps-projection-nav flex gap-1" role="tablist" aria-label="Configuration projection">
                {(["form", "manifest", "effective"] as const).map((mode) => <button key={mode} type="button" role="tab" aria-selected={configurationMode === mode} onClick={() => setConfigurationMode(mode)} className="pill-tab min-w-0 flex-1 px-3 py-2 text-sm capitalize" data-state={configurationMode === mode ? "active" : "inactive"}>{mode}</button>)}
              </div>
            </header>

            <div className="min-h-0 flex-1 overflow-y-auto pt-[var(--card-pad)]" data-testid="persona-studio-configuration-viewport" data-saved-profile-id={hasSavedVersion ? selectedProfile.id : ""} data-draft-state={isDirty ? "dirty" : "clean"}>
              {configurationMode === "form" ? (
                <div data-testid="persona-studio-form" className="space-y-[var(--card-pad)]">
                  <FormSection id="identity" title="Identity" summary="Portable name and description for this Persona Profile." open={openSections.identity} highlighted={false} onToggle={() => toggleSection("identity")}>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-name"><span>Persona name</span><Input id="persona-studio-name" aria-label="Persona name" value={config.identity.name} onChange={(event) => updateConfig((current) => ({ ...current, identity: { ...current.identity, name: event.target.value } }))} placeholder="Enter persona name" /></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-description"><span>Description</span><Textarea id="persona-studio-description" aria-label="Persona description" value={config.identity.description} onChange={(event) => updateConfig((current) => ({ ...current, identity: { ...current.identity, description: event.target.value } }))} rows={3} className="min-h-[88px] resize-y" /></FieldLabel>
                    </div>
                  </FormSection>
                  <FormSection id="prompt" title="Behavior / Prompt" summary="Authored prompt guidance only; it does not execute an assistant." open={openSections.prompt} highlighted={sectionIsHighlighted("prompt")} onToggle={() => toggleSection("prompt")}>
                    <FieldLabel htmlFor="persona-studio-system-prompt" highlighted={fieldIsHighlighted("prompt.systemPrompt")}><span>System prompt</span><Textarea id="persona-studio-system-prompt" value={config.prompt.systemPrompt} onChange={(event) => updateConfig((current) => ({ ...current, prompt: { ...current.prompt, systemPrompt: event.target.value } }))} rows={5} className="min-h-[130px] resize-y" /></FieldLabel>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-style-notes" highlighted={fieldIsHighlighted("prompt.styleNotes")}><span>Style notes</span><Textarea id="persona-studio-style-notes" value={config.prompt.styleNotes} onChange={(event) => updateConfig((current) => ({ ...current, prompt: { ...current.prompt, styleNotes: event.target.value } }))} rows={4} className="min-h-[106px] resize-y" /></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-directives" highlighted={fieldIsHighlighted("prompt.directives")}><span>Directives</span><Textarea id="persona-studio-directives" value={config.prompt.directives} onChange={(event) => updateConfig((current) => ({ ...current, prompt: { ...current.prompt, directives: event.target.value } }))} rows={4} className="min-h-[106px] resize-y" /></FieldLabel>
                    </div>
                  </FormSection>
                  <FormSection id="model" title="Model" summary="Requested provider and model values; availability is not resolved here." open={openSections.model} highlighted={sectionIsHighlighted("model")} onToggle={() => toggleSection("model")}>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-model-provider" highlighted={fieldIsHighlighted("model.provider")}><span>Provider</span><select id="persona-studio-model-provider" aria-label="Model provider" className="h-9 w-full rounded-md border px-3 text-sm" style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }} value={config.model.provider} onChange={(event) => updateConfig((current) => ({ ...current, model: { ...current.model, provider: event.target.value } }))}><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="google">Google</option><option value="local">Local</option></select></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-model-name" highlighted={fieldIsHighlighted("model.model")}><span>Model</span><Input id="persona-studio-model-name" aria-label="Model" value={config.model.model} onChange={(event) => updateConfig((current) => ({ ...current, model: { ...current.model, model: event.target.value } }))} /></FieldLabel>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-temperature" highlighted={fieldIsHighlighted("model.temperature")}><span>Temperature · {config.model.temperature.toFixed(2)}</span><input id="persona-studio-temperature" className="material-slider w-full" type="range" min="0" max="2" step="0.1" value={config.model.temperature} onChange={(event) => updateConfig((current) => ({ ...current, model: { ...current.model, temperature: Number(event.target.value) } }))} /></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-max-tokens"><span>Max tokens</span><Input id="persona-studio-max-tokens" type="number" value={config.model.maxTokens} onChange={(event) => updateConfig((current) => ({ ...current, model: { ...current.model, maxTokens: Number(event.target.value) || 0 } }))} /></FieldLabel>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-top-k"><span>Top K</span><Input id="persona-studio-top-k" type="number" value={config.model.topK} onChange={(event) => updateConfig((current) => ({ ...current, model: { ...current.model, topK: Number(event.target.value) || 0 } }))} /></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-top-p"><span>Top P</span><Input id="persona-studio-top-p" type="number" step="0.01" value={config.model.topP} onChange={(event) => updateConfig((current) => ({ ...current, model: { ...current.model, topP: Number(event.target.value) || 0 } }))} /></FieldLabel>
                    </div>
                  </FormSection>
                  <FormSection id="voice" title="Voice" summary="Requested voice settings. Discovery remains separately bounded by its existing surface." open={openSections.voice} highlighted={sectionIsHighlighted("voice")} onToggle={() => toggleSection("voice")}><PersonaVoicePanel config={config} onChange={(next) => updateConfig(() => next)} /></FormSection>
                  <FormSection id="capabilities" title="Capabilities" summary="Requested permissions are not proof of an available or granted capability." open={openSections.capabilities} highlighted={sectionIsHighlighted("capabilities")} onToggle={() => toggleSection("capabilities")}>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {(["web", "email", "calendar", "cli", "filesystem"] as const).map((permission) => <label key={permission} className="flex items-center gap-2 rounded-[var(--radius-micro)] border px-3 py-2 text-sm" style={{ borderColor: fieldIsHighlighted(`capabilities.permissions.${permission}`) ? "var(--accent)" : "var(--panel-border)" }}><input type="checkbox" checked={config.tools.permissions[permission]} onChange={(event) => updateConfig((current) => ({ ...current, tools: { ...current.tools, permissions: { ...current.tools.permissions, [permission]: event.target.checked } } }))} />{permission === "cli" ? "CLI" : permission.charAt(0).toUpperCase() + permission.slice(1)} requested</label>)}
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-pinned-tools"><span>Pinned tools (comma-separated)</span><Textarea id="persona-studio-pinned-tools" value={config.tools.pinnedTools.join(", ")} onChange={(event) => updateConfig((current) => ({ ...current, tools: { ...current.tools, pinnedTools: parseCommaSeparated(event.target.value) } }))} rows={3} className="min-h-[82px] resize-y" /></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-allowed-tools"><span>Allowed tools (comma-separated)</span><Textarea id="persona-studio-allowed-tools" value={config.tools.allowedTools.join(", ")} onChange={(event) => updateConfig((current) => ({ ...current, tools: { ...current.tools, allowedTools: parseCommaSeparated(event.target.value) } }))} rows={3} className="min-h-[82px] resize-y" /></FieldLabel>
                    </div>
                  </FormSection>
                  <FormSection id="retrieval" title="Retrieval" summary="An authored preference only; Studio does not execute retrieval." open={openSections.retrieval} highlighted={sectionIsHighlighted("retrieval")} onToggle={() => toggleSection("retrieval")}>
                    <label className="flex items-center gap-2 text-sm" data-highlighted={fieldIsHighlighted("retrieval.enabled") ? "true" : "false"}><input type="checkbox" checked={config.retrieval.enabled} onChange={(event) => updateConfig((current) => ({ ...current, retrieval: { ...current.retrieval, enabled: event.target.checked } }))} />Retrieval requested</label>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FieldLabel htmlFor="persona-studio-retrieval-mode"><span>Mode</span><select id="persona-studio-retrieval-mode" className="h-9 w-full rounded-md border px-3 text-sm" style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)" }} value={config.retrieval.mode} onChange={(event) => updateConfig((current) => ({ ...current, retrieval: { ...current.retrieval, mode: event.target.value } }))}><option value="hybrid">Hybrid</option><option value="semantic">Semantic</option><option value="keyword">Keyword</option></select></FieldLabel>
                      <FieldLabel htmlFor="persona-studio-retrieval-top-k"><span>Top K</span><Input id="persona-studio-retrieval-top-k" type="number" value={config.retrieval.topK} onChange={(event) => updateConfig((current) => ({ ...current, retrieval: { ...current.retrieval, topK: Number(event.target.value) || 0 } }))} /></FieldLabel>
                    </div>
                    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={config.retrieval.rerank} onChange={(event) => updateConfig((current) => ({ ...current, retrieval: { ...current.retrieval, rerank: event.target.checked } }))} />Request reranking</label>
                  </FormSection>
                  <FormSection id="bindings" title="Activation & Bindings" summary="Server-owned environmental authority is deliberately outside the portable manifest." open={openSections.bindings} highlighted={false} onToggle={() => toggleSection("bindings")}>
                    <div className="space-y-3 rounded-[var(--tile-radius)] border px-3 py-3 text-sm leading-6" style={{ borderColor: "var(--panel-border)", background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)" }}><p>Project pins, invocation aliases, connector grants, credentials, and runtime authorization are not editable in this workspace.</p><p className="text-xs text-[var(--muted)]">Bindings: Not resolved. No authoritative Binding editor or effective-config resolver is available here.</p></div>
                  </FormSection>
                </div>
              ) : null}
              {configurationMode === "manifest" ? <section data-testid="persona-studio-manifest" className="space-y-3 py-3"><div><h3 className="text-sm font-semibold">Writable authored manifest</h3><p className="mt-1 text-xs leading-5 text-[var(--muted)]">This JSON is the same local draft as Form. Revision, bindings, credentials, and runtime grants are rejected.</p></div><Textarea aria-label="Persona manifest JSON" value={manifestBuffer} onChange={(event) => handleManifestChange(event.target.value)} spellCheck={false} className="min-h-[28rem] font-mono text-xs leading-5" />{manifestError ? <p role="alert" className="text-xs leading-5 text-[var(--accent)]" data-testid="persona-studio-manifest-error">Manifest not applied: {manifestError}</p> : <p className="text-xs text-[var(--muted)]">Valid JSON updates the local draft; Save remains explicit.</p>}</section> : null}
              {configurationMode === "effective" ? <section data-testid="persona-studio-effective" className="space-y-4 py-3"><div><h3 className="text-sm font-semibold">Effective inspection</h3><p className="mt-1 text-xs leading-5 text-[var(--muted)]">This route has no authoritative effective-configuration resolver. Requested values below are not runtime truth.</p></div><dl className="space-y-2 text-sm">{[["Requested model", `${config.model.provider} / ${config.model.model}`], ["Requested web capability", config.tools.permissions.web ? "Requested" : "Not requested"], ["Requested retrieval", config.retrieval.enabled ? "Requested" : "Not requested"]].map(([label, value]) => <div key={label} className="grid gap-1 rounded-[var(--radius-micro)] border px-3 py-3 sm:grid-cols-[minmax(10rem,0.7fr)_1fr]" style={{ borderColor: "var(--panel-border)" }}><dt className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">{label}</dt><dd>{value}</dd></div>)}</dl><div className="rounded-[var(--tile-radius)] border px-3 py-3 text-sm leading-6" style={{ borderColor: "var(--panel-border)", background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)" }}><p className="font-medium">Unavailable to resolve here</p><p className="mt-1 text-xs text-[var(--muted)]">Provider availability, model availability, connector authorization and health, Project bindings, capability grants, and runtime effectiveness are Not resolved.</p></div></section> : null}
            </div>
          </div>
        </FrameCard>
      </div>
    </main>
  );
}
