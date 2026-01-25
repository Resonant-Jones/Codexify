import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DocumentTile from "@/components/documents/DocumentTile";

describe("DocumentTile", () => {
  it("renders embedding status badge", () => {
    render(
      <DocumentTile
        file={{ name: "Quarterly Plan.pdf", ext: "pdf", embeddingStatus: "processing" }}
      />
    );

    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("shows a short hint for failed embeddings", () => {
    render(
      <DocumentTile
        file={{
          name: "Quarterly Plan.pdf",
          ext: "pdf",
          embeddingStatus: "failed",
          embeddingError: "parsed_text_missing",
        }}
      />
    );

    expect(screen.getByText("Failed - No text")).toBeInTheDocument();
  });
});
