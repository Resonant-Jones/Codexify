# SCOUT-FDP: Firefox DevTools Protocol Edition

## Status: DORMANT SCAFFOLD

This plugin is **disabled by default** and contains **no active functionality**.
It is a pure scaffold for future Scout integration via Firefox DevTools Protocol.

---

## Purpose

SCOUT-FDP provides a sovereignty-aligned alternative to Chrome DevTools Protocol (CDP) by targeting **Firefox DevTools Protocol (FDP)**.

This variant of Scout is designed for:
- **Privacy-conscious workflows** using Firefox as the browser runtime
- **Sovereignty-aligned tooling** free from Chrome/Chromium dependencies
- **Future-proofing** against Chrome's proprietary API changes
- **Educational/research contexts** where Firefox is preferred

---

## What is Firefox DevTools Protocol (FDP)?

Firefox DevTools Protocol is Mozilla's remote debugging interface, allowing external tools to:
- Inspect and manipulate the DOM
- Monitor network activity
- Capture CSS cascade information
- Execute JavaScript in page context
- Access layout and rendering data

Unlike CDP, FDP is implemented in Firefox and Gecko-based browsers.

---

## Why Firefox Matters for Sovereignty

1. **Open governance**: Firefox is developed by Mozilla, a non-profit organization
2. **No tracking by default**: Firefox respects user privacy out-of-the-box
3. **Independent rendering engine**: Gecko is not based on Chromium/Blink
4. **Community-driven**: Firefox development is more transparent and community-oriented
5. **Standards-first**: Firefox often implements web standards before proprietary features

---

## Architecture

```
/plugins/scout-fdp/
├── plugin.manifest.ts          # Plugin metadata (disabled)
├── README.md                    # This file
├── index.ts                     # Entry point (stub)
├── /fdp/                        # Firefox DevTools Protocol layer
│   ├── connector.ts             # WebSocket connection stub
│   ├── session.ts               # Session management stub
│   └── commands.ts              # FDP command placeholders
├── /browser/                    # Browser extension stubs
│   ├── devtools-panel.js        # DevTools panel stub
│   ├── devtools-background.js   # Background service stub
│   └── devtools-messaging.ts    # Message protocol stub
├── /runtime/                    # Runtime processing layer
│   ├── index.ts                 # Payload processor
│   ├── sanitize.ts              # Sanitization logic
│   ├── generateLog.ts           # Log generation
│   └── types.ts                 # Type definitions
└── /schemas/                    # JSON schemas
    └── scoutLog.schema.json     # ScoutLog format
```

---

## Current State

### ✅ Implemented (Stubs Only)
- Plugin manifest (disabled)
- Folder structure
- Type definitions
- Placeholder functions

### ❌ NOT Implemented
- Actual FDP connection
- DevTools hooks
- Browser extension integration
- Codexify core integration
- Active scanning functionality

---

## Explicit Non-Features

This scaffold does **NOT**:
- Connect to any browser
- Open any WebSocket connections
- Import Codexify core modules
- Activate any DevTools hooks
- Interfere with existing plugins
- Affect build process
- Contain any executable logic

---

## TODO: Future Integration

### Phase 1: Core FDP Connection
- [ ] Implement WebSocket connector to Firefox remote debugging port
- [ ] Establish session lifecycle management
- [ ] Implement basic command dispatch
- [ ] Add event subscription handling

### Phase 2: DOM & CSS Inspection
- [ ] Implement DOM.getDocument equivalent
- [ ] Capture computed styles via CSS.getComputedStyleForNode
- [ ] Extract layout box models
- [ ] Capture CSS cascade information

### Phase 3: Browser Extension
- [ ] Create Firefox WebExtension manifest
- [ ] Implement DevTools panel UI
- [ ] Add background service for message routing
- [ ] Establish secure messaging between extension and plugin

### Phase 4: Runtime Processing
- [ ] Implement DOMPurify integration for sanitization
- [ ] Build ScoutLog generator with FDP-specific metadata
- [ ] Add redaction summary generation
- [ ] Implement payload validation

### Phase 5: Codexify Integration
- [ ] Add hooks to Codexify plugin system
- [ ] Implement settings UI in Codexify dashboard
- [ ] Add persona support for Firefox-specific agents
- [ ] Create end-to-end tests

### Phase 6: Advanced Features
- [ ] Network monitoring via FDP Network domain
- [ ] Console log capture
- [ ] Performance profiling integration
- [ ] Storage inspection (cookies, localStorage, etc.)

---

## Comparison: CDP vs FDP

| Feature | Chrome DevTools Protocol | Firefox DevTools Protocol |
|---------|-------------------------|--------------------------|
| Governance | Google (proprietary) | Mozilla (open) |
| Browser Support | Chrome, Edge, Brave, Opera | Firefox, Gecko browsers |
| API Stability | Frequent changes | More stable |
| Privacy | Telemetry enabled | Privacy-first |
| Documentation | Extensive | Good, but less examples |
| Ecosystem | Large | Smaller, growing |

---

## Development Notes

### Testing FDP Connections

To manually test FDP connections (future implementation):

1. Start Firefox with remote debugging:
   ```bash
   firefox --start-debugger-server 6000
   ```

2. Connect via WebSocket:
   ```javascript
   const ws = new WebSocket('ws://localhost:6000');
   ```

3. Send FDP commands:
   ```json
   {
     "to": "root",
     "type": "getRoot"
   }
   ```

### Key FDP Domains

- **DOM**: Document inspection and manipulation
- **CSS**: Style and cascade information
- **Network**: HTTP traffic monitoring
- **Console**: Console message access
- **Performance**: Profiling and timing
- **Storage**: Cookie and storage APIs

---

## Security Considerations

When this plugin is activated in the future:

1. **WebSocket security**: Only connect to localhost by default
2. **Command validation**: Sanitize all FDP commands before sending
3. **Payload sanitization**: Use DOMPurify for all DOM content
4. **Redaction**: Implement PII detection and redaction
5. **Permissions**: Request minimal Firefox extension permissions

---

## Contributing

This is a scaffold. Contributions should focus on:
- FDP command mappings
- Type definitions
- Documentation improvements
- Test cases (unit tests only, no integration)

**Do not**:
- Enable the plugin
- Add Codexify dependencies
- Implement active connections
- Change the dormant nature

---

## License

Follows Codexify's main license (see root LICENSE file).

---

## References

- [Firefox Remote Debugging Protocol](https://firefox-source-docs.mozilla.org/devtools/backend/protocol.html)
- [Firefox DevTools API](https://developer.mozilla.org/en-US/docs/Tools/Remote_Debugging)
- [Remote Debugging Protocol Specification](https://wiki.mozilla.org/Remote_Debugging_Protocol)

---

**Last Updated**: 2025-11-18
**Status**: Dormant Scaffold
**Version**: 0.1.0
