import * as React from "react";
import {
  invokeTauriCommand,
  isTauriRuntime,
} from "@/lib/runtimeConfig";
import {
  extractBackendMediaPath,
  resolveMediaSrc,
} from "@/lib/mediaUrl";

type DesktopMediaStatus = "idle" | "loading" | "ready" | "error";

type UseRenderableMediaSrcResult = {
  src: string;
  status: DesktopMediaStatus;
  isBackendOwned: boolean;
};

type DesktopFetchedMedia = {
  contentType: string;
  bytesBase64: string;
  sizeBytes: number;
};

type DesktopMediaErrorKind =
  | "invalid_path"
  | "fetch_failed"
  | "type_not_allowed"
  | "too_large";

type DesktopMediaErrorPayload = {
  kind: DesktopMediaErrorKind | string;
  detail?: string | null;
};

type DesktopMediaCacheEntry = {
  objectUrl: string;
  sizeBytes: number;
  refCount: number;
  lastAccessAt: number;
};

const MAX_DESKTOP_MEDIA_CACHE_ENTRIES = 64;
const MAX_DESKTOP_MEDIA_CACHE_BYTES = 64 * 1024 * 1024;

const desktopMediaCache = new Map<string, DesktopMediaCacheEntry>();
const desktopMediaInFlight = new Map<
  string,
  Promise<DesktopMediaCacheEntry>
>();
let desktopMediaTotalBytes = 0;

function now(): number {
  return Date.now();
}

function revokeDesktopMediaEntry(entry: DesktopMediaCacheEntry): void {
  try {
    window.URL.revokeObjectURL(entry.objectUrl);
  } catch {
    // Ignore object URL cleanup failures during teardown.
  }
}

function trimDesktopMediaCache(force = false): void {
  const needsTrim =
    force ||
    desktopMediaCache.size > MAX_DESKTOP_MEDIA_CACHE_ENTRIES ||
    desktopMediaTotalBytes > MAX_DESKTOP_MEDIA_CACHE_BYTES;
  if (!needsTrim) return;

  const evictableEntries = Array.from(desktopMediaCache.entries())
    .filter(([, entry]) => entry.refCount <= 0)
    .sort((left, right) => left[1].lastAccessAt - right[1].lastAccessAt);

  while (
    evictableEntries.length > 0 &&
    (force ||
      desktopMediaCache.size > MAX_DESKTOP_MEDIA_CACHE_ENTRIES ||
      desktopMediaTotalBytes > MAX_DESKTOP_MEDIA_CACHE_BYTES)
  ) {
    const [path, entry] = evictableEntries.shift()!;
    if (!desktopMediaCache.delete(path)) continue;
    desktopMediaTotalBytes = Math.max(0, desktopMediaTotalBytes - entry.sizeBytes);
    revokeDesktopMediaEntry(entry);
  }
}

function decodeBase64Bytes(bytesBase64: string): Uint8Array {
  const decoded = window.atob(bytesBase64);
  const bytes = new Uint8Array(decoded.length);
  for (let index = 0; index < decoded.length; index += 1) {
    bytes[index] = decoded.charCodeAt(index);
  }
  return bytes;
}

function createDesktopMediaObjectUrl(payload: DesktopFetchedMedia): {
  objectUrl: string;
  sizeBytes: number;
} {
  const bytes = decodeBase64Bytes(payload.bytesBase64);
  const blob = new Blob([bytes], {
    type: payload.contentType || "application/octet-stream",
  });
  return {
    objectUrl: window.URL.createObjectURL(blob),
    sizeBytes:
      typeof payload.sizeBytes === "number" && Number.isFinite(payload.sizeBytes)
        ? payload.sizeBytes
        : bytes.byteLength,
  };
}

function extractDesktopMediaErrorPayload(error: unknown): DesktopMediaErrorPayload {
  if (error && typeof error === "object" && "kind" in error) {
    const candidate = error as DesktopMediaErrorPayload;
    return {
      kind: String(candidate.kind || "fetch_failed"),
      detail:
        typeof candidate.detail === "string" ? candidate.detail : undefined,
    };
  }

  if (typeof error === "string") {
    try {
      const parsed = JSON.parse(error) as DesktopMediaErrorPayload;
      if (parsed && typeof parsed === "object" && "kind" in parsed) {
        return {
          kind: String(parsed.kind || "fetch_failed"),
          detail:
            typeof parsed.detail === "string" ? parsed.detail : undefined,
        };
      }
    } catch {
      return { kind: "fetch_failed", detail: error };
    }
  }

  return { kind: "fetch_failed" };
}

