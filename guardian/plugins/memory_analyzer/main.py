# guardian/plugins/memory_analyzer/main.py

from datetime import datetime

class MemoryAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.codex = None
        self.metacognition = None

    async def analyze_memories(self) -> dict:
        memories = self.codex.query_memories()
        patterns = await self.detect_patterns(memories)
        stats = self.calculate_statistics(memories)
        return {"patterns": patterns, "statistics": stats}

    async def detect_patterns(self, memories: list[dict]) -> list:
        contents = [m.get("content", "") for m in memories]
        return [c for c in set(contents) if contents.count(c) > 1]

    def calculate_statistics(self, memories: list[dict]) -> dict:
        confidences = [m.get("confidence", 1.0) for m in memories]
        total = len(memories)
        avg_conf = sum(confidences) / total if total else 0.0
        return {"total_memories": total, "average_confidence": avg_conf}

    def filter_memories(self, memories: list[dict], tags: list[str]) -> list[dict]:
        return [m for m in memories if any(tag in m.get("tags", []) for tag in tags)]

    def get_metadata(self) -> dict:
        return {
            "name": "MemoryAnalyzer",
            "version": "1.0",
            "description": "Analyzes memories and detects patterns.",
            "capabilities": ["analysis", "pattern_detection", "statistics"]
        }

    def health_check(self) -> dict:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }