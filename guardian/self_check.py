"""
Epistemic Self-Check Module
--------------------------
Provides metacognitive awareness capabilities for the Threadspace system.
Allows the system to reflect on its knowledge, confidence, and limitations.

This module implements systematic self-awareness checks to help the system
maintain accurate beliefs about its own capabilities and knowledge state.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EpistemicState:
    """Tracks the system's current knowledge and confidence state."""

    def __init__(self):
        self.confidence_levels = {
            "certain": 0.9,
            "highly_probable": 0.7,
            "probable": 0.5,
            "uncertain": 0.3,
            "guessing": 0.1,
        }
        self.last_assessment: Optional[Dict[str, Any]] = None
        self.knowledge_gaps: List[str] = []

    def assess_confidence(self, evidence: Dict[str, Any]) -> float:
        """Calculate confidence level based on available evidence."""
        # Placeholder for more sophisticated confidence calculation
        if not evidence:
            return self.confidence_levels["guessing"]
        return self.confidence_levels["probable"]


def load_agent_registry() -> Dict[str, Any]:
    """Load the current agent registry to check available capabilities."""
    try:
        registry_path = Path(__file__).parent / "agent_registry.json"
        with open(registry_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load agent registry: {e}")
        return {}


def epistemic_self_check(
    intent: str,
    available_functions: List[str],
    last_decision: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Perform a systematic self-check of the system's knowledge and capabilities.

    Args:
        intent: The intended action or decision to be made
        available_functions: List of currently available system functions
        last_decision: Previous decision context if any
        context: Additional context about the current state

    Returns:
        Dict containing:
        - confidence_level: Float between 0 and 1
        - knowledge_gaps: List of identified missing information
        - reasoning: Explanation of the confidence assessment
        - recommendations: Suggested actions to improve confidence
    """
    state = EpistemicState()
    agent_registry = load_agent_registry()

    # Gather evidence for confidence assessment
    evidence = {
        "has_required_functions": all(
            func in available_functions for func in _get_required_functions(intent)
        ),
        "has_required_agents": _check_required_agents(intent, agent_registry),
        "context_completeness": _assess_context_completeness(context),
        "previous_success": _check_previous_success(last_decision),
    }

    confidence = state.assess_confidence(evidence)

    # Identify knowledge gaps
    gaps = _identify_knowledge_gaps(intent, evidence, context)

    # Generate recommendations
    recommendations = _generate_recommendations(gaps, confidence)

    assessment = {
        "timestamp": datetime.utcnow().isoformat(),
        "intent": intent,
        "confidence_level": confidence,
        "knowledge_gaps": gaps,
        "reasoning": _generate_reasoning(evidence, confidence),
        "recommendations": recommendations,
        "evidence": evidence,
    }

    state.last_assessment = assessment
    logger.info(f"Completed epistemic self-check for intent: {intent}")

    return assessment


def _get_required_functions(intent: str) -> List[str]:
    """Determine required functions based on intent."""
    # Placeholder - expand based on actual system capabilities
    return ["base_operation"]


def _check_required_agents(intent: str, registry: Dict[str, Any]) -> bool:
    """Verify that required agents are available and healthy."""
    required_agents = _determine_required_agents(intent)
    return all(
        agent in registry and registry[agent]["status"] == "active"
        for agent in required_agents
    )


def _determine_required_agents(intent: str) -> List[str]:
    """Map intents to required agents."""
    # Placeholder - expand based on actual agent responsibilities
    return ["Axis"]  # Axis is always required as the stable compass


def _assess_context_completeness(context: Optional[Dict[str, Any]]) -> float:
    """Evaluate how complete the available context is."""
    if not context:
        return 0.0
    # Placeholder - implement more sophisticated context assessment
    return 0.5


def _check_previous_success(last_decision: Optional[Dict[str, Any]]) -> bool:
    """Check if the last similar decision was successful."""
    if not last_decision:
        return False
    return last_decision.get("success", False)


def _identify_knowledge_gaps(
    intent: str, evidence: Dict[str, Any], context: Optional[Dict[str, Any]]
) -> List[str]:
    """Identify missing information or capabilities."""
    gaps = []

    if not evidence["has_required_functions"]:
        gaps.append("Missing required system functions")

    if not evidence["has_required_agents"]:
        gaps.append("Required agents unavailable or inactive")

    if evidence["context_completeness"] < 0.5:
        gaps.append("Insufficient context for confident decision")

    return gaps


def _generate_reasoning(evidence: Dict[str, Any], confidence: float) -> str:
    """Generate a human-readable explanation of the confidence assessment."""
    reasons = []

    if evidence["has_required_functions"]:
        reasons.append("All required functions are available")

    if evidence["has_required_agents"]:
        reasons.append("Required agents are active and healthy")

    if evidence["context_completeness"] > 0.5:
        reasons.append("Sufficient context is available")

    if not reasons:
        return "Insufficient evidence for high confidence"

    return f"Confidence assessment ({confidence:.2f}): " + "; ".join(reasons)


def _generate_recommendations(gaps: List[str], confidence: float) -> List[str]:
    """Generate recommendations for improving confidence."""
    recommendations = []

    if gaps:
        for gap in gaps:
            recommendations.append(f"Address knowledge gap: {gap}")

    if confidence < 0.5:
        recommendations.append("Consider gathering more context before proceeding")

    return recommendations


# Example usage:
if __name__ == "__main__":
    # Simulate a self-check
    result = epistemic_self_check(
        intent="process_user_query",
        available_functions=["base_operation", "query_processing"],
        context={"user_query": "test query"},
    )
    print(json.dumps(result, indent=2))
