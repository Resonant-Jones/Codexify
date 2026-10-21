/**
 * Library resource projection.
 *
 * A read-only, typed projection over the *existing* Images and Documents
 * sources. It introduces no persistence, no mutation, and no new transport: it
 * reuses the shared authenticated client and the Documents scope projection.
 *
 * Design rules enforced here (see docs/architecture/
 * library-projects-spaces-product-surface-contract.md):
 *
 * - Resource **type** is classified independently from **origin**. A generated
 *   image is still an `image`; a generated document is still a `document`.
 *   No filter ever selects on origin.
 * - Presentation keys are **source-family qualified**. Canonical source IDs are
 *   unique only within their own family and legitimately collide across
 *   families, so a raw ID is never a presentation identity and never a
 *   cross-source dedup key.
 * - Canonical source IDs are preserved verbatim from the authoritative source.
 * - One identical scope query is applied to every source request, and account
 *   scope comes from the authenticated transport — never a client-supplied id.
 * - Incompleteness is first-class. A bounded list or a failed source is reported
 *   as such and can never masquerade as a complete `All` projection.
 * - Widgets stay explicitly unavailable. Nothing is fabricated to fill them.
 */

import api from "@/lib/api";
import {
  getDocumentScopeQuery,
  type DocumentsScope,
} from "@/components/documents/documentScopeProjection";

/* ── Approved taxonomy ─────────────────────────────────────────────────── */

/** The approved Library filter taxonomy: All | Images | Documents | Widgets. */
export type LibraryFilter = "all" | "images" | "documents" | "widgets";

export const LIBRARY_FILTERS: readonly LibraryFilter[] = [
  "all",
  "images",
  "documents",
  "widgets",
];

/**
 * Resource type is orthogonal to origin. `widget` is declared for taxonomy
 * completeness but is never produced while its backing records are unproven.
 */
export type LibraryResourceType = "image" | "document" | "widget";

/**
 * Provenance — how the record entered the system, as *proven* by authoritative
 * metadata. Deliberately includes `unknown`: a record sitting in an "uploaded"
 * source table is not proof of a user upload, and absence of provenance
 * metadata must never be resolved into a positive claim.
 */
export type LibraryResourceOrigin =
  | "uploaded"
  | "generated"
  | "imported"
  | "unknown";

/**
 * Source families are the authoritative identity namespaces. IDs collide
 * across these families by design, not by accident.
 */
export type LibrarySourceFamily =
  | "uploaded_image"
  | "generated_image"
  | "uploaded_document"
  | "generated_document";

/**
 * The transport-level source requests. Note that `document_artifact` is a
 * single request that yields *two* source families, while images require two
 * separate requests because the endpoint selects one family per call.
 */
export type LibrarySourceRequestId =
  | "uploaded_image"
  | "generated_image"
  | "document_artifact";

/* ── Projected resource ────────────────────────────────────────────────── */

export type LibraryResource = {
  /**
   * Source-family-qualified presentation identity. Unique by construction, so
   * two records sharing a raw ID across families never collide.
   */
  readonly presentationKey: string;
  /** Authoritative family, preserved for provenance and future authority work. */
  readonly sourceFamily: LibrarySourceFamily;
  /** Canonical source ID exactly as the authoritative source reported it. */
  readonly sourceId: string;
  /** Selectable type — what a Library filter is allowed to match on. */
  readonly resourceType: LibraryResourceType;
  /** Provenance — how the record entered the system. Never used for filtering. */
  readonly origin: LibraryResourceOrigin;
  readonly title: string;
  readonly sourceTag: string | null;
  readonly srcUrl: string | null;
  readonly mimeType: string | null;
  readonly filename: string | null;
  readonly projectId: number | null;
  readonly threadIds: readonly number[];
  readonly createdAt: string | null;
  /**
   * Original source record, untouched. Projection is additive: a consumer can
   * always reach the authoritative metadata this projection normalized from.
   */
  readonly raw: Readonly<Record<string, unknown>>;
};

export type LibraryRejectionReason =
  /** No canonical source ID — the record cannot be identified. */
  | "missing_source_id"
  /** Document metadata could not authoritatively establish its type. */
  | "unclassifiable_document"
  /** Synthetic/placeholder record — must never be presented as real data. */
  | "synthetic_record";

export type LibraryRejectedRecord = {
  readonly reason: LibraryRejectionReason;
  readonly source: LibrarySourceRequestId;
  readonly sourceFamily: LibrarySourceFamily | null;
  readonly sourceId: string | null;
  readonly detail: string;
};

