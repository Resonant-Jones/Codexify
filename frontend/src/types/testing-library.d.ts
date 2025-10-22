import type { TestingLibraryMatchers } from "@testing-library/jest-dom/matchers";

declare global {
  namespace Chai {
    interface Assertion extends TestingLibraryMatchers<any, any> {}
  }
}

export {};
