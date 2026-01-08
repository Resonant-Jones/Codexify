---
title: Codexify Plugin SDK
version: 0.1.0
status: draft
owner: @codexify
---

# Codexify Plugin SDK Specification

This document defines the official SDK structure, plugin interface, lifecycle expectations, and integration rules for building and registering Codexify-compatible plugins.

---

## 1. Plugin Interface

All plugins must implement the following lifecycle interface:

```ts
interface CodexifyPlugin {
  id: string
  name: string
  description?: string

  initialize(config: PluginConfig): Promise<void>
  shutdown(): Promise<void>
  healthCheck?(): Promise<PluginHealthStatus>
  getMetrics?(): Promise<PluginMetrics>
}
```

---

## 2. Plugin Manifest

Each plugin must register a manifest (`plugin.json`) with the following fields:

```json
{
  "id": "plugin.codexify.cloudcode",
  "name": "Cloud Code Plugin",
  "entry": "dist/index.js",
  "version": "0.1.0",
  "permissions": ["network", "filesystem"],
  "dependencies": [],
  "auth": {
    "type": "oauth2",
    "provider": "google",
    "scopes": ["openid", "profile"]
  }
}
```

---

## 3. Authentication & External Services

Codexify supports OAuth-style integrations via browser redirection or CLI tokens. The plugin must:

- Redirect the user to a known login URL
- Exchange the authorization code or token
- Store and reuse the token locally
- Refresh if needed via `refresh_token`

Plugins that support OAuth should expose:

```ts
interface OAuthCapablePlugin extends CodexifyPlugin {
  startAuthFlow(): Promise<string>
  completeAuthFlow(code: string): Promise<AuthTokens>
}
```

---

## 4. Execution Environment

Plugins run in a sandboxed JS/TS environment (Node-compatible). Access is governed by:

- Explicit manifest permissions
- Plugin health & metrics
- User consent (future release)

---

## 5. Distribution & Validation

Plugins intended for public use must pass SDK linting and conform to:

- Stable interface
- Health + metrics endpoint
- No side effects without user action
- Auth must respect user consent and token visibility

Plugins for personal/local use may skip these checks but will not be eligible for Codexify Registry distribution.

---

## 6. Example Plugin Wrappers

To wrap external services like OpenAI Codex or Cloud Code:

- Create a plugin with a tool-call interface: `invokeCodex(query: string)`
- Support API key or OAuth injection via `.env` or runtime secrets
- Route completions, transforms, or generation via a common interface

---

## 7. Future Extensions

Planned features:

- Plugin scaffolding generator (`npx create-codexify-plugin`)
- Plugin testing harness
- Plugin graph dependencies
- Local token vault integration

---

This SDK enables agents and developers to generate plugins declaratively or via interactive scaffolds.

Contributions welcome.
