/// <reference path="./chrome.d.ts" />

// Extension-local page-capture contract shared by the MV3 service worker
// (the Chrome Page Permission Broker) and the side panel (the capture UI).
// This seam is governed by ADR-076: explicit, user-initiated, read-only page
// observation with a local preview. It must not grow Guardian transport,
// attachment, persistence, or browser-action semantics.

export const PAGE_CAPTURE_MESSAGE = "codexify:page-capture:request"

export type PageCaptureMode = "selected_text" | "visible_page_text"

export const PAGE_CAPTURE_MODES: readonly PageCaptureMode[] = [
  "selected_text",
  "visible_page_text",
]

export function isPageCaptureMode(value: unknown): value is PageCaptureMode {
  return value === "selected_text" || value === "visible_page_text"
}

export const MAX_PAGE_CAPTURE_BYTES = 65536

export const PAGE_CAPTURE_EXTRACTOR_VERSION = "chrome-isolated-reader-v1"

export const PAGE_CAPTURE_SANITIZATION_VERSION = "chrome-page-capture-sanitization-v1"

export interface PageCaptureSanitizationEvidence {
  version: string
  topLevelDocumentOnly: boolean
  framesAndEmbedsExcluded: boolean
  formControlValuesExcluded: boolean
  editableContentExcluded: boolean
  hiddenContentExcluded: boolean
  scriptsAndStylesExcluded: boolean
}

export const PAGE_CAPTURE_SANITIZATION_EVIDENCE: PageCaptureSanitizationEvidence = {
  version: PAGE_CAPTURE_SANITIZATION_VERSION,
  topLevelDocumentOnly: true,
  framesAndEmbedsExcluded: true,
  formControlValuesExcluded: true,
  editableContentExcluded: true,
  hiddenContentExcluded: true,
  scriptsAndStylesExcluded: true,
}

export type PageCaptureFailureCode =
  | "permission_denied"
  | "protected_page"
  | "tab_unavailable"
  | "document_unavailable"
  | "empty_selection"
  | "empty_content"
  | "unsupported_mode"
  | "capture_failed"

// Bounded, user-facing failure text. Raw Chrome exception details must never
// reach the user through this surface.
export const PAGE_CAPTURE_FAILURE_MESSAGES: Record<PageCaptureFailureCode, string> = {
  permission_denied:
    "Chrome has not granted page access for this tab. Click the Codexify toolbar action on the page you want to capture, then try again.",
  protected_page: "This page is protected by Chrome and cannot be captured.",
  tab_unavailable: "No accessible active page was found to capture.",
  document_unavailable:
    "The page document identity could not be confirmed, so the capture was rejected.",
  empty_selection: "Select some text on the page before capturing the selection.",
  empty_content: "No visible page text was found to capture.",
  unsupported_mode: "That capture mode is not supported.",
  capture_failed: "The page capture could not be completed.",
}

export interface PageCaptureRequest {
  type: typeof PAGE_CAPTURE_MESSAGE
  mode: PageCaptureMode
}

export function isPageCaptureRequest(value: unknown): value is PageCaptureRequest {
  if (!value || typeof value !== "object") return false
  const candidate = value as { type?: unknown; mode?: unknown }
  return candidate.type === PAGE_CAPTURE_MESSAGE && isPageCaptureMode(candidate.mode)
}

export interface PageCaptureSuccess {
  captureRequestId: string
  mode: PageCaptureMode
  tabId: number
  documentId: string
  sourceUrl: string
  sourceOrigin: string
  sourceTitle: string
  capturedAt: string
  content: string
  contentByteLength: number
  originalContentByteLength: number
  truncated: boolean
  extractorVersion: string
  sanitization: PageCaptureSanitizationEvidence
}

export type PageCaptureResponse =
  | { ok: true; capture: PageCaptureSuccess }
  | { ok: false; code: PageCaptureFailureCode; message: string }

export function buildPageCaptureFailure(code: PageCaptureFailureCode): PageCaptureResponse {
  return { ok: false, code, message: PAGE_CAPTURE_FAILURE_MESSAGES[code] }
}

