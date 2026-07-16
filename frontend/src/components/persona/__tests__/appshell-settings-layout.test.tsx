import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppShell from "@/components/persona/layout/AppShell";
import { SETTINGS_DENSITY } from "@/features/settings/settingsDensityContract";

beforeEach(() => {
  localStorage.clear();
});

test("settings frame card is content-fit and keeps inner scrolling", async () => {
  const u = userEvent.setup();
  render(<AppShell />);

  await u.click(screen.getByRole("button", { name: /settings/i }));

  // Theme controls present confirms Settings/Appearance is rendered.
  expect(screen.getByRole("button", { name: /^light$/i })).toBeInTheDocument();

  const frameCard = screen.getByTestId("settings-framecard");
  expect(frameCard).toBeInTheDocument();
  expect(frameCard.className.split(/\s+/)).not.toContain("h-full");
  expect(frameCard).toHaveClass("mx-auto", "w-full");
  expect(frameCard).toHaveStyle({ maxWidth: SETTINGS_DENSITY.frameMaxWidth });
  expect(frameCard).not.toHaveStyle({ maxWidth: "min(46rem, calc(100vw - 2rem))" });

  const scrollBody = screen.getByTestId("settings-scroll-body");
  expect(scrollBody.className).toContain("overflow-auto");
  expect(scrollBody.className).toContain("p-0");
});