async function fetchDesktopMediaEntry(
  canonicalPath: string
): Promise<DesktopMediaCacheEntry> {
  const existingEntry = desktopMediaCache.get(canonicalPath);
  if (existingEntry) {
    existingEntry.lastAccessAt = now();
    return existingEntry;
  }

  const pendingEntry = desktopMediaInFlight.get(canonicalPath);
  if (pendingEntry) {
    return pendingEntry;
  }

  const request = invokeTauriCommand<DesktopFetchedMedia>("desktop_fetch_media", {
    path: canonicalPath,
  })
    .then((payload) => {
      const renderedMedia = createDesktopMediaObjectUrl(payload);
      const entry: DesktopMediaCacheEntry = {
        objectUrl: renderedMedia.objectUrl,
        sizeBytes: renderedMedia.sizeBytes,
        refCount: 0,
        lastAccessAt: now(),
      };
      desktopMediaCache.set(canonicalPath, entry);
      desktopMediaTotalBytes += entry.sizeBytes;
      return entry;
    })
    .catch((error) => {
      throw extractDesktopMediaErrorPayload(error);
    })
    .finally(() => {
      desktopMediaInFlight.delete(canonicalPath);
    });

  desktopMediaInFlight.set(canonicalPath, request);
  return request;
}

async function acquireDesktopMediaEntry(
  canonicalPath: string
): Promise<DesktopMediaCacheEntry> {
  const entry = await fetchDesktopMediaEntry(canonicalPath);
  entry.refCount += 1;
  entry.lastAccessAt = now();
  trimDesktopMediaCache();
  return entry;
}

function releaseDesktopMediaEntry(canonicalPath: string): void {
  const entry = desktopMediaCache.get(canonicalPath);
  if (!entry) return;
  entry.refCount = Math.max(0, entry.refCount - 1);
  entry.lastAccessAt = now();
  trimDesktopMediaCache();
}

function resolveDirectRenderableState(
  src: string,
  isBackendOwned: boolean
): UseRenderableMediaSrcResult {
  if (!src) {
    return { src: "", status: "idle", isBackendOwned };
  }
  return { src, status: "ready", isBackendOwned };
}

export function useRenderableMediaSrc(
  src: string | null | undefined
): UseRenderableMediaSrcResult {
  const normalizedSrc = resolveMediaSrc(String(src ?? ""));
  const canonicalBackendMediaPath = extractBackendMediaPath(src);
  const shouldUseDesktopBlobPath =
    isTauriRuntime() && canonicalBackendMediaPath !== null;

  const [state, setState] = React.useState<UseRenderableMediaSrcResult>(() => {
    if (!shouldUseDesktopBlobPath) {
      return resolveDirectRenderableState(
        normalizedSrc,
        canonicalBackendMediaPath !== null
      );
    }
    if (!normalizedSrc) {
      return { src: "", status: "idle", isBackendOwned: true };
    }
    return { src: "", status: "loading", isBackendOwned: true };
  });

  React.useEffect(() => {
    if (!shouldUseDesktopBlobPath || !canonicalBackendMediaPath) {
      setState(
        resolveDirectRenderableState(
          normalizedSrc,
          canonicalBackendMediaPath !== null
        )
      );
      return;
    }
    if (!normalizedSrc) {
      setState({ src: "", status: "idle", isBackendOwned: true });
      return;
    }

    let cancelled = false;
    setState({ src: "", status: "loading", isBackendOwned: true });

    acquireDesktopMediaEntry(canonicalBackendMediaPath)
      .then((entry) => {
        if (cancelled) {
          releaseDesktopMediaEntry(canonicalBackendMediaPath);
          return;
        }
        setState({
          src: entry.objectUrl,
          status: "ready",
          isBackendOwned: true,
        });
      })
      .catch((error: DesktopMediaErrorPayload) => {
        if (cancelled) return;
        console.debug("[desktop-media]", {
          path: canonicalBackendMediaPath,
          kind: error.kind,
          detail: error.detail ?? null,
        });
        setState({
          src: "",
          status: "error",
          isBackendOwned: true,
        });
      });

    return () => {
      cancelled = true;
      releaseDesktopMediaEntry(canonicalBackendMediaPath);
    };
  }, [canonicalBackendMediaPath, normalizedSrc, shouldUseDesktopBlobPath]);

  return state;
}

export function __resetDesktopMediaCacheForTests(): void {
  for (const entry of desktopMediaCache.values()) {
    revokeDesktopMediaEntry(entry);
  }
  desktopMediaCache.clear();
  desktopMediaInFlight.clear();
  desktopMediaTotalBytes = 0;
}
