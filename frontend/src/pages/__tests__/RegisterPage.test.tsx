import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";

import RegisterPage from "../login/RegisterPage";

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
}));

function prepareRegisterMode(authMode: "local" | "remote"): void {
  runtimeModeState.authMode = authMode;
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      assign: locationState.assign,
      href: "http://localhost:3000/register",
      origin: "http://localhost:3000",
      pathname: "/register",
      search: "",
    },
    writable: true,
  });
  locationState.assign.mockReset();
}

describe("registration page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    prepareRegisterMode("remote");
  });

  it("renders an email-shaped identity field for remote authentication", () => {
    render(<RegisterPage />);

    const email = screen.getByLabelText("Email address");
    expect(email).toHaveAttribute("type", "email");
    expect(email).toHaveAttribute("inputmode", "email");
    expect(email).toHaveAttribute("autocomplete", "email");
    expect(email).toHaveAttribute("placeholder", "you@example.com");
    expect(screen.queryByText("Choose a username")).toBeNull();
  });

  it("submits the remote email as the canonical registration username", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: {} } as never);

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email address"), "tomepenn@gmail.com");
    await user.type(screen.getByLabelText("Choose a password"), "user-chosen-password");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/auth/register", {
        username: "tomepenn@gmail.com",
        password: "user-chosen-password",
      });
    });
    expect(locationState.assign).toHaveBeenCalledWith("/login");
  });

  it("preserves username-oriented registration for local authentication", () => {
    prepareRegisterMode("local");

    render(<RegisterPage />);

    const username = screen.getByLabelText("Choose a username");
    expect(username).toHaveAttribute("type", "text");
    expect(username).toHaveAttribute("autocomplete", "username");
    expect(username).toHaveAttribute("placeholder", "e.g. resonant-jones");
    expect(screen.queryByLabelText("Email address")).toBeNull();
  });
});
