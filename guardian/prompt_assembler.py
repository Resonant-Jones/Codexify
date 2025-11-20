import json


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


# Backwards-compatible shim: build_prompt(thread, persona, system_overrides=None) -> str
# Used by tests to build prompts from thread, persona, and system overrides.
def build_prompt(thread: dict, persona: dict, system_overrides: dict = None) -> str:
    """
    Build a prompt from thread, persona, and optional system overrides.

    Backwards-compatible shim that constructs a formatted prompt string
    from thread context (title, transcript, branch) and persona information
    (name, system_prompt, anchor_points), optionally modified by system_overrides.

    Args:
        thread: Thread context dict with keys like 'title', 'transcript', 'branch'
        persona: Persona dict with keys like 'name', 'system_prompt', 'anchor_points'
        system_overrides: Optional dict of system-level overrides (e.g., 'tone')

    Returns:
        str: Formatted prompt string
    """
    # Extract thread info
    thread_title = thread.get("title", "Untitled")
    transcript = thread.get("transcript", "")
    branch_name = thread.get("branch", {}).get("name", "main")

    # Extract persona info
    persona_name = persona.get("name", "Assistant")
    system_prompt = persona.get("system_prompt", "")
    anchor_points = persona.get("anchor_points", [])

    # Apply system overrides (e.g., tone)
    overrides = system_overrides or {}
    tone = overrides.get("tone", "professional")

    # Format anchor points
    anchors_text = "\n".join(f"- {a}" for a in anchor_points)

    # Build the prompt
    prompt = f"""{system_prompt}

Thread: {thread_title}
Branch: {branch_name}
Tone: {tone}

Anchor Points:
{anchors_text}

Transcript:
{transcript}
"""
    return prompt.strip()
