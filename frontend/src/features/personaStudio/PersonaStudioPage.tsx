import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type PersonaConfig,
  type PersonaProfileDraft,
  type ToolsSettings,
  usePersonaStudioLocalDraftState,
} from "./personaStudioStore";
import DiagnosticsPanel from "./components/DiagnosticsPanel";
import TruthMatrix from "./components/TruthMatrix";

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
      className="pill-tab min-w-0 flex-1 px-4 py-3.5 text-[0.95rem]"
    >
      {children}
    </button>
  );
}

const TABS = [
  "Identity",
  "Model",
  "Voice",
  "Prompt",
  "Tools",
  "Retrieval",
  "Truth Matrix",
] as const;

const UTILITY_TABS = ["Profiles", "Diagnostics"] as const;
const EPHEMERAL_SCENARIO_CHIPS = ["Coding", "Research", "Planning", "Casual Help"] as const;

type UtilityTab = (typeof UTILITY_TABS)[number];

type EphemeralChatDraftSnapshot = {
  signature: string;
  personaName: string;
  description: string;
  modelLine: string;
  temperatureLine: string;
  systemPrompt: string;
  styleNotes: string;
  directives: string;
  retrieval: string;
  pinnedTools: string;
  allowedTools: string;
  voice: string;
};

type EphemeralChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  draftSignature: string;
  draftSnapshot: EphemeralChatDraftSnapshot;
};

function formatList(values: string[]) {
  return values.length > 0 ? values.join(", ") : "None";
}

function buildEphemeralChatDraftSnapshot(
  profile: PersonaProfileDraft | null
): EphemeralChatDraftSnapshot {
  const config = profile?.config ?? null;
  const personaName = profile?.name || config?.identity?.name || "Persona";
  const description =
    profile?.description || config?.identity?.description || "No description set.";
  const modelLine = config
    ? `${config.model.provider} / ${config.model.model}`
    : "No model selected.";
  const temperatureLine = config ? String(config.model.temperature) : "n/a";
  const systemPrompt = config?.prompt.systemPrompt || "No system prompt set.";
  const styleNotes = config?.prompt.styleNotes || "No style notes set.";
  const directives = config?.prompt.directives || "No directives set.";
  const retrieval = config
    ? config.retrieval.enabled
      ? `Enabled: ${config.retrieval.mode} / topK ${config.retrieval.topK} / rerank ${
          config.retrieval.rerank ? "on" : "off"
        }`
      : "Disabled"
    : "Unavailable";
  const pinnedTools = config ? formatList(config.tools.pinnedTools) : "None";
  const allowedTools = config ? formatList(config.tools.allowedTools) : "None";
  const voice = config
    ? config.voice.enabled
      ? `${config.voice.provider} / ${config.voice.voicePreset}`
      : "Disabled"
    : "Unavailable";

  return {
    signature: JSON.stringify({
      personaName,
      description,
      modelLine,
      temperatureLine,
      systemPrompt,
      styleNotes,
      directives,
      retrieval,
      pinnedTools,
      allowedTools,
      voice,
    }),
    personaName,
    description,
    modelLine,
    temperatureLine,
    systemPrompt,
    styleNotes,
    directives,
    retrieval,
    pinnedTools,
    allowedTools,
    voice,
  };
}

function getEphemeralPromptTone(prompt: string) {
  const normalizedPrompt = prompt.trim().toLowerCase();
  if (!normalizedPrompt) {
    return "I will keep the reply anchored to the current persona draft and stay inside the studio harness.";
  }
  if (/(code|bug|test|refactor|debug|implement)/.test(normalizedPrompt)) {
    return "I will keep this implementation-first and explicit about tradeoffs.";
  }
  if (/(research|cite|source|evidence|fact)/.test(normalizedPrompt)) {
    return "I will separate facts from assumptions and call out any missing evidence.";
  }
  if (/(plan|roadmap|next step|strategy)/.test(normalizedPrompt)) {
    return "I will turn this into a short, actionable plan.";
  }
  if (/(hello|hi|casual|chat|conversation)/.test(normalizedPrompt)) {
    return "I will keep the tone warm, direct, and low-friction.";
  }
  return "I will answer from the current draft without leaving Persona Studio.";
}

