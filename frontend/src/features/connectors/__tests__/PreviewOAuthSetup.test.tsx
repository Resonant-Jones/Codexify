import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";

import { canLaunchSetup, type ConnectionEntry } from "../connectionCatalog";
import { ConnectionConfigModal } from "../ConnectorConfigModal";

vi.mock("@/lib/api", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));

function setupEntry(id: "notion" | "github_knowledge"): ConnectionEntry {
  const provider = id === "notion" ? "notion" : "github-knowledge";
  return {
    id,
    display_name: id === "notion" ? "Notion" : "GitHub Knowledge",
    category: "knowledge",
    description: "Account-owned setup; read operations remain quarantined.",
    auth_methods: ["oauth_browser"],
    capabilities: ["content_search", "content_read"],
    implementation_state: "experimental",
    setup_state: "needs_setup",
    runtime_binding: {
      subsystem: "guardian.connections",
      adapter: null,
      setup_route: `/api/connect/${provider}/oauth/start`,
      registry_provider_id: null,
      oauth_backend_handler_exists: true,
    },
    required_fields: [],
    scopes: ["content_search", "content_read"],
    setup_help: "Authorization does not enable Preview invocation.",
    oauth: {
      supported: true,
      backend_handler_exists: true,
      launchable: true,
      node_configured: true,
      connection: null,
    },
    authorization: {
      registered: true,
      available: true,
      note: "Setup only; Guardian invocation remains unavailable in Preview.",
    },
  };
}

const flush = async () => act(async () => { await Promise.resolve(); });

describe("Preview setup-only catalog admission", () => {
  beforeEach(() => { vi.resetAllMocks(); vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it.each(["notion", "github_knowledge"] as const)(
    "opens %s OAuth setup without legacy token or read requests",
    async (id) => {
      const entry = setupEntry(id);
      const provider = id === "notion" ? "notion" : "github-knowledge";
      const label = id === "notion" ? "Notion" : "GitHub";
      expect(canLaunchSetup(entry)).toBe(true);
      const popup = { close: vi.fn(), closed: false, location: { href: "" }, opener: null };
      vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
      vi.mocked(api.get).mockResolvedValue({ data: { available: true, configured: false } });
      vi.mocked(api.post).mockResolvedValue({ data: {
        authorization_url: id === "notion"
          ? "https://api.notion.com/v1/oauth/authorize?state=synthetic"
          : "https://github.com/login/oauth/authorize?state=synthetic",
        generation: "synthetic-generation",
      } });
      render(<ConnectionConfigModal connection={entry} open onClose={vi.fn()} onChanged={vi.fn()} />);
      await flush();
      expect(api.get).toHaveBeenCalledExactlyOnceWith(`/api/connect/${provider}/oauth/status`);
      expect(screen.queryByLabelText(/token|secret|api key/i)).toBeNull();
      fireEvent.click(screen.getByRole("button", { name: `Connect ${label}` }));
      await flush();
      expect(api.post).toHaveBeenCalledExactlyOnceWith(`/api/connect/${provider}/oauth/start`, {});
      expect(api.put).not.toHaveBeenCalled();
      fireEvent.click(screen.getByRole("button", { name: "Close" }));
      await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
      expect(api.get).toHaveBeenCalledTimes(1);
      expect(popup.close).toHaveBeenCalled();
    },
  );

  it.each(["notion", "github_knowledge"] as const)(
    "keeps %s unavailable when operator configuration is missing",
    async (id) => {
      const entry = setupEntry(id);
      entry.setup_state = "unavailable";
      entry.oauth = { ...entry.oauth!, launchable: false, node_configured: false };
      expect(canLaunchSetup(entry)).toBe(false);
      vi.mocked(api.get).mockResolvedValue({ data: { available: false, configured: false } });
      render(<ConnectionConfigModal connection={entry} open onClose={vi.fn()} onChanged={vi.fn()} />);
      await flush();
      expect(screen.getByRole("button", { name: /^Connect / })).toBeDisabled();
      expect(api.post).not.toHaveBeenCalled();
      expect(api.put).not.toHaveBeenCalled();
    },
  );
});
