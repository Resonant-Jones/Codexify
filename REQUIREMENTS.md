## 🗂️ Dependency Management

We use [pip-tools](https://github.com/jazzband/pip-tools) for reliable dependency pinning.

| File | Purpose |
|------|---------|
| `requirements.in` | Base production dependencies |
| `requirements.txt` | Pinned production lock file (compiled) |
| `dev-requirements.in` | Developer tools |
| `dev-requirements.txt` | Pinned dev tools lock file |
| `test-requirements.in` | Test tools (pytest, lint, coverage) |
| `test-requirements.txt` | Pinned test tools lock file |
| `docs-requirements.in` | Documentation build dependencies |
| `docs-requirements.txt` | Pinned docs lock file |

---

## 📌 Managing Requirements

### 🛠️ How to update pinned requirements

1. **Install pip-tools** (if needed):

   ```bash
   pip install pip-tools
   ```

2. **Compile each `.in` file** to its `.txt` lock file:

   ```bash
   # Base
   pip-compile requirements.in

   # Dev
   pip-compile dev-requirements.in

   # Tests
   pip-compile test-requirements.in

   # Docs
   pip-compile docs-requirements.in
   ```

3. **Install from the pinned lock files:**

   ```bash
   pip install -r requirements.txt
   pip install -r dev-requirements.txt
   pip install -r test-requirements.txt
   pip install -r docs-requirements.txt
   ```

4. **Optional:** If you use a `/requirements` folder instead, adjust the paths:

   ```bash
   pip-compile requirements/base.in
   pip-compile requirements/dev.in
   # ...
   ```