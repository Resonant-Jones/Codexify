import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppShell from "@/components/persona/layout/AppShell";
import { vi } from "vitest";

// Mock the glass card so we can assert wallpaper + placements without WebGL.
vi.mock("@/components/ui/RefractiveGlassCard", () => {
  return {
    default: ({ wallpaperUrl, className, children }: any) => (
      <div data-testid="glass" data-wallpaper={wallpaperUrl ? "yes" : "no"} className={className}>
        {children}
      </div>
    ),
  };
});

beforeEach(() => {
  localStorage.clear();
});

test("Dashboard: exactly 2 glass surfaces, both receive wallpaper", async () => {
  const u = userEvent.setup();
  render(<AppShell />);

  await u.click(screen.getByRole("button", { name: /dashboard/i }));
  const glass = screen.getAllByTestId("glass");
  expect(glass).toHaveLength(2);
  glass.forEach(g => expect(g).toHaveAttribute("data-wallpaper", "yes"));
});

test("Guardian: no glass on chat", async () => {
  const u = userEvent.setup();
  render(<AppShell />);

  await u.click(screen.getByRole("button", { name: /guardian/i }));
  expect(screen.queryAllByTestId("glass")).toHaveLength(0);
});

test("Settings: only Workspace side is glass and gets wallpaper", async () => {
  const u = userEvent.setup();
  render(<AppShell />);

  await u.click(screen.getByRole("button", { name: /settings/i }));
  const glass = screen.getAllByTestId("glass");
  expect(glass).toHaveLength(1);
  expect(glass[0]).toHaveAttribute("data-wallpaper", "yes");
});

