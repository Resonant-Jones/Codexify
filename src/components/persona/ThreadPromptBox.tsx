import React, { useState, useContext, FormEvent } from "react";
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
        const memoryBlock = result.memory_fragments
          .map((f) => f.content)
          .join("\n");
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
    <div className="flex flex-col w-full max-w-xl mx-auto p-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prompt..."
          className="flex-1 p-2 border rounded disabled:opacity-50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !prompt}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>

      {loading && (
        <div className="mt-4 flex items-center gap-2">
          <svg
            className="animate-spin h-5 w-5 text-gray-600"
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
        <div className="mt-4 p-4 bg-gray-100 rounded">
          <h3 className="font-bold mb-2">Response</h3>
          <p>{completion}</p>
        </div>
      )}

      {debugMode && debugPrompt && (
        <div className="mt-4 p-4 bg-gray-50 border rounded">
          <h3 className="font-bold mb-2">Debug Prompt</h3>
          <pre className="whitespace-pre-wrap">{debugPrompt}</pre>
        </div>
      )}
    </div>
  );
};