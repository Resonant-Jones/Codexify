# Browser Host live Electron launch proof
- Status: **next-proof-needed**
- Primary classification: `host_security_assessment`
- Launch method: playwright_electron
- Production entrypoint used: true
- Trusted shell ready: false
- Compatible deterministic negotiation: false
- Remote request before compatibility: false
- Remote loaded after compatibility: false
- Insecure sandbox bypass: false
- Electron binary check: exit null, signal SIGABRT
- Direct entrypoint launch: exit null, signal SIGABRT
- macOS spctl assessment: exit 1; Code Signing subsystem error: true
- Graphical session: Aqua=true
- Capture attempted: false
- Attachment attempted: false
- Cleanup: passed
- Missing proof fields: electron_binary_check, trusted_window_created, preload_loaded, trusted_state_read, compatible_deterministic_negotiation, remote_load_after_compatibility
This packet does not qualify a complete real-Guardian Browser Host session, durable persistence, packaging, signing, or release support.