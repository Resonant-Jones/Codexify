/**
 * ChatGPTImportModal – Import ChatGPT export JSON file
 *
 * Handles file selection and upload to the migration endpoint.
 * Displays loading, success, and error states.
 */

import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import api, {
  normalizeChatGptImportStats,
  normalizeImportRuntimeError,
  preflightBackendAvailability,
  type ChatGptImportStats,
} from "@/lib/api";

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

export function ChatGPTImportModal({
  open,
  onOpenChange,
  userName = "user",
  onImported,
}: ChatGPTImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [status, setStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [stats, setStats] = useState<MigrationStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const setSelectedFile = (nextFile: File | null) => {
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

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    if (!dropped) {
      return;
    }
    setSelectedFile(dropped);
  };

  const handleMigrate = async () => {
    if (!file) return;

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
    } catch (err: any) {
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
            Upload or drop a file. The backend validates content and imports
            only supported ChatGPT export JSON.
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
              className="hidden"
              onChange={handleFileSelect}
              disabled={status === "uploading"}
            />
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs opacity-70">
                Drag and drop any file here, or choose one manually.
                Validation is based on file content.
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileRef.current?.click()}
                disabled={status === "uploading"}
                className="rounded-full"
              >
                Choose File
              </Button>
            </div>
            <div className="mt-2 text-xs opacity-70 truncate">
              {file ? `${file.name} (${Math.ceil(file.size / 1024)} KB)` : "No file selected"}
            </div>
          </div>

          {status === "uploading" && (
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
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={status === "uploading"}
            className="rounded-full px-4"
          >
            Cancel
          </Button>
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
        </div>
      </div>
    </div>
  );
}

export default ChatGPTImportModal;
