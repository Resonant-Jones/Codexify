import api from "@/lib/api";
import type { DocumentLike } from "@/types/documents";

export type DocumentContextTile = {
  id: string;
  title: string;
  preview?: string;
  ext?: string;
  type: "document";
};

export type DocumentContextContent = {
  tile: DocumentContextTile;
  content: string;
};

type EncodedDocumentTile = {
  id: string;
  title: string;
  preview?: string;
  ext?: string;
};

type EncodedDocumentContent = {
  id: string;
};

const DOC_TILE_MARKER_PREFIX = "cfy-doc-tile";
const DOC_CONTENT_MARKER_PREFIX = "cfy-doc-content";
const EXCESSIVE_BLANK_LINES_RE = /\n{3,}/g;

function normalizeString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function normalizePreview(preview?: string): string | undefined {
  const trimmed = normalizeString(preview);
  if (!trimmed) return undefined;
  return trimmed.length > 180 ? `${trimmed.slice(0, 177).trimEnd()}...` : trimmed;
}

function toBase64Url(input: string): string {
  const bytes = new TextEncoder().encode(input);
  if (typeof btoa === "function") {
    let binary = "";
    for (const byte of bytes) {
      binary += String.fromCharCode(byte);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  if (typeof Buffer !== "undefined") {
    return Buffer.from(bytes)
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  }

  throw new Error("Base64 encoder unavailable");
}

function fromBase64Url(input: string): string | null {
  const normalized = normalizeString(input);
  if (!normalized) return null;
  try {
    const padded = normalized.replace(/-/g, "+").replace(/_/g, "/");
    const withPadding = `${padded}${"=".repeat((4 - (padded.length % 4)) % 4)}`;
    if (typeof atob === "function") {
      const binary = atob(withPadding);
      const bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
      }
      return new TextDecoder().decode(bytes);
    }

    if (typeof Buffer !== "undefined") {
      return new TextDecoder().decode(Buffer.from(withPadding, "base64"));
    }
    return null;
  } catch {
    return null;
  }
}

function encodePayload(payload: unknown): string {
  return toBase64Url(JSON.stringify(payload));
}

function decodePayload<T>(payload: string): T | null {
  const decoded = fromBase64Url(payload);
  if (!decoded) return null;
  try {
    return JSON.parse(decoded) as T;
  } catch {
    return null;
  }
}

function resolveDocumentTitle(
  doc:
    | Pick<DocumentLike, "title" | "name">
    | (Partial<Pick<DocumentLike, "title" | "name">> & Record<string, unknown>)
): string {
  const title = normalizeString((doc as { title?: unknown }).title);
  if (title) return title;
  const name = normalizeString((doc as { name?: unknown }).name);
  return name || "Untitled";
}

export function createDocumentContextTile(
  doc:
    | Pick<DocumentLike, "id" | "title" | "name" | "ext">
    | (Partial<Pick<DocumentLike, "id" | "title" | "name" | "ext">> &
        Record<string, unknown>),
  preview?: string
): DocumentContextTile | null {
  const id = normalizeString((doc as { id?: unknown }).id);
  if (!id) return null;
  const tile: DocumentContextTile = {
    id,
    title: resolveDocumentTitle(doc),
    type: "document",
  };
  const ext = normalizeString((doc as { ext?: unknown }).ext).replace(/^\./, "");
  if (ext) tile.ext = ext.toLowerCase();
  const normalizedPreview = normalizePreview(preview);
  if (normalizedPreview) tile.preview = normalizedPreview;
  return tile;
}

function buildTileMarker(tile: DocumentContextTile): string {
  const payload: EncodedDocumentTile = {
    id: tile.id,
    title: tile.title,
    preview: tile.preview,
    ext: tile.ext,
  };
  return `<!-- ${DOC_TILE_MARKER_PREFIX}:${encodePayload(payload)} -->`;
}

function buildContentMarkerStart(id: string): string {
  return `<!-- ${DOC_CONTENT_MARKER_PREFIX}:start:${encodePayload({ id })} -->`;
}

function buildContentMarkerEnd(id: string): string {
  return `<!-- ${DOC_CONTENT_MARKER_PREFIX}:end:${encodePayload({ id })} -->`;
}

function extractDocumentContentBlocks(
  content: string
): {
  tiles: DocumentContextTile[];
  blocks: Array<{ id: string; content: string }>;
  text: string;
} {
  const tileMarkerRe = /<!--\s*cfy-doc-tile:([^>]*?)\s*-->/gi;
  const contentBlockRe =
    /<!--\s*cfy-doc-content:start:([^>]*?)\s*-->\s*([\s\S]*?)\s*<!--\s*cfy-doc-content:end:\1\s*-->/gi;

  const tiles: DocumentContextTile[] = [];
  let stripped = content || "";

  stripped = stripped.replace(tileMarkerRe, (_match, rawPayload: string) => {
    const payload = decodePayload<EncodedDocumentTile>(String(rawPayload || ""));
    if (!payload?.id) return "";
    tiles.push({
      id: payload.id,
      title: payload.title || "Untitled",
      preview: payload.preview || undefined,
      ext: payload.ext || undefined,
      type: "document",
    });
    return "";
  });

  const blocks: Array<{ id: string; content: string }> = [];
  stripped = stripped.replace(
    contentBlockRe,
    (_match, rawPayload: string, blockContent: string) => {
      const payload = decodePayload<EncodedDocumentContent>(String(rawPayload || ""));
      const id = normalizeString(payload?.id);
      if (!id) return "";
      const normalizedBlockContent = String(blockContent || "").trim();
      blocks.push({ id, content: normalizedBlockContent });
      return "";
    }
  );

  stripped = stripped.replace(EXCESSIVE_BLANK_LINES_RE, "\n\n").trim();

  return { tiles, blocks, text: stripped };
}

export function parseDocumentContextContent(content: string): {
  tiles: DocumentContextTile[];
  text: string;
} {
  const { tiles, text } = extractDocumentContentBlocks(content);
  return { tiles, text };
}

export function serializeDocumentContextMessage(
  text: string,
  contents: DocumentContextContent[]
): string {
  const parts: string[] = [];

  for (const entry of contents) {
    const tile = entry?.tile;
    if (!tile?.id || !tile.title) continue;
    parts.push(buildTileMarker(tile));

    const content = normalizeString(entry.content);
    if (!content) continue;

    parts.push(
      [
        buildContentMarkerStart(tile.id),
        content,
        buildContentMarkerEnd(tile.id),
      ].join("\n")
    );
  }

  const body = normalizeString(text);
  if (body) {
    parts.push(body);
  }

  return parts.join("\n\n").trim();
}

export async function loadDocumentContentById(documentId: string): Promise<{
  id: string;
  title: string;
  ext?: string;
  content: string;
}> {
  const normalizedId = normalizeString(documentId);
  if (!normalizedId) {
    throw new Error("Document id is required");
  }

  const response = await api.get(`/media/documents/${encodeURIComponent(normalizedId)}`);
  const payload = response?.data ?? {};
  const content =
    normalizeString(payload.content) ||
    normalizeString(payload.parsed_text) ||
    normalizeString(payload.parsedText);
  if (!content) {
    throw new Error("Document content is missing");
  }

  return {
    id: normalizeString(payload.id) || normalizedId,
    title: normalizeString(payload.title) || normalizeString(payload.filename) || "Untitled",
    ext: normalizeString(payload.ext) || undefined,
    content,
  };
}

export function getDocumentContextPreviewText(content: string): string {
  return parseDocumentContextContent(content).text;
}

export function collectDocumentContextTiles(content: string): DocumentContextTile[] {
  return parseDocumentContextContent(content).tiles;
}
