"""
Run a simple KG vs RAG benchmark locally.

Example:
    poetry run python -m guardian.eval.run_graph_rag_benchmark --compare
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guardian.context.broker import ContextBroker
from guardian.core.ai_router import chat_with_ai
from guardian.core.config import Settings, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NullVectorStore:
    def search(self, *args, **kwargs):
        return []


class NullChatlog:
    def last_messages(self, *args, **kwargs):
        return []


def load_benchmark(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - fallback path
        raise RuntimeError(
            "PyYAML is required to load benchmark specs"
        ) from exc
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_prompt(
    question: str, context: dict[str, Any]
) -> list[dict[str, str]]:
    parts = []
    for sem in context.get("semantic", []):
        parts.append(f"SEMANTIC: {sem}")
    for mem in context.get("memory", []):
        parts.append(f"MEMORY: {mem}")
    for g in context.get("graph", []):
        txt = g.get("text") or g
        parts.append(f"GRAPH: {txt}")
    ctx_block = "\n".join(str(p) for p in parts if p)
    prompt_text = "Context:\n" + ctx_block + "\n\nQuestion: " + question
    return [{"role": "user", "content": prompt_text}]


async def run_prompt(
    prompt_spec: dict[str, Any], settings: Settings, mode: str
) -> dict[str, Any]:
    start = time.time()
    broker = ContextBroker(
        chatlog_db=NullChatlog(),
        vector_store=NullVectorStore(),
        memory_store=None,
        sensors=None,
        settings=settings,
    )

    context_bundle, trace = await broker.assemble(
        thread_id=hash(prompt_spec["id"]) % (10**6),
        query=prompt_spec["question"],
        depth="normal",
        user_id=prompt_spec.get("user_id", "default"),
    )

    messages = build_prompt(prompt_spec["question"], context_bundle)
    answer = chat_with_ai(messages, settings=settings)
    latency_ms = int((time.time() - start) * 1000)

    return {
        "id": prompt_spec["id"],
        "mode": mode,
        "latency_ms": latency_ms,
        "answer": answer,
        "model": settings.LLM_MODEL,
        "provider": settings.LLM_PROVIDER,
    }


async def main():
    parser = argparse.ArgumentParser(description="KG vs RAG benchmark")
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path(__file__).parent / "benchmarks" / "graph_rag.yaml",
    )
    parser.add_argument(
        "--with-graph", action="store_true", help="Run with graph context only"
    )
    parser.add_argument(
        "--without-graph",
        action="store_true",
        help="Run without graph context only",
    )
    parser.add_argument(
        "--compare", action="store_true", help="Run both modes for comparison"
    )
    args = parser.parse_args()

    spec = load_benchmark(args.benchmark)
    prompts = spec.get("prompts", [])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"graph_rag_{timestamp}.jsonl"

    modes: list[str] = []
    if args.compare or (not args.with_graph and not args.without_graph):
        modes = ["with-graph", "without-graph"]
    else:
        if args.with_graph:
            modes.append("with-graph")
        if args.without_graph:
            modes.append("without-graph")

    results = []
    for prompt in prompts:
        for mode in modes:
            settings = Settings(**get_settings().model_dump())
            settings.GUARDIAN_ENABLE_GRAPH_CONTEXT = mode == "with-graph"

            try:
                res = await run_prompt(prompt, settings, mode)
                results.append(res)
            except Exception as exc:
                results.append(
                    {
                        "id": prompt["id"],
                        "mode": mode,
                        "error": str(exc),
                    }
                )

    with output_path.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row) + "\n")

    # Simple console summary
    for row in results:
        mode = row.get("mode")
        status = "error" if "error" in row else "ok"
        latency = row.get("latency_ms", "-")
        logger.info(f"[{mode}] {row['id']} -> {status}, latency={latency}ms")
    logger.info(f"Report written to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
