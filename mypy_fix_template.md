

🧠 Goal:

Eliminate all mypy errors from `<FILE_PATH>`, especially those caused by implicit Optional, missing type hints, and untyped collections. The project uses `--strict` mode (`no_implicit_optional=True`).

⸻

🧾 Instructions:
1. Enable postponed evaluation of annotations:
```python
from __future__ import annotations
```

2. Import required typing helpers:
```python
from typing import Optional, List, Dict, Any, Union
```

3. Fix function arguments with `None` defaults:
```python
# Before:
def my_function(foo: str = None)

# After:
def my_function(foo: Optional[str] = None)
```

4. Type all collections:
- Convert `[]` to `List[...]`
- Convert `{}` to `Dict[...]`
- Avoid bare `list`, `dict`, etc.

5. Annotate all return types:
```python
def my_function(...) -> None:
```

6. Annotate all instance variables:
```python
self.my_var: Optional[str] = None
```

7. Fix Pydantic or BaseModel definitions:
Ensure all model classes inherit from `BaseModel` and all fields are typed.

⸻

✅ Success Criteria:
- `mypy <FILE_PATH> --strict` returns 0 errors
- `python <FILE_PATH>` runs without crashing
- Type hints are specific, consistent, and avoid `Any` unless strictly necessary

📎 File: `<FILE_PATH>`
📊 Change summary: `+<INSERTIONS> / -<DELETIONS>`
