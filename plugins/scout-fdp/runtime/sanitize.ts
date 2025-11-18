/**
 * SCOUT-FDP HTML Sanitizer (STUB)
 *
 * This file sanitizes HTML content to remove scripts and unsafe elements.
 * Currently dormant - returns content with warning.
 */

/**
 * Sanitization Options
 */
export interface SanitizationOptions {
  /** Allow specific tags */
  allowedTags?: string[];
  /** Allow specific attributes */
  allowedAttributes?: string[];
  /** Strip comments */
  stripComments?: boolean;
  /** Strip event handlers */
  stripEventHandlers?: boolean;
}

/**
 * Sanitize HTML
 *
 * Removes scripts, event handlers, and other unsafe content from HTML.
 *
 * @param html - Raw HTML string
 * @param options - Sanitization options
 * @returns Sanitized HTML
 *
 * @remarks
 * DORMANT STUB: Returns HTML with warning comment.
 *
 * TODO: Future implementation should use DOMPurify:
 * ```typescript
 * import DOMPurify from 'dompurify';
 *
 * export function sanitizeHTML(html: string): string {
 *   return DOMPurify.sanitize(html, {
 *     ALLOWED_TAGS: ['div', 'span', 'p', 'a', 'img', ...],
 *     ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'id', ...],
 *     KEEP_CONTENT: true,
 *     RETURN_DOM: false,
 *     RETURN_DOM_FRAGMENT: false
 *   });
 * }
 * ```
 *
 * @example
 * ```typescript
 * const unsafe = '<script>alert("xss")</script><p>Hello</p>';
 * const safe = sanitizeHTML(unsafe);
 * // Result: '<p>Hello</p>'
 * ```
 */
export async function sanitizeHTML(
  html: string,
  options: SanitizationOptions = {}
): Promise<string> {
  // DORMANT: No actual sanitization
  // Return HTML with warning comment
  const warning =
    "<!-- SCOUT-FDP: HTML not sanitized (dormant mode) -->\n";

  // TODO: Implement DOMPurify integration
  // const clean = DOMPurify.sanitize(html, {
  //   ALLOWED_TAGS: options.allowedTags || DEFAULT_ALLOWED_TAGS,
  //   ALLOWED_ATTR: options.allowedAttributes || DEFAULT_ALLOWED_ATTR,
  //   ...
  // });

  return warning + html;
}

/**
 * Strip scripts from HTML
 *
 * Removes all script tags and inline event handlers.
 *
 * @param html - Raw HTML string
 * @returns HTML without scripts
 *
 * @remarks
 * DORMANT STUB: Returns HTML unchanged.
 *
 * TODO: Implement script stripping:
 * - Remove <script> tags
 * - Remove inline event handlers (onclick, onerror, etc.)
 * - Remove javascript: URLs
 */
export function stripScripts(html: string): string {
  // DORMANT: No script stripping
  // TODO: Implement script removal
  return html;
}

/**
 * Strip event handlers from HTML
 *
 * Removes inline event handler attributes.
 *
 * @param html - Raw HTML string
 * @returns HTML without event handlers
 *
 * @remarks
 * DORMANT STUB: Returns HTML unchanged.
 *
 * TODO: Implement event handler stripping:
 * - Remove onclick, onload, onerror, etc.
 * - Use regex or DOM parsing
 */
export function stripEventHandlers(html: string): string {
  // DORMANT: No event handler stripping
  // TODO: Implement event handler removal
  return html;
}

/**
 * Strip comments from HTML
 *
 * Removes HTML comments.
 *
 * @param html - Raw HTML string
 * @returns HTML without comments
 *
 * @remarks
 * DORMANT STUB: Returns HTML unchanged.
 *
 * TODO: Implement comment stripping
 */
export function stripComments(html: string): string {
  // DORMANT: No comment stripping
  // TODO: Implement comment removal using regex: /<!--[\s\S]*?-->/g
  return html;
}

/**
 * Validate sanitized HTML
 *
 * Checks if HTML is safe after sanitization.
 *
 * @param html - Sanitized HTML string
 * @returns Whether HTML is safe
 *
 * @remarks
 * DORMANT STUB: Always returns true.
 *
 * TODO: Implement safety validation:
 * - Check for remaining script tags
 * - Check for javascript: URLs
 * - Check for data: URLs with scripts
 * - Verify no event handlers remain
 */
export function validateSanitized(html: string): boolean {
  // DORMANT: No validation
  // TODO: Implement safety checks
  return true;
}

// Default allowed tags (for future implementation)
const DEFAULT_ALLOWED_TAGS = [
  "div",
  "span",
  "p",
  "a",
  "img",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "ul",
  "ol",
  "li",
  "table",
  "thead",
  "tbody",
  "tr",
  "td",
  "th",
  "strong",
  "em",
  "code",
  "pre",
  "blockquote"
];

// Default allowed attributes (for future implementation)
const DEFAULT_ALLOWED_ATTR = [
  "href",
  "src",
  "alt",
  "title",
  "class",
  "id",
  "data-*"
];

// TODO: Add custom sanitization rules support
// TODO: Add attribute value validation
// TODO: Add URL scheme validation (http/https only)
// TODO: Add SVG sanitization
// TODO: Add MathML sanitization
// TODO: Add iframe sandboxing support
