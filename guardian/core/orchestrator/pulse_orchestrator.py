"""
This is the command interpreter that receives Gemma's structured outputs,
routes them to appropriate agents, and returns their responses.

Gemma speaks in structured language (dict-like), and this orchestrator
translates her will into agentic action.
"""

import json


def _get_effective_timeout():
    try:
        # Use module-level settings so tests can patch it
        _s = settings  # type: ignore[name-defined]
    except Exception:
        _s = None
    # prefer settings.AGENT_TIMEOUT_SECONDS if present; else env; else 2.0
    if _s is not None:
        try:
            val = getattr(_s, "AGENT_TIMEOUT_SECONDS", None)
            if val is not None:
                return float(val)
        except Exception:
            pass
    import os

    env = os.getenv("FORESIGHT_TIMEOUT")
    if env and env.strip():
        try:
            return float(env)
        except Exception:
            pass
    return 2.0


import logging

logger = logging.getLogger(__name__)
import asyncio
import os
import random
from concurrent.futures import TimeoutError
from functools import lru_cache

try:
    from pebble import ProcessPool  # type: ignore

    _HAVE_PEBBLE = True
except Exception:  # ImportError or runtime issues
    from concurrent.futures import (
        ProcessPoolExecutor as ProcessPool,  # type: ignore
    )

    _HAVE_PEBBLE = False

import logging

# --- Load environment variables from .env if present ---
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from guardian.core.client_factory import get_memoryos_instance
from guardian.core.config import settings
from guardian.core.orchestrator.agents.foresight_agent import run_foresight
from guardian.core.orchestrator.agents.health_agent import get_health_summary
from guardian.core.orchestrator.agents.memory_agent import fetch_memory
from guardian.core.orchestrator.agents.ritual_agent import trigger_ritual

logger = logging.getLogger(__name__)
# Load environment variables from .env file
load_dotenv()
logger.info("🔑 GOOGLE_API_KEY: %s", os.getenv("GOOGLE_API_KEY"))
logger.info("🔑 GEMINI_API_KEY: %s", os.getenv("GEMINI_API_KEY"))
logger.info("🔑 OPENAI_API_KEY: %s", os.getenv("OPENAI_API_KEY"))


app = FastAPI()

# Map action strings to their corresponding agent functions for cleaner, scalable routing.
AGENT_ACTIONS = {
    "get_health_summary": get_health_summary,
    "trigger_ritual": trigger_ritual,
    "fetch_memory": fetch_memory,
    "run_foresight": run_foresight,
}


@lru_cache(maxsize=128)
def cached_agent_task(agent_name: str, params_json: str):
    # Deserialize params
    params = json.loads(params_json)
    memory_client = get_memoryos_instance()
    agent_function = AGENT_ACTIONS.get(agent_name)
    return agent_function(memory_client=memory_client, **params)


class OrchestrateCommand(BaseModel):
    action: str
    params: dict


def _execute_agent_task(agent_function, params: dict):
    """
    Internal helper to run the agent in a separate process.
    This allows for isolation and timeout control.

    Note: Caching is handled above if 'use_cache' is True.
    """
    # Each process gets its own singleton instance from the factory.
    # The lru_cache on get_memoryos_instance is per-process.

    memory_client = get_memoryos_instance()

    # NOTE: For large payloads, implement generator or async streaming logic here.

    return agent_function(memory_client=memory_client, **params)


