import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConnectionConfigModal } from "@/features/connectors/ConnectorConfigModal";
import SettingsView from "@/features/settings/SettingsView";

const catalogPayload = {
  categories: ["messaging", "web", "inference", "knowledge"],
  items: [
    {
      id: "slack",
      display_name: "Slack",
      category: "messaging",
      description: "Outbound Slack channel delivery through the existing channel adapter.",
      auth_methods: ["token"],
      capabilities: ["outbound_messaging"],
      implementation_state: "implemented",
      setup_state: "unavailable",
      runtime_binding: {
        subsystem: "guardian.channels",
        adapter: "guardian.channels.adapters.slack.SlackAdapter",
        setup_route: null,
        registry_provider_id: null,
        oauth_backend_handler_exists: false,
      },
      required_fields: [],
      scopes: [],
      setup_help: "The adapter uses a server-managed environment credential.",
      oauth: null,
      authorization: null,
    },
    {
      id: "whatsapp",
      display_name: "WhatsApp",
      category: "messaging",
      description: "WhatsApp messaging. No Codexify adapter exists yet.",
      auth_methods: [],
      capabilities: [],
      implementation_state: "unimplemented",
      setup_state: "unavailable",
      runtime_binding: {
        subsystem: null,
        adapter: null,
        setup_route: null,
        registry_provider_id: null,
        oauth_backend_handler_exists: false,
      },
      required_fields: [],
      scopes: [],
      setup_help: "No Codexify messaging adapter exists for this platform yet.",
      oauth: null,
      authorization: null,
    },
    {
      id: "deepseek",
      display_name: "DeepSeek",
      category: "inference",
      description: "DeepSeek chat through the existing adapter.",
      auth_methods: ["api_key"],
      capabilities: ["chat_completion"],
      implementation_state: "implemented",
      setup_state: "needs_setup",
      runtime_binding: {
        subsystem: "guardian.core.provider_registry",
        adapter: null,
        setup_route: null,
        registry_provider_id: "deepseek",
        oauth_backend_handler_exists: false,
      },
      required_fields: [{ key: "api_key", label: "API key", type: "password", secret: true }],
      scopes: [],
      setup_help: "Inference provider configuration is server-owned.",
      oauth: null,
      authorization: {
        registered: true,
        registry_provider_id: "deepseek",
        governance_classification: "static_authorized",
        authorized: false,
        available: false,
        enabled: false,
        disabled_reason: "Missing provider credentials",
      },
    },
    {
      id: "firecrawl",
      display_name: "Firecrawl",
      category: "web",
      description: "Web search and page extraction through Firecrawl.",
      auth_methods: ["api_key"],
      capabilities: ["search", "extract"],
      implementation_state: "unimplemented",
      setup_state: "unavailable",
      runtime_binding: {
        subsystem: null,
        adapter: null,
        setup_route: null,
        registry_provider_id: null,
        oauth_backend_handler_exists: false,
      },
      required_fields: [],
      scopes: [],
      setup_help: "No Codexify web adapter exists for this provider yet.",
      oauth: null,
      authorization: null,
    },
    {
      id: "notion",
      display_name: "Notion",
      category: "knowledge",
      description: "Read-only Notion knowledge retrieval.",
      auth_methods: ["token"],
      capabilities: ["content_search", "content_read"],
      implementation_state: "implemented",
      setup_state: "needs_setup",
      runtime_binding: {
        subsystem: "guardian.connections.notion",
        adapter: "guardian.connections.notion.service.NotionClient",
        setup_route: "/api/connect/notion/configure",
        registry_provider_id: null,
        oauth_backend_handler_exists: false,
      },
      required_fields: [
        {
          key: "integration_token",
          label: "Notion integration token",
          type: "password",
          secret: true,
        },
      ],
      scopes: ["content_read"],
      setup_help: "Share the intended pages with the integration.",
      oauth: null,
      validation: {
        configured: false,
        state: "unconfigured",
        last_validated_at: null,
      },
      authorization: null,
    },
  ],
};

