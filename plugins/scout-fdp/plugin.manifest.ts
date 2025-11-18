/**
 * SCOUT-FDP Plugin Manifest
 * Firefox DevTools Protocol Edition
 *
 * This is a DORMANT plugin scaffold for future Scout integration
 * via Firefox DevTools Protocol (FDP).
 *
 * STATUS: Disabled by default, no active hooks.
 */

export default {
  id: "scout-fdp",
  name: "Scout (Firefox DevTools Protocol)",
  version: "0.1.0",
  enabled: false, // DORMANT: Do not enable
  kind: "system" as const,
  entry: "./index.ts",
  description: "Dormant scaffold for Scout via Firefox DevTools Protocol.",
  settingsChip: null,
  tags: ["devtools", "fdp", "scaffold", "sovereignty"],
  runtimeConfig: {},
  personas: []
};

// NOTE: This plugin is dormant and does nothing until explicitly enabled.
// It is provided as a sovereignty-aligned alternative to Chrome DevTools Protocol.
// No browser connections are active. No Codexify core modules are imported.
