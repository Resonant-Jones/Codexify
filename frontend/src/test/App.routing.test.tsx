import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";

vi.mock("@/components/persona/layout/AppShell", () => ({
  default: () => <div data-testid="app-shell-mock" />,
}));

vi.mock("@/components/DocumentGenModal", () => ({
  default: () => null,
}));

describe("App shell route unlocks", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it.each(["/flow-builder?mode=expertise", "/persona-studio"])(
    "mounts AppShell directly for %s",
    (pathname) => {
      window.history.pushState({}, "", pathname);

      render(<App />);

      expect(screen.getByTestId("app-shell-mock")).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /generate doc/i })
      ).not.toBeInTheDocument();
    }
  );

  it("keeps ambient document generation available on normal shell routes", () => {
    window.history.pushState({}, "", "/dashboard");

    render(<App />);

    expect(screen.getByTestId("app-shell-mock")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generate doc/i })
    ).toBeInTheDocument();
  });
});
