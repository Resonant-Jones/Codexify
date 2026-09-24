import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";
import ActivateAccountPage, {
  ACTIVATION_UNAVAILABLE_MESSAGE,
} from "../login/ActivateAccountPage";

const RAW_TOKEN = "activation-token-that-is-long-enough-for-the-backend";

function loadActivationUrl(token: string | null = RAW_TOKEN): void {
  const fragment = token === null ? "" : `#token=${token}`;
  window.history.replaceState({}, "", `/activate${fragment}`);
}

describe("one-time account activation page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
    loadActivationUrl();
  });

  it("captures the fragment token and immediately removes it from history", () => {
    const replaceSpy = vi.spyOn(window.history, "replaceState");

    render(<ActivateAccountPage />);

    expect(replaceSpy).toHaveBeenCalledWith(
      expect.anything(),
      "",
      "/activate"
    );
    expect(window.location.pathname).toBe("/activate");
    expect(window.location.hash).toBe("");
    expect(document.body.textContent).not.toContain(RAW_TOKEN);
  });

  it("never writes token or password to browser persistence", async () => {
    const user = userEvent.setup();
    const localSet = vi.spyOn(Storage.prototype, "setItem");
    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: { ok: true, user_id: "recipient@example.com" },
    } as never);

    render(<ActivateAccountPage />);
    await user.type(screen.getByLabelText("New password"), "chosen-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "chosen-password"
    );
    await user.click(screen.getByRole("button", { name: "CREATE ACCOUNT" }));

    await waitFor(() => expect(postSpy).toHaveBeenCalledOnce());
    expect(localSet).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("requires non-empty matching passwords before redemption", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, "post");

    render(<ActivateAccountPage />);
    const submit = screen.getByRole("button", { name: "CREATE ACCOUNT" });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText("New password"), "first-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "different-password"
    );
    expect(submit).toBeDisabled();
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("posts only the captured token and recipient-selected password", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: { ok: true, user_id: "recipient@example.com" },
    } as never);

    render(<ActivateAccountPage />);
    await user.type(screen.getByLabelText("New password"), "chosen-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "chosen-password"
    );
    await user.click(screen.getByRole("button", { name: "CREATE ACCOUNT" }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/auth/activate", {
        token: RAW_TOKEN,
        password: "chosen-password",
      });
    });
    expect(postSpy.mock.calls[0]?.[1]).not.toHaveProperty("email");
    expect(postSpy.mock.calls[0]?.[1]).not.toHaveProperty("role");
  });

  it("shows a normal-login continuation after successful activation", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "post").mockResolvedValue({
      data: { ok: true, user_id: "recipient@example.com" },
    } as never);

    render(<ActivateAccountPage />);
    await user.type(screen.getByLabelText("New password"), "chosen-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "chosen-password"
    );
    await user.click(screen.getByRole("button", { name: "CREATE ACCOUNT" }));

    expect(
      await screen.findByRole("heading", { name: "Your account is ready" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "CONTINUE TO LOGIN" })
    ).toHaveAttribute("href", "/login");
    expect(screen.queryByLabelText("New password")).toBeNull();
  });

  it("uses one generic state for unavailable activation responses", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "post").mockRejectedValue(
      new Error("specific backend lifecycle detail")
    );

    render(<ActivateAccountPage />);
    await user.type(screen.getByLabelText("New password"), "chosen-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "chosen-password"
    );
    await user.click(screen.getByRole("button", { name: "CREATE ACCOUNT" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      ACTIVATION_UNAVAILABLE_MESSAGE
    );
    expect(screen.queryByText(/specific backend/i)).toBeNull();
  });

  it("shows the same bounded unavailable state when no token is present", () => {
    loadActivationUrl(null);
    render(<ActivateAccountPage />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      ACTIVATION_UNAVAILABLE_MESSAGE
    );
    expect(screen.queryByLabelText("New password")).toBeNull();
  });
});
