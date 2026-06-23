import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "../login/LoginPage";
import api, { buildAuthenticatedFetchInit, setAuthToken } from "@/lib/api";
import {
  __resetAuthStateForTests,
  getAuthState,
} from "@/lib/authState";
import { __resetRuntimeApiKeyForTests } from "@/lib/runtimeAuth";

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
}): void {
  vi.unstubAllEnvs();
  vi.stubEnv("VITE_GUARDIAN_API_KEY", options.devApiKey ?? "");
  vi.stubEnv("VITE_GUARDIAN_DEV_API_KEY", options.devApiKey ?? "");

  runtimeModeState.authMode = options.authMode;
  window.sessionStorage.clear();
  window.localStorage.clear();
  delete (window as any).location;
  (window as any).location = {
    assign: locationState.assign,
    href: "http://localhost:3000/login",
    origin: "http://localhost:3000",
    pathname: "/login",
    search: "",
  };
  locationState.assign.mockReset();
  setAuthToken(null);
  __resetAuthStateForTests();
  __resetRuntimeApiKeyForTests();
}

describe("trusted remote login page", () => {
  beforeEach(() => {
    prepareLoginMode({ authMode: "remote" });
  });

  it("remote_login_page_does_not_render_api_key_field", () => {
    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: "Session sign-in" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Use your workspace username and password. This browser will receive a session token after sign-in."
      )
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/api key/i)).toBeNull();
    expect(screen.queryByText(/x-api-key/i)).toBeNull();
    expect(screen.queryByText(/guardian_api_key/i)).toBeNull();
  });

  it("remote_login_submits_credentials_to_session_login_path", async () => {
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
    await user.type(screen.getByLabelText("Password"), "session-secret");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/auth/login", {
        username: "trusted-user",
        password: "session-secret",
      });
    });
  });

  it("remote_login_success_stores_session_and_unlocks_auth_gate", async () => {
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
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)).toBe(
        "session-token"
      );
    });
    await waitFor(() => {
      expect(getAuthState().status).toBe("authenticated");
      expect(getAuthState().ready).toBe(true);
      expect(getAuthState().token).toBe("session-token");
    });
    await waitFor(() => {
      expect(
        screen.getByText("A session is already active.")
      ).toBeInTheDocument();
    });

    expect(locationState.assign).toHaveBeenCalledWith("/");
  });

  it("remote_login_failure_shows_non_secret_error", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "post").mockRejectedValue(
      new Error("backend rejected the shared secret")
    );

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Username"), "trusted-user");
    await user.type(screen.getByLabelText("Password"), "bad-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Unable to sign in. Check your credentials and try again."
      );
    });
    expect(screen.queryByText(/shared secret/i)).toBeNull();
    expect(screen.queryByText(/backend rejected/i)).toBeNull();
  });

  it("local_dev_api_key_path_remains_available_outside_remote_mode", () => {
    prepareLoginMode({
      authMode: "local",
      devApiKey: "legacy-dev-key",
    });

    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    const headers = normalizeHeaders(buildAuthenticatedFetchInit().headers);

    expect(headers["X-API-Key"] ?? headers["x-api-key"]).toBe("legacy-dev-key");
    expect(headers.Authorization ?? headers.authorization).toBeUndefined();
    expect(screen.queryByLabelText(/api key/i)).toBeNull();
  });
});
