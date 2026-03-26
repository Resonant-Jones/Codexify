/**
 * useUploader.ts
 *
 * Handles chat/project uploads and emits UI hooks while supporting
 * optional disabled gating for turn-based composer locks.
 */
import { useCallback } from "react";
import { buildAuthenticatedFetchInit } from "../lib/api";
import { resolveApiUrl, resolveBackendUrl } from "../lib/runtimeConfig";

export type Accepted = ".pdf" | ".docx" | ".md" | ".txt" | ".png" | ".jpg" | ".jpeg" | ".webp";

export type UploadedAttachment = {
  kind: "image" | "document";
  id?: string;
  src_url: string;
  filename: string;
};

export type UploadedImageItem = {
  src: string;
  prompt: string;
  mock?: boolean;
  id?: string;
  filename?: string;
  src_url?: string;
  kind?: "image";
};

export type UploadedDocumentItem = {
  name: string;
  ext: string;
  mock?: boolean;
  source?: string;
  id?: string;
  filename?: string;
  src_url?: string;
  kind?: "document";
  embeddingStatus?: string;
  embeddingError?: string;
  embeddingStartedAt?: string;
  embeddingCompletedAt?: string;
};

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const DOC_EXT = new Set([".pdf", ".docx", ".md", ".txt"]);

// Convert backend-returned media paths (e.g. "/media/images/...jpg") into an absolute URL
// so the frontend can render them even when served from a different dev origin (5173 vs 8888).
export const toAbsoluteMediaUrl = (srcUrl: string) => {
  if (!srcUrl) return srcUrl;
  if (srcUrl.startsWith("http://") || srcUrl.startsWith("https://")) return srcUrl;
  return resolveBackendUrl(srcUrl);
};

function extOf(name: string): Accepted | null {
  const m = name.toLowerCase().match(/\.(pdf|docx|md|txt|png|jpg|jpeg|webp)$/);
  if (!m) return null;
  const e = `.${m[1]}` as Accepted;
  return e;
}

function normalizePositiveIdString(
  v: number | string | undefined | null
): string | undefined {
  if (v === undefined || v === null) return undefined;
  const s = String(v).trim();
  if (!s.length) return undefined;
  const parsed = Number(s);
  if (Number.isFinite(parsed)) {
    return parsed > 0 ? String(parsed) : undefined;
  }
  return s;
}

function toIdString(v: number | string | undefined | null): string | undefined {
  return normalizePositiveIdString(v);
}

function inferIdFromTag(tag: string | undefined, prefix: string): string | undefined {
  if (!tag) return undefined;
  const m = tag.match(new RegExp(`(?:^|\\s)${prefix}:(\\d+)(?:$|\\s)`));
  return normalizePositiveIdString(m?.[1]);
}

function inferIdFromPathname(regexes: RegExp[]): string | undefined {
  if (typeof window === "undefined") return undefined;

  // Support SPA routers that encode routes in `location.hash` (e.g. /#/chat/2)
  // and also allow IDs to come from query strings (e.g. ?thread_id=2).
  const loc = window.location;
  const candidates: string[] = [];

  const pathname = loc?.pathname || "";
  const hash = (loc?.hash || "").replace(/^#/, "");
  const search = loc?.search || "";

  // Normalize hash to look like a path (remove leading / if duplicated)
  const hashPath = hash.startsWith("/") ? hash : `/${hash}`;

  candidates.push(pathname);
  if (hash && hash !== "#") candidates.push(hashPath);

  // Add search string so regexes can match e.g. thread_id=2
  if (search) candidates.push(search);

  for (const p of candidates) {
    for (const rx of regexes) {
      const m = p.match(rx);
      if (m?.[1]) return normalizePositiveIdString(m[1]);
    }
  }

  return undefined;
}

function inferIdFromStorage(keys: string[]): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    for (const k of keys) {
      const v = localStorage.getItem(k);
      const normalized = normalizePositiveIdString(v);
      if (normalized) return normalized;
    }
  } catch {}
  return undefined;
}

const normalizeProjectName = (value: unknown): string =>
  String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");

function isDefaultProjectName(value: unknown): boolean {
  const normalized = normalizeProjectName(value);
  return normalized === "general" || normalized === "loose threads";
}

