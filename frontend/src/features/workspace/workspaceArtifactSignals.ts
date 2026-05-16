const AGENT_UPDATE_SOURCE_TAG_HINTS = [
  "assistant",
  "agent",
  "generated",
  "automation",
  "system",
  "codex",
];

type WorkspaceArtifactSignalCandidate = {
  source_tag?: string | null;
};

function normalizeSourceTag(tag: string | null | undefined): string {
  return String(tag ?? "")
    .trim()
    .toLowerCase();
}

export function isAgentUpdatedWorkspaceItem(
  item: WorkspaceArtifactSignalCandidate | null | undefined
): boolean {
  const normalizedTag = normalizeSourceTag(item?.source_tag);
  if (!normalizedTag) return false;
  return AGENT_UPDATE_SOURCE_TAG_HINTS.some((hint) =>
    normalizedTag.includes(hint)
  );
}
