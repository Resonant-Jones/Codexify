# 🗃️ HOTBOX: Dependency Ritual

Keep your Codexify dependencies consistent, conflict-free, and reproducible!

---

## 📌 **How it works**

You have:
- `requirements/*.in` → Editable input lists (your source of truth)
- `requirements/*.txt` → Auto-generated lockfiles (pin exact versions)

---

## 🧵 **Ritual**

### 1️⃣ Add or update packages

Edit the right `.in` file:

```bash
# Example: add 'rich' to base requirements
echo "rich>=13.0.0" >> requirements/requirements.in
```

---

### 2️⃣ Recompile and sync

Run your helper script to patch versions, recompile, and sync:

```bash
bash fix_dependencies.sh
```

What this does:
- Patches known version pins (like markitdown)
- Runs `pip-compile` for each `.in` → `.txt`
- Runs `pip-sync` to force local env to match
- Shows you outdated packages

---

### 3️⃣ Commit both!

```bash
git add requirements/*.in requirements/*.txt
git commit -m "🔒 Recompiled lockfiles"
```

---

## ✨ **One-liner reminder**

> **Add → Compile → Sync → Commit**

Stay fresh. Stay consistent. Stay HOTBOXED. 🔥