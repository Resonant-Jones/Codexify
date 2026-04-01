/**
 * Memory Browser - RAG Trace Inspector
 *
 * Diagnostic panel for inspecting the last assembled RAG context.
 * Displays semantic retrieval results, memory recall, metadata, scores, and depth mode.
 *
 * This is Codexify's Cognitive Map Viewer - it shows:
 * - Why the system retrieved what it did
 * - What evidence the model saw
 * - How strong the matches were
 * - From which silo (semantic vs memory)
 *
 * Token-compliant, follows Rendering Protocol and Glass layering rules.
 */

import React from "react";
import { fetchLatestRagTrace } from "@/lib/api";
import { useContextTrace } from "@/state/contextTrace";

type MemoryBrowserItem = {
  text: string;
  score?: number;
  metadata?: Record<string, unknown>;
};

type MemoryBrowserProps = {
  activeThreadId: number | null;
};

function normalizeTracePayload(payload: Record<string, unknown> | null): {
  semantic: MemoryBrowserItem[];
  memory: MemoryBrowserItem[];
} {
  const documents = Array.isArray(payload?.documents) ? payload.documents : [];
  const graph = Array.isArray(payload?.graph)
    ? payload.graph
    : Array.isArray(payload?.memory)
    ? payload.memory
    : [];

  const semantic = documents
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      text: String(item.snippet ?? item.text ?? "(empty)"),
      score:
        typeof item.score === "number" && Number.isFinite(item.score)
          ? item.score
          : undefined,
      metadata:
        item.title != null || item.id != null
          ? {
              id: item.id,
              title: item.title,
            }
          : undefined,
    }));

  const memory = graph
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      text: String(item.text ?? item.snippet ?? "(empty)"),
      score:
        typeof item.score === "number" && Number.isFinite(item.score)
          ? item.score
          : undefined,
      metadata:
        item.kind != null || item.node_id != null || item.origin != null
          ? {
              kind: item.kind,
              node_id: item.node_id,
              origin: item.origin,
            }
          : undefined,
    }));

  return { semantic, memory };
}

