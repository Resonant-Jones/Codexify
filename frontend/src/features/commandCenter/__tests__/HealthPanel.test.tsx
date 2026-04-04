import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HealthPanel from "../components/HealthPanel";
import { interpretHealthPayload } from "../hooks/useHealthSummary";

import type { CommandCenterHealthItem } from "@/features/commandCenter/types";
import { COMMAND_CENTER_HEALTH_STATES } from "@/features/commandCenter/types";

const onRefresh = vi.fn(async () => undefined);

const healthItems: CommandCenterHealthItem[] = [
  {
    checkedAt: Date.parse("2026-04-01T15:59:00Z"),
    details: {
      service: "core",
      status: "ok",
      timestamp: "2026-04-01T15:59:00Z",
    },
    endpoint: "/health",
    error: null,
    httpStatus: 200,
    key: "core",
    label: "Core",
    raw: JSON.stringify({
      details: { note: "ready" },
      service: "core",
      status: "ok",
      timestamp: "2026-04-01T15:59:00Z",
    }),
    status: COMMAND_CENTER_HEALTH_STATES.OK,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:01Z"),
    details: {
      service: "llm",
      status: "degraded",
      timestamp: "2026-04-01T15:59:01Z",
    },
    endpoint: "/health/llm",
    error: null,
    httpStatus: 200,
    key: "llm",
    label: "LLM",
    raw: JSON.stringify({
      details: { reason: "cache warm" },
      service: "llm",
      status: "degraded",
      timestamp: "2026-04-01T15:59:01Z",
    }),
    status: COMMAND_CENTER_HEALTH_STATES.DEGRADED,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:02Z"),
    details: null,
    endpoint: "/health/deps",
    error: "Invalid health response",
    httpStatus: 200,
    key: "deps",
    label: "Deps",
    raw: "<!DOCTYPE html><html><body>frontend shell</body></html>",
    status: COMMAND_CENTER_HEALTH_STATES.UNKNOWN,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:03Z"),
    details: {
      error: "queue probe failed",
      service: "vector",
      status: "down",
      timestamp: "2026-04-01T15:59:03Z",
    },
    endpoint: "/health/vector",
    error: "HTTP 503",
    httpStatus: 503,
    key: "vector",
    label: "Vector",
    raw: JSON.stringify({
      details: { error: "queue probe failed" },
      service: "vector",
      status: "down",
      timestamp: "2026-04-01T15:59:03Z",
    }),
    status: COMMAND_CENTER_HEALTH_STATES.DOWN,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:04Z"),
    details: {
      counts: { ephemeral: 0, longterm: 0, midterm: 0 },
      ok: true,
      service: "memory",
      status: "ok",
      timestamp: "2026-04-01T15:59:04Z",
    },
    endpoint: "/health/memory",
    error: null,
    httpStatus: 200,
    key: "memory",
    label: "Memory",
    raw: JSON.stringify({
      counts: { ephemeral: 0, longterm: 0, midterm: 0 },
      service: "memory",
      status: "ok",
      timestamp: "2026-04-01T15:59:04Z",
    }),
    status: COMMAND_CENTER_HEALTH_STATES.OK,
  },
];

describe("HealthPanel", () => {
  it("renders normalized status badges and keeps raw payloads collapsed by default", () => {
    render(
      <HealthPanel
        healthItems={healthItems}
        lastCheckedAt={Date.parse("2026-04-01T15:59:04Z")}
        loading={false}
        onRefresh={onRefresh}
      />
    );

    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
    expect(
      within(screen.getByTestId("command-center-health-core")).getByText("OK")
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("command-center-health-llm")).getByText("Degraded")
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("command-center-health-deps")).getByText("Unknown")
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("command-center-health-vector")).getByText("Down")
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("command-center-health-memory")).getByText("OK")
    ).toBeInTheDocument();

    const depsCard = screen.getByTestId("command-center-health-deps");
    const collapsedRaw = within(depsCard).getByText(
      "<!DOCTYPE html><html><body>frontend shell</body></html>"
    );
    expect(collapsedRaw).not.toBeVisible();

    fireEvent.click(within(depsCard).getByText("Inspect raw details"));
    expect(collapsedRaw).toBeVisible();

    expect(within(screen.getByTestId("command-center-health-core")).getByText("Core")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-health-llm")).getByText("LLM")).toBeInTheDocument();
  });

  it("treats HTML and empty payloads as invalid health responses", () => {
    expect(
      interpretHealthPayload(
        "<!DOCTYPE html><html><body>frontend shell</body></html>"
      )
    ).toMatchObject({
      error: "Invalid health response",
      status: COMMAND_CENTER_HEALTH_STATES.UNKNOWN,
    });

    expect(interpretHealthPayload("")).toMatchObject({
      error: "Invalid health response",
      status: COMMAND_CENTER_HEALTH_STATES.UNKNOWN,
    });
  });

  it("interprets semantic health payloads without falling back to UNKNOWN", () => {
    expect(
      interpretHealthPayload(
        JSON.stringify({
          details: {},
          service: "core",
          status: "ok",
          timestamp: "2026-04-01T15:59:00Z",
        })
      )
    ).toMatchObject({
      error: null,
      status: COMMAND_CENTER_HEALTH_STATES.OK,
    });

    expect(
      interpretHealthPayload(
        JSON.stringify({
          details: {},
          service: "llm",
          status: "degraded",
          timestamp: "2026-04-01T15:59:00Z",
        })
      )
    ).toMatchObject({
      error: null,
      status: COMMAND_CENTER_HEALTH_STATES.DEGRADED,
    });

    expect(
      interpretHealthPayload(
        JSON.stringify({
          details: {},
          service: "vector",
          status: "down",
          timestamp: "2026-04-01T15:59:00Z",
        })
      )
    ).toMatchObject({
      error: null,
      status: COMMAND_CENTER_HEALTH_STATES.DOWN,
    });
  });
});
