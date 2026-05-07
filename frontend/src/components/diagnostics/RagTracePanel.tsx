/**
 * RagTracePanel – Display RAG trace for debugging
 *
 * Shows retrieved documents and graph nodes used during completion.
 * Useful for understanding context retrieval and model behavior.
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { useRagTrace } from "@/hooks/useRagTrace";
import {
  RagDocument,
  RagGraphNode,
  RagSuppressionItem,
  RagSuppressionSummary,
} from "@/types/rag";

interface RagTracePanelProps {
  threadId: number | null;
}

function formatTraceValue(value: unknown): string | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : null;
  }
  if (Array.isArray(value)) {
    const parts = value
      .map(formatTraceValue)
      .filter((part): part is string => Boolean(part));
    return parts.length ? parts.join(", ") : null;
  }
  return String(value);
}

function metadataChip({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  const formatted = formatTraceValue(value);
  if (!formatted) return null;
  return (
    <span
      className="rounded-full border px-2 py-1 text-xs"
      style={{
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
      }}
    >
      {label}: {formatted}
    </span>
  );
}

function suppressionSummaryLabel(summary: RagSuppressionSummary | null): string | null {
  if (!summary) return null;
  if (typeof summary.count === "number" && summary.count > 0) {
    return `${summary.count} suppressed`;
  }
  const count = summary.items?.length ?? 0;
  return count > 0 ? `${count} suppressed` : null;
}

export function RagTracePanel({ threadId }: RagTracePanelProps) {
  const { trace, loading, error, fetchTrace } = useRagTrace(threadId);
  const [autoFetched, setAutoFetched] = useState(false);
  const retrievalPolicy = trace?.retrieval_policy ?? null;
  const retrievalProvenance = trace?.retrieval_provenance ?? null;
  const suppressionSummary = trace?.retrieval_suppression ?? null;
  const hasSuppression =
    Boolean(suppressionSummary?.items?.length) ||
    Boolean(
      suppressionSummary?.counts_by_reason &&
        Object.keys(suppressionSummary.counts_by_reason).length > 0
    );
  const hasVisibleContent =
    Boolean(trace?.documents?.length) ||
    Boolean(trace?.graph?.length) ||
    hasSuppression;

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
      {retrievalPolicy && (
        <div>
          <h4
            className="text-xs font-semibold mb-2 uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            Retrieval Policy
          </h4>
          <div className="flex flex-wrap gap-2">
            {metadataChip({
              label: "Source mode",
              value: retrievalPolicy.source_mode,
            })}
            {metadataChip({
              label: "Boundary",
              value: retrievalPolicy.boundary_label,
            })}
            {metadataChip({
              label: "Thread docs",
              value: retrievalPolicy.allow_thread_docs,
            })}
            {metadataChip({
              label: "Project docs",
              value: retrievalPolicy.allow_project_docs,
            })}
            {metadataChip({
              label: "Semantic widening",
              value: retrievalPolicy.allow_semantic_widening,
            })}
            {metadataChip({
              label: "Global widening",
              value: retrievalPolicy.allow_global_widening,
            })}
          </div>
        </div>
      )}

      {retrievalProvenance && (
        <div>
          <h4
            className="text-xs font-semibold mb-2 uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            Retrieval Provenance
          </h4>
          <div className="flex flex-wrap gap-2">
            {metadataChip({
              label: "Requested",
              value: retrievalProvenance.requested_source_mode,
            })}
            {metadataChip({
              label: "Normalized",
              value: retrievalProvenance.normalized_source_mode,
            })}
            {metadataChip({
              label: "Status",
              value: retrievalProvenance.retrieval_status,
            })}
          </div>
        </div>
      )}

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

      {hasSuppression && suppressionSummary && (
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h4
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: "var(--muted)" }}
            >
              Suppressed Context
            </h4>
            <span
              className="rounded-full border px-2 py-1 text-xs"
              style={{
                borderColor: "var(--panel-border)",
                color: "var(--muted)",
              }}
            >
              {suppressionSummaryLabel(suppressionSummary)}
            </span>
          </div>
          <div className="flex flex-wrap gap-2 mb-3">
            {Object.entries(suppressionSummary.counts_by_reason || {}).map(
              ([reason, count]) => (
                <span
                  key={reason}
                  className="rounded-full border px-2 py-1 text-xs"
                  style={{
                    borderColor: "var(--panel-border)",
                    color: "var(--muted)",
                  }}
                >
                  {reason}: {count}
                </span>
              )
            )}
          </div>
          <div className="space-y-2">
            {(suppressionSummary.items || []).map((item) => (
              <SuppressedItemCard key={`${item.id ?? item.suppression_reason ?? "suppressed"}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Empty Trace */}
      {trace && !hasVisibleContent && (
          <div className="text-center py-4">
            <p
              className="text-sm"
              style={{ color: "var(--muted)" }}
            >
              No documents, graph nodes, or suppressed context recorded.
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
      <div className="flex flex-wrap gap-2 mb-2">
        {metadataChip({ label: "Source type", value: doc.source_type })}
        {metadataChip({ label: "Role", value: doc.role })}
        {metadataChip({ label: "Lane", value: doc.retrieval_lane })}
        {metadataChip({ label: "Thread", value: doc.thread_id })}
        {metadataChip({ label: "Project", value: doc.project_id })}
        {metadataChip({ label: "Policy", value: doc.policy_reason })}
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

function SuppressedItemCard({ item }: { item: RagSuppressionItem }) {
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
            {item.id || item.suppression_reason || "suppressed item"}
          </h5>
        </div>
        {item.suppression_reason && (
          <div
            className="text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.15)",
              color: "rgb(239, 68, 68)",
            }}
          >
            {item.suppression_reason}
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {metadataChip({ label: "Source type", value: item.source_type })}
        {metadataChip({ label: "Role", value: item.role })}
        {metadataChip({ label: "Lane", value: item.retrieval_lane })}
        {metadataChip({ label: "Thread", value: item.thread_id })}
        {metadataChip({ label: "Project", value: item.project_id })}
        {metadataChip({ label: "Policy", value: item.policy_reason })}
      </div>
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
