

# 🧠 memory_agent.py
"""
This agent interfaces with the Codex-style memory logs,
retrieving entries based on tags, timestamps, or keywords.
"""

import os

# For demo purposes, define a simple memory log directory
MEMORY_DIR = "codex_memory"

def fetch_memory(tag: str = None, keyword: str = None):
    logs = []

    if not os.path.exists(MEMORY_DIR):
        return {"status": "error", "message": f"Memory directory '{MEMORY_DIR}' not found."}

    for filename in os.listdir(MEMORY_DIR):
        if filename.endswith(".md"):
            with open(os.path.join(MEMORY_DIR, filename), "r") as f:
                content = f.read()
                if (tag and f"#{tag}" in content) or (keyword and keyword.lower() in content.lower()):
                    logs.append({"file": filename, "excerpt": content[:300]})

    return {
        "status": "ok",
        "results": logs if logs else "No relevant entries found."
    }