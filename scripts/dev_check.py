#!/usr/bin/env python3

import subprocess

def run_command(description, command):
    print(f"🔍 Running {description}...")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"❌ {description} failed with exit code {result.returncode}")
    else:
        print(f"✅ {description} passed.\n")

if __name__ == "__main__":
    run_command("ruff lint", "ruff check .")
    run_command("mypy type checks", "mypy .")
    run_command("pytest", "pytest -v")