export function isPageCaptureResponse(value: unknown): value is PageCaptureResponse {
  if (!value || typeof value !== "object") return false
  const candidate = value as { ok?: unknown; capture?: unknown; code?: unknown; message?: unknown }
  if (candidate.ok === true) {
    return typeof candidate.capture === "object" && candidate.capture !== null
  }
  return (
    candidate.ok === false &&
    typeof candidate.code === "string" &&
    candidate.code in PAGE_CAPTURE_FAILURE_MESSAGES &&
    typeof candidate.message === "string"
  )
}

// ── Isolated-world reader ──────────────────────────────────────────────────
//
// pageCaptureReader runs inside the page's isolated execution world in the
// top frame only. chrome.scripting serializes this function with
// Function.prototype.toString, so it must remain completely self-contained:
// no references to module constants, imports, or closures. Keep the
// extraction semantics below aligned with the Electron Browser Host
// reference reader (browser_host/src/runtime/remote-tab.js captureRenderer):
// same excluded tags, same normalization, same 65,536 UTF-8 byte bound.

export interface PageCaptureReaderSuccess {
  text: string
  byteLength: number
  originalByteLength: number
  truncated: boolean
}

export type PageCaptureReaderErrorCode = "empty_selection" | "empty_content" | "unknown_capture_mode"

export interface PageCaptureReaderFailure {
  errorCode: PageCaptureReaderErrorCode
}

export type PageCaptureReaderOutput = PageCaptureReaderSuccess | PageCaptureReaderFailure

export function pageCaptureReader(mode: string): PageCaptureReaderOutput {
  const MAX_BYTES = 65536
  const EXCLUDED_TAGS = new Set([
    "INPUT",
    "TEXTAREA",
    "SELECT",
    "OPTION",
    "BUTTON",
    "SCRIPT",
    "STYLE",
    "NOSCRIPT",
    "TEMPLATE",
    "IFRAME",
    "FRAME",
    "OBJECT",
    "EMBED",
    "PORTAL",
  ])
  const encoder = new TextEncoder()
  const decoder = new TextDecoder()
  const byteLengthOf = (value: string): number => encoder.encode(value).length
  const truncateUtf8 = (value: string): { text: string; byteLength: number; truncated: boolean } => {
    const encoded = encoder.encode(value)
    if (encoded.length <= MAX_BYTES) {
      return { text: value, byteLength: encoded.length, truncated: false }
    }
    let end = MAX_BYTES
    while (end > 0 && (encoded[end] & 0xc0) === 0x80) end -= 1
    const sliced = encoded.slice(0, end)
    return { text: decoder.decode(sliced), byteLength: sliced.length, truncated: true }
  }
  const normalize = (value: string): string =>
    value
      .replace(/\u0000/g, "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim()
  const isExcludedElement = (element: Element | null): boolean => {
    if (!element || element.nodeType !== 1) return false
    if (EXCLUDED_TAGS.has(element.tagName)) return true
    if ((element as HTMLElement).hidden) return true
    if (element.getAttribute("aria-hidden") === "true") return true
    if (
      (element as HTMLElement).isContentEditable ||
      element.getAttribute("contenteditable") === "true"
    ) {
      return true
    }
    const style = window.getComputedStyle(element)
    return (
      style.display === "none" ||
      style.visibility === "hidden" ||
      style.visibility === "collapse"
    )
  }
  const isNodeExcluded = (node: Node | null): boolean => {
    let current = node && node.nodeType === 1 ? (node as Element) : node?.parentElement ?? null
    while (current) {
      if (isExcludedElement(current)) return true
      current = current.parentElement
    }
    return false
  }
  const collectVisibleText = (): PageCaptureReaderSuccess => {
    const body = document.body
    if (!body) return { text: "", byteLength: 0, originalByteLength: 0, truncated: false }
    const parts: string[] = []
    const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT)
    let node = walker.nextNode()
    while (node) {
      if (!isNodeExcluded(node)) {
        const text = normalize(node.nodeValue ?? "")
        if (text) parts.push(text)
      }
      node = walker.nextNode()
    }
    const fullText = normalize(parts.join("\n"))
    const bounded = truncateUtf8(fullText)
    return {
      text: bounded.text,
      byteLength: bounded.byteLength,
      originalByteLength: byteLengthOf(fullText),
      truncated: bounded.truncated,
    }
  }
  const selectedText = (): PageCaptureReaderOutput => {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed || selection.rangeCount < 1) {
      return { errorCode: "empty_selection" }
    }
    const range = selection.getRangeAt(0)
    if (
      isNodeExcluded(range.startContainer) ||
      isNodeExcluded(range.endContainer) ||
      isNodeExcluded(range.commonAncestorContainer)
    ) {
      return { errorCode: "empty_selection" }
    }
    const fragment = range.cloneContents()
    if (
      fragment.querySelector &&
      fragment.querySelector(
        "input,textarea,select,option,button,script,style,noscript,template,iframe,frame,object,embed,portal,[contenteditable='true']",
      )
    ) {
      return { errorCode: "empty_selection" }
    }
    const fullText = normalize(selection.toString())
    if (fullText === "") return { errorCode: "empty_selection" }
    const bounded = truncateUtf8(fullText)
    return {
      text: bounded.text,
      byteLength: bounded.byteLength,
      originalByteLength: byteLengthOf(fullText),
      truncated: bounded.truncated,
    }
  }
  if (mode === "selected_text") return selectedText()
  if (mode === "visible_page_text") {
    const visible = collectVisibleText()
    if (visible.text === "" || visible.originalByteLength === 0) {
      return { errorCode: "empty_content" }
    }
    return visible
  }
  return { errorCode: "unknown_capture_mode" }
}

