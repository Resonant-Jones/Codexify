"""
Codemap Service Module
-------------------
Provides functionality to load and query the project's codemap.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases
CodemapEntry = Dict[str, Union[str, int]]
CodemapResult = List[CodemapEntry]


def load_codemap() -> Dict:
    """
    Load the codemap from the project root.

    Returns:
        dict: Dictionary with codemap entries if successful; otherwise, {}.
    """
    try:
        # Get the absolute path to the project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        codemap_path = os.path.join(project_root, "codemap.json")

        with open(codemap_path, "r") as f:
            codemap = json.load(f)
            logger.info(f"Successfully loaded codemap from {codemap_path}")
            return codemap

    except FileNotFoundError:
        logger.error(f"codemap.json file not found at project root: {codemap_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding codemap.json: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading codemap: {e}")

    return {}


def query_codemap(term: str, codemap: Optional[Dict] = None) -> CodemapResult:
    """
    Query the codemap using fuzzy matching based on the term.

    Args:
        term (str): The search string to match against keys and descriptions.
        codemap (dict, optional): Use provided codemap. Otherwise, load using load_codemap.

    Returns:
        list: A list of results, where each result is a dict with keys:
             file, line, description. If no matches found, returns a list
             with a single dict containing an error message.
    """
    if not term:
        return [{"message": "Search term cannot be empty"}]

    if codemap is None:
        codemap = load_codemap()

    if not codemap:
        return [{"message": "No codemap data available"}]

    results: CodemapResult = []
    term = term.lower()

    # Search through the codemap entries
    for key, info in codemap.items():
        # Skip invalid entries
        if not isinstance(info, dict):
            continue

        # Perform case-insensitive substring matching on key and description
        if term in key.lower() or term in info.get("description", "").lower():

            results.append(
                {
                    "file": info.get("file", "Unknown"),
                    "line": info.get("line", "N/A"),
                    "description": info.get("description", "No description available"),
                }
            )

    # Sort results by filename and line number for consistent output
    results.sort(key=lambda x: (x["file"], x.get("line", 0)))

    return results if results else [{"message": f"No matches found for term: {term}"}]


def format_results(results: CodemapResult, explain: bool = False) -> str:
    """
    Format the codemap query results for CLI output.

    Args:
        results (list): List of result dictionaries from query_codemap
        explain (bool): Whether to include additional explanation (placeholder)

    Returns:
        str: Formatted string ready for display
    """
    output = []

    # Handle message-only results (e.g., errors or no matches)
    if len(results) == 1 and "message" in results[0]:
        return results[0]["message"]

    # Format each result
    for idx, item in enumerate(results, 1):
        if "message" in item:
            output.append(item["message"])
        else:
            output.extend(
                [
                    f"\nResult {idx}:",
                    f"File        : {item['file']}",
                    f"Line Number : {item['line']}",
                    f"Description : {item['description']}",
                    "-" * 50,
                ]
            )

    return "\n".join(output)


# Service wrapper for codemap operations
class CodemapService:
    """
    Service wrapper for codemap operations.
    """

    def __init__(self, codemap_path: Optional[str] = None):
        """
        Initialize the service, optionally loading a custom codemap file.
        """
        from typing import Optional

        if codemap_path:
            try:
                with open(codemap_path, "r") as f:
                    self._codemap = json.load(f)
            except Exception:
                self._codemap = load_codemap()
        else:
            self._codemap = load_codemap()

    def query(self, term: str) -> CodemapResult:
        """
        Query the loaded codemap for a search term.
        """
        return query_codemap(term, self._codemap)
