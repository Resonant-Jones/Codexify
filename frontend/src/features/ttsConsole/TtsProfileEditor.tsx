import type { TtsBackendInfo, TtsVoiceProfileDraft } from "./types";

type TtsProfileEditorProps = {
  draft: TtsVoiceProfileDraft | null;
  backends: TtsBackendInfo[];
  onChange: (draft: TtsVoiceProfileDraft) => void;
};

const VOICE_MODES = [
  ["preset", "Preset"],
  ["prompt", "Prompt"],
  ["reference_audio", "Reference"],
  ["custom", "Custom"],
] as const;

export default function TtsProfileEditor({
  draft,
  backends,
  onChange,
}: TtsProfileEditorProps) {
  if (!draft) {
    return (
      <section className="tts-console-pane" aria-label="TTS profile editor">
        <span className="tts-console-muted">Select a profile</span>
      </section>
    );
  }

  const setField = <Key extends keyof TtsVoiceProfileDraft>(
    key: Key,
    value: TtsVoiceProfileDraft[Key]
  ) => {
    onChange({ ...draft, [key]: value });
  };
  const backendParams = draft.backend_params ?? {};
  const setBackendParam = (key: string, value: unknown) => {
    const next = { ...backendParams };
    if (value === "" || value === null || value === undefined) {
      delete next[key];
    } else {
      next[key] = value;
    }
    setField("backend_params", next);
  };

  return (
    <section
      className="tts-console-pane"
      aria-label="TTS profile editor"
      data-testid="tts-profile-editor"
    >
      <div className="tts-console-form">
        <label className="tts-console-field">
          <span className="tts-console-label">Name</span>
          <input
            className="tts-console-input"
            aria-label="Profile name"
            value={draft.name}
            onChange={(event) => setField("name", event.target.value)}
          />
        </label>

        <div className="tts-console-grid">
          <label className="tts-console-field">
            <span className="tts-console-label">Backend</span>
            <select
              className="tts-console-select"
              aria-label="Backend"
              value={draft.backend_id}
              onChange={(event) => setField("backend_id", event.target.value)}
            >
              {backends.map((backend) => (
                <option key={backend.backend_id} value={backend.backend_id}>
                  {backend.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="tts-console-field">
            <span className="tts-console-label">Voice Mode</span>
            <select
              className="tts-console-select"
              aria-label="Voice mode"
              value={draft.voice_mode}
              onChange={(event) => setField("voice_mode", event.target.value)}
            >
              {VOICE_MODES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="tts-console-grid">
          <label className="tts-console-field">
            <span className="tts-console-label">Speaker</span>
            <input
              className="tts-console-input"
              aria-label="Speaker"
              value={draft.speaker ?? ""}
              onChange={(event) => setField("speaker", event.target.value)}
            />
          </label>
          <label className="tts-console-field">
            <span className="tts-console-label">Language</span>
            <input
              className="tts-console-input"
              aria-label="Language"
              value={draft.language ?? ""}
              onChange={(event) => setField("language", event.target.value)}
            />
          </label>
        </div>

        <label className="tts-console-field">
          <span className="tts-console-label">Voice Prompt</span>
          <textarea
            className="tts-console-textarea"
            aria-label="Voice prompt"
            value={draft.voice_prompt ?? ""}
            onChange={(event) => setField("voice_prompt", event.target.value)}
          />
        </label>

        <label className="tts-console-field">
          <span className="tts-console-label">Style Instructions</span>
          <textarea
            className="tts-console-textarea"
            aria-label="Style instructions"
            value={draft.style_instructions ?? ""}
            onChange={(event) =>
              setField("style_instructions", event.target.value)
            }
          />
        </label>

        <label className="tts-console-field">
          <span className="tts-console-label">Speed</span>
          <input
            className="tts-console-input"
            aria-label="Speed"
            type="number"
            min={0.5}
            max={2}
            step={0.05}
            value={draft.speed ?? ""}
            onChange={(event) => setField("speed", readNumber(event.target.value))}
          />
          <span className="tts-console-muted">Codexify delivery control</span>
        </label>

        <details
          className="tts-console-details"
          data-testid="tts-console-advanced"
        >
          <summary>Advanced</summary>
          <div className="tts-console-grid">
            <NumberField
              label="Temperature"
              value={draft.temperature}
              min={0}
              max={2}
              step={0.05}
              onChange={(value) => setField("temperature", value)}
            />
            <NumberField
              label="Top K"
              value={draft.top_k}
              min={0}
              step={1}
              onChange={(value) => setField("top_k", readInteger(value))}
            />
            <NumberField
              label="Top P"
              value={draft.top_p}
              min={0}
              max={1}
              step={0.01}
              onChange={(value) => setField("top_p", value)}
            />
            <NumberField
              label="Repetition Penalty"
              value={draft.repetition_penalty}
              min={0.1}
              step={0.05}
              onChange={(value) => setField("repetition_penalty", value)}
            />
            <NumberField
              label="Max New Tokens"
              value={draft.max_new_tokens}
              min={1}
              step={1}
              onChange={(value) => setField("max_new_tokens", readInteger(value))}
            />
            <label className="tts-console-checkbox">
              <input
                type="checkbox"
                checked={draft.do_sample ?? false}
                onChange={(event) => setField("do_sample", event.target.checked)}
              />
              Do Sample
            </label>
            <label className="tts-console-checkbox">
              <input
                type="checkbox"
                checked={Boolean(backendParams.non_streaming_mode)}
                onChange={(event) =>
                  setBackendParam("non_streaming_mode", event.target.checked)
                }
              />
              Non-Streaming Mode
            </label>
            <label className="tts-console-checkbox">
              <input
                type="checkbox"
                checked={draft.x_vector_only_mode ?? false}
                onChange={(event) =>
                  setField("x_vector_only_mode", event.target.checked)
                }
              />
              X-Vector Only Mode
            </label>
            <NumberField
              label="Subtalker Temperature"
              value={readBackendNumber(backendParams.subtalker_temperature)}
              min={0}
              max={2}
              step={0.05}
              onChange={(value) => setBackendParam("subtalker_temperature", value)}
            />
            <NumberField
              label="Subtalker Top K"
              value={readBackendNumber(backendParams.subtalker_top_k)}
              min={0}
              step={1}
              onChange={(value) => setBackendParam("subtalker_top_k", readInteger(value))}
            />
            <NumberField
              label="Subtalker Top P"
              value={readBackendNumber(backendParams.subtalker_top_p)}
              min={0}
              max={1}
              step={0.01}
              onChange={(value) => setBackendParam("subtalker_top_p", value)}
            />
            <label className="tts-console-checkbox">
              <input
                type="checkbox"
                checked={Boolean(backendParams.subtalker_dosample)}
                onChange={(event) =>
                  setBackendParam("subtalker_dosample", event.target.checked)
                }
              />
              Subtalker Do Sample
            </label>
          </div>

          <label className="tts-console-field">
            <span className="tts-console-label">Reference Text</span>
            <textarea
              className="tts-console-textarea"
              aria-label="Reference text"
              value={draft.reference_text ?? ""}
              onChange={(event) => setField("reference_text", event.target.value)}
            />
          </label>
        </details>
      </div>
    </section>
  );
}

type NumberFieldProps = {
  label: string;
  value: number | null | undefined;
  min?: number;
  max?: number;
  step?: number;
  onChange: (value: number | null) => void;
};

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: NumberFieldProps) {
  return (
    <label className="tts-console-field">
      <span className="tts-console-label">{label}</span>
      <input
        className="tts-console-input"
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step={step}
        value={value ?? ""}
        onChange={(event) => onChange(readNumber(event.target.value))}
      />
    </label>
  );
}

function readNumber(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function readInteger(value: number | null): number | null {
  if (value == null) return null;
  return Math.trunc(value);
}

function readBackendNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return null;
  return readNumber(value);
}
