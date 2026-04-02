import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import PersonaStudioPage from "../PersonaStudioPage";
import {
  personaStudioApiMock,
  resetPersonaStudioApiMock,
} from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

beforeEach(() => {
  window.localStorage.clear();
  resetPersonaStudioApiMock();
});

describe("Persona Studio tabs", () => {
  it("renders Truth Matrix tab and switches correctly", () => {
    render(<PersonaStudioPage />);

    fireEvent.click(screen.getByText("Truth Matrix"));

    expect(screen.getByText("Field-by-field implementation truth")).toBeInTheDocument();
  });
});