/* ── Completeness ─────────────────────────────────────────────────────── */

/**
 * Per-source outcome. Only `complete` and `empty` assert that coverage is
 * proven; everything else is a statement about what we could not establish.
 */
export type LibrarySourceStatus =
  /** Proven exhausted and non-empty. */
  | "complete"
  /** Proven exhausted and empty — an authenticated, authoritative zero. */
  | "empty"
  /** Reached the request limit, so the source may be truncated. */
  | "bounded"
  /**
   * Response metadata was malformed, missing, or self-inconsistent, or
   * authoritative records were rejected. The projection cannot claim coverage.
   */
  | "uncertain"
  /** The request itself failed. */
  | "failed";

export type LibrarySourceOutcome = {
  readonly source: LibrarySourceRequestId;
  readonly families: readonly LibrarySourceFamily[];
  readonly status: LibrarySourceStatus;
  readonly limit: number;
  /** Records actually projected out of this source. */
  readonly returnedCount: number;
  /** Authoritative `count` reported by the source, when it was usable. */
  readonly reportedCount: number | null;
  /** Authoritative records this source returned that could not be projected. */
  readonly rejectedCount: number;
  /** Why this status, when it is not proven coverage. */
  readonly detail: string | null;
  readonly error: string | null;
};

/**
 * `unavailable` means the filter has no authoritative source at all. It is
 * deliberately *not* expressed as a complete empty result, so "we could not
 * look" can never be misread as "we looked and there is nothing".
 */
export type LibraryCoverage = "known" | "unavailable";

export type LibraryCompleteness = {
  readonly complete: boolean;
  readonly coverage: LibraryCoverage;
  /** Human-readable explanation of the overall verdict. */
  readonly detail: string;
  /** Sources planned for this filter that did not prove coverage. */
  readonly incompleteSources: readonly LibrarySourceRequestId[];
  readonly boundedSources: readonly LibrarySourceRequestId[];
  readonly failedSources: readonly LibrarySourceRequestId[];
  readonly uncertainSources: readonly LibrarySourceRequestId[];
};

/* ── Widget discovery ─────────────────────────────────────────────────── */

export type LibraryWidgetDiscovery = {
  readonly available: false;
  /** Approved as taxonomy, unproven as capability. */
  readonly reason: string;
};

/* ── Projection result ────────────────────────────────────────────────── */

export type LibraryResourceProjection = {
  readonly filter: LibraryFilter;
  readonly scope: DocumentsScope;
  readonly resources: readonly LibraryResource[];
  readonly sources: readonly LibrarySourceOutcome[];
  readonly completeness: LibraryCompleteness;
  readonly widgetDiscovery: LibraryWidgetDiscovery;
  readonly rejected: readonly LibraryRejectedRecord[];
};

/* ── Read-only transport ──────────────────────────────────────────────── */

/**
 * Deliberately exposes `get` only. A projection has no business mutating an
 * authoritative source, so the type itself makes a mutation request
 * unrepresentable.
 */
export type LibraryResourceTransport = {
  get(
    path: string,
    config?: { params?: Record<string, unknown> }
  ): Promise<{ data?: unknown }>;
};

/** The shared authenticated client. Account scope rides its credentials. */
export const defaultLibraryTransport: LibraryResourceTransport = api;

const IMAGES_PATH = "/media/images";
const DOCUMENT_ARTIFACTS_PATH = "/media/document-artifacts";

/**
 * `/media/images` serves one source family per call and selects it with `tag`.
 * A complete Images projection therefore needs both calls; requesting only the
 * default family would silently omit every generated image.
 */
const IMAGE_SOURCES: readonly {
  request: LibrarySourceRequestId;
  family: LibrarySourceFamily;
  tag?: string;
}[] = [
  { request: "uploaded_image", family: "uploaded_image" },
  { request: "generated_image", family: "generated_image", tag: "generated" },
];

const DOCUMENT_FAMILIES: readonly LibrarySourceFamily[] = [
  "uploaded_document",
  "generated_document",
];

