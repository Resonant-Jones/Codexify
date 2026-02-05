/**
 * RagTracePanel – Display RAG trace for debugging
 *
 * Shows retrieved documents and graph nodes used during completion.
 * Useful for understanding context retrieval and model behavior.
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { useRagTrace } from "@/hooks/useRagTrace";
import { RagDocument, RagGraphNode } from "@/types/rag";

interface RagTracePanelProps {
  threadId: number | null;
}

export function RagTracePanel({ threadId }: RagTracePanelProps) {
  const { trace, loading, error, fetchTrace } = useRagTrace(threadId);
  const [autoFetched, setAutoFetched] = useState(false);

  // Auto-fetch trace when threadId changes
  useEffect(() => {
    if (threadId && !autoFetched) {
      fetchTrace();
      setAutoFetched(true);
    }
  }, [threadId, autoFetched, fetchTrace]);

  if (!threadId) {
    return (
      <div
        className="rounded-lg border p-4 text-center text-sm"
        style={{
          borderColor: "var(--panel-border)",
          backgroundColor: "var(--panel-bg)",
          color: "var(--muted)",
        }}
      >
        Select a thread to view its RAG trace.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h3
            className="text-sm font-semibold"
            style={{ color: "var(--text)" }}
          >
            RAG Trace
          </h3>
          <p
            className="text-xs"
            style={{ color: "var(--muted)", opacity: 0.75 }}
          >
            Dev-only: stored in memory and cleared on restart.
          </p>
        </div>
        <button
          onClick={() => {
            setAutoFetched(false);
            fetchTrace();
          }}
          disabled={loading}
          className="p-1 rounded hover:opacity-70 disabled:opacity-50 transition"
          title="Refresh trace"
          style={{ color: "var(--muted)" }}
        >
          <RefreshCw
            size={14}
            className={loading ? "animate-spin" : ""}
          />
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="space-y-3">
          <div
            className="h-4 rounded animate-pulse w-32"
            style={{ backgroundColor: "var(--panel-border)" }}
          />
          <div className="space-y-2">
            <div
              className="h-3 rounded animate-pulse"
              style={{ backgroundColor: "var(--panel-border)" }}
            />
            <div
              className="h-3 rounded animate-pulse w-5/6"
              style={{ backgroundColor: "var(--panel-border)" }}
            />
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div
          className="p-3 rounded-lg flex gap-2"
          style={{
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            borderColor: "rgba(239, 68, 68, 0.3)",
            border: "1px solid",
          }}
        >
          <AlertCircle
            size={16}
            className="flex-shrink-0 mt-0.5"
            style={{ color: "rgb(252, 165, 165)" }}
          />
          <div className="text-sm" style={{ color: "rgb(252, 165, 165)" }}>
            {error}
          </div>
        </div>
      )}

      {/* No Trace State */}
      {!trace && !error && !loading && (
        <div className="text-center py-4">
          <p
            className="text-sm"
            style={{ color: "var(--muted)" }}
          >
            No RAG trace yet for this thread.
          </p>
          <p
            className="text-xs mt-1"
            style={{ color: "var(--muted)", opacity: 0.7 }}
          >
            Run a completion to generate a trace.
          </p>
        </div>
      )}

      {/* Documents Section */}
      {trace && trace.documents && trace.documents.length > 0 && (
        <div>
          <h4
            className="text-xs font-semibold mb-2 uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            Documents ({trace.documents.length})
          </h4>
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
          <h4
            className="text-xs font-semibold mb-2 uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            Graph Nodes ({trace.graph.length})
          </h4>
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
          <div className="text-center py-4">
            <p
              className="text-sm"
              style={{ color: "var(--muted)" }}
            >
              No documents or graph nodes retrieved.
            </p>
          </div>
        )}
    </div>
  );
}

function DocumentCard({ doc }: { doc: RagDocument }) {
  return (
    <div
      className="p-3 border rounded-lg transition"
      style={{
        borderColor: "var(--panel-border)",
        backgroundColor: "var(--panel-bg)",
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <h5
            className="text-xs font-medium truncate"
            style={{ color: "var(--text)" }}
          >
            {doc.title}
          </h5>
        </div>
        {doc.score !== undefined && (
          <div
            className="text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0"
            style={{
              backgroundColor: "rgba(59, 130, 246, 0.2)",
              color: "rgb(59, 130, 246)",
            }}
          >
            {(doc.score * 100).toFixed(0)}%
          </div>
        )}
      </div>
      {doc.snippet && (
        <p
          className="text-xs line-clamp-2"
          style={{ color: "var(--muted)" }}
        >
          {doc.snippet}
        </p>
      )}
    </div>
  );
}

function GraphNodeCard({ node }: { node: RagGraphNode }) {
  return (
    <div
      className="p-3 border rounded-lg transition"
      style={{
        borderColor: "var(--panel-border)",
        backgroundColor: "var(--panel-bg)",
      }}
    >
      <div className="flex items-start gap-2 mb-2">
        <div
          className="text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0"
          style={{
            backgroundColor: "rgba(168, 85, 247, 0.2)",
            color: "rgb(168, 85, 247)",
          }}
        >
          {node.kind}
        </div>
      </div>
      {node.text && (
        <p
          className="text-xs line-clamp-3"
          style={{ color: "var(--muted)" }}
        >
          {node.text}
        </p>
      )}
    </div>
  );
}

export default RagTracePanel;
