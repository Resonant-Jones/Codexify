## 🗂️ Dependency Management

Codexify now uses a tiered dependency structure with clearly defined `.in` files for different functional areas, ensuring modular and maintainable dependency management.

| File | Purpose |
|------|---------|
| `requirements/base.in` | Core production dependencies |
| `requirements/ai.in` | AI-related dependencies |
| `requirements/websearch.in` | Web search integration dependencies |
| `requirements/dev.in` | Developer tools and utilities |
| `requirements/automation.in` | Automation and CI/CD dependencies |
| `requirements/all.in` | Aggregate of all dependencies for full installs |

> **Note:** Older flat requirement files such as `requirements.in`, `dev-requirements.in`, and others have been moved to `requirements/deprecated/` for reference.

---

## 📌 Managing Requirements

### 🛠️ How to update pinned requirements

1. **Install pip-tools** (if needed):

   ```bash
   pip install pip-tools
   ```

2. **Compile each `.in` file** in the `requirements/` directory to its corresponding `.txt` lock file:

   ```bash
   pip-compile requirements/base.in
   pip-compile requirements/ai.in
   pip-compile requirements/websearch.in
   pip-compile requirements/dev.in
   pip-compile requirements/automation.in
   ```

3. **Compile the aggregate `all.txt` lock file** to install all dependencies at once:

   ```bash
   pip-compile --output-file=requirements/all.txt requirements/all.in
   ```

4. **Install from the pinned lock files:**

   ```bash
   pip install -r requirements/base.txt
   pip install -r requirements/ai.txt
   pip install -r requirements/websearch.txt
   pip install -r requirements/dev.txt
   pip install -r requirements/automation.txt
   pip install -r requirements/all.txt  # For full environment setup
   ```

5. **Optional:** If you prefer a different folder structure, adjust the paths accordingly when running `pip-compile`.

This modular approach helps keep Codexify’s dependencies organized and scalable as the project grows.