/* ── Normalization helpers ────────────────────────────────────────────── */

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** Canonical IDs may arrive as strings or integers; both are preserved as text. */
function readSourceId(raw: Record<string, unknown>): string | null {
  const candidate = raw.id ?? raw.document_id;
  if (typeof candidate === "string") {
    const trimmed = candidate.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  if (typeof candidate === "number" && Number.isFinite(candidate)) {
    return String(candidate);
  }
  return null;
}

function readOptionalString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function readOptionalNumber(value: unknown): number | null {
  const parsed = typeof value === "string" ? Number(value) : value;
  return typeof parsed === "number" && Number.isInteger(parsed) && parsed > 0
    ? parsed
    : null;
}

function readThreadIds(raw: Record<string, unknown>): number[] {
  const collected: number[] = [];
  const push = (value: unknown) => {
    const parsed = readOptionalNumber(value);
    if (parsed != null && !collected.includes(parsed)) collected.push(parsed);
  };

  if (Array.isArray(raw.thread_ids)) {
    raw.thread_ids.forEach(push);
  }
  push(raw.thread_id);
  return collected;
}

function readCreatedAt(raw: Record<string, unknown>): string | null {
  return readOptionalString(raw.created_at ?? raw.createdAt);
}

function isSynthetic(raw: Record<string, unknown>): boolean {
  // Placeholder records are part of the Documents contract. They must be
  // rejected rather than projected as real user data.
  return raw.mock === true;
}

/**
 * Source-family-qualified key. This is the only identity the projection treats
 * as unique, and it is deliberately *not* the raw ID.
 */
export function toPresentationKey(
  family: LibrarySourceFamily,
  sourceId: string
): string {
  return `${family}:${sourceId}`;
}

/**
 * Provenance is read only from authoritative `source_tag` metadata.
 *
 * The source *family* is deliberately not used: a row living in an uploaded
 * table proves which table it came from, not that a user uploaded it. The
 * backend emits `source_tag: "generated"` for generated records of both kinds
 * and passes uploaded-family rows through with their own (often absent) tag, so
 * anything unrecognised stays `unknown` rather than being asserted.
 */
function readOrigin(raw: Record<string, unknown>): LibraryResourceOrigin {
  const tag = readOptionalString(raw.source_tag)?.toLowerCase();
  if (tag === "uploaded") return "uploaded";
  if (tag === "generated") return "generated";
  if (tag === "imported") return "imported";
  return "unknown";
}

function readListPayload(
  data: unknown,
  key: "images" | "documents"
): { ok: true; records: unknown[]; count: number } | { ok: false; reason: string } {
  const body = asRecord(data);
  if (!body) {
    return { ok: false, reason: "Response body is not an object." };
  }

  const list = body[key];
  if (!Array.isArray(list)) {
    return {
      ok: false,
      reason: `Response field "${key}" is missing or not an array.`,
    };
  }

  // Both endpoints report `count` as the post-limit length of the same list.
  // A missing, non-integer, negative, or disagreeing count means we cannot
  // establish what the source actually returned.
  const count = body.count;
  if (typeof count !== "number" || !Number.isInteger(count) || count < 0) {
    return {
      ok: false,
      reason: `Response "count" is missing or not a non-negative integer (got ${String(count)}).`,
    };
  }
  if (count !== list.length) {
    return {
      ok: false,
      reason: `Response "count" (${count}) disagrees with "${key}" length (${list.length}).`,
    };
  }

  return { ok: true, records: list, count };
}

type NormalizeContext = {
  source: LibrarySourceRequestId;
  family: LibrarySourceFamily;
};

type NormalizeOutcome =
  | { kind: "resource"; resource: LibraryResource }
  | { kind: "rejected"; rejected: LibraryRejectedRecord };

function normalizeImageRecord(
  value: unknown,
  context: NormalizeContext
): NormalizeOutcome {
  const raw = asRecord(value);
  if (!raw) {
    return {
      kind: "rejected",
      rejected: {
        reason: "missing_source_id",
        source: context.source,
        sourceFamily: context.family,
        sourceId: null,
        detail: "Image record is not an object.",
      },
    };
  }

  const sourceId = readSourceId(raw);
  if (!sourceId) {
    return {
      kind: "rejected",
      rejected: {
        reason: "missing_source_id",
        source: context.source,
        sourceFamily: context.family,
        sourceId: null,
        detail: "Image record has no canonical id.",
      },
    };
  }

  if (isSynthetic(raw)) {
    return {
      kind: "rejected",
      rejected: {
        reason: "synthetic_record",
        source: context.source,
        sourceFamily: context.family,
        sourceId,
        detail: "Image record is flagged as mock data.",
      },
    };
  }

  // Provenance is proven by metadata, never by which table the row came from.
  const origin = readOrigin(raw);

  return {
    kind: "resource",
    resource: {
      presentationKey: toPresentationKey(context.family, sourceId),
      sourceFamily: context.family,
      sourceId,
      resourceType: "image",
      origin,
      title:
        readOptionalString(raw.filename) ??
        readOptionalString(raw.prompt) ??
        "Untitled",
      sourceTag: readOptionalString(raw.source_tag),
      srcUrl: readOptionalString(raw.src_url),
      mimeType: readOptionalString(raw.mime_type),
      filename: readOptionalString(raw.filename),
      projectId: readOptionalNumber(raw.project_id),
      threadIds: readThreadIds(raw),
      createdAt: readCreatedAt(raw),
      raw,
    },
  };
}

/**
 * Documents arrive from a single endpoint mixing both families, so the family
 * comes from the authoritative `artifact_type` the backend assigned from the
 * source table. When that metadata cannot establish a type we refuse to guess.
 */
function normalizeDocumentRecord(
  value: unknown,
  source: LibrarySourceRequestId
): NormalizeOutcome {
  const raw = asRecord(value);
  if (!raw) {
    return {
      kind: "rejected",
      rejected: {
        reason: "missing_source_id",
        source,
        sourceFamily: null,
        sourceId: null,
        detail: "Document record is not an object.",
      },
    };
  }

  const sourceId = readSourceId(raw);
  if (!sourceId) {
    return {
      kind: "rejected",
      rejected: {
        reason: "missing_source_id",
        source,
        sourceFamily: null,
        sourceId: null,
        detail: "Document record has no canonical id.",
      },
    };
  }

  const declaredType = readOptionalString(raw.artifact_type)?.toLowerCase();
  const family: LibrarySourceFamily | null =
    declaredType === "generated"
      ? "generated_document"
      : declaredType === "uploaded"
        ? "uploaded_document"
        : null;

  if (!family) {
    return {
      kind: "rejected",
      rejected: {
        reason: "unclassifiable_document",
        source,
        sourceFamily: null,
        sourceId,
        detail: `Document artifact_type "${String(
          raw.artifact_type ?? ""
        )}" does not authoritatively identify a source family.`,
      },
    };
  }

  if (isSynthetic(raw)) {
    return {
      kind: "rejected",
      rejected: {
        reason: "synthetic_record",
        source,
        sourceFamily: family,
        sourceId,
        detail: "Document record is flagged as mock data.",
      },
    };
  }

  return {
    kind: "resource",
    resource: {
      presentationKey: toPresentationKey(family, sourceId),
      sourceFamily: family,
      sourceId,
      resourceType: "document",
      origin: readOrigin(raw),
      title: readOptionalString(raw.title) ?? readOptionalString(raw.filename) ?? "Untitled",
      sourceTag: readOptionalString(raw.source_tag),
      srcUrl: readOptionalString(raw.src_url),
      mimeType: readOptionalString(raw.mime_type),
      filename: readOptionalString(raw.filename),
      projectId: readOptionalNumber(raw.project_id),
      threadIds: readThreadIds(raw),
      createdAt: readCreatedAt(raw),
      raw,
    },
  };
}

/* ── Source fetching ──────────────────────────────────────────────────── */

type SourceFetch = {
  outcome: LibrarySourceOutcome;
  resources: LibraryResource[];
  rejected: LibraryRejectedRecord[];
};

/**
 * Decide what a source actually established. Only two outcomes claim coverage;
 * everything else reports precisely what could not be proven.
 */
function resolveSourceStatus(input: {
  limit: number;
  observedCount: number;
  rejectedCount: number;
}): { status: LibrarySourceStatus; detail: string | null } {
  if (input.rejectedCount > 0) {
    return {
      status: "uncertain",
      detail: `${input.rejectedCount} authoritative record(s) could not be projected, so coverage is incomplete.`,
    };
  }
  if (input.observedCount >= input.limit) {
    return {
      status: "bounded",
      detail: `Returned ${input.observedCount} record(s) at the request limit of ${input.limit}; the source may be truncated.`,
    };
  }
  if (input.observedCount === 0) {
    return { status: "empty", detail: null };
  }
  return { status: "complete", detail: null };
}

function uncertainOutcome(
  source: LibrarySourceRequestId,
  families: readonly LibrarySourceFamily[],
  limit: number,
  reason: string
): SourceFetch {
  return {
    outcome: {
      source,
      families,
      status: "uncertain",
      limit,
      returnedCount: 0,
      reportedCount: null,
      rejectedCount: 0,
      detail: reason,
      error: null,
    },
    resources: [],
    rejected: [],
  };
}

function describeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Unknown source failure";
}

