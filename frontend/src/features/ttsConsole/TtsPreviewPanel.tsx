import { Play } from "lucide-react";
import type { TtsPreviewResponse } from "./types";

type TtsPreviewPanelProps = {
  text: string;
  onTextChange: (value: string) => void;
  onPreview: () => void;
  previewing: boolean;
  previewResult: TtsPreviewResponse | null;
  message: string | null;
  error: string | null;
  disabled: boolean;
};

export default function TtsPreviewPanel({
  text,
  onTextChange,
  onPreview,
  previewing,
  previewResult,
  message,
  error,
  disabled,
}: TtsPreviewPanelProps) {
  return (
    <section className="tts-console-pane" aria-label="TTS preview">
      <div className="tts-console-form">
        <label className="tts-console-field">
          <span className="tts-console-label">Preview Text</span>
          <textarea
            className="tts-console-textarea"
            aria-label="Preview text"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="tts-console-action-button"
          data-primary="true"
          onClick={onPreview}
          disabled={disabled || previewing || text.trim().length === 0}
        >
          <Play size={15} aria-hidden="true" />
          {previewing ? "Rendering" : "Preview"}
        </button>
        {previewResult?.artifact.media_url && (
          <audio
            className="tts-console-preview-audio"
            controls
            src={previewResult.artifact.media_url}
          />
        )}
        {previewResult?.artifact.output_path && (
          <span className="tts-console-muted" data-testid="tts-preview-output">
            {previewResult.artifact.output_path}
          </span>
        )}
        <span
          className="tts-console-status"
          data-tone={error ? "error" : "neutral"}
          role={error ? "alert" : undefined}
        >
          {error ?? message ?? ""}
        </span>
      </div>
    </section>
  );
}
