import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { fetchLatestRagTrace } from "@/lib/api";
import { RagDocument, RagGraphNode } from "@/types/rag";

interface RAGTracePanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threadId: number | null;
}

/**
 * RAG Trace debug panel
 *
 * Displays retrieved documents and graph nodes used during completion,
 * useful for debugging context retrieval and understanding model behavior.
 */
export default function RAGTracePanel({
  open,
  onOpenChange,
  threadId,
}: RAGTracePanelProps) {
  const [trace, setTrace] = useState<{
    documents: RagDocument[];
    graph: RagGraphNode[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const fetchTrace = useCallback(async () => {
    if (threadId == null) {
      requestIdRef.current += 1;
      setTrace(null);
      setLoading(false);
      setError(null);
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setTrace(null);
    setLoading(true);
    setError(null);

    try {
      const payload = await fetchLatestRagTrace(threadId);
      if (requestId !== requestIdRef.current) {
        return;
      }

      const documents = Array.isArray((payload as { documents?: unknown[] }).documents)
        ? ((payload as { documents: unknown[] }).documents.filter(
            (value): value is RagDocument =>
              Boolean(value) && typeof value === "object"
          ) as RagDocument[])
        : [];
      const graph = Array.isArray((payload as { graph?: unknown[] }).graph)
        ? ((payload as { graph: unknown[] }).graph.filter(
            (value): value is RagGraphNode =>
              Boolean(value) && typeof value === "object"
          ) as RagGraphNode[])
        : [];

      setTrace({ documents, graph });
      setLoading(false);
      setError(null);
    } catch (err) {
      if (requestId !== requestIdRef.current) {
        return;
      }

      if (Number((err as { response?: { status?: number } })?.response?.status ?? 0) === 404) {
        setTrace(null);
        setLoading(false);
        setError(null);
        return;
      }

      setTrace(null);
      setLoading(false);
      setError(
        err instanceof Error ? err.message : "Failed to load RAG trace"
      );
    }
  }, [threadId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    void fetchTrace();
  }, [fetchTrace, open]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-96 overflow-y-auto">
        <SheetHeader className="mb-4">
          <SheetTitle className="flex items-center justify-between">
            <span>RAG Trace Debug</span>
            <button
              onClick={() => {
                void fetchTrace();
              }}
              disabled={loading}
              className="icon-inline h-8 w-8 p-0 disabled:opacity-50"
              title="Refresh trace"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </SheetTitle>
        </SheetHeader>

        <div className="space-y-6">
          {/* Loading State */}
          {loading && (
            <div className="space-y-3">
              <div
                className="h-4 w-32 animate-pulse rounded"
                style={{ background: "var(--surface-hover)" }}
              />
              <div className="space-y-2">
                <div
                  className="h-3 animate-pulse rounded"
                  style={{ background: "var(--surface-hover)" }}
                />
                <div
                  className="h-3 w-5/6 animate-pulse rounded"
                  style={{ background: "var(--surface-hover)" }}
                />
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div
              className="flex gap-2 rounded-lg border p-3"
              style={{
                background: "var(--danger-surface)",
                borderColor: "var(--danger-border)",
                color: "var(--danger-text)",
              }}
            >
              <AlertCircle
                size={16}
                className="mt-0.5 shrink-0"
                style={{ color: "var(--danger-text)" }}
              />
              <div className="text-sm">{error}</div>
            </div>
          )}

          {/* No Trace State */}
          {!trace && !error && !loading && (
            <div className="text-center py-8">
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                No RAG trace yet for this thread.
              </p>
              <p
                className="mt-1 text-xs"
                style={{ color: "var(--text-subtle)" }}
              >
                Run a completion to generate a trace.
              </p>
            </div>
          )}

          {/* Documents Section */}
          {trace && trace.documents && trace.documents.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-3">Documents</h3>
              <div className="space-y-2">
                {trace.documents.map((doc: RagDocument) => (
                  <DocumentCard key={doc.id} doc={doc} />
                ))}
              </div>
            </div>
          )}

          {/* Graph Section */}
          {trace && trace.graph && trace.graph.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-3">Graph Nodes</h3>
              <div className="space-y-2">
                {trace.graph.map((node: RagGraphNode) => (
                  <GraphNodeCard key={node.node_id} node={node} />
                ))}
              </div>
            </div>
          )}

          {/* Empty Trace */}
          {trace &&
            trace.documents &&
            trace.documents.length === 0 &&
            trace.graph &&
            trace.graph.length === 0 && (
              <div className="text-center py-8">
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  No documents or graph nodes retrieved.
                </p>
              </div>
            )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function DocumentCard({ doc }: { doc: RagDocument }) {
  return (
    <div
      className="rounded-lg border p-3 transition"
      style={{
        borderColor: "var(--panel-border)",
        backgroundColor: "var(--panel-sheet, var(--panel-bg))",
        color: "var(--text)",
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <h4 className="truncate text-sm font-medium">{doc.title}</h4>
        </div>
        {doc.score !== undefined && (
          <div
            className="shrink-0 rounded-full px-2 py-1 text-xs font-semibold"
            style={{
              background: "var(--info-surface)",
              color: "var(--info-text)",
            }}
          >
            {(doc.score * 100).toFixed(0)}%
          </div>
        )}
      </div>
      {doc.snippet && (
        <p className="line-clamp-2 text-xs" style={{ color: "var(--muted)" }}>
          {doc.snippet}
        </p>
      )}
    </div>
  );
}

function GraphNodeCard({ node }: { node: RagGraphNode }) {
  return (
    <div
      className="rounded-lg border p-3 transition"
      style={{
        borderColor: "var(--panel-border)",
        backgroundColor: "var(--panel-sheet, var(--panel-bg))",
        color: "var(--text)",
      }}
    >
      <div className="flex items-start gap-2 mb-2">
        <div
          className="shrink-0 rounded-full px-2 py-1 text-xs font-semibold"
          style={{
            background: "var(--tag-surface)",
            color: "var(--tag-text)",
          }}
        >
          {node.kind}
        </div>
      </div>
      {node.text && (
        <p className="line-clamp-3 text-xs" style={{ color: "var(--muted)" }}>
          {node.text}
        </p>
      )}
    </div>
  );
}