async function fetchImageSource(
  transport: LibraryResourceTransport,
  scopeQuery: Record<string, unknown>,
  tag: string | undefined
): Promise<SourceFetch> {
  const params: Record<string, unknown> = { ...scopeQuery };
  if (tag) params.tag = tag;

  const family = (
    tag === "generated" ? "generated_image" : "uploaded_image"
  ) as LibrarySourceFamily;
  const request = (
    tag === "generated" ? "generated_image" : "uploaded_image"
  ) as LibrarySourceRequestId;
  const limit = Number(params.limit ?? 0);

  try {
    const response = await transport.get(IMAGES_PATH, { params });
    const payload = readListPayload(response?.data, "images");
    if (!payload.ok) {
      return uncertainOutcome(request, [family], limit, payload.reason);
    }

    const resources: LibraryResource[] = [];
    const rejected: LibraryRejectedRecord[] = [];

    for (const record of payload.records) {
      const outcome = normalizeImageRecord(record, { source: request, family });
      if (outcome.kind === "resource") resources.push(outcome.resource);
      else rejected.push(outcome.rejected);
    }

    const resolved = resolveSourceStatus({
      limit,
      observedCount: payload.count,
      rejectedCount: rejected.length,
    });

    return {
      outcome: {
        source: request,
        families: [family],
        status: resolved.status,
        limit,
        returnedCount: resources.length,
        reportedCount: payload.count,
        rejectedCount: rejected.length,
        detail: resolved.detail,
        error: null,
      },
      resources,
      rejected,
    };
  } catch (error) {
    return {
      outcome: {
        source: request,
        families: [family],
        status: "failed",
        limit,
        returnedCount: 0,
        reportedCount: null,
        rejectedCount: 0,
        detail: null,
        error: describeError(error),
      },
      resources: [],
      rejected: [],
    };
  }
}