export function useUploader({
  onImages,
  onDocuments,
  onAnyUpload,
  onUploaded,
  tag,
  projectId,
  threadId,
  explicitAuth,
  disabled,
}: {
  onImages: (items: UploadedImageItem[]) => void;
  onDocuments: (items: UploadedDocumentItem[]) => void;
  onAnyUpload?: () => void;
  onUploaded?: (items: UploadedAttachment[]) => void;
  tag?: string; // optional source tag (e.g., "chat", "project:<id>")
  projectId?: number | string;
  threadId?: number | string;
  explicitAuth?: boolean;
  disabled?: boolean;
}) {
  const accept = ".pdf,.docx,.md,.txt,.png,.jpg,.jpeg,.webp";
  const forceApiKey = explicitAuth || tag === "gallery";

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const withAuth = (init: RequestInit): RequestInit =>
      buildAuthenticatedFetchInit(init, { forceApiKey });
    const apiUrl = (path: string): string => resolveApiUrl(path);

    if (disabled) {
      // Respect upstream gating (e.g., turn-in-flight) by ignoring new uploads.
      return;
    }
    const arr = Array.from(files);
    const imgs: UploadedImageItem[] = [];
    const docs: UploadedDocumentItem[] = [];
    const attachments: UploadedAttachment[] = [];

    // Resolve IDs robustly (avoid truthy checks; allow 0; infer from tag/path/storage when missing)
    let effectiveProjectId =
      toIdString(projectId) ||
      inferIdFromTag(tag, "project") ||
      inferIdFromPathname([
        /\bprojects\/(\d+)\b/i,
        /\bproject\/(\d+)\b/i,
        /[?&]project_id=(\d+)\b/i,
        /[?&]projectId=(\d+)\b/i,
      ]) ||
      inferIdFromStorage(["cfy.projectId", "cfy.activeProjectId", "projectId"]);

    let effectiveThreadId =
      toIdString(threadId) ||
      inferIdFromTag(tag, "thread") ||
      inferIdFromPathname([
        /\bchat\/(\d+)\b/i,
        /\bthreads\/(\d+)\b/i,
        /[?&]thread_id=(\d+)\b/i,
        /[?&]threadId=(\d+)\b/i,
      ]) ||
      inferIdFromStorage(["cfy.threadId", "cfy.activeThreadId", "threadId"]);

    // If project_id is missing but we have a thread_id, try to derive project_id from the thread list.
    // This fixes uploads from routes like /chat/:id where project context isn't encoded in the URL.
    async function resolveProjectIdFromThread(tid: string): Promise<string | undefined> {
      // Try a few plausible endpoints because the backend API surface can vary.
      // We only need a project id; accept either snake_case or camelCase fields.
      const candidates = [
        "/api/chat/threads",
        `/api/chat/${encodeURIComponent(tid)}`,
        `/api/chat/${encodeURIComponent(tid)}/thread`,
        `/api/chat/${encodeURIComponent(tid)}/meta`,
      ];

      const extract = (j: any): string | undefined => {
        // Common shapes:
        // - { threads: [...] }
        // - [...] (array)
        // - { thread: {...} }
        // - { ...thread fields... }
        const threads: any[] = Array.isArray(j)
          ? j
          : Array.isArray(j?.threads)
            ? j.threads
            : [];

        if (threads.length) {
          const hit = threads.find((t) => String(t?.id) === String(tid));
          const pid = hit?.project_id ?? hit?.projectId ?? hit?.project?.id;
          return normalizePositiveIdString(pid);
        }

        const thread = j?.thread ?? j;
        const pid = thread?.project_id ?? thread?.projectId ?? thread?.project?.id;
        return normalizePositiveIdString(pid);
      };

      for (const url of candidates) {
        try {
          const r = await fetch(apiUrl(url), withAuth({ method: "GET" }));
          if (!r.ok) continue;
          const j: any = await r.json();
          const pid = extract(j);
          if (pid !== undefined) return pid;
        } catch {
          // keep trying
        }
      }

      return undefined;
    }

    if (effectiveProjectId === undefined && effectiveThreadId !== undefined) {
      const inferred = await resolveProjectIdFromThread(String(effectiveThreadId));
      if (inferred !== undefined) effectiveProjectId = inferred;
    }

    async function resolveDefaultProjectId(): Promise<string | undefined> {
      const cached =
        inferIdFromStorage(["cfy.generalProjectId", "cfy.defaultProjectId"]) ||
        undefined;
      if (cached !== undefined) return cached;

      try {
        const response = await fetch(apiUrl("/api/projects"), withAuth({ method: "GET" }));
        if (!response.ok) return undefined;
        const payload: any = await response.json();
        const list = Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.projects)
          ? payload.projects
          : [];
        const match = list.find((project: any) =>
          isDefaultProjectName(project?.name)
        );
        const resolved =
          match?.id != null
            ? String(match.id)
            : match?.project_id != null
            ? String(match.project_id)
            : undefined;
        if (!resolved) return undefined;
        try {
          localStorage.setItem("cfy.generalProjectId", resolved);
          localStorage.setItem("cfy.defaultProjectId", resolved);
        } catch {}
        return resolved;
      } catch {
        return undefined;
      }
    }

    if (effectiveProjectId === undefined) {
      const fallbackProjectId = await resolveDefaultProjectId();
      if (fallbackProjectId !== undefined) {
        effectiveProjectId = fallbackProjectId;
      }
    }

    // Persist inferred context for later uploads (best-effort)
    try {
      if (effectiveProjectId !== undefined) {
        localStorage.setItem("cfy.activeProjectId", String(effectiveProjectId));
        localStorage.setItem("cfy.projectId", String(effectiveProjectId));
      }
      if (effectiveThreadId !== undefined) {
        localStorage.setItem("cfy.activeThreadId", String(effectiveThreadId));
      }
    } catch {}
    // Debug: let the app/devtools introspect what IDs were actually used.
    try {
      window.dispatchEvent(
        new CustomEvent("cfy:uploader:context", {
          detail: {
            projectId: effectiveProjectId,
            threadId: effectiveThreadId,
            tag,
            pathname: typeof window !== "undefined" ? window.location?.pathname : undefined,
            hash: typeof window !== "undefined" ? window.location?.hash : undefined,
            search: typeof window !== "undefined" ? window.location?.search : undefined,
          },
        })
      );
    } catch {}

    // Counters used for toast + error tracking (must be defined before any upload attempts)
    let imgSuccess = 0;
    let docSuccess = 0;
    let totalFailed = 0;

    const readAsDataUrl = (file: File) => new Promise<string>((res, rej) => {
      const rd = new FileReader();
      rd.onload = () => res(String(rd.result || ""));
      rd.onerror = () => rej(new Error("read error"));
      rd.readAsDataURL(file);
    });
    const readAsText = (file: File) => new Promise<string>((res, rej) => {
      const rd = new FileReader();
      rd.onload = () => res(String(rd.result || ""));
      rd.onerror = () => rej(new Error("read error"));
      rd.readAsText(file);
    });

    // Collect ingestion payloads for optional backend POST
    type IngestItem = { filename: string; mimeType: string; fileBytes: string; source?: string; tags?: string[] };
    const ingestItems: IngestItem[] = [];

    for (const f of arr) {
      const ext = extOf(f.name);
      if (!ext) continue;
      try {
        if (IMAGE_EXT.has(ext)) {
          // POST to backend /api/media/upload/image
          let uploadedImage: any = null;
          try {
            const formData = new FormData();
            formData.append("file", f);
            if (effectiveProjectId !== undefined) formData.append("project_id", effectiveProjectId);
            if (effectiveThreadId !== undefined) {
              formData.append("thread_id", effectiveThreadId);
              formData.append("threadId", effectiveThreadId);
            }

            const uploadResp = await fetch(
              apiUrl("/api/media/upload/image"),
              withAuth({
                method: "POST",
                body: formData,
              })
            );

            if (uploadResp.ok) {
              uploadedImage = await uploadResp.json();
            } else {
              throw new Error(`Image upload failed: ${uploadResp.status}`);
            }
          } catch {
            totalFailed++;
          }

          const uploadedOk = !!uploadedImage?.src_url;

          // Use server response URL (persisted) or fall back to local data URL (preview-only)
          const imageUrl = uploadedOk
            ? toAbsoluteMediaUrl(uploadedImage.src_url)
            : (await readAsDataUrl(f));

          imgs.push({
            src: imageUrl,
            prompt: f.name,
            mock: !uploadedOk,
            id: uploadedImage?.id,
            filename: uploadedImage?.filename || f.name,
            src_url: uploadedOk ? imageUrl : undefined,
            kind: "image",
          });
          if (uploadedOk) imgSuccess += 1;
          if (uploadedOk) {
            attachments.push({
              kind: "image",
              id: uploadedImage?.id,
              src_url: imageUrl,
              filename: uploadedImage?.filename || f.name,
            });
          }

          // data URL looks like data:mime;base64,XXXX
          const data = await readAsDataUrl(f);
          const base64 = (data.split(",")[1] || "");
          ingestItems.push({ filename: f.name, mimeType: f.type || "image/*", fileBytes: base64, source: tag || "upload", tags: [] });
        } else if (DOC_EXT.has(ext)) {
          // For text-like files, read content and optionally request embeddings
          let preview = f.name;
          if (ext === ".txt" || ext === ".md") {
            try {
              const txt = await readAsText(f);
              preview = txt.slice(0, 2000);
            } catch {}
          }

          // POST to backend /api/media/upload/document
          let uploadedDoc: any = null;
          try {
            const formData = new FormData();
            formData.append("file", f);
            if (effectiveProjectId !== undefined) {
              formData.append("project_id", effectiveProjectId);
              formData.append("projectId", effectiveProjectId);
            }
            if (effectiveThreadId !== undefined) {
              formData.append("thread_id", effectiveThreadId);
              formData.append("threadId", effectiveThreadId);
            }

            // Try multipart/form-data first (the "standard" upload method).
            let uploadResp = await fetch(
              apiUrl("/api/media/upload/document"),
              withAuth({
                method: "POST",
                body: formData,
              })
            );

            // If the backend is currently validating a JSON body (Pydantic model) instead of FormData,
            // it will often return 422 with missing `body.project_id` / `body.thread_id`. In that case,
            // fall back to a JSON upload using base64 bytes.
            if (!uploadResp.ok) {
              let errJson: any = null;
              try {
                errJson = await uploadResp.clone().json();
              } catch {}

              const detailArr: any[] = Array.isArray(errJson?.detail) ? errJson.detail : [];
              const needsJsonBody =
                uploadResp.status === 422 &&
                detailArr.some((d: any) => {
                  const loc = Array.isArray(d?.loc) ? d.loc : [];
                  // Any body-level missing/invalid for project/thread should trigger JSON fallback.
                  return (
                    loc[0] === "body" &&
                    loc.some((x: any) =>
                      String(x).toLowerCase().includes("project") || String(x).toLowerCase().includes("thread")
                    )
                  );
                });

              if (needsJsonBody) {
                // Read file as base64 once for JSON fallback.
                const dataUrl = await readAsDataUrl(f);
                const base64 = dataUrl.split(",")[1] || "";

                // Try a couple common payload shapes (snake_case + camelCase) to match backend variants.
                const pidNum = Number(effectiveProjectId);
                const tidNum = Number(effectiveThreadId);

                const payloads: any[] = [
                  {
                    project_id: Number.isFinite(pidNum) ? pidNum : effectiveProjectId,
                    thread_id: Number.isFinite(tidNum) ? tidNum : effectiveThreadId,
                    filename: f.name,
                    mime_type: f.type || "application/octet-stream",
                    file_bytes: base64,
                  },
                  {
                    projectId: Number.isFinite(pidNum) ? pidNum : effectiveProjectId,
                    threadId: Number.isFinite(tidNum) ? tidNum : effectiveThreadId,
                    filename: f.name,
                    mimeType: f.type || "application/octet-stream",
                    fileBytes: base64,
                  },
                  {
                    project_id: Number.isFinite(pidNum) ? pidNum : effectiveProjectId,
                    thread_id: Number.isFinite(tidNum) ? tidNum : effectiveThreadId,
                    filename: f.name,
                    mimeType: f.type || "application/octet-stream",
                    fileBytes: base64,
                  },
                ];

                let jsonOk = false;
                let lastStatus = uploadResp.status;

                for (const payload of payloads) {
                  const r = await fetch(
                    apiUrl("/api/media/upload/document"),
                    withAuth({
                      method: "POST",
                      headers: {
                        "content-type": "application/json",
                      },
                      body: JSON.stringify(payload),
                    })
                  );
                  lastStatus = r.status;
                  if (r.ok) {
                    uploadResp = r;
                    jsonOk = true;
                    break;
                  }
                }

                if (!jsonOk) {
                  throw new Error(`Upload failed (JSON fallback): ${lastStatus}`);
                }
              } else {
                throw new Error(`Upload failed: ${uploadResp.status}`);
              }
            }

            uploadedDoc = await uploadResp.json();
          } catch {
            totalFailed++;
            continue;
          }

          const serverDoc = uploadedDoc?.document || uploadedDoc || {};
          const filename = serverDoc?.filename || f.name;
          const docUrlRaw = serverDoc?.src_url || uploadedDoc?.src_url;
          const docUrl = docUrlRaw ? toAbsoluteMediaUrl(String(docUrlRaw)) : "";
          const docEntry = {
            name: filename.replace(/\.[^.]+$/, ""),
            ext: ext.replace(".", ""),
            source: tag,
            id: serverDoc?.id || uploadedDoc?.id,
            filename,
            src_url: docUrl || undefined,
            kind: "document" as const,
            embeddingStatus:
              serverDoc?.embedding_status || serverDoc?.embeddingStatus,
            embeddingError:
              serverDoc?.embedding_error || serverDoc?.embeddingError,
            embeddingStartedAt:
              serverDoc?.embedding_started_at ||
              serverDoc?.embeddingStartedAt,
            embeddingCompletedAt:
              serverDoc?.embedding_completed_at ||
              serverDoc?.embeddingCompletedAt,
          };
          docs.push(docEntry);
          docSuccess += 1;
          if (docUrl) {
            attachments.push({
              kind: "document",
              id: docEntry.id,
              src_url: docUrl,
              filename,
            });
          }

          const data = await readAsDataUrl(f);
          const base64 = (data.split(",")[1] || "");
          ingestItems.push({ filename: f.name, mimeType: f.type || "application/octet-stream", fileBytes: base64, source: tag || "upload", tags: [] });
          // Best-effort embedding call; ignore failures.
          try {
            const body = { texts: [preview] } as any;
            fetch(
              apiUrl("/api/embeddings"),
              withAuth({
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify(body),
              })
            ).catch(() => {});
          } catch {}
        }
      } catch {}
    }


    if (imgs.length) {
      onImages(imgs);
    }
    if (docs.length) {
      onDocuments(docs);
    }
    if (attachments.length) {
      onUploaded?.(attachments);
    }
    // Emit debug hook with full payloads
    try { window.dispatchEvent(new CustomEvent("cfy:documents:upload", { detail: { items: ingestItems } })); } catch {}

    // Optional ingestion POST if enabled and endpoint configured
    try {
      const enabled = (typeof window !== "undefined") && localStorage.getItem("cfy.ingest.enabled") === "true";
      const endpoint = (import.meta as any).env?.VITE_INGESTION_ENDPOINT as string | undefined;
      const runtimeOverride = localStorage.getItem("cfy.ingest.endpoint.override");
      const effectiveEndpoint = runtimeOverride || endpoint;
      if (enabled && effectiveEndpoint && ingestItems.length) {
        const resolvedIngestEndpoint =
          /^https?:\/\//i.test(effectiveEndpoint)
            ? effectiveEndpoint
            : apiUrl(effectiveEndpoint);
        for (const it of ingestItems) {
          try {
            const resp = await fetch(
              resolvedIngestEndpoint,
              withAuth({
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify({ ...it }),
              })
            );
            if (!resp.ok) throw new Error(String(resp.status));
          } catch (err) {
            totalFailed++;
          }
        }
      }
    } catch {}
    try {
      let summary = [];
      if (docSuccess) summary.push(`${docSuccess} document${docSuccess > 1 ? "s" : ""}`);
      if (imgSuccess) summary.push(`${imgSuccess} image${imgSuccess > 1 ? "s" : ""}`);

      let toastMessage = "";
      let toastType: "success" | "error" = "success";

      if (summary.length) {
        toastMessage = `Uploaded ${summary.join(" and ")} successfully.`;
        if (totalFailed > 0) {
          toastMessage += ` (${totalFailed} failed)`;
          toastType = "error";
        }
      } else if (totalFailed > 0) {
        toastMessage = `All ${totalFailed} uploads failed.`;
        toastType = "error";
      } else {
        toastMessage = "No files were processed.";
        toastType = "error";
      }

      window.dispatchEvent(new CustomEvent("cfy:toast", {
        detail: {
          message: toastMessage,
          type: toastType
        }
      }));
    } catch {}

    try {
      localStorage.setItem("cfy.hasUserUpload", "true");
    } catch {}
    onAnyUpload?.();
  }, [disabled, forceApiKey, onImages, onDocuments, onAnyUpload, tag, projectId, threadId]);

  return {
    accept,
    handleFiles,
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      if (disabled) return;
      if (e.dataTransfer?.files?.length) handleFiles(e.dataTransfer.files);
    },
    onDragOver: (e: React.DragEvent) => e.preventDefault(),
    pick: () => {
      if (disabled) return;
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.accept = accept;
      input.onchange = () => {
        if (input.files) handleFiles(input.files);
      };
      input.click();
    },
  } as const;
}

export default useUploader;
