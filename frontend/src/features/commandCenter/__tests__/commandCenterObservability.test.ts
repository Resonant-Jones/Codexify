import { describe, expect, it } from "vitest";

import { buildCommandCenterTraceReportModel } from "../commandCenterObservability";
import { classifyRetrievalPostureTrend, filterRetrievalPostureHistory, limitRetrievalPostureHistory } from "../components/TraceWorkbench";
import type { CommandCenterRagTracePayload } from "../types";

describe("commandCenterObservability null safety", () => {
  it("handles partial normalized trace payloads without throwing", () => {
    const partialTrace = {
      resolvedThreadId: 42,
      // intentionally omit semantic and graph to mirror partial live payload shapes
    } as unknown as CommandCenterRagTracePayload;

    expect(() =>
      buildCommandCenterTraceReportModel({
        normalizedTrace: partialTrace,
        rawTrace: {
          documents: undefined,
          graph: undefined,
          memory: undefined,
          payload_summary: {},
          retrieval_plan: {},
        },
        run: null,
        unavailableReason: null,
      })
    ).not.toThrow();
  });

  it("keeps report sections available when nested raw-trace fields are missing", () => {
    const model = buildCommandCenterTraceReportModel({
      normalizedTrace: null,
      rawTrace: {
        documents: null,
        graph: null,
        memory: null,
        payload_summary: null,
        retrieval_plan: null,
      },
      run: null,
      unavailableReason: null,
    });

    expect(model.verdict).toBe("Trace available for inspection.");
    expect(model.payloadSummaryRows.length).toBeGreaterThan(0);
    expect(model.markdown).toContain("## Retrieval Outcome");
  });
});

describe("retrieval posture history null safety", () => {
  it("treats missing history arrays as empty", () => {
    expect(filterRetrievalPostureHistory(undefined, "all")).toEqual([]);
    expect(limitRetrievalPostureHistory(undefined, 5)).toEqual([]);
    expect(classifyRetrievalPostureTrend(undefined)).toBe("insufficient_history");
  });
});
