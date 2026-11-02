/**
 * Library filter ⇄ URL mapping.
 *
 * The Library filter taxonomy is a **navigation** concern, so the mapping
 * between a filter and the `?filter=` query lives here rather than in the
 * resource projection (which owns the taxonomy) or in the view (which owns
 * presentation).
 *
 * Rules:
 *
 * - **The URL is authoritative.** A filter is read from the query string and
 *   nowhere else. No component keeps an independent filter state that could
 *   disagree with the address bar.
 * - The default filter is `all`, and it is **omitted** from the query so the
 *   canonical Library address stays `/library`.
 * - Any unrecognised value falls back to `all` predictably, rather than
 *   throwing or rendering an unknown filter.
 */

import {
  LIBRARY_FILTERS,
  type LibraryFilter,
} from "@/components/library/libraryResourceProjection";

export const LIBRARY_FILTER_QUERY_PARAM = "filter";

const LIBRARY_FILTER_SET: ReadonlySet<string> = new Set<string>(LIBRARY_FILTERS);

/**
 * Normalise one raw query value into a supported filter.
 *
 * An absent, blank, or unrecognised value resolves to `all`.
 */
export function parseLibraryFilter(raw: string | null | undefined): LibraryFilter {
  if (typeof raw !== "string") return "all";
  const normalized = raw.trim().toLowerCase();
  return LIBRARY_FILTER_SET.has(normalized) ? (normalized as LibraryFilter) : "all";
}

/**
 * Read the selected filter from a location search string.
 *
 * `"?filter=documents"` → `"documents"`. Anything else → `"all"`.
 */
export function readLibraryFilterFromSearch(search: string): LibraryFilter {
  if (typeof search !== "string" || search.length === 0) return "all";
  let params: URLSearchParams;
  try {
    params = new URLSearchParams(search);
  } catch {
    return "all";
  }
  return parseLibraryFilter(params.get(LIBRARY_FILTER_QUERY_PARAM));
}

/**
 * Build the query string for a filter.
 *
 * `"all"` → `""` (the canonical `/library` address). Any other filter →
 * `"?filter=<value>"`.
 */
export function buildLibraryFilterSearch(filter: LibraryFilter): string {
  if (filter === "all") return "";
  return `?${LIBRARY_FILTER_QUERY_PARAM}=${encodeURIComponent(filter)}`;
}
