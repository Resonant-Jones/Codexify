import re
import subprocess
from collections import defaultdict
from pathlib import Path

REQUIREMENTS_DIR = Path("./requirements")
IN_FILES = list(REQUIREMENTS_DIR.glob("*.in"))


def parse_requirements(in_file):
    pattern = re.compile(r"^([a-zA-Z0-9_\-]+)([<>=!~]+[^\s#]+)?")
    parsed = {}
    with open(in_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = pattern.match(line)
            if match:
                pkg, constraint = match.groups()
                parsed[pkg.lower()] = constraint or ""
    return parsed


def find_conflicts():
    versions = defaultdict(list)
    for f in IN_FILES:
        reqs = parse_requirements(f)
        for pkg, constraint in reqs.items():
            versions[pkg].append((f.name, constraint))
    conflicts = {
        pkg: entries
        for pkg, entries in versions.items()
        if len({c for _, c in entries}) > 1
    }
    return conflicts


def display_conflicts(conflicts):
    if not conflicts:
        print("✅ No conflicts found!")
        return
    print("⚠️ Conflicting packages:")
    for pkg, entries in conflicts.items():
        print(f"  {pkg}:")
        for file_name, constraint in entries:
            print(f"    - {file_name}: {constraint or '*any*'}")
        unique_constraints = {
            constraint or "*any*" for _, constraint in entries
        }
        print(f"    🔍 Unique_Constraints: {unique_constraints}")


def run_pip_compile():
    for f in IN_FILES:
        print(f"🔄 Compiling {f.name}...")
        subprocess.run(["pip-compile", str(f)])


def main():
    print(f"🔍 Checking {len(IN_FILES)} requirements files...")
    conflicts = find_conflicts()
    display_conflicts(conflicts)
    if conflicts:
        print("\nPlease resolve manually or edit the .in files.")
    else:
        confirm = input(
            "✅ No conflicts. Run pip-compile for all? [y/N]: "
        ).lower()
        if confirm == "y":
            run_pip_compile()


if __name__ == "__main__":
    main()
