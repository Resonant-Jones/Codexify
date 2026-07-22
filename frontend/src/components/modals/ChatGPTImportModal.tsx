/**
 * ChatGPTImportModal – Import ChatGPT conversation export files
 *
 * Handles file selection and upload to the migration endpoint.
 * Displays loading, success, and error states.
 */

import React, { useState, useRef, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import {
  clearAccountImportCoordinatorResult,
  getAccountImportCoordinatorSnapshot,
  startOpenAIAccountImport,
  subscribeAccountImportCoordinator,
} from "@/features/imports/accountImportCoordinator";
import api, {
  normalizeChatGptImportStats,
  normalizeImportRuntimeError,
  preflightBackendAvailability,
  type ChatGptImportStats,
} from "@/lib/api";
import type { AccountImportBrowserFile } from "@/lib/api";

interface ChatGPTImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userName?: string;
  onImported?: (stats: MigrationStats) => void;
}

export interface MigrationStats {
  threads_imported: ChatGptImportStats["threads_imported"];
  messages_imported: ChatGptImportStats["messages_imported"];
  projects_created?: ChatGptImportStats["projects_created"];
  projects_reused?: ChatGptImportStats["projects_reused"];
  messages_filtered?: ChatGptImportStats["messages_filtered"];
  embedding_candidates: ChatGptImportStats["embedding_candidates"];
  embeddings_persisted: ChatGptImportStats["embeddings_persisted"];
  embeddings_failed: ChatGptImportStats["embeddings_failed"];
  embedding_coverage_degraded: ChatGptImportStats["embedding_coverage_degraded"];
}

const LARGE_IMPORT_BYTES = 50 * 1024 * 1024;
const CHATGPT_EXPORT_ACCEPT =
  ".json,.dat,application/json,application/octet-stream";

function isZipExport(file: File): boolean {
  return (
    file.name.toLowerCase().endsWith(".zip") || file.type === "application/zip"
  );
}

type BrowserFileEntry = {
  isFile: true;
  isDirectory: false;
  fullPath: string;
  file: (
    success: (file: File) => void,
    failure?: (error: DOMException) => void
  ) => void;
};

type BrowserDirectoryReader = {
  readEntries: (
    success: (entries: BrowserEntry[]) => void,
    failure?: (error: DOMException) => void
  ) => void;
};

type BrowserDirectoryEntry = {
  isFile: false;
  isDirectory: true;
  fullPath: string;
  createReader: () => BrowserDirectoryReader;
};

type BrowserEntry = BrowserFileEntry | BrowserDirectoryEntry;

function readEntryFile(entry: BrowserFileEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file(resolve, reject));
}

async function readAllDirectoryEntries(
  entry: BrowserDirectoryEntry
): Promise<BrowserEntry[]> {
  const reader = entry.createReader();
  const entries: BrowserEntry[] = [];
  while (true) {
    const page = await new Promise<BrowserEntry[]>((resolve, reject) =>
      reader.readEntries(resolve, reject)
    );
    if (page.length === 0) return entries;
    entries.push(...page);
  }
}

async function enumerateEntry(
  entry: BrowserEntry
): Promise<AccountImportBrowserFile[]> {
  if (entry.isFile) {
    const file = await readEntryFile(entry);
    return [
      {
        file,
        relativePath: entry.fullPath.replace(/^\/+/, "") || file.name,
      },
    ];
  }
  const nested = await readAllDirectoryEntries(entry);
  const batches = await Promise.all(nested.map(enumerateEntry));
  return batches.flat();
}

export async function enumerateOpenAIExportDrop(
  dataTransfer: DataTransfer
): Promise<AccountImportBrowserFile[]> {
  const transferItems = Array.from(dataTransfer.items || []);
  const entries = transferItems
    .map((item) =>
      (
        item as DataTransferItem & {
          webkitGetAsEntry?: () => BrowserEntry | null;
        }
      ).webkitGetAsEntry?.()
    )
    .filter((entry): entry is BrowserEntry => Boolean(entry));
  if (entries.length > 0) {
    const nested = await Promise.all(entries.map(enumerateEntry));
    return nested.flat();
  }
  return Array.from(dataTransfer.files || []).map((file) => ({
    file,
    relativePath:
      (file as File & { webkitRelativePath?: string }).webkitRelativePath ||
      file.name,
  }));
}

