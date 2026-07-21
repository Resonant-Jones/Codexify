/// <reference path="./src/chrome.d.ts" />

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
