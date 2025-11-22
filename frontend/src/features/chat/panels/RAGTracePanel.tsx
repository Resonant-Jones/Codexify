import { useState, useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useRAGTrace } from "../hooks/useRAGTrace";
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
  const { trace, loading, error, fetchTrace } = useRAGTrace(threadId);
  const [autoFetched, setAutoFetched] = useState(false);

  // Auto-fetch trace when panel opens
  useEffect(() => {
    if (open && threadId && !autoFetched) {
      fetchTrace();
      setAutoFetched(true);
    }
  }, [open, threadId, autoFetched, fetchTrace]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-96 overflow-y-auto">
        <SheetHeader className="mb-4">
          <SheetTitle className="flex items-center justify-between">
            <span>RAG Trace Debug</span>
            <button
              onClick={() => fetchTrace()}
              disabled={loading}
              className="p-1 rounded hover:bg-black/10 disabled:opacity-50 transition"
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
              <div className="h-4 bg-gray-300 rounded animate-pulse w-32" />
              <div className="space-y-2">
                <div className="h-3 bg-gray-300 rounded animate-pulse" />
                <div className="h-3 bg-gray-300 rounded animate-pulse w-5/6" />
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex gap-2">
              <AlertCircle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          {/* No Trace State */}
          {!trace && !error && !loading && (
            <div className="text-center py-8">
              <p className="text-sm text-gray-500">
                No RAG trace yet for this thread.
              </p>
              <p className="text-xs text-gray-400 mt-1">
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
                <p className="text-sm text-gray-500">No documents or graph nodes retrieved.</p>
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
      className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
      style={{
        borderColor: "var(--panel-border, #e5e7eb)",
        backgroundColor: "var(--panel-bg, #f9fafb)",
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium truncate text-gray-900">
            {doc.title}
          </h4>
        </div>
        {doc.score !== undefined && (
          <div className="text-xs font-semibold px-2 py-1 rounded-full bg-blue-100 text-blue-700 flex-shrink-0">
            {(doc.score * 100).toFixed(0)}%
          </div>
        )}
      </div>
      {doc.snippet && (
        <p className="text-xs text-gray-600 line-clamp-2">{doc.snippet}</p>
      )}
    </div>
  );
}

function GraphNodeCard({ node }: { node: RagGraphNode }) {
  return (
    <div
      className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
      style={{
        borderColor: "var(--panel-border, #e5e7eb)",
        backgroundColor: "var(--panel-bg, #f9fafb)",
      }}
    >
      <div className="flex items-start gap-2 mb-2">
        <div className="text-xs font-semibold px-2 py-1 rounded-full bg-purple-100 text-purple-700 flex-shrink-0">
          {node.kind}
        </div>
      </div>
      {node.text && (
        <p className="text-xs text-gray-600 line-clamp-3">{node.text}</p>
      )}
    </div>
  );
}
