import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchSystemPromptInspectorSnapshot,
  type SystemPromptInspectorContext,
  type SystemPromptInspectorLayerState,
  type SystemPromptInspectorSnapshot,
  type SystemPromptSegment,
} from "@/features/settings/api/systemPrompt";

type LayerPresence = SystemPromptInspectorLayerState;

export type SystemPromptInspectorLayer = {
  description: string;
  editableHere: false;
  key: "base" | "depthMode" | "persona" | "imprint" | "systemDocs";
  metadata: string[];
  presence: LayerPresence;
  title: string;
};

export type UseSystemPromptInspectorResult = {
  error: string | null;
  hasLoaded: boolean;
  layers: SystemPromptInspectorLayer[];
  loading: boolean;
  reload: () => Promise<void>;
  snapshot: SystemPromptInspectorSnapshot | null;
};

function getErrorMessage(error: unknown): string {
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

  return "Failed to load system prompt inspector.";
}

function findSegment(
  snapshot: SystemPromptInspectorSnapshot | null,
  name: string
): SystemPromptSegment | null {
  return snapshot?.segments.find((segment) => segment.name === name) ?? null;
}

function resolveLayerPresence(
  snapshot: SystemPromptInspectorSnapshot | null,
  layer: "base" | "persona" | "imprint" | "systemDocs"
): LayerPresence {
  if (!snapshot) return "unavailable";

  switch (layer) {
    case "base":
      return snapshot.prompt.state;
    case "persona":
      return snapshot.persona.state;
    case "imprint":
      return snapshot.imprint.state;
    case "systemDocs":
      return snapshot.systemDocs.state;
  }
}

function pushMetadata(
  list: string[],
  label: string,
  value: string | number | null | undefined
) {
  if (value === null || value === undefined || value === "") return;
  list.push(`${label}: ${value}`);
}

function pushErrorCode(list: string[], errorCode: string | null) {
  pushMetadata(list, "Error code", errorCode);
}

function buildLayers(
  snapshot: SystemPromptInspectorSnapshot | null
): SystemPromptInspectorLayer[] {
  const baseSegment = findSegment(snapshot, "base");
  const personaSegment = findSegment(snapshot, "persona");
  const imprintSegment = findSegment(snapshot, "imprint");
  const docsSegment = findSegment(snapshot, "system_docs");

  const baseMetadata: string[] = [];
  pushMetadata(baseMetadata, "Tokens", baseSegment?.estimatedTokens ?? null);
  pushMetadata(baseMetadata, "Chars", baseSegment?.chars ?? null);
  pushErrorCode(baseMetadata, snapshot?.prompt.errorCode ?? null);

  const persona = snapshot?.persona;
  const personaMetadata: string[] = [];
  pushMetadata(personaMetadata, "Profile ID", snapshot?.persona.profileId ?? null);
  pushMetadata(personaMetadata, "Source", snapshot?.persona.source ?? null);
  if (
    persona &&
    (persona.state === "present" ||
      persona.profileId !== null ||
      persona.revision !== null)
  ) {
    pushMetadata(
      personaMetadata,
      "Revision",
      persona.revision === null ? "—" : persona.revision
    );
  }
  pushErrorCode(personaMetadata, snapshot?.persona.errorCode ?? null);
  pushMetadata(
    personaMetadata,
    "Tokens",
    personaSegment?.estimatedTokens ?? null
  );

  const imprintMetadata: string[] = [];
  pushMetadata(imprintMetadata, "Imprint ID", snapshot?.imprint?.id ?? null);
  pushMetadata(imprintMetadata, "Status", snapshot?.imprint?.status ?? null);
  pushMetadata(imprintMetadata, "Style", snapshot?.imprint?.style ?? null);
  pushMetadata(
    imprintMetadata,
    "Preferred name",
    snapshot?.imprint?.preferredName ?? null
  );
  pushMetadata(
    imprintMetadata,
    "Heat",
    snapshot?.imprint?.heatScore ?? null
  );
  pushMetadata(
    imprintMetadata,
    "Tokens",
    imprintSegment?.estimatedTokens ?? null
  );
  pushErrorCode(imprintMetadata, snapshot?.imprint.errorCode ?? null);

  const docsMetadata: string[] = [];
  pushMetadata(docsMetadata, "Docs", snapshot?.systemDocs.count ?? null);
  pushMetadata(docsMetadata, "Tokens", docsSegment?.estimatedTokens ?? null);
  if (snapshot?.systemDocs.truncated === true) {
    docsMetadata.push("Truncated to fit token budget");
  }
  pushErrorCode(docsMetadata, snapshot?.systemDocs.errorCode ?? null);

  return [
    {
      description:
        "Core system rules are part of the resolved prompt preview and remain immutable. Raw base prompt contents remain hidden here.",
      editableHere: false,
      key: "base",
      metadata: baseMetadata,
      presence: resolveLayerPresence(snapshot, "base"),
      title: "Base system layer",
    },
    {
      description:
        "Depth and mode are request-time settings. This inspector only sees persisted active identity records and resolved prompt metadata, so it cannot verify the exact value directly.",
      editableHere: false,
      key: "depthMode",
      metadata: [],
      presence: "unavailable",
      title: "Depth / mode layer",
    },
    {
      description:
        "Persona contributes user-facing voice and style when it is resolved into the prompt preview. This inspector shows the persisted record and resolved preview, not the raw request payload.",
      editableHere: false,
      key: "persona",
      metadata: personaMetadata,
      presence: resolveLayerPresence(snapshot, "persona"),
      title: "Persona layer",
    },
    {
      description:
        "Imprint contributes style and presentation when it is present in the resolved prompt preview. Review only; no accept/reject controls here.",
      editableHere: false,
      key: "imprint",
      metadata: imprintMetadata,
      presence: resolveLayerPresence(snapshot, "imprint"),
      title: "Imprint layer",
    },
    {
      description:
        "Attached system documents add supporting context when present in the resolved prompt preview. The inspector reports counts and budget hints only.",
      editableHere: false,
      key: "systemDocs",
      metadata: docsMetadata,
      presence: resolveLayerPresence(snapshot, "systemDocs"),
      title: "System docs layer",
    },
  ];
}

export function useSystemPromptInspector(
  context: SystemPromptInspectorContext = {}
): UseSystemPromptInspectorResult {
  const { projectId, threadId } = context;
  const [snapshot, setSnapshot] =
    useState<SystemPromptInspectorSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const next = await fetchSystemPromptInspectorSnapshot({
        projectId,
        threadId,
      });
      setSnapshot(next);
      setHasLoaded(true);
    } catch (nextError) {
      setError(getErrorMessage(nextError));
      setHasLoaded(true);
    } finally {
      setLoading(false);
    }
  }, [projectId, threadId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const layers = useMemo(() => buildLayers(snapshot), [snapshot]);

  return {
    error,
    hasLoaded,
    layers,
    loading,
    reload,
    snapshot,
  };
}

export default useSystemPromptInspector;
