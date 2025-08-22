import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppShell from "@/components/persona/layout/AppShell";

beforeEach(() => {
  localStorage.clear();
});

test("nav -> Settings persists and restores on next mount", async () => {
  const u = userEvent.setup();
  const { unmount } = render(<AppShell />);

  // Move to Settings
  await u.click(screen.getByRole("button", { name: /settings/i }));

  // Presence of theme control implies we're on Settings/Appearance
  expect(screen.getByRole("button", { name: /^light$/i })).toBeInTheDocument();

  // Remount a fresh AppShell; it should restore "settings"
  unmount();
  cleanup();
  render(<AppShell />);

  // Should still show appearance controls without navigating
  expect(screen.getByRole("button", { name: /^light$/i })).toBeInTheDocument();
});

