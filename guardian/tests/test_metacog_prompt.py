from guardian.metacognition import MetacognitionEngine
from guardian.prompt_assembler import build_prompt


def test_metacog_prompt_matches_assembler():
    thread = {
        "title": "Guardian & Resonant Weekly Sync",
        "transcript": "User: how did our last ritual go?\nGuardian: It felt grounded and luminous.",
        "branch": {"name": "ritual-analysis"},
    }
    persona = {
        "name": "Guardian",
        "system_prompt": "You are Guardian, steward of continuity.",
        "anchor_points": ["Protect the user's intent", "Preserve resonance"],
    }

    overrides = {"tone": "mythic"}

    engine = MetacognitionEngine()
    expected = build_prompt(thread, persona, system_overrides=overrides)
    assert (
        engine.build_summary_prompt(thread, persona, system_overrides=overrides)
        == expected
    )
