import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";

const authCapability = vi.hoisted(() => ({
  state: "available" as "available" | "unavailable" | "unknown",
}));

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: () => ({
    ready: authCapability.state !== "unknown",
    state: authCapability.state,
    mounted: [],
    declared: {},
  }),
}));

vi.mock("@/pages/login/LoginPage", () => ({
  default: () => <div data-testid="login-page" />,
}));

vi.mock("@/pages/login/RegisterPage", () => ({
  default: () => <div data-testid="register-page" />,
}));

describe("App auth route profile gating", () => {
  beforeEach(() => {
    authCapability.state = "available";
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    cleanup();
  });

  it("uses the canonical auth route capability token", () => {
    expect(SUPPORTED_PROFILE_ROUTE_LABELS.AUTH).toBe("auth");
  });

  it("renders login and register only when auth is available", () => {
    window.history.pushState({}, "", "/login");
    const { unmount } = render(<App />);

    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(screen.queryByTestId("auth-route-unavailable")).not.toBeInTheDocument();

    unmount();
    window.history.pushState({}, "", "/register");
    render(<App />);

    expect(screen.getByTestId("register-page")).toBeInTheDocument();
    expect(screen.queryByTestId("auth-route-unavailable")).not.toBeInTheDocument();
  });

  it.each(["unavailable", "unknown"] as const)(
    "fails closed for login when auth is %s",
    (state) => {
      authCapability.state = state;
      window.history.pushState({}, "", "/login");

      render(<App />);

      expect(screen.getByTestId("auth-route-unavailable")).toBeInTheDocument();
      expect(screen.queryByTestId("login-page")).not.toBeInTheDocument();
      expect(screen.queryByRole("form")).not.toBeInTheDocument();
    }
  );

  it.each(["unavailable", "unknown"] as const)(
    "fails closed for register when auth is %s",
    (state) => {
      authCapability.state = state;
      window.history.pushState({}, "", "/register");

      render(<App />);

      expect(screen.getByTestId("auth-route-unavailable")).toBeInTheDocument();
      expect(screen.queryByTestId("register-page")).not.toBeInTheDocument();
      expect(screen.queryByRole("form")).not.toBeInTheDocument();
    }
  );
});
