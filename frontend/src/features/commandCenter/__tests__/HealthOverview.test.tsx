import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import HealthOverview from "../components/HealthOverview";
import {
  COMMAND_CENTER_HEALTH_STATES,
  type CommandCenterHealthItem,
  type CommandCenterHealthState,
} from "../types";

// ── Test fixtures ────────────────────────────────────────────────────────

function healthItem(
  key: CommandCenterHealthItem["key"],
  status: CommandCenterHealthState,
  details?: Record<string, unknown> | null
): CommandCenterHealthItem {
  return {
    checkedAt: Date.now(),
    endpoint: `/health/${key === "core" ? "" : key}`,
    error: null,
    httpStatus: 200,
    key,
    label: key.charAt(0).toUpperCase() + key.slice(1),
    details: details ?? null,
    raw: details ? JSON.stringify(details) : null,
    status,
  };
}

function healthyCoreDetails(): Record<string, unknown> {
  return {
    status: "ok",
    supported_profile: {
      name: "v1-local-core-web-mcp",
      version: 1,
      surface: "local-docker-compose-webui",
      valid: true,
      mismatches: [],
      selected_provider: "local",
      selected_provider_supported: true,
      cloud_capable_configuration_present: false,
      release_hold: false,
      expected_provider: "local",
    },
    release_hold: false,
  };
}

function healthyLlmDetails(): Record<string, unknown> {
  return {
    status: "ok",
    provider_truth: {
      configured: true,
      authorized: true,
      discovered_inventory: true,
      discoverable: true,
      selectable: true,
      executable: true,
      egress_allowed: true,
      supported_profile_name: "v1-local-core-web-mcp",
      supported_profile_valid: true,
      supported_profile_mismatches: [],
      supported_profile_approved: true,
      cloud_capable_configuration_present: false,
      attempted: false,
      executed: false,
      completed: false,
    },
    configured_model: "mlx-community/Llama-3.2-3B-Instruct-4bit",
    configured_model_available: true,
    model_resolution: {
      strict: true,
      source: "whooshd_model_profile",
      model: "mlx-community/Llama-3.2-3B-Instruct-4bit",
      advertised_models: ["mlx-community/Llama-3.2-3B-Instruct-4bit"],
    },
  };
}

function allHealthyItems(): CommandCenterHealthItem[] {
  return [
    healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
    healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, healthyLlmDetails()),
  ];
}

const noopRefresh = vi.fn().mockResolvedValue(undefined);

// ── Tests ────────────────────────────────────────────────────────────────

describe("HealthOverview run verdict", () => {
  it("renders a go verdict when all required surfaces agree", () => {
    render(
      <HealthOverview
        healthItems={allHealthyItems()}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");
    expect(verdict).toBeDefined();
    expect(verdict.getAttribute("aria-label")).toContain("Go");
    expect(screen.getByText("Can I run?")).toBeDefined();
  });

  it("renders proof_needed for the C00-style configured model mismatch", () => {
    const llmDetails = healthyLlmDetails();
    llmDetails.configured_model_available = false;
    llmDetails.model_resolution = {
      strict: true,
      source: "whooshd_model_profile",
      model: "mlx-community/gemma-4-e2b-it-4bit",
      failure_kind: "configured_model_not_advertised_by_whooshd",
      advertised_models: ["mlx-community/Llama-3.2-3B-Instruct-4bit"],
    };
    llmDetails.configured_model = "mlx-community/gemma-4-e2b-it-4bit";

    render(
      <HealthOverview
        healthItems={[
          healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
          healthItem("llm", COMMAND_CENTER_HEALTH_STATES.DOWN, llmDetails),
        ]}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");
    expect(verdict.getAttribute("aria-label")).toContain("Proof needed");
    expect(screen.getByTestId("run-verdict-blockers")).toBeDefined();
  });

  it("renders proof_needed when required catalog or model inventory evidence is missing", () => {
    render(
      <HealthOverview
        healthItems={allHealthyItems()}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={false}
        modelInventoryAvailable={true}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");
    expect(verdict.getAttribute("aria-label")).toContain("Proof needed");
  });

  it("renders degraded when non-critical observability is degraded but core surfaces are healthy", () => {
    render(
      <HealthOverview
        healthItems={[
          healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
          healthItem(
            "llm",
            COMMAND_CENTER_HEALTH_STATES.DEGRADED,
            healthyLlmDetails()
          ),
        ]}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");
    expect(verdict.getAttribute("aria-label")).toContain("Degraded");
  });

  it("renders hold for explicit release/support contradiction", () => {
    const invalidCore = healthyCoreDetails();
    (invalidCore.supported_profile as Record<string, unknown>).valid = false;

    render(
      <HealthOverview
        healthItems={[
          healthItem("core", COMMAND_CENTER_HEALTH_STATES.DEGRADED, invalidCore),
          healthItem("llm", COMMAND_CENTER_HEALTH_STATES.OK, healthyLlmDetails()),
        ]}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");
    expect(verdict.getAttribute("aria-label")).toContain("Hold");
  });

  it("does not render go from /health ok alone", () => {
    render(
      <HealthOverview
        healthItems={[
          healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
        ]}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");
    expect(verdict.getAttribute("aria-label")).not.toContain("Go");
  });

  it("displays evidence and blocker counts the operator can inspect", () => {
    const llmDetails = healthyLlmDetails();
    llmDetails.configured_model_available = false;
    llmDetails.model_resolution = {
      strict: true,
      source: "whooshd_model_profile",
      model: "mlx-community/gemma-4-e2b-it-4bit",
      failure_kind: "configured_model_not_advertised_by_whooshd",
      advertised_models: ["mlx-community/Llama-3.2-3B-Instruct-4bit"],
    };
    llmDetails.configured_model = "mlx-community/gemma-4-e2b-it-4bit";

    render(
      <HealthOverview
        healthItems={[
          healthItem("core", COMMAND_CENTER_HEALTH_STATES.OK, healthyCoreDetails()),
          healthItem("llm", COMMAND_CENTER_HEALTH_STATES.DOWN, llmDetails),
        ]}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    // Evidence count is always visible
    const evidenceEl = screen.getByTestId("run-verdict-evidence");
    expect(evidenceEl).toBeDefined();
    expect(evidenceEl.textContent).toContain("Evidence:");

    // Blocker count visible when blockers exist
    const blockersEl = screen.getByTestId("run-verdict-blockers");
    expect(blockersEl).toBeDefined();
    expect(blockersEl.textContent).toContain("Blockers:");
  });

  it("does not render mutation controls in the verdict block", () => {
    render(
      <HealthOverview
        healthItems={allHealthyItems()}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    const verdict = screen.getByTestId("command-center-run-verdict");

    // No buttons inside the verdict block
    const buttons = verdict.querySelectorAll("button");
    expect(buttons.length).toBe(0);

    // No links inside the verdict block
    const links = verdict.querySelectorAll("a");
    expect(links.length).toBe(0);
  });

  it("renders no blocker count when verdict has no blockers", () => {
    render(
      <HealthOverview
        healthItems={allHealthyItems()}
        lastCheckedAt={Date.now()}
        loading={false}
        onRefresh={noopRefresh}
        catalogAvailable={true}
        modelInventoryAvailable={true}
      />
    );

    // Blocker element should not be present when there are no blockers
    const blockersEl = screen.queryByTestId("run-verdict-blockers");
    expect(blockersEl).toBeNull();
  });
});
