import type { Thread } from "@/types/ui";

export type SidebarProvenanceOption = {
  value: string;
  label: string;
};

const CANONICAL_PROVENANCE_LABELS = new Map<string, string>([
  ["anthropic", "Anthropic"],
  ["chat gpt", "ChatGPT"],
  ["chatgpt", "ChatGPT"],
  ["chatgpt import", "ChatGPT"],
  ["chatgpt v1", "ChatGPT"],
  ["chatgpt v1 canonical", "ChatGPT"],
  ["claude", "Claude"],
  ["gemini", "Gemini"],
  ["google gemini", "Gemini"],
  ["open ai", "OpenAI"],
  ["openai", "OpenAI"],
  ["openai v1", "OpenAI"],
]);

const PROVENANCE_LABEL_ORDER = new Map<string, number>(
  ["ChatGPT", "Claude", "Anthropic", "Gemini", "OpenAI"].map((label, index) => [
    label,
    index,
  ])
);

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function normalizeLookupKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_/.-]+/g, " ")
    .replace(/\s+/g, " ");
}

function humanizeFallback(value: string): string {
  const collapsed = value.trim().replace(/[_/.-]+/g, " ").replace(/\s+/g, " ");
  if (!collapsed) return "";
  return collapsed
    .split(" ")
    .map((part) => {
      if (!part) return part;
      return part.slice(0, 1).toUpperCase() + part.slice(1).toLowerCase();
    })
    .join(" ");
}

export function normalizeSidebarProvenanceLabel(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  const key = normalizeLookupKey(trimmed);
  return CANONICAL_PROVENANCE_LABELS.get(key) ?? humanizeFallback(trimmed);
}

function readThreadProvenanceCandidates(thread: Thread): unknown[] {
  const metadata = asRecord(thread.metadata);
  if (!metadata) return [];

  const provenance = asRecord(metadata.provenance);
  const directProvenance =
    typeof metadata.provenance === "string" ? metadata.provenance : null;
  return [
    metadata.import_source,
    directProvenance,
    provenance?.import_source,
    provenance?.provider,
    provenance?.source,
    provenance?.label,
    provenance?.name,
    metadata.provider,
    metadata.source,
    metadata.label,
    metadata.name,
  ];
}

export function getSidebarThreadProvenanceLabel(thread: Thread): string | null {
  for (const candidate of readThreadProvenanceCandidates(thread)) {
    const label = normalizeSidebarProvenanceLabel(candidate);
    if (label) return label;
  }
  return null;
}

export function collectSidebarProvenanceOptions(
  threads: Thread[]
): SidebarProvenanceOption[] {
  const seen = new Set<string>();
  const options: SidebarProvenanceOption[] = [];

  for (const thread of threads) {
    const label = getSidebarThreadProvenanceLabel(thread);
    if (!label || seen.has(label)) continue;
    seen.add(label);
    options.push({ value: label, label });
  }

  return options.sort((a, b) => {
    const aRank = PROVENANCE_LABEL_ORDER.get(a.label) ?? Number.MAX_SAFE_INTEGER;
    const bRank = PROVENANCE_LABEL_ORDER.get(b.label) ?? Number.MAX_SAFE_INTEGER;
    if (aRank !== bRank) return aRank - bRank;
    return a.label.localeCompare(b.label);
  });
}

export function threadMatchesSidebarProvenance(
  thread: Thread,
  selectedProvenance: string | null
): boolean {
  if (!selectedProvenance) return true;
  return getSidebarThreadProvenanceLabel(thread) === selectedProvenance;
}
