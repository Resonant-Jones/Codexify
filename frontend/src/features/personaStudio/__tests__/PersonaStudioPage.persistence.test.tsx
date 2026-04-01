import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import PersonaStudioPage from "../PersonaStudioPage";

beforeEach(() => {
  window.localStorage.clear();
});

describe("Persona Studio persistence", () => {
  it("persists the selected profile, active tab, and draft edits across remounts", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<PersonaStudioPage />);

    await user.click(screen.getByRole("button", { name: /code assistant/i }));

    const nameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Code Assistant Draft");

    const descriptionInput = screen.getByPlaceholderText(/describe this persona/i);
    await user.clear(descriptionInput);
    await user.type(descriptionInput, "Persisted draft description");

    await user.click(screen.getByRole("button", { name: /model/i }));

    unmount();
    render(<PersonaStudioPage />);

    expect(
      screen.getByRole("heading", { name: "Code Assistant Draft" })
    ).toBeInTheDocument();
    expect(screen.getByText("Provider")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/enter persona name/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /identity/i }));

    expect(screen.getByDisplayValue("Code Assistant Draft")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Persisted draft description")
    ).toBeInTheDocument();
  });

  it("resets to the built-in seed before the first save and to the last saved local snapshot after save", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await user.click(screen.getByRole("button", { name: /code assistant/i }));

    const nameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Transient Draft");

    await user.click(screen.getByRole("button", { name: /^reset$/i }));

    expect(screen.getByRole("heading", { name: "Code Assistant" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Code Assistant")).toBeInTheDocument();

    const savedNameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(savedNameInput);
    await user.type(savedNameInput, "Saved Draft");

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    const editedNameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(editedNameInput);
    await user.type(editedNameInput, "Unsaved Draft");

    await user.click(screen.getByRole("button", { name: /^reset$/i }));

    expect(screen.getByDisplayValue("Saved Draft")).toBeInTheDocument();
  });

  it("restores the local seed workspace when resetting all persona studio data", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await user.click(screen.getByRole("button", { name: /code assistant/i }));

    const nameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Reset All Draft");

    await user.click(screen.getByRole("button", { name: /model/i }));

    await user.click(
      screen.getByRole("button", {
        name: /reset all local persona studio data/i,
      })
    );

    expect(screen.getByRole("heading", { name: "Guardian Default" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Guardian Default")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /identity/i })).toBeInTheDocument();
    expect(screen.queryByText("Provider")).not.toBeInTheDocument();
  });
});
