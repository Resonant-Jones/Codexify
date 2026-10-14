import { StrictMode } from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { AxiosError, type AxiosResponse } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ConfigurationInspectorView from "./ConfigurationInspectorView";
import type { ConfigurationSnapshot } from "./contracts";

const mockedApi = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", () => ({ default: mockedApi }));

function snapshot(): ConfigurationSnapshot {
  return {
    schema_version: 1,
    generated_at: "2026-09-30T12:00:00Z",
    process: { service: "guardian", process_id: 1234, scope: "responding_guardian_process" },
    supported_profile: {
      evidence: "resolved", owner: "guardian.core.supported_profile",
      profile_name: "v1-local-core-web-mcp", version: 1, surface_class: "web-mcp",
      valid: true, unavailable_reason: null,
    },
    mounted_routes: {
      evidence: "observed", owner: "guardian.guardian_api._refresh_supported_profile_state",
      route_families: ["chat", "health", "admin"],
      interpretation: "mounted_only_not_authorization_health_or_release_support", unavailable_reason: null,
    },
    provider_egress: {
      evidence: "resolved", owner: "guardian.core.config.Settings+guardian.core.egress",
      configured_provider_class: "local", local_only_mode: true,
      cloud_providers_allowed: false, egress_allowlist_configured: false, unavailable_reason: null,
    },
    local_inference: {
      evidence: "declared", owner: "guardian.core.provider_registry.default_model_for_provider",
      provider_class: "local", configured_target: "local-chat", unavailable_reason: null,
    },
  };
}

function denied(status: number) {
  return new AxiosError("private exception body", undefined, undefined, undefined,
    { status, data: { detail: "private response body" } } as AxiosResponse);
}

