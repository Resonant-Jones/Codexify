import { describe, expect, it } from "vitest";

import {
  resolveModelDisplayLabel,
  shortenModelLabel,
} from "@/lib/modelLabels";

describe("modelLabels", () => {
  it("shortens local filesystem paths into concise model labels", () => {
    expect(
      shortenModelLabel(
        "/Users/resonant_jones/models/gemma-4-12B-it-qat-4bit"
      )
    ).toBe("Gemma 4 12B QAT");
  });

  it("prefers explicit profile display names when available", () => {
    expect(
      resolveModelDisplayLabel({
        profileDisplayName: "Gemma 4 E2B Unsloth",
        catalogDisplayName:
          "/Users/resonant_jones/models/gemma-4-e2b-it-4bit",
        modelId: "mlx-community/gemma-4-e2b-it-4bit",
      })
    ).toBe("Gemma 4 E2B Unsloth");
  });

  it("falls back to a concise catalog label for local artifact identifiers", () => {
    expect(
      resolveModelDisplayLabel({
        catalogDisplayName:
          "/Users/resonant_jones/models/gemma-4-e2b-it-4bit",
        modelId: "mlx-community/gemma-4-e2b-it-4bit",
      })
    ).toBe("Gemma 4 E2B");
  });

  it("falls back safely to unknown model ids", () => {
    expect(
      resolveModelDisplayLabel({
        modelId: "mystery-model-v42",
      })
    ).toBe("mystery-model-v42");
  });

  it("does not mutate routing or provider fields while normalizing labels", () => {
    const source = {
      providerId: "local",
      provider_id: "local",
      profileDisplayName: null,
      catalogDisplayName: "/Users/resonant_jones/models/gemma-4-12B-it-qat-4bit",
      modelId: "mlx-community/gemma-4-12B-it-qat-4bit",
      providerRuntimeState: "ready",
    } as const;
    const snapshot = JSON.parse(JSON.stringify(source));

    expect(resolveModelDisplayLabel(source)).toBe("Gemma 4 12B QAT");
    expect(source).toEqual(snapshot);
  });
});
