import { RotateCcw, Save, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createTtsProfile,
  deleteTtsProfile,
  fetchTtsBackends,
  fetchTtsProfiles,
  previewTtsProfile,
  setDefaultTtsProfile,
  updateTtsProfile,
} from "./ttsConsoleApi";
import TtsPreviewPanel from "./TtsPreviewPanel";
import TtsProfileEditor from "./TtsProfileEditor";
import TtsProfileList from "./TtsProfileList";
import type {
  TtsBackendInfo,
  TtsPreviewResponse,
  TtsVoiceProfile,
  TtsVoiceProfileDraft,
} from "./types";
import "./TtsConsole.css";

type TtsConsoleWindowProps = {
  open: boolean;
  onClose: () => void;
};

const DEFAULT_PREVIEW_TEXT = "This is a local Codexify voice preview.";

export default function TtsConsoleWindow({
  open,
  onClose,
}: TtsConsoleWindowProps) {
  const [profiles, setProfiles] = useState<TtsVoiceProfile[]>([]);
  const [backends, setBackends] = useState<TtsBackendInfo[]>([]);
  const [activeBackendId, setActiveBackendId] = useState("qwen3_tts");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<TtsVoiceProfileDraft | null>(null);
  const [savedDraft, setSavedDraft] = useState<TtsVoiceProfileDraft | null>(null);
  const [previewText, setPreviewText] = useState(DEFAULT_PREVIEW_TEXT);
  const [previewResult, setPreviewResult] = useState<TtsPreviewResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedId) ?? null,
    [profiles, selectedId]
  );
  const dirty = useMemo(
    () =>
      Boolean(
        draft &&
          savedDraft &&
          JSON.stringify(normalizeDraft(draft)) !==
            JSON.stringify(normalizeDraft(savedDraft))
      ),
    [draft, savedDraft]
  );

  const loadConsole = useCallback(async (preferredId?: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const [backendResponse, profileResponse] = await Promise.all([
        fetchTtsBackends(),
        fetchTtsProfiles(),
      ]);
      setBackends(backendResponse.items);
      setActiveBackendId(backendResponse.active_backend_id || "qwen3_tts");
      setProfiles(profileResponse.items);
      const nextSelected =
        preferredId && profileResponse.items.some((item) => item.id === preferredId)
          ? preferredId
          : profileResponse.default_profile_id ?? profileResponse.items[0]?.id ?? null;
      setSelectedId(nextSelected);
      setMessage("Loaded");
    } catch (loadError) {
      setError(readErrorMessage(loadError, "Unable to load TTS console"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      void loadConsole(null);
    }
  }, [loadConsole, open]);

  useEffect(() => {
    if (!selectedProfile) {
      setDraft(null);
      setSavedDraft(null);
      return;
    }
    const nextDraft = cloneProfile(selectedProfile);
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
    setPreviewResult(null);
    setError(null);
  }, [selectedProfile]);

  if (!open) return null;

  const replaceProfile = (profile: TtsVoiceProfile) => {
    setProfiles((current) =>
      current.map((item) => (item.id === profile.id ? profile : item))
    );
    setSelectedId(profile.id);
    const nextDraft = cloneProfile(profile);
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
  };

  const saveDraft = async (): Promise<TtsVoiceProfile | null> => {
    if (!draft) return null;
    setSaving(true);
    setError(null);
    try {
      const saved = await updateTtsProfile(draft.id, draft);
      replaceProfile(saved);
      setMessage("Saved");
      return saved;
    } catch (saveError) {
      setError(readErrorMessage(saveError, "Unable to save profile"));
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    setSaving(true);
    setError(null);
    try {
      const created = await createTtsProfile({
        name: "New voice profile",
        backend_id: activeBackendId,
        voice_mode: "preset",
        speaker: "default",
        speed: 1,
        output_format: "wav",
      });
      setProfiles((current) => [created, ...current]);
      setSelectedId(created.id);
      setMessage("Created");
    } catch (createError) {
      setError(readErrorMessage(createError, "Unable to create profile"));
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const copy: Partial<TtsVoiceProfileDraft> = { ...draft };
      delete copy.id;
      delete copy.is_default;
      const created = await createTtsProfile({
        ...copy,
        name: `${draft.name} Copy`,
        is_default: false,
      });
      setProfiles((current) => [created, ...current]);
      setSelectedId(created.id);
      setMessage("Duplicated");
    } catch (duplicateError) {
      setError(readErrorMessage(duplicateError, "Unable to duplicate profile"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    if (
      typeof window !== "undefined" &&
      !window.confirm("Delete TTS profile?")
    ) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await deleteTtsProfile(selectedId);
      const remaining = profiles.filter((profile) => profile.id !== selectedId);
      setProfiles(remaining);
      setSelectedId(remaining.find((profile) => profile.is_default)?.id ?? remaining[0]?.id ?? null);
      setMessage("Deleted");
    } catch (deleteError) {
      setError(readErrorMessage(deleteError, "Unable to delete profile"));
    } finally {
      setSaving(false);
    }
  };

  const handleSetDefault = async () => {
    if (!selectedId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await setDefaultTtsProfile(selectedId);
      setProfiles((current) =>
        current.map((profile) => ({
          ...profile,
          is_default: profile.id === updated.id,
        }))
      );
      replaceProfile(updated);
      setMessage("Default set");
    } catch (defaultError) {
      setError(readErrorMessage(defaultError, "Unable to set default"));
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    const profile = dirty ? await saveDraft() : selectedProfile;
    if (!profile) return;
    setPreviewing(true);
    setError(null);
    try {
      const result = await previewTtsProfile(profile.id, {
        text: previewText,
        format: profile.output_format ?? "wav",
      });
      setPreviewResult(result);
      setMessage("Preview ready");
    } catch (previewError) {
      setError(readErrorMessage(previewError, "Unable to render preview"));
    } finally {
      setPreviewing(false);
    }
  };

  const handleRevert = () => {
    if (!savedDraft) return;
    setDraft(cloneProfile(savedDraft));
    setError(null);
    setMessage("Reverted");
  };

  return (
    <div className="tts-console-overlay" role="presentation">
      <div
        className="tts-console-window"
        role="dialog"
        aria-modal="true"
        aria-label="TTS Console"
        data-testid="tts-console-window"
      >
        <header className="tts-console-header">
          <div>
            <h2 className="tts-console-title">TTS Console</h2>
            <span className="tts-console-muted">{activeBackendId}</span>
          </div>
          <button
            type="button"
            className="tts-console-icon-button"
            aria-label="Close TTS Console"
            onClick={onClose}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </header>

        <div className="tts-console-body">
          <TtsProfileList
            profiles={profiles}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onCreate={handleCreate}
            onDuplicate={handleDuplicate}
            onDelete={handleDelete}
            onSetDefault={handleSetDefault}
            hasSelection={Boolean(selectedId)}
          />
          <TtsProfileEditor
            draft={draft}
            backends={backends}
            onChange={(nextDraft) => {
              setDraft(nextDraft);
              setError(null);
              setMessage("Unsaved changes");
            }}
          />
          <TtsPreviewPanel
            text={previewText}
            onTextChange={setPreviewText}
            onPreview={handlePreview}
            previewing={previewing}
            previewResult={previewResult}
            message={loading ? "Loading" : message}
            error={error}
            disabled={!draft || saving || loading}
          />
        </div>

        <footer className="tts-console-footer">
          <span className="tts-console-status">
            {dirty ? "Unsaved changes" : "Saved state"}
          </span>
          <div className="tts-console-button-row">
            <button
              type="button"
              className="tts-console-action-button"
              onClick={handleRevert}
              disabled={!dirty || saving}
            >
              <RotateCcw size={15} aria-hidden="true" />
              Revert
            </button>
            <button
              type="button"
              className="tts-console-action-button"
              data-primary="true"
              onClick={() => void saveDraft()}
              disabled={!dirty || saving}
            >
              <Save size={15} aria-hidden="true" />
              {saving ? "Saving" : "Save"}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

function cloneProfile(profile: TtsVoiceProfile | TtsVoiceProfileDraft): TtsVoiceProfileDraft {
  return {
    ...profile,
    backend_params: { ...(profile.backend_params ?? {}) },
    pause_profile: profile.pause_profile ? { ...profile.pause_profile } : null,
  };
}

function normalizeDraft(profile: TtsVoiceProfileDraft): Record<string, unknown> {
  const { created_at: _createdAt, updated_at: _updatedAt, ...rest } = profile;
  return rest;
}

function readErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response
    ?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object") {
    const code = (detail as { code?: unknown }).code;
    if (typeof code === "string" && code.trim()) return code;
  }
  if (error instanceof Error && error.message.trim()) return error.message;
  return fallback;
}
