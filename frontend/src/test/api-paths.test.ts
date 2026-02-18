import { describe, expect, it } from "vitest";

import { buildThreadDocumentsPath } from "@/lib/api";

describe("API path builders", () => {
  it("builds thread documents path under /documents/threads/:id/documents", () => {
    expect(buildThreadDocumentsPath("123")).toBe(
      "/documents/threads/123/documents"
    );
  });
});
