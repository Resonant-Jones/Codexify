import { describe, expect, it, vi } from "vitest";

import {
  buildLibraryResourceProjection,
  sourcesForFilter,
  toPresentationKey,
  type LibraryResourceProjection,
  type LibraryResourceTransport,
} from "@/components/library/libraryResourceProjection";
import type { DocumentsScope } from "@/components/documents/documentScopeProjection";

/* ── Fixtures ─────────────────────────────────────────────────────────── */

const PROJECT_SCOPE: DocumentsScope = { kind: "project", projectId: 7, threadId: null };
const THREAD_SCOPE: DocumentsScope = { kind: "thread", projectId: 7, threadId: 42 };
const GLOBAL_SCOPE: DocumentsScope = { kind: "project", projectId: null, threadId: null };

type Call = { path: string; params: Record<string, unknown> | undefined };

/**
 * Read-only recording transport. It only implements `get`, mirroring the
 * production transport type, and asserts no mutation verb is ever reachable.
 */
function createTransport(
  handler: (call: Call) => { data?: unknown } | Promise<{ data?: unknown }>
) {
  const calls: Call[] = [];
  const transport: LibraryResourceTransport = {
    get: vi.fn(async (path: string, config?: { params?: Record<string, unknown> }) => {
      const call: Call = { path, params: config?.params };
      calls.push(call);
      return handler(call);
    }),
  };
  return { transport, calls };
}

/** Default handler: two image families plus a mixed document response. */
function defaultHandler(dataByPath: Record<string, unknown>) {
  return (call: Call) => {
    const family = call.params?.tag === "generated" ? "generated" : "uploaded";
    if (call.path === "/media/images") {
      return { data: dataByPath[`images:${family}`] ?? { images: [], count: 0 } };
    }
    return { data: dataByPath.documents ?? { documents: [], count: 0 } };
  };
}

const UPLOADED_IMAGE = {
  id: "img-1",
  project_id: 7,
  src_url: "/media/images/one.png?sig=a",
  filename: "one.png",
  mime_type: "image/png",
  filesize: 1024,
  source_tag: null,
  created_at: "2026-10-01T00:00:00",
};

const GENERATED_IMAGE = {
  id: "img-1",
  project_id: 7,
  src_url: "/media/images/generated.png?sig=b",
  filename: "A generated scene",
  mime_type: null,
  filesize: null,
  source_tag: "generated",
  created_at: "2026-10-02T00:00:00",
};

const UPLOADED_DOCUMENT = {
  id: "doc-1",
  document_id: "doc-1",
  artifact_type: "uploaded",
  title: "notes.pdf",
  filename: "notes.pdf",
  format: null,
  project_id: 7,
  thread_id: 42,
  thread_ids: [42],
  relation: null,
  relations: [],
  src_url: "/media/document-artifacts/notes.pdf?sig=c",
  filesize: 2048,
  mime_type: "application/pdf",
  source_tag: null,
  embedding_status: "complete",
  created_at: "2026-10-03T00:00:00",
};

const GENERATED_DOCUMENT = {
  id: "doc-2",
  document_id: "doc-2",
  artifact_type: "generated",
  title: "Generated brief",
  filename: null,
  format: "md",
  project_id: 7,
  thread_id: 42,
  thread_ids: [42],
  relations: ["produced"],
  src_url: null,
  mime_type: "text/markdown",
  source_tag: "generated",
  embedding_status: null,
  created_at: "2026-10-04T00:00:00",
};

/* ── Proof: type classification independent of origin ─────────────────── */

