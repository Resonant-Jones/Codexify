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

  test("reads and normalizes the canonical inspection projection with one request", async () => {
    apiGetMock.mockResolvedValue({
      data: {
        generated_at: "2026-09-06T04:12:00Z",
        scope: { user_id: "account-a", thread_id: 5, project_id: 77 },
        persona_profile: {
          state: "present",
          error_code: null,
          profile_id: "profile-axis",
          revision: 3,
          source: "account_binding",
        },
        imprint: {
          state: "present",
          error_code: null,
          id: 12,
          status: "active",
          preferred_name: "Harbor",
          heat_score: 0.7,
          style: "calm",
        },
        system_docs: {
          state: "present",
          error_code: null,
          count: 2,
          truncated: true,
        },
        prompt: {
          state: "present",
          error_code: null,
          projection_kind: "canonical_inspection",
          legacy_persona_included: false,
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
          docs_count: 2,
          docs_truncated: true,
          warnings: ["System docs truncated due to token budget."],
        },
      },
    } as any);

    const snapshot = await fetchSystemPromptInspectorSnapshot({
      projectId: 77,
      threadId: 5,
    });

    expect(apiGetMock).toHaveBeenCalledTimes(1);
    expect(apiGetMock).toHaveBeenCalledWith("/api/system_prompt/inspect", {
      params: { project_id: 77, thread_id: 5 },
    });
    expect(snapshot.generatedAt).toBe("2026-09-06T04:12:00Z");
    expect(snapshot.persona).toEqual({
      errorCode: null,
      profileId: "profile-axis",
      revision: 3,
      source: "account_binding",
      state: "present",
    });
    expect(snapshot.imprint).toMatchObject({
      id: 12,
      preferredName: "Harbor",
      style: "calm",
      state: "present",
    });
    expect(snapshot.systemDocs).toEqual({
      count: 2,
      errorCode: null,
      state: "present",
      truncated: true,
    });
    expect(snapshot.prompt).toEqual({
      docsCount: 2,
      docsTruncated: true,
      errorCode: null,
      legacyPersonaIncluded: false,
      projectionKind: "canonical_inspection",
      state: "present",
    });
    expect(snapshot.estimatedTokensTotal).toBe(1320);
    expect(snapshot.threshold.status).toBe("warn");
    expect(snapshot.segments).toHaveLength(4);
    expect(snapshot.warnings).toEqual(["System docs truncated due to token budget."]);
  });

  test("preserves revisionless Persona Profiles and independent backend layer states", async () => {
    apiGetMock.mockResolvedValue({
      data: {
        generated_at: "2026-09-06T05:00:00Z",
        scope: { user_id: "account-a", thread_id: 5, project_id: null },
        persona_profile: {
          state: "present",
          error_code: null,
          profile_id: "environment-profile",
          revision: null,
          source: "environment",
        },
        imprint: {
          state: "absent",
          error_code: null,
          id: null,
          status: null,
          preferred_name: null,
          heat_score: null,
          style: null,
        },
        system_docs: {
          state: "unavailable",
          error_code: "system_docs_observation_unavailable",
          count: null,
          truncated: null,
        },
        prompt: {
          state: "present",
          error_code: null,
          projection_kind: "canonical_inspection",
          legacy_persona_included: false,
          estimated_tokens_total: 420,
          threshold: {
            warn_tokens: 6000,
            hard_tokens: 8000,
            status: "ok",
          },
          segments: [
            { name: "base", chars: 600, estimated_tokens: 150, truncated: false },
          ],
          docs_count: null,
          docs_truncated: null,
        },
      },
    } as any);

    const snapshot = await fetchSystemPromptInspectorSnapshot();

    expect(snapshot.persona).toEqual({
      errorCode: null,
      profileId: "environment-profile",
      revision: null,
      source: "environment",
      state: "present",
    });
    expect(snapshot.imprint.state).toBe("absent");
    expect(snapshot.systemDocs).toEqual({
      count: null,
      errorCode: "system_docs_observation_unavailable",
      state: "unavailable",
      truncated: null,
    });
    expect(snapshot.prompt.state).toBe("present");
    expect(snapshot.docsCount).toBeNull();
    expect(snapshot.docsTruncated).toBeNull();
  });

  test("preserves an unavailable canonical Persona layer without collapsing the snapshot", async () => {
    apiGetMock.mockResolvedValue({
      data: {
        generated_at: "2026-09-06T05:30:00Z",
        scope: { user_id: "account-a", thread_id: 5, project_id: null },
        persona_profile: {
          state: "unavailable",
          error_code: "system_profile_resolution_unavailable",
          profile_id: "profile-pinned",
          revision: 7,
          source: null,
        },
        imprint: {
          state: "present",
          error_code: null,
          id: 12,
          status: "active",
          preferred_name: "Harbor",
          heat_score: null,
          style: null,
        },
        system_docs: {
          state: "absent",
          error_code: null,
          count: 0,
          truncated: false,
        },
        prompt: {
          state: "present",
          error_code: null,
          projection_kind: "canonical_inspection",
          legacy_persona_included: false,
          estimated_tokens_total: 300,
          threshold: {
            warn_tokens: 6000,
            hard_tokens: 8000,
            status: "ok",
          },
          segments: [
            { name: "base", chars: 1200, estimated_tokens: 300, truncated: false },
          ],
          docs_count: 0,
          docs_truncated: false,
        },
      },
    } as any);

    const snapshot = await fetchSystemPromptInspectorSnapshot();

    expect(snapshot.persona).toEqual({
      errorCode: "system_profile_resolution_unavailable",
      profileId: "profile-pinned",
      revision: 7,
      source: null,
      state: "unavailable",
    });
    expect(snapshot.imprint.state).toBe("present");
    expect(snapshot.systemDocs.state).toBe("absent");
    expect(snapshot.prompt.state).toBe("present");
  });

  test("propagates request-level failures for the existing retry behavior", async () => {
    const error = new Error("inspector request failed");
    apiGetMock.mockRejectedValueOnce(error);

    await expect(fetchSystemPromptInspectorSnapshot()).rejects.toBe(error);
    expect(apiGetMock).toHaveBeenCalledTimes(1);
  });
});
