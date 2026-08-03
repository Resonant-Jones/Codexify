import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CodingLoopCards } from "./CodingLoop";

describe("CodingLoopCards", () => {
  it("renders accepted lineage without implying completion or exposing paths", () => {
    render(
      <CodingLoopCards
        dispatchErrors={[]}
        runs={[
          {
            run_id: "run-1",
            source_message_id: 99,
            adapter_kind: "pi_codex_runner",
            status: "queued",
            result: {
              summary: "Guardian accepted the bounded coding task.",
              files_changed_count: 1,
              artifacts: [{ name: "result.patch" }],
            },
          },
        ]}
      />
    );

    expect(screen.getByText("Accepted — queued")).toBeInTheDocument();
    expect(screen.getByText(/source message 99/)).toBeInTheDocument();
    expect(screen.getByText("1 file(s) changed")).toBeInTheDocument();
    expect(screen.queryByText(/\/workspace\//)).not.toBeInTheDocument();
  });

  it("distinguishes a saved message from a rejected execution dispatch", () => {
    render(
      <CodingLoopCards
        runs={[]}
        dispatchErrors={[
          {
            id: "dispatch-1",
            sourceMessageId: 100,
            message: "queue unavailable",
          },
        ]}
      />
    );

    expect(screen.getByText("Coding Loop was not accepted")).toBeInTheDocument();
    expect(screen.getByText(/authored message was saved/)).toBeInTheDocument();
    expect(screen.getByText(/Source message 100/)).toBeInTheDocument();
  });
});
