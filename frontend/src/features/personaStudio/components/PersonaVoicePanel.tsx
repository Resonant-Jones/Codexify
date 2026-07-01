import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  fetchPersonaVoiceProviderVoices,
  fetchPersonaVoiceProviders,
  OptionalSurfaceError,
  previewPersonaVoice,
} from "@/lib/api";
import type {
  PersonaConfig,
  PersonaVoicePreviewResponse,
  PersonaVoiceProviderRecord,
  PersonaVoiceSelectableVoice,
} from "../types";
import {
  PERSONA_VOICE_PROVIDER_CLASSIFICATION,
  PERSONA_VOICE_PROVIDER_STATE,
} from "../types";

type PersonaVoicePanelProps = {
  config: PersonaConfig;
  onChange: (config: PersonaConfig) => void;
};

const DEFAULT_PREVIEW_TEXT =
  "This preview is ephemeral and does not save voice state.";

function classifyRouteAvailability(error: unknown): {
  summary: string;
  detail: string;
} {
  if (OptionalSurfaceError.isInstance(error)) {
    if (error.kind === "forbidden") {
      return {
        summary: "Voice discovery is unavailable in this posture.",
        detail:
          "This runtime reports that Persona Studio voice discovery is not enabled here.",
      };
    }
    return {
      summary: "Voice discovery is unavailable in this runtime.",
      detail:
        "Persona Studio could not find the backend voice discovery surface in this environment.",
    };
  }

  return {
    summary: "Voice discovery is temporarily unavailable.",
    detail: "The voice panel could not load provider data right now.",
  };
}

function badgeTone(provider: PersonaVoiceProviderRecord): React.CSSProperties {
  if (provider.state === PERSONA_VOICE_PROVIDER_STATE.AVAILABLE) {
    return {
      borderColor: "var(--accent)",
      color: "var(--accent)",
    };
  }
  if (provider.state === PERSONA_VOICE_PROVIDER_STATE.DEGRADED) {
    return {
      borderColor: "var(--panel-border)",
      color: "var(--text)",
    };
  }
  return {
    borderColor: "var(--panel-border)",
    color: "var(--muted)",
  };
}

