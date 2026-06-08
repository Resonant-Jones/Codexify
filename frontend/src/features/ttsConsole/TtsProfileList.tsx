import { Copy, Plus, Star, Trash2 } from "lucide-react";
import type { TtsVoiceProfile } from "./types";

type TtsProfileListProps = {
  profiles: TtsVoiceProfile[];
  selectedId: string | null;
  onSelect: (profileId: string) => void;
  onCreate: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onSetDefault: () => void;
  hasSelection: boolean;
};

export default function TtsProfileList({
  profiles,
  selectedId,
  onSelect,
  onCreate,
  onDuplicate,
  onDelete,
  onSetDefault,
  hasSelection,
}: TtsProfileListProps) {
  return (
    <section className="tts-console-pane" aria-label="TTS profiles">
      <div className="tts-console-button-row">
        <button
          type="button"
          className="tts-console-icon-button"
          aria-label="Create profile"
          title="Create profile"
          onClick={onCreate}
        >
          <Plus size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="tts-console-icon-button"
          aria-label="Duplicate profile"
          title="Duplicate profile"
          onClick={onDuplicate}
          disabled={!hasSelection}
        >
          <Copy size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="tts-console-icon-button"
          aria-label="Set default profile"
          title="Set default profile"
          onClick={onSetDefault}
          disabled={!hasSelection}
        >
          <Star size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="tts-console-icon-button"
          aria-label="Delete profile"
          title="Delete profile"
          onClick={onDelete}
          disabled={!hasSelection}
        >
          <Trash2 size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="tts-console-profile-stack" data-testid="tts-profile-list">
        {profiles.map((profile) => (
          <button
            key={profile.id}
            type="button"
            className="tts-console-profile-button"
            data-selected={profile.id === selectedId}
            onClick={() => onSelect(profile.id)}
          >
            <strong>{profile.name}</strong>
            <br />
            <span className="tts-console-muted">
              {profile.backend_id}
              {profile.is_default ? " · default" : ""}
            </span>
          </button>
        ))}
        {profiles.length === 0 && (
          <span className="tts-console-muted">No profiles</span>
        )}
      </div>
    </section>
  );
}