async function fetchDocumentSource(
  transport: LibraryResourceTransport,
  scopeQuery: Record<string, unknown>
): Promise<SourceFetch> {
  const params: Record<string, unknown> = { ...scopeQuery };
  const limit = Number(params.limit ?? 0);

  try {
    const response = await transport.get(DOCUMENT_ARTIFACTS_PATH, { params });
    const payload = readListPayload(response?.data, "documents");
    if (!payload.ok) {
      return uncertainOutcome("document_artifact", DOCUMENT_FAMILIES, limit, payload.reason);
    }

    const resources: LibraryResource[] = [];
    const rejected: LibraryRejectedRecord[] = [];

    for (const record of payload.records) {
      const outcome = normalizeDocumentRecord(record, "document_artifact");
      if (outcome.kind === "resource") resources.push(outcome.resource);
      else rejected.push(outcome.rejected);
    }

    // One limit governs the merged list, so a saturated merged list is
    // bounded for the endpoint as a whole.
    const resolved = resolveSourceStatus({
      limit,
      observedCount: payload.count,
      rejectedCount: rejected.length,
    });

    return {
      outcome: {
        source: "document_artifact",
        families: DOCUMENT_FAMILIES,
        status: resolved.status,
        limit,
        returnedCount: resources.length,
        reportedCount: payload.count,
        rejectedCount: rejected.length,
        detail: resolved.detail,
        error: null,
      },
      resources,
      rejected,
    };
  } catch (error) {
    return {
      outcome: {
        source: "document_artifact",
        families: DOCUMENT_FAMILIES,
        status: "failed",
        limit,
        returnedCount: 0,
        reportedCount: null,
        rejectedCount: 0,
        detail: null,
        error: describeError(error),
      },
      resources: [],
      rejected: [],
    };
  }
}

/* ── Completeness assembly ────────────────────────────────────────────── */

/**
 * Pure, deterministic source planner. Each filter requests exactly the sources
 * that can contribute to it — Widgets requests none, because no Widget source
 * exists. Deliberately a plain switch rather than a general framework.
 */
export function sourcesForFilter(
  filter: LibraryFilter
): readonly LibrarySourceRequestId[] {
  switch (filter) {
    case "images":
      return ["uploaded_image", "generated_image"];
    case "documents":
      return ["document_artifact"];
    case "widgets":
      return [];
    case "all":
    default:
      return ["uploaded_image", "generated_image", "document_artifact"];
  }
}

