import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test } from "vitest";
import AppShell from "@/components/persona/layout/AppShell";
import { SETTINGS_DENSITY } from "@/features/settings/settingsDensityContract";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("cfy.lastView", "settings");
  window.history.replaceState({}, "", "/settings");
});

afterEach(() => {
  cleanup();
});

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    value: width,
  });
}

test("settings frame card is content-fit and keeps inner scrolling", async () => {
  setViewportWidth(1440);
  render(<AppShell />);

  // Theme controls present confirms Settings/Appearance is rendered.
  expect(screen.getByRole("button", { name: /^light$/i })).toBeInTheDocument();

  const frameCard = screen.getByTestId("settings-framecard");
  expect(frameCard).toBeInTheDocument();
  expect(frameCard.className.split(/\s+/)).not.toContain("h-full");
  expect(frameCard).toHaveClass("mx-auto", "w-full");
  expect(frameCard).toHaveStyle({ maxWidth: SETTINGS_DENSITY.frameMaxWidth });

  const scrollBody = screen.getByTestId("settings-scroll-body");
  expect(scrollBody.className).toContain("overflow-auto");
  expect(scrollBody.className).toContain("p-0");
});

test.each([
  ["small", 430],
  ["medium", 768],
] as const)("Settings stays full-width at the %s breakpoint", async (_label, width) => {
  setViewportWidth(width);
  render(<AppShell />);

  const frameCard = screen.getByTestId("settings-framecard");
  expect(frameCard).toHaveClass("mx-auto", "w-full");
  expect(frameCard).toHaveStyle({ maxWidth: "none" });
});
