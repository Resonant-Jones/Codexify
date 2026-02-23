/**
 * ChatGPTImportModal – Import ChatGPT export JSON file
 *
 * Handles file selection and upload to the migration endpoint.
 * Displays loading, success, and error states.
 */

import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";

interface ChatGPTImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userName?: string;
  onImported?: (stats: MigrationStats) => void;
}

export interface MigrationStats {
  threads_imported: number;
  messages_imported: number;
  projects_created?: number;
  projects_reused?: number;
  messages_filtered?: number;
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
  const fileRef = useRef<HTMLInputElement | null>(null);

  const setSelectedFile = (nextFile: File | null) => {
    setFile(nextFile);
    setStatus("idle");
    setError(null);
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

    setStatus("uploading");
    setError(null);

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

      const nextStats: MigrationStats = {
        threads_imported: Number(response.data?.threads_imported ?? 0),
        messages_imported: Number(response.data?.messages_imported ?? 0),
        projects_created: Number(response.data?.projects_created ?? 0),
        projects_reused: Number(response.data?.projects_reused ?? 0),
        messages_filtered: Number(response.data?.messages_filtered ?? 0),
      };
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
      const detail =
        err?.response?.data?.detail ??
        err?.response?.data?.error ??
        err?.message;
      setError(detail || "Failed to migrate data");
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
                background: "rgba(34, 197, 94, 0.1)",
                borderColor: "rgba(34, 197, 94, 0.3)",
                color: "rgb(134, 239, 172)",
              }}
            >
              <div className="font-semibold mb-1">Migration Successful ✓</div>
              <div className="text-xs opacity-80">
                Imported {stats.threads_imported} thread
                {stats.threads_imported !== 1 ? "s" : ""} and{" "}
                {stats.messages_imported} message
                {stats.messages_imported !== 1 ? "s" : ""}.
              </div>
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
