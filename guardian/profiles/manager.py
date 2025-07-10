"""
Companion Profile Manager
----------------------
Handles storage, retrieval, and activation of companion profiles.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CompanionProfileManager:
    """Manages companion profiles and registry."""

    def __init__(self):
        self.profiles_dir = Path("guardian/profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = Path("guardian/agent_registry.json")
        self._ensure_registry()

    def _ensure_registry(self) -> None:
        """Ensure registry file exists with proper structure."""
        if not self.registry_path.exists():
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_registry({"companions": []})

    def _load_registry(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load companion registry."""
        try:
            with open(self.registry_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {"companions": []}

    def _save_registry(self, registry: Dict[str, List[Dict[str, Any]]]) -> None:
        """Save companion registry."""
        try:
            with open(self.registry_path, "w") as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize name for use in filenames."""
        return "".join(c for c in name if c.isalnum() or c in "._- ").strip()

    def save_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Save companion profile and update registry.

        Args:
            profile: Companion profile data

        Returns:
            bool: True if saved successfully
        """
        name = profile.get("name")
        if not name:
            logger.error("Profile must have a name")
            return False

        # Sanitize filename
        safe_name = self._sanitize_filename(name)
        if not safe_name:
            logger.error("Invalid profile name")
            return False

        # Check for duplicates
        registry = self._load_registry()
        if any(comp["name"] == name for comp in registry["companions"]):
            logger.error(f"Companion '{name}' already exists")
            return False

        # Save profile file
        profile_path = self.profiles_dir / f"{safe_name}.json"
        try:
            with open(profile_path, "w") as f:
                json.dump(profile, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            return False

        # Update registry
        registry["companions"].append(
            {"name": name, "path": str(profile_path), "active": False}
        )
        self._save_registry(registry)

        logger.info(f"Saved companion profile: {name}")
        return True

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load companion profile by name.

        Args:
            name: Companion name

        Returns:
            Optional[Dict[str, Any]]: Profile data if found
        """
        safe_name = self._sanitize_filename(name)
        profile_path = self.profiles_dir / f"{safe_name}.json"

        try:
            with open(profile_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load profile '{name}': {e}")
            return None

    def delete_profile(self, name: str) -> bool:
        """
        Delete companion profile and registry entry.

        Args:
            name: Companion name

        Returns:
            bool: True if deleted successfully
        """
        safe_name = self._sanitize_filename(name)
        profile_path = self.profiles_dir / f"{safe_name}.json"

        # Remove profile file
        try:
            if profile_path.exists():
                profile_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete profile file: {e}")
            return False

        # Update registry
        registry = self._load_registry()
        registry["companions"] = [
            comp for comp in registry["companions"] if comp["name"] != name
        ]
        self._save_registry(registry)

        logger.info(f"Deleted companion profile: {name}")
        return True

    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all companion profiles.

        Returns:
            List[Dict[str, Any]]: List of companion metadata
        """
        registry = self._load_registry()
        return registry["companions"]

    def deploy_profile(self, name: str) -> bool:
        """
        Set companion as active in registry.

        Args:
            name: Companion name

        Returns:
            bool: True if deployed successfully
        """
        # Verify profile exists
        if not self.load_profile(name):
            logger.error(f"Profile '{name}' not found")
            return False

        # Update registry
        registry = self._load_registry()
        found = False

        for comp in registry["companions"]:
            if comp["name"] == name:
                comp["active"] = True
                found = True
            else:
                comp["active"] = False

        if not found:
            logger.error(f"Profile '{name}' not found in registry")
            return False

        self._save_registry(registry)
        logger.info(f"Deployed companion profile: {name}")
        return True


# Global profile manager instance
profile_manager = CompanionProfileManager()
