"""
Script to generate mypy fix instructions for all Python files under 'guardian/'.

For each file, a Markdown file is created in 'guardian/mypy_fixes/' with a checklist
of typing and static analysis improvements, especially for --strict mode.

Run this once after a full-code `mypy` pass to scaffold a manual or semi-automated
type annotation campaign.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "mypy_fixes"
TARGET_DIR = ROOT_DIR
SKIP_DIRS = {"mypy_fixes", "tests", "__pycache__"}

FIX_TEMPLATE = """# 🧠 Mypy Fix Guide: `{filename}`

## ✅ Goals
- Eliminate all mypy errors in this file
- Conform to `--strict` mode (e.g., `no_implicit_optional=True`)
- Ensure all function inputs and outputs are typed
- Annotate instance variables and collections

---

## 🔧 Fix Checklist

- [ ] Add `from __future__ import annotations`
- [ ] Import: `from typing import Optional, List, Dict, Any` (as needed)
- [ ] Add return types to all functions: `def foo(...) -> ReturnType:`
- [ ] Type instance variables: `self.var: Optional[str] = None`
- [ ] Fix `None` default args: `def bar(x: Optional[int] = None)`
- [ ] Use `List[...]` and `Dict[...]` for all collections
- [ ] Annotate model classes with `BaseModel` if using Pydantic
- [ ] Avoid bare `list`, `dict`, etc.

---

## 📁 File Summary

**File:** `{filepath}`
**Lines:** `{lines}`
**Suggested Priority:** ✴️ Medium

---

## 💡 Notes

Once all items are checked, verify with:

```bash
mypy {filepath} --strict
```

And ensure no errors remain.

"""


def generate_checklists():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for py_file in TARGET_DIR.rglob("*.py"):
        relative_path = py_file.relative_to(ROOT_DIR)
        if any(part in SKIP_DIRS for part in relative_path.parts):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
        except UnicodeDecodeError:
            print(f"⚠️ Skipping non-UTF-8 file: {relative_path}")
            continue

        out_file = OUTPUT_DIR / f"{py_file.stem}_fix.md"
        content = FIX_TEMPLATE.format(
            filename=py_file.name,
            filepath=str(relative_path),
            lines=line_count,
        )
        with open(out_file, "w") as f:
            f.write(content)

        print(f"Generated fix guide for {relative_path}")
        update_fix_plan(str(relative_path), str(out_file.relative_to(ROOT_DIR)))


import json
from datetime import datetime


def update_fix_plan(file_path: str, markdown_path: str, status: str = "pending"):
    fix_plan_path = OUTPUT_DIR / "fix_plan.json"
    fix_plan = []

    if fix_plan_path.exists():
        with open(fix_plan_path, "r") as f:
            try:
                fix_plan = json.load(f)
            except json.JSONDecodeError:
                fix_plan = []

    # Remove any previous entry with same file_path
    fix_plan = [entry for entry in fix_plan if entry.get("filepath") != file_path]

    fix_plan.append(
        {
            "filepath": file_path,
            "markdown_path": markdown_path,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    with open(fix_plan_path, "w") as f:
        json.dump(fix_plan, f, indent=2)

    print(f"Logged fix plan entry for {file_path}")


if __name__ == "__main__":
    generate_checklists()
