import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CodingWorkOrdersPanel from "@/features/commandCenter/components/CodingWorkOrdersPanel";
import api from "@/lib/api";
import type {
  CommandCenterCodingWorkOrder,
  CommandCenterOrchestratorNextResponse,
} from "@/features/commandCenter/types";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const apiGetMock = vi.mocked(api.get);
const apiPostMock = vi.mocked(api.post);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, reject, resolve };
}

function buildWorkOrder(
  overrides: Partial<CommandCenterCodingWorkOrder> = {}
): CommandCenterCodingWorkOrder {
  return {
    adapter_kind: "mock",
    archived_at: null,
    assigned_worker_id: null,
    blocked_reason: null,
    campaign_id: "campaign-1",
    commit_after_validation: false,
    created_at: "2026-05-10T08:00:00+00:00",
    created_by: null,
    dependency_ids: [],
    extra_meta: {},
    file_scope: ["frontend/src/App.tsx"],
    latest_lease_id: null,
    latest_receipt_id: null,
    latest_run_id: null,
    max_validation_attempts: 1,
    objective: "Objective",
    priority: 1,
    require_human_review_before_merge: true,
    require_worktree_lease: false,
    scope: "backend",
    source_message_id: null,
    source_thread_id: null,
    status: "ready",
    title: "Work order",
    updated_at: "2026-05-10T08:01:00+00:00",
    validation_command: "pytest -q",
    work_order_id: "wo-1",
    ...overrides,
  };
}

function buildRecommendationResponse(
  overrides: Partial<CommandCenterOrchestratorNextResponse> = {}
): CommandCenterOrchestratorNextResponse {
  return {
    campaign_id: null,
    decision_reasons: ["evaluated work orders: 3"],
    generated_at: "2026-05-10T08:02:00+00:00",
    limit: 5,
    ok: true,
    recommendations: [
      {
        decision: "recommendation_only",
        dependency_ids: [],
        file_scope: ["frontend/src/App.tsx"],
        latest_lease_id: null,
        latest_run_id: null,
        priority: 3,
        rank: 1,
        reason_codes: ["READY_FOR_DISPATCH", "HUMAN_REVIEW_REQUIRED"],
        requires_human_review: true,
        status: "ready",
        title: "Recommendation one",
        work_order_id: "wo-rec-1",
      },
    ],
    skipped: [
      {
        message: "work order is not in ready status (current=draft)",
        reason_code: "STATUS_NOT_READY",
        work_order_id: "wo-skip-1",
      },
    ],
    ...overrides,
  };
}

function configureSuccessResponses(workOrders: CommandCenterCodingWorkOrder[]) {
  const orchestrator = buildRecommendationResponse();
  apiGetMock.mockImplementation(async (url: string) => {
    if (url === "/api/coding/work-orders") {
      return {
        data: {
          count: workOrders.length,
          items: workOrders,
          limit: 50,
          offset: 0,
          ok: true,
        },
      };
    }
    if (/^\/api\/coding\/work-orders\/[^/]+$/.test(url)) {
      const workOrderId = decodeURIComponent(url.split("/").pop() ?? "");
      const found = workOrders.find((item) => item.work_order_id === workOrderId);
      return { data: { ok: true, work_order: found ?? workOrders[0] } };
    }
    if (url === "/api/coding/orchestrator/next") {
      return { data: orchestrator };
    }
    throw new Error(`Unexpected GET ${url}`);
  });

  apiPostMock.mockImplementation(async (url: string) => {
    if (url === "/api/coding/work-orders") {
      return { data: { ok: true, work_order: workOrders[0] } };
    }
    if (url.endsWith("/cancel")) {
      return { data: { ok: true, work_order: workOrders[0] } };
    }
    throw new Error(`Unexpected POST ${url}`);
  });
}

