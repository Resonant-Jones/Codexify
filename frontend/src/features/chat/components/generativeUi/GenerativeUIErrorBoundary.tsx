/**
 * Error boundary for generative UI surfaces.
 *
 * A render-time throw inside a generated artifact must never blank the chat
 * transcript. Without this, a single bad artifact unmounts the whole message
 * list, which is exactly the transcript-integrity failure the chat runtime
 * contract forbids.
 *
 * Failure degrades to an inline notice; surrounding message prose is unaffected.
 */
import React from "react";

type Props = { children: React.ReactNode };
type State = { failed: boolean };

export class GenerativeUIErrorBoundary extends React.Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    // Surfaced for diagnostics only. Never includes generated source.
    if (import.meta.env.DEV) {
      console.error("[cfy-ui] artifact render failed", error);
    }
  }

  render() {
    if (this.state.failed) {
      return (
        <div
          data-testid="generative-ui-error"
          className="max-w-[min(34rem,100%)] rounded-xl border border-dashed border-black/20 px-3 py-2 text-xs dark:border-white/20"
          style={{ color: "var(--muted)" }}
        >
          The generated interface could not be displayed.
        </div>
      );
    }
    return this.props.children;
  }
}

export default GenerativeUIErrorBoundary;