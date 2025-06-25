import argparse
import json
import os
from pathlib import Path

import openai  # Optional: required only if patches are fetched dynamically
from rich import print
from rich.console import Console
from rich.markdown import Markdown

FIX_PLAN_PATH = Path("fix_plan.json")
CONSOLE = Console()


def load_fix_plan() -> list[dict]:
    with open(FIX_PLAN_PATH, "r") as f:
        return json.load(f)


def save_fix_plan(plan: list[dict]):
    with open(FIX_PLAN_PATH, "w") as f:
        json.dump(plan, f, indent=2)


def extract_patch(md_path: Path) -> tuple[str, str]:
    with open(md_path, "r") as f:
        content = f.read()

    if "```python" not in content:
        raise ValueError(f"No patch block found in {md_path}")

    before = content.split("```python")[1]
    patch = before.split("```")[1]
    lines = patch.strip().splitlines()
    old_lines = []
    new_lines = []
    in_old = False
    in_new = False

    for line in lines:
        if line.startswith("-"):
            old_lines.append(line[1:].lstrip())
        elif line.startswith("+"):
            new_lines.append(line[1:].lstrip())

    return "\n".join(old_lines), "\n".join(new_lines)


def apply_patch(py_path: Path, old_code: str, new_code: str, dry_run=True):
    with open(py_path, "r") as f:
        content = f.read()

    if old_code not in content:
        raise ValueError(f"Old code not found in {py_path}")

    updated = content.replace(old_code, new_code)

    if dry_run:
        CONSOLE.rule(f"[bold yellow]Changes to {py_path}")
        print(Markdown(f"```diff\n- {old_code}\n+ {new_code}\n```"))
    else:
        with open(py_path, "w") as f:
            f.write(updated)


def main(dry_run: bool):
    plan = load_fix_plan()
    for entry in plan:
        if entry.get("status") == "patched":
            continue

        md_path = Path(entry["markdown_path"]).resolve()
        py_path = Path(entry["python_file"])

        try:
            old_code, new_code = extract_patch(md_path)
            apply_patch(py_path, old_code, new_code, dry_run=dry_run)
            if not dry_run:
                entry["status"] = "patched"
        except Exception as e:
            print(f"[red]Error processing {md_path}: {e}")

    if not dry_run:
        save_fix_plan(plan)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="Apply patches instead of dry run"
    )
    args = parser.parse_args()
    main(dry_run=not args.apply)
