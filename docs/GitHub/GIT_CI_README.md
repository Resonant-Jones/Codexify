# Guardian Backend CI & Local Dev Notes

## 📋 Overview

This project uses GitHub Actions for CI/CD automation.  
We also use the official **GitHub Actions VSCode Extension** for:
- Syntax highlighting and validation for workflow `.yml` files.
- Managing workflows and logs directly in VSCode.
- Debugging workflow runs without leaving the IDE.

---

## ✅ Getting Started

1. Install the **GitHub Actions VSCode Extension** from the Marketplace.
2. Sign in with your GitHub account when prompted.
3. Open your repository locally in VSCode (remote/dev containers are not fully supported).
4. Use the Actions icon in the sidebar to:
   - View workflow runs.
   - Investigate failures.
   - Edit and validate workflow files with auto-complete.

---

## ⚙️ Project Structure Tips

- Always ensure your local `guardian/` package has correct `__init__.py` files.
- Keep `imprint_zero.py` and `user_management.py` in the `guardian/` directory.
- Adjust your `PYTHONPATH` to include the project root:
  ```
  export PYTHONPATH=$(pwd)
  ```

---

## 🧰 Common Debugging

- If you see `ModuleNotFoundError`, verify:
  1. The file physically exists.
  2. The module path matches the directory structure.
  3. `PYTHONPATH` includes the parent of `guardian/`.

- Use:
  ```
  python -c "import guardian.imprint_zero"
  ```
  to test your import path.

---

## 📜 License

This project is MIT licensed.  
Extension: GitHub Actions VSCode Extension © GitHub.
