import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GuardianScheduleAction from "@/features/chat/components/GuardianScheduleAction";
import { dispatchGuardianIntent } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>(
    "@/lib/api"
  );
  return {
    ...actual,
    dispatchGuardianIntent: vi.fn(),
  };
});

const dispatchGuardianIntentMock = vi.mocked(dispatchGuardianIntent);

describe("GuardianScheduleAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("validates required fields before review", async () => {
    const user = userEvent.setup();

    render(<GuardianScheduleAction />);

    await user.click(screen.getByRole("button", { name: "Review job" }));

    expect(await screen.findByText("Job name is required.")).toBeInTheDocument();
    expect(
      screen.getByText("Payload reference is required.")
    ).toBeInTheDocument();
    expect(dispatchGuardianIntentMock).not.toHaveBeenCalled();
  });

  test("shows a confirmation step and creates a durable noop job", async () => {
    const user = userEvent.setup();

    dispatchGuardianIntentMock.mockResolvedValue({
      status: "accepted",
      dispatch_target: "cron",
      downstream_result_json: {
        created_at: "2026-03-09T05:30:00Z",
        id: 42,
        is_enabled: true,
        job_type: "noop",
        name: "Daily pulse",
        payload: { reference: "status/daily-pulse" },
        schedule: "@daily",
        updated_at: "2026-03-09T05:30:00Z",
      },
    });

    render(<GuardianScheduleAction />);

    await user.type(screen.getByLabelText("Job name"), "Daily pulse");
    await user.type(
      screen.getByLabelText("Payload reference"),
      "status/daily-pulse"
    );
    await user.click(screen.getByRole("button", { name: "Review job" }));

    expect(await screen.findByText("Confirm scheduled job")).toBeInTheDocument();
    expect(screen.getByText("Daily pulse")).toBeInTheDocument();
    expect(screen.getByText("status/daily-pulse")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create durable job" }));

    await waitFor(() => {
      expect(dispatchGuardianIntentMock).toHaveBeenCalledWith({
        actor: { kind: "human", id: "local" },
        approval_state: "pending",
        intent_kind: "cron.create",
        policy: {
          approval_required: false,
          allow_write_execution: true,
          metadata: { action: "create_cron_job" },
        },
        provenance_json: {
          action: "create_cron_job",
          input: {
            isEnabled: true,
            jobType: "noop",
            name: "Daily pulse",
            payload: { reference: "status/daily-pulse" },
            schedule: "@daily",
          },
          source: "chat.schedule.action",
        },
        scope: {
          metadata: {
            action: "create_cron_job",
            source: "chat.schedule.action",
          },
        },
        source_surface: "chat",
        target: {
          is_enabled: true,
          job_type: "noop",
          name: "Daily pulse",
          payload: { reference: "status/daily-pulse" },
          schedule: "@daily",
        },
      });
    });

    expect(
      await screen.findByRole("status")
    ).toHaveTextContent("Created durable job #42 for schedule @daily.");
  });

  test("validates webhook targets before review", async () => {
    const user = userEvent.setup();

    render(<GuardianScheduleAction />);

    await user.type(screen.getByLabelText("Job name"), "Webhook ping");
    await user.selectOptions(screen.getByLabelText("Job type"), "webhook");
    await user.type(screen.getByLabelText("Webhook URL"), "ftp://example.com/hook");
    await user.click(screen.getByRole("button", { name: "Review job" }));

    expect(
      await screen.findByText("Webhook URL must begin with http:// or https://.")
    ).toBeInTheDocument();
    expect(screen.queryByText("Confirm scheduled job")).not.toBeInTheDocument();
  });

  test("supports a custom interval schedule and reports backend failures", async () => {
    const user = userEvent.setup();

    dispatchGuardianIntentMock.mockResolvedValue({
      status: "failed",
      dispatch_target: "cron",
      rejection_reason: "webhook target host is forbidden by default policy",
    });

    render(<GuardianScheduleAction />);

    await user.type(screen.getByLabelText("Job name"), "Webhook ping");
    await user.selectOptions(screen.getByLabelText("Job type"), "webhook");
    await user.selectOptions(screen.getByLabelText("Schedule"), "custom");
    await user.type(
      screen.getByLabelText("Custom schedule expression"),
      "*/15 * * * *"
    );
    await user.type(
      screen.getByLabelText("Webhook URL"),
      "https://api.example.com/hook"
    );
    await user.click(screen.getByRole("button", { name: "Review job" }));
    await user.click(screen.getByRole("button", { name: "Create durable job" }));

    await waitFor(() => {
      expect(dispatchGuardianIntentMock).toHaveBeenCalledWith({
        actor: { kind: "human", id: "local" },
        approval_state: "pending",
        intent_kind: "cron.create",
        policy: {
          approval_required: false,
          allow_write_execution: true,
          metadata: { action: "create_cron_job" },
        },
        provenance_json: {
          action: "create_cron_job",
          input: {
            isEnabled: true,
            jobType: "webhook",
            name: "Webhook ping",
            payload: { url: "https://api.example.com/hook" },
            schedule: "*/15 * * * *",
          },
          source: "chat.schedule.action",
        },
        scope: {
          metadata: {
            action: "create_cron_job",
            source: "chat.schedule.action",
          },
        },
        source_surface: "chat",
        target: {
          is_enabled: true,
          job_type: "webhook",
          name: "Webhook ping",
          payload: { url: "https://api.example.com/hook" },
          schedule: "*/15 * * * *",
        },
      });
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "webhook target host is forbidden by default policy"
    );
  });
});
