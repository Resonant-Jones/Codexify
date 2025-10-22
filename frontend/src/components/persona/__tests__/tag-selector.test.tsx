import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PersonaProvider } from "../PersonaProvider";
import { TagSelector } from "../TagSelector";

function Harness() {
  return (
    <PersonaProvider>
      <TagSelector />
    </PersonaProvider>
  );
}

test("TagSelector can add/remove via setState(prev => ...)", async () => {
  const u = userEvent.setup();
  render(<Harness />);

  // Type a tag and click Add
  const input = screen.getByPlaceholderText(/add or search tags/i);
  await u.type(input, "alpha");
  await u.click(screen.getByRole("button", { name: /add/i }));

  // Tag appears in Selected list
  expect(screen.getByText("alpha")).toBeInTheDocument();

  // Remove via the × button (aria-label: Remove alpha)
  await u.click(screen.getByRole("button", { name: /remove alpha/i }));
  expect(screen.queryByRole("button", { name: /remove alpha/i })).not.toBeInTheDocument();
});