describe("ConfigurationInspectorView", () => {
  beforeEach(() => {
    mockedApi.get.mockReset().mockResolvedValue({ data: snapshot() });
  });

  it("projects the four backend sections, process metadata, owners and evidence", async () => {
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(await screen.findByText("responding_guardian_process")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Configuration Inspector" })).toBeInTheDocument();
    expect(screen.getByText("1234")).toBeInTheDocument();
    expect(screen.getByText("2026-09-30T12:00:00Z")).toBeInTheDocument();
    const profile = within(screen.getByRole("region", { name: "Supported Profile" }));
    expect(profile.getByText("v1-local-core-web-mcp")).toBeInTheDocument();
    expect(profile.getByText("1")).toBeInTheDocument();
    expect(profile.getByText("web-mcp")).toBeInTheDocument();
    expect(profile.getByText("Valid profile posture").nextElementSibling).toHaveTextContent("Yes");
    const routes = within(screen.getByRole("region", { name: "Mounted Routes" }));
    for (const route of ["chat", "health", "admin"]) expect(routes.getByText(route)).toBeInTheDocument();
    const provider = within(screen.getByRole("region", { name: "Provider & Egress" }));
    expect(provider.getByText("Configured provider class").nextElementSibling).toHaveTextContent("local");
    for (const [label, value] of [["Local-only mode", "Yes"], ["Cloud providers allowed", "No"], ["Egress allowlist configured", "No"]]) {
      expect(provider.getByText(label).nextElementSibling).toHaveTextContent(value);
    }
    const local = within(screen.getByRole("region", { name: "Local Inference" }));
    expect(local.getByText("Configured target").nextElementSibling).toHaveTextContent("local-chat");
    expect(local.getByText("Provider class").nextElementSibling).toHaveTextContent("local");
    for (const section of [snapshot().supported_profile, snapshot().mounted_routes, snapshot().provider_egress, snapshot().local_inference]) {
      expect(screen.getByText(section.owner)).toBeInTheDocument();
    }
    expect(screen.getAllByText("Resolved")).toHaveLength(2);
    expect(screen.getByText("Observed")).toBeInTheDocument();
    expect(screen.getByText("Declared")).toBeInTheDocument();
    expect(mockedApi.get).toHaveBeenCalledExactlyOnceWith("/api/operator/configuration");
  });

  it("keeps configuration, health, authority and served-model meaning separate", async () => {
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    await screen.findByText("local-chat");
    expect(screen.getByText(/Read-only installation\/operator posture, reflecting the responding Guardian process/)).toBeInTheDocument();
    expect(screen.getByText("Configuration evidence is separate from runtime health and release support.")).toBeInTheDocument();
    expect(screen.getByText("Mounted only — not authorization, health, or release support.")).toBeInTheDocument();
    expect(screen.queryByText(/effective model|active model|running model|served model/i)).not.toBeInTheDocument();
  });

  it.each([
    ["supported_profile", "supported_profile_state_unavailable", "Supported profile state unavailable."],
    ["mounted_routes", "mounted_route_inventory_unavailable", "Mounted route inventory unavailable."],
    ["provider_egress", "provider_egress_posture_unavailable", "Provider / egress posture unavailable."],
    ["local_inference", "local_inference_target_unavailable", "Local inference target unavailable."],
  ] as const)("translates %s unavailability without rendering its stale values", async (key, reason, message) => {
    const data = snapshot();
    const section = data[key];
    Object.assign(section, { evidence: "unavailable", unavailable_reason: reason });
    mockedApi.get.mockResolvedValue({ data });
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText(section.owner)).toBeInTheDocument();
    const card = screen.getByText(section.owner).closest("section")!;
    expect(within(card).queryByRole("list")).not.toBeInTheDocument();
    expect(card.querySelector("dl")).toBeNull();
    expect(mockedApi.get).toHaveBeenCalledTimes(1);
  });

  it.each([401, 403])("bounds operator denial (%s)", async (status) => {
    mockedApi.get.mockRejectedValue(denied(status));
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(await screen.findByText("Operator access required")).toBeInTheDocument();
    expect(screen.getByText("This view requires Guardian operator authority.")).toBeInTheDocument();
    expect(screen.queryByText("local-chat")).not.toBeInTheDocument();
    expect(screen.queryByText(/private/)).not.toBeInTheDocument();
  });

  it("bounds route unavailability without probing alternatives", async () => {
    mockedApi.get.mockRejectedValue(denied(404));
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(await screen.findByText("Configuration Inspector unavailable in this runtime profile")).toBeInTheDocument();
    expect(mockedApi.get).toHaveBeenCalledExactlyOnceWith("/api/operator/configuration");
  });

  it("allows manual retry after a bounded generic failure", async () => {
    mockedApi.get.mockRejectedValueOnce(denied(500));
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(await screen.findByText("Unable to load configuration snapshot")).toBeInTheDocument();
    expect(screen.queryByText(/private/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByText("local-chat")).toBeInTheDocument();
    expect(mockedApi.get).toHaveBeenCalledTimes(2);
  });

  it.each([
    ["wrong version", (data: Record<string, unknown>) => { data.schema_version = 2; }],
    ...["process", "supported_profile", "mounted_routes", "provider_egress", "local_inference"].map((key) =>
      [`missing ${key}`, (data: Record<string, unknown>) => { delete data[key]; }] as const),
    ...["supported_profile", "mounted_routes", "provider_egress", "local_inference"].map((key) =>
      [`invalid ${key} evidence`, (data: Record<string, unknown>) => { (data[key] as Record<string, unknown>).evidence = "healthy"; }] as const),
    ["missing value", (data: Record<string, unknown>) => { delete (data.local_inference as Record<string, unknown>).configured_target; }],
    ["wrong boolean", (data: Record<string, unknown>) => { (data.provider_egress as Record<string, unknown>).local_only_mode = "true"; }],
    ["invalid route interpretation", (data: Record<string, unknown>) => { (data.mounted_routes as Record<string, unknown>).interpretation = "healthy"; }],
    ["invalid timestamp", (data: Record<string, unknown>) => { data.generated_at = "unknown"; }],
    ["unknown reason", (data: Record<string, unknown>) => { (data.local_inference as Record<string, unknown>).unavailable_reason = "private body"; }],
  ] as const)("fails closed on %s", async (_label, mutate) => {
    const data = snapshot() as unknown as Record<string, unknown>;
    mutate(data);
    mockedApi.get.mockResolvedValue({ data });
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(await screen.findByText("Unable to load configuration snapshot")).toBeInTheDocument();
    expect(screen.queryByText("local-chat")).not.toBeInTheDocument();
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("loads once in StrictMode, refreshes once, clears old data, and never polls", async () => {
    vi.useFakeTimers();
    try {
      render(<StrictMode><ConfigurationInspectorView onBackToSettings={vi.fn()} /></StrictMode>);
      await act(async () => {});
      expect(screen.getByText("local-chat")).toBeInTheDocument();
      expect(mockedApi.get).toHaveBeenCalledTimes(1);
      await act(async () => { vi.advanceTimersByTime(120_000); });
      expect(mockedApi.get).toHaveBeenCalledTimes(1);
      let resolve!: (value: { data: ConfigurationSnapshot }) => void;
      mockedApi.get.mockReturnValueOnce(new Promise((done) => { resolve = done; }));
      fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
      expect(screen.queryByText("local-chat")).not.toBeInTheDocument();
      expect(screen.getByText("Loading configuration snapshot…")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();
      expect(mockedApi.get).toHaveBeenCalledTimes(2);
      await act(async () => { resolve({ data: snapshot() }); });
      await act(async () => { vi.advanceTimersByTime(120_000); });
      expect(mockedApi.get).toHaveBeenCalledTimes(2);
    } finally { vi.useRealTimers(); }
  });

  it("reuses the opening request across compositor remounts, including after Refresh", async () => {
    const request = { current: null as Promise<ConfigurationSnapshot> | null };
    const mount = () => render(<ConfigurationInspectorView onBackToSettings={vi.fn()} snapshotRequest={request} />);
    let view = mount();
    await screen.findByText("local-chat");
    expect(mockedApi.get).toHaveBeenCalledTimes(1);
    view.unmount();
    view = mount();
    await screen.findByText("local-chat");
    expect(mockedApi.get).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await screen.findByText("local-chat");
    expect(mockedApi.get).toHaveBeenCalledTimes(2);
    view.unmount();
    view = mount();
    await screen.findByText("local-chat");
    expect(mockedApi.get).toHaveBeenCalledTimes(2);
    view.unmount();
    request.current = null; // AppShell clears this reference when leaving the Inspector.
    mount();
    await screen.findByText("local-chat");
    expect(mockedApi.get).toHaveBeenCalledTimes(3);
  });

  it("keeps the loading shell without placeholder configuration values", () => {
    mockedApi.get.mockReturnValue(new Promise(() => {}));
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Configuration Inspector" })).toBeInTheDocument();
    expect(screen.getByText("Loading configuration snapshot…")).toBeInTheDocument();
    expect(screen.queryByText("local-chat")).not.toBeInTheDocument();
  });

  it("contains only Refresh and Back actions, with no edit controls", async () => {
    const back = vi.fn();
    const { container } = render(<ConfigurationInspectorView onBackToSettings={back} />);
    await screen.findByText("local-chat");
    expect(container.querySelectorAll("input, select, textarea, [role=switch], [role=slider], [contenteditable=true]")).toHaveLength(0);
    expect(screen.getAllByRole("button").map((button) => button.textContent)).toEqual(["Back to Settings", "Refresh"]);
    expect(screen.queryByRole("button", { name: /save|apply/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back to Settings" }));
    expect(back).toHaveBeenCalledOnce();
  });

  it("ignores extra secret/account data rather than rendering arbitrary response fields", async () => {
    mockedApi.get.mockResolvedValue({ data: { ...snapshot(), account_id: "private-account", credential: "private-credential" } });
    render(<ConfigurationInspectorView onBackToSettings={vi.fn()} />);
    await screen.findByText("local-chat");
    expect(screen.queryByText(/private-/)).not.toBeInTheDocument();
  });
});
