import argparse
import asyncio
import datetime
import os
from typing import Optional

import yaml

from guardian.core.research.Modules.agent.search import SearchAgent
from guardian.core.utils.hybrid_router import HybridRouter
from guardian.core.utils.markdown_extract import extract_json_from_markdown


# --- Model backend router ---
def get_model_backend(model_name: str):
    local_models = {"gemma3:1b", "gemma3:2b", "gemma3:7b"}
    return "local" if model_name in local_models else "remote"


class LookingGlassAgent(SearchAgent):
    """Alias of SearchAgent for LookingGlass CLI interface."""

    pass


def generate_markdown_log(
    query: str,
    output: str,
    model: str = "gemma3",
    generated_by: str = "lookingglass",
    tags: Optional[list[str]] = None,
    base_dir: str = os.path.expanduser("~/ResearchVault/lookingglass"),
) -> str:
    if tags is None:
        tags = []
    now = datetime.datetime.utcnow()
    iso_timestamp = now.isoformat() + "Z"
    date_path = now.strftime("%Y/%m/%d")
    safe_query = query[:30].replace(" ", "_").replace("/", "-")
    filename = f"{now.strftime('%Y-%m-%d_%H%M%S')}_{safe_query}.md"

    full_path = os.path.join(base_dir, date_path)
    os.makedirs(full_path, exist_ok=True)
    filepath = os.path.join(full_path, filename)

    metadata = {
        "type": "research",
        "model": model,
        "generated_by": generated_by,
        "query": query,
        "timestamp": iso_timestamp,
        "tags": tags,
    }
    yaml_header = "---\n" + yaml.dump(metadata) + "---\n\n"

    content = (
        f"# Research Summary\n\n"
        f"## Query\n\n{query}\n\n"
        f"## Output\n\n```json\n{output}\n```\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(yaml_header)
        f.write(content)

    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run LookingGlass (Spy) Search queries via CLI"
    )
    parser.add_argument("-q", "--query", required=True, help="Search query string")
    parser.add_argument(
        "-b",
        "--backend",
        default="ollama",
        help="Model backend: ollama, gemini, openai",
    )
    parser.add_argument(
        "-m", "--model", default="gemma3:1b", help="Model identifier (e.g., gemma3:1b)"
    )
    args = parser.parse_args()

    backend_map = {
        "ollama": None,  # import deferred below
        "gemini": None,
        "openai": None,
    }

    # Determine model using HybridRouter unless explicitly overridden
    if args.model:
        model_name = args.model
    else:
        model_name, _ = HybridRouter.get_model(task_type="research")
        print(f"[Router] Using model: {model_name}")

    backend = get_model_backend(model_name)

    # Import dynamically to avoid unused import warnings
    if args.backend == "ollama":
        from guardian.core.research.Modules.model import ollama

        ModelClass = ollama.Ollama
    elif args.backend == "gemini":
        from guardian.core.research.Modules.model import gemini

        ModelClass = gemini.Gemini
    elif args.backend == "openai":
        from guardian.core.research.Modules.model import openai

        ModelClass = openai.OpenAI
    else:
        from guardian.core.research.Modules.model import ollama

        ModelClass = ollama.Ollama

    if backend == "local":
        print("[Router] Using local model backend")
        model_instance = ModelClass(model_name)
        agent = LookingGlassAgent(model=model_instance)
    else:
        print("[Router] Using remote planner backend")
        from guardian.core.research.Modules.agent.remote_planner import (
            RemotePlannerAgent,
        )

        agent = RemotePlannerAgent()

    async def run_agent():
        planner_output = await agent.run(args.query, [])

        import json

        if isinstance(planner_output, str):
            try:
                planner_tasks = json.loads(planner_output)
            except json.JSONDecodeError:
                extracted = extract_json_from_markdown(planner_output)
                if extracted:
                    try:
                        planner_tasks = json.loads(extracted)
                    except json.JSONDecodeError:
                        print(
                            "[ERROR] Failed to parse extracted JSON block from planner output."
                        )
                        print(extracted)
                        planner_tasks = []
                else:
                    print("[ERROR] No JSON block found in planner output.")
                    print(planner_output)
                    planner_tasks = []
        else:
            planner_tasks = planner_output

        if not planner_tasks:
            print("[ERROR] Planner returned no valid tasks. Raw output:")
            print(planner_output)
            return

        results = []
        i = 0
        while i < len(planner_tasks) - 1:
            try:
                task1 = planner_tasks[i]
                task2 = planner_tasks[i + 1]
            except (IndexError, KeyError) as e:
                print(f"[ERROR] Task indexing issue at index {i}: {e}")
                break

            if task1["tool"] == "url_search" and task2["tool"] == "page_content":
                urls = await agent._search_url(
                    task1["keyword"], [], task1["search_engine"]
                )
                page_data = await agent._summarize_pages(urls)
                results.append(
                    {"search": task1["keyword"], "urls": urls, "summary": page_data}
                )
                i += 2
            else:
                print(
                    f"Unexpected task pair at index {i}: {task1['tool']} then {task2['tool']}"
                )
                i += 1

        final_output = {"agent": "planner", "data": results, "task": args.query}

        output_str = json.dumps(final_output, indent=2)
        log_path = generate_markdown_log(
            query=args.query,
            output=output_str,
            model=model_name,
            generated_by="lookingglass",
            tags=[],
        )
        print(f"Markdown log saved to: {log_path}")

        with open(log_path, "r", encoding="utf-8") as f:
            print(f.read())

    asyncio.run(run_agent())
