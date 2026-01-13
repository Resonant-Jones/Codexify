/**
 * ChatGPTImportModal – Import ChatGPT export JSON file
 *
 * Handles file selection and upload to the migration endpoint.
 * Displays loading, success, and error states.
 */

import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";

interface ChatGPTImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userName?: string;
}

interface MigrationResponse {
  threads_imported: number;
  messages_imported: number;
}

export function ChatGPTImportModal({
  open,
  onOpenChange,
  userName = "user",
}: ChatGPTImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [stats, setStats] = useState<MigrationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f && f.name.endsWith(".json")) {
      setFile(f);
      setStatus("idle");
      setError(null);
      setStats(null);
    } else {
      setError("Please select a valid .json file");
    }
  };

  const handleMigrate = async () => {
    if (!file) return;

    setStatus("uploading");
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/upload-chatgpt-export", {
        method: "POST",
        headers: {
          "X-User-Id": userName,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.details || data.error || "Migration failed"
        );
      }

      setStats({
        threads_imported: data.threads_imported,
        messages_imported: data.messages_imported,
      });
      setStatus("success");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err: any) {
      console.error("Migration error:", err);
      setStatus("error");
      setError(err.message || "Failed to migrate data");
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
            Upload your ChatGPT export JSON file to import your conversation
            history.
          </p>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFileSelect}
              disabled={status === "uploading"}
            />
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
            <span className="text-xs opacity-70 truncate max-w-xs">
              {file ? file.name : "No file selected"}
            </span>
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
