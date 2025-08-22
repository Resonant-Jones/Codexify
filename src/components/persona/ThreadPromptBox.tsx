import React, { useState, useContext, FormEvent, useEffect } from "react";
import { PersonaEngine } from "../../persona/PersonaEngine";
import { PersonaContext } from "./PersonaProvider";

/**
 * ThreadPromptBox – a minimal chat input component that uses the
 * memory‑aware PersonaEngine.
 *
 * Features:
 * - Pulls activePersonaId, memoryTags, and debugMode from PersonaProvider.
 * - Calls PersonaEngine.generateWithMemory on submit.
 * - Shows a loading spinner while awaiting the response.
 * - Displays the completion and, when debugMode is true, the full assembled prompt.
 */
export const ThreadPromptBox: React.FC = () => {
  const { activePersonaId, memoryTags, debugMode } = useContext(PersonaContext);

  const isDevRuntime = typeof process !== "undefined" && process.env && process.env.NODE_ENV !== "production";
  const [devEnabled, setDevEnabled] = useState<boolean>(isDevRuntime);
  useEffect(() => {
    if (isDevRuntime) return;
    try {
      const qs = typeof window !== "undefined" ? window.location.search : "";
      const hasQuery = qs ? /(?:^|[?&])dev=1(?:&|$)/.test(qs) : false;
      const stored = typeof window !== "undefined" && window.localStorage.getItem("cfy.devTools") === "on";
      if (hasQuery || stored) setDevEnabled(true);
    } catch {}
  }, [isDevRuntime]);
  if (!devEnabled) return null;

  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [completion, setCompletion] = useState<string | null>(null);
  const [debugPrompt, setDebugPrompt] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!activePersonaId) return;
    setLoading(true);
    setCompletion(null);
    setDebugPrompt(null);
    try {
      const result = await PersonaEngine.generateWithMemory(
        prompt,
        activePersonaId,
        memoryTags
      );
      setCompletion(result.completion);
      if (debugMode) {
        const frags = (result as any).memory_fragments ?? [];
        const memoryBlock = Array.isArray(frags) ? frags.map((f: any) => f?.content ?? "").join("\n") : "";
        const fullPrompt = `--- Memory ---\n${memoryBlock}\n--- End Memory ---\n${prompt}`;
        setDebugPrompt(fullPrompt);
      }
    } catch (err) {
      console.error(err);
      setCompletion("Error generating response.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col w-full max-w-xl mx-auto p-4" style={{ color: "var(--text)" }}>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={activePersonaId ? "Enter your prompt..." : "Pick a persona to enable dev prompt…"}
          className="flex-1 p-2 rounded border focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
          style={{ background: "transparent", borderColor: "var(--panel-border)", color: "var(--text)", outlineColor: "var(--accent-weak)" }}
          disabled={loading || !activePersonaId}
        />
        <button
          type="submit"
          disabled={loading || !prompt || !activePersonaId}
          className="px-4 py-2 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
          style={{ background: "var(--accent-weak)", color: "#000", outlineColor: "var(--accent-weak)" }}
        >
          Send
        </button>
      </form>
      <div className="sr-only" aria-live="polite">{!activePersonaId ? "Select a persona to enable dev prompt" : loading ? "Generating" : completion ? "Response ready" : "Idle"}</div>

      {loading && (
        <div className="mt-4 flex items-center gap-2">
          <svg
            className="animate-spin h-5 w-5"
            style={{ color: "var(--muted)" }}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            />
          </svg>
          <span>Generating...</span>
        </div>
      )}

      {completion && (
        <div className="mt-4 p-4 rounded border" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
          <h3 className="font-bold mb-2">Response</h3>
          <p>{completion}</p>
        </div>
      )}

      {debugMode && debugPrompt && (
        <div className="mt-4 p-4 rounded border" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
          <h3 className="font-bold mb-2">Debug Prompt</h3>
          <pre className="whitespace-pre-wrap">{debugPrompt}</pre>
        </div>
      )}
    </div>
  );
};