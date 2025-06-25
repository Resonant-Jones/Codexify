import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path.home() / ".pulseos" / "actors"


def list_companions() -> None:
    """List all companions in the BASE_DIR. Handles missing dir and empty state."""
    try:
        if not BASE_DIR.exists() or not BASE_DIR.is_dir():
            print(
                f"ℹ️  No companions found. Directory does not exist: {BASE_DIR.resolve()}"
            )
            return
        companions = [p.name for p in BASE_DIR.iterdir() if p.is_dir()]
        if not companions:
            print(f"ℹ️  No companions found in {BASE_DIR.resolve()}")
            return
        print(f"📜 Companions in {BASE_DIR.resolve()}:")
        for name in sorted(companions):
            print(f" - {name}")
    except Exception as e:
        print(f"❌ Failed to list companions: {e}")


def delete_companion(actor_name: str) -> None:
    """Delete a companion's folder and all files inside it, with confirmation and error handling."""
    actor_path = BASE_DIR / actor_name
    if not actor_path.exists() or not actor_path.is_dir():
        print(f"⚠️  Companion '{actor_name}' not found in {BASE_DIR.resolve()}")
        return
    print(
        f"⚠️  You are about to delete companion '{actor_name}' and all its data in {actor_path.resolve()}."
    )
    print(
        "🔒 This action is irreversible! Consider backing up your identities folder first."
    )
    confirm = input(
        f"Type the companion's name ({actor_name}) to confirm deletion: "
    ).strip()
    if confirm != actor_name:
        print("❌ Deletion cancelled. Name did not match.")
        return
    try:
        shutil.rmtree(actor_path)
        print(f"🗑️  Companion '{actor_name}' deleted from {BASE_DIR.resolve()}")
    except Exception as e:
        print(f"❌ Failed to delete companion '{actor_name}': {e}")


def create_identity(actor_name: str) -> None:
    """Create a new companion identity with a default imprint zero template."""
    actor_path = BASE_DIR / actor_name
    try:
        actor_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ Failed to create directory '{actor_path}': {e}")
        return

    identity = {
        "name": actor_name,
        "voice": "Undefined",
        "core_values": [],
        "rituals": [],
        "style_guidelines": {"avoid": [], "prefer": []},
        "user_anchors": [],
        "last_seen": datetime.now(datetime.UTC).isoformat() + "Z",
        "affective_trace": {"mood": "Neutral", "theme": "Unformed"},
    }

    cue_card = f"You are {actor_name}, a new companion. You have no fixed form yet.\nAsk questions, observe, and adapt to support your user over time."

    last_context = "## Last Two Interactions\n\n(None yet.)"

    try:
        with open(actor_path / "identity.json", "w") as f:
            json.dump(identity, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to write identity.json for '{actor_name}': {e}")
        return

    try:
        with open(actor_path / f"{actor_name}.prompt", "w") as f:
            f.write(cue_card)
    except Exception as e:
        print(f"❌ Failed to write prompt file for '{actor_name}': {e}")
        return

    try:
        with open(actor_path / "last_context.md", "w") as f:
            f.write(last_context)
    except Exception as e:
        print(f"❌ Failed to write last_context.md for '{actor_name}': {e}")
        return

    print(f"🔄 New companion '{actor_name}' created in {actor_path}")
    print("ℹ️  Identities are stored in:", BASE_DIR.resolve())
    print(
        "🔒 Please back up this folder (e.g. to iCloud/Google Drive) to preserve your companions and memories."
    )


def switch_identity(actor_name: str) -> None:
    """Switch to an existing companion identity if it exists."""
    path = BASE_DIR / actor_name
    if not path.exists():
        print(
            f"⚠️ Companion '{actor_name}' not found. Run with --create to start a new one."
        )
        return
    try:
        print(f"✅ Switched to companion: {actor_name}")
        print(f"📁 Path: {path.resolve()}")
        print("ℹ️  Identities are stored in:", BASE_DIR.resolve())
        print(
            "🔒 Please back up this folder (e.g. to iCloud/Google Drive) to preserve your companions and memories."
        )
    except Exception as e:
        print(f"❌ Error accessing path information for '{actor_name}': {e}")


def backup_identities(backup_path: str = None) -> str:
    """Create a zip archive backup of the identities directory.

    Args:
        backup_path (str, optional): The base path for the backup zip file. If None, a timestamped filename in home directory is used.

    Returns:
        str: The full path to the created backup zip file.
    """
    try:
        if backup_path is None:
            timestamp = datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"pulseos_actors_backup_{timestamp}"
            backup_dir = Path.home()
            backup_path = str(backup_dir / backup_filename)
        else:
            backup_path = str(
                Path(backup_path).with_suffix("")
            )  # remove .zip if present to avoid duplication

        shutil.make_archive(backup_path, "zip", BASE_DIR)
        print(f"💾 Backup created at: {backup_path}.zip")
        return f"{backup_path}.zip"
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage companion identities: switch, create, backup, list, or delete."
    )
    parser.add_argument(
        "name", nargs="?", default=None, help="Name of the companion (e.g., gregorios)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--create", action="store_true", help="Create new companion with imprint zero"
    )
    group.add_argument(
        "--backup",
        action="store_true",
        help="Backup all companion identities to a zip archive",
    )
    group.add_argument("--list", action="store_true", help="List all companions")
    group.add_argument(
        "--delete",
        action="store_true",
        help="Delete a companion (requires name argument, confirmation required)",
    )
    args = parser.parse_args()

    if args.backup:
        backup_file = backup_identities()
        if backup_file:
            print(f"Backup file location: {backup_file}")
    elif args.create:
        if args.name is None:
            print("⚠️ Please specify a companion name to create.")
        else:
            create_identity(args.name)
    elif args.list:
        list_companions()
    elif args.delete:
        if args.name is None:
            print("⚠️ Please specify a companion name to delete.")
        else:
            delete_companion(args.name)
    else:
        if args.name is None:
            print("⚠️ Please specify a companion name to switch to.")
        else:
            switch_identity(args.name)