def orchestrate(command: dict):
    action = command.get("action")
    params = command.get("params", {})
    logger.info(f"Orchestrating action: {action} with params: {params}")

    # Handle the 'run_model' action separately as it has a unique setup.
    if action == "run_model":
        try:
            from guardian.core.orchestrator.model_loader import (
                load_model_backend,
            )

            prompt = params.get("prompt", "")
            model = load_model_backend("default")
            response = model.generate(prompt)
            logger.info("Action 'run_model' executed successfully")
            return {"status": "ok", "response": response}
        except Exception as e:
            logger.exception(f"Error executing 'run_model' action: {e}")
            return {"status": "error", "message": f"Failed to run model: {e}"}

    # Look up the agent function from our mapping.
    agent_function = AGENT_ACTIONS.get(action)

    if not agent_function:
        logger.warning(f"Unknown action received: {action}")
        return {"status": "error", "message": f"Unknown action '{action}'."}

    # Determine if caching should be used
    use_cache = params.get("use_cache", False)

    # Execute the agent function, optionally using cache, in a separate process to enforce a timeout.
    try:
        if use_cache:
            # Use in-memory LRU cache for results.
            # TODO: For multiple orchestrator instances, integrate a distributed cache like Redis.
            result = cached_agent_task(action, json.dumps(params))
        else:
            # In pytest, avoid spawning a separate process so monkeypatches apply
            # Determine effective timeout (allow FORESIGHT_TIMEOUT override for foresight runs)
            effective_timeout = (
                _get_effective_timeout()
                if action == "run_foresight"
                else settings.AGENT_TIMEOUT_SECONDS
            )

            if os.getenv("PYTEST_CURRENT_TEST"):
                from concurrent.futures import ThreadPoolExecutor

                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_execute_agent_task, agent_function, params)
                    try:
                        result = fut.result(timeout=effective_timeout)
                    except TimeoutError:
                        if action == "run_foresight":
                            jitter = 0.2 + random.random() * 0.3
                            logger.warning(
                                "run_foresight soft-timeout after %ss; retrying once (+~%ss jitter)",
                                effective_timeout,
                                round(jitter, 2),
                            )
                            import time as _t

                            _t.sleep(jitter)
                            result = ex.submit(
                                _execute_agent_task, agent_function, params
                            ).result(timeout=effective_timeout)
                        else:
                            raise
            elif _HAVE_PEBBLE:
                with ProcessPool() as pool:  # pebble ProcessPool
                    try:
                        future = pool.schedule(
                            function=_execute_agent_task,
                            args=[agent_function, params],
                            timeout=effective_timeout,
                        )
                        result = (
                            future.result()
                        )  # Blocks until completion or timeout
                    except TimeoutError:
                        if action == "run_foresight":
                            jitter = 0.2 + random.random() * 0.3
                            logger.warning(
                                "run_foresight soft-timeout after %ss; retrying once (+~%ss jitter)",
                                effective_timeout,
                                round(jitter, 2),
                            )
                            import time as _t

                            _t.sleep(jitter)
                            future = pool.schedule(
                                function=_execute_agent_task,
                                args=[agent_function, params],
                                timeout=effective_timeout,
                            )
                            result = future.result()
                        else:
                            raise
            else:
                # Fallback using stdlib ProcessPoolExecutor with timeout
                from concurrent.futures import ProcessPoolExecutor

                with ProcessPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_execute_agent_task, agent_function, params)
                    try:
                        result = fut.result(timeout=effective_timeout)
                    except TimeoutError:
                        if action == "run_foresight":
                            jitter = 0.2 + random.random() * 0.3
                            logger.warning(
                                "run_foresight soft-timeout after %ss; retrying once (+~%ss jitter)",
                                effective_timeout,
                                round(jitter, 2),
                            )
                            import time as _t

                            _t.sleep(jitter)
                            result = ex.submit(
                                _execute_agent_task, agent_function, params
                            ).result(timeout=effective_timeout)
                        else:
                            raise

        logger.info(f"Action '{action}' executed successfully")
        return result
    except TimeoutError:
        logger.error(
            f"Action '{action}' timed out after {settings.AGENT_TIMEOUT_SECONDS} seconds."
        )
        return {"status": "error", "message": f"Action '{action}' timed out."}
    except Exception as e:
        # Log the full exception traceback for effective debugging.
        logger.exception(
            f"An unexpected error occurred while executing action '{action}'"
        )
        # Return a standardized error response to the caller.
        return {
            "status": "error",
            "message": f"An unexpected error occurred in the agent for action '{action}'.",
            "details": str(e),
        }


async def orchestrate_streaming(command: dict):
    """
    Async generator for streaming orchestration of chunked or large instructions.
    UI should handle newline-delimited JSON chunks for live updates.
    """
    action = command.get("action")
    params = command.get("params", {})
    logger.info(f"Streaming orchestrator started for action: {action}")

    # Split instructions into chunks if needed
    chunks = params.get("chunks", [])
    if not chunks:
        chunks = [params]  # Fallback to single chunk if none provided

    for idx, chunk_params in enumerate(chunks):
        logger.info(f"Processing chunk {idx+1}/{len(chunks)}: {chunk_params}")
        chunk_command = {"action": action, "params": chunk_params}

        result = orchestrate(chunk_command)
        yield json.dumps({"chunk": idx + 1, "result": result}) + "\n"

        # Optional delay to simulate processing time and keep spinner alive
        await asyncio.sleep(0.1)


# TODO: Consider better chunking logic on the client-side or pre-processing large instructions.


@app.post("/orchestrate")
async def orchestrate_endpoint(command: OrchestrateCommand, request: Request):
    command_dict = command.dict()
    # Detect streaming requests via 'stream' param
    if command_dict.get("params", {}).get("stream", False):
        return StreamingResponse(
            orchestrate_streaming(command_dict), media_type="application/json"
        )
    else:
        response = orchestrate(command_dict)
        if response.get("status") == "error":
            raise HTTPException(status_code=400, detail=response)
        return JSONResponse(content=response)


@app.get("/health")
async def health_check():
    return {"status": "ok", "orchestrator": "alive"}


# To run: uvicorn guardian.core.orchestrator.pulse_orchestrator:app --reload
# Example usage for testing
if __name__ == "__main__":
    test_command = {
        "action": "trigger_ritual",
        "params": {"name": "evening_grounding"},
    }
    result = orchestrate(test_command)
    logger.info(json.dumps(result, indent=2))
