// NOTE: This plugin is dormant. It will NOT load until explicitly enabled.

/**
 * SCOUT Plugin Manifest
 *
 * This is a dormant inspection plugin scaffold designed for future
 * Codexify DevTools integration. The plugin is registered but intentionally
 * disabled to prevent any runtime interference.
 */

export default {
  id: "scout",
  name: "Scout",
  version: "0.1.0",
  kind: "system" as const,
  enabled: false, // Plugin is dormant and will not activate
  entry: "./index.ts",
  description: "Dormant inspection plugin scaffold for future Codexify DevTools integration.",
  settingsChip: null,
  tags: ["local-first", "inspection", "devtools", "scaffold"],

  runtimeConfig: {},

  personas: [
    {
      shardPath: "./persona/ScoutInspector.shard.pkg.json",
      enabled: false, // Persona is also dormant
    }
  ],

  // Future configuration hooks (all disabled)
  hooks: {
    onInit: null,
    onDestroy: null,
    onMessage: null,
  },

  // Browser extension components (registered but inactive)
  browser: {
    contentScript: "./browser/scoutContentScript.ts",
    background: "./browser/scoutBackground.ts",
    messaging: "./browser/scoutMessaging.ts",
  },

  // Metadata
  meta: {
    author: "Codexify Team",
    license: "MIT",
    repository: null,
    documentation: "./README.md",
  }
};
