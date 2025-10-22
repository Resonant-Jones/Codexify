import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppShell from "@/components/persona/layout/AppShell";

// JSDOM: stub matchMedia so "system" resolves predictably
beforeAll(() => {
  // Light by default
  window.matchMedia = (q: string) => ({
    media: q,
    matches: false,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  });
});

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
});

test("Settings/Appearance toggles dark class on <html>", async () => {
  const u = userEvent.setup();
  render(<AppShell />);

  // Go to Settings → Appearance tab (default tab is Appearance)
  await u.click(screen.getByRole("button", { name: /settings/i }));

  // Click "Dark" in SegmentedThemeControl
  await u.click(screen.getByRole("button", { name: /^dark$/i }));
  expect(document.documentElement.classList.contains("dark")).toBe(true);

  // Click "Light"
  await u.click(screen.getByRole("button", { name: /^light$/i }));
  expect(document.documentElement.classList.contains("dark")).toBe(false);
});