describe("resource type classification", () => {
  it("classifies uploaded and generated records by type, never by origin", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:uploaded": { images: [UPLOADED_IMAGE], count: 1 },
        "images:generated": { images: [GENERATED_IMAGE], count: 1 },
        documents: {
          documents: [UPLOADED_DOCUMENT, GENERATED_DOCUMENT],
          count: 2,
        },
      })
    );

    const all = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });
    const images = await buildLibraryResourceProjection({
      filter: "images",
      scope: PROJECT_SCOPE,
      transport,
    });
    const documents = await buildLibraryResourceProjection({
      filter: "documents",
      scope: PROJECT_SCOPE,
      transport,
    });

    // A generated image is an Image, not a separate "Generated" bucket.
    expect(images.resources.map((r) => r.sourceId).sort()).toEqual(["img-1", "img-1"]);
    expect(images.resources.every((r) => r.resourceType === "image")).toBe(true);
    // A generated document is a Document.
    expect(documents.resources.map((r) => r.sourceId).sort()).toEqual(["doc-1", "doc-2"]);
    expect(documents.resources.every((r) => r.resourceType === "document")).toBe(true);
    // Origin stays orthogonal and preserved.
    expect(all.resources.filter((r) => r.origin === "generated")).toHaveLength(2);
    expect(all.resources.filter((r) => r.origin === "uploaded")).toHaveLength(2);
  });

  it("refuses to classify a document whose authoritative type is missing", async () => {
    const { transport } = createTransport(
      defaultHandler({
        documents: {
          documents: [{ id: "doc-x", title: "mystery" }],
          count: 1,
        },
      })
    );

    const projection = await buildLibraryResourceProjection({
      filter: "documents",
      scope: PROJECT_SCOPE,
      transport,
    });

    expect(projection.resources).toHaveLength(0);
    expect(projection.rejected).toEqual([
      expect.objectContaining({
        reason: "unclassifiable_document",
        sourceId: "doc-x",
        source: "document_artifact",
      }),
    ]);
  });

  it("never emits a widget while widget records are unproven", async () => {
    const { transport } = createTransport(defaultHandler({}));
    const projection = await buildLibraryResourceProjection({
      filter: "widgets",
      scope: PROJECT_SCOPE,
      transport,
    });

    expect(projection.resources).toEqual([]);
    expect(projection.widgetDiscovery.available).toBe(false);
    expect(projection.widgetDiscovery.reason).toMatch(/authoritative Widget backing record/i);
  });
});

/* ── Proof: source-family identity collisions ─────────────────────────── */

describe("source-family identity", () => {
  it("keeps same raw ID from different families distinct", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:uploaded": { images: [UPLOADED_IMAGE], count: 1 },
        "images:generated": { images: [{ ...GENERATED_IMAGE, id: "img-1" }], count: 1 },
      })
    );

    const projection = await buildLibraryResourceProjection({
      filter: "images",
      scope: PROJECT_SCOPE,
      transport,
    });

    expect(projection.resources).toHaveLength(2);
    expect(projection.resources.map((r) => r.sourceId)).toEqual(["img-1", "img-1"]);
    expect(new Set(projection.resources.map((r) => r.presentationKey)).size).toBe(2);
    expect(projection.resources.map((r) => r.sourceFamily).sort()).toEqual([
      "generated_image",
      "uploaded_image",
    ]);
    // Canonical IDs survive verbatim.
    expect(projection.resources.every((r) => r.sourceId === "img-1")).toBe(true);
  });

  it("does not deduplicate across sources by raw ID alone", async () => {
    const { transport } = createTransport(
      defaultHandler({
        // A document and an image share the same raw ID.
        "images:uploaded": { images: [UPLOADED_IMAGE], count: 1 },
        documents: { documents: [{ ...UPLOADED_DOCUMENT, id: "img-1" }], count: 1 },
      })
    );

    const projection = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    expect(projection.resources).toHaveLength(2);
    expect(new Set(projection.resources.map((r) => r.presentationKey)).size).toBe(2);
    expect(
      projection.resources.map((r) => r.resourceType).sort()
    ).toEqual(["document", "image"]);
  });

  it("builds family-qualified keys rather than raw IDs", () => {
    expect(toPresentationKey("uploaded_image", "5")).toBe("uploaded_image:5");
    expect(toPresentationKey("generated_document", "5")).toBe("generated_document:5");
  });
});

/* ── Proof: provenance preservation ───────────────────────────────────── */

