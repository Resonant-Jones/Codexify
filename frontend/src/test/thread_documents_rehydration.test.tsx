// Mock session persistence to prevent network calls during tests
import { vi } from "vitest";

vi.mock("@/state/session/SessionStateStore", () => ({
  RedisSessionStateStore: class {
    async setSessionState() {
      return Promise.resolve();
    }
  }
}));

// Now import the actual test spec
import "../tests/thread_documents_rehydration.spec";
