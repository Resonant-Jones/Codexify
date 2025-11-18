export default {
  id: "scout-iddb",
  name: "Scout (IDDB Integration)",
  version: "0.1.0",
  enabled: false,
  kind: "system",
  entry: "./index.ts",
  description: "Dormant scaffold for Scout as semantic nodes inside IDDB.",
  settingsChip: null,
  tags: ["iddb", "graph", "semantic", "scaffold"],
  runtimeConfig: {},
  personas: ["./persona/ScoutCurator.shard.pkg.json"]
};
