import json
import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

__all__ = ["Agent", "_extract_response"]

"""Abstract base class and utilities for Guardian Agents."""


class Agent(ABC):
    """
    Abstract base class for Guardian Agents.

    Each agent must implement:
      - run: Executes the agent’s primary logic.
      - get_recv_format: Specifies the input schema.
      - get_send_format: Specifies the output schema.
    """

    def __init__(self, model: Any):
        self.model = model
        self.name: str = ""
        self.description: str = ""

    """
        An agent should have a run method such that it can run it's workflow
        NOTE: choosing right tool for the right job should also place in the run method
    """

    @abstractmethod
    async def run(self, response, data=None):
        pass

    @abstractmethod
    def get_recv_format(self) -> BaseModel:
        pass

    @abstractmethod
    def get_send_format(self) -> BaseModel:
        pass


def _extract_response(res):
    """
    Extracts the JSON string from a markdown code block or direct string.
    Handles LLM output as dict or string, logs debug info.
    Fallback: bracket-matching to find best JSON blob if needed.
    """

    # 1. If it's a dict with 'choices', extract actual string content
    if isinstance(res, dict) and "choices" in res:
        try:
            res = res["choices"][0]["message"]["content"]
        except Exception as e:
            print(
                f"[DEBUG] _extract_response: Could not extract content from dict: {e}\nGot: {res}"
            )
            return None

    # 2. If not string now, bail out with debug
    if not isinstance(res, str):
        print(f"[DEBUG] _extract_response: Expected string, got {type(res)}: {res}")
        return None

    # 3. Try to extract JSON from Markdown code block
    markdown_pattern = r"```(?:json)?\n([\s\S]+?)\n```"
    markdown_matches = re.findall(markdown_pattern, res, re.DOTALL)
    if markdown_matches:
        extracted = markdown_matches[0].strip()
        print(f"[DEBUG] _extract_response: Extracted markdown block:\n{extracted}")
        return extracted

    # 4. Try to parse the raw string as JSON
    try:
        json.loads(res.strip())
        print(f"[DEBUG] _extract_response: Raw content is valid JSON:\n{res.strip()}")
        return res.strip()
    except Exception:
        print(
            f"[DEBUG] _extract_response: Raw content is not valid JSON. Trying fallback extraction."
        )

    # 5. Fallback: Try to extract JSON objects or arrays from within the string
    json_candidates = []
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = 0
        while True:
            start_pos = res.find(start_char, start_idx)
            if start_pos == -1:
                break
            bracket_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(res)):
                char = res[i]
                if char == start_char:
                    bracket_count += 1
                elif char == end_char:
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i
                        break
            if bracket_count == 0 and end_pos > start_pos:
                candidate = res[start_pos : end_pos + 1].strip()
                json_candidates.append(candidate)
            start_idx = start_pos + 1
    for candidate in reversed(json_candidates):
        try:
            json.loads(candidate)
            print(
                f"[DEBUG] _extract_response: Extracted valid fallback JSON candidate:\n{candidate}"
            )
            return candidate
        except json.JSONDecodeError:
            continue

    print(f"[DEBUG] _extract_response: No valid JSON found after all attempts.")
    return None
