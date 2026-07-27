import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { injectCssVars } from "../../src/theme"
import { SidePanelApp } from "./SidePanelApp"
import "./sidepanel.css"

injectCssVars()

const root = document.getElementById("root")
if (!root) {
  throw new Error("Codexify side-panel root is missing.")
}

createRoot(root).render(
  <StrictMode>
    <SidePanelApp />
  </StrictMode>,
)
