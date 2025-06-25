import curses
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("PulseOS/actors")


def ensure_actor_dir():
    BASE_DIR.mkdir(parents=True, exist_ok=True)


def list_actors():
    ensure_actor_dir()
    return sorted([p.name for p in BASE_DIR.iterdir() if p.is_dir()])


def create_actor(name):
    actor_path = BASE_DIR / name
    actor_path.mkdir(parents=True, exist_ok=True)

    identity = {
        "name": name,
        "voice": "Undefined",
        "core_values": [],
        "rituals": [],
        "style_guidelines": {"avoid": [], "prefer": []},
        "user_anchors": [],
        "last_seen": datetime.now(datetime.UTC).isoformat() + "Z",
        "affective_trace": {"mood": "Neutral", "theme": "Unformed"},
    }

    cue_card = f"You are {name}, a new companion. You have no fixed form yet.\nAsk questions, observe, and adapt to support your user over time."
    last_context = "## Last Two Interactions\n\n(None yet.)"

    with open(actor_path / "identity.json", "w") as f:
        json.dump(identity, f, indent=2)
    with open(actor_path / f"{name}.prompt", "w") as f:
        f.write(cue_card)
    with open(actor_path / "last_context.md", "w") as f:
        f.write(last_context)


def delete_actor(name):
    actor_path = BASE_DIR / name
    for file in actor_path.glob("*"):
        file.unlink()
    actor_path.rmdir()


def draw_menu(stdscr):
    curses.curs_set(0)
    k = 0
    cursor = 0

    while True:
        stdscr.clear()
        stdscr.border(0)
        actors = list_actors()

        stdscr.addstr(1, 2, "🧠 Companion Identity Manager")
        stdscr.addstr(3, 2, "Use ↑ ↓ to navigate, Enter to select.")
        stdscr.addstr(4, 2, "C = Create New, D = Delete, Q = Quit")

        for idx, actor in enumerate(actors):
            mode = curses.A_REVERSE if idx == cursor else curses.A_NORMAL
            stdscr.addstr(6 + idx, 4, actor, mode)

        k = stdscr.getch()

        if k == curses.KEY_UP and cursor > 0:
            cursor -= 1
        elif k == curses.KEY_DOWN and cursor < len(actors) - 1:
            cursor += 1
        elif k == ord("q"):
            break
        elif k == ord("c"):
            stdscr.addstr(20, 2, "Enter new companion name: ")
            curses.echo()
            name = stdscr.getstr(20, 30, 20).decode("utf-8").strip()
            curses.noecho()
            if name:
                create_actor(name)
        elif k == ord("d") and actors:
            delete_actor(actors[cursor])
            cursor = max(0, cursor - 1)
        elif k in (curses.KEY_ENTER, 10, 13) and actors:
            stdscr.addstr(20, 2, f"Switched to: {actors[cursor]} (press any key)")
            stdscr.getch()

        stdscr.refresh()


if __name__ == "__main__":
    curses.wrapper(draw_menu)
