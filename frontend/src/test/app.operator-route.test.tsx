import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import App from "@/App";

vi.mock("@/components/DocumentGenModal", () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock("@/components/persona/layout/AppShell", () => ({
  __esModule: true,
  default: () => <div>AppShell</div>,
}));

describe("App operator route", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/operator");
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  test("renders the operator console shell at /operator", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Operator Console" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Completion Replay" })
    ).toBeInTheDocument();
  });
});
