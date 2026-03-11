"""
Public entry points for the ResonantOS wallet scaffold plugin.
"""

from .manifest import RESONANTOS_WALLET_MANIFEST
from .plugin import ResonantOSWalletPlugin

__all__ = ["RESONANTOS_WALLET_MANIFEST", "ResonantOSWalletPlugin"]
