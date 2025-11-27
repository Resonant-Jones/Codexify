import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PersonaProvider, usePersona } from "../PersonaProvider";

function Probe() {
  const { memoryTags, setMemoryTags } = usePersona();
  return (
    <div>
      <div data-testid="tags">{memoryTags.join(",")}</div>
      <button onClick={() => setMemoryTags((prev) => Array.from(new Set([...prev, "alpha"])))}>
        add-alpha
      </button>
      <button onClick={() => setMemoryTags((prev) => prev.filter((x) => x !== "alpha"))}>
        remove-alpha
      </button>
    </div>
  );
}

test("setMemoryTags updater adds and removes without duplicates", async () => {
  const u = userEvent.setup();
  render(
    <PersonaProvider>
      <Probe />
    </PersonaProvider>
  );

  const tags = () => screen.getByTestId("tags");
  expect(tags().textContent).toBe("");

  await u.click(screen.getByText("add-alpha"));
  expect(tags().textContent).toBe("alpha");

  // Add again (should not duplicate if normalized)
  await u.click(screen.getByText("add-alpha"));
  expect(tags().textContent).toBe("alpha");

  await u.click(screen.getByText("remove-alpha"));
  expect(tags().textContent).toBe("");
});
