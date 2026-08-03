import { describe, it } from "vitest";

// The canonical spec is discovered under tests/. Keeping this legacy path
// skipped avoids registering the same stateful App-shell test twice in one
// Vitest run while preserving the historical import location.
describe.skip("legacy thread document rehydration alias", () => {
  it("is covered by tests/thread_documents_rehydration.spec.tsx", () => {});
});
