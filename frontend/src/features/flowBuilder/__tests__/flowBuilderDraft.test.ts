import { describe, expect, it } from "vitest";

import { createFlowBuilderExpertiseDraft } from "../flowBuilderDraft";

describe("createFlowBuilderExpertiseDraft", () => {
  it("creates a non-runtime draft specification skeleton for the expertise lane", () => {
    const draft = createFlowBuilderExpertiseDraft();

    expect(draft.sourceMode).toBe("expertise");
    expect(draft.title).toBe("Draft specification");
    expect(draft.status).toBe("draft-only");
    expect(draft.runtimeSupport).toBe("none");
    expect(draft.objective).toContain("desired outcome");
    expect(draft.assumptions).toContain("inferred");
    expect(draft.unknowns).toContain("missing steps");
    expect(draft.validationQuestions).toContain("questions");
  });
});
