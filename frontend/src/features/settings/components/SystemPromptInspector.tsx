import useSystemPromptInspector from "@/features/settings/hooks/useSystemPromptInspector";

type SystemPromptInspectorProps = {
  className?: string;
  projectId?: number | null;
  threadId?: number;
};

const PRESENCE_LABEL: Record<string, string> = {
  present: "Present",
  absent: "Absent",
  unavailable: "Unavailable",
};

const PRESENCE_STYLE: Record<string, { background: string; borderColor: string }> =
  {
    present: {
      background: "rgba(34, 197, 94, 0.12)",
      borderColor: "rgba(34, 197, 94, 0.35)",
    },
    absent: {
      background: "rgba(148, 163, 184, 0.12)",
      borderColor: "rgba(148, 163, 184, 0.28)",
    },
    unavailable: {
      background: "rgba(245, 158, 11, 0.12)",
      borderColor: "rgba(245, 158, 11, 0.35)",
    },
  };

export default function SystemPromptInspector({
  className,
  projectId,
  threadId,
}: SystemPromptInspectorProps) {
  const { error, hasLoaded, layers, loading, reload, snapshot } =
    useSystemPromptInspector({ projectId, threadId });

  return (
    <section
      className={[
        "space-y-4 rounded-2xl border p-4 sm:p-5",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 88%, transparent)",
        borderColor: "var(--panel-border)",
      }}
      data-testid="system-prompt-inspector"
    >
      <div className="space-y-1">
        <h2 className="text-base font-semibold" style={{ color: "var(--text)" }}>
          System Prompt Inspector
        </h2>
        <p className="text-sm leading-6" style={{ color: "var(--muted)" }}>
          Read-only visibility into persisted active identity records and the
          resolved prompt preview. Request-time selection is only visible when
          exposed by existing backend status surfaces; edit controls stay
          outside this inspector.
        </p>
      </div>

      {loading ? (
        <div
          className="rounded-xl border px-3 py-4 text-sm"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
          role="status"
        >
          Loading prompt stack…
        </div>
      ) : (
        <>
          <div
            className="grid gap-3 rounded-xl border p-3 text-sm sm:grid-cols-2"
            style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
          >
            <div>
              <div className="text-xs uppercase tracking-wide opacity-70">
                Token summary
              </div>
              <div className="mt-1 font-medium">
                {snapshot?.estimatedTokensTotal ?? "—"} tokens
              </div>
              <div className="mt-1 text-xs opacity-80">
                Status: {(snapshot?.threshold.status ?? "unknown").toUpperCase()}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide opacity-70">
                Metadata
              </div>
              <div className="mt-1 text-sm">
                Docs: {snapshot?.docsCount ?? "—"}
              </div>
              <div className="mt-1 text-xs opacity-80">
                Generated: {snapshot?.generatedAt ?? "Not exposed"}
              </div>
            </div>
          </div>

          {snapshot?.warnings.length ? (
            <div
              className="rounded-xl border px-3 py-2 text-sm"
              style={{
                borderColor: "rgba(245, 158, 11, 0.35)",
                background: "rgba(245, 158, 11, 0.12)",
                color: "var(--text)",
              }}
              role="note"
            >
              {snapshot.warnings.join(" ")}
            </div>
          ) : null}

          <ol className="space-y-3" aria-label="Prompt layers">
            {layers.map((layer, index) => {
              const presenceStyle = PRESENCE_STYLE[layer.presence];

              return (
                <li
                  key={layer.key}
                  className="rounded-xl border p-3"
                  style={{ borderColor: "var(--panel-border)" }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div
                        className="text-xs uppercase tracking-wide opacity-70"
                        style={{ color: "var(--muted)" }}
                      >
                        Layer {index + 1}
                      </div>
                      <div
                        className="text-sm font-semibold"
                        style={{ color: "var(--text)" }}
                      >
                        {layer.title}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className="rounded-full border px-2 py-1 font-medium"
                        style={{
                          ...presenceStyle,
                          color: "var(--text)",
                        }}
                      >
                        {PRESENCE_LABEL[layer.presence]}
                      </span>
                      <span
                        className="rounded-full border px-2 py-1"
                        style={{
                          borderColor: "var(--panel-border)",
                          color: "var(--muted)",
                        }}
                      >
                        Editable here: {layer.editableHere ? "Yes" : "No"}
                      </span>
                    </div>
                  </div>

                  <p
                    className="mt-3 text-sm leading-6"
                    style={{ color: "var(--muted)" }}
                  >
                    {layer.description}
                  </p>

                  {layer.metadata.length ? (
                    <ul className="mt-3 flex flex-wrap gap-2 text-xs">
                      {layer.metadata.map((item) => (
                        <li
                          key={item}
                          className="rounded-full border px-2 py-1"
                          style={{
                            borderColor: "var(--panel-border)",
                            color: "var(--text)",
                          }}
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-3 text-xs opacity-75" style={{ color: "var(--muted)" }}>
                      No extra metadata exposed for this layer.
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </>
      )}

      {error && (
        <div
          className="rounded-xl border px-3 py-2 text-sm"
          style={{
            borderColor: "rgba(239, 68, 68, 0.35)",
            background: "rgba(239, 68, 68, 0.12)",
            color: "var(--text)",
          }}
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-[var(--tile-radius,19px)] border px-4 py-2 text-sm font-medium transition disabled:pointer-events-none disabled:opacity-50"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--text)",
            background: "transparent",
          }}
          onClick={() => void reload()}
          disabled={loading}
        >
          {hasLoaded ? "Reload inspector" : "Retry"}
        </button>
      </div>
    </section>
  );
}