describe("CodingWorkOrdersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders panel title and explanatory non-dispatch copy", async () => {
    configureSuccessResponses([buildWorkOrder()]);

    render(<CodingWorkOrdersPanel />);

    expect(
      screen.getByRole("heading", { name: "Automated Worker Control Plane" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Dispatch, lease allocation, merge automation, and worker launch are not enabled/i)
    ).toBeInTheDocument();

    expect(await screen.findByTestId("coding-work-orders-panel")).toBeInTheDocument();
  });

  it("renders work orders from the API response", async () => {
    const workOrders = [
      buildWorkOrder({ title: "Ready one", work_order_id: "wo-ready", status: "ready" }),
      buildWorkOrder({ title: "Blocked one", work_order_id: "wo-blocked", status: "blocked" }),
    ];
    configureSuccessResponses(workOrders);

    render(<CodingWorkOrdersPanel />);

    expect(await screen.findByText("Ready one")).toBeInTheDocument();
    expect(screen.getByText("Blocked one")).toBeInTheDocument();
    expect(screen.getAllByTestId("coding-work-order-row")).toHaveLength(2);
  });

  it("renders orchestrator recommendations and skipped reasons", async () => {
    configureSuccessResponses([buildWorkOrder()]);

    render(<CodingWorkOrdersPanel />);

    const recommendations = await screen.findByTestId(
      "coding-orchestrator-recommendations"
    );
    expect(within(recommendations).getByText(/Recommendation one/)).toBeInTheDocument();
    expect(
      within(recommendations).getByText("READY_FOR_DISPATCH")
    ).toBeInTheDocument();

    const skipped = screen.getByTestId("coding-orchestrator-skipped");
    expect(
      within(skipped).getByText(/Skipped reasons are collapsed to keep recommendations scannable/i)
    ).toBeInTheDocument();
    fireEvent.click(
      within(skipped).getByRole("button", { name: /show skipped reasons/i })
    );
    expect(within(skipped).getByText(/wo-skip-1/)).toBeInTheDocument();
    expect(within(skipped).getByText(/STATUS_NOT_READY/)).toBeInTheDocument();
  });

  it("submitting create form calls POST /api/coding/work-orders", async () => {
    configureSuccessResponses([buildWorkOrder()]);

    render(<CodingWorkOrdersPanel />);

    const form = await screen.findByTestId("coding-work-order-create-form");
    fireEvent.click(screen.getByRole("button", { name: /expand form/i }));
    fireEvent.change(within(form).getByLabelText("Title"), {
      target: { value: "Create from UI" },
    });
    fireEvent.change(within(form).getByLabelText("Objective"), {
      target: { value: "Objective from UI" },
    });
    fireEvent.submit(form);

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith(
        "/api/coding/work-orders",
        expect.objectContaining({
          objective: "Objective from UI",
          title: "Create from UI",
        })
      );
    });
  });

  it("toggles the create form collapse state", async () => {
    configureSuccessResponses([buildWorkOrder()]);

    render(<CodingWorkOrdersPanel />);

    const form = await screen.findByTestId("coding-work-order-create-form");
    expect(form).toHaveClass("hidden");

    fireEvent.click(screen.getByRole("button", { name: /expand form/i }));
    expect(form).not.toHaveClass("hidden");

    fireEvent.click(screen.getByRole("button", { name: /collapse form/i }));
    expect(form).toHaveClass("hidden");
  });

  it("cancel action calls POST /api/coding/work-orders/{id}/cancel", async () => {
    configureSuccessResponses([
      buildWorkOrder({
        status: "ready",
        title: "Cancelable order",
        work_order_id: "wo-cancelable",
      }),
    ]);

    render(<CodingWorkOrdersPanel />);

    const cancelButton = await screen.findByRole("button", {
      name: "Cancel wo-cancelable",
    });
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith(
        "/api/coding/work-orders/wo-cancelable/cancel",
        { reason: "operator_cancelled_from_command_center" }
      );
    });
  });

  it("refresh recommendations calls GET /api/coding/orchestrator/next", async () => {
    configureSuccessResponses([buildWorkOrder()]);

    render(<CodingWorkOrdersPanel />);
    await screen.findByText(/Recommendation one/);

    const refreshButton = screen.getByRole("button", {
      name: "Refresh recommendations",
    });
    fireEvent.click(refreshButton);

    await waitFor(() => {
      const recommendationCalls = apiGetMock.mock.calls.filter(
        ([url]) => url === "/api/coding/orchestrator/next"
      );
      expect(recommendationCalls.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("does not render a dispatch button or call dispatch endpoint", async () => {
    configureSuccessResponses([buildWorkOrder()]);

    render(<CodingWorkOrdersPanel />);
    await screen.findByText(/Recommendation one/);

    expect(
      screen.queryByRole("button", { name: /dispatch/i })
    ).not.toBeInTheDocument();
    const dispatchCalls = apiPostMock.mock.calls.filter(([url]) =>
      String(url).includes("/api/coding/orchestrator/dispatch")
    );
    expect(dispatchCalls).toHaveLength(0);
  });

  it("renders loading states while requests are in flight", async () => {
    const pendingWorkOrders = deferred<{
      data: {
        count: number;
        items: CommandCenterCodingWorkOrder[];
        limit: number;
        offset: number;
        ok: boolean;
      };
    }>();
    const pendingRecommendations = deferred<{
      data: CommandCenterOrchestratorNextResponse;
    }>();
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/api/coding/work-orders") return pendingWorkOrders.promise;
      if (url === "/api/coding/orchestrator/next") return pendingRecommendations.promise;
      throw new Error(`Unexpected GET ${url}`);
    });
    apiPostMock.mockResolvedValue({ data: { ok: true } });

    render(<CodingWorkOrdersPanel />);

    expect(await screen.findByText("Loading work orders…")).toBeInTheDocument();
    expect(screen.getByText("Loading recommendations…")).toBeInTheDocument();

    pendingWorkOrders.resolve({
      data: {
        count: 0,
        items: [],
        limit: 50,
        offset: 0,
        ok: true,
      },
    });
    pendingRecommendations.resolve({
      data: buildRecommendationResponse({
        recommendations: [],
        skipped: [],
      }),
    });
  });

  it("renders error states from failed API requests", async () => {
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/api/coding/work-orders") {
        return Promise.reject(new Error("work order request failed"));
      }
      if (url === "/api/coding/orchestrator/next") {
        return Promise.reject(new Error("recommendation request failed"));
      }
      throw new Error(`Unexpected GET ${url}`);
    });
    apiPostMock.mockResolvedValue({ data: { ok: true } });

    render(<CodingWorkOrdersPanel />);

    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
    expect(screen.getByTestId("coding-work-order-create-form")).toBeInTheDocument();
    expect(screen.getByTestId("coding-orchestrator-recommendations")).toBeInTheDocument();

    expect(
      await screen.findByText("work order request failed")
    ).toBeInTheDocument();
    expect(screen.getByText("recommendation request failed")).toBeInTheDocument();
  });

  it("renders summary chips with status counts", async () => {
    configureSuccessResponses([
      buildWorkOrder({ status: "ready", work_order_id: "wo-1" }),
      buildWorkOrder({ status: "running", work_order_id: "wo-2" }),
      buildWorkOrder({ status: "blocked", work_order_id: "wo-3" }),
      buildWorkOrder({ status: "merge_ready", work_order_id: "wo-4" }),
    ]);

    render(<CodingWorkOrdersPanel />);
    await screen.findAllByTestId("coding-work-order-row");

    expect(
      screen.getByText((_, node) => node?.textContent === "Total: 4")
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, node) => node?.textContent === "Ready: 1")
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, node) => node?.textContent === "Active-ish: 2")
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, node) => node?.textContent === "Blocked/escalated: 1")
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, node) => node?.textContent === "Merge-ready: 1")
    ).toBeInTheDocument();
  });
});
