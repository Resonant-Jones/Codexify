/**
 * Scout-IDDB Plugin Entry Point
 *
 * DORMANT PLUGIN - NO SIDE EFFECTS
 *
 * This plugin provides a scaffold for mapping Scout logs to IDDB nodes.
 * It is currently disabled and performs no automatic operations.
 */

import manifest from "./plugin.manifest";
import { processScoutToIDDB, processBatch } from "./runtime";
import { handleScoutCuratorRequest } from "./persona/curatorHandler";

// Plugin metadata (exported for introspection)
export const pluginInfo = {
  id: manifest.id,
  name: manifest.name,
  version: manifest.version,
  enabled: manifest.enabled,
  status: "dormant",
  description: manifest.description,
};

// Re-export runtime functions for manual use
export { processScoutToIDDB, processBatch };

// Re-export types for external use
export type {
  RawScoutLog,
  ScoutSanitizedLog,
  ScoutIDDBNode,
  ScoutIDDBRelation,
  ProcessingResult,
  SanitizationConfig,
  NodeGenerationConfig,
} from "./runtime/types";

// Re-export persona handler
export { handleScoutCuratorRequest };

/**
 * Plugin lifecycle hooks (all dormant)
 */
export const lifecycle = {
  /**
   * Called when plugin is loaded (if enabled)
   * Currently does nothing as plugin is disabled
   */
  onLoad: () => {
    // No-op: plugin is dormant
    return {
      success: false,
      reason: "Plugin is disabled in manifest",
    };
  },

  /**
   * Called when plugin is unloaded
   * Currently does nothing as plugin is disabled
   */
  onUnload: () => {
    // No-op: plugin is dormant
    return {
      success: true,
    };
  },

  /**
   * Called when plugin is enabled (future use)
   */
  onEnable: () => {
    // No-op: requires manual activation
    return {
      success: false,
      reason: "Manual activation required - see README.md",
    };
  },

  /**
   * Called when plugin is disabled
   */
  onDisable: () => {
    // No-op: already disabled
    return {
      success: true,
    };
  },
};

/**
 * Plugin capabilities (informational only)
 */
export const capabilities = {
  processLogs: false, // Not active
  writeToIDDB: false, // Never writes
  curatorPersona: false, // Persona is dormant
  realTimeProcessing: false, // Not active
  batchProcessing: false, // Not active
};

/**
 * Configuration interface (for future activation)
 */
export const config = {
  getConfig: () => manifest.runtimeConfig,
  setConfig: (_newConfig: any) => {
    throw new Error(
      "Configuration cannot be changed while plugin is dormant"
    );
  },
};

/**
 * Default export: plugin metadata
 */
export default {
  manifest,
  pluginInfo,
  lifecycle,
  capabilities,
  config,
  processScoutToIDDB,
  processBatch,
  handleScoutCuratorRequest,
};
