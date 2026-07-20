import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import api, { buildAuthenticatedFetchInit, setAuthToken } from "@/lib/api";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
  getAuthState,
  resolveAuthStateOnBoot,
} from "@/lib/authState";
import { __resetRuntimeApiKeyForTests } from "@/lib/runtimeAuth";

import LoginPage from "../login/LoginPage";

const runtimeModeState = vi.hoisted(() => ({
  authMode: "remote" as "local" | "remote",
}));

const locationState = vi.hoisted(() => ({
  assign: vi.fn(),
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getRuntimeConfigSync: () => ({
    authMode: runtimeModeState.authMode,
  }),
  resolveApiUrl: (path: string) => path,
}));

const SESSION_TOKEN_STORAGE_KEY = "guardian.auth.token";
const LOCAL_BODY_COPY =
  "Sign in to enter your local workspace. Your session and workspace data remain on this device.";
const REMOTE_BODY_COPY =
  "Sign in to enter your Codexify workspace. This browser will receive a private session token for the active session.";

function normalizeHeaders(
  headers: RequestInit["headers"]
): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) {
    const normalized: Record<string, string> = {};
    headers.forEach((value, key) => {
      normalized[key] = value;
    });
    return normalized;
  }
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }
  return { ...(headers as Record<string, string>) };
}

function prepareLoginMode(options: {
  authMode: "local" | "remote";
  devApiKey?: string;
  privatePreview?: boolean;
}): void {
  vi.unstubAllEnvs();
  vi.stubEnv("VITE_GUARDIAN_API_KEY", options.devApiKey ?? "");
  vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", options.devApiKey ?? "");
  vi.stubEnv(
    "VITE_PRIVATE_PREVIEW",
    options.privatePreview ? "true" : "false"
  );

  runtimeModeState.authMode = options.authMode;
  window.sessionStorage.clear();
  window.localStorage.clear();
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      assign: locationState.assign,
      href: "http://localhost:3000/login",
      origin: "http://localhost:3000",
      pathname: "/login",
      search: "",
    },
    writable: true,
  });
  locationState.assign.mockReset();
  setAuthToken(null);
  __resetAuthStateForTests();
  __resetRuntimeApiKeyForTests();
  resolveAuthStateOnBoot();
}

describe("trusted remote login page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    prepareLoginMode({ authMode: "remote" });
  });

  it("renders the remote private-workspace presentation without an API-key field", () => {
    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: "Welcome back to Codexify" })
    ).toBeInTheDocument();
    expect(screen.getByText("PRIVATE WORKSPACE")).toBeInTheDocument();
    expect(screen.getByText(REMOTE_BODY_COPY)).toBeInTheDocument();
    expect(screen.queryByText(LOCAL_BODY_COPY)).toBeNull();
    expect(
      screen.getByRole("button", { name: "ENTER WORKSPACE" })
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/api key/i)).toBeNull();
    expect(screen.queryByText(/x-api-key/i)).toBeNull();
    expect(screen.queryByText(/guardian_api_key/i)).toBeNull();
  });

  it("renders the local-workspace presentation", () => {
    prepareLoginMode({ authMode: "local" });

    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: "Welcome back to Codexify" })
    ).toBeInTheDocument();
    expect(screen.getByText("LOCAL WORKSPACE")).toBeInTheDocument();
    expect(screen.getByText(LOCAL_BODY_COPY)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "ENTER WORKSPACE" })
    ).toBeInTheDocument();
  });

  it("submits a trimmed username and an unmodified password", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: {
        token: "session-token",
        user_id: "user-123",
        expires_at: 1_725_000_000,
      },
    } as never);

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Username"), "  trusted-user  ");
    await user.type(
      screen.getByLabelText("Password"),
      "  session-secret  "
    );
    await user.click(
      screen.getByRole("button", { name: "ENTER WORKSPACE" })
    );

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/auth/login", {
        username: "trusted-user",
        password: "  session-secret  ",
      });
    });
  });

  it("stores a successful session and redirects to the workspace", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "post").mockResolvedValue({
      data: {
        token: "session-token",
        user_id: "user-123",
        expires_at: 1_725_000_000,
      },
    } as never);

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Username"), "trusted-user");
    await user.type(screen.getByLabelText("Password"), "session-secret");
    await user.click(
      screen.getByRole("button", { name: "ENTER WORKSPACE" })
    );

    await waitFor(() => {
      expect(window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)).toBe(
        "session-token"
      );
    });
    expect(getAuthState()).toMatchObject({
      status: "authenticated",
      ready: true,
      token: "session-token",
    });
    expect(
      screen.getByRole("heading", { name: "Your workspace is ready" })
    ).toBeInTheDocument();
    expect(locationState.assign).toHaveBeenCalledWith("/");
  });

  it("renders only the generic secret-safe login failure", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "post").mockRejectedValue(
      new Error("backend rejected the shared secret")
    );

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Username"), "trusted-user");
    await user.type(screen.getByLabelText("Password"), "bad-password");
    await user.click(
      screen.getByRole("button", { name: "ENTER WORKSPACE" })
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Unable to sign in. Check your credentials and try again."
      );
    });
    expect(screen.queryByText(/shared secret/i)).toBeNull();
    expect(screen.queryByText(/backend rejected/i)).toBeNull();
  });

  it("renders a distinct token-backed active-session state", () => {
    setAuthToken("session-token");

    render(<LoginPage />);

    expect(screen.queryByLabelText("Username")).toBeNull();
    expect(screen.queryByText("New to Codexify?")).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Your workspace is ready" })
    ).toBeInTheDocument();
    expect(
      screen.getByText("An active session was found on this device.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "CONTINUE TO WORKSPACE" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign in as another user" })
    ).toBeInTheDocument();
  });

  it("continues an active session to the workspace", async () => {
    const user = userEvent.setup();
    setAuthToken("session-token");

    render(<LoginPage />);

    await user.click(
      screen.getByRole("button", { name: "CONTINUE TO WORKSPACE" })
    );

    expect(locationState.assign).toHaveBeenCalledWith("/");
  });

  it("signs out a token-backed session and returns focus to the form", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, "post").mockResolvedValue({} as never);
    setAuthToken("session-token");

    render(<LoginPage />);

    await user.click(
      screen.getByRole("button", { name: "Sign in as another user" })
    );

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/auth/logout");
    });
    expect(window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Welcome back to Codexify" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveFocus();
  });

  it("keeps key-backed local access compatible without a misleading user switch", () => {
    prepareLoginMode({
      authMode: "local",
      devApiKey: "legacy-dev-key",
    });

    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: "Your workspace is ready" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Local workspace access is already configured on this device."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Sign in as another user" })
    ).toBeNull();
    expect(screen.queryByLabelText("Username")).toBeNull();

    const headers = normalizeHeaders(buildAuthenticatedFetchInit().headers);
    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe(
      "legacy-dev-key"
    );
    expect(headers.Authorization ?? headers.authorization).toBeUndefined();
    expect(screen.queryByLabelText(/api key/i)).toBeNull();
  });

  it("hides registration during private preview", () => {
    prepareLoginMode({ authMode: "local", privatePreview: true });

    render(<LoginPage />);

    expect(screen.queryByText("New to Codexify?")).toBeNull();
    expect(
      screen.queryByRole("link", { name: "Create a user profile" })
    ).toBeNull();
  });

  it("shows a non-interactive readiness state before auth resolves", () => {
    __setAuthStateForTests({ status: "unknown", ready: false });

    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: "Preparing your workspace" })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Checking the local access state on this device.")
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Username")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
