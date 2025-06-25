import json
from pathlib import Path


def assemble_prompt(identity_path, cue_card_path, context_path, current_goal=None):
    # Load identity profile
    with open(identity_path, "r") as file:
        identity = json.load(file)

    # Load cue card
    with open(cue_card_path, "r") as file:
        cue_card = file.read().strip()

    # Load last context
    with open(context_path, "r") as file:
        last_context = file.read().strip()

    # Format user anchors as inline context
    anchors = "\n".join(f"- {a}" for a in identity.get("user_anchors", []))

    # Add affective trace
    mood = identity.get("affective_trace", {}).get("mood", "Unknown")
    theme = identity.get("affective_trace", {}).get("theme", "Unknown")

    # Compose full prompt
    prompt = f"""{cue_card}

User Anchors:
{anchors}

Affective Trace:
Mood: {mood}
Theme: {theme}

{last_context}

Current Goal:
{current_goal if current_goal else "Assist Resonant with ongoing work."}
"""
    return prompt


# Example usage (adjust paths as needed)
if __name__ == "__main__":
    prompt = assemble_prompt(
        identity_path="identity.json",
        cue_card_path="gregorios.prompt",
        context_path="last_context.md",
        current_goal="Assist Resonant in compiling Codexify schema routing for the desktop GUI.",
    )
    print(prompt)
