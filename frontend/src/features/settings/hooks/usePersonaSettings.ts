import { useCallback, useEffect, useState } from "react";

import {
  fetchPersonaSettings,
  updatePersonaSettings,
  type ActivePersonaSettings,
  type PersonaSettingsContext,
} from "@/features/settings/api/persona";

const EMPTY_PERSONA_ERROR =
  "Persona text cannot be empty unless clearing is explicitly enabled for this context.";

function getErrorMessage(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const response = error.response as { data?: { detail?: unknown; error?: unknown } };
    if (typeof response.data?.detail === "string" && response.data.detail.trim()) {
      return response.data.detail;
    }
    if (typeof response.data?.error === "string" && response.data.error.trim()) {
      return response.data.error;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

export type UsePersonaSettingsResult = {
  draftText: string;
  error: string | null;
  hasLoaded: boolean;
  isDirty: boolean;
  isEmptySaveBlocked: boolean;
  loading: boolean;
  persona: ActivePersonaSettings | null;
  save: () => Promise<boolean>;
  saving: boolean;
  setDraftText: (next: string) => void;
  reset: () => void;
  reload: () => Promise<void>;
};

export function usePersonaSettings(
  context: PersonaSettingsContext = {}
): UsePersonaSettingsResult {
  const { projectId, threadId } = context;
  const [persona, setPersona] = useState<ActivePersonaSettings | null>(null);
  const [draftText, setDraftText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const applyPersona = useCallback((next: ActivePersonaSettings) => {
    setPersona(next);
    setDraftText(next.text);
  }, []);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const next = await fetchPersonaSettings({ projectId, threadId });
      applyPersona(next);
      setHasLoaded(true);
    } catch (nextError) {
      setError(getErrorMessage(nextError, "Failed to load persona settings."));
      setHasLoaded(true);
    } finally {
      setLoading(false);
    }
  }, [applyPersona, projectId, threadId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const reset = useCallback(() => {
    setDraftText(persona?.text ?? "");
    setError(null);
  }, [persona?.text]);

  const isEmptySaveBlocked =
    !(persona?.canClear ?? false) && draftText.trim().length === 0;

  const save = useCallback(async () => {
    if (isEmptySaveBlocked) {
      setError(EMPTY_PERSONA_ERROR);
      return false;
    }

    setSaving(true);
    setError(null);

    try {
      const next = await updatePersonaSettings({
        text: draftText,
        projectId,
        threadId,
      });
      applyPersona(next);
      return true;
    } catch (nextError) {
      setError(getErrorMessage(nextError, "Failed to save persona settings."));
      return false;
    } finally {
      setSaving(false);
    }
  }, [applyPersona, draftText, isEmptySaveBlocked, projectId, threadId]);

  return {
    draftText,
    error,
    hasLoaded,
    isDirty: draftText !== (persona?.text ?? ""),
    isEmptySaveBlocked,
    loading,
    persona,
    reset,
    reload,
    save,
    saving,
    setDraftText,
  };
}

export default usePersonaSettings;
