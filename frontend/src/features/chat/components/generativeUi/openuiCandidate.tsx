/** Isolated OpenUI candidate. Not registered in the production native registry. */
import React from "react";
import { createLibrary, defineComponent, Renderer } from "@openuidev/react-lang";
import { z } from "zod/v4";

const MetricPanel = defineComponent({
  name: "CodexifyMetric",
  description: "Read-only metric card using the active Codexify shell theme.",
  props: z.object({
    title: z.string().max(100),
    value: z.string().max(40),
    detail: z.string().max(180).optional(),
  }),
  component: ({ props }) => (
    <section
      data-testid="openui-codexify-metric"
      style={{
        maxWidth: "100%",
        overflowWrap: "anywhere",
        border: "1px solid var(--panel-border)",
        borderRadius: "var(--card-radius, var(--tile-radius))",
        padding: "var(--card-pad)",
        background: "var(--panel-bg)",
        color: "var(--text)",
      }}
    >
      <div style={{ color: "var(--muted)", fontSize: "0.875em" }}>{props.title}</div>
      <strong style={{ display: "block", fontSize: "1.6em" }}>{props.value}</strong>
      {props.detail ? <div style={{ color: "var(--muted)" }}>{props.detail}</div> : null}
    </section>
  ),
});

export const codexifyOpenUiCandidateLibrary = createLibrary({
  components: [MetricPanel],
  root: "CodexifyMetric",
});

/** A validated cfy-ui native artifact could pass its program as this response. */
export function OpenUiCandidate({ response }: { response: string }) {
  return (
    <Renderer
      response={response}
      library={codexifyOpenUiCandidateLibrary}
      isStreaming={false}
      /* Deliberately omit toolProvider and onAction: no generated tool/action authority. */
    />
  );
}
