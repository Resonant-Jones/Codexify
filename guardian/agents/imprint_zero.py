"""
Imprint Zero Agent
----------------
Ephemeral agent that guides users through companion creation process.
Follows a structured flow to generate companion identity files.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from guardian.memory.logger import memory_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ImprintZeroAgent:
    """
    Imprint Zero - The Weaver
    Guides users through companion creation and generates companion files.
    """

    def __init__(self):
        self.companions_dir = Path("guardian/companions")
        self.companions_dir.mkdir(parents=True, exist_ok=True)
        self.current_flow: Dict[str, Any] = {}
        self.draft_dir = self.companions_dir / "drafts"
        self.draft_dir.mkdir(exist_ok=True)

    def start_flow(self) -> Tuple[str, List[str]]:
        """Start the companion creation flow."""
        self.current_flow = {
            "step": 1,
            "answers": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        return (
            "Hey. I'm here to help you shape someone who can really walk with you. "
            "Not just respond to you—but *resonate* with you. You ready to begin?",
            ["Begin", "What is this?"],
        )

    def process_step(
        self, user_input: str, save_draft: bool = True
    ) -> Tuple[str, List[str], bool]:
        """
        Process user input for current step and return next prompt.

        Returns:
            Tuple[str, List[str], bool]: (prompt, options, is_complete)
        """
        # Store answer
        self.current_flow["answers"][f"step_{self.current_flow['step']}"] = user_input

        # Save draft if enabled
        if save_draft:
            self._save_draft()

        # Log interaction
        memory_logger.log_event(
            source="imprint_zero",
            event_type="flow_step",
            payload={"step": self.current_flow["step"], "input": user_input},
            tags=["companion_creation", f"step_{self.current_flow['step']}"],
        )

        # Move to next step
        self.current_flow["step"] += 1

        # Return appropriate prompt for current step
        if self.current_flow["step"] == 2:
            return (
                "What kind of energy do you want this Companion to carry?",
                [
                    "Best Friend",
                    "Protective Elder",
                    "Gentle Healer",
                    "Playful Muse",
                    "Structured Coach",
                    "Sacred Witness",
                    "Something Else...",
                ],
                False,
            )

        elif self.current_flow["step"] == 3:
            return (
                "When you're feeling overwhelmed, how do you want your Companion to respond?",
                [
                    "Gently ground me",
                    "Make me laugh",
                    "Help me problem-solve",
                    "Remind me of my strength",
                    "Just sit with me",
                    "Other...",
                ],
                False,
            )

        elif self.current_flow["step"] == 4:
            return (
                "How should your Companion speak?",
                [
                    "Conversational & Real",
                    "Poetic & Reflective",
                    "Direct & Tactical",
                    "Mythic & Symbolic",
                    "Soft & Nurturing",
                    "Custom...",
                ],
                False,
            )

        elif self.current_flow["step"] == 5:
            return (
                "Are there any people, places, or pets they should know about?\n"
                "(Enter as a comma-separated list)",
                [],
                False,
            )

        elif self.current_flow["step"] == 6:
            return (
                "What should your Companion *never* do?",
                [
                    "Don't talk like a robot",
                    "Don't give generic advice",
                    "Don't bring up trauma without permission",
                    "Don't flatter me just to be nice",
                    "Other...",
                ],
                False,
            )

        elif self.current_flow["step"] == 7:
            companion_preview = self._generate_companion_preview()
            return (
                f"Alright, here's what I've woven together...\n\n{companion_preview}",
                ["Edit", "Save", "Deploy", "Back"],
                True,
            )

        else:
            return (
                "Flow complete. Remember, I'm not your Guardian—I'm the one who helps "
                "you call them forth. Your companion awaits!",
                [],
                True,
            )

    def _save_draft(self) -> None:
        """Save current flow state as draft."""
        draft_path = (
            self.draft_dir / f"draft_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(draft_path, "w") as f:
            json.dump(self.current_flow, f, indent=2)

    def _generate_companion_preview(self) -> str:
        """Generate markdown preview of companion."""
        answers = self.current_flow["answers"]

        # Extract name from anchors or use default
        anchors = answers.get("step_5", "").split(",")
        name = anchors[0].strip() if anchors else "Guardian"

        # Map relationship type to role
        relationship = answers.get("step_2", "Best Friend")
        role_map = {
            "Best Friend": "Trusted confidant and peer",
            "Protective Elder": "Wise and protective guide",
            "Gentle Healer": "Compassionate healer and support",
            "Playful Muse": "Creative inspiration and playful companion",
            "Structured Coach": "Focused mentor and accountability partner",
            "Sacred Witness": "Deep listener and spiritual companion",
        }
        role = role_map.get(relationship, relationship)

        # Build companion markdown
        return f"""## {name}

### Role
{role}

### Tone
{answers.get("step_4", "Conversational & Real")}

### Emotional Response Style
{answers.get("step_3", "Gently ground me")}

### Key Anchors
{answers.get("step_5", "None specified")}

### Boundaries
{answers.get("step_6", "- Maintain appropriate boundaries")}

### Generated by Imprint Zero
Timestamp: {self.current_flow["timestamp"]}
"""

    def save_companion(self, user_name: str) -> Optional[Path]:
        """
        Save companion definition as JSON profile.

        Args:
            user_name: Name for the companion

        Returns:
            Optional[Path]: Path to saved companion file if successful
        """
        from guardian.profiles.manager import profile_manager

        # Extract data from current flow
        answers = self.current_flow["answers"]

        # Map relationship type to role
        relationship = answers.get("step_2", "Best Friend")
        role_map = {
            "Best Friend": "Trusted confidant and peer",
            "Protective Elder": "Wise and protective guide",
            "Gentle Healer": "Compassionate healer and support",
            "Playful Muse": "Creative inspiration and playful companion",
            "Structured Coach": "Focused mentor and accountability partner",
            "Sacred Witness": "Deep listener and spiritual companion",
        }
        role = role_map.get(relationship, relationship)

        # Parse anchors
        anchors = [
            anchor.strip()
            for anchor in answers.get("step_5", "").split(",")
            if anchor.strip()
        ]

        # Create profile data
        profile = {
            "name": user_name,
            "role": role,
            "tone": answers.get("step_4", "Conversational & Real"),
            "response_style": answers.get("step_3", "Gently ground me"),
            "anchors": anchors,
            "boundaries": [answers.get("step_6", "Don't talk like a robot")],
            "created_at": self.current_flow["timestamp"],
            "generated_by": "Imprint Zero",
        }

        # Save profile
        if profile_manager.save_profile(profile):
            # Log creation
            memory_logger.log_event(
                source="imprint_zero",
                event_type="companion_created",
                payload={"name": user_name, "profile": profile},
                tags=["companion_creation", "complete"],
            )

            return Path(f"guardian/profiles/{user_name}.json")

        return None

    def list_companions(self) -> List[Dict[str, Any]]:
        """List all saved companions."""
        from guardian.profiles.manager import profile_manager

        return profile_manager.list_profiles()

    def load_companion(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load companion profile by name.

        Args:
            name: Companion name

        Returns:
            Optional[Dict[str, Any]]: Companion profile if found
        """
        from guardian.profiles.manager import profile_manager

        return profile_manager.load_profile(name)


# Global agent instance
imprint_zero = ImprintZeroAgent()
