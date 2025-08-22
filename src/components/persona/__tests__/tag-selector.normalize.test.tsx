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

beforeEach(() => localStorage.clear());

test("add trims input, prevents duplicates, remove works", async () => {
  const u = userEvent.setup();
  render(<Harness />);

  // Adjust placeholders/labels if yours differ
  const input = screen.getByPlaceholderText(/add.*tags/i);
  const addBtn = screen.getByRole("button", { name: /add/i });

  await u.type(input, "  alpha  ");
  await u.click(addBtn);
  expect(screen.getByText("alpha")).toBeInTheDocument();

  // Try to add duplicate (different case/spacing); expect single entry
  await u.clear(input);
  await u.type(input, "Alpha");
  await u.click(addBtn);
  const alphas = screen.getAllByText(/^alpha$/i);
  expect(alphas).toHaveLength(1);

  // Remove via “Remove alpha” button (TagSelector should set aria-label like this)
  const remove = screen.getByRole("button", { name: /remove alpha/i });
  await u.click(remove);
  expect(screen.queryByText(/^alpha$/i)).not.toBeInTheDocument();
});

