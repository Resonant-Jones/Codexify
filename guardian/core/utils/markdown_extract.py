import json
import re


def extract_json_from_markdown(markdown_text: str):
    """
    Extract the first JSON object found inside a markdown code block from the given markdown text.
    """
    pattern = r"```json\\n(.*?)\\n```"
    match = re.search(pattern, markdown_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON block found in markdown.")

    json_str = match.group(1)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in markdown: {e}")