function selectedFolderFiles(files: FileList | null): AccountImportBrowserFile[] {
  return Array.from(files || []).map((file) => ({
    file,
    relativePath:
      (file as File & { webkitRelativePath?: string }).webkitRelativePath ||
      file.name,
  }));
}

const formatFileSize = (size: number) => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.ceil(size / 1024)} KB`;
};

function formatJobDetail(detail: Record<string, unknown>): string {
  return [detail.code, detail.path, detail.message]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(" — ");
}

export function ChatGPTImportModal({
  open,
  onOpenChange,
  userName = "user",
  onImported,
}: ChatGPTImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const isLargeImport = Boolean(file && file.size >= LARGE_IMPORT_BYTES);
  const [isDragOver, setIsDragOver] = useState(false);
  const [status, setStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [stats, setStats] = useState<MigrationStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const folderRef = useRef<HTMLInputElement | null>(null);
  const accountImport = useSyncExternalStore(
    subscribeAccountImportCoordinator,
    getAccountImportCoordinatorSnapshot,
    getAccountImportCoordinatorSnapshot
  );
  const accountImportActive = accountImport.phase !== "idle";
  const accountImportTransferring = ["preflighting", "transferring"].includes(
    accountImport.phase
  );
  const accountImportInProgress = [
    "preflighting",
    "transferring",
    "accepted",
    "running",
  ].includes(accountImport.phase);

  const setSelectedFile = (nextFile: File | null) => {
    if (
      ["completed", "completed_with_warnings", "failed"].includes(
        accountImport.phase
      )
    ) {
      clearAccountImportCoordinatorResult();
    }
    setFile(nextFile);
    setStatus("idle");
    setError(null);
    setErrorDetail(null);
    setStats(null);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) {
      return;
    }
    setSelectedFile(f);
  };

  const startFolderImport = (files: AccountImportBrowserFile[]) => {
    setFile(null);
    setStatus("idle");
    setError(null);
    setErrorDetail(null);
    setStats(null);
    void startOpenAIAccountImport(files, userName).catch(() => {
      // The module-level coordinator owns and exposes the durable error state.
    });
  };

  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = selectedFolderFiles(e.target.files);
    if (files.length === 0) return;
    startFolderImport(files);
    e.target.value = "";
  };

  const handleFileDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const transferItems = Array.from(e.dataTransfer.items || []);
    const hasDirectoryEntry = transferItems.some(
      (item) =>
        Boolean(
          (
            item as DataTransferItem & {
              webkitGetAsEntry?: () => BrowserEntry | null;
            }
          ).webkitGetAsEntry?.()?.isDirectory
        )
    );
    if (transferItems.length === 0) {
      const dropped = Array.from(e.dataTransfer.files || []).map((droppedFile) => ({
        file: droppedFile,
        relativePath:
          (droppedFile as File & { webkitRelativePath?: string })
            .webkitRelativePath || droppedFile.name,
      }));
      if (dropped.length === 0) return;
      if (dropped.length > 1 || isZipExport(dropped[0].file)) {
        startFolderImport(dropped);
        return;
      }
      setSelectedFile(dropped[0].file);
      return;
    }
    try {
      const dropped = await enumerateOpenAIExportDrop(e.dataTransfer);
      if (dropped.length === 0) return;
      if (
        hasDirectoryEntry ||
        dropped.length > 1 ||
        isZipExport(dropped[0].file)
      ) {
        startFolderImport(dropped);
        return;
      }
      setSelectedFile(dropped[0].file);
    } catch (dropError) {
      setStatus("error");
      setError(
        dropError instanceof Error
          ? dropError.message
          : "Unable to read the dropped export folder."
      );
      setErrorDetail(null);
      return;
    }
  };

  const handleMigrate = async () => {
    if (!file) return;

    if (isZipExport(file)) {
      startFolderImport([{ file, relativePath: file.name }]);
      return;
    }

    setError(null);
    setErrorDetail(null);

    const availability = await preflightBackendAvailability();
    if (!availability.ok) {
      setStatus("error");
      setError(
        availability.message ||
          "ChatGPT import cannot start because the local backend runtime is unavailable. Restore the local stack and retry."
      );
      setErrorDetail(availability.technicalDetail || null);
      return;
    }

    setStatus("uploading");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await api.post(
        "/api/upload-chatgpt-export",
        formData,
        {
          headers: {
            "X-User-Id": userName,
          },
          // Large imports can exceed the default HTTP timeout.
          timeout: 0,
        }
      );

      const nextStats: MigrationStats =
        normalizeChatGptImportStats(response.data);
      setStats(nextStats);
      onImported?.(nextStats);
      setStatus("success");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      try {
        window.dispatchEvent(
          new CustomEvent("cfy:threads:refresh", {
            detail: { kind: "refresh", source: "chatgpt-import" },
          })
        );
      } catch (eventErr) {
        console.warn("[migration] thread refresh event failed", eventErr);
      }
    } catch (err: unknown) {
      console.error("Migration error:", err);
      setStatus("error");
      const normalized = normalizeImportRuntimeError(err, {
        phase: "upload",
      });
      setError(normalized.message);
      setErrorDetail(normalized.technicalDetail || null);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => status !== "uploading" && onOpenChange(false)}
      />

      {/* Modal */}
      <div
        className="relative z-[1201] w-[min(540px,90vw)] rounded-2xl border p-6 flex flex-col gap-4 shadow-xl"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        <div>
          <h2 className="text-lg font-semibold">Import from ChatGPT</h2>
          <p
            className="text-sm mt-1 opacity-70"
            style={{ color: "var(--muted)" }}
          >
            Drop or select a complete OpenAI account export folder. Legacy
            single JSON and modern OpenAI .dat conversation files remain
            supported.
          </p>
        </div>

        <div className="space-y-3">
          <div
            className="rounded-xl border border-dashed p-4 text-sm"
            style={{
              borderColor: isDragOver
                ? "rgba(34, 197, 94, 0.6)"
                : "var(--panel-border)",
              background: isDragOver
                ? "rgba(34, 197, 94, 0.08)"
                : "rgba(255, 255, 255, 0.02)",
            }}
            onDragEnter={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDragOver(true);
            }}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (!isDragOver) setIsDragOver(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsDragOver(false);
            }}
            onDrop={handleFileDrop}
          >
            <input
              ref={fileRef}
              type="file"
              accept={CHATGPT_EXPORT_ACCEPT}
              className="hidden"
              onChange={handleFileSelect}
              disabled={status === "uploading" || accountImportInProgress}
            />
            <input
              ref={folderRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFolderSelect}
              disabled={status === "uploading" || accountImportInProgress}
              {...({ webkitdirectory: "", directory: "" } as React.InputHTMLAttributes<HTMLInputElement>)}
            />
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs opacity-70">
                Drop a conversation JSON, .dat file, or complete export folder
                here. Folder drops start immediately and retain nested paths.
              </div>
              <div className="flex flex-shrink-0 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileRef.current?.click()}
                  disabled={status === "uploading" || accountImportInProgress}
                  className="rounded-full"
                >
                  Choose File
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => folderRef.current?.click()}
                  disabled={status === "uploading" || accountImportInProgress}
                  className="rounded-full"
                >
                  Choose Folder
                </Button>
              </div>
            </div>
            <div className="mt-2 text-xs opacity-70 truncate">
              {accountImport.selectedFileCount > 0
                ? `${accountImport.selectedFileCount} files (${formatFileSize(
                    accountImport.selectedByteCount
                  )})`
                : file
                  ? `${file.name} (${formatFileSize(file.size)})`
                  : "No file selected"}
            </div>
          </div>

          {isLargeImport && (
            <div
              className="rounded-xl border p-3 text-xs"
              style={{
                borderColor: "var(--panel-border)",
                background:
                  "color-mix(in oklab, var(--panel-sheet) 92%, transparent)",
                color: "var(--text)",
              }}
            >
              <div className="font-semibold">Large export detected</div>
              <div className="mt-1 opacity-80">
                Large ChatGPT exports are accepted. Processing may take longer,
                runs in the background, and can resume across sessions or after
                restarts.
              </div>
            </div>
          )}

          {accountImportTransferring && (
            <div
              className="rounded-xl border p-3 text-sm"
              style={{
                borderColor: "rgba(59, 130, 246, 0.35)",
                background: "rgba(59, 130, 246, 0.1)",
              }}
            >
              <div className="font-semibold">
                {accountImport.phase === "preflighting"
                  ? "Checking import runtime..."
                  : "Transferring export..."}
              </div>
              <div className="mt-1 text-xs opacity-80">
                {accountImport.job
                  ? `${accountImport.job.uploaded_file_count} of ${accountImport.job.total_file_count} files staged. `
                  : "Preparing staged intake. "}
                Keep this page open until the server accepts the complete transfer.
              </div>
            </div>
          )}

          {accountImport.phase === "accepted" && accountImport.job && (
            <div
              className="rounded-xl border p-3 text-sm"
              style={{
                borderColor: "rgba(34, 197, 94, 0.35)",
                background: "rgba(34, 197, 94, 0.1)",
              }}
            >
              <div className="font-semibold">Accepted — continuing in background</div>
              <div className="mt-1 text-xs opacity-80">
                Job {accountImport.job.job_id.slice(0, 8)} is queued. You can close
                this window and continue using Codexify.
              </div>
            </div>
          )}

          {accountImport.phase === "running" && accountImport.job && (
            <div
              className="rounded-xl border p-3 text-sm"
              style={{
                borderColor: "rgba(59, 130, 246, 0.35)",
                background: "rgba(59, 130, 246, 0.1)",
              }}
            >
              <div className="font-semibold">Import running in background</div>
              <div className="mt-1 text-xs opacity-80">
                {accountImport.job.imported_thread_count} threads, {" "}
                {accountImport.job.imported_message_count} messages, and {" "}
                {accountImport.job.imported_media_count} images committed so far.
              </div>
            </div>
          )}

          {(accountImport.phase === "completed" ||
            accountImport.phase === "completed_with_warnings") &&
            accountImport.job && (
              <div
                className="rounded-xl border p-3 text-sm"
                style={{
                  borderColor:
                    accountImport.phase === "completed_with_warnings"
                      ? "rgba(245, 158, 11, 0.35)"
                      : "rgba(34, 197, 94, 0.35)",
                  background:
                    accountImport.phase === "completed_with_warnings"
                      ? "rgba(245, 158, 11, 0.1)"
                      : "rgba(34, 197, 94, 0.1)",
                }}
              >
                <div className="font-semibold">
                  {accountImport.phase === "completed_with_warnings"
                    ? "Import completed with warnings"
                    : "Import completed"}
                </div>
                <div className="mt-1 text-xs opacity-80">
                  Imported {accountImport.job.imported_thread_count} threads, {" "}
                  {accountImport.job.imported_message_count} messages, and {" "}
                  {accountImport.job.imported_media_count} images.
                </div>
                <div className="mt-1 text-xs opacity-80">
                  Duplicates: {accountImport.job.duplicate_count}. Skipped: {" "}
                  {accountImport.job.skipped_count}. Warnings: {" "}
                  {accountImport.job.warning_count}.
                </div>
                {accountImport.job.warning_details.length > 0 && (
                  <details className="mt-2 text-[11px] opacity-80">
                    <summary className="cursor-pointer">
                      Review warning details
                    </summary>
                    <ul className="mt-1 space-y-1 pl-4 list-disc">
                      {accountImport.job.warning_details
                        .slice(0, 10)
                        .map((detail, index) => (
                          <li key={`${String(detail.code || "warning")}-${index}`}>
                            {formatJobDetail(detail) || "Import warning"}
                          </li>
                        ))}
                    </ul>
                  </details>
                )}
              </div>
            )}

          {!accountImportActive && status === "uploading" && (
            <div className="text-sm text-center opacity-70 animate-pulse py-3">
              Processing conversations... this may take a moment.
            </div>
          )}

          {status === "success" && stats && (
            <div
              className="text-sm font-medium p-3 rounded-lg border"
              style={{
                background: stats.embedding_coverage_degraded
                  ? "rgba(245, 158, 11, 0.12)"
                  : "rgba(34, 197, 94, 0.1)",
                borderColor: stats.embedding_coverage_degraded
                  ? "rgba(245, 158, 11, 0.35)"
                  : "rgba(34, 197, 94, 0.3)",
                color: stats.embedding_coverage_degraded
                  ? "rgb(253, 186, 116)"
                  : "rgb(134, 239, 172)",
              }}
            >
              <div className="font-semibold mb-1">
                {stats.embedding_coverage_degraded
                  ? "Migration Completed with Partial Embeddings ⚠"
                  : "Migration Successful ✓"}
              </div>
              <div className="text-xs opacity-80">
                Imported {stats.threads_imported} thread
                {stats.threads_imported !== 1 ? "s" : ""} and{" "}
                {stats.messages_imported} message
                {stats.messages_imported !== 1 ? "s" : ""}.
              </div>
              {stats.embedding_coverage_degraded && (
                <div className="mt-2 text-xs opacity-80 space-y-1">
                  <div>
                    Embeddings persisted: {stats.embeddings_persisted} of{" "}
                    {stats.embedding_candidates} candidate
                    {stats.embedding_candidates !== 1 ? "s" : ""}.
                  </div>
                  <div>
                    Embeddings skipped/failed: {stats.embeddings_failed}.
                  </div>
                  <div>
                    Import completed, but retrieval quality may be reduced
                    until embeddings are rebuilt.
                  </div>
                </div>
              )}
            </div>
          )}

          {status === "error" && error && (
            <div
              className="text-sm font-medium p-3 rounded-lg border"
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                borderColor: "rgba(239, 68, 68, 0.3)",
                color: "rgb(252, 165, 165)",
              }}
            >
              <div className="font-semibold mb-1">Migration Failed</div>
              <div className="text-xs opacity-80">{error}</div>
              {errorDetail && (
                <details className="mt-2 text-[11px] opacity-70">
                  <summary className="cursor-pointer">Technical detail</summary>
                  <div className="mt-1 break-words">{errorDetail}</div>
                </details>
              )}
            </div>
          )}

          {accountImport.phase === "failed" && accountImport.error && (
            <div
              className="text-sm font-medium p-3 rounded-lg border"
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                borderColor: "rgba(239, 68, 68, 0.3)",
                color: "rgb(252, 165, 165)",
              }}
            >
              <div className="font-semibold mb-1">Account import failed</div>
              <div className="text-xs opacity-80">{accountImport.error}</div>
              {accountImport.technicalDetail && (
                <details className="mt-2 text-[11px] opacity-70">
                  <summary className="cursor-pointer">Technical detail</summary>
                  <div className="mt-1 break-words">
                    {accountImport.technicalDetail}
                  </div>
                </details>
              )}
              {accountImport.job?.error_details.length ? (
                <details className="mt-2 text-[11px] opacity-70">
                  <summary className="cursor-pointer">
                    Review failure details
                  </summary>
                  <ul className="mt-1 space-y-1 pl-4 list-disc">
                    {accountImport.job.error_details
                      .slice(0, 10)
                      .map((detail, index) => (
                        <li key={`${String(detail.code || "failure")}-${index}`}>
                          {formatJobDetail(detail) || "Import failure"}
                        </li>
                      ))}
                  </ul>
                </details>
              ) : null}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={status === "uploading"}
            className="rounded-full px-4"
          >
            {accountImportActive ? "Close" : "Cancel"}
          </Button>
          {!accountImportActive && (
            <Button
              type="button"
              onClick={handleMigrate}
              disabled={!file || status === "uploading"}
              className="rounded-full px-4"
            >
              {status === "uploading" ? (
                <>
                  <span className="inline-block h-3 w-3 mr-2 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  Importing...
                </>
              ) : (
                "Upload & Migrate"
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatGPTImportModal;
