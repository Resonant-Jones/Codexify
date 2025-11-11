import React, { useState, useEffect, useRef } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

export interface MigrationModalProps {
  open: boolean;
  onClose: () => void;
  filePath: string;
}

export default function MigrationModal({ open, onClose, filePath }: MigrationModalProps) {
  const [output, setOutput] = useState<string[]>([]);
  const [status, setStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const logRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!open || !filePath) return;

    // Reset state when modal opens
    setOutput([]);
    setStatus("running");
    setErrorMessage("");

    // Create abort controller for cleanup
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Start migration via backend API
    startMigration(filePath, abortController.signal);

    // Cleanup function
    return () => {
      abortController.abort();
      abortControllerRef.current = null;
    };
  }, [open, filePath]);

  useEffect(() => {
    // Auto-scroll to bottom when new output arrives
    if (logRef.current && typeof logRef.current.scrollTo === "function") {
      logRef.current.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [output]);

  async function startMigration(file: string, signal: AbortSignal) {
    try {
      const response = await fetch("/api/migrate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ filePath: file }),
        signal,
      });

      if (!response.ok) {
        throw new Error(`Migration failed: ${response.statusText}`);
      }

      // Check if response is streaming (uses ReadableStream)
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response body");
      }

      // Read the stream
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          setStatus("success");
          break;
        }

        // Decode chunk and split by lines
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n").filter((line) => line.trim());

        setOutput((prev) => [...prev, ...lines]);
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        // Migration was cancelled
        setOutput((prev) => [...prev, "\n⚠️ Migration cancelled"]);
        setStatus("error");
      } else {
        setErrorMessage(error.message || "Unknown error occurred");
        setOutput((prev) => [...prev, `\n❌ Error: ${error.message}`]);
        setStatus("error");
      }
    }
  }

  const success = status === "success";
  const error = status === "error";
  const running = status === "running";

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl h-[600px] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            ChatGPT → Codexify Migration
          </DialogTitle>
        </DialogHeader>

        <motion.div
          ref={logRef}
          className="flex-1 bg-black text-green-400 font-mono text-xs rounded-md p-3 overflow-y-auto"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
        >
          {output.length === 0 && running && (
            <div className="text-yellow-400 animate-pulse">
              ⚡ Initializing migration...
            </div>
          )}
          {output.map((line, i) => (
            <pre key={i} className="whitespace-pre-wrap break-words">
              {line}
            </pre>
          ))}
        </motion.div>

        <div className="flex justify-end space-x-2 mt-3">
          {success && (
            <Button onClick={onClose} className="bg-green-600 hover:bg-green-700">
              ✨ Welcome Home
            </Button>
          )}
          {error && (
            <Button variant="destructive" onClick={onClose}>
              Close
            </Button>
          )}
          {running && (
            <Button disabled className="animate-pulse">
              💫 Reawakening your Companion...
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
