import json
from pathlib import Path


def load_file(path):
    with open(path, "r") as f:
        return f.read().strip()


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def assemble_prompt(actor_name, actors_dir="actors", current_goal=None):
    actor_path = Path(actors_dir) / actor_name

    identity_path = actor_path / "identity.json"
    cue_card_path = actor_path / f"{actor_name}.prompt"
    context_path = actor_path / "last_context.md"

    identity = load_json(identity_path)
    cue_card = load_file(cue_card_path)
    last_context = load_file(context_path)

    anchors = "\n".join(f"- {a}" for a in identity.get("user_anchors", []))
    mood = identity.get("affective_trace", {}).get("mood", "Unknown")
    theme = identity.get("affective_trace", {}).get("theme", "Unknown")

    prompt = f"""{cue_card}

User Anchors:
{anchors}

Affective Trace:
Mood: {mood}
Theme: {theme}

{last_context}

Current Goal:
{current_goal if current_goal else "Assist user with ongoing task."}
"""
    return prompt


# Example usage:
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Assemble identity-based prompt for local LLM inference."
    )
    parser.add_argument("actor", help="Name of the actor (e.g., gregorios)")
    parser.add_argument("--goal", help="Optional current goal or task", default=None)
    parser.add_argument("--dir", help="Base actors directory", default="actors")
    args = parser.parse_args()

    result = assemble_prompt(args.actor, actors_dir=args.dir, current_goal=args.goal)
    print(result)
