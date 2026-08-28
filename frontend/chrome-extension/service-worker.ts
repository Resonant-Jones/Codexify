/// <reference path="./src/chrome.d.ts" />

import {
  buildPageCaptureFailure,
  classifyCaptureTarget,
  isPageCaptureRequest,
  mapBrokerException,
  normalizeInjectionCapture,
  pageCaptureReader,
  type PageCaptureMode,
  type PageCaptureResponse,
} from "./src/pageCapture"

async function configureSidePanelAction(): Promise<void> {
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
}

void configureSidePanelAction().catch(() => undefined)

chrome.runtime.onInstalled.addListener(() => {
  void configureSidePanelAction().catch(() => undefined)
})

chrome.runtime.onStartup.addListener(() => {
  void configureSidePanelAction().catch(() => undefined)
})

// ── Chrome Page Permission Broker (ADR-076) ────────────────────────────────
//
// The service worker mediates every capture between the side panel and the
// observed page. It stays stateless across capture requests, credential-blind,
// network-silent, and persistence-free; it never receives Guardian API keys,
// Bearer session tokens, chat messages, or Command Bus authority.

async function captureActivePage(mode: PageCaptureMode): Promise<PageCaptureResponse> {
  let tabs: chrome.tabs.Tab[] = []
  try {
    tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true })
  } catch {
    return buildPageCaptureFailure("tab_unavailable")
  }
  const tab = tabs[0]
  const target = classifyCaptureTarget(tab)
  if (!target.ok) return buildPageCaptureFailure(target.code)

  let injections: Array<chrome.scripting.InjectionResult> = []
  try {
    // Isolated world (default) and top frame only (allFrames defaults false).
    injections = await chrome.scripting.executeScript({
      target: { tabId: target.tabId, allFrames: false },
      func: pageCaptureReader,
      args: [mode],
    })
  } catch (error) {
    return buildPageCaptureFailure(mapBrokerException(error))
  }
  const injection = Array.isArray(injections) ? injections[0] : undefined
  return normalizeInjectionCapture({
    mode,
    tab,
    documentId: injection?.documentId,
    readerResult: injection?.result,
  })
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!isPageCaptureRequest(message)) return undefined
  void captureActivePage(message.mode).then(
    (response) => sendResponse(response),
    () => sendResponse(buildPageCaptureFailure("capture_failed")),
  )
  return true
})
