"""
Axis Agent
---------
Core decision-making and routing system.
Provides stable compass for system operations and maintains operational coherence.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.self_check import epistemic_self_check

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions that Axis can make."""

    ROUTING = "routing"
    RESOURCE = "resource"
    PRIORITY = "priority"
    STRATEGY = "strategy"
    INTERVENTION = "intervention"


class Decision:
    """Represents a decision made by Axis."""

    def __init__(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        confidence: float,
    ):
        self.decision_type = decision_type
        self.context = context
        self.options = options
        self.confidence = confidence
        self.timestamp = datetime.utcnow()
        self.selected_option: Optional[Dict[str, Any]] = None
        self.outcome: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary representation."""
        return {
            "decision_type": self.decision_type.value,
            "context": self.context,
            "options": self.options,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "selected_option": self.selected_option,
            "outcome": self.outcome,
        }


class AxisAgent:
    """
    Core decision-making and routing agent.
    Maintains system stability and operational coherence.
    """

    def __init__(self, codex: CodexAwareness, metacognition: MetacognitionEngine):
        self.codex = codex
        self.metacognition = metacognition
        self.decisions: List[Decision] = []
        self.active_contexts: Dict[str, Dict[str, Any]] = {}
        self.stability_metrics: Dict[str, float] = {
            "routing_confidence": 1.0,
            "resource_balance": 1.0,
            "system_coherence": 1.0,
        }

    async def make_decision(
        self,
        decision_type: Union[DecisionType, str],
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Make a decision based on given context and options.

        Args:
            decision_type: Type of decision to make
            context: Decision context
            options: Available options

        Returns:
            Dict containing decision results
        """
        # --- Input Validation for decision_type ---
        actual_decision_type: DecisionType
        if isinstance(decision_type, str):
            try:
                actual_decision_type = DecisionType(decision_type)
            except ValueError as e:  # If string is invalid enum member
                logger.error(f"Invalid decision_type string '{decision_type}': {e}")
                raise e  # Re-raise to be caught by test's assertRaises
        elif isinstance(decision_type, DecisionType):
            actual_decision_type = decision_type
        else:
            raise TypeError(
                f"decision_type must be DecisionType or str, got {type(decision_type).__name__}"
            )
        # --- End Input Validation for decision_type ---

        try:
            # Validate context and options
            # Use actual_decision_type from now on
            if not self._validate_decision_input(
                actual_decision_type, context, options
            ):
                raise ValueError("Invalid decision input")

            # Perform epistemic check
            check_result = epistemic_self_check(
                intent=f"make_{decision_type.value}_decision",
                available_functions=[
                    "decision_making",
                    "context_analysis",
                    "outcome_prediction",
                ],
                context=context,
            )

            # Create decision object
            decision = Decision(
                decision_type=decision_type,
                context=context,
                options=options,
                confidence=check_result["confidence_level"],
            )

            # Query relevant historical decisions
            historical_context = await self._get_historical_context(
                decision_type, context
            )

            # Evaluate options
            evaluated_options = await self._evaluate_options(
                decision, historical_context
            )

            # Select best option
            selected_option = self._select_option(evaluated_options)
            decision.selected_option = selected_option

            # Store decision
            self.decisions.append(decision)
            decision_id = self._store_decision(decision)

            # Update stability metrics
            self._update_stability_metrics(decision)

            return {
                "status": "success",
                "decision_id": decision_id,
                "selected_option": selected_option,
                "confidence": decision.confidence,
                "stability_metrics": self.stability_metrics,
            }

        except Exception as e:
            logger.error(f"Decision making failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "stability_metrics": self.stability_metrics,
            }

    def _validate_decision_input(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
    ) -> bool:
        """Validate decision input parameters."""
        if not context or not options:
            return False

        required_fields = {
            DecisionType.ROUTING: {"destination", "payload"},
            DecisionType.RESOURCE: {"resource_type", "quantity"},
            DecisionType.PRIORITY: {"tasks", "constraints"},
            DecisionType.STRATEGY: {"objective", "parameters"},
            DecisionType.INTERVENTION: {"trigger", "severity"},
        }

        # Check context fields
        if not all(field in context for field in required_fields[decision_type]):
            return False

        # Check options structure
        for option in options:
            if "id" not in option or "value" not in option:
                return False

        return True

    async def _get_historical_context(
        self, decision_type: DecisionType, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant historical decisions."""
        query = f"type:decision decision_type:{decision_type.value}"

        # Add context-specific query terms
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                query += f" {key}:{value}"

        results = self.codex.query_memory(query=query, limit=10, min_confidence=0.7)

        return [r.content for r in results]

    async def _evaluate_options(
        self, decision: Decision, historical_context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate decision options using historical context.

        Args:
            decision: Current decision
            historical_context: Relevant historical decisions

        Returns:
            List of evaluated options with scores
        """
        evaluated_options = []

        for option in decision.options:
            # Base score from option attributes
            base_score = self._calculate_base_score(option)

            # Historical success rate
            historical_score = self._calculate_historical_score(
                option, historical_context
            )

            # Stability impact
            stability_score = self._calculate_stability_score(
                option, decision.decision_type
            )

            # Combine scores
            final_score = (
                base_score * 0.4 + historical_score * 0.3 + stability_score * 0.3
            )

            evaluated_options.append(
                {
                    **option,
                    "score": final_score,
                    "metrics": {
                        "base_score": base_score,
                        "historical_score": historical_score,
                        "stability_score": stability_score,
                    },
                }
            )

        return sorted(evaluated_options, key=lambda x: x["score"], reverse=True)

    def _calculate_base_score(self, option: Dict[str, Any]) -> float:
        """Calculate base score for an option."""
        # Example scoring logic - customize based on needs
        score = 0.5  # Default score

        if "confidence" in option:
            score += option["confidence"] * 0.3

        if "priority" in option:
            score += min(option["priority"] / 10.0, 0.2)

        return min(1.0, score)

    def _calculate_historical_score(
        self, option: Dict[str, Any], historical_context: List[Dict[str, Any]]
    ) -> float:
        """Calculate score based on historical performance."""
        if not historical_context:
            return 0.5  # Default score with no history

        relevant_decisions = [
            d
            for d in historical_context
            if d.get("selected_option", {}).get("id") == option["id"]
        ]

        if not relevant_decisions:
            return 0.5

        # Calculate success rate
        successes = sum(
            1 for d in relevant_decisions if d.get("outcome", {}).get("success", False)
        )

        return successes / len(relevant_decisions)

    def _calculate_stability_score(
        self, option: Dict[str, Any], decision_type: DecisionType
    ) -> float:
        """Calculate score based on system stability impact."""
        stability_score = 0.5  # Default score

        # Consider current stability metrics
        if decision_type == DecisionType.ROUTING:
            stability_score = self.stability_metrics["routing_confidence"]
        elif decision_type == DecisionType.RESOURCE:
            stability_score = self.stability_metrics["resource_balance"]
        else:
            stability_score = self.stability_metrics["system_coherence"]

        # Adjust based on option attributes
        if "stability_impact" in option:
            stability_score *= 1.0 + option["stability_impact"]

        return min(1.0, max(0.0, stability_score))

    def _select_option(self, evaluated_options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best option based on evaluation."""
        if not evaluated_options:
            raise ValueError("No options to select from")

        # Select highest scoring option
        return evaluated_options[0]

    def _store_decision(self, decision: Decision) -> str:
        """Store decision in memory system."""
        return self.codex.store_memory(
            content=decision.to_dict(),
            source="axis",
            tags=["decision", decision.decision_type.value],
            confidence=decision.confidence,
        )

    def _update_stability_metrics(self, decision: Decision) -> None:
        """Update system stability metrics based on decision."""
        # Update type-specific metric
        if decision.decision_type == DecisionType.ROUTING:
            self.stability_metrics["routing_confidence"] = min(
                1.0,
                self.stability_metrics["routing_confidence"] * 0.8
                + decision.confidence * 0.2,
            )
        elif decision.decision_type == DecisionType.RESOURCE:
            self.stability_metrics["resource_balance"] = min(
                1.0,
                self.stability_metrics["resource_balance"] * 0.8
                + decision.confidence * 0.2,
            )

        # Update overall system coherence
        self.stability_metrics["system_coherence"] = min(
            1.0, sum(self.stability_metrics.values()) / len(self.stability_metrics)
        )

    async def record_outcome(
        self, decision_id: str, outcome: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record the outcome of a decision.

        Args:
            decision_id: ID of the decision
            outcome: Outcome information

        Returns:
            Dict containing update status
        """
        try:
            # Try to get decision directly from artifacts
            decision_data = self.codex.artifacts.get(decision_id)

            if not decision_data:
                # If not found, try query as fallback
                results = self.codex.query_memory(query=f"id:{decision_id}", limit=1)
                if results:
                    decision_data = results[0]

            if not decision_data:
                logger.warning(
                    f"Decision {decision_id} not found, creating placeholder"
                )
                # Create placeholder decision data
                decision_data = {
                    "id": decision_id,
                    "decision_type": "unknown",
                    "context": {},
                    "confidence": 0.5,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Update decision with outcome
            if isinstance(decision_data, dict):
                decision_content = decision_data
            else:
                decision_content = decision_data.content

            decision_content["outcome"] = outcome

            # Store updated decision
            try:
                self.codex.store_memory(
                    content=decision_content,
                    source="axis",
                    tags=["decision", "outcome"],
                    confidence=decision_content.get("confidence", 0.5),
                )
            except Exception as store_error:
                logger.warning(f"Failed to store decision outcome: {store_error}")

            # Update stability metrics based on outcome
            if outcome.get("success", False):
                self._strengthen_stability()
            else:
                self._weaken_stability()

            return {
                "status": "success",
                "decision_id": decision_id,
                "stability_metrics": self.stability_metrics,
            }

        except Exception as e:
            logger.error(f"Failed to record outcome: {e}")
            # Still update stability metrics even on error
            self._weaken_stability()
            return {
                "status": "warning",
                "error": str(e),
                "stability_metrics": self.stability_metrics,
            }

    def _strengthen_stability(self) -> None:
        """Strengthen stability metrics after successful outcome."""
        for metric in self.stability_metrics:
            self.stability_metrics[metric] = min(
                1.0, self.stability_metrics[metric] * 0.9 + 0.1
            )

    def _weaken_stability(self) -> None:
        """Weaken stability metrics after failed outcome."""
        for metric in self.stability_metrics:
            self.stability_metrics[metric] *= 0.9


# Example usage:
if __name__ == "__main__":
    # Initialize dependencies
    codex = CodexAwareness()
    metacognition = MetacognitionEngine()

    # Create Axis agent
    axis = AxisAgent(codex, metacognition)

    # Example decision making
    async def test_decision():
        result = await axis.make_decision(
            decision_type=DecisionType.ROUTING,
            context={"destination": "memory_system", "payload": {"type": "test_data"}},
            options=[
                {"id": "opt1", "value": "direct_route"},
                {"id": "opt2", "value": "cached_route"},
            ],
        )
        print(f"Decision result: {result}")

    # Run test
    import asyncio

    asyncio.run(test_decision())
