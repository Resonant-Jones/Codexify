import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import * as React from "react";

import ThreadWakePanel from "@/features/commandCenter/components/ThreadWakePanel";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function mockFetchResponse(status: number, body: unknown) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

function mockFetchReject(error: Error) {
  return vi.spyOn(globalThis, "fetch").mockRejectedValue(error);
}

const SAMPLE_HEALTH = {
  enabled: true,
  mode: "observe",
  status: "observing",
  entry_count: 3,
  ready_entries: 0,
  stale_entries: 0,
  max_entries: 16,
  estimated_memory_bytes: 0,
  max_memory_bytes: 1_073_741_824,
  total_hits: 12,
  total_misses: 20,
  total_evictions: 2,
  global_allowed: false,
  backend_capabilities: { stub: "unsupported" },
  entries_by_status: { observed: 3 },
  entries_by_scope: { thread: 3 },
};

/* ------------------------------------------------------------------ */
/*  Tests                                                             */
/* ------------------------------------------------------------------ */

// Use pollIntervalMs=0 in all tests to disable the polling interval
// (avoids infinite timer loops with fake timers)

function renderPanel(props: Partial<Parameters<typeof ThreadWakePanel>[0]> = {}) {
  return render(
    <ThreadWakePanel baseUrl="http://localhost:8000/v1" pollIntervalMs={0} {...props} />,
  );
}

describe("ThreadWakePanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders status when health response is available", async () => {
    mockFetchResponse(200, SAMPLE_HEALTH);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId("threadwake-panel")).toBeInTheDocument();
    });

    expect(screen.getByText("OBSERVING")).toBeInTheDocument();
    expect(screen.getByText("observe")).toBeInTheDocument();
    expect(screen.getByText("38%")).toBeInTheDocument();
  });

  it("renders 'Unavailable' when endpoint is unreachable", async () => {
    mockFetchReject(new Error("Connection refused"));
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Unavailable")).toBeInTheDocument();
    });
  });

  it("hides panel when hideWhenUnavailable is true and endpoint fails", async () => {
    mockFetchReject(new Error("Connection refused"));

    render(
      <ThreadWakePanel
        baseUrl="http://localhost:8000/v1"
        pollIntervalMs={0}
        hideWhenUnavailable
      />,
    );

    // Panel should not be in the DOM at all
    await waitFor(() => {
      expect(screen.queryByTestId("threadwake-panel")).not.toBeInTheDocument();
    });
  });

  it("does not use the word 'memory' in the title or primary labels", async () => {
    mockFetchResponse(200, SAMPLE_HEALTH);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId("threadwake-panel")).toBeInTheDocument();
    });

    const title = screen.getByText("ThreadWake Cache");
    expect(title.textContent).not.toContain("memory");
  });

  it("shows 'Est. Memory' label when memory estimate > 0", async () => {
    mockFetchResponse(200, {
      ...SAMPLE_HEALTH,
      estimated_memory_bytes: 440_401_920,
    });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Est. Memory")).toBeInTheDocument();
    });
    expect(screen.getByText("420 MB")).toBeInTheDocument();
  });

  it("shows 'Ready Entries' when ready entries > 0", async () => {
    mockFetchResponse(200, {
      ...SAMPLE_HEALTH,
      status: "ready",
      ready_entries: 5,
    });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Ready Entries")).toBeInTheDocument();
    });
    expect(screen.getByText("5 / 16")).toBeInTheDocument();
  });

  it('shows "READY" badge when status is ready', async () => {
    mockFetchResponse(200, {
      ...SAMPLE_HEALTH,
      status: "ready",
      ready_entries: 3,
    });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("READY")).toBeInTheDocument();
    });
  });

  it('shows "DEGRADED" badge when status is degraded', async () => {
    mockFetchResponse(200, {
      ...SAMPLE_HEALTH,
      status: "degraded",
      stale_entries: 5,
      ready_entries: 1,
    });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("DEGRADED")).toBeInTheDocument();
    });
  });

  it("does not show raw hashes in the panel", async () => {
    mockFetchResponse(200, SAMPLE_HEALTH);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId("threadwake-panel")).toBeInTheDocument();
    });

    const panel = screen.getByTestId("threadwake-panel");
    expect(panel.textContent).not.toMatch(/[a-f0-9]{64}/);
  });

  it("does not render mode when status is off", async () => {
    mockFetchResponse(200, {
      ...SAMPLE_HEALTH,
      status: "off",
      mode: "off",
      entry_count: 0,
      total_hits: 0,
      total_misses: 0,
    });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId("threadwake-panel")).toBeInTheDocument();
    });

    expect(screen.queryByText("Mode")).not.toBeInTheDocument();
  });

  it("shows 'Unavailable' when baseUrl is null", async () => {
    render(
      <ThreadWakePanel baseUrl={null} pollIntervalMs={0} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Unavailable")).toBeInTheDocument();
    });
  });

  it("omits hit rate when no data", async () => {
    mockFetchResponse(200, {
      ...SAMPLE_HEALTH,
      total_hits: 0,
      total_misses: 0,
    });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByTestId("threadwake-panel")).toBeInTheDocument();
    });

    expect(screen.queryByText("Cache Hit Rate")).not.toBeInTheDocument();
  });

  it("includes disclaimer footer text", async () => {
    mockFetchResponse(200, SAMPLE_HEALTH);
    renderPanel();

    await waitFor(() => {
      expect(
        screen.getByText(/runtime optimization, not long-term memory/),
      ).toBeInTheDocument();
    });
  });
});
