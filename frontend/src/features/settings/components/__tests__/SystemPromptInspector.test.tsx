import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import SystemPromptInspector from "@/features/settings/components/SystemPromptInspector";
import { fetchSystemPromptInspectorSnapshot } from "@/features/settings/api/systemPrompt";

vi.mock("@/features/settings/api/systemPrompt", () => ({
  fetchSystemPromptInspectorSnapshot: vi.fn(),
}));

const fetchSystemPromptInspectorSnapshotMock = vi.mocked(
  fetchSystemPromptInspectorSnapshot
);

describe("SystemPromptInspector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders the layered prompt stack as a read-only inspector", async () => {
    fetchSystemPromptInspectorSnapshotMock.mockResolvedValue({
      docsCount: 2,
      docsTruncated: true,
      estimatedTokensTotal: 1320,
      generatedAt: "2026-03-09T04:12:00Z",
      imprint: {
        createdAt: "2026-03-08T18:00:00Z",
        heatScore: 0.7,
        id: 12,
        preferredName: "Harbor",
        status: "active",
      },
      persona: {
        createdAt: "2026-03-08T18:05:00Z",
        id: 8,
        snippet: "Calm and technical.",
        source: "user",
      },
      segments: [
        { name: "base", chars: 1200, estimatedTokens: 300, truncated: false },
        { name: "imprint", chars: 220, estimatedTokens: 55, truncated: false },
        { name: "persona", chars: 180, estimatedTokens: 45, truncated: false },
        {
          name: "system_docs",
          chars: 1400,
          estimatedTokens: 350,
          truncated: true,
        },
      ],
      segmentsPresent: {
        base: true,
        imprint: true,
        persona: true,
        system_docs: true,
      },
      threshold: {
        hardTokens: 8000,
        status: "ok",
        warnTokens: 6000,
      },
      warnings: ["System docs truncated due to token budget."],
    });

    render(<SystemPromptInspector projectId={77} threadId={5} />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading prompt stack…");

    expect(await screen.findByText("System Prompt Inspector")).toBeInTheDocument();
    expect(screen.getByText("1320 tokens")).toBeInTheDocument();
    expect(screen.getAllByText("Docs: 2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Present")).toHaveLength(4);
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Editable here: No")).toHaveLength(5);
    expect(screen.getByText("Persona ID: 8")).toBeInTheDocument();
    expect(screen.getByText("Imprint ID: 12")).toBeInTheDocument();
    expect(screen.getByText("Truncated to fit token budget")).toBeInTheDocument();

    expect(fetchSystemPromptInspectorSnapshotMock).toHaveBeenCalledWith({
      projectId: 77,
      threadId: 5,
    });
  });

  test("degrades gracefully when layers are absent or not exposed", async () => {
    fetchSystemPromptInspectorSnapshotMock.mockResolvedValue({
      docsCount: 0,
      docsTruncated: false,
      estimatedTokensTotal: null,
      generatedAt: null,
      imprint: null,
      persona: null,
      segments: [{ name: "base", chars: 1200, estimatedTokens: 300, truncated: false }],
      segmentsPresent: {
        base: true,
        imprint: false,
        persona: false,
        system_docs: false,
      },
      threshold: {
        hardTokens: null,
        status: "unknown",
        warnTokens: null,
      },
      warnings: [],
    });

    render(<SystemPromptInspector />);

    expect(await screen.findByText("— tokens")).toBeInTheDocument();
    expect(screen.getAllByText("Absent")).toHaveLength(3);
    expect(screen.getByText("Generated: Not exposed")).toBeInTheDocument();
    expect(
      screen.getAllByText("No extra metadata exposed for this layer.").length
    ).toBeGreaterThan(0);
  });

  test("shows an error and supports reload", async () => {
    const user = userEvent.setup();

    fetchSystemPromptInspectorSnapshotMock
      .mockRejectedValueOnce(new Error("inspector failed"))
      .mockResolvedValueOnce({
        docsCount: 1,
        docsTruncated: false,
        estimatedTokensTotal: 420,
        generatedAt: "2026-03-09T05:00:00Z",
        imprint: null,
        persona: null,
        segments: [{ name: "base", chars: 600, estimatedTokens: 150, truncated: false }],
        segmentsPresent: { base: true, system_docs: false },
        threshold: {
          hardTokens: 8000,
          status: "ok",
          warnTokens: 6000,
        },
        warnings: [],
      });

    render(<SystemPromptInspector />);

    expect(await screen.findByRole("alert")).toHaveTextContent("inspector failed");

    await user.click(screen.getByRole("button", { name: "Reload inspector" }));

    await waitFor(() => {
      expect(fetchSystemPromptInspectorSnapshotMock).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText("420 tokens")).toBeInTheDocument();
  });
});
