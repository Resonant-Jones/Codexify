"""
Echoform Agent
------------
Reflective and transitional process handler.
Manages system state transitions and maintains operational resonance.
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResonanceState(Enum):
    """System resonance states."""

    HARMONIC = "harmonic"  # Optimal state
    ADAPTIVE = "adaptive"  # Adjusting to changes
    DISSONANT = "dissonant"  # Needs adjustment
    CRITICAL = "critical"  # Requires immediate attention


class TransitionType(Enum):
    """Types of system state transitions."""

    UPGRADE = "upgrade"  # System improvement
    RECOVERY = "recovery"  # Error recovery
    SCALING = "scaling"  # Resource scaling
    REBALANCE = "rebalance"  # Load balancing
    EMERGENCY = "emergency"  # Emergency procedures


class StateTransition:
    """Represents a system state transition."""

    def __init__(
        self,
        transition_type: TransitionType,
        from_state: Dict[str, Any],
        to_state: Dict[str, Any],
        metadata: Dict[str, Any],
    ):
        self.transition_type = transition_type
        self.from_state = from_state
        self.to_state = to_state
        self.metadata = metadata
        self.timestamp = datetime.now(UTC)
        self.completed = False
        self.success: Optional[bool] = None
        self.duration: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert transition to dictionary representation."""
        return {
            "transition_type": self.transition_type.value,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "completed": self.completed,
            "success": self.success,
            "duration": self.duration,
        }


