import React, { useEffect, useState } from "react";
import api from "@/lib/api";

type Diagnostics = { cpu?: number; memory?: number };
type Thread = { id: number; title?: string; updated_at?: string };
type Doc = { id: string; title: string; relation?: string };

export default function WorkspacePane({ threadId }: { threadId: number }) {
  const [thread, setThread] = useState<Thread | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [diagnostics, setDiagnostics] = useState<Diagnostics>({});

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await api.get<{ thread: Thread; documents: Doc[]; diagnostics: Diagnostics }>(
          `/api/workspace/${threadId}`
        );
        if (cancelled) return;
        setThread(res.data.thread);
        setDocuments(res.data.documents || []);
        setDiagnostics(res.data.diagnostics || {});
      } catch (e) {
        // Non-fatal for UI; leave defaults
        console.warn("WorkspacePane fetch failed", e);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [threadId]);

  return (
    <div className="p-3 text-sm">
      <div className="mb-2 font-semibold">Workspace</div>
      <div className="mb-3 opacity-70">
        {thread ? (
          <>
            <div>Thread: {thread.title || `#${thread.id}`}</div>
            {thread.updated_at && <div>Updated: {new Date(thread.updated_at).toLocaleString()}</div>}
          </>
        ) : (
          <div>Loading…</div>
        )}
      </div>
      <div className="mb-3">
        <div className="mb-1 text-xs uppercase opacity-60">Documents</div>
        {documents.length === 0 ? (
          <div className="opacity-70">No linked docs</div>
        ) : (
          <ul className="list-disc pl-5">
            {documents.map((d) => (
              <li key={d.id}>{d.title}</li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <div className="mb-1 text-xs uppercase opacity-60">Diagnostics</div>
        <div className="opacity-80">CPU: {diagnostics.cpu ?? 0}% · Mem: {diagnostics.memory ?? 0}%</div>
      </div>
    </div>
  );
}