const mockedApi = vi.hoisted(() => ({
  get: vi.fn(async (url: string) => {
    if (url === "/api/connections") return { data: catalogPayload };
    return { data: [] };
  }),
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

vi.mock("@/components/controls/SegmentedThemeControl", () => ({
  default: () => <div data-testid="segmented-theme-control" />,
}));

vi.mock("@/features/connectors/useConnectors", () => ({
  useConnectors: () => ({
    connectors: [],
    updateConnector: vi.fn(),
    loading: false,
    error: null,
    authorizeOAuth: vi.fn(),
    testConnector: vi.fn(),
    syncConnector: vi.fn(),
  }),
}));

vi.mock("@/features/connectors/ConnectorCard", () => ({
  ConnectorCard: () => null,
}));

vi.mock("@/components/modals/ChatGPTImportModal", () => ({
  ChatGPTImportModal: () => null,
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getDesktopConnectionSettings: vi.fn(() => ({
    backendBaseUrl: "",
    sharePublicBaseUrl: "",
  })),
  initRuntimeConfig: vi.fn(async () => ({
    mode: "web",
    backendBaseUrl: "",
    apiBaseUrl: "/api",
    sseUrl: "/api/events",
    sharePublicBaseUrl: "",
    authMode: "local",
  })),
  invokeTauriCommand: vi.fn(),
  isTauriRuntime: vi.fn(() => false),
  openExternalUrl: vi.fn(async () => true),
  resolveBackendUrl: vi.fn((path: string) => path),
  saveDesktopConnectionSettings: vi.fn(async () => ({
    mode: "web",
    backendBaseUrl: "",
    apiBaseUrl: "/api",
    sseUrl: "/api/events",
    sharePublicBaseUrl: "",
    authMode: "local",
  })),
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

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  ensureRuntimeRouteCapabilitiesLoaded: vi.fn(),
  getRuntimeRouteCapabilityState: vi.fn(() => "available"),
  markRuntimeRouteUnavailableIfNotFound: vi.fn(),
  useRuntimeRouteCapabilities: () => ({
    ready: true,
    states: { imprint: "available", connectors: "available" },
  }),
}));

vi.mock("@/features/settings/api/persona", () => ({
  updatePersonaSettings: vi.fn(),
}));

function renderSettingsView() {
  return render(
    <SettingsView
      mode="light"
      setMode={vi.fn()}
      guardianName="Guardian"
      setGuardianName={vi.fn()}
      userName="User"
      setUserName={vi.fn()}
      role="Builder"
      setRole={vi.fn()}
      notes="Notes"
      setNotes={vi.fn()}
      baseColor="#111827"
      setBaseColor={vi.fn()}
      depth={0.3}
      setDepth={vi.fn()}
      fade={0.2}
      setFade={vi.fn()}
      resolved="light"
      systemPrompt="System prompt"
      setSystemPrompt={vi.fn()}
      wallpaper={null}
      setWallpaper={vi.fn()}
      extColors={{} as any}
      setExtColors={vi.fn()}
      dashboardThreadRows={2}
      setDashboardThreadRows={vi.fn()}
      surfaceDepth={0}
      setSurfaceDepth={vi.fn()}
      surfaceWarmth={0}
      setSurfaceWarmth={vi.fn()}
    />
  );
}

async function openConnectorsTab() {
  renderSettingsView();
  await act(async () => {
    fireEvent.click(screen.getByRole("tab", { name: /^connectors$/i }));
  });
  await waitFor(() => {
    expect(screen.getByTestId("connections-bay")).toBeInTheDocument();
  });
}

describe("Connections catalog bay", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("renders category navigation including Knowledge", async () => {
    await openConnectorsTab();

    for (const category of ["all", "messaging", "web", "inference", "knowledge"]) {
      expect(
        screen.getByTestId(`connections-category-${category}`)
      ).toBeInTheDocument();
    }
  });

  it("configures, validates, and disconnects Notion without browser secret storage", async () => {
    const notion = catalogPayload.items.find((item) => item.id === "notion")!;
    const changed = vi.fn();
    mockedApi.post
      .mockResolvedValueOnce({
        data: { validation: { state: "unvalidated" } },
      })
      .mockResolvedValueOnce({ data: { validation: { state: "valid" } } })
      .mockResolvedValueOnce({ data: { removed: true } });

    render(
      <ConnectionConfigModal
        connection={notion}
        open
        onClose={vi.fn()}
        onChanged={changed}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    const input = await screen.findByLabelText("Notion integration token");
    expect(input).toHaveAttribute("type", "password");
    fireEvent.change(input, { target: { value: "notion-browser-secret" } });
    fireEvent.click(screen.getByRole("button", { name: /^continue$/i }));

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith(
        "/api/connect/notion/configure",
        { settings: { integration_token: "notion-browser-secret" } }
      );
    });
    expect(window.localStorage.getItem("integration_token")).toBeNull();
    expect(window.sessionStorage.getItem("integration_token")).toBeNull();

    fireEvent.click(screen.getByTestId("notion-validate"));
    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith(
        "/api/connect/notion/validate",
        {}
      );
    });
    expect(screen.getByText(/Validation succeeded/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    fireEvent.click(screen.getByTestId("notion-disconnect"));
    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith(
        "/api/connect/notion/disconnect",
        {}
      );
    });
    expect(changed).toHaveBeenCalled();
  });

  it("does not advertise a browser setup flow for server-managed messaging credentials", async () => {
    await openConnectorsTab();

    const slackRow = screen.getByTestId("connection-row-slack");
    expect(within(slackRow).getByText("Implemented")).toBeInTheDocument();
    const configure = within(slackRow).getByRole("button", {
      name: /^configure$/i,
    });
    expect(configure).toBeDisabled();
  });

  it("keeps the setup wizard on the save step after a failed save", async () => {
    mockedApi.post.mockResolvedValueOnce({ data: { error: "save failed" } });
    const connection = {
      id: "test-connection",
      display_name: "Test connection",
      category: "inference",
      description: "A launchable test connection.",
      auth_methods: ["api_key"],
      capabilities: ["chat_completion"],
      implementation_state: "implemented",
      setup_state: "needs_setup",
      runtime_binding: {
        subsystem: "test",
        adapter: null,
        setup_route: "/api/test-connections",
        registry_provider_id: null,
        oauth_backend_handler_exists: false,
      },
      required_fields: [],
      scopes: [],
      setup_help: "Test setup.",
      oauth: null,
      authorization: null,
    };

    render(
      <ConnectionConfigModal
        connection={connection}
        open
        onClose={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /^continue$/i }));

    await waitFor(() => {
      expect(screen.getByText("save failed")).toBeInTheDocument();
    });
    expect(screen.queryByText("Configuration saved.")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^continue$/i })
    ).toBeDisabled();
  });

  it("marks unsupported entries as not implemented and disables setup", async () => {
    await openConnectorsTab();

    const whatsappRow = screen.getByTestId("connection-row-whatsapp");
    expect(
      within(whatsappRow).getByText("Not implemented")
    ).toBeInTheDocument();
    const configure = within(whatsappRow).getByRole("button", {
      name: /^configure$/i,
    });
    expect(configure).toBeDisabled();

    fireEvent.click(
      within(whatsappRow).getByRole("button", {
        name: /show whatsapp details/i,
      })
    );
    await waitFor(() => {
      expect(screen.getByTestId("connection-setup-unavailable")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Setup is not yet available for this connection\./)
    ).toBeInTheDocument();
  });

  it("shows DeepSeek as API-key only, never OAuth", async () => {
    await openConnectorsTab();

    const deepseekRow = screen.getByTestId("connection-row-deepseek");
    fireEvent.click(
      within(deepseekRow).getByRole("button", {
        name: /show deepseek details/i,
      })
    );
    await waitFor(() => {
      expect(screen.getByTestId("connection-detail")).toBeInTheDocument();
    });
    const detail = screen.getByTestId("connection-detail");
    expect(within(detail).getByText(/API key/)).toBeInTheDocument();
    expect(within(detail).queryByText(/OAuth/)).not.toBeInTheDocument();
    expect(within(detail).getByText("not authorized")).toBeInTheDocument();
  });

  it("filters rows by search", async () => {
    await openConnectorsTab();

    fireEvent.change(screen.getByLabelText("Search connections"), {
      target: { value: "whatsapp" },
    });

    await waitFor(() => {
      expect(
        screen.queryByTestId("connection-row-slack")
      ).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("connection-row-whatsapp")).toBeInTheDocument();
  });

  it("does not merge adapter, setup, and registry truth into one dot", async () => {
    await openConnectorsTab();

    const deepseekRow = screen.getByTestId("connection-row-deepseek");
    expect(within(deepseekRow).getByText("Adapter")).toBeInTheDocument();
    expect(within(deepseekRow).getByText("Setup")).toBeInTheDocument();
    expect(within(deepseekRow).getByText("Registry")).toBeInTheDocument();
  });
});
