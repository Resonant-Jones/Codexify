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
  id?: string;
  src: string;
  prompt: string;
  project?: string | number;
  tag?: string;
};
