import { beforeEach, describe, expect, test, vi } from "vitest";

import api from "@/lib/api";

import { fetchSystemPromptInspectorSnapshot } from "@/features/settings/api/systemPrompt";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

const apiGetMock = vi.mocked(api.get);

describe("fetchSystemPromptInspectorSnapshot", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("reads the persisted status and resolved summary surfaces only", async () => {
    apiGetMock.mockImplementation(async (url: string) => {
      if (url === "/api/imprint/status") {
        return {
          data: {
            imprint: {
              id: 12,
              status: "active",
              heat_score: 0.7,
              preferred_name: "Harbor",
              created_at: "2026-03-08T18:00:00Z",
            },
            persona: {
              id: 8,
              source: "user",
              snippet: "Calm and technical.",
              created_at: "2026-03-08T18:05:00Z",
            },
            system_prompt_meta: {
              estimated_tokens: 1320,
              docs_count: 2,
              segments_present: {
                base: true,
                imprint: true,
                persona: true,
                system_docs: true,
              },
              segments: [
                {
                  name: "base",
                  chars: 1200,
                  estimated_tokens: 300,
                  truncated: false,
                },
                {
                  name: "imprint",
                  chars: 220,
                  estimated_tokens: 55,
                  truncated: false,
                },
                {
                  name: "persona",
                  chars: 180,
                  estimated_tokens: 45,
                  truncated: false,
                },
                {
                  name: "system_docs",
                  chars: 1400,
                  estimated_tokens: 350,
                  truncated: true,
                },
              ],
            },
          },
        } as any;
      }

      if (url === "/api/system_prompt/summary") {
        return {
          data: {
            estimated_tokens_total: 1320,
            threshold: {
              warn_tokens: 6000,
              hard_tokens: 8000,
              status: "warn",
            },
            segments: [
              {
                name: "base",
                chars: 1200,
                estimated_tokens: 300,
                truncated: false,
              },
              {
                name: "system_docs",
                chars: 1400,
                estimated_tokens: 350,
                truncated: true,
              },
            ],
            docs_count: 2,
            generated_at: "2026-03-09T04:12:00Z",
            estimated_tokens: 1320,
            cap_tokens: 8000,
            docs_truncated: true,
            overflow: false,
            warnings: ["System docs truncated due to token budget."],
          },
        } as any;
      }

      throw new Error(`unexpected endpoint: ${url}`);
    });

    const snapshot = await fetchSystemPromptInspectorSnapshot({
      projectId: 77,
      threadId: 5,
    });

    expect(apiGetMock).toHaveBeenCalledTimes(2);
    expect(apiGetMock).toHaveBeenNthCalledWith(1, "/api/imprint/status", {
      params: { project_id: 77, thread_id: 5 },
    });
    expect(apiGetMock).toHaveBeenNthCalledWith(
      2,
      "/api/system_prompt/summary",
      { params: { project_id: 77, thread_id: 5 } }
    );
    expect(snapshot.imprint?.status).toBe("active");
    expect(snapshot.persona?.source).toBe("user");
    expect(snapshot.threshold.status).toBe("warn");
    expect(snapshot.docsCount).toBe(2);
    expect(snapshot.segmentsPresent.imprint).toBe(true);
    expect(snapshot.segmentsPresent.persona).toBe(true);
  });
});
