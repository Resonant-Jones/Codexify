"""
Metacognition Module
------------------
Central integration point for Threadspace's self-awareness capabilities.
Coordinates between CodexAwareness, EpistemicSelfCheck, and AgentRegistry
to provide unified metacognitive functions.

This module enables the system to:
1. Maintain awareness of its capabilities and limitations
2. Track confidence in decisions
3. Access and reflect on memory artifacts
4. Monitor agent health and coordination
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from guardian.codex_awareness import CodexAwareness, MemoryArtifact
from guardian.self_check import epistemic_self_check
from guardian.threads.thread_manager import ThreadManager  # We'll create this next

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MetacognitionEngine:
    """
    Coordinates self-awareness and metacognitive capabilities across the system.
    """

    def __init__(
        self,
        thread_manager: Optional[ThreadManager] = None,
        codex_awareness: Optional[CodexAwareness] = None,
    ):
        """Initialize the metacognition engine.

        Args:
            thread_manager: Optional ThreadManager instance.
            codex_awareness: Optional CodexAwareness instance. If None, creates its own.
        """
        self.codex_awareness = codex_awareness or CodexAwareness()
        self.thread_manager = thread_manager
        self.registry_path = Path(__file__).parent / "agent_registry.json"
        self.last_health_check: Optional[Dict[str, Any]] = None
        self.last_reflection: Optional[Dict[str, Any]] = None

    def load_agent_registry(self) -> Dict[str, Any]:
        """Load the current agent registry."""
        try:
            with open(self.registry_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load agent registry: {e}")
            return {}

    def update_agent_status(
        self, agent_id: str, status: str, health_status: str = "nominal"
    ) -> bool:
        """
        Update an agent's status in the registry.

        Args:
            agent_id: ID of the agent to update
            status: New status ('active', 'pending', 'inactive')
            health_status: Health status ('nominal', 'warning', 'error')

        Returns:
            bool: Success of the update operation
        """
        try:
            registry = self.load_agent_registry()
            if agent_id in registry:
                registry[agent_id].update(
                    {
                        "status": status,
                        "health_status": health_status,
                        "last_active": datetime.utcnow().isoformat(),
                    }
                )

                with open(self.registry_path, "w") as f:
                    json.dump(registry, f, indent=2)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            return False

    def system_health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive system health check.

        Returns:
            Dict containing:
            - agent_status: Status of all agents
            - memory_status: State of memory systems
            - thread_health: Thread manager health report (if available)
            - overall_health: System-wide health assessment
        """
        registry = self.load_agent_registry()

        # Get thread health if thread manager is available
        thread_health = (
            self.thread_manager.health_check()
            if self.thread_manager
            else {"status": "unknown", "message": "No thread manager available"}
        )

        # Check memory systems
        try:
            memory_check = self.codex_awareness.query_memory(
                query="system_health", limit=1
            )
            memory_status = "nominal" if memory_check is not None else "warning"
        except Exception as e:
            logger.error(f"Memory system check failed: {str(e)}")
            memory_status = "error"

        # Aggregate health status
        agent_status = {}
        for agent_id, info in registry.items():
            if isinstance(info, dict):  # Ensure 'info' is a dictionary
                agent_status[agent_id] = info.get("health_status", "unknown")
            # else: skip non-dict items like 'companions': []

        overall_health = self._assess_overall_health(
            agent_status, memory_status, thread_health
        )

        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_status": agent_status,
            "memory_status": memory_status,
            "thread_health": thread_health,
            "overall_health": overall_health,
        }

        self.last_health_check = health_report
        return health_report

    def _assess_overall_health(
        self,
        agent_status: Dict[str, str],
        memory_status: str,
        thread_health: Dict[str, Any],
    ) -> str:
        """Determine overall system health status."""
        if (
            memory_status == "error"
            or "error" in agent_status.values()
            or thread_health.get("status") == "error"
        ):
            return "error"

        if (
            memory_status == "warning"
            or "warning" in agent_status.values()
            or thread_health.get("status") == "warning"
        ):
            return "warning"

        return "nominal"

    def reflect_on_decision(
        self, intent: str, context: Dict[str, Any], available_functions: List[str]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive reflection on a pending decision.

        Args:
            intent: The intended action
            context: Current context and relevant information
            available_functions: Available system functions

        Returns:
            Dict containing reflection results and confidence assessment
        """
        # Perform epistemic self-check
        epistemic_check = epistemic_self_check(
            intent=intent, available_functions=available_functions, context=context
        )

        # Query relevant memories
        relevant_memories = self.codex_awareness.query_memory(
            query=intent, min_confidence=0.5
        )

        # Get current agent states
        agent_registry = self.load_agent_registry()
        active_agents = []
        for agent_id, info in agent_registry.items():
            if isinstance(info, dict) and info.get("status") == "active":
                active_agents.append(agent_id)

        reflection = {
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent,
            "epistemic_check": epistemic_check,
            "relevant_memories": [m.to_dict() for m in relevant_memories],
            "active_agents": active_agents,
            "confidence_assessment": self._assess_confidence(
                epistemic_check, relevant_memories, active_agents
            ),
        }

        self.last_reflection = reflection
        return reflection

    def _assess_confidence(
        self,
        epistemic_check: Dict[str, Any],
        relevant_memories: List[MemoryArtifact],
        active_agents: List[str],
    ) -> Dict[str, Any]:
        """
        Assess overall confidence based on multiple factors.

        Returns:
            Dict containing:
            - confidence_score: Float between 0 and 1
            - factors: List of contributing factors
            - recommendations: List of suggested improvements
        """
        factors = []
        confidence_score = epistemic_check["confidence_level"]

        # Consider relevant memories
        if relevant_memories:
            memory_confidence = sum(m.confidence for m in relevant_memories) / len(
                relevant_memories
            )
            confidence_score = (confidence_score + memory_confidence) / 2
            factors.append(f"Memory confidence: {memory_confidence:.2f}")

        # Consider active agents
        required_agents = {"Axis", "Vestige"}  # Minimum required set
        if not required_agents.issubset(set(active_agents)):
            confidence_score *= 0.8
            factors.append("Missing required agents")

        # Generate recommendations
        recommendations = []
        if confidence_score < 0.7:
            if not relevant_memories:
                recommendations.append("Gather more relevant historical context")
            if not required_agents.issubset(set(active_agents)):
                recommendations.append("Ensure all required agents are active")

        return {
            "confidence_score": confidence_score,
            "factors": factors,
            "recommendations": recommendations,
        }

    async def handle_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle system errors and initiate recovery procedures.

        Args:
            error: The error that occurred
            context: Context information about the error

        Returns:
            Dict containing error handling results
        """
        try:
            # Log the error
            logger.error(f"Error occurred: {error}")

            # Store error in memory
            error_memory = {
                "type": "system_error",
                "error": str(error),
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            }

            memory_id = self.codex_awareness.store_memory(
                content=error_memory,
                source="error_handler",
                tags=["error", "system"],
                confidence=1.0,
            )

            # Update system status
            self.last_health_check = self.system_health_check()

            # Initiate recovery procedures
            recovery_result = self._initiate_recovery(error, context)

            return {
                "status": "handled",
                "error": str(error),
                "memory_id": memory_id,
                "recovery_status": recovery_result["status"],
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error handling failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _initiate_recovery(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Initiate system recovery procedures.

        Args:
            error: The error that occurred
            context: Error context

        Returns:
            Dict containing recovery status
        """
        try:
            # Check affected components
            affected_components = self._identify_affected_components(error, context)

            # Attempt recovery for each component
            recovery_actions = []
            for component in affected_components:
                action = self._recover_component(component)
                recovery_actions.append(action)

            # Store recovery attempt
            self.codex_awareness.store_memory(
                content={
                    "type": "recovery_attempt",
                    "error": str(error),
                    "actions": recovery_actions,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                source="recovery_handler",
                tags=["recovery", "system"],
                confidence=1.0,
            )

            return {
                "status": "recovered",
                "actions": recovery_actions,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _identify_affected_components(
        self, error: Exception, context: Dict[str, Any]
    ) -> List[str]:
        """Identify system components affected by an error."""
        affected = []

        # Check thread manager
        if "thread" in str(error).lower():
            affected.append("thread_manager")

        # Check memory system
        if "memory" in str(error).lower():
            affected.append("memory_system")

        # Check agents
        if context.get("source") in self.load_agent_registry():
            affected.append(f"agent_{context['source']}")

        return affected or [
            "system"
        ]  # Default to system-wide if no specific components

    def _recover_component(self, component: str) -> Dict[str, Any]:
        """Attempt recovery of a specific component."""
        try:
            if component == "thread_manager":
                if self.thread_manager is None:
                    return {
                        "component": component,
                        "status": "skipped",
                        "message": "No thread manager available",
                    }
                # Restart essential threads
                self.thread_manager.health_check()
                return {"component": component, "status": "recovered"}

            elif component == "memory_system":
                # Verify memory system
                self.codex_awareness.query_memory("health_check", limit=1)
                return {"component": component, "status": "recovered"}

            elif component.startswith("agent_"):
                # Restart agent
                agent_id = component.split("_")[1]
                self.update_agent_status(agent_id, "active")
                return {"component": component, "status": "recovered"}

            else:
                # System-wide recovery
                self.system_health_check()
                return {"component": component, "status": "recovered"}

        except Exception as e:
            return {"component": component, "status": "failed", "error": str(e)}

    async def check_recovery_status(self) -> Dict[str, Any]:
        """
        Check the status of system recovery.

        Returns:
            Dict containing recovery status information
        """
        try:
            # Get latest health check
            health = self.system_health_check()

            # Get recent recovery attempts
            recovery_memories = self.codex_awareness.query_memory(
                query="recovery_attempt", limit=1
            )

            if recovery_memories:
                latest_recovery = recovery_memories[0].content
                recovery_time = datetime.fromisoformat(latest_recovery["timestamp"])
                current_time = datetime.utcnow()

                if (
                    current_time - recovery_time
                ).total_seconds() < 300:  # Within 5 minutes
                    return {
                        "status": "recovered",
                        "health_status": health["overall_health"],
                        "last_recovery": latest_recovery,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

            return {
                "status": "nominal",
                "health_status": health["overall_health"],
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Recovery status check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def store_decision_outcome(
        self, intent: str, outcome: Dict[str, Any], confidence: float, tags: List[str]
    ) -> str:
        """
        Store the outcome of a decision for future reference.

        Args:
            intent: The original intent
            outcome: Result of the decision
            confidence: Confidence in the outcome
            tags: Relevant tags for categorization

        Returns:
            str: ID of the stored memory artifact
        """
        memory_content = {
            "intent": intent,
            "outcome": outcome,
            "original_confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return self.codex_awareness.store_memory(
            content=memory_content,
            source="decision_outcome",
            tags=tags,
            confidence=confidence,
        )


# Example usage:
if __name__ == "__main__":
    # Initialize the metacognition engine
    meta = MetacognitionEngine()

    # Perform a system health check
    health_status = meta.system_health_check()
    print("\nSystem Health Check:")
    print(json.dumps(health_status, indent=2))

    # Reflect on a sample decision
    reflection = meta.reflect_on_decision(
        intent="process_user_query",
        context={"query": "test query"},
        available_functions=["base_operation", "query_processing"],
    )
    print("\nDecision Reflection:")
    print(json.dumps(reflection, indent=2))