export default function MemoryBrowser({
  activeThreadId,
}: MemoryBrowserProps) {
  const {
    lastDepth = "normal",
    lastThreadId = null,
    lastTimestamp = null,
  } = useContextTrace() as any;
  const [traceState, setTraceState] = React.useState<{
    error: string | null;
    loading: boolean;
    memory: MemoryBrowserItem[];
    semantic: MemoryBrowserItem[];
  }>({
    error: null,
    loading: false,
    memory: [],
    semantic: [],
  });

  React.useEffect(() => {
    let cancelled = false;

    if (activeThreadId == null) {
      setTraceState({
        error: null,
        loading: false,
        memory: [],
        semantic: [],
      });
      return () => {
        cancelled = true;
      };
    }

    setTraceState({
      error: null,
      loading: true,
      memory: [],
      semantic: [],
    });

    void fetchLatestRagTrace(activeThreadId)
      .then((payload) => {
        if (cancelled) return;
        setTraceState({
          error: null,
          loading: false,
          ...normalizeTracePayload(payload),
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (
          Number((error as { response?: { status?: number } })?.response?.status ?? 0) ===
          404
        ) {
          setTraceState({
            error: null,
            loading: false,
            memory: [],
            semantic: [],
          });
          return;
        }

        setTraceState({
          error:
            error instanceof Error ? error.message : "Failed to load RAG trace",
          loading: false,
          memory: [],
          semantic: [],
        });
      });

    return () => {
      cancelled = true;
    };
  }, [activeThreadId]);

  const displayThreadId = activeThreadId ?? lastThreadId ?? null;
  const displayDepth =
    activeThreadId != null && lastThreadId === activeThreadId
      ? lastDepth
      : "normal";
  const displayTimestamp =
    activeThreadId != null && lastThreadId === activeThreadId
      ? lastTimestamp
      : null;
  const { semantic, memory, loading, error } = traceState;

  const hasData = semantic.length > 0 || memory.length > 0;

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
          Memory Browser
        </h2>
        <p className="text-sm opacity-80" style={{ color: "var(--muted)" }}>
          Inspect the context Codexify retrieved during the last completion.
        </p>
      </div>

      {/* Metadata Card */}
      <div
        className="rounded-[var(--radius)] p-[var(--card-pad)]"
        style={{
          background: "var(--chip-bg)",
          border: "1px solid var(--panel-border)",
        }}
      >
        <div className="text-sm opacity-70" style={{ color: "var(--muted)" }}>
          <strong>Depth:</strong> {displayDepth}
          {" • "}
          <strong>Thread:</strong> {displayThreadId || "n/a"}
          {displayTimestamp && (
            <>
              {" • "}
              <strong>Time:</strong> {new Date(displayTimestamp).toLocaleString()}
            </>
          )}
        </div>
      </div>

      {loading && (
        <div
          className="rounded-[var(--radius)] p-[var(--card-pad)] text-center"
          style={{
            background: "var(--panel-bg)",
            border: "1px solid var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <p className="text-sm opacity-70">Loading RAG trace for this thread…</p>
        </div>
      )}

      {error && !loading && (
        <div
          className="rounded-[var(--radius)] p-[var(--card-pad)] text-center"
          style={{
            background: "var(--panel-bg)",
            border: "1px solid var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <p className="text-sm opacity-70">{error}</p>
        </div>
      )}

      {!hasData && !loading && !error && (
        <div
          className="rounded-[var(--radius)] p-[var(--card-pad)] text-center"
          style={{
            background: "var(--panel-bg)",
            border: "1px solid var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <p className="text-sm opacity-70">
            {activeThreadId == null
              ? 'Select a thread to inspect retrieved context.'
              : 'No RAG trace available yet for this thread. Send a message with depth "normal", "deep", or "diagnostic" to see retrieved context here.'}
          </p>
        </div>
      )}

      {/* Semantic Snippets Section */}
      {semantic.length > 0 && (
        <section>
          <h3 className="text-base font-medium mb-3" style={{ color: "var(--text)" }}>
            Semantic Snippets
            <span className="ml-2 text-xs opacity-60">({semantic.length} results)</span>
          </h3>
          <div className="flex flex-col gap-3">
            {semantic.map((item, i) => (
              <div
                key={i}
                className="rounded-[var(--radius)] p-[var(--card-pad)]"
                style={{
                  background: "var(--panel-bg)",
                  border: "1px solid var(--panel-border)",
                }}
              >
                <div className="text-sm mb-2" style={{ color: "var(--text)" }}>
                  {item.text || "(empty)"}
                </div>
                <div className="flex items-center gap-3 text-xs opacity-70" style={{ color: "var(--muted)" }}>
                  {item.score !== undefined && (
                    <span>
                      <strong>Score:</strong> {item.score.toFixed(3)}
                    </span>
                  )}
                  {item.metadata && Object.keys(item.metadata).length > 0 && (
                    <span>
                      <strong>Metadata:</strong> {JSON.stringify(item.metadata).slice(0, 60)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Memory Recall Section */}
      {memory.length > 0 && (
        <section>
          <h3 className="text-base font-medium mb-3" style={{ color: "var(--text)" }}>
            Memory Recall
            <span className="ml-2 text-xs opacity-60">({memory.length} results)</span>
          </h3>
          <div className="flex flex-col gap-3">
            {memory.map((item, i) => (
              <div
                key={i}
                className="rounded-[var(--radius)] p-[var(--card-pad)]"
                style={{
                  background: "var(--panel-bg)",
                  border: "1px solid var(--panel-border)",
                }}
              >
                <div className="text-sm mb-2" style={{ color: "var(--text)" }}>
                  {item.text || "(empty)"}
                </div>
                <div className="flex items-center gap-3 text-xs opacity-70" style={{ color: "var(--muted)" }}>
                  {item.score !== undefined && (
                    <span>
                      <strong>Score:</strong> {item.score.toFixed(3)}
                    </span>
                  )}
                  {item.metadata && Object.keys(item.metadata).length > 0 && (
                    <span>
                      <strong>Metadata:</strong> {JSON.stringify(item.metadata).slice(0, 60)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
