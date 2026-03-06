import { useState } from "react";
import { Zap } from "lucide-react";
import { isRagTraceUIEnabled } from "@/lib/devFlags";
import RAGTracePanel from "../panels/RAGTracePanel";

interface TraceButtonProps {
  threadId: number | null;
}

/**
 * Developer button to open the RAG Trace debug panel
 *
 * Only visible when VITE_SHOW_RAG_TRACE_UI is true or the dev flag is enabled
 */
export default function TraceButton({ threadId }: TraceButtonProps) {
  const [showPanel, setShowPanel] = useState(false);

  if (!isRagTraceUIEnabled()) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setShowPanel(true)}
        title="Open RAG Trace debug panel"
        className="icon-inline opacity-80 transition hover:opacity-100"
      >
        <Zap size={18} />
      </button>

      <RAGTracePanel
        open={showPanel}
        onOpenChange={setShowPanel}
        threadId={threadId}
      />
    </>
  );
}