// ── Trusted-side broker helpers ────────────────────────────────────────────

export function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).length
}

export function truncateUtf8Bytes(
  value: string,
  maxBytes: number = MAX_PAGE_CAPTURE_BYTES,
): { text: string; byteLength: number; truncated: boolean } {
  const encoded = new TextEncoder().encode(value)
  if (encoded.length <= maxBytes) {
    return { text: value, byteLength: encoded.length, truncated: false }
  }
  let end = maxBytes
  while (end > 0 && (encoded[end] & 0xc0) === 0x80) end -= 1
  const sliced = encoded.subarray(0, end)
  return { text: new TextDecoder().decode(sliced), byteLength: sliced.length, truncated: true }
}

export interface PageCaptureTabSnapshot {
  id?: number
  url?: string
  title?: string
}

export type PageCaptureTarget =
  | { ok: true; tabId: number; url: string }
  | { ok: false; code: PageCaptureFailureCode }

const PROTECTED_STORE_HOSTS = new Set(["chromewebstore.google.com", "chrome.google.com"])

// A hidden tab URL means Chrome has not granted this extension page authority
// for that tab; the activeTab grant exists only for the tab on which the user
// invoked the extension action. Missing authority fails closed instead of
// requesting persistent host access.
export function classifyCaptureTarget(
  tab: PageCaptureTabSnapshot | null | undefined,
): PageCaptureTarget {
  if (
    !tab ||
    typeof tab.id !== "number" ||
    !Number.isInteger(tab.id) ||
    tab.id < 0
  ) {
    return { ok: false, code: "tab_unavailable" }
  }
  const url = typeof tab.url === "string" && tab.url !== "" ? tab.url : ""
  if (url === "") return { ok: false, code: "permission_denied" }
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    return { ok: false, code: "protected_page" }
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return { ok: false, code: "protected_page" }
  }
  if (PROTECTED_STORE_HOSTS.has(parsed.hostname.toLowerCase())) {
    return { ok: false, code: "protected_page" }
  }
  return { ok: true, tabId: tab.id, url }
}

// Maps a chrome.scripting exception to a bounded failure code. The raw
// Chrome error text is never surfaced.
export function mapBrokerException(error: unknown): PageCaptureFailureCode {
  const message = error instanceof Error ? error.message : String(error ?? "")
  if (/cannot access|host permission|permission/i.test(message)) return "permission_denied"
  return "capture_failed"
}

