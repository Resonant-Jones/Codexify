# Crypto Wallet Plugin for Codexify

## Overview

This document outlines how to add a software wallet for cryptocurrency to Codexify using the existing plugin SDK architecture.

---

## Context

Codexify has a well-developed plugin system that allows extending functionality without modifying core code. A crypto wallet could be added as a self-contained plugin.

---

## Codexify Plugin Architecture

### Plugin Locations
- **Main plugins**: `guardian/plugins/`
- **Runtime plugins**: Loaded dynamically via `guardian/core/plugins.py`
- **Config**: `guardian/config/core.py` (PLUGIN_DIR setting)

### Plugin Base Interface
Located at `guardian/plugins/plugin_base.py`:
```python
class PluginBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def version(self) -> str: ...
    @abstractmethod
    def activate(self, core_services: Dict[str, Any]) -> None: ...
    @abstractmethod
    def register_cli(self, cli: Any) -> None: ...
```

### Plugin Structure
Each plugin needs:
```
plugin_name/
├── plugin.json    # Metadata (name, version, entry point)
├── main.py        # Main implementation
└── tests/         # Optional tests
```

### Core Services Available to Plugins
```python
core_services = {
    "memory_os": MemoryOS,      # Conversation/context management
    "codemap": CodemapService, # Project navigation
    "config": ConfigLoader,    # Environment settings
}
```

### Existing Plugin Examples
- `guardian/plugins/memory_analyzer/` - Analyzes memory patterns
- `guardian/plugins/system_diagnostics/` - System health
- `guardian/plugins/codexify/` - Knowledge retrieval
- `guardian/plugins/tts/` - Text-to-speech

---

## Implementation Approach

### Create a New Plugin: `crypto_wallet`

Location: `guardian/plugins/crypto_wallet/`

#### 1. plugin.json
```json
{
  "name": "crypto_wallet",
  "version": "0.1.0",
  "description": "Solana software wallet for Codexify",
  "author": "Codexify Team",
  "dependencies": [],
  "capabilities": ["wallet:solana"],
  "entry": "plugins/crypto_wallet/main.py"
}
```

#### 2. main.py
Implement `PluginBase` with:
- `activate()`: Initialize wallet (load from secure storage)
- `register_cli()`: Expose CLI commands (balance, send, receive)
- Optional: `health_check()` for plugin monitoring

#### 3. wallet_service.py
Core wallet logic for Solana operations.

### Permissions to Declare
- `wallet:read` - View balances and addresses
- `wallet:write` - Send transactions
- `storage:read` / `storage:write` - Persist wallet data

### Library Recommendations

| Function | Library |
|----------|---------|
| Solana RPC | `solana` (PyPI) |
| Key Storage | `keyring` (OS keychain) |
| Encryption | `cryptography` (for encrypted file storage) |
| Mnemonic | `bip39` (if needed for key derivation) |

---

## Key Implementation Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Blockchain** | Solana | Selected - use `solana` PyPI library |
| **Key Storage** | Local encrypted file / OS keychain | Use `keyring` library for OS keychain |
| **UI Integration** | None / CLI only / Frontend panel | Start with CLI, add UI panel later |
| **Transaction Signing** | Hot wallet (in-memory keys) | Consider cold storage support for security |

---

## Files to Create

```
guardian/plugins/crypto_wallet/
├── plugin.json           # Plugin metadata
├── main.py               # Plugin implementation (PluginBase)
├── wallet_service.py     # Wallet logic (Solana operations)
└── tests/
    └── test_wallet.py    # Unit tests
```

---

## Wallet Operations

### CLI Commands (via `register_cli`)
- `wallet create` - Generate new wallet
- `wallet import <private_key>` - Import existing wallet
- `wallet balance` - View SOL balance
- `wallet address` - Show wallet address
- `wallet send <address> <amount>` - Send SOL
- `wallet history` - View transaction history

### Programmatic API
```python
# Via core_services or direct plugin access
wallet = plugin.get_wallet()
balance = wallet.get_balance()
transaction = wallet.send(to_address, amount)
```

---

## Security Considerations

1. **Private Key Storage**: Never store raw private keys. Use OS keychain or encrypted files.
2. **Mnemonic Support**: Consider BIP39 mnemonic for backup/recovery.
3. **Network**: Default to devnet for testing, mainnet-beta requires caution.
4. **Transaction Signing**: Consider requiring confirmation for each transaction.
5. **Rate Limiting**: Implement rate limiting on send operations.

---

## Testing

1. Place plugin in `guardian/plugins/`
2. Start Guardian - plugin should auto-load
3. Test CLI commands: `guardian-cli wallet balance`
4. If UI panel enabled, verify frontend renders

---

## Summary

Codexify's plugin SDK is well-suited for adding a crypto wallet:
- **Plugin base class** provides lifecycle management
- **Core services** give access to memory, config, and more
- **UI panel support** enables frontend integration
- **Permission system** allows fine-grained access control

A Solana crypto wallet could be added as a self-contained plugin without modifying core Codexify code.

---

## Next Steps (If Proceeding)

1. Choose key storage approach (keyring vs encrypted file)
2. Define transaction signing flow
3. Design UI integration (if desired)
4. Implement plugin following existing patterns
5. Test on devnet before production