describe("provenance preservation", () => {
  it("preserves origin and original source metadata", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:generated": { images: [GENERATED_IMAGE], count: 1 },
        documents: { documents: [GENERATED_DOCUMENT], count: 1 },
      })
    );

    const projection = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });
    const generatedImage = projection.resources.find(
      (r) => r.sourceFamily === "generated_image"
    );

    expect(generatedImage).toBeDefined();
    expect(generatedImage!.origin).toBe("generated");
    expect(generatedImage!.sourceTag).toBe("generated");
    // Original record preserved untouched, including fields with no typed slot.
    expect(generatedImage!.raw).toEqual(GENERATED_IMAGE);
    expect(generatedImage!.raw.filesize).toBeNull();
    expect(generatedImage!.mimeType).toBeNull();

    const generatedDocument = projection.resources.find(
      (r) => r.sourceFamily === "generated_document"
    );
    expect(generatedDocument!.origin).toBe("generated");
    expect(generatedDocument!.raw.format).toBe("md");
    expect(generatedDocument!.raw.embedding_status).toBeNull();
    expect(generatedDocument!.threadIds).toEqual([42]);
  });

  it("does not let a missing image source_tag overwrite upload provenance", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:uploaded": { images: [UPLOADED_IMAGE], count: 1 },
      })
    );

    const projection = await buildLibraryResourceProjection({
      filter: "images",
      scope: PROJECT_SCOPE,
      transport,
    });

    expect(projection.resources[0].origin).toBe("uploaded");
    expect(projection.resources[0].sourceTag).toBeNull();
  });
});

/* ── Proof: scope propagation ─────────────────────────────────────────── */

describe("authorized scope propagation", () => {
  it("applies the identical project scope to every source request", async () => {
    const { transport, calls } = createTransport(defaultHandler({}));
    await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    expect(calls).toHaveLength(3);
    for (const call of calls) {
      expect(call.params).toMatchObject({ limit: 100, project_id: 7 });
      expect(call.params).not.toHaveProperty("thread_id");
    }
  });

  it("applies the identical thread scope to every source request", async () => {
    const { transport, calls } = createTransport(defaultHandler({}));
    await buildLibraryResourceProjection({ scope: THREAD_SCOPE, transport });

    expect(calls).toHaveLength(3);
    for (const call of calls) {
      // Documents rejects project_id + thread_id together, so scope stays single.
      expect(call.params).toMatchObject({ limit: 100, thread_id: 42 });
      expect(call.params).not.toHaveProperty("project_id");
    }
  });

  it("keeps an unscoped projection unscoped for every source", async () => {
    const { transport, calls } = createTransport(defaultHandler({}));
    await buildLibraryResourceProjection({ scope: GLOBAL_SCOPE, transport });

    for (const call of calls) {
      expect(call.params).not.toHaveProperty("project_id");
      expect(call.params).not.toHaveProperty("thread_id");
    }
  });

  it("reads both image families and documents from authorized read paths", async () => {
    const { transport, calls } = createTransport(defaultHandler({}));
    await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    const images = calls.filter((c) => c.path === "/media/images");
    expect(images).toHaveLength(2);
    expect(images.map((c) => c.params?.tag)).toEqual([undefined, "generated"]);
    expect(
      calls.filter((c) => c.path === "/media/document-artifacts")
    ).toHaveLength(1);
  });

  it("never forwards a client-supplied account identity", async () => {
    const { transport, calls } = createTransport(defaultHandler({}));
    await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    for (const call of calls) {
      expect(call.params).not.toHaveProperty("user_id");
      expect(call.params).not.toHaveProperty("X-User-Id");
    }
  });
});

/* ── Proof: partial failures and bounded lists ────────────────────────── */

