import { describe, expect, it } from "vitest";

import {
  buildLibraryFilterSearch,
  LIBRARY_FILTER_QUERY_PARAM,
  parseLibraryFilter,
  readLibraryFilterFromSearch,
} from "@/components/library/libraryFilterRoute";

describe("libraryFilterRoute", () => {
  describe("parseLibraryFilter", () => {
    it("accepts every approved filter", () => {
      expect(parseLibraryFilter("all")).toBe("all");
      expect(parseLibraryFilter("images")).toBe("images");
      expect(parseLibraryFilter("documents")).toBe("documents");
      expect(parseLibraryFilter("widgets")).toBe("widgets");
    });

    it("normalizes case and surrounding whitespace", () => {
      expect(parseLibraryFilter("  Documents ")).toBe("documents");
      expect(parseLibraryFilter("IMAGES")).toBe("images");
    });

    it("falls back to all for absent, blank, or unknown values", () => {
      expect(parseLibraryFilter(null)).toBe("all");
      expect(parseLibraryFilter(undefined)).toBe("all");
      expect(parseLibraryFilter("")).toBe("all");
      expect(parseLibraryFilter("   ")).toBe("all");
      expect(parseLibraryFilter("bogus")).toBe("all");
      expect(parseLibraryFilter("documents2")).toBe("all");
      expect(parseLibraryFilter("image")).toBe("all");
    });
  });

  describe("readLibraryFilterFromSearch", () => {
    it("reads the filter query parameter", () => {
      expect(readLibraryFilterFromSearch("?filter=documents")).toBe("documents");
      expect(readLibraryFilterFromSearch("?filter=images")).toBe("images");
      expect(readLibraryFilterFromSearch("?filter=widgets")).toBe("widgets");
      expect(readLibraryFilterFromSearch("?filter=all")).toBe("all");
    });

    it("reads the filter when it is not the only parameter", () => {
      expect(readLibraryFilterFromSearch("?scope=general&filter=documents")).toBe(
        "documents"
      );
      expect(readLibraryFilterFromSearch("?filter=documents&scope=general")).toBe(
        "documents"
      );
    });

    it("falls back to all when the parameter is absent or invalid", () => {
      expect(readLibraryFilterFromSearch("")).toBe("all");
      expect(readLibraryFilterFromSearch("?")).toBe("all");
      expect(readLibraryFilterFromSearch("?scope=general")).toBe("all");
      expect(readLibraryFilterFromSearch("?filter=bogus")).toBe("all");
    });
  });

  describe("buildLibraryFilterSearch", () => {
    it("omits the default filter so the canonical address stays clean", () => {
      expect(buildLibraryFilterSearch("all")).toBe("");
    });

    it("encodes every non-default filter", () => {
      expect(buildLibraryFilterSearch("images")).toBe(
        `?${LIBRARY_FILTER_QUERY_PARAM}=images`
      );
      expect(buildLibraryFilterSearch("documents")).toBe(
        `?${LIBRARY_FILTER_QUERY_PARAM}=documents`
      );
      expect(buildLibraryFilterSearch("widgets")).toBe(
        `?${LIBRARY_FILTER_QUERY_PARAM}=widgets`
      );
    });

    it("round-trips every filter through the search string", () => {
      for (const filter of ["all", "images", "documents", "widgets"] as const) {
        expect(readLibraryFilterFromSearch(buildLibraryFilterSearch(filter))).toBe(
          filter
        );
      }
    });
  });
});
