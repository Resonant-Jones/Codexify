from __future__ import annotations

from guardian.contracts.imprint_snapshot import ImprintSignalSnapshot
from guardian.services.imprint_proposal_service import build_imprint_proposal


def test_proposal_generation_is_deterministic_from_snapshot():
    snapshot = ImprintSignalSnapshot(
        snapshot_version=1,
        builder_version="imprint-snapshot-v1",
        user_id="u1",
        project_id=7,
        scope_kind="project_scoped",
        requested_depth="deep",
        project_identity_depth="deep",
        settings={
            "memory_mode": "deep",
            "diary_requires_unlock": False,
            "allow_sensitive_modeling": True,
            "requested_depth": "deep",
            "project_identity_depth": "deep",
        },
        folded_state={
            "user_global": {
                "state_payload": {
                    "communication_profile": {
                        "tone": "direct",
                        "verbosity": "concise",
                        "formality": "casual",
                        "directness": "high",
                    },
                    "preferred_name": "friend",
                    "name_hints": ["ari"],
                    "persona_hints": ["keep answers grounded"],
                    "prompt_hints": ["ask clarifying questions"],
                    "question_topics": ["preferences"],
                    "tags": ["friendly"],
                    "signal_counts": {"speech_pattern": 1},
                    "trait_scores": {"directness": 0.9},
                    "trait_sample_counts": {"directness": 1},
                    "source_observation_count": 1,
                }
            },
            "project_scoped": {
                "state_payload": {
                    "communication_profile": {
                        "tone": "direct",
                        "verbosity": "concise",
                        "formality": "casual",
                        "directness": "high",
                    },
                    "preferred_name": "friend",
                    "name_hints": ["ari"],
                    "persona_hints": ["keep answers grounded"],
                    "prompt_hints": ["ask clarifying questions"],
                    "question_topics": ["preferences"],
                    "tags": ["friendly"],
                    "signal_counts": {"speech_pattern": 1},
                    "trait_scores": {"directness": 0.9},
                    "trait_sample_counts": {"directness": 1},
                    "source_observation_count": 1,
                }
            },
        },
        effective_state={
            "communication_profile": {
                "tone": "direct",
                "verbosity": "concise",
                "formality": "casual",
                "directness": "high",
            },
            "preferred_name": "friend",
            "name_hints": ["ari"],
            "persona_hints": ["keep answers grounded"],
            "prompt_hints": ["ask clarifying questions"],
            "question_topics": ["preferences"],
            "tags": ["friendly"],
            "signal_counts": {"speech_pattern": 2},
            "trait_scores": {"directness": 0.9},
            "source_observation_count": 2,
            "combined_markers": [
                "ari",
                "friendly",
                "keep answers grounded",
                "preferences",
                "ask clarifying questions",
            ],
            "derived_characteristics": {
                "tone": "direct",
                "verbosity": "concise",
                "formality": "casual",
                "directness": "high",
            },
        },
    )

    proposal1 = build_imprint_proposal(snapshot)
    proposal2 = build_imprint_proposal(snapshot)

    assert proposal1.proposal_name == proposal2.proposal_name
    assert proposal1.persona_draft == proposal2.persona_draft
    assert proposal1.prompt_metadata == proposal2.prompt_metadata
    assert proposal1.prompt_metadata["snapshot_hash"] == snapshot.snapshot_hash
    assert (
        proposal1.prompt_metadata["generator_version"] == "imprint-proposal-v1"
    )
    assert proposal1.prompt_metadata["proposal_name"] == proposal1.proposal_name
    assert proposal1.preferred_name == "friend"
