type CSSVarMap = Record<string, string>

const BASE_VARS: CSSVarMap = {
  '--radius-micro': '12px',
  '--radius-tile': '19px',
  '--card-radius': '19px',
  '--edge-chrome': '6px',
  '--shell-gap': '16px',
  '--viewport-radius': '19px',
  '--tile-radius': '19px',
  '--page-pad': '0px',
  '--card-pad': '12px',
  '--frame': '1.5px',
  '--bezel': '6px',
  '--rim': '1.5px',
  '--workspace-w': '24rem',
  '--panel-bg': '#1b1b1d',
  '--panel-border': 'rgba(255,255,255,0.08)',
  '--panel-bezel': 'rgba(255,255,255,0.12)',
  '--panel-sheet': '#1f1f22',
  '--panel-sheet-border': 'rgba(255,255,255,0.14)',
  '--chip-bg': '#262629',
  '--text': '#ffffff',
  '--muted': 'rgba(255,255,255,0.88)',
  '--accent': '#8ec5ff',
  '--accent-strong': '#5ab7ff',
}

let alreadyInjected = false

/**
 * Sets baseline CSS custom properties on first render so that AppShell
 * (and any components that mount before it) can rely on design tokens
 * being available. Tokens can be overridden by passing in the same keys.
 */
export function injectCssVars(overrides: CSSVarMap = {}): void {
  if (typeof document === 'undefined' || alreadyInjected) return
  const root = document.documentElement
  const vars = { ...BASE_VARS, ...overrides }
  for (const [key, value] of Object.entries(vars)) {
    if (value == null) continue
    root.style.setProperty(key, value)
  }
  alreadyInjected = true
}

export type { CSSVarMap }
