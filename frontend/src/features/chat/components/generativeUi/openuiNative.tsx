/** Bounded OpenUI Lang component library for the existing Codexify native artifact lane. */
import { createLibrary, createParser, defineComponent, Renderer } from "@openuidev/react-lang";
import { z } from "zod/v4";
import {
  OPENUI_FOUNDATION_LIBRARY_VERSION,
  codexifyOpenUiFoundationLibrary,
} from "./openuiFoundationLibrary";
import { admitOpenUiFoundationProgram } from "./openuiProgramAdmission";

export const OPENUI_LIBRARY_VERSION = 1;
export const OPENUI_MAX_PROGRAM_CHARS = 2048;

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

export const codexifyOpenUiLibrary = createLibrary({
  components: [MetricPanel],
  root: "CodexifyMetric",
});

const parser = createParser(codexifyOpenUiLibrary.toJSONSchema(), codexifyOpenUiLibrary.root);

/**
 * Admit exactly one read-only literal call in this first integration slice.
 * Parsing arbitrary OpenUI programs here would admit functions, actions, and
 * Query/Mutation surfaces into the trusted host tree without Guardian grants.
 */
export function validateOpenUiProgram(props: Record<string, unknown>): string | null {
  if (props.libraryVersion !== OPENUI_LIBRARY_VERSION) return null;
  if (Object.keys(props).length !== 2) return null;
  const raw = props.program;
  if (typeof raw !== "string" || !raw || raw.length > OPENUI_MAX_PROGRAM_CHARS) return null;

  const match = /^root\s*=\s*CodexifyMetric\(([\s\S]*)\)$/.exec(raw.trim());
  if (!match) return null;

  let values: unknown;
  try {
    // This is JSON parsing, not JavaScript or OpenUI evaluation. Only JSON
    // string literals may reach the OpenUI parser and native React renderer.
    values = JSON.parse(`[${match[1]}]`);
  } catch {
    return null;
  }
  if (!Array.isArray(values) || values.length < 2 || values.length > 3) return null;
  const limits = [100, 40, 180];
  if (!values.every((value, index) => typeof value === "string" && value.length <= limits[index])) return null;

  const normalized = `root = CodexifyMetric(${values.map((value) => JSON.stringify(value)).join(", ")})`;
  const parsed = parser.parse(normalized);
  if (parsed.meta.errors.length || parsed.meta.unresolved.length) return null;
  return normalized;
}

/** Untrusted persisted props are validated before reaching OpenUI's renderer. */
export function OpenUiNative(props: Record<string, unknown>) {
  const admitted = admitOpenUiProgram(props);
  if (!admitted) return null;
  return (
    <Renderer
      response={admitted.program}
      library={admitted.version === 1 ? codexifyOpenUiLibrary : codexifyOpenUiFoundationLibrary}
      isStreaming={false}
      /* No toolProvider or onAction: actions and network remain unavailable. */
    />
  );
}

/**
 * Version-aware, fail-closed admission across both library versions.
 *
 * Version 1 keeps its original single-literal-metric validator verbatim, so
 * existing persisted artifacts restore exactly as before. Version 2 routes
 * through the structural admission walk, which re-derives the resolved tree
 * rather than trusting permissive parser output.
 */
export function admitOpenUiProgram(
  props: Record<string, unknown>,
): { version: 1 | 2; program: string } | null {
  const declared = props?.libraryVersion;
  if (declared === OPENUI_LIBRARY_VERSION) {
    const program = validateOpenUiProgram(props);
    return program ? { version: 1, program } : null;
  }
  if (declared === OPENUI_FOUNDATION_LIBRARY_VERSION) {
    const admitted = admitOpenUiFoundationProgram(props);
    return admitted.ok ? { version: 2, program: admitted.program } : null;
  }
  return null;
}
