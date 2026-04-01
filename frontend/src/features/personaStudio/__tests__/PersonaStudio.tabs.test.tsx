import { beforeEach, describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import PersonaStudioPage from "../PersonaStudioPage";

beforeEach(() => {
  window.localStorage.clear();
});

describe("Persona Studio tabs", () => {
  it("renders Truth Matrix tab and switches correctly", () => {
    render(<PersonaStudioPage />);

    fireEvent.click(screen.getByText("Truth Matrix"));

    expect(screen.getByText("Field-by-field implementation truth")).toBeInTheDocument();
  });
});
