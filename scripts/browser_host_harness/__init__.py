# Browser Host Comparative Proof Harness — shared technology-neutral scaffold.
#
# This package implements the deterministic fixture server, Guardian contract stub,
# canonical harness registries, and proof-receipt scaffold required by:
#   docs/architecture/browser-host-comparative-proof-harness-spec.md
#
# It does not implement a Browser Host, candidate adapter, page capture,
# production Guardian route, or technology selection.
#
# All servers bind loopback-only (127.0.0.1) on ephemeral ports.
# No outbound internet requests are made.
# No production credential, database, or provider is used.

__version__ = "0.1.0"
__all__: list[str] = []
