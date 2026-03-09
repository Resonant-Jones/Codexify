import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchSystemPromptInspectorSnapshot,
  type SystemPromptInspectorContext,
  type SystemPromptInspectorSnapshot,
  type SystemPromptSegment,
} from "@/features/settings/api/systemPrompt";

type LayerPresence = "present" | "absent" | "unavailable";

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

function resolvePresence(
  snapshot: SystemPromptInspectorSnapshot | null,
  segmentName: string
): LayerPresence {
  if (!snapshot) return "unavailable";
  if (segmentName in snapshot.segmentsPresent) {
    return snapshot.segmentsPresent[segmentName] ? "present" : "absent";
  }

  const segment = findSegment(snapshot, segmentName);
  if (!segment) return "unavailable";
  return segment.chars > 0 || segment.estimatedTokens > 0 ? "present" : "absent";
}

function pushMetadata(
  list: string[],
  label: string,
  value: string | number | null | undefined
) {
  if (value === null || value === undefined || value === "") return;
  list.push(`${label}: ${value}`);
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

  const personaMetadata: string[] = [];
  pushMetadata(personaMetadata, "Persona ID", snapshot?.persona?.id ?? null);
  pushMetadata(personaMetadata, "Source", snapshot?.persona?.source ?? null);
  pushMetadata(
    personaMetadata,
    "Captured",
    snapshot?.persona?.createdAt ?? null
  );
  pushMetadata(
    personaMetadata,
    "Tokens",
    personaSegment?.estimatedTokens ?? null
  );

  const imprintMetadata: string[] = [];
  pushMetadata(imprintMetadata, "Imprint ID", snapshot?.imprint?.id ?? null);
  pushMetadata(imprintMetadata, "Status", snapshot?.imprint?.status ?? null);
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
    "Captured",
    snapshot?.imprint?.createdAt ?? null
  );
  pushMetadata(
    imprintMetadata,
    "Tokens",
    imprintSegment?.estimatedTokens ?? null
  );

  const docsMetadata: string[] = [];
  pushMetadata(docsMetadata, "Docs", snapshot?.docsCount ?? null);
  pushMetadata(docsMetadata, "Tokens", docsSegment?.estimatedTokens ?? null);
  if (snapshot?.docsTruncated) {
    docsMetadata.push("Truncated to fit token budget");
  }

  return [
    {
      description:
        "Core system rules are active when this layer is present. Raw base prompt contents remain hidden here.",
      editableHere: false,
      key: "base",
      metadata: baseMetadata,
      presence: resolvePresence(snapshot, "base"),
      title: "Base system layer",
    },
    {
      description:
        "The current depth or mode selection is not exposed as a dedicated backend status field, so this inspector cannot verify it directly.",
      editableHere: false,
      key: "depthMode",
      metadata: [],
      presence: "unavailable",
      title: "Depth / mode layer",
    },
    {
      description:
        "Persona contributes user-facing voice and style when present. This inspector does not edit it.",
      editableHere: false,
      key: "persona",
      metadata: personaMetadata,
      presence:
        snapshot?.persona || resolvePresence(snapshot, "persona") === "present"
          ? "present"
          : resolvePresence(snapshot, "persona"),
      title: "Persona layer",
    },
    {
      description:
        "Imprint contributes a style layer when present. Review only; no accept/reject controls here.",
      editableHere: false,
      key: "imprint",
      metadata: imprintMetadata,
      presence:
        snapshot?.imprint || resolvePresence(snapshot, "imprint") === "present"
          ? "present"
          : resolvePresence(snapshot, "imprint"),
      title: "Imprint layer",
    },
    {
      description:
        "Attached system documents add supporting context when present. The inspector reports counts and budget hints only.",
      editableHere: false,
      key: "systemDocs",
      metadata: docsMetadata,
      presence:
        (snapshot?.docsCount ?? 0) > 0
          ? "present"
          : resolvePresence(snapshot, "system_docs"),
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