export interface NormalizeInjectionCaptureInput {
  mode: PageCaptureMode
  tab: PageCaptureTabSnapshot
  documentId: unknown
  readerResult: unknown
  now?: () => string
  generateId?: () => string
}

interface RawReaderResult {
  text?: unknown
  byteLength?: unknown
  originalByteLength?: unknown
  errorCode?: unknown
}

const MAX_SANE_ORIGINAL_BYTES = 2147483647

// Normalizes one isolated-world injection into the extension-local capture
// record. Everything coming from the page is untrusted data: byte lengths are
// re-derived on the trusted side, and a capture without a valid main-frame
// Chrome documentId fails closed.
export function normalizeInjectionCapture(input: NormalizeInjectionCaptureInput): PageCaptureResponse {
  const { mode } = input
  if (typeof input.documentId !== "string" || input.documentId === "") {
    return buildPageCaptureFailure("document_unavailable")
  }
  const raw = (input.readerResult ?? null) as RawReaderResult | null
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return buildPageCaptureFailure("capture_failed")
  }
  if (typeof raw.errorCode === "string") {
    if (raw.errorCode === "empty_selection" || raw.errorCode === "empty_content") {
      return buildPageCaptureFailure(raw.errorCode)
    }
    if (raw.errorCode === "unknown_capture_mode") {
      return buildPageCaptureFailure("unsupported_mode")
    }
    return buildPageCaptureFailure("capture_failed")
  }
  if (typeof raw.text !== "string" || raw.text === "") {
    return buildPageCaptureFailure("empty_content")
  }
  const bounded = truncateUtf8Bytes(raw.text)
  if (bounded.text === "") return buildPageCaptureFailure("empty_content")
  const claimedOriginal =
    typeof raw.originalByteLength === "number" &&
    Number.isInteger(raw.originalByteLength) &&
    raw.originalByteLength >= 0 &&
    raw.originalByteLength <= MAX_SANE_ORIGINAL_BYTES
      ? raw.originalByteLength
      : bounded.byteLength
  const originalContentByteLength = Math.max(claimedOriginal, bounded.byteLength)
  const sourceUrl = typeof input.tab.url === "string" ? input.tab.url : ""
  let sourceOrigin = ""
  if (sourceUrl) {
    try {
      sourceOrigin = new URL(sourceUrl).origin
    } catch {
      sourceOrigin = ""
    }
  }
  const capture: PageCaptureSuccess = {
    captureRequestId: input.generateId?.() ?? crypto.randomUUID(),
    mode,
    tabId: typeof input.tab.id === "number" ? input.tab.id : -1,
    documentId: input.documentId,
    sourceUrl,
    sourceOrigin,
    sourceTitle:
      typeof input.tab.title === "string" ? input.tab.title.slice(0, 512) : "",
    capturedAt: (input.now ?? (() => new Date().toISOString()))(),
    content: bounded.text,
    contentByteLength: bounded.byteLength,
    originalContentByteLength,
    truncated: originalContentByteLength > bounded.byteLength,
    extractorVersion: PAGE_CAPTURE_EXTRACTOR_VERSION,
    sanitization: { ...PAGE_CAPTURE_SANITIZATION_EVIDENCE },
  }
  return { ok: true, capture }
}

// ── Side-panel capture client ──────────────────────────────────────────────

export interface PageCaptureClient {
  requestPageCapture(mode: PageCaptureMode): Promise<PageCaptureResponse>
}

export const chromePageCaptureClient: PageCaptureClient = {
  requestPageCapture: async (mode) => {
    if (
      typeof chrome === "undefined" ||
      typeof chrome.runtime?.sendMessage !== "function"
    ) {
      return buildPageCaptureFailure("capture_failed")
    }
    try {
      const response = await chrome.runtime.sendMessage<PageCaptureResponse>({
        type: PAGE_CAPTURE_MESSAGE,
        mode,
      })
      return isPageCaptureResponse(response)
        ? response
        : buildPageCaptureFailure("capture_failed")
    } catch {
      return buildPageCaptureFailure("capture_failed")
    }
  },
}