function buildEphemeralChatReply(
  prompt: string,
  draftSnapshot: EphemeralChatDraftSnapshot,
  turnNumber: number
) {
  const trimmedPrompt = prompt.trim().replace(/\s+/g, " ");
  const promptLine = trimmedPrompt ? `You said: "${trimmedPrompt}".` : "You sent an empty prompt.";
  const turnLine =
    turnNumber === 1
      ? "This is the first temporary turn in this Studio session."
      : `This is temporary turn ${turnNumber} in the current Studio session.`;

  return [
    `${draftSnapshot.personaName} is the active persona draft right now.`,
    promptLine,
    getEphemeralPromptTone(trimmedPrompt),
    `Current draft snapshot: ${draftSnapshot.modelLine}; temperature ${draftSnapshot.temperatureLine}; retrieval ${draftSnapshot.retrieval}; voice ${draftSnapshot.voice}.`,
    turnLine,
    "This conversation stays inside Persona Studio and clears on reload.",
  ].join(" ");
}

function EphemeralChatHarness({ profile }: { profile: PersonaProfileDraft | null }) {
  const [ephemeralMessages, setEphemeralMessages] = React.useState<EphemeralChatMessage[]>([]);
  const [ephemeralPrompt, setEphemeralPrompt] = React.useState("");
  const [isResponding, setIsResponding] = React.useState(false);
  const messageIdRef = React.useRef(0);
  const sessionVersionRef = React.useRef(0);
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const currentDraftSnapshot = React.useMemo(
    () => buildEphemeralChatDraftSnapshot(profile),
    [profile]
  );

  const lastAssistantDraftSignature = React.useMemo(() => {
    for (let index = ephemeralMessages.length - 1; index >= 0; index -= 1) {
      const entry = ephemeralMessages[index];
      if (entry.role === "assistant") {
        return entry.draftSignature;
      }
    }

    return null;
  }, [ephemeralMessages]);

  const draftChangedSinceLastReply =
    Boolean(lastAssistantDraftSignature) &&
    lastAssistantDraftSignature !== currentDraftSnapshot.signature;

  const clearEphemeralSession = React.useCallback(() => {
    sessionVersionRef.current += 1;
    messageIdRef.current = 0;
    setEphemeralMessages([]);
    setEphemeralPrompt("");
    setIsResponding(false);
    inputRef.current?.focus();
  }, []);

  const sendEphemeralPrompt = React.useCallback(
    async (message: string) => {
      const trimmedMessage = message.trim();
      if (!trimmedMessage || isResponding) {
        return;
      }

      const sessionVersionAtSend = sessionVersionRef.current;
      const draftSnapshotAtSend = buildEphemeralChatDraftSnapshot(profile);
      const nextTurnNumber =
        ephemeralMessages.filter((entry) => entry.role === "assistant").length + 1;
      const userMessage: EphemeralChatMessage = {
        id: `ephemeral-message-${messageIdRef.current + 1}`,
        role: "user",
        content: trimmedMessage,
        draftSignature: draftSnapshotAtSend.signature,
        draftSnapshot: draftSnapshotAtSend,
      };

      messageIdRef.current += 1;
      setIsResponding(true);
      setEphemeralMessages((previous) => [...previous, userMessage]);
      setEphemeralPrompt("");

      await Promise.resolve();

      if (sessionVersionRef.current !== sessionVersionAtSend) {
        return;
      }

      const assistantMessage: EphemeralChatMessage = {
        id: `ephemeral-message-${messageIdRef.current + 1}`,
        role: "assistant",
        content: buildEphemeralChatReply(trimmedMessage, draftSnapshotAtSend, nextTurnNumber),
        draftSignature: draftSnapshotAtSend.signature,
        draftSnapshot: draftSnapshotAtSend,
      };

      messageIdRef.current += 1;
      setEphemeralMessages((previous) => [...previous, assistantMessage]);
      setIsResponding(false);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    },
    [ephemeralMessages, isResponding, profile]
  );

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendEphemeralPrompt(ephemeralPrompt);
  };

  const hasMessages = ephemeralMessages.length > 0;

  return (
    <Card
      className="bezel-none rounded-2xl border"
      role="region"
      aria-label="Persona Studio ephemeral chat harness"
      data-testid="persona-studio-ephemeral-chat-harness"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="space-y-3 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base">Ephemeral Chat Harness</CardTitle>
            <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
              Temporary, isolated, non-runtime. Uses the current draft, including unsaved edits,
              and clears when this Studio session is reloaded.
            </p>
          </div>
          <Badge
            variant="outline"
            className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
            style={{ borderColor: "var(--panel-border)" }}
          >
            Studio-only
          </Badge>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {EPHEMERAL_SCENARIO_CHIPS.map((prompt) => (
            <Button
              key={prompt}
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void sendEphemeralPrompt(prompt)}
              disabled={isResponding}
            >
              {prompt}
            </Button>
          ))}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={clearEphemeralSession}
            disabled={!hasMessages && !ephemeralPrompt.trim()}
          >
            Clear Session
          </Button>
        </div>
        <form className="flex flex-wrap gap-2" onSubmit={handleSubmit}>
          <Input
            ref={inputRef}
            value={ephemeralPrompt}
            onChange={(event) => setEphemeralPrompt(event.target.value)}
            placeholder="Type a temporary message"
            aria-label="Ephemeral chat prompt"
            className="min-w-0 flex-1"
            disabled={isResponding}
          />
          <Button type="submit" disabled={!ephemeralPrompt.trim() || isResponding}>
            Send
          </Button>
        </form>
        <div className="space-y-1 text-xs leading-5" style={{ color: "var(--muted)" }}>
          <p>
            No Guardian thread creation, no memory writes, no runtime conversation history, and
            no artifact lineage.
          </p>
          <p>
            This harness is session-local only. A full reload clears the temporary transcript.
          </p>
        </div>
        {draftChangedSinceLastReply ? (
          <p className="text-xs font-medium leading-5" style={{ color: "var(--accent)" }}>
            Draft changed since the last reply. New turns use the current draft; earlier replies
            remain as historical session turns.
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="pt-0">
        <div
          className="space-y-3 rounded-2xl border p-3"
          data-testid="persona-studio-ephemeral-chat-transcript"
          aria-live="polite"
          aria-busy={isResponding}
          style={{
            background: "color-mix(in srgb, var(--panel-bg) 98%, transparent)",
            borderColor: "var(--panel-border)",
          }}
        >
          {hasMessages ? (
            <>
              {isResponding ? (
                <div className="flex justify-start">
                  <div
                    className="max-w-[95%] rounded-2xl border px-3 py-3 text-sm"
                    style={{
                      background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
                      borderColor: "var(--panel-border)",
                    }}
                  >
                    <div
                      className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Ephemeral chat harness
                    </div>
                    <p className="mt-1 leading-6">Generating a draft-aware reply…</p>
                  </div>
                </div>
              ) : null}
              {ephemeralMessages.map((entry) =>
                entry.role === "user" ? (
                  <div key={entry.id} className="flex justify-end">
                    <div
                      className="max-w-[85%] rounded-2xl border px-3 py-2 text-sm"
                      style={{
                        background: "color-mix(in srgb, var(--accent) 10%, var(--panel-bg))",
                        borderColor: "color-mix(in oklab, var(--accent) 18%, var(--panel-border))",
                      }}
                    >
                      <div
                        className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                        style={{ color: "var(--muted)" }}
                      >
                        You
                      </div>
                      <p className="mt-1 leading-6">{entry.content}</p>
                    </div>
                  </div>
                ) : (
                  <div key={entry.id} className="flex justify-start">
                    <div
                      className="max-w-[95%] rounded-2xl border px-3 py-3 text-sm"
                      style={{
                        background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
                        borderColor: "var(--panel-border)",
                      }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.16em]">
                          Ephemeral assistant
                        </div>
                        <Badge
                          variant="outline"
                          className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                          style={{ borderColor: "var(--panel-border)" }}
                        >
                          {entry.draftSignature === currentDraftSnapshot.signature
                            ? "Current draft"
                            : "Earlier draft"}
                        </Badge>
                      </div>
                      <p className="mt-2 leading-6">{entry.content}</p>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        <div className="space-y-1">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Persona
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.personaName}</p>
                        </div>
                        <div className="space-y-1">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Model
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.modelLine}</p>
                        </div>
                        <div className="space-y-1">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Temperature
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.temperatureLine}</p>
                        </div>
                        <div className="space-y-1">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Voice
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.voice}</p>
                        </div>
                        <div className="space-y-1 sm:col-span-2">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Prompt
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.systemPrompt}</p>
                        </div>
                        <div className="space-y-1 sm:col-span-2">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Style Notes
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.styleNotes}</p>
                        </div>
                        <div className="space-y-1 sm:col-span-2">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Directives
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.directives}</p>
                        </div>
                        <div className="space-y-1">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Retrieval
                          </div>
                          <p className="leading-6">{entry.draftSnapshot.retrieval}</p>
                        </div>
                        <div className="space-y-1">
                          <div
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Tools
                          </div>
                          <p className="leading-6">
                            Pinned: {entry.draftSnapshot.pinnedTools} | Allowed:{" "}
                            {entry.draftSnapshot.allowedTools}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              )}
            </>
          ) : (
            <div className="space-y-2">
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                No ephemeral messages yet.
              </p>
              <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                Start a temporary conversation with the active persona draft. The transcript stays
                local to this Studio session and is not part of runtime chat history.
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function IdentityEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
          Persona Name
        </label>
        <Input
          className="h-10"
          value={config.identity.name}
          onChange={(e) =>
            onChange({
              ...config,
              identity: { ...config.identity, name: e.target.value },
            })
          }
          placeholder="Enter persona name"
        />
      </div>
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
          Description
        </label>
        <Textarea
          className="min-h-[140px] resize-y"
          value={config.identity.description}
          onChange={(e) =>
            onChange({
              ...config,
              identity: { ...config.identity, description: e.target.value },
            })
          }
          rows={5}
          placeholder="Describe this persona"
        />
      </div>
    </div>
  );
}

function ModelEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  const providerId = "persona-studio-model-provider";
  const modelId = "persona-studio-model-id";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor={providerId}>
            Provider
          </label>
          <select
            id={providerId}
            className="w-full h-9 px-3 rounded-md border text-sm"
            style={{
              background: "transparent",
              borderColor: "var(--panel-border)",
              color: "var(--text)",
            }}
            value={config.model.provider}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, provider: e.target.value },
              })
            }
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google</option>
            <option value="local">Local</option>
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor={modelId}>
            Model
          </label>
          <Input
            id={modelId}
            value={config.model.model}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, model: e.target.value },
              })
            }
            placeholder="e.g., gpt-4o"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Temperature</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={config.model.temperature}
              onChange={(e) =>
                onChange({
                  ...config,
                  model: { ...config.model, temperature: parseFloat(e.target.value) },
                })
              }
              className="flex-1"
            />
            <span className="text-sm w-12 text-right">{config.model.temperature}</span>
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Max Tokens</label>
          <Input
            type="number"
            value={config.model.maxTokens}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, maxTokens: parseInt(e.target.value) || 0 },
              })
            }
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Generation Top K</label>
          <Input
            type="number"
            value={config.model.topK}
            onChange={(e) =>
              onChange({
                ...config,
                model: { ...config.model, topK: parseInt(e.target.value) || 0 },
              })
            }
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Top P</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.model.topP}
              onChange={(e) =>
                onChange({
                  ...config,
                  model: { ...config.model, topP: parseFloat(e.target.value) },
                })
              }
              className="flex-1"
            />
            <span className="text-sm w-12 text-right">{config.model.topP}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function VoiceEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={config.voice.enabled}
            onChange={(e) =>
              onChange({
                ...config,
                voice: { ...config.voice, enabled: e.target.checked },
              })
            }
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
        </label>
        <span className="text-sm font-medium">Voice Enabled</span>
      </div>

      {config.voice.enabled && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Provider</label>
              <select
                className="w-full h-9 px-3 rounded-md border text-sm"
                style={{
                  background: "transparent",
                  borderColor: "var(--panel-border)",
                  color: "var(--text)",
                }}
                value={config.voice.provider}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, provider: e.target.value },
                  })
                }
              >
                <option value="elevenlabs">ElevenLabs</option>
                <option value="aws">AWS Polly</option>
                <option value="google">Google TTS</option>
                <option value="azure">Azure Speech</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Voice Preset / Voice ID</label>
              <Input
                value={config.voice.voicePreset}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, voicePreset: e.target.value },
                  })
                }
                placeholder="e.g., rachel"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Speed</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={config.voice.speed}
                  onChange={(e) =>
                    onChange({
                      ...config,
                      voice: { ...config.voice, speed: parseFloat(e.target.value) },
                    })
                  }
                  className="flex-1"
                />
                <span className="text-sm w-12 text-right">{config.voice.speed}x</span>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Wake Word</label>
              <Input
                value={config.voice.wakeWord}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, wakeWord: e.target.value },
                  })
                }
                placeholder="e.g., Hey Guardian"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.voice.interruptible}
                onChange={(e) =>
                  onChange({
                    ...config,
                    voice: { ...config.voice, interruptible: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
            </label>
            <span className="text-sm font-medium">Interruptible</span>
          </div>
        </>
      )}
    </div>
  );
}

function PromptEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">System Prompt</label>
        <Textarea
          value={config.prompt.systemPrompt}
          onChange={(e) =>
            onChange({
              ...config,
              prompt: { ...config.prompt, systemPrompt: e.target.value },
            })
          }
          rows={6}
          placeholder="Enter the system prompt that defines this persona's behavior"
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">Style Notes</label>
        <Textarea
          value={config.prompt.styleNotes}
          onChange={(e) =>
            onChange({
              ...config,
              prompt: { ...config.prompt, styleNotes: e.target.value },
            })
          }
          rows={3}
          placeholder="Notes about tone, manner, and communication style"
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">Directives</label>
        <Textarea
          value={config.prompt.directives}
          onChange={(e) =>
            onChange({
              ...config,
              prompt: { ...config.prompt, directives: e.target.value },
            })
          }
          rows={3}
          placeholder="Operational directives and constraints"
        />
      </div>
    </div>
  );
}

function ToolsEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  const [newPinnedTool, setNewPinnedTool] = React.useState("");
  const [newAllowedTool, setNewAllowedTool] = React.useState("");
  const [newSkill, setNewSkill] = React.useState("");

  const addPinnedTool = () => {
    if (newPinnedTool.trim() && !config.tools.pinnedTools.includes(newPinnedTool.trim())) {
      onChange({
        ...config,
        tools: {
          ...config.tools,
          pinnedTools: [...config.tools.pinnedTools, newPinnedTool.trim()],
        },
      });
      setNewPinnedTool("");
    }
  };

  const removePinnedTool = (tool: string) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        pinnedTools: config.tools.pinnedTools.filter((t) => t !== tool),
      },
    });
  };

  const addAllowedTool = () => {
    if (newAllowedTool.trim() && !config.tools.allowedTools.includes(newAllowedTool.trim())) {
      onChange({
        ...config,
        tools: {
          ...config.tools,
          allowedTools: [...config.tools.allowedTools, newAllowedTool.trim()],
        },
      });
      setNewAllowedTool("");
    }
  };

  const removeAllowedTool = (tool: string) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        allowedTools: config.tools.allowedTools.filter((t) => t !== tool),
      },
    });
  };

  const addSkill = () => {
    if (newSkill.trim() && !config.tools.skills.includes(newSkill.trim())) {
      onChange({
        ...config,
        tools: {
          ...config.tools,
          skills: [...config.tools.skills, newSkill.trim()],
        },
      });
      setNewSkill("");
    }
  };

  const removeSkill = (skill: string) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        skills: config.tools.skills.filter((s) => s !== skill),
      },
    });
  };

  const togglePermission = (key: keyof ToolsSettings["permissions"]) => {
    onChange({
      ...config,
      tools: {
        ...config.tools,
        permissions: {
          ...config.tools.permissions,
          [key]: !config.tools.permissions[key],
        },
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <label className="text-sm font-medium">Pinned Tools</label>
        <div className="flex flex-wrap gap-2">
          {config.tools.pinnedTools.map((tool) => (
            <Badge
              key={tool}
              variant="outline"
              className="px-2 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {tool}
              <button
                type="button"
                onClick={() => removePinnedTool(tool)}
                className="ml-1.5 text-[var(--muted)] hover:text-[var(--text)]"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newPinnedTool}
            onChange={(e) => setNewPinnedTool(e.target.value)}
            placeholder="Add pinned tool"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && addPinnedTool()}
          />
          <Button type="button" size="sm" variant="ghost" onClick={addPinnedTool}>
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium">Allowed Tools</label>
        <div className="flex flex-wrap gap-2">
          {config.tools.allowedTools.map((tool) => (
            <Badge
              key={tool}
              variant="outline"
              className="px-2 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {tool}
              <button
                type="button"
                onClick={() => removeAllowedTool(tool)}
                className="ml-1.5 text-[var(--muted)] hover:text-[var(--text)]"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newAllowedTool}
            onChange={(e) => setNewAllowedTool(e.target.value)}
            placeholder="Add allowed tool"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && addAllowedTool()}
          />
          <Button type="button" size="sm" variant="ghost" onClick={addAllowedTool}>
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium">Skills</label>
        <div className="flex flex-wrap gap-2">
          {config.tools.skills.map((skill) => (
            <Badge
              key={skill}
              variant="outline"
              className="px-2 py-1 text-xs"
              style={{ borderColor: "var(--panel-border)" }}
            >
              {skill}
              <button
                type="button"
                onClick={() => removeSkill(skill)}
                className="ml-1.5 text-[var(--muted)] hover:text-[var(--text)]"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)}
            placeholder="Add skill"
            className="flex-1"
            onKeyDown={(e) => e.key === "Enter" && addSkill()}
          />
          <Button type="button" size="sm" variant="ghost" onClick={addSkill}>
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium">Permissions</label>
        <div className="grid grid-cols-2 gap-3">
          {(
            [
              ["web", "Web Access"],
              ["email", "Email"],
              ["calendar", "Calendar"],
              ["cli", "CLI"],
              ["filesystem", "Filesystem"],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`perm-${key}`}
                checked={config.tools.permissions[key]}
                onChange={() => togglePermission(key)}
                className="rounded"
              />
              <label htmlFor={`perm-${key}`} className="text-sm">
                {label}
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RetrievalEditor({
  config,
  onChange,
}: {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={config.retrieval.enabled}
            onChange={(e) =>
              onChange({
                ...config,
                retrieval: { ...config.retrieval, enabled: e.target.checked },
              })
            }
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
        </label>
        <span className="text-sm font-medium">Retrieval Enabled</span>
      </div>

      {config.retrieval.enabled && (
        <>
          <div className="space-y-2">
            <label className="text-sm font-medium">Retrieval Mode</label>
            <select
              className="w-full h-9 px-3 rounded-md border text-sm"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
              value={config.retrieval.mode}
              onChange={(e) =>
                onChange({
                  ...config,
                  retrieval: { ...config.retrieval, mode: e.target.value },
                })
              }
            >
              <option value="semantic">Semantic</option>
              <option value="hybrid">Hybrid</option>
              <option value="keyword">Keyword</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Retrieval Top K</label>
            <Input
              type="number"
              value={config.retrieval.topK}
              onChange={(e) =>
                onChange({
                  ...config,
                  retrieval: { ...config.retrieval, topK: parseInt(e.target.value) || 0 },
                })
              }
            />
            <p className="text-xs text-[var(--muted)]">
              Number of documents to retrieve (distinct from Generation Top K)
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.retrieval.rerank}
                onChange={(e) =>
                  onChange({
                    ...config,
                    retrieval: { ...config.retrieval, rerank: e.target.checked },
                  })
                }
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-[var(--panel-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
            </label>
            <span className="text-sm font-medium">Rerank Results</span>
          </div>
        </>
      )}
    </div>
  );
}

export default function PersonaStudioPage() {
  const {
    profiles,
    selectedProfileId,
    activeTab,
    selectedProfile,
    selectedSavedProfile,
    isDirty,
    hasSavedVersion,
    setSelectedProfileId,
    setActiveTab,
    updateSelectedProfile,
    saveSelectedProfile,
    saveSelectedProfileAsNew,
    resetSelectedProfile,
    resetAllLocalPersonaStudioData,
  } = usePersonaStudioLocalDraftState();

  const [isUtilityPaneOpen, setIsUtilityPaneOpen] = React.useState(true);
  const [utilityTab, setUtilityTab] = React.useState<UtilityTab>("Profiles");

  const currentConfig = selectedProfile?.config || null;

  const handleConfigChange = (newConfig: PersonaConfig) => {
    updateSelectedProfile((currentProfile) => ({
      ...currentProfile,
      name: newConfig.identity.name,
      description: newConfig.identity.description,
      config: newConfig,
    }));
  };

  const handleSave = () => {
    saveSelectedProfile();
  };

  const handleSaveAsNew = () => {
    saveSelectedProfileAsNew();
  };

  const handleReset = () => {
    resetSelectedProfile();
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case "Identity":
        return currentConfig ? (
          <IdentityEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Model":
        return currentConfig ? (
          <ModelEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Voice":
        return currentConfig ? (
          <VoiceEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Prompt":
        return currentConfig ? (
          <PromptEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Tools":
        return currentConfig ? (
          <ToolsEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Retrieval":
        return currentConfig ? (
          <RetrievalEditor config={currentConfig} onChange={handleConfigChange} />
        ) : null;
      case "Truth Matrix":
        return <TruthMatrix />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full w-full overflow-auto p-[var(--card-pad)]">
      <div className="flex h-full flex-col gap-6">
        <div
          className="flex flex-col gap-4"
          data-testid="persona-studio-page-header"
        >
          <div className="max-w-3xl space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight">Persona Studio</h1>
            <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
              Configure runtime persona profiles. This is for configuration only — no chat history or memory records are created.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div
              className="glass-pill flex min-w-0 flex-1 items-stretch gap-1.5 overflow-x-auto px-1"
              data-testid="persona-studio-section-tabs"
              style={
                {
                  "--pill-active-text": "var(--text-on-accent)",
                  "--pill-font": "0.92rem",
                  width: "100%",
                  justifyContent: "stretch",
                } as React.CSSProperties
              }
            >
              {TABS.map((tab) => (
                <TabButton
                  key={tab}
                  active={activeTab === tab}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </TabButton>
              ))}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsUtilityPaneOpen((value) => !value)}
              aria-label={isUtilityPaneOpen ? "Hide utility pane" : "Show utility pane"}
            >
              {isUtilityPaneOpen ? "Hide Utility Pane" : "Show Utility Pane"}
            </Button>
          </div>
        </div>

        <div
          className={`grid min-h-0 flex-1 gap-4 ${
            isUtilityPaneOpen ? "lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)]" : ""
          }`}
        >
          {isUtilityPaneOpen ? (
            <Card
              className="bezel-none flex min-h-0 flex-col overflow-hidden rounded-2xl border"
              role="complementary"
              aria-label="Persona Studio utility pane"
              data-testid="persona-studio-utility-pane"
              style={{
                background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
                borderColor: "var(--panel-border)",
              }}
            >
              <CardHeader className="space-y-3 pb-3">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">Utility Pane</CardTitle>
                  <Badge
                    variant="outline"
                    className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                    style={{ borderColor: "var(--panel-border)" }}
                  >
                    {utilityTab}
                  </Badge>
                </div>
                <div
                  className="glass-pill flex w-full items-stretch gap-1.5 overflow-x-auto px-1"
                  data-testid="persona-studio-utility-tabs"
                  style={
                    {
                      "--pill-active-text": "var(--text-on-accent)",
                      "--pill-font": "0.92rem",
                      width: "100%",
                      justifyContent: "stretch",
                    } as React.CSSProperties
                  }
                >
                  {UTILITY_TABS.map((tab) => (
                    <TabButton
                      key={tab}
                      active={utilityTab === tab}
                      onClick={() => setUtilityTab(tab)}
                    >
                      {tab}
                    </TabButton>
                  ))}
                </div>
              </CardHeader>
              <CardContent className="relative min-h-0 flex-1 pt-0">
                {utilityTab === "Profiles" ? (
                  <div
                    data-testid="persona-studio-utility-profiles-panel"
                    data-state="active"
                    className="relative space-y-2"
                  >
                    {profiles.map((profile) => (
                      <button
                        key={profile.id}
                        type="button"
                        onClick={() => {
                          setSelectedProfileId(profile.id);
                        }}
                        className={`w-full rounded-xl p-3 text-left transition-colors ${
                          profile.id === selectedProfileId
                            ? "border-2"
                            : "border border-transparent hover:border-[var(--panel-border)]"
                        }`}
                        style={{
                          background:
                            profile.id === selectedProfileId
                              ? "rgba(255,255,255,0.08)"
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
                        <p className="mt-1 line-clamp-2 text-xs" style={{ color: "var(--muted)" }}>
                          {profile.description}
                        </p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div
                    role="complementary"
                    aria-label="Persona Studio diagnostics"
                    data-testid="persona-studio-diagnostics"
                    data-state="active"
                    className="relative h-full"
                  >
                    <DiagnosticsPanel
                      profile={selectedProfile}
                      config={currentConfig}
                      isDirty={isDirty}
                      hasSavedVersion={hasSavedVersion}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          ) : null}

          <Card
            className="bezel-none flex min-h-0 flex-col rounded-2xl border"
            role="region"
            aria-label="Persona Studio editor"
            data-testid="persona-studio-editor"
            data-saved-profile-id={selectedSavedProfile?.id ?? ""}
            data-draft-state={isDirty ? "dirty" : "clean"}
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 98%, transparent)",
              borderColor: "color-mix(in oklab, var(--accent-strong) 18%, var(--panel-border))",
            }}
          >
            <CardHeader className="space-y-4 pb-4">
              <EphemeralChatHarness profile={selectedProfile} />
              <div
                className="rounded-2xl border px-4 py-4"
                data-testid="persona-studio-active-profile-summary"
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 91%, transparent)",
                  borderColor: "var(--panel-border)",
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 space-y-1.5">
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.18em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Active profile
                    </div>
                    <CardTitle className="text-lg leading-6">
                      {selectedProfile?.name || "Editor"}
                    </CardTitle>
                    <p className="max-w-2xl text-sm leading-6" style={{ color: "var(--muted)" }}>
                      {selectedProfile?.description ||
                        "Select a persona profile to edit its runtime identity and behavior."}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-1 uppercase tracking-[0.14em]"
                      style={{
                        borderColor: "var(--panel-border)",
                      }}
                    >
                      {selectedProfile?.isDefault ? "Default profile" : "Custom profile"}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-1 uppercase tracking-[0.14em]"
                      style={{
                        borderColor: "var(--accent)",
                        color: "var(--accent)",
                      }}
                    >
                      Active profile
                    </Badge>
                  </div>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  <div
                    className="rounded-xl border px-3 py-2"
                    style={{
                      borderColor: "var(--panel-border)",
                      background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                    }}
                  >
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Selection
                    </div>
                    <div className="mt-1 text-sm font-medium">
                      {selectedProfile?.isDefault
                        ? "Default runtime profile"
                        : "Custom runtime profile"}
                    </div>
                  </div>
                  <div
                    className="rounded-xl border px-3 py-2"
                    style={{
                      borderColor: "var(--panel-border)",
                      background: "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                    }}
                  >
                    <div
                      className="text-[11px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Status
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <Badge
                        variant="outline"
                        className="text-[10px] px-2 py-1"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        {selectedProfile?.isDefault ? "Default" : "Custom"}
                      </Badge>
                      <Badge
                        variant="outline"
                        className="text-[10px] px-2 py-1"
                        style={{
                          borderColor: "var(--accent)",
                          color: "var(--accent)",
                        }}
                      >
                        Active
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex min-h-0 flex-1 flex-col space-y-5 pt-0">
              <div
                className="rounded-2xl border p-5"
                style={{
                  background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
                  borderColor: "var(--panel-border)",
                }}
              >
                {renderActiveTab()}
              </div>
            </CardContent>
            <CardFooter className="flex flex-wrap items-center gap-3 pt-0">
              <Button type="button" onClick={handleSave} disabled={!isDirty}>
                Save
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={handleSaveAsNew}
                disabled={!currentConfig}
              >
                Save As New
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={handleReset}
                disabled={!isDirty}
              >
                Reset
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={resetAllLocalPersonaStudioData}
                className="whitespace-nowrap"
                aria-label="Reset All Local Persona Studio Data"
                title="Reset All Local Persona Studio Data"
              >
                Reset All Data
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}