function summarize(filter: LibraryFilter, outcomes: readonly LibrarySourceOutcome[]): LibraryCompleteness {
  const relevant = new Set(sourcesForFilter(filter));
  const considered = outcomes.filter((outcome) => relevant.has(outcome.source));
  const incomplete = considered.filter(
    (outcome) => outcome.status !== "complete" && outcome.status !== "empty"
  );

  const pick = (status: LibrarySourceStatus) =>
    considered.filter((outcome) => outcome.status === status).map((o) => o.source);

  // A filter with no planned source has no coverage to report. Saying
  // "complete" here would assert a Widget listing was checked and came back
  // empty, which is precisely the claim we cannot make.
  if (considered.length === 0) {
    return {
      complete: false,
      coverage: "unavailable",
      detail:
        filter === "widgets"
          ? WIDGET_DISCOVERY.reason
          : "No authoritative source is planned for this filter.",
      incompleteSources: [],
      boundedSources: [],
      failedSources: [],
      uncertainSources: [],
    };
  }

  const complete = incomplete.length === 0;
  return {
    complete,
    coverage: "known",
    detail: complete
      ? `All ${considered.length} contributing source(s) reported proven coverage.`
      : incomplete
          .map((outcome) => `${outcome.source}: ${outcome.detail ?? outcome.error ?? outcome.status}`)
          .join(" "),
    incompleteSources: incomplete.map((outcome) => outcome.source),
    boundedSources: pick("bounded"),
    failedSources: pick("failed"),
    uncertainSources: pick("uncertain"),
  };
}

const WIDGET_DISCOVERY: LibraryWidgetDiscovery = {
  available: false,
  reason:
    "No authoritative Widget backing record, persistence, or versioned listing mechanism exists yet. " +
    "Widgets stay unavailable rather than being synthesized from unrelated records.",
};

/* ── Public projection ────────────────────────────────────────────────── */

export type BuildLibraryProjectionOptions = {
  /** Which approved filter this projection answers. */
  readonly filter?: LibraryFilter;
  /** The selected Project/thread scope, applied to every source request. */
  readonly scope: DocumentsScope;
  readonly transport?: LibraryResourceTransport;
};

/**
 * Build a read-only Library projection for one filter over one scope.
 *
 * Never throws for a source failure — a failed source degrades its own results
 * and is reported through `completeness`, so callers cannot mistake a partial
 * projection for a complete one.
 */
export async function buildLibraryResourceProjection(
  options: BuildLibraryProjectionOptions
): Promise<LibraryResourceProjection> {
  const filter = options.filter ?? "all";
  const scope = options.scope;
  const transport = options.transport ?? defaultLibraryTransport;

  // One scope query, reused verbatim for every source request this filter needs.
  const scopeQuery = getDocumentScopeQuery(scope) as unknown as Record<
    string,
    unknown
  >;
  const planned = new Set(sourcesForFilter(filter));

  // Only the sources that can actually satisfy the filter are requested. A
  // Widgets projection issues no GETs at all.
  const fetches = await Promise.all([
    ...IMAGE_SOURCES.filter((source) => planned.has(source.request)).map((source) =>
      fetchImageSource(transport, scopeQuery, source.tag)
    ),
    ...(planned.has("document_artifact")
      ? [fetchDocumentSource(transport, scopeQuery)]
      : []),
  ]);

  const sources = fetches.map((fetch) => fetch.outcome);
  const rejected = fetches.flatMap((fetch) => fetch.rejected);

  // Cross-source dedup is keyed on the source-family-qualified presentation
  // key, never on the raw ID, so same-ID records from different families both
  // survive. Same-family repeats collapse only on an exact key match.
  const deduped = new Map<string, LibraryResource>();
  for (const resource of fetches.flatMap((fetch) => fetch.resources)) {
    if (!deduped.has(resource.presentationKey)) {
      deduped.set(resource.presentationKey, resource);
    }
  }

  const allResources = [...deduped.values()];
  const filtered =
    filter === "widgets"
      ? []
      : filter === "all"
        ? allResources
        : allResources.filter(
            (resource) =>
              filter === "images"
                ? resource.resourceType === "image"
                : resource.resourceType === "document"
          );

  return {
    filter,
    scope,
    resources: filtered,
    sources,
    completeness: summarize(filter, sources),
    widgetDiscovery: WIDGET_DISCOVERY,
    rejected,
  };
}