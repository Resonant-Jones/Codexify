"""Channel adapter framework package."""

from guardian.channels.allowlist import (
    PairingCodeError,
    allow_sender,
    create_pairing_code,
    is_allowed,
    redeem_pairing_code,
)
from guardian.channels.base import (
    Adapter,
    AdapterContext,
    InboundMessage,
    OutboundMessage,
)
from guardian.channels.registry import (
    get_adapter,
    list_adapters,
    register_adapter,
)
from guardian.channels.router import handle_inbound

__all__ = [
    "Adapter",
    "AdapterContext",
    "InboundMessage",
    "OutboundMessage",
    "PairingCodeError",
    "allow_sender",
    "create_pairing_code",
    "is_allowed",
    "redeem_pairing_code",
    "register_adapter",
    "get_adapter",
    "list_adapters",
    "handle_inbound",
]