class EchoformAgent:
    """
    Reflective process and transition management agent.
    Maintains system resonance and handles state transitions.
    """

    def __init__(self, codex: CodexAwareness, metacognition: MetacognitionEngine):
        self.codex = codex
        self.metacognition = metacognition
        self.current_resonance = ResonanceState.HARMONIC
        self.active_transitions: Dict[str, StateTransition] = {}
        self.resonance_history: List[Tuple[datetime, ResonanceState]] = []
        self.transition_patterns: Dict[str, List[Dict[str, Any]]] = {}

    async def assess_resonance(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess current system resonance state.

        Args:
            system_state: Current system state information

        Returns:
            Dict containing resonance assessment
        """
        try:
            # Analyze system metrics
            metrics_analysis = self._analyze_metrics(system_state)

            # Check for patterns
            pattern_analysis = self._analyze_patterns(metrics_analysis, system_state)

            # Determine resonance state
            new_resonance = self._determine_resonance(
                metrics_analysis, pattern_analysis
            )

            # Update history
            self._update_resonance_history(new_resonance)

            # Store assessment
            assessment_id = self._store_assessment(
                new_resonance, metrics_analysis, pattern_analysis
            )

            return {
                "status": "success",
                "resonance_state": new_resonance.value,
                "assessment_id": assessment_id,
                "metrics": metrics_analysis,
                "patterns": pattern_analysis,
            }

        except Exception as e:
            logger.error(f"Resonance assessment failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "current_resonance": self.current_resonance.value,
            }

    def _analyze_metrics(self, system_state: Dict[str, Any]) -> Dict[str, float]:
        """Analyze system metrics for resonance assessment."""
        logger.info(
            logger.debug(
                f"EchoformAgent._analyze_metrics called with system_state: {system_state}"
            )
        )  # DEBUG
        metrics = {}

        # Resource utilization
        if "resources" in system_state:
            resources = system_state["resources"]
            if isinstance(resources, dict):  # DEBUG Check
                metrics["resource_balance"] = self._calculate_resource_balance(
                    resources
                )
            else:
                logger.warning(
                    logger.debug("resources in system_state is not a dict: {resources}")
                )  # DEBUG
                metrics["resource_balance"] = 0.0
        else:
            logger.info(
                logger.debug("resources key not in system_state for _analyze_metrics")
            )  # DEBUG
            metrics["resource_balance"] = 0.0

        # Performance metrics
        if "performance" in system_state:
            performance = system_state["performance"]
            if isinstance(performance, dict):  # DEBUG Check
                metrics["performance_score"] = self._calculate_performance_score(
                    performance
                )
            else:
                logger.warning(
                    logger.debug(
                        f"'performance' in system_state is not a dict: {performance}"
                    )
                )  # DEBUG
                metrics["performance_score"] = 0.0
        else:
            logger.info(
                logger.debug(
                    "'performance' key not in system_state for _analyze_metrics"
                )
            )  # DEBUG
            metrics["performance_score"] = 0.0

        # Error rates
        if "errors" in system_state:
            errors = system_state["errors"]
            if isinstance(errors, dict):  # DEBUG Check
                metrics["error_rate"] = self._calculate_error_rate(errors)
            else:
                logger.warning(
                    logger.debug(f"'errors' in system_state is not a dict: {errors}")
                )  # DEBUG
                metrics["error_rate"] = (
                    0.0  # Default to a safe value (1.0 implies no errors, 0.0 implies all errors)
                )
        else:
            logger.info(
                logger.debug("'errors' key not in system_state for _analyze_metrics")
            )  # DEBUG
            metrics["error_rate"] = 1.0  # Assume no errors if not provided

        # System coherence
        if "coherence" in system_state:
            coherence = system_state["coherence"]
            if isinstance(coherence, dict):  # DEBUG Check
                metrics["coherence_score"] = self._calculate_coherence_score(coherence)
            else:
                logger.warning(
                    logger.debug(
                        f"'coherence' in system_state is not a dict: {coherence}"
                    )
                )  # DEBUG
                metrics["coherence_score"] = 0.0
        else:
            logger.info(
                logger.debug("'coherence' key not in system_state for _analyze_metrics")
            )  # DEBUG
            metrics["coherence_score"] = 0.0

        logger.info(f"_analyze_metrics returning: {metrics}")
        return metrics

    def _calculate_resource_balance(self, resources: Dict[str, Any]) -> float:
        """Calculate resource balance score."""
        if not resources:
            return 0.0

        # Example calculation - customize based on needs
        utilization_scores = []

        for resource, metrics in resources.items():
            if "utilization" in metrics:
                # Optimal utilization around 70%
                util = metrics["utilization"]
                score = 1.0 - abs(0.7 - util)
                utilization_scores.append(score)

        return (
            sum(utilization_scores) / len(utilization_scores)
            if utilization_scores
            else 0.0
        )

    def _calculate_performance_score(self, performance: Dict[str, Any]) -> float:
        """Calculate performance score."""
        if not performance:
            return 0.0

        scores = []

        # Response time score
        if "response_time" in performance:
            rt_score = 1.0 - min(performance["response_time"] / 1000.0, 1.0)
            scores.append(rt_score)

        # Throughput score
        if "throughput" in performance:
            tp_score = min(performance["throughput"] / 100.0, 1.0)
            scores.append(tp_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_error_rate(self, errors: Dict[str, Any]) -> float:
        """Calculate error rate score."""
        if not errors:
            return 0.0

        total_operations = errors.get("total_operations", 0)
        if total_operations == 0:
            return 0.0

        error_count = errors.get("error_count", 0)
        return 1.0 - (error_count / total_operations)

    def _calculate_coherence_score(self, coherence: Dict[str, Any]) -> float:
        """Calculate system coherence score."""
        if not coherence:
            return 0.0

        scores = []

        # Component alignment
        if "component_alignment" in coherence:
            scores.append(coherence["component_alignment"])

        # State consistency
        if "state_consistency" in coherence:
            scores.append(coherence["state_consistency"])

        return sum(scores) / len(scores) if scores else 0.0

    def _analyze_patterns(
        self, metrics: Dict[str, float], system_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze system patterns for resonance assessment."""
        patterns = {
            "trends": self._analyze_trends(metrics),
            "cycles": self._analyze_cycles(system_state),
            "anomalies": self._detect_anomalies(metrics, system_state),
        }

        return patterns

    def _analyze_trends(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Analyze metric trends."""
        trends = {}

        for metric, value in metrics.items():
            # Compare with historical values
            history = [
                state
                for timestamp, state in self.resonance_history[-10:]
                if hasattr(state, metric)
            ]

            if history:
                avg_value = sum(getattr(state, metric, 0.0) for state in history) / len(
                    history
                )
                trend = value - avg_value
                trends[metric] = {
                    "direction": "up" if trend > 0 else "down",
                    "magnitude": abs(trend),
                }

        return trends

    def _analyze_cycles(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system cycles and patterns."""
        cycles = {}

        # Analyze load patterns
        if "load" in system_state:
            cycles["load"] = self._detect_load_cycles(system_state["load"])

        # Analyze resource patterns
        if "resources" in system_state:
            cycles["resources"] = self._detect_resource_cycles(
                system_state["resources"]
            )

        return cycles

    def _detect_load_cycles(self, load_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect load cycling patterns."""
        # Example implementation - expand based on needs
        return {
            "periodic": self._is_periodic(load_data),
            "frequency": self._calculate_frequency(load_data),
        }

    def _detect_resource_cycles(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect resource usage cycles."""
        cycles = {}

        for resource, data in resource_data.items():
            cycles[resource] = {
                "periodic": self._is_periodic(data),
                "frequency": self._calculate_frequency(data),
            }

        return cycles

    def _is_periodic(self, data: Dict[str, Any]) -> bool:
        """Determine if data shows periodic behavior."""
        # Simplified implementation - enhance based on needs
        if "history" not in data:
            return False

        history = data["history"]
        if len(history) < 3:
            return False

        # Check for repeating patterns
        pattern_length = len(history) // 2
        return self._has_repeating_pattern(history, pattern_length)

    def _has_repeating_pattern(self, data: List[Any], pattern_length: int) -> bool:
        """Check for repeating patterns in data."""
        if len(data) < pattern_length * 2:
            return False

        pattern = data[:pattern_length]
        next_section = data[pattern_length : pattern_length * 2]

        # Compare sections with tolerance
        tolerance = 0.1
        return all(abs(a - b) <= tolerance for a, b in zip(pattern, next_section))

    def _calculate_frequency(self, data: Dict[str, Any]) -> Optional[float]:
        """Calculate frequency of cyclic behavior."""
        if "history" not in data or len(data["history"]) < 2:
            return None

        history = data["history"]
        peaks = self._find_peaks(history)

        if len(peaks) < 2:
            return None

        # Calculate average time between peaks
        peak_intervals = [peaks[i + 1] - peaks[i] for i in range(len(peaks) - 1)]

        return 1.0 / (sum(peak_intervals) / len(peak_intervals))

    def _find_peaks(self, data: List[float]) -> List[int]:
        """Find indices of peaks in data."""
        peaks = []

        for i in range(1, len(data) - 1):
            if data[i] > data[i - 1] and data[i] > data[i + 1]:
                peaks.append(i)

        return peaks

    def _detect_anomalies(
        self, metrics: Dict[str, float], system_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect system anomalies."""
        anomalies = {}

        # Check metric anomalies
        for metric, value in metrics.items():
            if self._is_anomalous(metric, value):
                anomalies[metric] = {
                    "value": value,
                    "severity": self._calculate_anomaly_severity(metric, value),
                }

        # Check state anomalies
        state_anomalies = self._check_state_anomalies(system_state)
        if state_anomalies:
            anomalies["state"] = state_anomalies

        return anomalies

    def _is_anomalous(self, metric: str, value: float) -> bool:
        """Determine if a metric value is anomalous."""
        # Get historical values
        history = [
            state
            for timestamp, state in self.resonance_history[-20:]
            if hasattr(state, metric)
        ]

        if not history:
            return False

        # Calculate statistics
        values = [getattr(state, metric, 0.0) for state in history]
        mean = sum(values) / len(values)
        std_dev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5

        # Check if value is outside 2 standard deviations
        return abs(value - mean) > 2 * std_dev

    def _calculate_anomaly_severity(self, metric: str, value: float) -> float:
        """Calculate severity of an anomaly."""
        history = [
            state
            for timestamp, state in self.resonance_history[-20:]
            if hasattr(state, metric)
        ]

        if not history:
            return 0.0

        values = [getattr(state, metric, 0.0) for state in history]
        mean = sum(values) / len(values)
        std_dev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5

        # Calculate how many standard deviations from mean
        deviations = abs(value - mean) / std_dev if std_dev > 0 else 0

        # Normalize to 0-1 range
        return min(deviations / 4.0, 1.0)

    def _check_state_anomalies(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check for anomalies in system state."""
        anomalies = {}

        # Check component states
        if "components" in system_state:
            for comp, state in system_state["components"].items():
                if state.get("status") == "error":
                    anomalies[f"component_{comp}"] = {"type": "error", "severity": 1.0}

        # Check resource states
        if "resources" in system_state:
            for resource, metrics in system_state["resources"].items():
                if metrics.get("utilization", 0) > 0.9:
                    anomalies[f"resource_{resource}"] = {
                        "type": "high_utilization",
                        "severity": 0.8,
                    }

        return anomalies

    def _determine_resonance(
        self, metrics: Dict[str, float], pattern_analysis: Dict[str, Any]
    ) -> ResonanceState:
        """Determine system resonance state."""
        # Calculate overall health score
        if not metrics:  # Handle empty metrics
            health_score = 0.0
        else:
            health_score = sum(metrics.values()) / len(metrics)

        # Check for anomalies
        anomaly_count = len(pattern_analysis.get("anomalies", {}))

        # Determine state
        if health_score > 0.8 and anomaly_count == 0:
            return ResonanceState.HARMONIC
        elif health_score > 0.6:
            return ResonanceState.ADAPTIVE
        elif health_score > 0.4:
            return ResonanceState.DISSONANT
        else:
            return ResonanceState.CRITICAL

    def _update_resonance_history(self, new_state: ResonanceState) -> None:
        """Update resonance state history."""
        self.resonance_history.append((datetime.now(UTC), new_state))

        # Maintain history size
        while len(self.resonance_history) > 1000:
            self.resonance_history.pop(0)

        self.current_resonance = new_state

    def _store_assessment(
        self,
        resonance: ResonanceState,
        metrics: Dict[str, float],
        patterns: Dict[str, Any],
    ) -> str:
        """Store resonance assessment in memory."""
        return self.codex.store_memory(
            content={
                "type": "resonance_assessment",
                "resonance_state": resonance.value,
                "metrics": metrics,
                "patterns": patterns,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            source="echoform",
            tags=["resonance", "assessment"],
            confidence=self._calculate_assessment_confidence(metrics, patterns),
        )

    def _calculate_assessment_confidence(
        self, metrics: Dict[str, float], patterns: Dict[str, Any]
    ) -> float:
        """Calculate confidence in resonance assessment."""
        # Base confidence from metrics
        if not metrics:  # Handle empty metrics
            metric_confidence = 0.0
        else:
            metric_confidence = sum(metrics.values()) / len(metrics)

        # Adjust based on pattern clarity
        pattern_confidence = 0.5
        if patterns.get("trends"):
            pattern_confidence += 0.2
        if patterns.get("cycles"):
            pattern_confidence += 0.2
        if not patterns.get("anomalies"):
            pattern_confidence += 0.1

        return (metric_confidence + pattern_confidence) / 2.0


# Example usage:
if __name__ == "__main__":
    # Initialize dependencies
    codex = CodexAwareness()
    metacognition = MetacognitionEngine()

    # Create Echoform agent
    echoform = EchoformAgent(codex, metacognition)

    # Example resonance assessment
    async def test_assessment():
        result = await echoform.assess_resonance(
            {
                "resources": {
                    "cpu": {"utilization": 0.7},
                    "memory": {"utilization": 0.6},
                },
                "performance": {"response_time": 100, "throughput": 50},
                "errors": {"total_operations": 1000, "error_count": 5},
            }
        )
        print(f"Assessment result: {result}")

    # Run test
    import asyncio

    asyncio.run(test_assessment())
