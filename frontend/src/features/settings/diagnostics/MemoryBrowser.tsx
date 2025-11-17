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
import { useContextTrace } from "@/state/contextTrace";

export default function MemoryBrowser() {
  const {
    lastSemantic = [],
    lastMemory = [],
    lastDepth = "normal",
    lastThreadId = null,
    lastTimestamp = null,
  } = useContextTrace() as any;

  const hasData = lastSemantic.length > 0 || lastMemory.length > 0;

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
          <strong>Depth:</strong> {lastDepth}
          {" • "}
          <strong>Thread:</strong> {lastThreadId || "n/a"}
          {lastTimestamp && (
            <>
              {" • "}
              <strong>Time:</strong> {new Date(lastTimestamp).toLocaleString()}
            </>
          )}
        </div>
      </div>

      {!hasData && (
        <div
          className="rounded-[var(--radius)] p-[var(--card-pad)] text-center"
          style={{
            background: "var(--panel-bg)",
            border: "1px solid var(--panel-border)",
            color: "var(--muted)",
          }}
        >
          <p className="text-sm opacity-70">
            No RAG trace available yet. Send a message with depth "normal", "deep", or "diagnostic" to see retrieved context here.
          </p>
        </div>
      )}

      {/* Semantic Snippets Section */}
      {lastSemantic.length > 0 && (
        <section>
          <h3 className="text-base font-medium mb-3" style={{ color: "var(--text)" }}>
            Semantic Snippets
            <span className="ml-2 text-xs opacity-60">({lastSemantic.length} results)</span>
          </h3>
          <div className="flex flex-col gap-3">
            {lastSemantic.map((item: any, i: number) => (
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
      {lastMemory.length > 0 && (
        <section>
          <h3 className="text-base font-medium mb-3" style={{ color: "var(--text)" }}>
            Memory Recall
            <span className="ml-2 text-xs opacity-60">({lastMemory.length} results)</span>
          </h3>
          <div className="flex flex-col gap-3">
            {lastMemory.map((item: any, i: number) => (
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
