import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppShell from "@/components/persona/layout/AppShell";
import { vi } from "vitest";

// Mock the glass card to assert whether wallpaper is wired in
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

test("Clicking 'Use Demo' stores wallpaper and glass receives it", async () => {
  const u = userEvent.setup();
  render(<AppShell />);

  // Go to Settings → Appearance (default tab)
  await u.click(screen.getByRole("button", { name: /settings/i }));
  await u.click(screen.getByRole("button", { name: /use demo/i }));

  // Confirm storage was set
  const stored = localStorage.getItem("cfy.wallpaper");
  expect(stored).toBeTruthy();

  // Go to Dashboard and confirm both glass surfaces get wallpaper
  await u.click(screen.getByRole("button", { name: /dashboard/i }));
  const glass = screen.getAllByTestId("glass");
  expect(glass).toHaveLength(2);
  glass.forEach((g) => expect(g).toHaveAttribute("data-wallpaper", "yes"));
});

