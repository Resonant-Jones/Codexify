import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { PersonaProfileDraft } from "./personaStudioStore";

/**
 * PersonaPreviewPanel
 *
 * Sandboxed, non-runtime preview surface for the active persona draft.
 *
 * Boundary contract:
 * - Draft only: reflects the unsaved draft state, never the saved runtime profile.
 * - No memory writes: nothing is persisted to profile storage or memory layer.
 * - No thread persistence: no chat thread is created, mutated, or persisted.
 *
 * This component is intentionally a presentation shell. It does not call
 * /api/chat/*, does not invoke provider routing, and does not write to
 * memory or identity. The composer is local-only; turns clear on remount.
 */

const PREVIEW_SCENARIO_CHIPS = [
  "Coding",
  "Research",
  "Planning",
  "Casual Help",
] as const;

const BOUNDARY_CHIPS = [
  "Draft only",
  "No memory writes",
  "No thread persistence",
] as const;

type PreviewDraftSnapshot = {
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

type PreviewTurn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  draftSignature: string;
  draftSnapshot: PreviewDraftSnapshot;
};

function formatList(values: string[]) {
  return values.length > 0 ? values.join(", ") : "None";
}

function buildPreviewDraftSnapshot(
  profile: PersonaProfileDraft | null
): PreviewDraftSnapshot {
  const config = profile?.config ?? null;
  const personaName = config?.identity?.name || profile?.name || "Persona";
  const description =
    config?.identity?.description || profile?.description || "No description set.";
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

function getPreviewPromptTone(prompt: string) {
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

function buildPreviewReply(
  prompt: string,
  draftSnapshot: PreviewDraftSnapshot,
  turnNumber: number
) {
  const trimmedPrompt = prompt.trim().replace(/\s+/g, " ");
  const promptLine = trimmedPrompt ? `You said: "${trimmedPrompt}".` : "You sent an empty prompt.";
  const turnLine =
    turnNumber === 1
      ? "This is the first preview turn in this Studio session."
      : `This is preview turn ${turnNumber} in the current Studio session.`;

  return [
    `${draftSnapshot.personaName} is the active persona draft right now.`,
    promptLine,
    getPreviewPromptTone(trimmedPrompt),
    `Current draft snapshot: ${draftSnapshot.modelLine}; temperature ${draftSnapshot.temperatureLine}; retrieval ${draftSnapshot.retrieval}; voice ${draftSnapshot.voice}.`,
    turnLine,
    "This preview stays local to Persona Studio, never persists, and clears on reload.",
  ].join(" ");
}

function BoundaryChip({ label }: { label: string }) {
  return (
    <Badge
      variant="outline"
      className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
      data-testid={`persona-preview-panel-boundary-${label
        .toLowerCase()
        .replace(/\s+/g, "-")}`}
      style={{ borderColor: "var(--panel-border)" }}
    >
      {label}
    </Badge>
  );
}

export interface PersonaPreviewPanelProps {
  profile: PersonaProfileDraft | null;
}

export default function PersonaPreviewPanel({ profile }: PersonaPreviewPanelProps) {
  const [previewTurns, setPreviewTurns] = React.useState<PreviewTurn[]>([]);
  const [previewPrompt, setPreviewPrompt] = React.useState("");
  const [isResponding, setIsResponding] = React.useState(false);
  const messageIdRef = React.useRef(0);
  const sessionVersionRef = React.useRef(0);
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  const currentDraftSnapshot = React.useMemo(
    () => buildPreviewDraftSnapshot(profile),
    [profile]
  );

  const lastAssistantDraftSignature = React.useMemo(() => {
    for (let index = previewTurns.length - 1; index >= 0; index -= 1) {
      const entry = previewTurns[index];
      if (entry.role === "assistant") {
        return entry.draftSignature;
      }
    }
    return null;
  }, [previewTurns]);

  const draftChangedSinceLastReply =
    Boolean(lastAssistantDraftSignature) &&
    lastAssistantDraftSignature !== currentDraftSnapshot.signature;

  const clearPreviewSession = React.useCallback(() => {
    sessionVersionRef.current += 1;
    messageIdRef.current = 0;
    setPreviewTurns([]);
    setPreviewPrompt("");
    setIsResponding(false);
    inputRef.current?.focus();
  }, []);

  const sendPreviewPrompt = React.useCallback(
    async (message: string) => {
      const trimmedMessage = message.trim();
      if (!trimmedMessage || isResponding) {
        return;
      }

      const sessionVersionAtSend = sessionVersionRef.current;
      const draftSnapshotAtSend = buildPreviewDraftSnapshot(profile);
      const nextTurnNumber =
        previewTurns.filter((entry) => entry.role === "assistant").length + 1;
      const userMessage: PreviewTurn = {
        id: `preview-turn-${messageIdRef.current + 1}`,
        role: "user",
        content: trimmedMessage,
        draftSignature: draftSnapshotAtSend.signature,
        draftSnapshot: draftSnapshotAtSend,
      };

      messageIdRef.current += 1;
      setIsResponding(true);
      setPreviewTurns((previous) => [...previous, userMessage]);
      setPreviewPrompt("");

      await Promise.resolve();

      if (sessionVersionRef.current !== sessionVersionAtSend) {
        return;
      }

      const assistantMessage: PreviewTurn = {
        id: `preview-turn-${messageIdRef.current + 1}`,
        role: "assistant",
        content: buildPreviewReply(trimmedMessage, draftSnapshotAtSend, nextTurnNumber),
        draftSignature: draftSnapshotAtSend.signature,
        draftSnapshot: draftSnapshotAtSend,
      };

      messageIdRef.current += 1;
      setPreviewTurns((previous) => [...previous, assistantMessage]);
      setIsResponding(false);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    },
    [previewTurns, isResponding, profile]
  );

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendPreviewPrompt(previewPrompt);
  };

  const hasTurns = previewTurns.length > 0;

  return (
    <Card
      className="bezel-none flex min-h-0 flex-1 flex-col overflow-y-auto rounded-2xl border lg:h-full"
      role="region"
      aria-label="Persona Preview panel"
      data-testid="persona-preview-panel"
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 94%, transparent)",
        borderColor: "var(--panel-border)",
        boxShadow: "0 10px 30px color-mix(in srgb, var(--bg) 62%, transparent)",
      }}
    >
      <CardHeader className="space-y-4 pb-4" data-testid="persona-preview-panel-header">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base font-semibold">
                Persona Preview
              </CardTitle>
              {BOUNDARY_CHIPS.map((label) => (
                <BoundaryChip key={label} label={label} />
              ))}
            </div>
            <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
              Sandboxed response tuning for the current draft. Preview-only, isolated
              from Guardian runtime, and clears on reload.
            </p>
          </div>
          <Badge
            variant="outline"
            className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
            style={{ borderColor: "var(--panel-border)" }}
          >
            Preview
          </Badge>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {PREVIEW_SCENARIO_CHIPS.map((prompt) => (
            <Button
              key={prompt}
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void sendPreviewPrompt(prompt)}
              disabled={isResponding}
            >
              {prompt}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 pt-0">
        <div className="flex min-h-0 w-full flex-1 flex-col gap-4">
          <section
            className="flex min-h-0 flex-1 flex-col rounded-[var(--card-radius)] border px-4 py-4"
            data-testid="persona-preview-panel-transcript"
            aria-live="polite"
            aria-busy={isResponding}
            style={{
              background: "color-mix(in srgb, var(--panel-bg) 97%, transparent)",
              borderColor: "var(--panel-border)",
            }}
          >
            <div
              className="flex flex-wrap items-center justify-between gap-2 border-b pb-3"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <div className="space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em]">
                  Preview transcript
                </div>
                <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                  Preview turns stay in this mounted Studio session only.
                </p>
              </div>
              <Badge
                variant="outline"
                className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                style={{ borderColor: "var(--panel-border)" }}
              >
                Session cache
              </Badge>
            </div>
            <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pt-3 pr-1">
              {hasTurns ? (
                <div className="space-y-3">
                  {isResponding ? (
                    <div
                      className="rounded-[var(--tile-radius)] border px-4 py-4 text-sm"
                      style={{
                        background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
                        borderColor: "var(--panel-border)",
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge
                            variant="outline"
                            className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                            style={{ borderColor: "var(--panel-border)" }}
                          >
                            Draft-aware turn
                          </Badge>
                          <span
                            className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                            style={{ color: "var(--muted)" }}
                          >
                            Generating
                          </span>
                        </div>
                      </div>
                      <p className="mt-2 leading-6">Generating a draft-aware preview…</p>
                    </div>
                  ) : null}
                  {previewTurns.map((entry, index) => {
                    const isAssistant = entry.role === "assistant";
                    const turnNumber = index + 1;

                    return (
                      <div
                        key={entry.id}
                        data-testid="persona-preview-panel-turn-row"
                        data-message-role={entry.role}
                        data-message-layout={isAssistant ? "preview-block" : "user-bubble"}
                        className="border-b pb-4 text-sm last:border-b-0 last:pb-0"
                        style={{
                          borderColor: "var(--panel-border)",
                        }}
                      >
                        {isAssistant ? (
                          <div className="space-y-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge
                                  variant="outline"
                                  className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                                  style={{ borderColor: "var(--panel-border)" }}
                                >
                                  Turn {turnNumber}
                                </Badge>
                                <div
                                  className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                  style={{ color: "var(--muted)" }}
                                >
                                  Preview block
                                </div>
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
                            <div
                              className="rounded-[var(--tile-radius)] border px-4 py-4"
                              style={{
                                borderColor: "var(--panel-border)",
                                background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
                              }}
                            >
                              <p className="leading-6">{entry.content}</p>
                              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Persona
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.personaName}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Model
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.modelLine}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Temperature
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.temperatureLine}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Voice
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.voice}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3 sm:col-span-2"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Prompt
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.systemPrompt}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3 sm:col-span-2"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Style Notes
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.styleNotes}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3 sm:col-span-2"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Directives
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.directives}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Retrieval
                                  </div>
                                  <p className="mt-1 leading-6">{entry.draftSnapshot.retrieval}</p>
                                </div>
                                <div
                                  className="rounded-[var(--tile-radius)] border px-3 py-3"
                                  style={{
                                    borderColor: "var(--panel-border)",
                                    background:
                                      "color-mix(in srgb, var(--panel-bg) 96%, transparent)",
                                  }}
                                >
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    Tools
                                  </div>
                                  <p className="mt-1 leading-6">
                                    Pinned: {entry.draftSnapshot.pinnedTools} | Allowed:{" "}
                                    {entry.draftSnapshot.allowedTools}
                                  </p>
                                </div>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="flex justify-end">
                            <div
                              className="max-w-[92%] rounded-[var(--tile-radius)] border px-4 py-3"
                              style={{
                                background:
                                  "color-mix(in srgb, var(--accent) 9%, var(--panel-bg))",
                                borderColor:
                                  "color-mix(in oklab, var(--accent) 18%, var(--panel-border))",
                              }}
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge
                                    variant="outline"
                                    className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                                    style={{ borderColor: "var(--panel-border)" }}
                                  >
                                    Turn {turnNumber}
                                  </Badge>
                                  <div
                                    className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ color: "var(--muted)" }}
                                  >
                                    User bubble
                                  </div>
                                </div>
                                <span
                                  className="text-[10px] font-semibold uppercase tracking-[0.14em]"
                                  style={{ color: "var(--muted)" }}
                                >
                                  Captured at send time
                                </span>
                              </div>
                              <p className="mt-2 leading-6">{entry.content}</p>
                              <p
                                className="mt-2 text-xs leading-5"
                                style={{ color: "var(--muted)" }}
                              >
                                Captured against the draft that was active when this input was
                                sent.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div
                  className="space-y-3 rounded-[var(--tile-radius)] border px-4 py-4"
                  style={{
                    borderColor: "var(--panel-border)",
                    background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
                  }}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant="outline"
                      className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                      style={{ borderColor: "var(--panel-border)" }}
                    >
                      Empty preview
                    </Badge>
                    <span
                      className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: "var(--muted)" }}
                    >
                      Draft-only tuning
                    </span>
                  </div>
                  <p className="text-sm" style={{ color: "var(--muted)" }}>
                    No preview turns yet. Use this draft-only surface to test the active
                    persona draft before anything becomes runtime chat or durable state.
                  </p>
                  <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                    Send a temporary prompt, inspect the draft snapshot, and keep
                    iterating in this mounted Studio session only.
                  </p>
                </div>
              )}
            </div>
          </section>
          <section
            className="mt-auto space-y-3 border-t pt-4"
            data-testid="persona-preview-panel-composer"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <div
                  className="text-[10px] font-semibold uppercase tracking-[0.16em]"
                  style={{ color: "var(--muted)" }}
                >
                  Preview composer
                </div>
                <p className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                  Local-only draft input for bounded tests and structured-output checks.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={clearPreviewSession}
                disabled={!hasTurns && !previewPrompt.trim()}
                className="shrink-0"
                style={{ borderColor: "var(--panel-border)" }}
              >
                Clear preview session
              </Button>
            </div>
            {draftChangedSinceLastReply ? (
              <p className="text-xs font-medium leading-5" style={{ color: "var(--accent)" }}>
                Draft changed since the last reply. New turns use the current draft;
                earlier replies remain as historical preview turns.
              </p>
            ) : null}
            <form className="flex flex-wrap gap-2" onSubmit={handleSubmit}>
              <Input
                ref={inputRef}
                value={previewPrompt}
                onChange={(event) => setPreviewPrompt(event.target.value)}
                placeholder="Draft-only, no memory writes, no thread persistence"
                aria-label="Persona preview prompt"
                className="min-w-0 flex-1"
                disabled={isResponding}
              />
              <Button type="submit" disabled={!previewPrompt.trim() || isResponding}>
                Send
              </Button>
            </form>
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