export default function PersonaVoicePanel({
  config,
  onChange,
}: PersonaVoicePanelProps) {
  const [providers, setProviders] = React.useState<PersonaVoiceProviderRecord[]>(
    []
  );
  const [providersLoading, setProvidersLoading] = React.useState(true);
  const [providersError, setProvidersError] = React.useState<{
    summary: string;
    detail: string;
  } | null>(null);
  const [voices, setVoices] = React.useState<PersonaVoiceSelectableVoice[]>([]);
  const [voicesLoading, setVoicesLoading] = React.useState(false);
  const [voicesDetail, setVoicesDetail] = React.useState<string>("");
  const [previewText, setPreviewText] = React.useState(DEFAULT_PREVIEW_TEXT);
  const [previewLoading, setPreviewLoading] = React.useState(false);
  const [previewResponse, setPreviewResponse] =
    React.useState<PersonaVoicePreviewResponse | null>(null);
  const [previewDetail, setPreviewDetail] = React.useState<string>("");

  const selectedProviderId = (config.voice.provider || "").trim();
  const selectedVoiceId = (config.voice.voicePreset || "").trim();

  const currentProvider = React.useMemo(() => {
    if (!providers.length) return null;
    const exact = providers.find(
      (provider) => provider.providerId === selectedProviderId
    );
    return exact ?? null;
  }, [providers, selectedProviderId]);

  const providerOptions = React.useMemo(() => {
    if (!selectedProviderId) return providers;
    if (providers.some((provider) => provider.providerId === selectedProviderId)) {
      return providers;
    }

    return [
      {
        providerId: selectedProviderId,
        label: selectedProviderId,
        classification: PERSONA_VOICE_PROVIDER_CLASSIFICATION.CLOUD,
        state: PERSONA_VOICE_PROVIDER_STATE.UNAVAILABLE,
        statusDetail:
          "This draft references a provider that is not available in the current discovery surface.",
        capabilities: {
          presetVoices: false,
          cloning: false,
          promptDefinedVoice: false,
          preview: false,
        },
      },
      ...providers,
    ];
  }, [providers, selectedProviderId]);

  React.useEffect(() => {
    let cancelled = false;

    async function loadProviders() {
      setProvidersLoading(true);
      setProvidersError(null);
      try {
        const nextProviders = await fetchPersonaVoiceProviders();
        if (cancelled) return;
        setProviders(nextProviders);
      } catch (error) {
        if (cancelled) return;
        setProviders([]);
        setProvidersError(classifyRouteAvailability(error));
      } finally {
        if (!cancelled) {
          setProvidersLoading(false);
        }
      }
    }

    void loadProviders();
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    let cancelled = false;

    async function loadVoices() {
      if (!selectedProviderId) {
        setVoices([]);
        setVoicesDetail("Choose a provider to load selectable preset voices.");
        return;
      }

      setVoicesLoading(true);
      setVoicesDetail("Loading selectable preset voices.");
      try {
        const response = await fetchPersonaVoiceProviderVoices(selectedProviderId);
        if (cancelled) return;
        setVoices(response.voices ?? []);
        setVoicesDetail(response.statusDetail);

        if (
          response.voices.length > 0 &&
          !response.voices.some((voice) => voice.voiceId === selectedVoiceId)
        ) {
          const nextVoice = response.voices[0]?.voiceId ?? "";
          if (nextVoice) {
            onChange({
              ...config,
              voice: {
                ...config.voice,
                voicePreset: nextVoice,
              },
            });
          }
        }
      } catch (error) {
        if (cancelled) return;
        setVoices([]);
        const routeState = classifyRouteAvailability(error);
        setVoicesDetail(routeState.detail);
      } finally {
        if (!cancelled) {
          setVoicesLoading(false);
        }
      }
    }

    setPreviewResponse(null);
    setPreviewDetail("");
    void loadVoices();
    return () => {
      cancelled = true;
    };
  }, [config, onChange, selectedProviderId, selectedVoiceId]);

  const handleProviderChange = (providerId: string) => {
    onChange({
      ...config,
      voice: {
        ...config.voice,
        provider: providerId,
      },
    });
  };

  const handleVoiceChange = (voiceId: string) => {
    onChange({
      ...config,
      voice: {
        ...config.voice,
        voicePreset: voiceId,
      },
    });
  };

  const handleVoiceEnabledChange = (enabled: boolean) => {
    onChange({
      ...config,
      voice: {
        ...config.voice,
        enabled,
      },
    });
  };

  const handleSpeedChange = (speed: number) => {
    onChange({
      ...config,
      voice: {
        ...config.voice,
        speed,
      },
    });
  };

  const handleInterruptibleChange = (interruptible: boolean) => {
    onChange({
      ...config,
      voice: {
        ...config.voice,
        interruptible,
      },
    });
  };

  const runPreview = async () => {
    if (!selectedProviderId || !selectedVoiceId) return;
    setPreviewLoading(true);
    setPreviewDetail("");

    try {
      const response = await previewPersonaVoice({
        provider: selectedProviderId,
        voice_id: selectedVoiceId,
        sample_text: previewText,
        speed: config.voice.speed,
      });
      setPreviewResponse(response);
      setPreviewDetail(response.statusDetail);
    } catch (error) {
      const routeState = classifyRouteAvailability(error);
      setPreviewResponse(null);
      setPreviewDetail(routeState.detail);
    } finally {
      setPreviewLoading(false);
    }
  };

  const previewSupported =
    currentProvider?.capabilities.preview === true &&
    currentProvider.state === PERSONA_VOICE_PROVIDER_STATE.AVAILABLE &&
    Boolean(selectedVoiceId);

  return (
    <div
      className="flex min-h-0 flex-col gap-[var(--shell-gap)]"
      data-testid="persona-voice-panel"
    >
      <section
        className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
        data-testid="persona-voice-panel-provider"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
        }}
      >
        <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Provider
            </h3>
            <p className="text-sm leading-6 text-[var(--text)]">
              Select a provider without turning Persona Studio into a provider console.
            </p>
          </div>
          {currentProvider ? (
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                style={{
                  borderColor: "var(--panel-border)",
                }}
              >
                {currentProvider.classification}
              </Badge>
              <Badge
                variant="outline"
                className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                style={badgeTone(currentProvider)}
              >
                {currentProvider.state}
              </Badge>
            </div>
          ) : null}
        </div>

        <div className="mt-[var(--shell-gap)] grid gap-[var(--shell-gap)] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-2">
            <label
              className="text-sm font-medium text-[var(--text)]"
              htmlFor="persona-voice-provider-select"
            >
              Voice Provider
            </label>
            <select
              id="persona-voice-provider-select"
              className="h-10 w-full rounded-[var(--tile-radius)] border bg-[var(--chip-bg)] px-[var(--card-pad)] text-sm"
              style={{
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
              value={selectedProviderId}
              onChange={(event) => handleProviderChange(event.target.value)}
              disabled={providersLoading || providerOptions.length === 0}
            >
              {providerOptions.length === 0 ? (
                <option value="">No provider discovery available</option>
              ) : null}
              {providerOptions.map((provider) => (
                <option key={provider.providerId} value={provider.providerId}>
                  {provider.label}
                </option>
              ))}
            </select>
          </div>
          <div
            className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
            }}
          >
            <p className="text-sm font-medium text-[var(--text)]">
              Availability and capability summary
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              {providersError?.summary ??
                currentProvider?.statusDetail ??
                "Voice discovery will surface provider truth when available."}
            </p>
            {providersError?.detail ? (
              <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                {providersError.detail}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {currentProvider ? (
                <>
                  <Badge
                    variant="outline"
                    className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                    style={{ borderColor: "var(--panel-border)" }}
                  >
                    preset voices {currentProvider.capabilities.presetVoices ? "yes" : "no"}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                    style={{ borderColor: "var(--panel-border)" }}
                  >
                    preview {currentProvider.capabilities.preview ? "yes" : "no"}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                    style={{ borderColor: "var(--panel-border)" }}
                  >
                    cloning {currentProvider.capabilities.cloning ? "provider view" : "outside v1"}
                  </Badge>
                </>
              ) : (
                <Badge
                  variant="outline"
                  className="px-2 py-1 text-[10px] uppercase tracking-[0.14em]"
                  style={{ borderColor: "var(--panel-border)" }}
                >
                  discovery pending
                </Badge>
              )}
            </div>
          </div>
        </div>
      </section>

      <section
        className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
        data-testid="persona-voice-panel-preset"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
        }}
      >
        <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Voice Preset
            </h3>
            <p className="text-sm leading-6 text-[var(--text)]">
              Bind a selectable preset voice. Advanced creation stays outside Persona Studio V1.
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled
          >
            Manage in Provider View
          </Button>
        </div>

        <div className="mt-[var(--shell-gap)] grid gap-[var(--shell-gap)] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-2">
            <label
              className="text-sm font-medium text-[var(--text)]"
              htmlFor="persona-voice-preset-select"
            >
              Selectable Preset Voice
            </label>
            <select
              id="persona-voice-preset-select"
              className="h-10 w-full rounded-[var(--tile-radius)] border bg-[var(--chip-bg)] px-[var(--card-pad)] text-sm"
              style={{
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
              value={selectedVoiceId}
              onChange={(event) => handleVoiceChange(event.target.value)}
              disabled={voicesLoading || voices.length === 0}
            >
              {voices.length === 0 ? (
                <option value="">
                  {voicesLoading
                    ? "Loading preset voices"
                    : "No selectable preset voices available"}
                </option>
              ) : null}
              {voices.map((voice) => (
                <option key={voice.voiceId} value={voice.voiceId}>
                  {voice.label}
                </option>
              ))}
            </select>
            <p className="text-sm leading-6 text-[var(--muted)]">
              {voicesDetail || "Preset voice inventory appears here when discovery is available."}
            </p>
          </div>

          <div
            className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
            }}
          >
            <p className="text-sm font-medium text-[var(--text)]">
              Selected voice summary
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text)]">
              {selectedVoiceId || "No preset voice bound yet."}
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              {voices.find((voice) => voice.voiceId === selectedVoiceId)?.summary ??
                "Preset-first binding keeps Persona Studio fast and provider-reactive."}
            </p>
          </div>
        </div>
      </section>

      <section
        className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
        data-testid="persona-voice-panel-runtime-style"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
        }}
      >
        <div className="space-y-1">
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Runtime Style
          </h3>
          <p className="text-sm leading-6 text-[var(--text)]">
            Only generic runtime controls belong here.
          </p>
        </div>

        <div className="mt-[var(--shell-gap)] grid gap-[var(--shell-gap)] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--text)]">
              Speed
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={config.voice.speed}
                onChange={(event) =>
                  handleSpeedChange(parseFloat(event.target.value))
                }
                className="flex-1"
              />
              <span className="w-12 text-right text-sm text-[var(--muted)]">
                {config.voice.speed.toFixed(1)}x
              </span>
            </div>
          </div>

          <div
            className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
            }}
          >
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={config.voice.interruptible}
                onChange={(event) =>
                  handleInterruptibleChange(event.target.checked)
                }
                className="rounded"
              />
              <span className="text-sm font-medium text-[var(--text)]">
                Interruptible playback
              </span>
            </label>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Advanced provider creation controls stay out of this panel.
            </p>
          </div>
        </div>
      </section>

      <section
        className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
        data-testid="persona-voice-panel-preview"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
        }}
      >
        <div className="space-y-1">
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Preview
          </h3>
          <p className="text-sm leading-6 text-[var(--text)]">
            Preview is ephemeral only. No chat history, no persona save, no provider asset creation.
          </p>
        </div>

        <div className="mt-[var(--shell-gap)] space-y-[var(--shell-gap)]">
          <div className="space-y-2">
            <label
              className="text-sm font-medium text-[var(--text)]"
              htmlFor="persona-voice-preview-text"
            >
              Sample text
            </label>
            <Textarea
              id="persona-voice-preview-text"
              value={previewText}
              onChange={(event) => setPreviewText(event.target.value)}
              rows={4}
              className="min-h-[120px] resize-y"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              onClick={() => void runPreview()}
              disabled={!previewSupported || previewLoading}
            >
              {previewLoading ? "Preparing Preview" : "Preview Voice"}
            </Button>
            <p className="text-sm leading-6 text-[var(--muted)]">
              {previewDetail ||
                (previewSupported
                  ? "Run a bounded preview without mutating persona or chat state."
                  : "Preview becomes available when the selected provider and preset support it.")}
            </p>
          </div>

          {previewResponse?.preview?.playbackUrl ? (
            <div
              className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
              data-testid="persona-voice-preview-audio"
              style={{
                borderColor: "var(--panel-border)",
                background: "var(--chip-bg)",
              }}
            >
              <audio
                controls
                src={previewResponse.preview.playbackUrl}
                className="w-full"
              />
            </div>
          ) : null}
        </div>
      </section>

      <section
        className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
        data-testid="persona-voice-panel-binding"
        style={{
          borderColor: "var(--panel-border)",
          background: "color-mix(in srgb, var(--panel-bg) 95%, transparent)",
        }}
      >
        <div className="space-y-1">
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Binding
          </h3>
          <p className="text-sm leading-6 text-[var(--text)]">
            Keep the draft’s bound voice explicit and reviewable.
          </p>
        </div>

        <div className="mt-[var(--shell-gap)] grid gap-[var(--shell-gap)] lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
          <div
            className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
            }}
          >
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={config.voice.enabled}
                onChange={(event) =>
                  handleVoiceEnabledChange(event.target.checked)
                }
                className="rounded"
              />
              <span className="text-sm font-medium text-[var(--text)]">
                Voice output enabled
              </span>
            </label>
          </div>

          <div
            className="rounded-[var(--tile-radius)] border p-[var(--card-pad)]"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
            }}
          >
            <p className="text-sm font-medium text-[var(--text)]">
              Current draft binding
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text)]">
              {selectedProviderId || "No provider selected"} · {selectedVoiceId || "No preset selected"}
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              {config.voice.enabled
                ? "This draft will use the selected provider and preset when voice output is enabled downstream."
                : "This draft keeps a voice binding ready, but runtime voice output is currently off."}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
