/**
 * Gallery item shapes.
 *
 * `GalleryItem` is the **renderable** gallery item: an image reference with an
 * optional canonical identity, project scope, and source tag. The gallery grid
 * renders it, and Library derives it from its server-backed Images projection.
 *
 * It lives here, outside any component, so that the gallery grid and Library do
 * not depend on a component module to describe their data.
 *
 * This is deliberately distinct from the **browser-local gallery entry** shape
 * in `types/ui.ts` (`{ src, prompt, mock? }`). That one describes what a
 * browser's local gallery cache holds; this one describes what the grid
 * renders. They are not interchangeable, and they use different field
 * vocabularies.
 */
export type GalleryItem = {
  /**
   * Local identity for the tile. It identifies the item within the surface —
   * for Library it is the source-family-qualified presentation key, so two
   * records sharing a raw id across families never collide.
   *
   * This is **not** a storage identifier and must never be sent to a backend
   * route.
   */
  id?: string;
  /**
   * Canonical source identifier, used as the backend **deletion target**.
   *
   * Present only when the source family has a supported deletion contract. It
   * is deliberately distinct from `id`: the presentation identity is
   * source-family-qualified, while this is the raw source record id the
   * backend route expects.
   *
   * Eligibility follows the source *family* alone — never provenance, URL
   * shape, or the presentation identity.
   */
  deletionId?: string;
  src: string;
  prompt: string;
  project?: string | number;
  tag?: string;
};
