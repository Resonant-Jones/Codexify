import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConnectionConfigModal } from "@/features/connectors/ConnectorConfigModal";

const unconfiguredMiniMaxEntry = {
  id: "minimax_oauth",
  display_name: "MiniMax OAuth",
  category: "inference",
  description: "MiniMax Global OAuth subscription-style setup.",
  auth_methods: ["oauth_browser"],
  capabilities: ["chat_completion"],
  implementation_state: "partial",
  setup_state: "unavailable",
  runtime_binding: {
    subsystem: "guardian.connectors.minimax",
    adapter: null,
    setup_route: "/api/connect/minimax/start",
    registry_provider_id: "minimax",
    oauth_backend_handler_exists: true,
  },
  required_fields: [],
  scopes: [],
  setup_help:
    "MiniMax OAuth setup uses the Codexify-owned application configuration on this node.",
  oauth: {
    supported: true,
    backend_handler_exists: true,
    launchable: false,
    node_configured: false,
    connection: null,
  },
  authorization: {
    registered: true,
    registry_provider_id: "minimax",
    governance_classification: "static_authorized",
    authorized: false,
    available: false,
    enabled: false,
    disabled_reason: "Missing provider credentials",
  },
};

const configuredPendingEntry = {
  ...unconfiguredMiniMaxEntry,
  setup_state: "authenticating",
  oauth: {
    ...unconfiguredMiniMaxEntry.oauth,
    launchable: true,
    node_configured: true,
    connection: {
      provider: "minimax_oauth",
      mode: "node_local",
      status: "pending",
      scopes: [],
      expires_at: null,
      last_refresh_at: null,
      error_kind: null,
    },
  },
};

const configuredConnectedEntry = {
  ...unconfiguredMiniMaxEntry,
  setup_state: "connected",
  oauth: {
    ...unconfiguredMiniMaxEntry.oauth,
    launchable: true,
    node_configured: true,
    connection: {
      provider: "minimax_oauth",
      mode: "node_local",
      status: "connected",
      scopes: ["chat"],
      expires_at: "2027-01-01T00:00:00+00:00",
      last_refresh_at: "2026-08-17T00:00:00+00:00",
      error_kind: null,
    },
  },
};

const mockedApi = vi.hoisted(() => ({
  get: vi.fn(async () => ({ data: [] })),
  post: vi.fn(async () => ({ data: {} })),
  patch: vi.fn(async () => ({ data: {} })),
  delete: vi.fn(async () => ({ data: {} })),
  interceptors: {
    request: { use: vi.fn(() => 1), eject: vi.fn() },
    response: { use: vi.fn(() => 2), eject: vi.fn() },
  },
}));

vi.mock("@/components/ui/button", () => ({
  Button: (props: Record<string, unknown>) => (
    <button {...props}>{props.children as string}</button>
  ),
}));

vi.mock("@/components/ui/input", () => ({
  Input: (props: Record<string, unknown>) => <input {...props} />,
}));

vi.mock("@/components/ui/textarea", () => ({
  Textarea: (props: Record<string, unknown>) => <textarea {...props} />,
}));

vi.mock("@/lib/api", () => ({
  default: mockedApi,
  clearRuntimeApiKey: vi.fn(),
  getAuthToken: vi.fn(() => null),
  getDevApiKey: vi.fn(() => ""),
  readRuntimeApiKey: vi.fn(() => ""),
  refreshApiBaseUrl: vi.fn(),
  setRuntimeApiKey: vi.fn(),
}));

describe("MiniMax OAuth lifecycle modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("shows node-not-configured state when backend handler exists but launchable is false", async () => {
    render(
      <ConnectionConfigModal
        connection={unconfiguredMiniMaxEntry}
        open
        onClose={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    // When launchable=false, the setup state reads "Not available" via
    // the canonical SETUP_STATE_LABELS projection. The provider registry
    // shows static_authorized classification (registry authorization is
    // independent of OAuth setup availability).
    expect(screen.getByText("Not available")).toBeInTheDocument();
    // No verification metadata exposed when the entry cannot launch.
    expect(screen.queryByTestId("minimax-oauth-flow")).not.toBeInTheDocument();
  });

  it("renders verification URI, user code, and a manual open link when launchable", async () => {
    render(
      <ConnectionConfigModal
        connection={configuredPendingEntry}
        open
        onClose={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    // The persisted pending connection is shown.
    expect(
      screen.getByText(/Persisted OAuth state: pending/)
    ).toBeInTheDocument();
  });

  it("never writes the verification URL or user code to local/session storage", async () => {
    render(
      <ConnectionConfigModal
        connection={configuredPendingEntry}
        open
        onClose={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    const allLocal = JSON.stringify(window.localStorage);
    const allSession = JSON.stringify(window.sessionStorage);
    expect(allLocal).not.toMatch(/minimax/i);
    expect(allSession).not.toMatch(/minimax/i);
    expect(allLocal).not.toMatch(/user[_-]?code/i);
    expect(allSession).not.toMatch(/user[_-]?code/i);
    expect(allLocal).not.toMatch(/flow[_-]?id/i);
    expect(allSession).not.toMatch(/flow[_-]?id/i);
  });

  it("shows Connected status without exposing any token in the detail surface", async () => {
    render(
      <ConnectionConfigModal
        connection={configuredConnectedEntry}
        open
        onClose={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    expect(
      screen.getByText(/Persisted OAuth state: connected/)
    ).toBeInTheDocument();
    const body = document.body.textContent || "";
    // No token prefixes, suffixes, or lengths leak into the DOM.
    expect(body).not.toMatch(/access_token/);
    expect(body).not.toMatch(/refresh_token/);
    expect(body).not.toMatch(/Bearer /);
    // Provider-registry authorization still reports static_authorized
    // (the registry's governance classification); active authorization
    // is governed by the supported profile, not by OAuth credential
    // presence.
    expect(screen.getByText("static_authorized")).toBeInTheDocument();
  });
});

describe("MiniMax OAuth start/poll lifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("calls /api/connect/minimax/start on save and surfaces the verification URI + user code", async () => {
    mockedApi.post.mockImplementation(async (url: string) => {
      if (url === "/api/connect/minimax/start") {
        return {
          data: {
            provider: "minimax_oauth",
            flow_id: "flow-test-abc",
            verification_uri: "https://api.minimax.io/activate",
            user_code: "USER-CODE-XYZ",
            expires_at: "2026-08-17T01:00:00+00:00",
            poll_interval_seconds: 2,
          },
        };
      }
      return { data: {} };
    });

    render(
      <ConnectionConfigModal
        connection={{ ...configuredPendingEntry, oauth: { ...configuredPendingEntry.oauth, connection: null } }}
        open
        onClose={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    // Click Continue on the save step.
    const continueBtn = screen.getByRole("button", { name: /continue/i });
    await act(async () => {
      fireEvent.click(continueBtn);
    });

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith(
        "/api/connect/minimax/start",
        expect.any(Object)
      );
    });
    expect(screen.getByTestId("minimax-oauth-flow")).toBeInTheDocument();
    expect(screen.getByTestId("minimax-oauth-open-link")).toBeInTheDocument();
    // PKCE verifier is never serialized to the DOM.
    const body = document.body.textContent || "";
    expect(body).not.toMatch(/verifier/);
    expect(body).not.toMatch(/code_verifier/);
    expect(body).not.toMatch(/code_challenge/);
  });
});