describe("completeness reporting", () => {
  it("marks a projection incomplete when a source fails", async () => {
    const { transport } = createTransport((call) => {
      if (call.params?.tag === "generated") throw new Error("image store unreachable");
      if (call.path === "/media/images") {
        return { data: { images: [UPLOADED_IMAGE], count: 1 } };
      }
      return { data: { documents: [UPLOADED_DOCUMENT], count: 1 } };
    });

    const projection = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    expect(projection.completeness.complete).toBe(false);
    expect(projection.completeness.failedSources).toEqual(["generated_image"]);
    // The failed source degrades alone; healthy sources survive.
    expect(projection.resources).toHaveLength(2);
    expect(
      projection.sources.find((s) => s.source === "generated_image")?.error
    ).toMatch(/image store unreachable/);
  });

  it("never presents a partial All projection as complete", async () => {
    const { transport } = createTransport(() => {
      throw new Error("backend down");
    });

    const projection = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    expect(projection.resources).toEqual([]);
    expect(projection.completeness.complete).toBe(false);
    expect(projection.completeness.failedSources.sort()).toEqual([
      "document_artifact",
      "generated_image",
      "uploaded_image",
    ]);
  });

  it("marks a list that reached the request limit as bounded", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:uploaded": {
          images: Array.from({ length: 100 }, (_, i) => ({ ...UPLOADED_IMAGE, id: `i-${i}` })),
          count: 100,
        },
      })
    );

    const projection = await buildLibraryResourceProjection({
      filter: "images",
      scope: PROJECT_SCOPE,
      transport,
    });

    expect(projection.completeness.complete).toBe(false);
    expect(projection.completeness.boundedSources).toEqual(["uploaded_image"]);
    expect(projection.resources).toHaveLength(100);
  });

  it("reports a saturated merged document list as bounded", async () => {
    const { transport } = createTransport(
      defaultHandler({
        documents: {
          documents: Array.from({ length: 100 }, (_, i) => ({
            ...UPLOADED_DOCUMENT,
            id: `d-${i}`,
          })),
          count: 100,
        },
      })
    );

    const projection = await buildLibraryResourceProjection({
      filter: "documents",
      scope: PROJECT_SCOPE,
      transport,
    });

    expect(projection.completeness.boundedSources).toEqual(["document_artifact"]);
  });

  it("scopes completeness to the sources a filter actually uses", async () => {
    const { transport } = createTransport((call) => {
      if (call.path === "/media/document-artifacts") throw new Error("documents down");
      return { data: { images: [], count: 0 } };
    });

    const images = await buildLibraryResourceProjection({
      filter: "images",
      scope: PROJECT_SCOPE,
      transport,
    });
    const all = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    // A document failure does not make the Images filter incomplete.
    expect(images.completeness.complete).toBe(true);
    expect(all.completeness.complete).toBe(false);
    expect(all.completeness.failedSources).toEqual(["document_artifact"]);
    expect(sourcesForFilter("widgets")).toEqual([]);
  });
});

/* ── Proof: no synthetic resources, no mutation ───────────────────────── */

describe("no synthetic resources and no mutation", () => {
  it("rejects mock records instead of projecting them as real", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:uploaded": {
          images: [{ ...UPLOADED_IMAGE, id: "mock-1", mock: true }],
          count: 1,
        },
        documents: {
          documents: [{ ...UPLOADED_DOCUMENT, id: "mock-2", mock: true }],
          count: 1,
        },
      })
    );

    const projection = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    expect(projection.resources).toEqual([]);
    expect(
      projection.rejected.filter((r) => r.reason === "synthetic_record").map((r) => r.sourceId)
    ).toEqual(["mock-1", "mock-2"]);
  });

  it("issues no mutation requests", async () => {
    const { transport, calls } = createTransport(defaultHandler({}));
    const projection: LibraryResourceProjection = await buildLibraryResourceProjection({
      scope: PROJECT_SCOPE,
      transport,
    });

    // The transport type exposes `get` only, so no mutating verb is reachable.
    expect(Object.keys(transport)).toEqual(["get"]);
    expect((transport as unknown as Record<string, unknown>).post).toBeUndefined();
    expect((transport as unknown as Record<string, unknown>).delete).toBeUndefined();
    expect(
      calls.every((c) => c.path === "/media/images" || c.path === "/media/document-artifacts")
    ).toBe(true);
    expect(projection.sources.every((s) => s.status !== "failed")).toBe(true);
  });

  it("tolerates malformed payloads without fabricating resources", async () => {
    const { transport } = createTransport(
      defaultHandler({
        "images:uploaded": { images: [{ filename: "no id" }, null, "nope"], count: 3 },
        documents: { documents: undefined, count: 0 },
      })
    );

    const projection = await buildLibraryResourceProjection({ scope: PROJECT_SCOPE, transport });

    expect(projection.resources).toEqual([]);
    expect(projection.rejected.every((r) => r.reason === "missing_source_id")).toBe(true);
  });
});