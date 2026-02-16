import React from "react";
import clsx from "clsx";
import { AlertTriangle } from "lucide-react";
import useImprintZero from "@/imprint/useImprintZero";

type Props = {
  open: boolean;
  onClose: () => void;
};

export default function PersonaSettingsPanel({ open, onClose }: Props) {
  const imprint = useImprintZero();
  const [draftPersona, setDraftPersona] = React.useState("");

  React.useEffect(() => {
    const personaSnippet = imprint.status?.persona?.snippet || "";
    setDraftPersona(personaSnippet);
  }, [imprint.status?.persona?.snippet]);

  if (!open) return null;

  const meta = imprint.status?.system_prompt_meta;
  const warnings = meta?.warnings || [];
  const totalTokens =
    meta?.estimated_tokens_total ?? meta?.estimated_tokens ?? "—";
  const thresholdStatus = (meta?.threshold?.status || "unknown").toUpperCase();
  const segmentTokenMap = React.useMemo(() => {
    const map: Record<string, number> = {};
    const segments = Array.isArray(meta?.segments) ? meta.segments : [];
    for (const segment of segments) {
      if (!segment?.name) continue;
      map[segment.name] = Number(segment.estimated_tokens || 0);
    }
    return map;
  }, [meta?.segments]);

  return (
    <div className="fixed inset-0 z-[250] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/45" onClick={onClose} />
      <div
        className="relative z-[251] w-[min(900px,96vw)] max-h-[90vh] overflow-auto rounded-2xl border bg-[var(--panel-bg)] p-5"
        style={{ borderColor: "var(--panel-border)" }}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Persona & System Prompt
            </div>
            <div className="text-xs opacity-70" style={{ color: "var(--muted)" }}>
              Immutable core is fixed; persona and docs customize style and context.
            </div>
          </div>
          <button className="icon-inline" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <section className="rounded-xl border p-3" style={{ borderColor: "var(--panel-border)" }}>
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Persona
            </div>
            <div className="text-xs opacity-70 mb-2" style={{ color: "var(--muted)" }}>
              Source: {imprint.status?.persona?.source || "—"} | Created: {imprint.status?.persona?.created_at || "—"}
            </div>
            <textarea
              value={draftPersona}
              onChange={(e) => setDraftPersona(e.target.value)}
              className="w-full rounded-lg border bg-transparent p-2 text-sm"
              rows={8}
              style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
            />
            <div className="mt-2 flex justify-between text-xs opacity-70" style={{ color: "var(--muted)" }}>
              <span>Edits are saved as user persona and override Imprint Zero.</span>
              <span>{draftPersona.length} chars</span>
            </div>
            <div className="mt-3 flex justify-end">
              <button
                className="embedded-btn"
                onClick={() => imprint.updatePersona(draftPersona)}
                disabled={!draftPersona.trim()}
              >
                Save Persona
              </button>
            </div>
          </section>

          <section className="rounded-xl border p-3 space-y-2" style={{ borderColor: "var(--panel-border)" }}>
            <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              System Prompt Summary
            </div>
            <div className="text-xs" style={{ color: "var(--text)" }}>
              Tokens ~ {totalTokens} | Status {thresholdStatus}
            </div>
            <div className="text-xs opacity-70" style={{ color: "var(--muted)" }}>
              Base: {segmentTokenMap.base ?? 0} | Persona: {segmentTokenMap.persona ?? 0} | Docs:{" "}
              {segmentTokenMap.system_docs ?? 0}
            </div>
            {warnings.length > 0 && (
              <div
                className="flex items-center gap-2 rounded-lg border px-2 py-1 text-xs"
                style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
              >
                <AlertTriangle className="h-4 w-4" />
                {warnings.join(" ")}
              </div>
            )}

            <div className="mt-2">
              <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                System Docs
              </div>
              <div className="space-y-2 mt-2 max-h-[220px] overflow-auto pr-1">
                {imprint.systemDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className={clsx(
                      "rounded-lg border p-2 text-xs flex items-center justify-between gap-2",
                      doc.enabled ? "opacity-100" : "opacity-60"
                    )}
                    style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
                  >
                    <div className="flex-1">
                      <div className="font-semibold">{doc.title}</div>
                      <div className="opacity-70">Scope: {doc.scope} | ~{doc.token_estimate} tokens</div>
                    </div>
                    <label className="inline-flex items-center gap-1 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={doc.enabled}
                        onChange={(e) => imprint.toggleSystemDoc(doc.id, e.target.checked)}
                      />
                      Enabled
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        <section className="mt-4 rounded-xl border p-3" style={{ borderColor: "var(--panel-border)" }}>
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Imprint
          </div>
          <div className="text-xs opacity-70" style={{ color: "var(--muted)" }}>
            Active imprint only influences style; persona overrides take precedence.
          </div>
          <div className="mt-2 text-xs" style={{ color: "var(--text)" }}>
            Name: {imprint.status?.imprint?.preferred_name || "—"} | Heat: {imprint.status?.imprint?.heat_score ?? "—"}
          </div>
        </section>
      </div>
    </div>
  );
}
