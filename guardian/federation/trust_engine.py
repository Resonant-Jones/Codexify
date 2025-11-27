"""Event-driven trust and reputation engine.

Subscribes to federation events and updates trust metrics automatically.
Implements exponential decay to prevent stale trust drift.
"""

import asyncio
import logging
from typing import Any, Dict

from guardian.core import event_bus
from guardian.federation.trust_registry import get_trust_registry

logger = logging.getLogger(__name__)

# Event mappings: (event_topic, metric, delta)
TRUST_EVENTS: Dict[str, tuple[str, float]] = {
    "federation.session.accepted": ("auth_success", 0.02),
    "federation.session.denied": ("auth_success", -0.05),
    "federation.diff.applied": ("diff_accuracy", 0.01),
    "federation.diff.rejected": ("diff_accuracy", -0.03),
    "federation.graph.updated": ("uptime", 0.005),
    "federation.policy.violation": ("violations", 1.0),  # Add violations
}


class TrustEngine:
    """Event-driven trust and reputation engine.

    Subscribes to federation events and automatically updates trust metrics.
    Runs periodic decay to reduce metric drift over time.
    """

    def __init__(self, decay_interval_seconds: int = 600):
        """Initialize trust engine.

        Args:
            decay_interval_seconds: How often to apply decay (default 10 minutes)
        """
        self.registry = get_trust_registry()
        self.decay_interval = decay_interval_seconds
        self._running = False

    async def start(self) -> None:
        """Start the trust engine and subscribe to events."""
        logger.info("Starting trust engine")
        self._running = True

        # Start event subscription in background
        asyncio.create_task(self._subscribe_to_events())

        # Start periodic decay
        asyncio.create_task(self._decay_loop())

    async def stop(self) -> None:
        """Stop the trust engine."""
        logger.info("Stopping trust engine")
        self._running = False

    async def _subscribe_to_events(self) -> None:
        """Subscribe to federation events and update trust."""
        queue = event_bus.subscribe_in_memory()

        try:
            while self._running:
                try:
                    message = await queue.get()
                    topic = message.get("type")
                    payload = message.get("data", {})

                    # Check if this is a trust event
                    if topic in TRUST_EVENTS:
                        await self._handle_trust_event(topic, payload)

                except Exception as e:
                    logger.error(f"Error processing event in trust engine: {e}")

        except Exception as e:
            logger.error(f"Trust engine event subscription error: {e}")
        finally:
            event_bus.unsubscribe_in_memory(queue)

    async def _handle_trust_event(
        self, topic: str, payload: Dict[str, Any]
    ) -> None:
        """Handle a trust-related event.

        Args:
            topic: Event topic
            payload: Event payload
        """
        metric, delta = TRUST_EVENTS.get(topic, (None, None))
        if not metric:
            return

        # Extract node_id from payload
        node_id = (
            payload.get("source_node_id")
            or payload.get("target_node_id")
            or payload.get("author")
        )

        if not node_id:
            logger.warning(f"Could not extract node_id from {topic} event")
            return

        try:
            self.registry.update_metric(node_id, metric, delta)
            trust_score = self.registry.compute_trust_score(node_id)

            logger.debug(
                f"Updated trust for {node_id}: {metric} += {delta} (score: {trust_score:.2f})"
            )

            # Emit trust update event
            event_bus.emit_event(
                topic="federation.trust.updated",
                payload={
                    "node_id": node_id,
                    "metric": metric,
                    "delta": delta,
                    "trust_score": trust_score,
                },
            )

        except Exception as e:
            logger.error(f"Error updating trust for {node_id}: {e}")

    async def _decay_loop(self) -> None:
        """Periodically apply decay to trust metrics."""
        while self._running:
            try:
                await asyncio.sleep(self.decay_interval)

                if self._running:
                    self.registry.decay()
                    logger.debug("Applied trust decay")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in decay loop: {e}")

    def get_peer_trust(self, node_id: str) -> float:
        """Get current trust score for a peer.

        Args:
            node_id: Peer node identifier

        Returns:
            Trust score from 0.0 to 1.0
        """
        return self.registry.get_trust_level(node_id)

    def is_trusted(self, node_id: str, threshold: float = 0.3) -> bool:
        """Check if a peer is trusted above threshold.

        Args:
            node_id: Peer node identifier
            threshold: Trust threshold (default 0.3)

        Returns:
            True if peer's trust score >= threshold
        """
        return self.get_peer_trust(node_id) >= threshold


# Global trust engine instance
_trust_engine: TrustEngine | None = None


def get_trust_engine() -> TrustEngine:
    """Get or create the global trust engine instance.

    Returns:
        TrustEngine instance
    """
    global _trust_engine
    if _trust_engine is None:
        _trust_engine = TrustEngine()
    return _trust_engine


async def start_trust_engine() -> None:
    """Start the global trust engine."""
    engine = get_trust_engine()
    await engine.start()
